import os
import json
import glob
from datetime import datetime
import uuid
from typing import Dict, Any, Optional, List

from utils.config import settings
from utils.logger import logger
from models.schemas import TaskItem, CompletedTask

class FileQueue:
    def __init__(self):
        # 디렉토리 생성
        os.makedirs(settings.PENDING_DIR, exist_ok=True)
        os.makedirs(settings.COMPLETED_DIR, exist_ok=True)
        os.makedirs(settings.FAILED_DIR, exist_ok=True)
    
    async def enqueue(self, payload: Dict[str, Any]) -> str:
        """작업을 큐에 추가합니다."""
        # 작업 ID 생성
        timestamp = int(datetime.now().timestamp() * 1000)
        issue_id = payload.get("issue", {}).get("number", "unknown")
        repo_name = payload.get("repository", {}).get("full_name", "unknown").replace("/", "-")
        task_id = f"{timestamp}_{repo_name}_{issue_id}.json"
        
        # 작업 파일 저장
        task_path = os.path.join(settings.PENDING_DIR, task_id)
        
        try:
            with open(task_path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            logger.info(f"Task enqueued: {task_id}")
            return task_id
        except Exception as e:
            logger.error(f"Failed to enqueue task: {str(e)}")
            raise
    
    async def dequeue(self) -> Optional[TaskItem]:
        """큐에서 가장 오래된 작업을 가져옵니다."""
        # 대기 중인 작업 파일 찾기 (생성 시간순으로 정렬)
        task_files = sorted(glob.glob(f"{settings.PENDING_DIR}/*.json"))
        
        if not task_files:
            return None
        
        # 가장 오래된 작업 파일 처리
        task_file = task_files[0]
        task_id = os.path.basename(task_file)
        
        try:
            # 파일 읽기
            with open(task_file, 'r', encoding='utf-8') as f:
                payload = json.load(f)
                
            return TaskItem(
                task_id=task_id,
                payload=payload,
                created_at=datetime.now()
            )
        except Exception as e:
            logger.error(f"Failed to dequeue task {task_id}: {str(e)}")
            return None
    
    async def complete_task(self, task_id: str, task_data: CompletedTask) -> bool:
        """작업을 완료 처리합니다."""
        # 작업 파일 경로
        task_file = os.path.join(settings.PENDING_DIR, task_id)
        completed_file = os.path.join(settings.COMPLETED_DIR, "completed_tasks.json")

        try:
            # 디렉토리 확인 및 생성
            os.makedirs(settings.COMPLETED_DIR, exist_ok=True)

            # 기존 완료 기록 읽기
            completed_data = []
            if os.path.exists(completed_file):
                try:
                    with open(completed_file, 'r', encoding='utf-8') as f:
                        completed_data = json.load(f)
                except json.JSONDecodeError:
                    logger.warning("Could not parse completed_tasks.json. Starting with empty list.")
                    completed_data = []

            # datetime 객체를 ISO 형식 문자열로 변환하여 추가
            task_dict = task_data.model_dump()
            # datetime 객체 처리
            for key, value in task_dict.items():
                if isinstance(value, datetime):
                    task_dict[key] = value.isoformat()

            # 완료 정보 추가
            completed_data.append(task_dict)

            # 완료 파일 업데이트 (atomic write)
            temp_file = f"{completed_file}.temp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(completed_data, f, ensure_ascii=False, indent=2)

            os.replace(temp_file, completed_file)

            # 처리 완료된 작업 파일 삭제
            if os.path.exists(task_file):
                os.remove(task_file)

            logger.info(f"Task completed: {task_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to complete task {task_id}: {str(e)}")
            return False
    
    async def fail_task(self, task_id: str, error: str, payload: Optional[Dict[str, Any]] = None) -> bool:
        """작업을 실패 처리합니다."""
        # 작업 파일 경로
        task_file = os.path.join(settings.PENDING_DIR, task_id)
        failed_file = os.path.join(settings.FAILED_DIR, task_id)
        
        try:
            # 실패 정보 작성
            error_info = {
                "task_id": task_id,
                "error": str(error),
                "timestamp": datetime.now().isoformat()
            }
            
            if payload:
                error_info["original_payload"] = payload
            
            # 실패 파일 작성
            with open(failed_file, 'w', encoding='utf-8') as f:
                json.dump(error_info, f, ensure_ascii=False, indent=2)
            
            # 원본 파일 삭제
            if os.path.exists(task_file):
                os.remove(task_file)
                
            logger.error(f"Task failed: {task_id} - {error}")
            return True
        except Exception as e:
            logger.error(f"Failed to mark task as failed {task_id}: {str(e)}")
            return False
        
    async def retry_failed_tasks(self) -> int:
        """실패한 작업을 재시도합니다."""
        failed_files = glob.glob(f"{settings.FAILED_DIR}/*.json")
        
        if not failed_files:
            return 0
        
        retried_count = 0
        
        for failed_file in failed_files:
            try:
                with open(failed_file, 'r', encoding='utf-8') as f:
                    failed_data = json.load(f)
                
                # 원본 페이로드가 있는 경우에만 재시도
                if "original_payload" in failed_data:
                    task_id = failed_data.get("task_id", f"retry_{int(datetime.now().timestamp() * 1000)}.json")
                    new_task_path = os.path.join(settings.PENDING_DIR, task_id)
                    
                    with open(new_task_path, 'w', encoding='utf-8') as f:
                        json.dump(failed_data["original_payload"], f, ensure_ascii=False, indent=2)
                    
                    # 실패 파일 삭제
                    os.remove(failed_file)
                    retried_count += 1
            except Exception as e:
                logger.error(f"Error retrying failed task {failed_file}: {str(e)}")
        
        return retried_count
    
    async def get_status(self) -> Dict[str, int]:
        """큐 상태를 반환합니다."""
        pending_count = len(glob.glob(f"{settings.PENDING_DIR}/*.json"))
        failed_count = len(glob.glob(f"{settings.FAILED_DIR}/*.json"))
        
        # 완료된 작업 수 확인
        completed_count = 0
        completed_file = os.path.join(settings.COMPLETED_DIR, "completed_tasks.json")
        if os.path.exists(completed_file):
            try:
                with open(completed_file, 'r', encoding='utf-8') as f:
                    completed_data = json.load(f)
                    completed_count = len(completed_data)
            except:
                pass
        
        return {
            "pending_tasks": pending_count,
            "completed_tasks": completed_count,
            "failed_tasks": failed_count
        }