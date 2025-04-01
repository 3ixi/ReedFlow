import os
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
from starlette.middleware.sessions import SessionMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

from app.routes import admin, workflows, auth
from app.models.workflow import init_workflows
from app.utils.scheduler import init_scheduler
from app.utils.config import get_log_level, ensure_config_exists
from app.models.log import setup_logging, log_system_action, migrate_old_logs

# 创建应用
app = FastAPI(
    title="ReedFlow",
    description="自动化工作流管理系统",
    version="1.6.3",
)

# 添加会话中间件
app.add_middleware(
    SessionMiddleware,
    secret_key=secrets.token_urlsafe(32),
    session_cookie="reedflow_session",
    max_age=43200,  # 12小时过期
)

# 跨域中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 挂载模板
templates = Jinja2Templates(directory="app/templates")

# 注册路由
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(workflows.router)

@app.get("/")
async def root():
    """根路径重定向到登录页面"""
    return RedirectResponse(url="/login")

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """全局HTTP异常处理器"""
    if exc.status_code == 404:
        return templates.TemplateResponse(
            "error.html", 
            {"request": request, "status_code": exc.status_code, "detail": "您访问的页面不存在"},
            status_code=404
        )
    
    # 对401未授权错误进行特殊处理，重定向到登录页面
    if exc.status_code == 401:
        return RedirectResponse(url="/login", status_code=303)
    
    # 记录错误日志
    log_system_action("error", f"HTTP错误 {exc.status_code}: {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc.detail)}
    )

@app.on_event("startup")
async def startup_event():
    """应用启动时执行的任务"""
    try:
        # 确保数据目录存在
        os.makedirs("app/data", exist_ok=True)
        
        # 确保配置文件存在并更新
        ensure_config_exists()
        
        # 设置日志级别
        log_level = get_log_level()
        setup_logging(log_level)
        
        # 关闭外部库的调试日志，避免它们被记录到系统日志
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        
        # 记录启动日志
        log_system_action("info", "系统启动")
        
        # 迁移旧日志到新的分离存储格式
        migrate_old_logs()
        
        # 初始化工作流数据
        init_workflows()
        
        # 初始化调度器
        init_scheduler()
    except Exception as e:
        log_system_action("error", f"启动失败: {e}")
        raise

def main():
    """应用程序主入口"""
    try:
        # 确保数据目录存在
        os.makedirs("app/data", exist_ok=True)
        
        # 设置日志记录
        setup_logging()
        
        # 关闭外部库的调试日志，避免它们被记录到系统日志
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        
        # 迁移旧日志
        migrate_old_logs()
        
        # 初始化工作流数据
        init_workflows()
        
        # 初始化调度器
        init_scheduler()
    except Exception as e:
        log_system_action("error", f"启动失败: {e}")
        raise

if __name__ == "__main__":
    # 移除reload=True以防止命令行窗口交互问题
    # 使用workers和log_level参数优化服务器性能和日志显示
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        workers=1,
        log_level="info"
    ) 