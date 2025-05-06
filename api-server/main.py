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

# 공통 라우터 등록 (모드에 관계없이 항상 사용)
app.include_router(admin.router)
app.include_router(task.router)
app.include_router(ping.router)

# 시스템 모드에 따라 라우터 조건부 등록
if settings.SYSTEM_MODE in ["PUSH", "DUAL"]:
    # PUSH 또는 DUAL 모드일 때만 웹훅 라우터 등록
    app.include_router(webhook.router)
    logger.info(f"웹훅 라우터가 등록되었습니다 (SYSTEM_MODE: {settings.SYSTEM_MODE})")
else:
    logger.info(f"PULL 모드에서는 웹훅 라우터가 비활성화됩니다 (SYSTEM_MODE: {settings.SYSTEM_MODE})")

if settings.SYSTEM_MODE in ["PULL", "DUAL"]:
    # PULL 또는 DUAL 모드일 때만 풀링 라우터 등록
    app.include_router(pulling.router, tags=["Pulling"])
    logger.info(f"풀링 라우터가 등록되었습니다 (SYSTEM_MODE: {settings.SYSTEM_MODE})")
else:
    logger.info(f"PUSH 모드에서는 풀링 라우터가 비활성화됩니다 (SYSTEM_MODE: {settings.SYSTEM_MODE})")

# 작업 처리기
task_processor = TaskProcessor()

@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행되는 이벤트 핸들러."""
    logger.info("Starting GitHub Issue Comment Bot...")
    logger.info(f"시스템 모드: {settings.SYSTEM_MODE}")
    
    # 백그라운드에서 작업 처리기 시작
    asyncio.create_task(task_processor.start())
    
    # PULL 또는 DUAL 모드이고 풀링 레포지토리 목록이 설정된 경우, 풀링 작업 자동 시작
    if settings.SYSTEM_MODE in ["PULL", "DUAL"] and settings.PULLING_REPO_LIST and settings.PULLING_REPO_LIST.strip():
        repo_list = [repo.strip() for repo in settings.PULLING_REPO_LIST.split(',') if repo.strip()]
        if repo_list:
            logger.info(f"Auto-starting issue pulling for repositories: {', '.join(repo_list)}")
            logger.info(f"Pulling interval set to {settings.PULLING_INTERVAL} seconds")
            asyncio.create_task(pulling.pull_issues_task())
        else:
            logger.info("No repositories configured for pulling. Pulling feature is disabled.")
    elif settings.SYSTEM_MODE == "PUSH":
        logger.info("PUSH 모드에서는 풀링 기능이 비활성화됩니다.")

@app.on_event("shutdown")
def shutdown_event():
    """애플리케이션 종료 시 실행되는 이벤트 핸들러."""
    logger.info("Shutting down GitHub Issue Comment Bot...")
    task_processor.stop()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)