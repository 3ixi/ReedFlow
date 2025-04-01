import multiprocessing
import socket
import os
import time
import sys
import uvicorn
from datetime import datetime
import platform

# 避免PowerShell和命令行窗口交互问题
if platform.system() == "Windows":
    # 在Windows上使用spawn启动方式，避免资源继承导致的问题
    multiprocessing.set_start_method('spawn', force=True)

# 获取版本号
VERSION = "1.6.3"

# 美化的ASCII艺术字体
ASCII_ART = r"""
██████╗ ███████╗███████╗██████╗ ███████╗██╗      ██████╗ ██╗    ██╗
██╔══██╗██╔════╝██╔════╝██╔══██╗██╔════╝██║     ██╔═══██╗██║    ██║
██████╔╝█████╗  █████╗  ██║  ██║█████╗  ██║     ██║   ██║██║ █╗ ██║
██╔══██╗██╔══╝  ██╔══╝  ██║  ██║██╔══╝  ██║     ██║   ██║██║███╗██║
██║  ██║███████╗███████╗██████╔╝██║     ███████╗╚██████╔╝╚███╔███╔╝
╚═╝  ╚═╝╚══════╝╚══════╝╚═════╝ ╚═╝     ╚══════╝ ╚═════╝  ╚══╝╚══╝ 
"""

def get_local_ip():
    """获取本机IP地址"""
    try:
        # 创建一个临时socket连接，获取本地IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        # 如果获取失败，返回localhost
        return "127.0.0.1"

def run_server():
    """在独立进程中运行服务器"""
    # 日志配置
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "uvicorn.logging.DefaultFormatter",
                "fmt": "%(levelprefix)s %(message)s",
                "use_colors": None,
            },
            "access": {
                "()": "uvicorn.logging.AccessFormatter",
                "fmt": '%(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
            },
            "access": {
                "formatter": "access",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": "INFO"},
            "uvicorn.error": {"level": "INFO"},
            "uvicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": False},
        },
    }
    
    # 启动Uvicorn服务器
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000,
        workers=1,
        log_level="info",
        log_config=log_config
    )

def show_welcome_message():
    """显示欢迎信息和启动说明"""
    os.system('cls' if os.name == 'nt' else 'clear')
    print("\033[94m" + ASCII_ART + "\033[0m")
    print(f"\033[1mReedFlow v{VERSION} 自动化工作流管理系统\033[0m")
    print("-" * 60)
    print("系统状态: \033[92m已启动\033[0m")
    local_ip = get_local_ip()
    print(f"您可以通过以下地址访问:")
    print(f"  > \033[96mhttp://{local_ip}:8000\033[0m (本机网络)")
    print(f"  > \033[96mhttp://127.0.0.1:8000\033[0m (本地访问)")
    print("-" * 60)
    print("提示:")
    print("1. 保持此窗口处于打开状态，系统才能正常运行")
    print("2. 关闭此窗口将停止系统服务")
    print("3. 在浏览器中访问上述地址即可使用系统")
    print("4. 如点击网页没有反应，在此窗口执行一次Ctrl+C")
    print("-" * 60)

if __name__ == "__main__":
    # 显示欢迎信息
    show_welcome_message()
    
    # 创建服务器进程
    server_process = multiprocessing.Process(target=run_server)
    server_process.daemon = True  # 设置为守护进程，主进程退出时自动终止
    server_process.start()
    
    try:
        # 主进程保持运行，但不阻塞命令行输入
        while server_process.is_alive():
            # 非阻塞方式保持主进程运行
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\033[93m正在关闭服务...\033[0m")
        # 优雅地关闭服务器进程
        server_process.terminate()
        server_process.join(timeout=5)
        print("\033[91mReedFlow服务已停止\033[0m")
        sys.exit(0) 