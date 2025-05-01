from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime

# 웹훅 페이로드 관련 모델
class GitHubIssue(BaseModel):
    number: int
    title: str
    body: Optional[str] = None
    user: Optional[Dict[str, Any]] = None

class GitHubRepository(BaseModel):
    full_name: str
    name: str
    owner: Dict[str, Any]

class GitHubWebhookPayload(BaseModel):
    action: str
    issue: GitHubIssue
    repository: GitHubRepository
    sender: Dict[str, Any]

# 작업 관련 모델
class TaskItem(BaseModel):
    task_id: str
    payload: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.now)

class CompletedTask(BaseModel):
    task_id: str
    repository: str  # 깃헙 주소 (full_name)
    requester: str   # 요청자 (작성자 로그인명)
    requested_at: datetime  # 요청 시간
    issue_title: str
    issue_body: str
    llm_response: str
    completed_at: datetime = Field(default_factory=datetime.now)
    status: str = "success"

# API 응답 모델
class WebhookResponse(BaseModel):
    status: str
    task_id: Optional[str] = None
    reason: Optional[str] = None

class SystemStatus(BaseModel):
    status: str
    pending_tasks: int
    completed_tasks: int
    failed_tasks: int

class RetryResponse(BaseModel):
    status: str
    count: int