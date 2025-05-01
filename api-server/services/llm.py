import httpx
from typing import Dict, Any, Optional

from utils.config import settings
from utils.logger import logger

class LLMService:
    def __init__(self):
        self.api_url = settings.SEARCH_API_URL
    
    async def generate_response(self, query: str) -> Optional[Dict[str, Any]]:
        """LLM API를 호출하여 응답을 생성합니다."""
        try:
            logger.info(f"Calling LLM API with query: {query[:2000]}...")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    json={"query": query},
                    timeout=60.0  # LLM은 시간이 걸릴 수 있으므로 타임아웃 길게 설정
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error calling LLM API: {str(e)}")
            return None
    
    def craft_issue_query(self, issue_title: str, 
                         issue_body: str) -> str:
        """이슈 정보를 바탕으로 LLM에게 보낼 쿼리를 생성합니다."""
        # LLM에게 보낼 향상된 쿼리 생성
        query = f"""질문이 들어온 제목과 내용입니다.

제목: 
{issue_title}

내용:
{issue_body}

"""
        return query