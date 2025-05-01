import asyncio
import os
from fastapi import FastAPI
import uvicorn

from utils.config import settings
from utils.logger import logger
from services.processor import TaskProcessor
from apis import webhook, admin, task, ping, pulling

# 디렉토리 생성
os.makedirs(settings.PENDING_DIR, exist_ok=True)
os.makedirs(settings.COMPLETED_DIR, exist_ok=True)
os.makedirs(settings.FAILED_DIR, exist_ok=True)

# FastAPI 애플리케이션 생성
app = FastAPI(title="GitHub Issue Comment Bot")

# 모든 라우터 등록 (웹훅 및 풀링 기능 모두 제공)
app.include_router(webhook.router)
app.include_router(admin.router)
app.include_router(task.router)
app.include_router(ping.router)
app.include_router(pulling.router, tags=["Pulling"])

# 작업 처리기
task_processor = TaskProcessor()

@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행되는 이벤트 핸들러."""
    logger.info("Starting GitHub Issue Comment Bot...")
    
    # 백그라운드에서 작업 처리기 시작
    asyncio.create_task(task_processor.start())
    
    # 풀링 레포지토리 목록이 설정된 경우, 풀링 작업 자동 시작
    if settings.PULLING_REPO_LIST and settings.PULLING_REPO_LIST.strip():
        repo_list = [repo.strip() for repo in settings.PULLING_REPO_LIST.split(',') if repo.strip()]
        if repo_list:
            logger.info(f"Auto-starting issue pulling for repositories: {', '.join(repo_list)}")
            logger.info(f"Pulling interval set to {settings.PULLING_INTERVAL} seconds")
            asyncio.create_task(pulling.pull_issues_task())
        else:
            logger.info("No repositories configured for pulling. Pulling feature is disabled.")
    else:
        logger.info("PULLING_REPO_LIST is not set. Pulling feature is disabled.")

@app.on_event("shutdown")
def shutdown_event():
    """애플리케이션 종료 시 실행되는 이벤트 핸들러."""
    logger.info("Shutting down GitHub Issue Comment Bot...")
    task_processor.stop()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)