from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # LLM 검색 API 설정
    SEARCH_API_URL: str = "http://localhost:8000/search"
    
    # GitHub API 설정
    GITHUB_API_URL: str = "https://api.github.com"
    GITHUB_TOKEN: str = ""
    
    # 작업 폴더 설정
    TASKS_DIR: str = "file-queue"
    PENDING_DIR: str = "file-queue/waiting-list"
    COMPLETED_DIR: str = "file-queue/completed"
    FAILED_DIR: str = "file-queue/failed"
    
    # 작업 확인 주기 (초)
    QUEUE_WORKING_INTERVAL: int = 30
    
    # GitHub 레포지토리 풀링 설정
    PULLING_REPO_LIST: str = ""
    PULLING_INTERVAL: int = 300
    
    # 시스템 모드 설정
    # 가능한 값: PUSH, PULL, DUAL
    SYSTEM_MODE: str = "PUSH"
    
    class Config:
        env_file = ".env"

settings = Settings()