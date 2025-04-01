import os
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
from starlette.middleware.sessions import SessionMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.routes import admin, workflows, auth
from app.models.workflow import init_workflows
from app.utils.scheduler import init_scheduler
from app.utils.data_dir import ensure_data_dir
from app.utils.config import get_config, ensure_config_exists, get_log_level
from app.models.log import setup_logging, log_system_action

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
async def starlette_exception_handler(request: Request, exc: StarletteHTTPException):
    """Starlette HTTP异常处理"""
    # 如果是401未授权错误，重定向到登录页面
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        return RedirectResponse(url="/login", status_code=303)
    
    if exc.status_code == 404:
        return templates.TemplateResponse(
            "error.html", 
            {"request": request, "status_code": exc.status_code, "detail": "您访问的页面不存在"},
            status_code=404
        )
    
    # 记录错误日志
    log_system_action("error", f"HTTP错误 {exc.status_code}: {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc.detail)}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """FastAPI HTTP异常处理"""
    # 如果是401未授权错误，重定向到登录页面
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        return RedirectResponse(url="/login", status_code=303)
    
    # 记录错误日志
    log_system_action("error", f"HTTP错误: {exc.status_code} - {exc.detail}", {
        "status_code": exc.status_code,
        "detail": exc.detail,
        "path": request.url.path
    })
    
    return templates.TemplateResponse(
        "error.html", 
        {"request": request, "error": exc.detail, "status_code": exc.status_code}
    )

@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    # 确保数据目录存在
    ensure_data_dir()
    
    # 确保配置文件存在
    ensure_config_exists()
    
    # 设置日志系统
    log_level = get_log_level()
    setup_logging(log_level)
    
    # 记录系统启动
    log_system_action("info", "系统启动", {"version": "1.6.3"})
    
    # 初始化工作流
    init_workflows()
    
    # 初始化调度器
    init_scheduler()

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