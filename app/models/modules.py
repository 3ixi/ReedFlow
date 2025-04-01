from typing import Dict, List, Any, Optional, Tuple, Union, Callable
import logging
import hashlib
import base64
import json
import re
import time
import urllib.parse
import http.client
import socket
import ssl
import random
import string
import datetime
import asyncio
from datetime import timedelta
try:
    import httpx
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
    import smtplib
    from email.mime.text import MIMEText
    from email.header import Header
except ImportError:
    # 如果缺少某些库，可能会导致某些模块无法使用
    pass

# 导入工具模块
from app.utils.config import get_config, get_variable, set_variable, get_variables, update_variables, get_account_info, get_account_config, update_account_config, update_account_field
from app.models.log import log_workflow_action
from app.utils.notification import send_notification
from app.models.module_types import MODULE_TYPES, get_all_module_types

# 设置日志
logger = logging.getLogger("modules")

# 变量替换正则表达式
VAR_PATTERN = r'\[(.*?)\]'

# 模块类型定义已移至module_types.py

# 变量替换函数
def replace_variables(text: str, variables: Dict[str, Any]) -> str:
    """替换文本中的变量引用"""
    if not text:
        return text
        
    def replace_var(match):
        var_name = match.group(1).strip()
        return str(variables.get(var_name, f"${{未找到变量: {var_name}}}"))
    
    return re.sub(VAR_PATTERN, replace_var, text)

# 获取JSON路径中的值
def get_value_from_json_path(json_data: Dict[str, Any], path: str) -> Any:
    """从JSON对象中提取指定路径的值"""
    if not path:
        return json_data
        
    parts = re.split(r'\.(?![^\[]*\])', path)
    current = json_data
    
    for part in parts:
        match = re.match(r'([^\[]+)(?:\[(\d+)\])?', part)
        if not match:
            return None
            
        key, index = match.groups()
        
        if key not in current:
            return None
            
        current = current[key]
        
        if index is not None:
            try:
                current = current[int(index)]
            except (IndexError, TypeError):
                return None
                
    return current

# 模块执行函数
async def execute_module(module: Dict[str, Any], variables: Dict[str, Any], workflow_id: str = None) -> Dict[str, Any]:
    """执行单个模块"""
    module_type = module.get("type")
    module_name = module.get("name", "未命名模块")
    config = module.get("config", {})
    result = {"success": True, "output": None, "error": None}
    
    try:
        if module_type == "md5":
            input_text = replace_variables(config.get("input", ""), variables)
            # 记录输入参数
            if workflow_id:
                log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' 输入: {input_text}", {"module_type": module_type})
            
            md5_hash = hashlib.md5(input_text.encode()).hexdigest()
            result["output"] = md5_hash
            
            # 记录输出结果
            if workflow_id:
                log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' 输出: {md5_hash}", {"module_type": module_type})
            
            if config.get("output_var"):
                variables[config["output_var"]] = md5_hash
                
        elif module_type == "base64_encode":
            input_text = replace_variables(config.get("input", ""), variables)
            # 记录输入参数
            if workflow_id:
                log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' 输入: {input_text}", {"module_type": module_type})
            
            encoded = base64.b64encode(input_text.encode()).decode()
            result["output"] = encoded
            
            # 记录输出结果
            if workflow_id:
                log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' 输出: {encoded}", {"module_type": module_type})
            
            if config.get("output_var"):
                variables[config["output_var"]] = encoded
                
        elif module_type == "base64_decode":
            input_text = replace_variables(config.get("input", ""), variables)
            # 记录输入参数
            if workflow_id:
                log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' 输入: {input_text}", {"module_type": module_type})
            
            try:
                decoded = base64.b64decode(input_text).decode()
                result["output"] = decoded
                
                # 记录输出结果
                if workflow_id:
                    log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' 输出: {decoded}", {"module_type": module_type})
                
                if config.get("output_var"):
                    variables[config["output_var"]] = decoded
            except Exception as e:
                result["success"] = False
                result["error"] = f"Base64解码失败: {str(e)}"
                if workflow_id:
                    log_workflow_action(workflow_id, "error", f"模块 '{module_name}' Base64解码失败: {str(e)}", {"module_type": module_type})
                
        elif module_type == "text_replace":
            input_text = replace_variables(config.get("input", ""), variables)
            search_text = replace_variables(config.get("search", ""), variables)
            replace_text = replace_variables(config.get("replace", ""), variables)
            
            # 记录输入参数
            if workflow_id:
                log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' 替换操作", {
                    "module_type": module_type,
                    "input": input_text,
                    "search": search_text,
                    "replace": replace_text
                })
            
            replaced = input_text.replace(search_text, replace_text)
            result["output"] = replaced
            
            # 记录输出结果
            if workflow_id:
                log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' 替换结果: {replaced}", {"module_type": module_type})
            
            if config.get("output_var"):
                variables[config["output_var"]] = replaced
                
        elif module_type == "url_encode":
            input_text = replace_variables(config.get("input", ""), variables)
            # 记录输入参数
            if workflow_id:
                log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' 输入: {input_text}", {"module_type": module_type})
            
            encoded = urllib.parse.quote(input_text)
            result["output"] = encoded
            
            # 记录输出结果
            if workflow_id:
                log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' 输出: {encoded}", {"module_type": module_type})
            
            if config.get("output_var"):
                variables[config["output_var"]] = encoded
                
        elif module_type == "url_decode":
            input_text = replace_variables(config.get("input", ""), variables)
            # 记录输入参数
            if workflow_id:
                log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' 输入: {input_text}", {"module_type": module_type})
            
            try:
                decoded = urllib.parse.unquote(input_text)
                result["output"] = decoded
                
                # 记录输出结果
                if workflow_id:
                    log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' 输出: {decoded}", {"module_type": module_type})
                
                if config.get("output_var"):
                    variables[config["output_var"]] = decoded
            except Exception as e:
                result["success"] = False
                result["error"] = f"URL解码失败: {str(e)}"
                if workflow_id:
                    log_workflow_action(workflow_id, "error", f"模块 '{module_name}' URL解码失败: {str(e)}", {"module_type": module_type})
                
        elif module_type == "http_request":
            url = replace_variables(config.get("url", ""), variables)
            method = config.get("method", "GET").upper()
            
            # 处理请求头
            headers_str = config.get("headers", "{}")
            headers_str = replace_variables(headers_str, variables)
            try:
                headers = json.loads(headers_str) if headers_str else {}
            except:
                headers = {}
                
            # 处理请求体
            body = replace_variables(config.get("body", ""), variables)
            
            # 获取代理设置 - 先检查当前分支代理，再检查全局代理
            current_branch = variables.get("_current_branch", "default")
            branch_proxy = variables.get(f"_branch_proxy_{current_branch}")
            global_proxy = variables.get("_global_proxy")
            proxy = branch_proxy or global_proxy
            
            # 获取是否使用HTTP/2和检查状态码配置
            use_http2 = config.get("use_http2", False)
            check_status = config.get("check_status", False)
            timeout = int(config.get("timeout", 30))
            
            # 记录请求信息
            if workflow_id:
                log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' HTTP请求", {
                    "module_type": module_type,
                    "url": url,
                    "method": method,
                    "headers": headers,
                    "body": body,
                    "proxy": proxy,
                    "use_http2": use_http2,
                    "check_status": check_status,
                    "timeout": timeout
                })
            
            # 发送请求
            try:
                async with httpx.AsyncClient(http2=use_http2, proxies=proxy, timeout=timeout) as client:
                    if method == "GET":
                        response = await client.get(url, headers=headers)
                    elif method == "POST":
                        response = await client.post(url, headers=headers, content=body)
                    elif method == "PUT":
                        response = await client.put(url, headers=headers, content=body)
                    elif method == "DELETE":
                        response = await client.delete(url, headers=headers)
                    else:
                        response = await client.request(method, url, headers=headers, content=body)
                    
                    # 检查状态码
                    if check_status and (response.status_code < 200 or response.status_code >= 300):
                        result["success"] = False
                        result["error"] = f"HTTP请求失败: 状态码 {response.status_code}"
                        if workflow_id:
                            log_workflow_action(workflow_id, "error", f"模块 '{module_name}' HTTP请求失败: 状态码 {response.status_code}", {"module_type": module_type})
                        
                        # 如果设置了状态码变量名，仍然保存状态码
                        if config.get("status_code_var"):
                            variables[config["status_code_var"]] = response.status_code
                        
                        return result
                    
                    response_text = response.text
                    result["output"] = response_text
                    
                    # 记录响应信息
                    if workflow_id:
                        # 获取响应头信息，转换为字典形式
                        response_headers = dict(response.headers)
                        log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' HTTP响应 {response.status_code}", {
                            "module_type": module_type,
                            "status_code": response.status_code,
                            "headers": response_headers,
                            "response_text": response_text[:1000] + ("..." if len(response_text) > 1000 else "")  # 限制长度
                        })
                    
                    if config.get("output_var"):
                        variables[config["output_var"]] = response_text
                        
                    # 如果设置了状态码变量名，保存状态码
                    if config.get("status_code_var"):
                        variables[config["status_code_var"]] = response.status_code
            
            except httpx.RequestError as e:
                result["success"] = False
                result["error"] = f"HTTP请求错误: {str(e)}"
                if workflow_id:
                    log_workflow_action(workflow_id, "error", f"模块 '{module_name}' HTTP请求错误: {str(e)}", {"module_type": module_type})
                
                # 如果设置了状态码变量名，设置为0表示连接错误
                if config.get("status_code_var"):
                    variables[config["status_code_var"]] = 0

        elif module_type == "json_parse":
            input_text = replace_variables(config.get("input", ""), variables)
            path = config.get("path", "")
            
            # 记录输入参数
            if workflow_id:
                log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' JSON解析", {
                    "module_type": module_type,
                    "input": input_text[:1000] + ("..." if len(input_text) > 1000 else ""),
                    "path": path
                })
            
            try:
                json_data = json.loads(input_text)
                parsed_value = get_value_from_json_path(json_data, path)
                
                if isinstance(parsed_value, (dict, list)):
                    parsed_value_str = json.dumps(parsed_value, ensure_ascii=False)
                else:
                    parsed_value_str = str(parsed_value)
                    
                result["output"] = parsed_value_str
                
                # 记录解析结果
                if workflow_id:
                    log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' JSON解析结果", {
                        "module_type": module_type,
                        "parsed_value": parsed_value_str[:1000] + ("..." if len(parsed_value_str) > 1000 else "")
                    })
                
                if config.get("output_var") and parsed_value is not None:
                    variables[config["output_var"]] = parsed_value_str
            except Exception as e:
                result["success"] = False
                result["error"] = f"JSON解析失败: {str(e)}"
                if workflow_id:
                    log_workflow_action(workflow_id, "error", f"模块 '{module_name}' JSON解析失败: {str(e)}", {"module_type": module_type})
                
        elif module_type == "set_variable":
            var_name = config.get("name", "")
            var_value = replace_variables(config.get("value", ""), variables)
            
            # 记录设置变量操作
            if workflow_id:
                log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' 设置变量", {
                    "module_type": module_type,
                    "variable_name": var_name,
                    "variable_value": var_value
                })
            
            if var_name:
                variables[var_name] = var_value
                result["output"] = var_value
                
        elif module_type == "text_template":
            template = config.get("template", "")
            
            # 记录模板内容
            if workflow_id:
                log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' 文本模板", {
                    "module_type": module_type,
                    "template": template[:1000] + ("..." if len(template) > 1000 else "")
                })
            
            output = replace_variables(template, variables)
            result["output"] = output
            
            # 记录生成结果
            if workflow_id:
                log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' 文本模板生成结果", {
                    "module_type": module_type,
                    "output": output[:1000] + ("..." if len(output) > 1000 else "")
                })
            
            if config.get("output_var"):
                variables[config["output_var"]] = output
                
        elif module_type == "notification":
            notification_type = config.get("type", "email")
            title = replace_variables(config.get("title", ""), variables)
            content = replace_variables(config.get("content", ""), variables)
            to = replace_variables(config.get("to", ""), variables)
            
            # 记录通知内容
            if workflow_id:
                log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' 发送通知", {
                    "module_type": module_type,
                    "notification_type": notification_type,
                    "title": title,
                    "content": content[:1000] + ("..." if len(content) > 1000 else ""),
                    "to": to
                })
            
            if notification_type == "email":
                # 发送邮件
                system_config = get_config()
                email_config = system_config.get("email", {})
                
                if not email_config.get("smtp_server") or not email_config.get("smtp_user"):
                    result["success"] = False
                    result["error"] = "邮件服务未配置"
                    if workflow_id:
                        log_workflow_action(workflow_id, "error", f"模块 '{module_name}' 邮件服务未配置", {"module_type": module_type})
                else:
                    try:
                        # 如果未设置收件人，则使用默认收件人
                        if not to:
                            to = email_config.get("default_recipient", "")
                            if not to:
                                result["success"] = False
                                result["error"] = "未设置收件人地址且未配置默认收件人"
                                if workflow_id:
                                    log_workflow_action(workflow_id, "error", f"模块 '{module_name}' 未设置收件人地址且未配置默认收件人", {"module_type": module_type})
                                return result
                        
                        msg = MIMEText(content, 'plain', 'utf-8')
                        msg['Subject'] = Header(title, 'utf-8')
                        msg['From'] = email_config.get("sender") or email_config.get("smtp_user")
                        msg['To'] = to
                        
                        smtp_server = email_config.get("smtp_server")
                        smtp_port = email_config.get("smtp_port", 465)
                        smtp_user = email_config.get("smtp_user")
                        smtp_password = email_config.get("smtp_password")
                        
                        # 记录将要使用的收件人地址
                        if workflow_id:
                            log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' 准备发送邮件", {
                                "module_type": module_type,
                                "smtp_server": smtp_server,
                                "smtp_port": smtp_port,
                                "from": msg['From'],
                                "to": to
                            })
                        
                        # 尝试使用SSL连接
                        try:
                            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
                            server.login(smtp_user, smtp_password)
                            server.sendmail(msg['From'], [to], msg.as_string())
                            server.quit()
                            
                            result["output"] = "邮件发送成功"
                            if workflow_id:
                                log_workflow_action(workflow_id, "info", f"模块 '{module_name}' 邮件发送成功", 
                                                  {"module_type": module_type, "protocol": "SSL", "recipient": to})
                        except ssl.SSLError as ssl_err:
                            # SSL连接失败，尝试普通连接并启用TLS
                            logger.warning(f"SSL连接失败: {str(ssl_err)}，尝试非SSL连接")
                            if workflow_id:
                                log_workflow_action(workflow_id, "warning", f"模块 '{module_name}' SSL连接失败，尝试非SSL连接", 
                                                  {"module_type": module_type, "error": str(ssl_err)})
                            
                            server = smtplib.SMTP(smtp_server, smtp_port)
                            server.ehlo()
                            if server.has_extn('STARTTLS'):
                                server.starttls()
                                server.ehlo()
                            server.login(smtp_user, smtp_password)
                            server.sendmail(msg['From'], [to], msg.as_string())
                            server.quit()
                            
                            result["output"] = "邮件发送成功（非SSL模式）"
                            if workflow_id:
                                log_workflow_action(workflow_id, "info", f"模块 '{module_name}' 邮件发送成功（非SSL模式）", 
                                                  {"module_type": module_type, "protocol": "TLS/Plain"})
                    except Exception as e:
                        result["success"] = False
                        error_msg = str(e)
                        result["error"] = f"邮件发送失败: {error_msg}"
                        
                        # 提供更友好的错误提示
                        if "Authentication" in error_msg:
                            result["error"] += "。请检查账号和密码是否正确（对于QQ邮箱，需要使用授权码而非登录密码）"
                        elif "SSL" in error_msg:
                            result["error"] += "。请确认端口配置正确且支持SSL。QQ邮箱建议使用端口465"
                        elif "Connection" in error_msg:
                            result["error"] += "。请检查服务器地址和端口配置，QQ邮箱推荐端口465(SSL)或587(TLS)"
                        
                        if workflow_id:
                            log_workflow_action(workflow_id, "error", f"模块 '{module_name}' 邮件发送失败: {error_msg}", 
                                              {"module_type": module_type})
                        
            elif notification_type == "wxpusher":
                # 发送微信推送
                system_config = get_config()
                wxpusher_config = system_config.get("wxpusher", {})
                
                if not wxpusher_config.get("app_token"):
                    result["success"] = False
                    result["error"] = "WxPusher服务未配置"
                    if workflow_id:
                        log_workflow_action(workflow_id, "error", f"模块 '{module_name}' WxPusher服务未配置", {"module_type": module_type})
                else:
                    try:
                        # 准备基本请求数据
                        wxpusher_data = {
                            "appToken": wxpusher_config.get("app_token"),
                            "content": content,
                            "summary": title,
                            "contentType": 1,  # 文本类型
                        }
                        
                        # 如果未设置接收人，则使用默认接收人UID
                        if not to:
                            to = wxpusher_config.get("default_uid", "")
                            if not to:
                                result["success"] = False
                                result["error"] = "未设置接收人UID且未配置默认接收人"
                                if workflow_id:
                                    log_workflow_action(workflow_id, "error", f"模块 '{module_name}' 未设置接收人UID且未配置默认接收人", {"module_type": module_type})
                                return result
                        
                        # 设置接收人UID
                        wxpusher_data["uids"] = [to]
                        
                        # 记录将要使用的接收人UID
                        if workflow_id:
                            log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' 准备发送微信推送", {
                                "module_type": module_type,
                                "app_token": wxpusher_config.get("app_token"),
                                "to_uid": to
                            })
                        
                        async with httpx.AsyncClient() as client:
                            response = await client.post(
                                "https://wxpusher.zjiecode.com/api/send/message", 
                                json=wxpusher_data
                            )
                            response_json = response.json()
                            
                            # 记录推送响应
                            if workflow_id:
                                log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' WxPusher响应", {
                                    "module_type": module_type,
                                    "response": response_json
                                })
                            
                            if response_json.get("success"):
                                result["output"] = "微信推送发送成功"
                                if workflow_id:
                                    log_workflow_action(workflow_id, "info", f"模块 '{module_name}' 微信推送发送成功", {"module_type": module_type})
                            else:
                                result["success"] = False
                                result["error"] = f"微信推送失败: {response_json.get('msg')}"
                                if workflow_id:
                                    log_workflow_action(workflow_id, "error", f"模块 '{module_name}' 微信推送失败: {response_json.get('msg')}", {"module_type": module_type})
                    except Exception as e:
                        result["success"] = False
                        result["error"] = f"微信推送失败: {str(e)}"
                        if workflow_id:
                            log_workflow_action(workflow_id, "error", f"模块 '{module_name}' 微信推送失败: {str(e)}", {"module_type": module_type})
                        
            elif notification_type == "pushplus":
                # 发送PushPlus推送
                system_config = get_config()
                pushplus_config = system_config.get("pushplus", {})
                
                if not pushplus_config.get("token"):
                    result["success"] = False
                    result["error"] = "PushPlus服务未配置"
                    if workflow_id:
                        log_workflow_action(workflow_id, "error", f"模块 '{module_name}' PushPlus服务未配置", {"module_type": module_type})
                else:
                    try:
                        # 准备请求数据，to字段可能是用户指定的topic
                        pushplus_data = {
                            "token": pushplus_config.get("token"),
                            "title": title,
                            "content": content,
                            "template": "html"
                        }
                        
                        # 如果用户提供了接收者，则覆盖默认配置
                        if to:
                            pushplus_data["topic"] = to
                        elif pushplus_config.get("topic"):
                            # 使用系统配置的默认topic
                            pushplus_data["topic"] = pushplus_config.get("topic")
                        
                        async with httpx.AsyncClient() as client:
                            response = await client.post(
                                "https://www.pushplus.plus/send", 
                                json=pushplus_data
                            )
                            response_json = response.json()
                            
                            # 记录推送响应
                            if workflow_id:
                                log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' PushPlus响应", {
                                    "module_type": module_type,
                                    "response": response_json
                                })
                            
                            if response_json.get("code") == 200:
                                result["output"] = "PushPlus推送发送成功"
                                if workflow_id:
                                    log_workflow_action(workflow_id, "info", f"模块 '{module_name}' PushPlus推送发送成功", {"module_type": module_type})
                            else:
                                result["success"] = False
                                result["error"] = f"PushPlus推送失败: {response_json.get('msg')}"
                                if workflow_id:
                                    log_workflow_action(workflow_id, "error", f"模块 '{module_name}' PushPlus推送失败: {response_json.get('msg')}", {"module_type": module_type})
                    except Exception as e:
                        result["success"] = False
                        result["error"] = f"PushPlus推送失败: {str(e)}"
                        if workflow_id:
                            log_workflow_action(workflow_id, "error", f"模块 '{module_name}' PushPlus推送失败: {str(e)}", {"module_type": module_type})
                
        elif module_type == "delay":
            seconds = config.get("seconds", 5)
            await asyncio.sleep(seconds)
            result["output"] = f"等待了 {seconds} 秒"
            
        elif module_type == "aes_encrypt":
            input_text = replace_variables(config.get("input", ""), variables)
            key = replace_variables(config.get("key", ""), variables)
            mode = config.get("mode", "ECB")
            iv_text = replace_variables(config.get("iv", ""), variables)
            encoding = config.get("encoding", "base64")
            
            # 记录输入
            if workflow_id:
                log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' 输入: {input_text[:100]}", {"module_type": module_type})
            
            try:
                # 处理密钥长度
                if len(key) < 16:
                    key = key.ljust(16, '\0')  # 补足16位
                elif len(key) > 16 and len(key) < 24:
                    key = key.ljust(24, '\0')  # 补足24位
                elif len(key) > 24 and len(key) < 32:
                    key = key.ljust(32, '\0')  # 补足32位
                elif len(key) > 32:
                    key = key[:32]  # 截取32位
                
                key_bytes = key.encode('utf-8')
                
                # ECB模式
                if mode == "ECB":
                    cipher = AES.new(key_bytes, AES.MODE_ECB)
                    ct_bytes = cipher.encrypt(pad(input_text.encode('utf-8'), AES.block_size))
                # CBC模式
                else:
                    # 处理IV
                    if iv_text:
                        # 处理IV长度，确保为16字节
                        if len(iv_text) < 16:
                            iv_text = iv_text.ljust(16, '\0')  # 补足16位
                        elif len(iv_text) > 16:
                            iv_text = iv_text[:16]  # 截取16位
                        iv = iv_text.encode('utf-8')
                    else:
                        iv = b'\x00' * 16  # 使用全零IV
                    
                    cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
                    ct_bytes = cipher.encrypt(pad(input_text.encode('utf-8'), AES.block_size))
                
                # 编码输出
                if encoding == "base64":
                    encrypted = base64.b64encode(ct_bytes).decode('utf-8')
                else:  # hex
                    encrypted = ct_bytes.hex()
                
                result["output"] = encrypted
                
                # 记录输出
                if workflow_id:
                    log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' 输出: {encrypted[:100]}", {"module_type": module_type})
                
                if config.get("output_var"):
                    variables[config["output_var"]] = encrypted
                    
            except Exception as e:
                result["success"] = False
                result["error"] = f"AES加密失败: {str(e)}"
                if workflow_id:
                    log_workflow_action(workflow_id, "error", f"模块 '{module_name}' AES加密失败: {str(e)}", {"module_type": module_type})
                
        elif module_type == "aes_decrypt":
            input_text = replace_variables(config.get("input", ""), variables)
            key = replace_variables(config.get("key", ""), variables)
            mode = config.get("mode", "ECB")
            iv_text = replace_variables(config.get("iv", ""), variables)
            encoding = config.get("encoding", "base64")
            
            # 记录输入
            if workflow_id:
                log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' 输入: {input_text[:100]}", {"module_type": module_type})
            
            try:
                # 处理密钥长度
                if len(key) < 16:
                    key = key.ljust(16, '\0')  # 补足16位
                elif len(key) > 16 and len(key) < 24:
                    key = key.ljust(24, '\0')  # 补足24位
                elif len(key) > 24 and len(key) < 32:
                    key = key.ljust(32, '\0')  # 补足32位
                elif len(key) > 32:
                    key = key[:32]  # 截取32位
                
                key_bytes = key.encode('utf-8')
                
                # 解码输入
                if encoding == "base64":
                    ct_bytes = base64.b64decode(input_text)
                else:  # hex
                    ct_bytes = bytes.fromhex(input_text)
                
                # ECB模式
                if mode == "ECB":
                    cipher = AES.new(key_bytes, AES.MODE_ECB)
                    pt_bytes = unpad(cipher.decrypt(ct_bytes), AES.block_size)
                # CBC模式
                else:
                    # 处理IV
                    if iv_text:
                        # 处理IV长度，确保为16字节
                        if len(iv_text) < 16:
                            iv_text = iv_text.ljust(16, '\0')  # 补足16位
                        elif len(iv_text) > 16:
                            iv_text = iv_text[:16]  # 截取16位
                        iv = iv_text.encode('utf-8')
                    else:
                        iv = b'\x00' * 16  # 使用全零IV
                    
                    cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
                    pt_bytes = unpad(cipher.decrypt(ct_bytes), AES.block_size)
                
                decrypted = pt_bytes.decode('utf-8')
                result["output"] = decrypted
                
                # 记录输出
                if workflow_id:
                    log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' 输出: {decrypted[:100]}", {"module_type": module_type})
                
                if config.get("output_var"):
                    variables[config["output_var"]] = decrypted
                    
            except Exception as e:
                result["success"] = False
                result["error"] = f"AES解密失败: {str(e)}"
                if workflow_id:
                    log_workflow_action(workflow_id, "error", f"模块 '{module_name}' AES解密失败: {str(e)}", {"module_type": module_type})
                    
        elif module_type == "condition":
            input_value = replace_variables(config.get("input", ""), variables)
            condition = config.get("condition", "等于")
            compare_value = replace_variables(config.get("compare_value", ""), variables)
            true_branch = config.get("true_branch", "if_true")
            false_branch = config.get("false_branch", "if_false")
            
            # 记录条件判断
            if workflow_id:
                log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' 条件判断: {input_value} {condition} {compare_value}", {"module_type": module_type})
            
            # 条件判断
            condition_result = False
            
            if condition == "包含":
                condition_result = compare_value in input_value
            elif condition == "等于":
                condition_result = input_value == compare_value
            elif condition == "大于":
                try:
                    condition_result = float(input_value) > float(compare_value)
                except (ValueError, TypeError):
                    condition_result = False
            elif condition == "小于":
                try:
                    condition_result = float(input_value) < float(compare_value)
                except (ValueError, TypeError):
                    condition_result = False
            elif condition == "不包含":
                condition_result = compare_value not in input_value
            elif condition == "为空":
                condition_result = not input_value or input_value.lower() == "null" or input_value.lower() == "none"
            
            # 设置结果
            result["output"] = condition_result
            result["branch"] = true_branch if condition_result else false_branch
            
            # 记录判断结果
            if workflow_id:
                log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' 条件结果: {condition_result}, 分支: {result['branch']}", {"module_type": module_type})
            
            # 设置变量
            variables["_condition_result"] = condition_result
            variables["_current_branch"] = result["branch"]
                
        elif module_type == "condition_end":
            # 清除条件变量
            if "_condition_result" in variables:
                del variables["_condition_result"]
            if "_current_branch" in variables:
                del variables["_current_branch"]
            
            result["output"] = "条件判断结束"
            
            # 记录
            if workflow_id:
                log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' 条件判断结束", {"module_type": module_type})
                
        elif module_type == "repeat":
            target_module = config.get("target_module", "")
            times = config.get("times", 1)
            interval = config.get("interval", 0)
            
            # 记录重复操作
            if workflow_id:
                log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' 重复执行模块 {target_module} {times}次", {"module_type": module_type})
            
            # 存储重复状态
            variables["_repeat_module"] = target_module
            variables["_repeat_times"] = times
            variables["_repeat_current"] = 0
            
            result["output"] = f"将重复执行模块 {target_module} {times}次"
        
        # 随机数生成模块
        elif module_type == "random_number":
            random_type = config.get("type", "整数")
            output_var = config.get("output_var", "")
            
            # 记录操作信息
            if workflow_id:
                log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' 生成随机数", {
                    "module_type": module_type,
                    "random_type": random_type
                })
            
            # 生成随机数
            if random_type == "整数":
                min_val = int(config.get("min", 1))
                max_val = int(config.get("max", 100))
                random_value = random.randint(min_val, max_val)
                result["output"] = str(random_value)
                
                if workflow_id:
                    log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' 生成整数随机数", {
                        "module_type": module_type,
                        "range": f"{min_val} - {max_val}",
                        "result": random_value
                    })
            else:  # 字符串类型
                length = int(config.get("length", 8))
                chars_type = config.get("chars", "数字+字母")
                
                if chars_type == "数字":
                    chars = string.digits
                elif chars_type == "字母":
                    chars = string.ascii_letters
                elif chars_type == "数字+字母":
                    chars = string.digits + string.ascii_letters
                else:  # 数字+字母+符号
                    chars = string.digits + string.ascii_letters + string.punctuation
                
                random_value = ''.join(random.choice(chars) for _ in range(length))
                result["output"] = random_value
                
                if workflow_id:
                    log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' 生成随机字符串", {
                        "module_type": module_type,
                        "length": length,
                        "chars_type": chars_type,
                        "result": random_value
                    })
            
            # 保存到变量
            if output_var:
                variables[output_var] = result["output"]
        
        # 时间戳模块
        elif module_type == "timestamp":
            action = config.get("action", "获取当前时间")
            output_format = config.get("format", "时间戳(秒)")
            output_var = config.get("output_var", "")
            
            # 记录操作信息
            if workflow_id:
                log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' 处理时间戳", {
                    "module_type": module_type,
                    "action": action,
                    "format": output_format
                })
            
            try:
                if action == "获取当前时间":
                    # 获取当前时间
                    current_time = datetime.datetime.now()
                    
                    if output_format == "时间戳(秒)":
                        timestamp_value = str(int(current_time.timestamp()))
                    elif output_format == "时间戳(毫秒)":
                        timestamp_value = str(int(current_time.timestamp() * 1000))
                    else:  # 格式化时间
                        datetime_format = config.get("datetime_format", "%Y-%m-%d %H:%M:%S")
                        timestamp_value = current_time.strftime(datetime_format)
                    
                    result["output"] = timestamp_value
                    
                else:  # 转换时间字符串
                    input_time = replace_variables(config.get("input_time", ""), variables)
                    input_format = config.get("input_format", "%Y-%m-%d %H:%M:%S")
                    
                    # 解析输入时间
                    parsed_time = datetime.datetime.strptime(input_time, input_format)
                    
                    if output_format == "时间戳(秒)":
                        timestamp_value = str(int(parsed_time.timestamp()))
                    elif output_format == "时间戳(毫秒)":
                        timestamp_value = str(int(parsed_time.timestamp() * 1000))
                    else:  # 格式化时间
                        datetime_format = config.get("datetime_format", "%Y-%m-%d %H:%M:%S")
                        timestamp_value = parsed_time.strftime(datetime_format)
                    
                    result["output"] = timestamp_value
                
                # 记录结果
                if workflow_id:
                    log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' 时间戳结果", {
                        "module_type": module_type,
                        "result": result["output"]
                    })
                
                # 保存到变量
                if output_var:
                    variables[output_var] = result["output"]
                    
            except Exception as e:
                result["success"] = False
                result["error"] = f"时间处理失败: {str(e)}"
                if workflow_id:
                    log_workflow_action(workflow_id, "error", f"模块 '{module_name}' 时间处理失败: {str(e)}", {"module_type": module_type})
        
        # 系统代理模块
        elif module_type == "system_proxy":
            proxy_url = replace_variables(config.get("proxy_url", ""), variables)
            scope = config.get("scope", "全局")
            reset = config.get("reset", False)
            
            # 记录操作信息
            if workflow_id:
                log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' 设置系统代理", {
                    "module_type": module_type,
                    "proxy_url": proxy_url if not reset else "重置",
                    "scope": scope
                })
            
            # 设置或重置代理
            if reset:
                # 重置代理设置
                if scope == "全局":
                    variables["_global_proxy"] = None
                else:
                    variables[f"_branch_proxy_{variables.get('_current_branch', 'default')}"] = None
                
                result["output"] = "已重置代理设置"
            else:
                # 设置代理
                if scope == "全局":
                    variables["_global_proxy"] = proxy_url
                else:
                    variables[f"_branch_proxy_{variables.get('_current_branch', 'default')}"] = proxy_url
                
                result["output"] = f"已设置代理: {proxy_url}"
            
            # 记录结果
            if workflow_id:
                log_workflow_action(workflow_id, "info", f"模块 '{module_name}' {result['output']}", {"module_type": module_type})
            
        # 处理账号配置
        elif module_type == "account_config":
            action = config.get("action", "读取")
            category = config.get("category", "静态Token")
            service = config.get("service", "")
            account_name = config.get("account_name", "")
            field = config.get("field", "用户名")
            value = config.get("value", "")
            
            # 转换中文类别名称为英文
            category_mapping = {
                "静态Token": "static_tokens",
                "动态Token": "dynamic_tokens",
                "其他信息": "other"
            }
            category_key = category_mapping.get(category, "static_tokens")
            
            # 记录操作信息
            if workflow_id:
                log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' 账号配置操作", {
                    "module_type": module_type,
                    "action": action,
                    "category": category,
                    "service": service,
                    "account_name": account_name,
                    "field": field
                })
            
            if action == "读取":
                # 读取账号配置
                account_info = get_account_info(category_key, service, account_name)
                
                # 将英文字段名映射为中文
                field_mapping = {
                    "username": "用户名",
                    "password": "密码",
                    "token": "token",
                    "expires_at": "过期时间"
                }
                
                # 获取指定字段的值
                field_key = next((k for k, v in field_mapping.items() if v == field), field)
                field_value = account_info.get(field_key, "")
                
                result["output"] = field_value
                
                # 记录读取结果
                if workflow_id:
                    log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' 读取账号配置", {
                        "module_type": module_type,
                        "category": category,
                        "service": service,
                        "account_name": account_name,
                        "field": field,
                        "value": field_value if field != "密码" else "******"
                    })
                
                # 设置输出变量
                if config.get("output_var"):
                    variables[config["output_var"]] = field_value
            
            elif action == "更新":
                # 从变量中获取值
                if value and value.startswith("[") and value.endswith("]"):
                    var_name = value[1:-1]  # 去除[]
                    if var_name in variables:
                        value = variables[var_name]
                    else:
                        result["success"] = False
                        result["error"] = f"变量 {var_name} 未定义"
                        if workflow_id:
                            log_workflow_action(workflow_id, "error", f"模块 '{module_name}' 更新账号配置失败，变量未定义", {
                                "module_type": module_type,
                                "variable": var_name
                            })
                        return result
                
                # 更新账号配置
                if service and account_name:
                    success = update_account_field(category_key, service, account_name, field, value)
                    if success:
                        result["output"] = f"账号配置 '{account_name}' 更新成功"
                        
                        # 记录更新结果
                        if workflow_id:
                            log_workflow_action(workflow_id, "info", f"模块 '{module_name}' 账号配置更新成功", {
                                "module_type": module_type,
                                "category": category,
                                "service": service,
                                "account_name": account_name,
                                "field": field,
                                "value": value if field != "密码" else "******"
                            })
                    else:
                        result["success"] = False
                        result["error"] = "更新账号配置失败"
                        if workflow_id:
                            log_workflow_action(workflow_id, "error", f"模块 '{module_name}' 更新账号配置失败", {
                                "module_type": module_type,
                                "category": category,
                                "service": service,
                                "account_name": account_name
                            })
                else:
                    result["success"] = False
                    result["error"] = "未提供完整的账号信息（服务名称和配置名称）"
                    if workflow_id:
                        log_workflow_action(workflow_id, "error", f"模块 '{module_name}' 未提供完整的账号信息", {
                            "module_type": module_type,
                            "service": service,
                            "account_name": account_name
                        })
            else:
                result["success"] = False
                result["error"] = f"未支持的操作类型: {action}"
                if workflow_id:
                    log_workflow_action(workflow_id, "error", f"模块 '{module_name}' 未支持的操作类型", {
                        "module_type": module_type,
                        "action": action
                    })
        # 检查域名模块
        elif module_type == "check_domains":
            domains_input = config.get("domains", "")
            port = int(config.get("port", 80))
            timeout = int(config.get("timeout", 5))
            output_var = config.get("output_var", "")
            all_results_var = config.get("all_results_var", "")
            
            # 解析域名列表，移除空行和注释
            domains = []
            for line in domains_input.splitlines():
                line = line.strip()
                if line and not line.startswith('#'):
                    # 移除协议前缀如果有的话
                    line = re.sub(r'^https?://', '', line)
                    # 只取域名部分，不包括路径
                    line = line.split('/')[0]
                    domains.append(line)
            
            if not domains:
                result["success"] = False
                result["error"] = "未提供有效的域名"
                if workflow_id:
                    log_workflow_action(workflow_id, "error", f"模块 '{module_name}' 未提供有效的域名", {"module_type": module_type})
                return result
            
            # 记录域名检查开始
            if workflow_id:
                log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' 开始检查域名", {
                    "module_type": module_type,
                    "domains": domains,
                    "port": port,
                    "timeout": timeout
                })
            
            # 检查结果
            results = {}
            available_domain = None
            
            # 检查每个域名
            for domain in domains:
                try:
                    # 创建socket连接
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(timeout)
                    
                    # 开始连接
                    start_time = time.time()
                    result_code = sock.connect_ex((domain, port))
                    response_time = round((time.time() - start_time) * 1000, 2)  # 毫秒
                    
                    # 关闭连接
                    sock.close()
                    
                    # 记录结果
                    if result_code == 0:
                        results[domain] = {
                            "available": True,
                            "message": "连接成功",
                            "response_time": response_time
                        }
                        
                        # 如果尚未找到可用域名，记录第一个可用的
                        if available_domain is None:
                            available_domain = domain
                            
                        if workflow_id:
                            log_workflow_action(workflow_id, "info", f"域名 {domain} 可用 (响应时间: {response_time}ms)", {
                                "module_type": module_type,
                                "domain": domain,
                                "available": True,
                                "response_time": response_time
                            })
                    else:
                        error_message = f"连接失败，错误码: {result_code}"
                        results[domain] = {
                            "available": False,
                            "message": error_message,
                            "response_time": response_time
                        }
                        
                        if workflow_id:
                            log_workflow_action(workflow_id, "warning", f"域名 {domain} 不可用 ({error_message})", {
                                "module_type": module_type,
                                "domain": domain,
                                "available": False,
                                "error_code": result_code
                            })
                            
                except socket.gaierror:
                    # 域名无法解析
                    results[domain] = {
                        "available": False,
                        "message": "域名无法解析"
                    }
                    
                    if workflow_id:
                        log_workflow_action(workflow_id, "warning", f"域名 {domain} 无法解析", {
                            "module_type": module_type,
                            "domain": domain,
                            "available": False,
                            "error": "域名无法解析"
                        })
                        
                except Exception as e:
                    # 其他错误
                    results[domain] = {
                        "available": False,
                        "message": f"检查失败: {str(e)}"
                    }
                    
                    if workflow_id:
                        log_workflow_action(workflow_id, "error", f"检查域名 {domain} 时出错: {str(e)}", {
                            "module_type": module_type,
                            "domain": domain,
                            "available": False,
                            "error": str(e)
                        })
                        
                # 如果已找到可用域名且不需要检查所有域名的结果，可以提前终止
                if available_domain and not all_results_var:
                    break
            
            # 设置输出结果
            if available_domain:
                result["output"] = available_domain
                if output_var:
                    variables[output_var] = available_domain
                    
                if workflow_id:
                    log_workflow_action(workflow_id, "info", f"模块 '{module_name}' 找到可用域名: {available_domain}", {
                        "module_type": module_type,
                        "available_domain": available_domain
                    })
            else:
                result["success"] = False
                result["error"] = "未找到可用的域名"
                result["output"] = ""
                
                if output_var:
                    variables[output_var] = ""
                    
                if workflow_id:
                    log_workflow_action(workflow_id, "warning", f"模块 '{module_name}' 未找到可用域名", {"module_type": module_type})
            
            # 如果需要所有结果，保存到变量
            if all_results_var:
                variables[all_results_var] = json.dumps(results)
                if workflow_id:
                    log_workflow_action(workflow_id, "debug", f"模块 '{module_name}' 保存所有检查结果到变量 {all_results_var}", {
                        "module_type": module_type,
                        "results": results
                    })
        else:
            result["success"] = False
            result["error"] = f"未知的模块类型: {module_type}"
            if workflow_id:
                log_workflow_action(workflow_id, "error", f"模块 '{module_name}' 未知的模块类型: {module_type}", {"module_type": module_type})
            
    except Exception as e:
        result["success"] = False
        result["error"] = f"模块执行出错: {str(e)}"
        if workflow_id:
            log_workflow_action(workflow_id, "error", f"模块 '{module_name}' 执行异常: {str(e)}", {"module_type": module_type, "exception": str(e)})
        else:
            logger.error(f"执行模块 {module.get('name')} 时出错: {e}")
        
    return result

async def execute_workflow(workflow: Dict[str, Any]) -> Dict[str, Any]:
    """执行完整工作流"""
    modules = workflow.get("modules", [])
    connections = workflow.get("connections", [])
    workflow_id = workflow.get("id")
    workflow_name = workflow.get("name", "未命名工作流")
    
    # 记录工作流开始执行
    log_workflow_action(workflow_id, "info", f"开始执行工作流: {workflow_name}")
    
    # 创建模块ID到模块的映射
    module_map = {module.get("id"): module for module in modules}
    
    # 创建模块依赖图
    dependency_graph = {}
    for module in modules:
        module_id = module.get("id")
        dependency_graph[module_id] = []
    
    for connection in connections:
        source = connection.get("source")
        target = connection.get("target")
        if source and target:
            dependency_graph[target].append(source)
    
    # 拓扑排序 - 确定执行顺序
    execution_order = []
    visited = set()
    temp_visited = set()
    
    def visit(node):
        if node in temp_visited:
            # 检测到循环依赖
            error_msg = f"工作流包含循环依赖，无法执行"
            log_workflow_action(workflow_id, "error", error_msg)
            raise Exception(error_msg)
        
        if node not in visited:
            temp_visited.add(node)
            for dependency in dependency_graph.get(node, []):
                visit(dependency)
            temp_visited.remove(node)
            visited.add(node)
            execution_order.append(node)
    
    # 对每个节点进行拓扑排序
    for node in dependency_graph:
        if node not in visited:
            visit(node)
    
    # 反转执行顺序，因为我们需要从依赖最少的节点开始
    execution_order.reverse()
    
    # 为每个模块分配执行顺序号（用于条件判断和重复操作）
    module_order = {}
    current_order = 1
    current_branch = None
    in_condition_block = False
    
    for module_id in execution_order:
        module = module_map.get(module_id)
        module_type = module.get("type")
        
        # 如果是条件判断模块，开始进入分支
        if module_type == "condition":
            in_condition_block = True
            module_order[module_id] = current_order
            current_order += 1
        # 如果是条件结束模块，结束分支
        elif module_type == "condition_end":
            in_condition_block = False
            current_branch = None
            module_order[module_id] = current_order
            current_order += 1
        # 在条件块中的模块
        elif in_condition_block:
            # 如果尚未分配分支，模块会在条件判断后被分配
            module_order[module_id] = f"{current_order-1}.{module.get('name', 'unnamed')}"
        # 正常模块
        else:
            module_order[module_id] = current_order
            current_order += 1
    
    # 执行工作流
    variables = get_variables()  # 获取全局变量
    workflow_results = {}
    
    # 添加当前执行的分支和模块重复状态
    variables["_current_branch"] = None
    variables["_repeat_module"] = None
    variables["_repeat_times"] = 0
    variables["_repeat_current"] = 0
    
    # 生成有序模块执行队列
    ordered_modules = sorted([(module_order[mid], mid) for mid in execution_order])
    i = 0
    
    while i < len(ordered_modules):
        order, module_id = ordered_modules[i]
        module = module_map.get(module_id)
        if not module:
            i += 1
            continue
            
        module_name = module.get("name", "未命名模块")
        module_type = module.get("type")
        
        # 处理条件判断
        if module_type == "condition":
            log_workflow_action(workflow_id, "info", f"执行条件判断模块: {module_name}", {"module_id": module_id})
            result = await execute_module(module, variables, workflow_id)
            workflow_results[module_id] = result
            
            # 记录结果
            if result.get("success"):
                log_workflow_action(workflow_id, "info", f"条件判断模块 '{module_name}' 执行成功")
            else:
                log_workflow_action(workflow_id, "error", f"条件判断模块 '{module_name}' 执行失败: {result.get('error')}")
                
            # 记录当前活动分支
            variables["_current_branch"] = result.get("branch")
            
        # 处理条件结束
        elif module_type == "condition_end":
            log_workflow_action(workflow_id, "info", f"执行条件结束模块: {module_name}", {"module_id": module_id})
            result = await execute_module(module, variables, workflow_id)
            workflow_results[module_id] = result
            
            # 清除分支状态
            variables["_current_branch"] = None
            
        # 处理重复操作
        elif module_type == "repeat":
            log_workflow_action(workflow_id, "info", f"执行重复操作模块: {module_name}", {"module_id": module_id})
            result = await execute_module(module, variables, workflow_id)
            workflow_results[module_id] = result
            
            # 开始重复执行目标模块
            target_module_order = module.get("config", {}).get("target_module", "")
            times = int(module.get("config", {}).get("times", 1))
            interval = float(module.get("config", {}).get("interval", 0))
            
            # 查找目标模块
            target_module_id = None
            for mo, mid in ordered_modules:
                if str(mo) == str(target_module_order):
                    target_module_id = mid
                    break
            
            if target_module_id:
                target_module = module_map.get(target_module_id)
                
                # 执行重复操作
                for t in range(times):
                    variables["_repeat_current"] = t + 1
                    
                    log_workflow_action(workflow_id, "info", f"重复执行模块 '{target_module.get('name')}' ({t+1}/{times})", {"module_id": target_module_id})
                    target_result = await execute_module(target_module, variables, workflow_id)
                    
                    # 记录结果
                    if target_result.get("success"):
                        log_workflow_action(workflow_id, "info", f"重复执行模块 '{target_module.get('name')}' ({t+1}/{times}) 成功")
                    else:
                        log_workflow_action(workflow_id, "error", f"重复执行模块 '{target_module.get('name')}' ({t+1}/{times}) 失败: {target_result.get('error')}")
                        
                    # 执行间隔
                    if t < times - 1 and interval > 0:
                        await asyncio.sleep(interval)
                        
            # 清除重复状态
            variables["_repeat_module"] = None
            variables["_repeat_times"] = 0
            variables["_repeat_current"] = 0
            
        # 正常模块，在条件分支内时需要检查分支
        elif isinstance(order, str) and "." in str(order):
            # 在条件分支内的模块，检查是否是当前活动分支
            module_branch = order.split(".", 1)[1]
            current_branch = variables.get("_current_branch")
            
            # 只有当前活动分支的模块才会执行
            if current_branch and module_branch == current_branch:
                log_workflow_action(workflow_id, "info", f"执行分支 '{current_branch}' 中的模块: {module_name}", {"module_id": module_id})
                result = await execute_module(module, variables, workflow_id)
                workflow_results[module_id] = result
                
                # 记录结果
                if result.get("success"):
                    log_workflow_action(workflow_id, "info", f"模块 '{module_name}' 执行成功")
                else:
                    log_workflow_action(workflow_id, "error", f"模块 '{module_name}' 执行失败: {result.get('error')}")
                
        # 普通模块
        else:
            log_workflow_action(workflow_id, "info", f"执行模块: {module_name}", {"module_id": module_id})
            
            try:
                # 传递工作流ID到execute_module函数
                result = await execute_module(module, variables, workflow_id)
                workflow_results[module_id] = result
                
                # 记录模块执行结果
                if result.get("success"):
                    log_workflow_action(workflow_id, "info", f"模块 '{module_name}' 执行成功")
                else:
                    log_workflow_action(workflow_id, "error", f"模块 '{module_name}' 执行失败: {result.get('error')}")
            except Exception as e:
                error_msg = f"模块 '{module_name}' 执行异常: {str(e)}"
                log_workflow_action(workflow_id, "error", error_msg)
                workflow_results[module_id] = {"success": False, "error": error_msg}
        
        i += 1
    
    # 保存更新后的变量
    update_variables(variables)
    
    # 创建模块ID到模块名称的映射
    module_id_to_name = {}
    for module_id, module in module_map.items():
        module_name = module.get("name", "未命名模块")
        module_type = module.get("type")
        module_type_info = MODULE_TYPES.get(module_type, {})
        module_type_name = module_type_info.get("name", module_type)
        # 保存模块ID到可读名称的映射
        module_id_to_name[module_id] = f"{module_name} ({module_type_name})"
    
    # 记录工作流执行完成
    success = all(result.get("success", False) for result in workflow_results.values())
    if success:
        log_workflow_action(workflow_id, "info", f"工作流 '{workflow_name}' 执行成功完成")
    else:
        log_workflow_action(workflow_id, "warning", f"工作流 '{workflow_name}' 执行完成，但存在失败的模块")
    
    # 转换结果，创建一个新的字典，用模块名称替代模块ID
    readable_results = {}
    for module_id, result in workflow_results.items():
        module_name = module_id_to_name.get(module_id, module_id)
        readable_results[module_name] = result
    
    # 记录详细结果到日志（包含模块ID和模块名称）
    log_details = {
        "success": success,
        "results": workflow_results,
        "module_names": module_id_to_name  # 添加模块名称映射，便于前端显示
    }
    log_workflow_action(workflow_id, "info", f"工作流 '{workflow_name}' 执行完成", log_details)
    
    return {
        "success": success,
        "results": workflow_results,
        "module_names": module_id_to_name  # 返回模块名称映射，供上层使用
    }

# get_all_module_types函数已移至module_types.py 