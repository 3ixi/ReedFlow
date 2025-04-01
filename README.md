# ReedFlow - 自动化工作流管理系统

ReedFlow是一个基于Python+FastAPI的自动化工作流管理系统，用户可以通过直观的Web界面创建、编辑和管理自动化工作流。系统提供了多种内置模块，用户可以拖拽模块创建工作流，设置定时任务，实现自动化操作。

## 主要功能

- 用户友好的Web界面，支持PC端和移动端
- 拖拽式工作流编辑器，直观设计工作流
- 丰富的内置模块：MD5加密、Base64编码/解码、查找/替换文本、URL编码/解码等
- HTTP/HTTP2请求模块，支持API调用
- JSON解析模块，自动提取数据
- 通知服务支持（邮件、WxPusher推送、PushPlus）
- 定时任务调度，支持Cron表达式
- 变量存储和引用机制
- 账号配置读写功能

## 技术栈

- 后端：Python 3.8+, FastAPI, Jinja2, APScheduler
- 前端：Tailwind CSS, JavaScript
- 数据存储：JSON文件（无需数据库）

## 安装与运行

### 环境要求

- Python 3.8或更高版本

### 安装步骤

1. 安装依赖包

```bash
pip install -r requirements.txt
```

2. 运行应用

```bash
python run.py
```

应用将在 `http://localhost:8000` 启动，默认管理密码为 `admin`

## 使用说明

1. 访问 `http://localhost:8000` 并使用管理密码登录
2. 点击"新建"按钮创建工作流
3. 从左侧拖拽模块到中间画布
4. 点击模块进行配置
5. 使用连接点连接各个模块，形成工作流
6. 设置工作流名称、描述和定时表达式
7. 保存工作流并设置为启用状态

## 定制开发

如果您需要添加新的模块类型，可以按照以下步骤进行：

1. 在 `app/models/modules.py` 文件中的 `MODULE_TYPES` 字典中添加新模块定义
2. 在 `execute_module` 函数中添加对应的模块执行逻辑
3. 重启应用即可使用新模块

## 特别说明

- 由于个人精力原因，部分模块功能没有开发完整，可能会出现报错，后续暂无修复计划，可以在`execute_module`函数中修改逻辑
