from fastapi import APIRouter
from typing import List
import glob
import os
import json

from models.schemas import TaskItem
from utils.config import settings
from utils.logger import logger
from fastapi import HTTPException
from fastapi import Body
from services.queue import FileQueue
from models.schemas import CompletedTask

router = APIRouter()

@router.get("/tasks/pending", response_model=List[TaskItem])
async def get_pending_tasks():
    """작업 대기 중인 JSON 파일 리스트를 반환합니다."""
    task_files = sorted(glob.glob(f"{settings.PENDING_DIR}/*.json"))
    tasks = []
    for task_file in task_files:
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                payload = json.load(f)
            task_id = os.path.basename(task_file)
            tasks.append(TaskItem(task_id=task_id, payload=payload))
        except Exception as e:
            logger.error(f"Failed to read pending task {task_file}: {str(e)}")
    return tasks

@router.get("/tasks/completed", response_model=List[CompletedTask])
async def get_completed_tasks():
    """작업 완료된 JSON 리스트를 반환합니다."""
    completed_file = os.path.join(settings.COMPLETED_DIR, "completed_tasks.json")
    if not os.path.exists(completed_file):
        return []
    try:
        with open(completed_file, 'r', encoding='utf-8') as f:
            completed_data = json.load(f)
        return [CompletedTask(**item) for item in completed_data]
    except Exception as e:
        logger.error(f"Failed to read completed tasks: {str(e)}")
        return []
    
@router.get("/tasks/failed", response_model=List[dict])
async def get_failed_tasks():
    """실패한 작업 JSON 파일 리스트를 반환합니다."""
    failed_files = sorted(glob.glob(f"{settings.FAILED_DIR}/*.json"))
    failed_tasks = []
    for failed_file in failed_files:
        try:
            with open(failed_file, 'r', encoding='utf-8') as f:
                failed_data = json.load(f)
            failed_tasks.append(failed_data)
        except Exception as e:
            logger.error(f"Failed to read failed task {failed_file}: {str(e)}")
    return failed_tasks

@router.get("/tasks/{task_id}", response_model=dict)
async def get_task_detail(task_id: str):
    """특정 작업의 상세 정보를 반환합니다."""
    # 대기 중인 작업 확인
    pending_file = os.path.join(settings.PENDING_DIR, task_id)
    if os.path.exists(pending_file):
        with open(pending_file, 'r', encoding='utf-8') as f:
            return {"status": "pending", "data": json.load(f)}
    
    # 실패한 작업 확인
    failed_file = os.path.join(settings.FAILED_DIR, task_id)
    if os.path.exists(failed_file):
        with open(failed_file, 'r', encoding='utf-8') as f:
            return {"status": "failed", "data": json.load(f)}
    
    # 완료된 작업 확인
    completed_file = os.path.join(settings.COMPLETED_DIR, "completed_tasks.json")
    if os.path.exists(completed_file):
        with open(completed_file, 'r', encoding='utf-8') as f:
            completed_data = json.load(f)
            for task in completed_data:
                if task.get("task_id") == task_id:
                    return {"status": "completed", "data": task}
    
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")



@router.post("/tasks", response_model=dict)
async def create_task(payload: dict = Body(...)):
    """새 작업을 수동으로 추가합니다."""
    queue = FileQueue()  # services.queue에서 가져온 FileQueue 인스턴스
    task_id = await queue.enqueue(payload)
    return {"status": "queued", "task_id": task_id}