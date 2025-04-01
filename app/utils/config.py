import os
import yaml
import json
import logging
from typing import Dict, Any, Optional

# 配置文件路径
CONFIG_FILE = "app/data/config.yaml"
VARS_FILE = "app/data/variables.json"
ACCOUNT_CONFIG_FILE = "app/data/account_config.json"

# 默认配置
DEFAULT_CONFIG = {
    "admin_password": "admin",
    "log_level": "INFO",  # 新增日志级别，可选：DEBUG, INFO, WARNING, ERROR
    "log_max_entries": 10000,  # 每种类型日志保留的最大条数
    "email": {
        "smtp_server": "",
        "smtp_port": 465,
        "smtp_user": "",
        "smtp_password": "",
        "sender": "",
        # 新增默认收件人配置
        "default_recipient": ""
    },
    "wxpusher": {
        "app_token": "",
        # 新增默认UID配置
        "default_uid": ""
    },
    "pushplus": {
        "token": "",
        "topic": "",
        # 新增默认接收者配置
        "default_receiver": ""
    }
}

def _load_config() -> Dict[str, Any]:
    """从文件加载配置，不进行任何检查"""
    # 直接从文件读取配置
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except (FileNotFoundError, yaml.YAMLError):
        return {}

def ensure_config_exists():
    """确保配置文件存在"""
    # 创建数据目录
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    
    if not os.path.exists(CONFIG_FILE):
        # 创建包含默认配置的文件
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(DEFAULT_CONFIG, f, allow_unicode=True, sort_keys=False)
    else:
        # 确保已有配置包含所有默认项
        current_config = _load_config()
        updated = False
        
        # 使用深度合并添加缺失的配置
        def deep_merge(source, destination):
            """深度合并字典"""
            nonlocal updated
            for key, value in source.items():
                if key not in destination:
                    destination[key] = value
                    updated = True
                elif isinstance(value, dict) and isinstance(destination[key], dict):
                    deep_merge(value, destination[key])
            return destination
        
        result = deep_merge(DEFAULT_CONFIG, current_config)
        
        if updated:
            # 如果添加了新配置项，保存更新后的配置
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                yaml.dump(result, f, allow_unicode=True, sort_keys=False)
    
    # 确保变量文件存在
    if not os.path.exists(VARS_FILE):
        # 创建变量目录
        os.makedirs(os.path.dirname(VARS_FILE), exist_ok=True)
        with open(VARS_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)

def get_config() -> Dict[str, Any]:
    """获取当前配置"""
    # 确保配置文件存在
    if not os.path.exists(CONFIG_FILE):
        ensure_config_exists()
    
    # 读取配置文件
    return _load_config()

def update_config(config: Dict[str, Any]) -> None:
    """更新配置"""
    # 确保配置文件存在
    if not os.path.exists(CONFIG_FILE):
        ensure_config_exists()
    
    # 读取现有配置
    current_config = _load_config()
    
    # 处理日志级别更改
    if 'log_level' in config and config['log_level'] != current_config.get('log_level'):
        log_level = config['log_level']
        # 验证日志级别
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
        if log_level.upper() in valid_levels:
            # 设置根日志记录器的级别
            logging.getLogger().setLevel(getattr(logging, log_level.upper()))
        else:
            # 如果无效，回退到默认值
            config['log_level'] = current_config.get('log_level', 'INFO')
    
    # 更新配置
    current_config.update(config)
    
    # 写入文件
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        yaml.dump(current_config, f, allow_unicode=True, sort_keys=False)

def get_admin_password() -> str:
    """获取管理员密码"""
    config = _load_config()
    return config.get("admin_password", "admin")

def set_admin_password(password: str) -> None:
    """设置管理员密码"""
    update_config({"admin_password": password})

def get_log_level() -> str:
    """
    获取当前日志级别
    
    Returns:
        日志级别字符串
    """
    config = _load_config()
    return config.get("log_level", "INFO")

def set_log_level(level: str):
    """
    设置日志级别
    
    Args:
        level: 日志级别
    """
    if level not in ["DEBUG", "INFO", "WARNING", "ERROR"]:
        level = "INFO"
    
    update_config({"log_level": level})
    
    # 设置Python日志系统的日志级别
    numeric_level = getattr(logging, level, None)
    if isinstance(numeric_level, int):
        logging.getLogger().setLevel(numeric_level)

def get_email_config() -> Dict[str, Any]:
    """获取邮件配置"""
    config = _load_config()
    return config.get("email", {})

def get_wxpusher_config() -> Dict[str, Any]:
    """获取微信推送配置"""
    config = _load_config()
    return config.get("wxpusher", {})

def _load_variables() -> Dict[str, Any]:
    """从文件加载变量，不进行任何检查"""
    try:
        with open(VARS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def get_variables() -> Dict[str, Any]:
    """获取所有存储的变量"""
    if not os.path.exists(VARS_FILE):
        ensure_config_exists()
    return _load_variables()

def update_variables(variables: Dict[str, Any]) -> None:
    """更新变量存储"""
    if not os.path.exists(VARS_FILE):
        ensure_config_exists()
    
    # 读取现有变量
    current_vars = _load_variables()
    # 更新变量
    current_vars.update(variables)
    # 写入文件
    with open(VARS_FILE, 'w', encoding='utf-8') as f:
        json.dump(current_vars, f, ensure_ascii=False, indent=2)

def get_variable(name: str, default: Any = None) -> Any:
    """获取指定变量的值"""
    variables = _load_variables()
    return variables.get(name, default)

def set_variable(name: str, value: Any) -> None:
    """设置指定变量的值"""
    update_variables({name: value})

def get_account_config() -> Dict[str, Any]:
    """获取账号配置信息"""
    try:
        with open(ACCOUNT_CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # 如果文件不存在或格式错误，返回空字典
        return {"accounts": {}}

def update_account_config(config: Dict[str, Any]) -> None:
    """更新账号配置信息"""
    # 创建目录（如果不存在）
    os.makedirs(os.path.dirname(ACCOUNT_CONFIG_FILE), exist_ok=True)
    
    # 写入文件
    with open(ACCOUNT_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def update_account_field(category: str, service: str, account_name: str, field: str, value: str) -> bool:
    """更新特定账号的指定字段
    
    Args:
        category: 账号类别，如 static_tokens, dynamic_tokens, other
        service: 服务类型，如 weibo, alipay, custom_service
        account_name: 账号名称，如 default, test, production
        field: 字段名称，如 用户名, 密码, token, 过期时间
        value: 字段值
        
    Returns:
        更新是否成功
    """
    # 获取当前账号配置
    account_config = get_account_config()
    
    # 将中文字段名映射为英文字段名
    field_mapping = {
        "用户名": "username",
        "密码": "password",
        "token": "token",
        "过期时间": "expires_at"
    }
    
    # 转换字段名
    field_name = field_mapping.get(field, field)
    
    try:
        # 确保路径存在
        if category not in account_config["accounts"]:
            account_config["accounts"][category] = {}
        if service not in account_config["accounts"][category]:
            account_config["accounts"][category][service] = {}
        if account_name not in account_config["accounts"][category][service]:
            account_config["accounts"][category][service][account_name] = {}
        
        # 更新字段值
        account_config["accounts"][category][service][account_name][field_name] = value
        
        # 保存更新后的配置
        update_account_config(account_config)
        return True
    except Exception as e:
        logging.error(f"更新账号配置字段失败: {e}")
        return False

def get_account_info(category: str, service: str, account_name: str) -> Dict[str, Any]:
    """获取特定账号的配置信息
    
    Args:
        category: 账号类别，如 email, database, api
        service: 服务类型，如 smtp_server, mysql, postgresql
        account_name: 账号名称，如 default, gmail, production
        
    Returns:
        账号配置信息，如未找到则返回空字典
    """
    account_config = get_account_config()
    
    try:
        return account_config["accounts"][category][service][account_name]
    except (KeyError, TypeError):
        return {} 