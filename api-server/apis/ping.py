from fastapi import APIRouter, Request
from typing import Dict, Any

from utils.logger import logger
from models.schemas import WebhookResponse
from services.queue import FileQueue

router = APIRouter()

@router.get("/ping")
async def github_webhook():
    """헬스체크를 처리합니다."""
    logger.info("헬스체크")
    

    return {"pong"}