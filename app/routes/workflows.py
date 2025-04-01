from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
import json

from app.routes.auth import get_current_user
from app.models.workflow import get_all_workflows, get_workflow_by_id, update_workflow_result
from app.models.modules import execute_workflow
from app.utils.scheduler import get_next_run_time, manual_run_workflow
from app.models.log import log_workflow_action

router = APIRouter(prefix="/api/workflows", tags=["workflows"])

@router.get("/")
async def list_workflows(user: str = Depends(get_current_user)) -> List[Dict[str, Any]]:
    """获取所有工作流列表"""
    workflows = get_all_workflows()
    
    # 添加下次运行时间
    for workflow in workflows:
        workflow["next_run"] = get_next_run_time(workflow.get("id", ""))
    
    return workflows

@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str, user: str = Depends(get_current_user)) -> Dict[str, Any]:
    """获取指定ID的工作流"""
    workflow = get_workflow_by_id(workflow_id)
    
    if not workflow:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    # 添加下次运行时间
    workflow["next_run"] = get_next_run_time(workflow.get("id", ""))
    
    return workflow

@router.post("/{workflow_id}/run")
async def run_workflow(workflow_id: str, user: str = Depends(get_current_user)):
    """手动运行工作流"""
    workflow = get_workflow_by_id(workflow_id)
    
    if not workflow:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    # 记录手动运行日志
    log_workflow_action(workflow_id, "info", f"用户 '{user}' 手动触发工作流运行")
    
    # 触发工作流执行
    manual_run_workflow(workflow_id)
    
    return {"message": "工作流已触发执行"}

@router.get("/{workflow_id}/modules")
async def get_workflow_modules(workflow_id: str, user: str = Depends(get_current_user)) -> List[Dict[str, Any]]:
    """获取工作流中的所有模块"""
    workflow = get_workflow_by_id(workflow_id)
    
    if not workflow:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    return workflow.get("modules", []) 