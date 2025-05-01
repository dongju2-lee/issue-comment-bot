import httpx
from typing import Optional, List, Dict, Any

from utils.config import settings
from utils.logger import logger

class GitHubService:
    def __init__(self):
        self.api_url = settings.GITHUB_API_URL
        self.token = settings.GITHUB_TOKEN
        
        if not self.token:
            logger.warning("GitHub token is not set. API calls may be rate limited.")
    
    async def post_comment(self, repo_name: str, issue_number: int, comment: str) -> bool:
        """GitHub 이슈에 댓글을 작성합니다."""
        try:
            logger.info(f"Posting comment to {repo_name}#{issue_number}")
            
            url = f"{self.api_url}/repos/{repo_name}/issues/{issue_number}/comments"
            headers = {
                "Accept": "application/vnd.github.v3+json"
            }
            
            if self.token:
                headers["Authorization"] = f"token {self.token}"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json={"body": comment},
                    headers=headers
                )
                response.raise_for_status()
                
            logger.info(f"Comment posted successfully to {repo_name}#{issue_number}")
            return True
        except Exception as e:
            logger.error(f"Error posting comment to GitHub: {str(e)}")
            return False
            
    async def get_issues(self, repo_name: str, since_id: int = 0, limit: int = 100, state: str = "open") -> List[Dict[str, Any]]:
        """GitHub 레포지토리에서 이슈 목록을 가져옵니다.
        
        Args:
            repo_name: 레포지토리 이름 (형식: owner/repo)
            since_id: 이 ID보다 큰 이슈만 가져옵니다 (기본값: 0, 모든 이슈)
            limit: 가져올 최대 이슈 수 (기본값: 100)
            state: 이슈 상태 ("open", "closed", "all") (기본값: "open")
            
        Returns:
            이슈 목록 (딕셔너리 리스트)
        """
        try:
            logger.info(f"Fetching issues from {repo_name} (since_id: {since_id})")
            
            url = f"{self.api_url}/repos/{repo_name}/issues"
            headers = {
                "Accept": "application/vnd.github.v3+json"
            }
            
            if self.token:
                headers["Authorization"] = f"token {self.token}"
            
            params = {
                "state": state,
                "per_page": min(100, limit),  # GitHub API는 페이지당 최대 100개 항목 제한
                "sort": "created",
                "direction": "desc"  # 최신 이슈부터 가져오기
            }
            
            issues = []
            page = 1
            
            async with httpx.AsyncClient() as client:
                while len(issues) < limit:
                    params["page"] = page
                    response = await client.get(
                        url,
                        params=params,
                        headers=headers,
                        timeout=30.0  # 타임아웃 30초
                    )
                    response.raise_for_status()
                    
                    page_issues = response.json()
                    if not page_issues:
                        break  # 더 이상 이슈가 없음
                    
                    # since_id보다 큰 이슈만 필터링
                    filtered_issues = [issue for issue in page_issues 
                                      if issue.get("id", 0) > since_id 
                                      and not issue.get("pull_request")]  # PR 제외
                    
                    issues.extend(filtered_issues)
                    
                    # 더 이상 가져올 수 없는 경우 중단
                    if len(page_issues) < params["per_page"]:
                        break
                    
                    page += 1
                    
                    # 요청 한도에 도달한 경우
                    if len(issues) >= limit:
                        issues = issues[:limit]
                        break
            
            logger.info(f"Fetched {len(issues)} issues from {repo_name}")
            return issues
        
        except Exception as e:
            logger.error(f"Error fetching issues from GitHub: {str(e)}")
            return []