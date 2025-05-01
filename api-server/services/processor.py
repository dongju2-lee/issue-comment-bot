import asyncio
from typing import Optional

from utils.logger import logger
from utils.config import settings
from models.schemas import CompletedTask
from services.queue import FileQueue
from services.github import GitHubService
from services.llm import LLMService
from datetime import datetime

class TaskProcessor:
    def __init__(self):
        self.queue = FileQueue()
        self.github_service = GitHubService()
        self.llm_service = LLMService()
        self.running = False
    
    async def process_task(self):
        """큐에서 하나의 작업을 처리합니다."""
        # 작업 가져오기
        task = await self.queue.dequeue()
        
        if not task:
            return False
        
        try:
            # 이슈 정보 추출
            payload = task.payload
            issue = payload.get("issue", {})
            repo = payload.get("repository", {})
            
            issue_number = issue.get("number")
            repo_name = repo.get("full_name")
            issue_title = issue.get("title", "")
            issue_body = issue.get("body", "")
            issue_user = issue.get("user", {}).get("login", "Anonymous")
            
            # LLM 쿼리 생성
            query = self.llm_service.craft_issue_query(
                issue_title=issue_title,
                issue_body=issue_body
            )
            
            # LLM API 호출
            llm_response = await self.llm_service.generate_response(query)
            
            if not llm_response:
                await self.queue.fail_task(
                    task.task_id, 
                    "Failed to get response from LLM API",
                    payload
                )
                return False
            logger.info(f"llm호출하여 얻은 응답입니다: {llm_response}")
            # 댓글 추출
            comment = llm_response.get("summary", "Sorry, I couldn't process your issue at this time.")
            
            # GitHub에 댓글 작성
            success = await self.github_service.post_comment(repo_name, issue_number, comment)
            
            if not success:
                await self.queue.fail_task(
                    task.task_id, 
                    "Failed to post comment to GitHub",
                    payload
                )
                return False
            
            # 작업 완료 처리
            completed_task = CompletedTask(
                task_id=task.task_id,
                repository=repo_name,
                requester=issue_user,
                requested_at=datetime.now(),  # 현재 시간으로 요청 시간 대체
                issue_title=issue_title,
                issue_body=issue_body,
                llm_response=comment,
                status="success"
            )
            
            await self.queue.complete_task(task.task_id, completed_task)
            return True
            
        except Exception as e:
            logger.error(f"Error processing task {task.task_id}: {str(e)}")
            await self.queue.fail_task(
                task.task_id, 
                str(e),
                task.payload if task else None
            )
            return False
    
    async def start(self):
        """작업 처리 루프를 시작합니다."""
        self.running = True
        
        while self.running:
            try:
                logger.info("Checking for pending tasks...")
                processed = await self.process_task()
                
                if not processed:
                    logger.info("No pending tasks found. Waiting...")
                    await asyncio.sleep(settings.QUEUE_WORKING_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in task processor: {str(e)}")
                await asyncio.sleep(settings.QUEUE_WORKING_INTERVAL)
    
    def stop(self):
        """작업 처리 루프를 중지합니다."""
        self.running = False