from fastapi import APIRouter, Request, Form, Depends, HTTPException, status
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
import bcrypt
from app.utils.config import get_admin_password

router = APIRouter()
security = HTTPBasic()
templates = Jinja2Templates(directory="app/templates")

# 验证密码
def verify_password(plain_password, hashed_password=None):
    # 如果没有提供哈希密码，使用默认的admin密码
    if hashed_password is None:
        admin_password = get_admin_password()
        if plain_password == admin_password:
            return True
    else:
        # 使用bcrypt验证密码
        if isinstance(hashed_password, str):
            hashed_password = hashed_password.encode('utf-8')
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password)
    return False

# 验证用户是否已登录
async def get_current_user(request: Request):
    user = request.session.get("user")
    if not user:
        # 改为直接重定向到登录页面，而不是抛出异常
        # 这里不能使用重定向，因为get_current_user是一个依赖项，
        # 而依赖项不能直接返回Response对象，只能抛出异常
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未授权访问",
            headers={"WWW-Authenticate": "Basic"},
        )
    return user

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """登录页面"""
    # 如果用户已登录，直接跳转到仪表盘
    if request.session.get("user"):
        return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login(request: Request, password: str = Form(...)):
    """处理登录请求"""
    if verify_password(password):
        # 设置会话
        request.session["user"] = "admin"
        return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    else:
        # 登录失败，返回错误信息
        return templates.TemplateResponse(
            "login.html", 
            {"request": request, "error": "密码错误"}
        )

@router.get("/logout")
async def logout(request: Request):
    """处理登出请求"""
    # 清除会话
    request.session.clear()
    return RedirectResponse(url="/login") 