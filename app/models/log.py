import os
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Tuple
from pydantic import BaseModel, Field

from app.utils.data_dir import get_data_dir
from app.utils.config import get_config

# 日志文件路径
SYSTEM_LOG_FILE_PATH = os.path.join(get_data_dir(), "system_logs.json")
WORKFLOW_LOG_FILE_PATH = os.path.join(get_data_dir(), "workflow_logs.json")

class LogEntry(BaseModel):
    """日志条目模型"""
    id: str
    timestamp: str
    level: str  # debug, info, warning, error
    source: str  # 'system' 或 workflow_id
    message: str
    details: Optional[Dict[str, Any]] = None

def _ensure_logs_file(file_path: str):
    """确保日志文件存在"""
    if not os.path.exists(file_path):
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        # 创建空的日志文件
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump([], f)

def init_logs():
    """初始化日志系统，确保日志文件存在"""
    _ensure_logs_file(SYSTEM_LOG_FILE_PATH)
    _ensure_logs_file(WORKFLOW_LOG_FILE_PATH)

def _load_logs(log_type: str = "system") -> List[Dict[str, Any]]:
    """加载指定类型的日志"""
    file_path = SYSTEM_LOG_FILE_PATH if log_type == "system" else WORKFLOW_LOG_FILE_PATH
    _ensure_logs_file(file_path)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        # 如果文件损坏，创建新的空日志
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump([], f)
        return []
    except Exception as e:
        logging.error(f"加载日志文件失败: {str(e)}")
        return []

def _save_logs(logs: List[Dict[str, Any]], log_type: str = "system"):
    """保存指定类型的日志"""
    file_path = SYSTEM_LOG_FILE_PATH if log_type == "system" else WORKFLOW_LOG_FILE_PATH
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"保存日志文件失败: {str(e)}")

def setup_logging(log_level: str = "INFO"):
    """
    设置Python内置日志系统，将日志输出到控制台和系统日志
    
    Args:
        log_level: 日志级别
    """
    # 获取数值日志级别
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO
        logging.warning(f'无效的日志级别: {log_level}，使用默认值INFO')
    
    # 获取根日志记录器
    logger = logging.getLogger()
    logger.setLevel(numeric_level)
    
    # 清除现有的处理器
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    
    # 创建格式化器
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # 创建自定义处理器，将日志加入到系统日志中
    class SystemLogHandler(logging.Handler):
        def emit(self, record):
            try:
                # 跳过外部库的调试日志，避免它们进入系统日志
                if record.levelno <= logging.DEBUG and (
                    record.name.startswith('httpx') or 
                    record.name.startswith('httpcore') or
                    record.name.startswith('urllib3')
                ):
                    return
                
                level_map = {
                    logging.DEBUG: 'debug',
                    logging.INFO: 'info',
                    logging.WARNING: 'warning',
                    logging.ERROR: 'error',
                    logging.CRITICAL: 'error'
                }
                level = level_map.get(record.levelno, 'info')
                message = self.format(record)
                log_system_action(level, message)
            except Exception:
                self.handleError(record)
    
    # 添加自定义处理器
    system_handler = SystemLogHandler()
    system_handler.setLevel(numeric_level)
    system_handler.setFormatter(formatter)
    
    # 将处理器添加到根日志记录器
    logger.addHandler(console_handler)
    logger.addHandler(system_handler)
    
    # 确保日志文件存在
    _ensure_logs_file(SYSTEM_LOG_FILE_PATH)
    _ensure_logs_file(WORKFLOW_LOG_FILE_PATH)
    
    # 记录日志系统启动信息
    logging.info("日志系统已初始化")

def add_log(level: str, source: str, message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    添加一条日志
    
    Args:
        level: 日志级别，如 'debug', 'info', 'warning', 'error'
        source: 日志来源，'system' 或工作流ID
        message: 日志消息
        details: 日志的详细数据
        
    Returns:
        新添加的日志记录
    """
    # 规范化日志级别
    level = level.lower()
    if level not in ['debug', 'info', 'warning', 'error']:
        level = 'info'
    
    # 创建日志条目
    log_entry = LogEntry(
        id=str(uuid.uuid4()),
        timestamp=datetime.now().isoformat(),
        level=level,
        source=source,
        message=message,
        details=details
    ).dict()
    
    # 确定日志类型和文件
    log_type = "system" if source == "system" else "workflow"
    
    # 添加到对应日志文件
    logs = _load_logs(log_type)
    logs.append(log_entry)
    
    # 获取日志保留条数配置
    config = get_config()
    log_max_entries = config.get("log_max_entries", 10000)
    
    # 如果日志太多，保留最新的配置数量条
    if len(logs) > log_max_entries:
        logs = logs[-log_max_entries:]
    
    _save_logs(logs, log_type)
    return log_entry

def get_logs(
    log_type: str = "system", 
    workflow_id: Optional[str] = None,
    log_level: Optional[str] = None,
    page: int = 1,
    page_size: int = 50
) -> Tuple[List[Dict[str, Any]], int]:
    """
    获取日志列表，支持过滤和分页
    
    Args:
        log_type: 日志类型，'system' 或 'workflow'
        workflow_id: 工作流ID，仅当log_type为'workflow'时有效
        log_level: 日志级别过滤
        page: 页码，从1开始
        page_size: 每页记录数
        
    Returns:
        (日志列表, 总记录数)
    """
    # 根据类型加载日志
    if log_type == "system":
        logs = _load_logs("system")
        # 系统日志不需要按工作流ID过滤
        filtered_logs = logs
    elif log_type == "workflow":
        logs = _load_logs("workflow")
        # 如果指定了工作流ID，则按ID过滤
        if workflow_id:
            filtered_logs = [log for log in logs if log.get("source") == workflow_id]
        else:
            # 否则返回所有工作流日志
            filtered_logs = logs
    else:
        # 如果类型不明确，加载所有日志
        system_logs = _load_logs("system")
        workflow_logs = _load_logs("workflow")
        logs = system_logs + workflow_logs
        # 如果指定了工作流ID，过滤组合日志
        if workflow_id:
            filtered_logs = [log for log in logs if log.get("source") == workflow_id]
        else:
            filtered_logs = logs
    
    # 过滤日志级别
    if log_level and log_level.lower() not in ["all", "none", ""]:
        filtered_logs = [log for log in filtered_logs if log.get("level") == log_level.lower()]
    
    # 总记录数
    total = len(filtered_logs)
    
    # 按时间倒序排序
    filtered_logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    # 分页
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    # 返回分页后的日志和总数
    return filtered_logs[start_idx:end_idx], total

def clear_logs(log_type: str = "system", workflow_id: Optional[str] = None) -> int:
    """
    清除指定类型的日志
    
    Args:
        log_type: 日志类型，'system' 或 'workflow'
        workflow_id: 工作流ID，仅当log_type为'workflow'时有效
        
    Returns:
        清除的日志数量
    """
    if log_type == "system":
        logs = _load_logs("system")
        original_count = len(logs)
        _save_logs([], "system")
        return original_count
    elif log_type == "workflow":
        if workflow_id:
            logs = _load_logs("workflow")
            original_count = len(logs)
            new_logs = [log for log in logs if log.get("source") != workflow_id]
            cleared_count = original_count - len(new_logs)
            _save_logs(new_logs, "workflow")
            return cleared_count
        else:
            logs = _load_logs("workflow")
            original_count = len(logs)
            _save_logs([], "workflow")
            return original_count
    else:
        # 清空所有日志
        system_count = len(_load_logs("system"))
        workflow_count = len(_load_logs("workflow"))
        _save_logs([], "system")
        _save_logs([], "workflow")
        return system_count + workflow_count

def log_system_action(level: str, message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """记录系统操作日志"""
    return add_log(level, "system", message, details)

def log_workflow_action(workflow_id: str, level: str, message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """记录工作流操作日志"""
    return add_log(level, workflow_id, message, details)

# 为了向后兼容，保留旧的函数名但使用新的实现
def get_system_logs(limit: int = 100, offset: int = 0, level: Optional[str] = None) -> List[Dict[str, Any]]:
    """获取系统日志（向后兼容）"""
    logs, _ = get_logs("system", None, level, offset//limit + 1, limit)
    return logs

def get_workflow_logs(workflow_id: Optional[str] = None, limit: int = 100, offset: int = 0, level: Optional[str] = None) -> List[Dict[str, Any]]:
    """获取工作流日志（向后兼容）"""
    logs, _ = get_logs("workflow", workflow_id, level, offset//limit + 1, limit)
    return logs

# 迁移旧日志到新系统
def migrate_old_logs():
    """将旧的日志格式迁移到新的分离格式"""
    old_log_file = os.path.join(get_data_dir(), "logs.json")
    if os.path.exists(old_log_file):
        try:
            with open(old_log_file, "r", encoding="utf-8") as f:
                old_logs = json.load(f)
            
            system_logs = [log for log in old_logs if log.get("source") == "system"]
            workflow_logs = [log for log in old_logs if log.get("source") != "system"]
            
            # 如果新文件不存在，先创建
            _ensure_logs_file(SYSTEM_LOG_FILE_PATH)
            _ensure_logs_file(WORKFLOW_LOG_FILE_PATH)
            
            # 加载现有的新日志
            existing_system_logs = _load_logs("system")
            existing_workflow_logs = _load_logs("workflow")
            
            # 合并日志
            merged_system_logs = existing_system_logs + system_logs
            merged_workflow_logs = existing_workflow_logs + workflow_logs
            
            # 按时间排序
            merged_system_logs.sort(key=lambda x: x.get("timestamp", ""))
            merged_workflow_logs.sort(key=lambda x: x.get("timestamp", ""))
            
            # 保存合并后的日志
            _save_logs(merged_system_logs, "system")
            _save_logs(merged_workflow_logs, "workflow")
            
            # 重命名旧日志文件作为备份
            os.rename(old_log_file, old_log_file + ".bak")
            
            logging.info("成功迁移旧日志到新的分离存储格式")
        except Exception as e:
            logging.error(f"迁移旧日志失败: {str(e)}")

def clear_workflow_warnings(workflow_id: str) -> int:
    """清除工作流的所有警告日志，用于重试成功后清除警告状态
    
    Args:
        workflow_id: 工作流ID
        
    Returns:
        int: 清除的日志数量
    """
    init_logs()
    logs = _load_logs("workflow")
    
    # 过滤出需要保留的日志（非该工作流的WARNING日志）
    filtered_logs = [
        log for log in logs 
        if not (log.get("source") == workflow_id and 
                log.get("level") == "warning")
    ]
    
    # 计算移除的日志数量
    removed_count = len(logs) - len(filtered_logs)
    
    # 只有在有日志被移除时才写入文件
    if removed_count > 0:
        _save_logs(filtered_logs, "workflow")
    
    return removed_count 