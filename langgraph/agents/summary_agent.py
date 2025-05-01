from typing import List, Dict, Any, TypedDict, Annotated
import operator
import os
from dotenv import load_dotenv
from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import HumanMessage, SystemMessage
import vertexai
from utils.logger import setup_logger

# 로거 설정
logger = setup_logger("summary_agent")

# .env 파일 로드
load_dotenv()

# 환경 변수 설정
VERTEX_PROJECT_ID = os.getenv("VERTEX_PROJECT_ID", "da-aiagent-dev")
VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")
VERTEX_LLM_MODEL = os.getenv("VERTEX_LLM_MODEL", "gemini-2.5-pro-preview-03-25")

# AgentState 타입 정의 - 그래프에서 사용
class AgentState(TypedDict):
    query: str
    search_results: Annotated[List[Dict[str, Any]], operator.add]
    summary: str

class SummaryAgent:
    """검색 결과를 요약하는 에이전트"""
    
    def __init__(self):
        # VertexAI 초기화
        vertexai.init(project=VERTEX_PROJECT_ID, location=VERTEX_LOCATION)
        
        # LLM 모델 초기화
        self.llm = ChatVertexAI(
            model=VERTEX_LLM_MODEL,
            temperature=0.0,
            max_tokens=65535,
            max_retries=2
        )
        logger.info("SummaryAgent initialized")
    
    async def summarize(self, query: str, search_results: List[Dict[str, Any]]) -> str:
        """검색 결과를 바탕으로 요약 생성"""
        logger.info(f"Summarizing results for query: {query}")
        
        try:
            # 시스템 메시지 구성
            system_message = SystemMessage(
                content="당신은 검색 결과를 바탕으로 사용자 질문에 답변하는 도우미입니다. 검색 결과에 관련 정보가 없다면 솔직히 모른다고 답변하세요."
            )
            
            # 검색 결과 문맥 구성
            user_prompt = f"""
                            사용자 질문한 질문의 제목과 내용입니다: 
                            {query}

                            검색 결과:
                            {search_results}

                            """
            user_message = HumanMessage(content=user_prompt)
            
            # 모델 호출
            response = await self.llm.ainvoke([system_message, user_message])
            
            logger.info("Summary generated successfully")
            return response.content
            
        except Exception as e:
            logger.error(f"Error in summarization: {str(e)}")
            raise
    
    # 노드 함수 추가 - 이제 이 함수가 그래프의 노드로 사용됨
    async def summarize_results_node(self, state: AgentState) -> AgentState:
        """검색 결과를 요약하는 노드"""
        logger.info("Executing summarize_results node")
        query = state["query"]
        search_results = state["search_results"]
        
        summary = await self.summarize(query, search_results)
        logger.info(f"검색 최종 결과 : {summary}")
        
        return {"summary": summary}