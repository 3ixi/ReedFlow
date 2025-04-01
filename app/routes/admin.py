from fastapi import APIRouter, Request, Depends, Form, HTTPException, status, Query, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse, Response
from fastapi.templating import Jinja2Templates
from typing import Optional, Dict, Any, List
import json
import smtplib
import httpx
from email.header import Header
from email.mime.text import MIMEText
import uuid
import ast
import re
from datetime import datetime
import ssl

from app.routes.auth import get_current_user
from app.models.workflow import get_all_workflows, get_workflow_by_id, save_workflow, delete_workflow, update_workflow_status, export_workflow, import_workflow
from app.models.module_types import get_all_module_types
from app.utils.config import get_config, update_config, get_account_config, update_account_config
from app.utils.scheduler import add_workflow_job, remove_workflow_job, get_next_run_time, manual_run_workflow
from app.models.log import get_logs, clear_logs, log_system_action

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user: str = Depends(get_current_user)):
    """管理仪表盘页面"""
    workflows = get_all_workflows()
    # 添加下次运行时间
    for workflow in workflows:
        workflow["next_run"] = get_next_run_time(workflow.get("id", ""))
        
        # 检查是否有警告日志，如有则添加警告标记
        has_warning = False
        # 获取最近的工作流日志
        logs, _ = get_logs(
            log_type="workflow", 
            workflow_id=workflow.get("id"), 
            log_level="WARNING", 
            page=1, 
            page_size=1
        )
        if logs and len(logs) > 0:
            has_warning = True
        
        workflow["has_warning"] = has_warning
    
    return templates.TemplateResponse(
        "admin/dashboard.html", 
        {"request": request, "workflows": workflows}
    )

@router.get("/workflow/new", response_class=HTMLResponse)
async def new_workflow_page(request: Request, user: str = Depends(get_current_user)):
    """新建工作流页面"""
    module_types = get_all_module_types()
    
    return templates.TemplateResponse(
        "admin/workflow_editor.html", 
        {
            "request": request, 
            "workflow": {"id": "", "name": "", "description": "", "modules": [], "connections": []},
            "module_types": module_types,
            "is_new": True
        }
    )

@router.get("/workflow/{workflow_id}", response_class=HTMLResponse)
async def edit_workflow_page(workflow_id: str, request: Request, user: str = Depends(get_current_user)):
    """编辑工作流页面"""
    workflow = get_workflow_by_id(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    module_types = get_all_module_types()
    
    return templates.TemplateResponse(
        "admin/workflow_editor.html", 
        {
            "request": request, 
            "workflow": workflow,
            "module_types": module_types,
            "is_new": False
        }
    )

@router.post("/workflow/save")
async def save_workflow_api(request: Request, user: str = Depends(get_current_user)):
    """保存工作流API"""
    data = await request.json()
    workflow = data.get("workflow")
    
    if not workflow or not workflow.get("name"):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "message": "工作流名称不能为空"}
        )
    
    # 保存工作流
    saved_workflow = save_workflow(workflow)
    
    # 设置定时任务
    if workflow.get("enabled") and workflow.get("cron"):
        add_workflow_job(workflow)
    else:
        remove_workflow_job(workflow.get("id"))
    
    # 记录日志
    log_system_action("info", f"保存工作流: {workflow.get('name')}", {"workflow_id": saved_workflow.get("id")})
    
    return JSONResponse(
        content={"success": True, "message": "工作流保存成功", "workflow": saved_workflow}
    )

@router.post("/workflow/{workflow_id}/toggle")
async def toggle_workflow_status(workflow_id: str, request: Request, user: str = Depends(get_current_user)):
    """切换工作流启用状态"""
    data = await request.json()
    enabled = data.get("enabled", False)
    
    workflow = get_workflow_by_id(workflow_id)
    if not workflow:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"success": False, "message": "工作流不存在"}
        )
    
    # 更新工作流状态
    result = update_workflow_status(workflow_id, enabled)
    
    # 更新调度任务
    if enabled and workflow.get("cron"):
        add_workflow_job(workflow)
    else:
        remove_workflow_job(workflow_id)
    
    # 记录日志
    status_text = "启用" if enabled else "禁用"
    log_system_action("info", f"{status_text}工作流: {workflow.get('name')}", {"workflow_id": workflow_id})
    
    return JSONResponse(
        content={"success": result, "message": f"工作流已{'启用' if enabled else '禁用'}"}
    )

@router.delete("/workflow/{workflow_id}")
async def delete_workflow_api(workflow_id: str, user: str = Depends(get_current_user)):
    """删除工作流"""
    workflow = get_workflow_by_id(workflow_id)
    if not workflow:
        return JSONResponse(
            content={"success": False, "message": "工作流不存在"}
        )
    
    workflow_name = workflow.get("name", "未知工作流")
    
    # 删除工作流
    result = delete_workflow(workflow_id)
    
    # 删除调度任务
    if result:
        remove_workflow_job(workflow_id)
        # 记录日志
        log_system_action("info", f"删除工作流: {workflow_name}", {"workflow_id": workflow_id})
    
    return JSONResponse(
        content={"success": result, "message": "工作流删除成功" if result else "工作流不存在"}
    )

@router.post("/workflow/{workflow_id}/run")
async def run_workflow_api(workflow_id: str, user: str = Depends(get_current_user)):
    """手动运行工作流"""
    workflow = get_workflow_by_id(workflow_id)
    if not workflow:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"success": False, "message": "工作流不存在"}
        )
    
    # 手动触发工作流
    manual_run_workflow(workflow_id)
    
    # 记录日志
    log_system_action("info", f"手动运行工作流: {workflow.get('name')}", {"workflow_id": workflow_id})
    
    return JSONResponse(
        content={"success": True, "message": "工作流已触发执行"}
    )

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, user: str = Depends(get_current_user)):
    """系统设置页面"""
    config = get_config()
    
    return templates.TemplateResponse(
        "admin/settings.html", 
        {"request": request, "config": config}
    )

@router.get("/account_config", response_class=HTMLResponse)
async def account_config_page(request: Request, user: str = Depends(get_current_user)):
    """账号配置管理页面"""
    account_config = get_account_config()
    
    return templates.TemplateResponse(
        "admin/account_config.html", 
        {"request": request, "account_config": account_config}
    )

@router.post("/account_config/save")
async def save_account_config(request: Request, user: str = Depends(get_current_user)):
    """保存账号配置"""
    data = await request.json()
    config = data.get("config", {})
    
    # 记录日志
    log_system_action("info", "更新账号配置信息")
    
    # 更新配置
    update_account_config(config)
    
    return JSONResponse(
        content={"success": True, "message": "账号配置保存成功"}
    )

@router.post("/settings/save")
async def save_settings(request: Request, user: str = Depends(get_current_user)):
    """保存系统设置"""
    data = await request.json()
    config = data.get("config", {})
    
    # 记录日志
    log_system_action("info", "更新系统设置", {"changed_fields": list(config.keys())})
    
    # 确保email配置中包含default_recipient字段
    if 'email' in config and 'default_recipient' not in config['email']:
        config['email']['default_recipient'] = ""
    
    # 更新配置
    update_config(config)
    
    return JSONResponse(
        content={"success": True, "message": "设置保存成功"}
    )

@router.post("/settings/test-notification")
async def test_notification(request: Request, user: str = Depends(get_current_user)):
    """测试通知服务"""
    data = await request.json()
    notification_type = data.get("type", "")
    notification_config = data.get("config", {})
    
    # 记录测试动作
    log_system_action("info", "测试通知服务", {"type": notification_type})
    
    if notification_type == "email":
        # 测试邮件服务
        try:
            smtp_server = notification_config.get("smtp_server", "")
            smtp_port = notification_config.get("smtp_port", 465)
            smtp_user = notification_config.get("smtp_user", "")
            smtp_password = notification_config.get("smtp_password", "")
            sender = notification_config.get("sender", "") or smtp_user
            
            # 获取指定的收件人，优先使用用户在测试请求中提供的default_recipient
            default_recipient = notification_config.get("default_recipient", "")
            # 如果测试请求中提供了收件人地址，就使用这个地址；否则回退到SMTP用户自己
            recipient = default_recipient if default_recipient else smtp_user
            
            if not smtp_server or not smtp_user:
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "message": "邮件服务未配置完整"}
                )
                
            if not recipient:
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "message": "未设置收件人地址"}
                )
            
            # 创建测试邮件
            msg = MIMEText("这是一封测试邮件，来自ReedFlow系统。\n\n如果您收到此邮件，说明您的邮件服务配置正确。", 'plain', 'utf-8')
            msg['Subject'] = Header("ReedFlow测试通知", 'utf-8')
            msg['From'] = sender
            msg['To'] = recipient
            
            try:
                # 尝试使用SSL连接
                server = smtplib.SMTP_SSL(smtp_server, smtp_port)
                server.login(smtp_user, smtp_password)
                server.sendmail(sender, [recipient], msg.as_string())
                server.quit()
                
                log_system_action("info", "邮件发送测试成功", {"server": smtp_server, "port": smtp_port, "recipient": recipient})
                return JSONResponse(
                    content={"success": True, "message": f"邮件发送成功！请检查 {recipient} 的收件箱。"}
                )
            except ssl.SSLError as ssl_err:
                log_system_action("error", "邮件发送测试失败 - SSL错误", {"error": str(ssl_err)})
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "message": f"SSL连接错误: {str(ssl_err)}。请确认端口配置正确且支持SSL。QQ邮箱建议使用端口465。"}
                )
            except smtplib.SMTPAuthenticationError as auth_err:
                log_system_action("error", "邮件发送测试失败 - 认证错误", {"error": str(auth_err)})
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "message": f"邮箱认证失败: {str(auth_err)}。请检查账号和密码是否正确（QQ邮箱需使用授权码而非登录密码）。"}
                )
            except Exception as e:
                # 如果SSL方式失败，尝试使用非SSL连接
                log_system_action("warning", "SSL连接失败，尝试普通连接", {"error": str(e)})
                try:
                    server = smtplib.SMTP(smtp_server, smtp_port)
                    server.ehlo()
                    if server.has_extn('STARTTLS'):
                        server.starttls()
                        server.ehlo()
                    server.login(smtp_user, smtp_password)
                    server.sendmail(sender, [recipient], msg.as_string())
                    server.quit()
                    
                    log_system_action("info", "邮件发送测试成功（非SSL模式）", {"server": smtp_server, "port": smtp_port})
                    return JSONResponse(
                        content={"success": True, "message": "邮件发送成功（使用非SSL模式）！请检查收件箱。"}
                    )
                except Exception as e2:
                    log_system_action("error", "邮件发送测试失败", {"error": str(e2)})
                    return JSONResponse(
                        status_code=400,
                        content={"success": False, "message": f"邮件发送失败: {str(e2)}。请检查服务器地址和端口配置，QQ邮箱推荐端口465(SSL)或587(TLS)。"}
                    )
        except Exception as e:
            log_system_action("error", "邮件发送测试失败", {"error": str(e)})
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": f"邮件服务错误: {str(e)}"}
            )
            
    elif notification_type == "wxpusher":
        # 测试WxPusher服务
        try:
            app_token = notification_config.get("app_token", "")
            default_uid = notification_config.get("default_uid", "")
            
            if not app_token:
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "message": "WxPusher AppToken未配置"}
                )
            
            # 创建测试消息
            wxpusher_data = {
                "appToken": app_token,
                "content": "这是一条测试消息，来自ReedFlow系统。",
                "summary": "ReedFlow测试通知",
                "contentType": 1  # 文本类型
            }
            
            # 如果有默认UID，则使用UID发送；否则，使用topicIds
            if default_uid:
                wxpusher_data["uids"] = [default_uid]
                log_system_action("info", "测试WxPusher服务", {"app_token": app_token, "uid": default_uid})
            else:
                wxpusher_data["topicIds"] = [1]
                log_system_action("info", "测试WxPusher服务(使用topicId)", {"app_token": app_token, "topicId": 1})
            
            # 发送请求
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://wxpusher.zjiecode.com/api/send/message", 
                    json=wxpusher_data
                )
                response_json = response.json()
                
                if response_json.get("success"):
                    return JSONResponse(
                        content={"success": True, "message": "微信推送发送成功！请查看微信。"}
                    )
                else:
                    log_system_action("error", "测试WxPusher服务失败", {"response": response_json})
                    return JSONResponse(
                        status_code=400,
                        content={"success": False, "message": f"微信推送失败: {response_json.get('msg')}"}
                    )
        except Exception as e:
            log_system_action("error", "测试WxPusher服务失败", {"error": str(e)})
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": f"微信推送失败: {str(e)}"}
            )
    
    elif notification_type == "pushplus":
        # 测试PushPlus服务
        try:
            token = notification_config.get("token", "")
            topic = notification_config.get("topic", "")
            
            if not token:
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "message": "PushPlus Token未配置"}
                )
            
            # 创建测试消息
            pushplus_data = {
                "token": token,
                "title": "ReedFlow测试通知",
                "content": "这是一条测试消息，来自ReedFlow系统。",
                "template": "html"
            }
            
            # 如果提供了topic，添加到请求中
            if topic:
                pushplus_data["topic"] = topic
            
            # 发送请求
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://www.pushplus.plus/send", 
                    json=pushplus_data
                )
                response_json = response.json()
                
                if response_json.get("code") == 200:
                    return JSONResponse(
                        content={"success": True, "message": "PushPlus推送发送成功！"}
                    )
                else:
                    log_system_action("error", "测试PushPlus服务失败", {"response": response_json})
                    return JSONResponse(
                        status_code=400,
                        content={"success": False, "message": f"PushPlus推送失败: {response_json.get('msg')}"}
                    )
        except Exception as e:
            log_system_action("error", "测试PushPlus服务失败", {"error": str(e)})
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": f"PushPlus推送失败: {str(e)}"}
            )
    
    else:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": f"不支持的通知类型: {notification_type}"}
        )

@router.get("/logs", response_class=HTMLResponse)
async def logs_page(
    request: Request, 
    user: str = Depends(get_current_user),
    type: str = Query("system", description="日志类型: system 或 workflow"),
    workflow_id: Optional[str] = Query(None, description="工作流ID，仅当type=workflow时有效"),
    level: Optional[str] = Query(None, description="日志级别: debug, info, warning, error"),
    page: int = Query(1, description="页码", ge=1),
    page_size: int = Query(50, description="每页数量", ge=1, le=100),
):
    """日志页面"""
    # 获取所有工作流，用于在UI中展示
    workflows = get_all_workflows()
    
    # 获取日志
    logs, total = get_logs(
        log_type=type,
        workflow_id=workflow_id,
        log_level=level,
        page=page,
        page_size=page_size
    )
    
    return templates.TemplateResponse(
        "admin/logs.html", 
        {
            "request": request, 
            "logs": logs,
            "workflows": workflows,
            "type": type,
            "workflow_id": workflow_id,
            "level": level,
            "page": page,
            "page_size": page_size,
            "total": total
        }
    )

@router.post("/logs/clear")
async def clear_logs_api(
    request: Request, 
    user: str = Depends(get_current_user),
    type: str = Form(..., description="日志类型: system 或 workflow"),
    workflow_id: Optional[str] = Form(None, description="工作流ID，仅当type=workflow时有效")
):
    """清空日志"""
    # 执行清除日志操作
    count = clear_logs(log_type=type, workflow_id=workflow_id)
    
    # 记录清除日志的操作
    log_system_action(
        "info", 
        f"清空了{count}条{type}日志", 
        {"log_type": type, "count": count, "workflow_id": workflow_id}
    )
    
    # 返回JSON响应
    return JSONResponse(
        content={"success": True, "message": f"已清空{count}条日志"}
    )

@router.get("/modules", response_class=HTMLResponse)
async def modules_page(request: Request, user: str = Depends(get_current_user)):
    """模块管理页面"""
    module_types = get_all_module_types()
    
    return templates.TemplateResponse(
        "admin/modules.html", 
        {"request": request, "module_types": module_types}
    )

@router.get("/documentation", response_class=HTMLResponse)
async def documentation_page(request: Request, user: str = Depends(get_current_user)):
    """使用文档页面"""
    return templates.TemplateResponse(
        "admin/documentation.html", 
        {"request": request}
    )

@router.get("/python-converter", response_class=HTMLResponse)
async def python_converter_page(request: Request, user: str = Depends(get_current_user)):
    """Python脚本转换页面"""
    return templates.TemplateResponse(
        "admin/python_converter.html", 
        {"request": request}
    )

@router.get("/workflow/export/{workflow_id}")
async def export_workflow_endpoint(
    workflow_id: str,
    user: str = Depends(get_current_user)
):
    """导出工作流为.rfj文件（zlib压缩）"""
    # 导出工作流数据
    data, filename = export_workflow(workflow_id)
    
    if not data:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    # 记录操作
    log_system_action("info", f"导出工作流", {"workflow_id": workflow_id, "filename": filename})
    
    # 使用ASCII文件名，避免编码问题
    headers = {
        'Content-Disposition': f'attachment; filename="{filename}"'
    }
    return Response(
        content=data,
        media_type="application/octet-stream",
        headers=headers
    )

@router.post("/workflow/import")
async def import_workflow_endpoint(
    file: UploadFile = File(...),
    user: str = Depends(get_current_user)
):
    """导入工作流（从.rfj文件）"""
    # 检查文件扩展名
    if not file.filename.lower().endswith(".rfj"):
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "只支持导入.rfj格式的工作流文件"}
        )
    
    # 读取文件内容
    content = await file.read()
    
    # 导入工作流
    workflow = import_workflow(content)
    
    if not workflow:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "工作流文件无效或已损坏"}
        )
    
    # 记录操作
    log_system_action("info", f"导入工作流", {"workflow_name": workflow.get("name"), "workflow_id": workflow.get("id")})
    
    return JSONResponse(
        content={"success": True, "message": "工作流导入成功", "workflow": workflow}
    )

@router.post("/python-converter/convert")
async def convert_python_script(request: Request, user: str = Depends(get_current_user)):
    """转换Python脚本为工作流"""
    try:
        data = await request.json()
        code = data.get("code", "")
        workflow_name = data.get("name", "Python脚本转换")
        
        if not code:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "请提供Python代码"}
            )
        
        # 解析Python代码
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False, 
                    "message": "Python代码语法错误", 
                    "details": f"第{e.lineno}行: {e.msg}"
                }
            )
        
        # 初始化工作流数据结构
        workflow = {
            "id": str(uuid.uuid4()),
            "name": workflow_name,
            "description": "由Python脚本转换生成的工作流",
            "modules": [],
            "connections": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "enabled": False,
            "cron": None
        }
        
        # 记录已识别的模块
        recognized_modules = []
        warnings = []
        
        # 创建模块ID计数器和存储
        module_count = 0
        module_ids = []
        module_nodes = {}  # 存储节点对应的模块ID
        module_types = {}  # 存储模块ID对应的类型
        module_names = {}  # 存储模块ID对应的名称
        module_orders = {}  # 存储模块ID对应的顺序
        child_modules = {}  # 记录条件模块的子模块
        
        # 坐标系统
        x_base = 100
        y_base = 100
        y_increment = 100
        
        # 变量命名规则检测
        var_pattern = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
        
        # 识别requests导入
        has_requests_import = False
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    if name.name == 'requests':
                        has_requests_import = True
                        break
            elif isinstance(node, ast.ImportFrom):
                if node.module == 'requests':
                    has_requests_import = True
                    break
        
        if not has_requests_import:
            warnings.append("未检测到requests库导入语句，但尝试创建HTTP请求模块")
        
        # 第一遍：创建所有模块
        for node in ast.iter_child_nodes(tree):
            # 跳过导入语句
            if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                continue
                
            module_count += 1
            
            # 处理变量赋值
            if isinstance(node, ast.Assign):
                if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                    var_name = node.targets[0].id
                    
                    # 检查是否是有效的变量名
                    if not var_pattern.match(var_name):
                        warnings.append(f"变量名'{var_name}'不符合命名规则，已自动调整")
                        var_name = re.sub(r'[^a-zA-Z0-9_]', '_', var_name)
                    
                    # 创建设置变量模块
                    module_id = f"module_{int(datetime.now().timestamp()*1000)}_{module_count}"
                    module_ids.append(module_id)
                    module_nodes[node] = module_id
                    module_types[module_id] = "set_variable"
                    module_names[module_id] = "设置变量"
                    module_orders[module_id] = module_count
                    
                    # 特殊处理: 检测requests.get/post等调用并创建HTTP请求模块
                    is_http_request = False
                    request_method = ""
                    request_url = ""
                    request_json = None
                    request_params = None
                    request_headers = None
                    request_proxies = None
                    
                    if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute):
                        if (isinstance(node.value.func.value, ast.Name) and 
                            node.value.func.value.id == 'requests' and 
                            node.value.func.attr in ['get', 'post', 'put', 'delete']):
                            
                            is_http_request = True
                            request_method = node.value.func.attr.upper()
                            
                            # 提取URL参数
                            if node.value.args:
                                if hasattr(ast, 'unparse'):
                                    request_url = ast.unparse(node.value.args[0])
                                else:
                                    request_url = "请求URL"
                            
                            # 提取关键字参数
                            for keyword in node.value.keywords:
                                if keyword.arg == 'json':
                                    if hasattr(ast, 'unparse'):
                                        request_json = ast.unparse(keyword.value)
                                elif keyword.arg == 'params':
                                    if hasattr(ast, 'unparse'):
                                        request_params = ast.unparse(keyword.value)
                                elif keyword.arg == 'headers':
                                    if hasattr(ast, 'unparse'):
                                        request_headers = ast.unparse(keyword.value)
                                elif keyword.arg == 'proxies':
                                    # 存储代理配置，稍后创建系统代理模块
                                    if hasattr(ast, 'unparse'):
                                        request_proxies = ast.unparse(keyword.value)
                    
                    if is_http_request:
                        # 创建HTTP请求模块而不是变量赋值模块
                        module_types[module_id] = "http_request"
                        module_names[module_id] = "HTTP请求"
                        
                        # 添加HTTP请求模块
                        workflow["modules"].append({
                            "id": module_id,
                            "type": "http_request",
                            "name": "HTTP请求",
                            "config": {
                                "method": request_method,
                                "url": request_url,
                                "headers": {},
                                "body": request_json if request_json else "",
                                "response_var": var_name
                            },
                            "position": {
                                "x": x_base,
                                "y": y_base + (module_count - 1) * y_increment
                            },
                            "order": module_count
                        })
                        
                        recognized_modules.append(f"HTTP请求: {request_method} {request_url}")
                    else:
                        # 分析赋值的值
                        value = ""
                        if isinstance(node.value, ast.Constant):
                            value = str(node.value.value)
                        elif isinstance(node.value, ast.Name):
                            value = f"[{node.value.id}]"  # 引用其他变量
                        elif isinstance(node.value, ast.Call) and hasattr(node.value.func, 'id') and node.value.func.id == 'input':
                            value = "[user_input]"  # 标记为用户输入
                        elif isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute):
                            # 处理方法调用，如response.json()
                            if node.value.func.attr == 'json' and isinstance(node.value.func.value, ast.Name):
                                value = f"[{node.value.func.value.id}]"  # 例如：[response]
                                
                                # 添加模块
                                workflow["modules"].append({
                                    "id": module_id,
                                    "type": "json_parser",
                                    "name": "解析JSON",
                                    "config": {
                                        "input": value,
                                        "output_var": var_name
                                    },
                                    "position": {
                                        "x": x_base,
                                        "y": y_base + (module_count - 1) * y_increment
                                    },
                                    "order": module_count
                                })
                                
                                module_types[module_id] = "json_parser"
                                module_names[module_id] = "解析JSON"
                                recognized_modules.append(f"JSON解析: {var_name} = {value}.json()")
                                continue
                            else:
                                value = "[expression_result]"  # 其他方法调用
                        else:
                            value = "[expression_result]"  # 复杂表达式
                        
                        # 添加标准的变量赋值模块
                        workflow["modules"].append({
                            "id": module_id,
                            "type": "set_variable",
                            "name": "设置变量",
                            "config": {
                                "name": var_name,
                                "value": value
                            },
                            "position": {
                                "x": x_base,
                                "y": y_base + (module_count - 1) * y_increment
                            },
                            "order": module_count
                        })
                        
                        recognized_modules.append(f"变量赋值: {var_name} = {value}")
                
            # 处理条件语句
            elif isinstance(node, ast.If):
                # 创建条件判断模块
                condition_id = f"module_{int(datetime.now().timestamp()*1000)}_{module_count}"
                module_ids.append(condition_id)
                module_nodes[node] = condition_id
                module_types[condition_id] = "condition"
                module_names[condition_id] = "条件判断"
                module_orders[condition_id] = module_count
                
                # 记录条件模块开始
                condition_start_idx = len(module_ids) - 1
                
                # 尝试解析条件表达式
                condition_text = "条件表达式"
                condition_config = {
                    "input": "[condition_input]",
                    "condition": "等于",
                    "compare_value": "true",
                    "true_branch": "if_true",
                    "false_branch": "if_false"
                }
                
                # 特殊处理HTTP响应状态码检查
                if isinstance(node.test, ast.Compare) and isinstance(node.test.left, ast.Attribute):
                    if (node.test.left.attr == 'status_code' and 
                        isinstance(node.test.left.value, ast.Name) and 
                        len(node.test.ops) == 1 and len(node.test.comparators) == 1):
                        
                        response_var = node.test.left.value.id
                        op = node.test.ops[0]
                        status_code = node.test.comparators[0].value if isinstance(node.test.comparators[0], ast.Constant) else 200
                        
                        condition_text = f"{response_var}.status_code 检查"
                        
                        # 根据操作符选择条件表达式
                        if isinstance(op, ast.Eq):
                            condition_op = "等于"
                        elif isinstance(op, ast.NotEq):
                            condition_op = "不等于"
                        elif isinstance(op, ast.Lt):
                            condition_op = "小于"
                        elif isinstance(op, ast.LtE):
                            condition_op = "小于等于"
                        elif isinstance(op, ast.Gt):
                            condition_op = "大于"
                        elif isinstance(op, ast.GtE):
                            condition_op = "大于等于"
                        else:
                            condition_op = "等于"
                        
                        condition_config = {
                            "input": f"[{response_var}.status_code]",
                            "condition": condition_op,
                            "compare_value": str(status_code),
                            "true_branch": "if_true",
                            "false_branch": "if_false"
                        }
                elif isinstance(node.test, ast.Compare):
                    if len(node.test.ops) == 1 and len(node.test.comparators) == 1:
                        left = ast.unparse(node.test.left) if hasattr(ast, 'unparse') else "左值"
                        right = ast.unparse(node.test.comparators[0]) if hasattr(ast, 'unparse') else "右值"
                        op_map = {
                            ast.Eq: "等于",
                            ast.NotEq: "不等于",
                            ast.Lt: "小于",
                            ast.LtE: "小于等于",
                            ast.Gt: "大于",
                            ast.GtE: "大于等于",
                            ast.In: "包含",
                            ast.NotIn: "不包含"
                        }
                        op = op_map.get(type(node.test.ops[0]), "比较")
                        condition_text = f"{left} {op} {right}"
                
                # 添加条件模块
                workflow["modules"].append({
                    "id": condition_id,
                    "type": "condition",
                    "name": "条件判断",
                    "config": condition_config,
                    "position": {
                        "x": x_base,
                        "y": y_base + (module_count - 1) * y_increment
                    },
                    "order": module_count
                })
                
                recognized_modules.append(f"条件判断: {condition_text}")
                
                # 添加结束条件判断模块
                module_count += 1
                end_condition_id = f"module_{int(datetime.now().timestamp()*1000)}_{module_count}"
                module_ids.append(end_condition_id)
                module_types[end_condition_id] = "condition_end"
                module_names[end_condition_id] = "结束条件判断"
                module_orders[end_condition_id] = module_count
                
                # 记录条件模块结束
                condition_end_idx = len(module_ids) - 1
                
                # 将条件开始和结束模块关联起来
                child_modules[condition_start_idx] = condition_end_idx
                
                workflow["modules"].append({
                    "id": end_condition_id,
                    "type": "condition_end",
                    "name": "结束条件判断",
                    "config": {},
                    "position": {
                        "x": x_base,
                        "y": y_base + (module_count - 1) * y_increment + 150
                    },
                    "order": module_count
                })
                
                recognized_modules.append("结束条件判断")
            
            # 处理循环
            elif isinstance(node, ast.For):
                # 创建重复操作模块
                module_id = f"module_{int(datetime.now().timestamp()*1000)}_{module_count}"
                module_ids.append(module_id)
                module_nodes[node] = module_id
                module_types[module_id] = "repeat"
                module_names[module_id] = "重复操作"
                module_orders[module_id] = module_count
                
                # 获取循环变量名
                if isinstance(node.target, ast.Name):
                    loop_var = node.target.id
                else:
                    loop_var = "循环变量"
                
                # 获取迭代对象
                if hasattr(ast, 'unparse'):
                    iter_obj = ast.unparse(node.iter)
                else:
                    iter_obj = "迭代对象"
                
                # 添加循环处理模块
                workflow["modules"].append({
                    "id": module_id,
                    "type": "repeat",
                    "name": "重复操作",
                    "config": {
                        "times": 5,  # 默认循环次数
                        "interval": 0,
                        "iterVar": loop_var,
                        "iterObj": iter_obj if "." not in iter_obj else f"[{iter_obj}]"
                    },
                    "position": {
                        "x": x_base,
                        "y": y_base + (module_count - 1) * y_increment
                    },
                    "order": module_count
                })
                
                recognized_modules.append(f"循环: for {loop_var} in {iter_obj}")
            
            # 处理函数调用
            elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                call_node = node.value
                
                # 处理print函数
                if isinstance(call_node.func, ast.Name) and call_node.func.id == 'print':
                    # 创建通知模块
                    module_id = f"module_{int(datetime.now().timestamp()*1000)}_{module_count}"
                    module_ids.append(module_id)
                    module_nodes[node] = module_id
                    module_types[module_id] = "notification"
                    module_names[module_id] = "通知服务"
                    module_orders[module_id] = module_count
                    
                    # 提取打印内容
                    message = ""
                    if call_node.args:
                        if hasattr(ast, 'unparse'):
                            message = ast.unparse(call_node.args[0])
                        else:
                            message = "打印内容"
                    
                    # 添加通知模块
                    workflow["modules"].append({
                        "id": module_id,
                        "type": "notification",
                        "name": "通知服务",
                        "config": {
                            "type": "email",
                            "title": "脚本通知",
                            "content": message,
                            "to": ""
                        },
                        "position": {
                            "x": x_base,
                            "y": y_base + (module_count - 1) * y_increment
                        },
                        "order": module_count
                    })
                    
                    recognized_modules.append(f"通知: {message}")
                
                # 处理time.sleep()函数 - 转换为间隔时间模块
                elif (isinstance(call_node.func, ast.Attribute) and 
                      isinstance(call_node.func.value, ast.Name) and 
                      call_node.func.value.id == 'time' and 
                      call_node.func.attr == 'sleep'):
                    
                    # 创建间隔时间模块
                    module_id = f"module_{int(datetime.now().timestamp()*1000)}_{module_count}"
                    module_ids.append(module_id)
                    module_nodes[node] = module_id
                    module_types[module_id] = "delay"
                    module_names[module_id] = "间隔时间"
                    module_orders[module_id] = module_count
                    
                    # 提取等待秒数
                    seconds = 5  # 默认等待5秒
                    if call_node.args and len(call_node.args) > 0:
                        if isinstance(call_node.args[0], ast.Num):
                            seconds = call_node.args[0].n
                        elif hasattr(ast, 'unparse'):
                            seconds_expr = ast.unparse(call_node.args[0])
                            if seconds_expr.isdigit():
                                seconds = int(seconds_expr)
                    
                    # 添加间隔时间模块
                    workflow["modules"].append({
                        "id": module_id,
                        "type": "delay",
                        "name": "间隔时间",
                        "config": {
                            "seconds": seconds
                        },
                        "position": {
                            "x": x_base,
                            "y": y_base + (module_count - 1) * y_increment
                        },
                        "order": module_count
                    })
                    
                    recognized_modules.append(f"间隔时间: {seconds}秒")
                
                # 特殊处理: 检测requests.get/post等调用并创建HTTP请求模块
                is_http_request = False
                request_method = ""
                request_url = ""
                request_json = None
                request_params = None
                request_headers = None
                request_proxies = None
                
                if isinstance(node.value, ast.Call):
                    call_node = node.value
                    
                    # 判断是否是requests.方法()调用
                    if (isinstance(call_node.func, ast.Attribute) and 
                        isinstance(call_node.func.value, ast.Name) and 
                        call_node.func.value.id == 'requests'):
                        
                        if call_node.func.attr in ['get', 'post', 'put', 'delete']:
                            is_http_request = True
                            request_method = call_node.func.attr.upper()
                            
                            # 提取URL参数
                            if call_node.args and len(call_node.args) > 0:
                                if isinstance(call_node.args[0], ast.Str):
                                    request_url = call_node.args[0].s
                                elif hasattr(ast, 'unparse'):
                                    request_url = ast.unparse(call_node.args[0])
                            
                            # 提取关键字参数
                            for keyword in call_node.keywords:
                                if keyword.arg == 'json':
                                    if hasattr(ast, 'unparse'):
                                        request_json = ast.unparse(keyword.value)
                                elif keyword.arg == 'params':
                                    if hasattr(ast, 'unparse'):
                                        request_params = ast.unparse(keyword.value)
                                elif keyword.arg == 'headers':
                                    if hasattr(ast, 'unparse'):
                                        request_headers = ast.unparse(keyword.value)
                                elif keyword.arg == 'proxies':
                                    # 存储代理配置，稍后创建系统代理模块
                                    if hasattr(ast, 'unparse'):
                                        request_proxies = ast.unparse(keyword.value)
                
                # 如果存在代理设置，创建系统代理模块
                if request_proxies:
                    # 首先创建代理模块
                    proxy_module_id = f"module_{int(datetime.now().timestamp()*1000)}_{module_count}"
                    module_count += 1  # 增加计数器
                    module_ids.append(proxy_module_id)
                    module_types[proxy_module_id] = "system_proxy"
                    module_names[proxy_module_id] = "系统代理"
                    module_orders[proxy_module_id] = module_count - 1
                    
                    # 提取代理URL
                    proxy_url = "http://proxy.example.com:8080"  # 默认值
                    if isinstance(request_proxies, str) and "http" in request_proxies:
                        # 尝试从字符串中提取代理URL
                        pattern = r"['\"]https?://[^'\"]+['\"]"
                        match = re.search(pattern, request_proxies)
                        if match:
                            proxy_url = match.group(0).strip("'\"")
                    
                    # 添加系统代理模块
                    workflow["modules"].append({
                        "id": proxy_module_id,
                        "type": "system_proxy",
                        "name": "系统代理",
                        "config": {
                            "proxy_url": proxy_url,
                            "scope": "全局",
                            "reset": False
                        },
                        "position": {
                            "x": x_base,
                            "y": y_base + (module_count - 2) * y_increment
                        },
                        "order": module_count - 1
                    })
                    
                    recognized_modules.append(f"系统代理: {proxy_url}")
                    
                    # 添加连接：代理模块到HTTP请求模块的连接
                    if module_id and is_http_request:
                        workflow["connections"].append({
                            "id": f"connection_{uuid.uuid4()}",
                            "source": proxy_module_id,
                            "target": module_id
                        })

                # 检测时间戳相关操作
                if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                    call_node = node.value
                    
                    # 处理datetime.now()、datetime.datetime.now()调用
                    is_timestamp_now = False
                    if isinstance(call_node.func, ast.Attribute) and call_node.func.attr == 'now':
                        if isinstance(call_node.func.value, ast.Name) and call_node.func.value.id in ['datetime']:
                            is_timestamp_now = True
                        elif (isinstance(call_node.func.value, ast.Attribute) and 
                              isinstance(call_node.func.value.value, ast.Name) and 
                              call_node.func.value.value.id == 'datetime' and 
                              call_node.func.value.attr == 'datetime'):
                            is_timestamp_now = True
                    
                    # 处理time.time()调用
                    is_time_time = False
                    if (isinstance(call_node.func, ast.Attribute) and 
                        isinstance(call_node.func.value, ast.Name) and 
                        call_node.func.value.id == 'time' and 
                        call_node.func.attr == 'time'):
                        is_time_time = True
                    
                    # 处理datetime.strptime()调用 - 时间字符串转时间戳
                    is_strptime = False
                    if (isinstance(call_node.func, ast.Attribute) and 
                        call_node.func.attr == 'strptime' and 
                        isinstance(call_node.func.value, ast.Attribute) and 
                        isinstance(call_node.func.value.value, ast.Name) and 
                        call_node.func.value.value.id == 'datetime' and 
                        call_node.func.value.attr == 'datetime'):
                        is_strptime = True
                    
                    # 处理所有时间戳相关操作
                    if is_timestamp_now or is_time_time or is_strptime:
                        # 获取输出变量名
                        var_name = ""
                        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                            var_name = node.targets[0].id
                        
                        # 创建时间戳模块
                        module_id = f"module_{int(datetime.now().timestamp()*1000)}_{module_count}"
                        module_ids.append(module_id)
                        module_nodes[node] = module_id
                        module_types[module_id] = "timestamp"
                        module_names[module_id] = "时间戳"
                        module_orders[module_id] = module_count
                        
                        if is_timestamp_now:
                            # 处理获取当前时间
                            workflow["modules"].append({
                                "id": module_id,
                                "type": "timestamp",
                                "name": "时间戳",
                                "config": {
                                    "action": "获取当前时间",
                                    "format": "格式化时间",
                                    "datetime_format": "%Y-%m-%d %H:%M:%S",
                                    "output_var": var_name
                                },
                                "position": {
                                    "x": x_base,
                                    "y": y_base + (module_count - 1) * y_increment
                                },
                                "order": module_count
                            })
                            recognized_modules.append(f"时间戳: 获取当前时间 -> {var_name}")
                        
                        elif is_time_time:
                            # 处理time.time()获取当前时间戳
                            workflow["modules"].append({
                                "id": module_id,
                                "type": "timestamp",
                                "name": "时间戳",
                                "config": {
                                    "action": "获取当前时间",
                                    "format": "时间戳(秒)",
                                    "output_var": var_name
                                },
                                "position": {
                                    "x": x_base,
                                    "y": y_base + (module_count - 1) * y_increment
                                },
                                "order": module_count
                            })
                            recognized_modules.append(f"时间戳: 获取当前时间戳 -> {var_name}")
                        
                        elif is_strptime and len(call_node.args) >= 2:
                            # 处理时间字符串转换
                            time_str = ""
                            time_format = "%Y-%m-%d %H:%M:%S"  # 默认格式
                            
                            if hasattr(ast, 'unparse'):
                                if len(call_node.args) > 0:
                                    time_str = ast.unparse(call_node.args[0])
                                if len(call_node.args) > 1 and isinstance(call_node.args[1], ast.Str):
                                    time_format = call_node.args[1].s
                            
                            workflow["modules"].append({
                                "id": module_id,
                                "type": "timestamp",
                                "name": "时间戳",
                                "config": {
                                    "action": "转换时间字符串",
                                    "format": "时间戳(秒)",
                                    "input_time": time_str,
                                    "input_format": time_format,
                                    "output_var": var_name
                                },
                                "position": {
                                    "x": x_base,
                                    "y": y_base + (module_count - 1) * y_increment
                                },
                                "order": module_count
                            })
                            recognized_modules.append(f"时间戳: 转换时间字符串 {time_str} -> {var_name}")
        
        # 如果没有识别到任何模块，返回错误
        if not workflow["modules"]:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False, 
                    "message": "脚本转换失败：未能识别任何支持的模块", 
                    "details": "请检查代码是否包含变量赋值、条件判断、循环或HTTP请求等支持的操作。"
                }
            )
        
        # 第二遍：创建模块之间的连接关系
        for i in range(len(module_ids) - 1):
            # 获取当前模块和下一个模块的ID
            current_id = module_ids[i]
            next_id = module_ids[i + 1]
            
            # 设置连接的详细信息
            source_type = module_types.get(current_id, "")
            source_name = module_names.get(current_id, "")
            source_order = module_orders.get(current_id, 0)
            target_type = module_types.get(next_id, "")
            target_name = module_names.get(next_id, "")
            target_order = module_orders.get(next_id, 0)
            
            # 如果当前索引是条件模块的结束索引，跳过这个连接
            if any(end_idx == i for end_idx in child_modules.values()):
                continue
            
            # 如果当前索引是条件模块的开始，连接到结束模块
            if i in child_modules:
                # 为条件模块添加"true"连接（当前模块 -> 下一个模块）
                workflow["connections"].append({
                    "id": f"conn_{int(datetime.now().timestamp()*1000)}_{i}_true",
                    "source": current_id,
                    "target": next_id,
                    "sourceHandle": "output_true",
                    "targetHandle": "input",
                    "type": "condition_true",
                    "sourceType": source_type,
                    "sourceName": source_name,
                    "sourceOrder": source_order,
                    "targetType": target_type,
                    "targetName": target_name,
                    "targetOrder": target_order
                })
                
                # 为条件模块添加"false"连接（当前模块 -> 结束条件模块）
                end_module_id = module_ids[child_modules[i]]
                end_type = module_types.get(end_module_id, "")
                end_name = module_names.get(end_module_id, "")
                end_order = module_orders.get(end_module_id, 0)
                
                workflow["connections"].append({
                    "id": f"conn_{int(datetime.now().timestamp()*1000)}_{i}_false",
                    "source": current_id,
                    "target": end_module_id,
                    "sourceHandle": "output_false",
                    "targetHandle": "input",
                    "type": "condition_false",
                    "sourceType": source_type,
                    "sourceName": source_name,
                    "sourceOrder": source_order,
                    "targetType": end_type,
                    "targetName": end_name,
                    "targetOrder": end_order
                })
                
                # 继续正常的流程
                if child_modules[i] < len(module_ids) - 1:
                    next_after_end = module_ids[child_modules[i] + 1]
                    next_type = module_types.get(next_after_end, "")
                    next_name = module_names.get(next_after_end, "")
                    next_order = module_orders.get(next_after_end, 0)
                    
                    workflow["connections"].append({
                        "id": f"conn_{int(datetime.now().timestamp()*1000)}_{child_modules[i]}",
                        "source": end_module_id,
                        "target": next_after_end,
                        "sourceHandle": "output",
                        "targetHandle": "input",
                        "sourceType": end_type,
                        "sourceName": end_name,
                        "sourceOrder": end_order,
                        "targetType": next_type,
                        "targetName": next_name,
                        "targetOrder": next_order
                    })
            else:
                # 普通模块连接
                workflow["connections"].append({
                    "id": f"conn_{int(datetime.now().timestamp()*1000)}_{i}",
                    "source": current_id,
                    "target": next_id,
                    "sourceHandle": "output",
                    "targetHandle": "input",
                    "sourceType": source_type,
                    "sourceName": source_name,
                    "sourceOrder": source_order,
                    "targetType": target_type,
                    "targetName": target_name,
                    "targetOrder": target_order
                })
        
        # 返回转换结果
        return JSONResponse(
            content={
                "success": True,
                "message": "脚本转换成功",
                "workflow": workflow,
                "modules_count": len(workflow["modules"]),
                "recognized_modules": recognized_modules,
                "warnings": warnings
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False, 
                "message": "脚本转换过程中发生错误", 
                "details": str(e)
            }
        )

@router.post("/python-converter/create-workflow")
async def create_workflow_from_python(request: Request, user: str = Depends(get_current_user)):
    """从Python脚本转换结果创建工作流"""
    try:
        data = await request.json()
        workflow_data = data.get("workflow", {})
        
        if not workflow_data:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "请提供工作流数据"}
            )
        
        # 生成工作流ID（如果未提供）
        if not workflow_data.get("id"):
            workflow_data["id"] = str(uuid.uuid4())
        
        # 设置创建时间和更新时间
        now = datetime.now().isoformat()
        workflow_data["created_at"] = now
        workflow_data["updated_at"] = now
        
        # 设置默认值
        workflow_data["enabled"] = workflow_data.get("enabled", False)
        workflow_data["cron"] = workflow_data.get("cron", None)
        
        # 保存工作流
        save_workflow(workflow_data)
        
        # 记录操作日志
        log_system_action("info", f"从Python脚本创建了工作流: {workflow_data.get('name')}")
        
        return JSONResponse(
            content={
                "success": True,
                "message": "工作流创建成功",
                "workflow_id": workflow_data["id"]
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"创建工作流失败: {str(e)}"}
        )

@router.post("/workflow/{workflow_id}/alert-settings")
async def update_alert_settings(
    workflow_id: str, 
    request: Request, 
    user: str = Depends(get_current_user)
):
    """更新工作流预警设置"""
    data = await request.json()
    retry_count = data.get("retry_count", 0)
    retry_interval = data.get("retry_interval", 5)
    
    workflow = get_workflow_by_id(workflow_id)
    if not workflow:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"success": False, "message": "工作流不存在"}
        )
    
    # 更新工作流预警设置
    workflow["retry_count"] = retry_count
    workflow["retry_interval"] = retry_interval
    
    # 保存工作流
    updated_workflow = save_workflow(workflow)
    
    # 记录日志
    log_system_action(
        "info", 
        f"更新工作流预警设置: {workflow.get('name')}", 
        {"workflow_id": workflow_id, "retry_count": retry_count, "retry_interval": retry_interval}
    )
    
    return JSONResponse(
        content={"success": True, "message": "预警设置保存成功", "workflow": updated_workflow}
    ) 