import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.models.workflow import get_all_workflows, get_workflow_by_id, update_workflow_result
from app.models.modules import execute_workflow
from app.models.log import log_system_action, log_workflow_action, clear_workflow_warnings
import uuid

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("scheduler")

# 关闭httpx和httpcore的调试日志，避免这些日志进入系统日志
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpcore.connection").setLevel(logging.WARNING)
logging.getLogger("httpcore.http11").setLevel(logging.WARNING)

# 全局调度器
scheduler = None

def init_scheduler():
    """初始化调度器"""
    global scheduler
    if scheduler is None:
        scheduler = BackgroundScheduler()
        scheduler.start()
        logger.info("调度器已启动")
        
        # 加载所有启用的工作流并设置调度
        workflows = get_all_workflows()
        for workflow in workflows:
            if workflow.get("enabled", False) and workflow.get("cron"):
                add_workflow_job(workflow)

def add_workflow_job(workflow: Dict[str, Any]):
    """添加工作流调度任务"""
    global scheduler
    
    if scheduler is None:
        init_scheduler()
    
    workflow_id = workflow.get("id")
    cron_expr = workflow.get("cron")
    
    if not workflow_id or not cron_expr:
        logger.error(f"无法添加工作流调度 - 缺少ID或CRON表达式: {workflow}")
        return
    
    # 检查是否已存在调度，如果有则移除
    remove_workflow_job(workflow_id)
    
    try:
        # 尝试解析CRON表达式
        try:
            trigger = CronTrigger.from_crontab(cron_expr)
        except Exception as cron_error:
            # CRON表达式无效
            logger.error(f"无效的CRON表达式 '{cron_expr}': {str(cron_error)}")
            return None
        
        # 添加新的调度
        job = scheduler.add_job(
            run_workflow,
            trigger,
            args=[workflow_id],
            id=str(workflow_id),
            replace_existing=True
        )
        
        # 验证任务是否成功添加
        if job and job.next_run_time:
            next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"已为工作流 '{workflow.get('name')}' (ID: {workflow_id}) 添加调度: {cron_expr}, 下次运行时间: {next_run}")
        else:
            logger.warning(f"工作流 '{workflow.get('name')}' (ID: {workflow_id}) 调度已添加，但未能获取下次运行时间")
        
        return job
    except Exception as e:
        logger.error(f"添加工作流调度出错: {str(e)}")
        return None

def remove_workflow_job(workflow_id: str):
    """移除工作流调度任务"""
    global scheduler
    if scheduler is None:
        return
    
    try:
        scheduler.remove_job(str(workflow_id))
        logger.info(f"已移除工作流ID: {workflow_id}的调度")
    except Exception as e:
        # 工作可能不存在，忽略错误
        pass

def run_workflow(workflow_id: str):
    """运行工作流"""
    logger.info(f"开始执行工作流 ID: {workflow_id}")
    
    try:
        workflow = get_workflow_by_id(workflow_id)
        if not workflow:
            logger.error(f"找不到工作流 ID: {workflow_id}")
            return
        
        # 创建异步线程运行工作流
        thread = threading.Thread(
            target=run_async_workflow,
            args=(workflow,)
        )
        thread.start()
        
    except Exception as e:
        logger.error(f"执行工作流出错 (ID: {workflow_id}): {e}")

def run_async_workflow(workflow: Dict[str, Any]):
    """在异步环境中运行工作流"""
    workflow_id = workflow.get("id", "unknown")
    workflow_name = workflow.get("name", "未命名工作流")
    
    try:
        # 创建事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 记录工作流开始运行
        log_workflow_action(workflow_id, "info", f"定时触发工作流 '{workflow_name}' 运行")
        
        # 运行工作流
        result = loop.run_until_complete(execute_workflow(workflow))
        
        # 记录执行结果
        success = result.get("success", False)
        if success:
            update_workflow_result(workflow_id, "执行成功")
            log_workflow_action(workflow_id, "info", f"工作流 '{workflow_name}' 执行成功", result)
            
            # 成功后清除工作流的警告状态
            clear_workflow_warnings(workflow_id)
            log_workflow_action(workflow_id, "info", f"工作流执行成功，已清除警告状态")
        else:
            error_msg = result.get("error", "未知错误")
            update_workflow_result(workflow_id, f"执行失败: {error_msg}")
            log_workflow_action(workflow_id, "warning", f"工作流 '{workflow_name}' 执行失败: {error_msg}", result)
            
            # 检查是否需要重试
            retry_count = workflow.get("retry_count", 0)
            if retry_count > 0:
                retry_interval = workflow.get("retry_interval", 5)  # 默认5分钟
                # 确保间隔至少为1分钟
                retry_interval = max(retry_interval, 1)
                log_workflow_action(workflow_id, "info", f"工作流 '{workflow_name}' 将在 {retry_interval} 分钟后重试, 剩余重试次数: {retry_count}")
                
                # 安排重试任务
                scheduler.add_job(
                    retry_workflow_job,
                    'date',
                    run_date=datetime.now() + timedelta(minutes=retry_interval),
                    args=[workflow_id, retry_count],
                    id=f"retry_{workflow_id}_{uuid.uuid4().hex}"
                )
        
        # 关闭事件循环
        loop.close()
        
    except Exception as e:
        error_msg = f"异步执行工作流出错: {str(e)}"
        log_workflow_action(workflow_id, "error", error_msg)
        
        # 即使出错也更新最后运行时间
        try:
            update_workflow_result(workflow.get("id"), f"执行出错: {str(e)}")
            
            # 检查是否需要重试
            retry_count = workflow.get("retry_count", 0)
            if retry_count > 0:
                retry_interval = workflow.get("retry_interval", 5)  # 默认5分钟
                # 确保间隔至少为1分钟
                retry_interval = max(retry_interval, 1)
                log_workflow_action(workflow_id, "info", f"工作流 '{workflow_name}' 将在 {retry_interval} 分钟后重试, 剩余重试次数: {retry_count}")
                
                # 安排重试任务
                scheduler.add_job(
                    retry_workflow_job,
                    'date',
                    run_date=datetime.now() + timedelta(minutes=retry_interval),
                    args=[workflow_id, retry_count],
                    id=f"retry_{workflow_id}_{uuid.uuid4().hex}"
                )
        except Exception as update_err:
            log_workflow_action(workflow_id, "error", f"更新工作流结果失败: {str(update_err)}")

def get_next_run_time(workflow_id: str) -> str:
    """获取工作流下次运行时间"""
    global scheduler
    if scheduler is None:
        return "调度器未启动"
    
    try:
        job = scheduler.get_job(str(workflow_id))
        if job and job.next_run_time:
            return job.next_run_time.strftime("%Y-%m-%d %H:%M:%S")
        return "未设置调度"
    except Exception:
        return "未设置调度"

def manual_run_workflow(workflow_id: str):
    """手动运行工作流"""
    logger.info(f"手动触发工作流 ID: {workflow_id}")
    run_workflow(workflow_id)

async def execute_workflow_job(workflow_id: str):
    """执行工作流的任务函数"""
    from app.models.modules import execute_workflow
    from app.models.workflow import get_workflow_by_id, update_workflow_result
    from app.models.log import log_workflow_action, clear_workflow_warnings
    
    # 获取工作流
    workflow = get_workflow_by_id(workflow_id)
    if not workflow:
        return
    
    workflow_name = workflow.get("name", "未知工作流")
    
    # 记录开始执行
    log_workflow_action(workflow_id, "info", f"开始执行工作流: {workflow_name}")
    
    # 执行工作流
    try:
        result = await execute_workflow(workflow)
        
        # 记录执行结果
        success = result.get("success", False)
        if success:
            update_workflow_result(workflow_id, "执行成功")
            log_workflow_action(workflow_id, "info", f"工作流 '{workflow_name}' 执行成功", result)
            
            # 成功后清除工作流的警告状态
            clear_workflow_warnings(workflow_id)
            log_workflow_action(workflow_id, "info", f"工作流执行成功，已清除警告状态")
        else:
            update_workflow_result(workflow_id, f"执行失败: {result.get('error', '未知错误')}")
            log_workflow_action(workflow_id, "warning", f"工作流 '{workflow_name}' 执行失败", result)
            
            # 检查是否需要重试
            retry_count = workflow.get("retry_count", 0)
            if retry_count > 0:
                retry_interval = workflow.get("retry_interval", 5)  # 默认5分钟
                # 确保间隔至少为1分钟
                retry_interval = max(retry_interval, 1)
                log_workflow_action(workflow_id, "info", f"工作流 '{workflow_name}' 将在 {retry_interval} 分钟后重试, 剩余重试次数: {retry_count}")
                
                # 安排重试任务
                scheduler.add_job(
                    retry_workflow_job,
                    'date',
                    run_date=datetime.now() + timedelta(minutes=retry_interval),
                    args=[workflow_id, retry_count],
                    id=f"retry_{workflow_id}_{uuid.uuid4().hex}"
                )
    except Exception as e:
        # 记录执行异常
        update_workflow_result(workflow_id, f"执行异常: {str(e)}")
        log_workflow_action(workflow_id, "error", f"工作流 '{workflow_name}' 执行异常", {"error": str(e)})
        
        # 检查是否需要重试
        retry_count = workflow.get("retry_count", 0)
        if retry_count > 0:
            retry_interval = workflow.get("retry_interval", 5)  # 默认5分钟
            # 确保间隔至少为1分钟
            retry_interval = max(retry_interval, 1)
            log_workflow_action(workflow_id, "info", f"工作流 '{workflow_name}' 将在 {retry_interval} 分钟后重试, 剩余重试次数: {retry_count}")
            
            # 安排重试任务
            scheduler.add_job(
                retry_workflow_job,
                'date',
                run_date=datetime.now() + timedelta(minutes=retry_interval),
                args=[workflow_id, retry_count],
                id=f"retry_{workflow_id}_{uuid.uuid4().hex}"
            )

async def retry_workflow_job(workflow_id: str, remaining_retries: int):
    """重试执行工作流的任务函数"""
    from app.models.modules import execute_workflow
    from app.models.workflow import get_workflow_by_id, update_workflow_result
    from app.models.log import log_workflow_action, clear_workflow_warnings
    
    # 获取工作流
    workflow = get_workflow_by_id(workflow_id)
    if not workflow:
        return
    
    workflow_name = workflow.get("name", "未知工作流")
    
    # 记录重试执行
    log_workflow_action(workflow_id, "info", f"重试执行工作流: {workflow_name}, 剩余重试次数: {remaining_retries-1}")
    
    # 执行工作流
    try:
        result = await execute_workflow(workflow)
        
        # 记录执行结果
        success = result.get("success", False)
        if success:
            update_workflow_result(workflow_id, "执行成功")
            log_workflow_action(workflow_id, "info", f"工作流 '{workflow_name}' 重试执行成功", result)
            
            # 成功后清除工作流的警告状态 - 通过删除所有WARNING级别的日志
            clear_workflow_warnings(workflow_id)
            log_workflow_action(workflow_id, "info", f"工作流 '{workflow_name}' 重试成功，已清除警告状态")
        else:
            update_workflow_result(workflow_id, f"执行失败: {result.get('error', '未知错误')}")
            log_workflow_action(workflow_id, "warning", f"工作流 '{workflow_name}' 重试执行失败", result)
            
            # 检查是否还有重试次数
            if remaining_retries > 1:
                retry_interval = workflow.get("retry_interval", 5)  # 默认5分钟
                # 确保间隔至少为1分钟
                retry_interval = max(retry_interval, 1)
                log_workflow_action(workflow_id, "info", f"工作流 '{workflow_name}' 将在 {retry_interval} 分钟后再次重试, 剩余重试次数: {remaining_retries-1}")
                
                # 安排重试任务
                scheduler.add_job(
                    retry_workflow_job,
                    'date',
                    run_date=datetime.now() + timedelta(minutes=retry_interval),
                    args=[workflow_id, remaining_retries-1],
                    id=f"retry_{workflow_id}_{uuid.uuid4().hex}"
                )
            else:
                log_workflow_action(workflow_id, "warning", f"工作流 '{workflow_name}' 已达到最大重试次数，不再重试")
    except Exception as e:
        # 记录执行异常
        update_workflow_result(workflow_id, f"执行异常: {str(e)}")
        log_workflow_action(workflow_id, "error", f"工作流 '{workflow_name}' 重试执行异常", {"error": str(e)})
        
        # 检查是否还有重试次数
        if remaining_retries > 1:
            retry_interval = workflow.get("retry_interval", 5)  # 默认5分钟
            # 确保间隔至少为1分钟
            retry_interval = max(retry_interval, 1)
            log_workflow_action(workflow_id, "info", f"工作流 '{workflow_name}' 将在 {retry_interval} 分钟后再次重试, 剩余重试次数: {remaining_retries-1}")
            
            # 安排重试任务
            scheduler.add_job(
                retry_workflow_job,
                'date',
                run_date=datetime.now() + timedelta(minutes=retry_interval),
                args=[workflow_id, remaining_retries-1],
                id=f"retry_{workflow_id}_{uuid.uuid4().hex}"
            ) 