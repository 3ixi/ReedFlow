import os
from typing import Optional

# 默认数据目录
DEFAULT_DATA_DIR = "app/data"

def get_data_dir() -> str:
    """
    获取数据存储目录
    
    Returns:
        数据目录的绝对路径
    """
    # 从环境变量或配置文件获取数据目录
    # 为避免循环导入，延迟导入
    from app.utils.config import get_config
    
    # 尝试从配置中获取自定义数据目录
    try:
        config = get_config()
        data_dir = config.get("data_dir")
        if data_dir and os.path.isabs(data_dir):
            return data_dir
    except Exception:
        pass
    
    # 如果没有配置或读取失败，使用默认目录
    return DEFAULT_DATA_DIR

def ensure_data_dir() -> str:
    """
    确保数据目录存在，如果不存在则创建
    
    Returns:
        数据目录的绝对路径
    """
    data_dir = get_data_dir()
    
    # 确保目录存在
    os.makedirs(data_dir, exist_ok=True)
    
    # 确保必要的子目录存在
    for subdir in ["", "workflows", "modules"]:
        path = os.path.join(data_dir, subdir)
        os.makedirs(path, exist_ok=True)
    
    return data_dir 