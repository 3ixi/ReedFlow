import os
import json
import uuid
import zlib
import base64
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pydantic import BaseModel, Field

# 工作流存储位置
WORKFLOWS_FILE = "app/data/workflows.json"

class WorkflowModule(BaseModel):
    """工作流模块"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    name: str
    config: Dict[str, Any] = {}
    position: Dict[str, float] = {"x": 0, "y": 0}

class Workflow(BaseModel):
    """工作流模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    modules: List[WorkflowModule] = []
    connections: List[Dict[str, Any]] = []
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    enabled: bool = False
    cron: Optional[str] = None
    last_run: Optional[str] = None
    last_result: Optional[str] = None

def init_workflows():
    """初始化工作流存储"""
    if not os.path.exists(WORKFLOWS_FILE):
        with open(WORKFLOWS_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)

def get_all_workflows() -> List[Dict[str, Any]]:
    """获取所有工作流"""
    init_workflows()
    with open(WORKFLOWS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_workflow_by_id(workflow_id: str) -> Optional[Dict[str, Any]]:
    """根据ID获取工作流"""
    workflows = get_all_workflows()
    for workflow in workflows:
        if workflow.get('id') == workflow_id:
            return workflow
    return None

def save_workflow(workflow: Dict[str, Any]) -> Dict[str, Any]:
    """保存工作流"""
    workflows = get_all_workflows()
    
    # 设置更新时间
    workflow['updated_at'] = datetime.now().isoformat()
    
    # 检查是否存在，进行更新或添加
    existing_index = None
    for i, w in enumerate(workflows):
        if w.get('id') == workflow.get('id'):
            existing_index = i
            break
    
    if existing_index is not None:
        workflows[existing_index] = workflow
    else:
        # 如果是新工作流，确保有ID和创建时间
        if 'id' not in workflow or not workflow['id']:
            workflow['id'] = str(uuid.uuid4())
        if 'created_at' not in workflow:
            workflow['created_at'] = datetime.now().isoformat()
        workflows.append(workflow)
    
    # 保存到文件
    with open(WORKFLOWS_FILE, 'w', encoding='utf-8') as f:
        json.dump(workflows, f, ensure_ascii=False, indent=2)
    
    return workflow

def delete_workflow(workflow_id: str) -> bool:
    """删除工作流"""
    workflows = get_all_workflows()
    filtered_workflows = [w for w in workflows if w.get('id') != workflow_id]
    
    if len(filtered_workflows) == len(workflows):
        return False  # 没有找到要删除的工作流
        
    # 保存到文件
    with open(WORKFLOWS_FILE, 'w', encoding='utf-8') as f:
        json.dump(filtered_workflows, f, ensure_ascii=False, indent=2)
    
    return True

def update_workflow_status(workflow_id: str, enabled: bool) -> bool:
    """更新工作流启用状态"""
    workflow = get_workflow_by_id(workflow_id)
    if not workflow:
        return False
    
    workflow['enabled'] = enabled
    save_workflow(workflow)
    return True

def update_workflow_result(workflow_id: str, result: str) -> bool:
    """更新工作流执行结果"""
    workflow = get_workflow_by_id(workflow_id)
    if not workflow:
        return False
    
    workflow['last_run'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    workflow['last_result'] = result
    save_workflow(workflow)
    return True 

def export_workflow(workflow_id: str) -> Tuple[Optional[bytes], Optional[str]]:
    """
    导出工作流，使用zlib压缩
    
    Args:
        workflow_id: 工作流ID
        
    Returns:
        Tuple[bytes, str]: 压缩后的工作流数据和文件名，如果工作流不存在则返回(None, None)
    """
    workflow = get_workflow_by_id(workflow_id)
    if not workflow:
        return None, None
    
    # 将工作流转换为JSON字符串
    workflow_json = json.dumps(workflow, ensure_ascii=False)
    
    # 使用zlib压缩
    json_bytes = workflow_json.encode('utf-8')
    compressed_data = zlib.compress(json_bytes, level=9)
    
    # 文件名使用英文和ID，避免编码问题
    safe_name = workflow.get("id", "workflow")
    filename = f"workflow_{safe_name}.rfj"
    
    return compressed_data, filename

def import_workflow(data: bytes) -> Optional[Dict[str, Any]]:
    """
    导入工作流，解压缩zlib压缩的数据
    
    Args:
        data: 压缩的工作流数据
        
    Returns:
        Dict[str, Any]: 解压后的工作流数据，如果解压失败则返回None
    """
    try:
        # 使用zlib解压
        decompressed_data = zlib.decompress(data)
        
        # 解析JSON
        workflow_data = json.loads(decompressed_data.decode('utf-8'))
        
        # 验证工作流数据
        if not isinstance(workflow_data, dict) or "name" not in workflow_data:
            return None
        
        # 生成新的ID，避免冲突
        workflow_data["id"] = str(uuid.uuid4())
        
        # 保存工作流
        return save_workflow(workflow_data)
    except Exception as e:
        print(f"导入工作流失败: {e}")
        return None