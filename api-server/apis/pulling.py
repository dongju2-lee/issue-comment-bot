from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
import os
import time
import json
import asyncio
import uuid
from typing import Dict, List, Any
from datetime import datetime

from utils.config import settings
from utils.logger import logger
from services.github import GitHubService
from services.queue import FileQueue

router = APIRouter()
queue = FileQueue()
github_service = GitHubService()

# 마지막으로 처리한 이슈의 ID를 저장할 딕셔너리
last_processed_issue_ids = {}

async def pull_issues_from_repo(repo_name: str) -> List[Dict[str, Any]]:
    """특정 레포지토리에서 새로운 이슈들을 가져옵니다."""
    try:
        # 해당 레포지토리에서 마지막으로 처리한 이슈 ID 가져오기
        last_id = last_processed_issue_ids.get(repo_name, 0)
        
        # GitHub API를 통해 이슈 가져오기
        issues = await github_service.get_issues(repo_name, since_id=last_id)
        
        if issues and len(issues) > 0:
            # 가장 최근 이슈의 ID를 저장
            newest_id = max(issue.get("id", 0) for issue in issues)
            last_processed_issue_ids[repo_name] = newest_id
            logger.info(f"레포지토리 {repo_name}에서 {len(issues)}개의 새 이슈를 가져왔습니다. 마지막 ID: {newest_id}")
            return issues
        
        logger.info(f"레포지토리 {repo_name}에서 새 이슈가 없습니다.")
        return []
    
    except Exception as e:
        logger.error(f"레포지토리 {repo_name}에서 이슈를 가져오는 중 오류 발생: {str(e)}")
        return []

async def pull_issues_task():
    """모든 레포지토리에서 이슈를 주기적으로 가져오는 백그라운드 작업"""
    logger.info("이슈 풀링 작업 시작")
    
    # 환경 변수에서 레포지토리 목록 가져오기
    repo_list = [repo.strip() for repo in settings.PULLING_REPO_LIST.split(',') if repo.strip()]
    
    if not repo_list:
        logger.warning("풀링할 레포지토리가 설정되지 않았습니다. 풀링 작업을 종료합니다.")
        return
    
    logger.info(f"다음 레포지토리에서 이슈 풀링 예정: {', '.join(repo_list)}")
    logger.info(f"풀링 간격: {settings.PULLING_INTERVAL}초")
    
    while True:
        try:
            pull_start_time = time.time()
            total_issues_pulled = 0
            
            for repo_name in repo_list:
                if not repo_name:
                    continue
                
                # 레포지토리에서 이슈 가져오기
                issues = await pull_issues_from_repo(repo_name)
                total_issues_pulled += len(issues)
                
                # 가져온 이슈들을 큐에 추가
                for issue in issues:
                    # 이슈 데이터를 웹훅 페이로드 형식으로 변환
                    payload = {
                        "action": "opened",
                        "issue": issue,
                        "repository": {
                            "full_name": repo_name
                        },
                        "pulled_at": datetime.now().isoformat(),
                        "source": "pull"
                    }
                    
                    # 작업을 큐에 추가
                    await queue.enqueue(payload)
                    logger.info(f"이슈 #{issue.get('number')} ({repo_name})가 큐에 추가되었습니다.")
            
            pull_duration = time.time() - pull_start_time
            if total_issues_pulled > 0:
                logger.info(f"풀링 작업 완료: {total_issues_pulled}개의 이슈를 {pull_duration:.2f}초 동안 처리했습니다.")
            else:
                logger.info(f"풀링 작업 완료: 새로운 이슈가 없습니다. 소요 시간: {pull_duration:.2f}초")
            
            # 설정된 간격만큼 대기
            logger.info(f"다음 풀링까지 {settings.PULLING_INTERVAL}초 대기 중...")
            await asyncio.sleep(settings.PULLING_INTERVAL)
        
        except Exception as e:
            logger.error(f"이슈 풀링 중 오류 발생: {str(e)}")
            logger.info("1분 후 풀링을 재시도합니다.")
            await asyncio.sleep(60)  # 오류 발생시 1분 후 재시도

@router.post("/pull/start", status_code=200)
async def start_pulling(background_tasks: BackgroundTasks):
    """이슈 풀링 작업을 시작합니다."""
    try:
        # 레포지토리 목록 확인
        repo_list = [repo.strip() for repo in settings.PULLING_REPO_LIST.split(',') if repo.strip()]
        if not repo_list:
            return {
                "status": "error", 
                "message": "PULLING_REPO_LIST 환경 변수가 설정되지 않았습니다. 풀링할 레포지토리를 설정해주세요."
            }
        
        background_tasks.add_task(pull_issues_task)
        return {
            "status": "started", 
            "message": f"이슈 풀링 작업이 시작되었습니다. 레포지토리: {', '.join(repo_list)}"
        }
    except Exception as e:
        logger.error(f"풀링 작업 시작 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pull/manual", status_code=200)
async def manual_pull():
    """모든 레포지토리에서 수동으로 이슈를 가져옵니다."""
    try:
        # 환경 변수에서 레포지토리 목록 가져오기
        repo_list = [repo.strip() for repo in settings.PULLING_REPO_LIST.split(',') if repo.strip()]
        
        if not repo_list:
            return {
                "status": "error", 
                "message": "PULLING_REPO_LIST 환경 변수가 설정되지 않았습니다. 풀링할 레포지토리를 설정해주세요."
            }
        
        total_issues = 0
        manual_pull_start_time = time.time()
        
        for repo_name in repo_list:
            if not repo_name:
                continue
            
            # 레포지토리에서 이슈 가져오기 (최근 50개만)
            logger.info(f"레포지토리 {repo_name}에서 수동으로 이슈를 가져오는 중...")
            issues = await github_service.get_issues(repo_name, limit=50)
            
            # 가져온 이슈들을 큐에 추가
            for issue in issues:
                # 이슈 데이터를 웹훅 페이로드 형식으로 변환
                payload = {
                    "action": "opened",
                    "issue": issue,
                    "repository": {
                        "full_name": repo_name
                    },
                    "pulled_at": datetime.now().isoformat(),
                    "source": "manual_pull"
                }
                
                # 작업을 큐에 추가
                await queue.enqueue(payload)
            
            total_issues += len(issues)
            logger.info(f"레포지토리 {repo_name}에서 {len(issues)}개의 이슈를 수동으로 가져왔습니다.")
        
        manual_pull_duration = time.time() - manual_pull_start_time
        
        return {
            "status": "success",
            "repos_processed": len(repo_list),
            "repos": repo_list,
            "total_issues_pulled": total_issues,
            "duration_seconds": round(manual_pull_duration, 2)
        }
    
    except Exception as e:
        logger.error(f"수동 풀링 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pull/status", status_code=200)
async def get_pulling_status():
    """현재 풀링 상태를 반환합니다."""
    repo_list = [repo.strip() for repo in settings.PULLING_REPO_LIST.split(',') if repo.strip()]
    
    return {
        "pulling_enabled": len(repo_list) > 0,
        "pulling_repos": repo_list,
        "interval_seconds": settings.PULLING_INTERVAL,
        "last_processed_issues": last_processed_issue_ids
    }
