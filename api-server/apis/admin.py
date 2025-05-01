from fastapi import APIRouter
from typing import Dict, Any

from models.schemas import SystemStatus, RetryResponse
from services.queue import FileQueue

router = APIRouter()
queue = FileQueue()

@router.get("/status", response_model=SystemStatus)
async def get_status() -> SystemStatus:
    """시스템 상태를 반환합니다."""
    status_data = await queue.get_status()
    
    return SystemStatus(
        status="running",
        **status_data
    )

@router.post("/retry", response_model=RetryResponse)
async def retry_failed_tasks() -> RetryResponse:
    """실패한 작업을 재시도합니다."""
    retried_count = await queue.retry_failed_tasks()
    
    if retried_count == 0:
        return RetryResponse(status="no_failed_tasks", count=0)
    
    return RetryResponse(status="retried", count=retried_count)