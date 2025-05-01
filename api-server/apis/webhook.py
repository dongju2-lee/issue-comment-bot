from fastapi import APIRouter, Body  
from typing import Dict, Any

from utils.logger import logger
from models.schemas import WebhookResponse
from services.queue import FileQueue

router = APIRouter()
queue = FileQueue()

@router.post("/webhook", response_model=WebhookResponse)
async def github_webhook(payload: Dict[str, Any] = Body(...)) -> WebhookResponse:
    """GitHub 웹훅을 처리합니다."""
    logger.info(f"Received webhook: issue {payload.get('issue', {}).get('number')} in repo {payload.get('repository', {}).get('full_name')}")
    
    # 이슈 생성 이벤트만 처리
    if payload.get("action") != "opened":
        logger.info(f"Ignoring action: {payload.get('action')}")
        return WebhookResponse(
            status="ignored", 
            reason=f"Action {payload.get('action')} is not handled"
        )
    
    # 작업을 큐에 추가
    task_id = await queue.enqueue(payload)
    
    return WebhookResponse(status="queued", task_id=task_id)