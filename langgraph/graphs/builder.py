from typing import TypedDict, List, Annotated, Dict, Any
import operator
from langgraph.graph import StateGraph, START, END
from agents.search_agent import SearchAgent
from agents.summary_agent import SummaryAgent
from utils.logger import setup_logger

# 로거 설정
logger = setup_logger("graph_builder")

# 상태 정의 (TypedDict 사용)
class AgentState(TypedDict):
    query: str
    search_results: Annotated[List[Dict[str, Any]], operator.add]
    summary: str

class GraphBuilder:
    """검색 및 요약 그래프를 구축하는 클래스"""
    
    def __init__(self):
        self.search_agent = SearchAgent()
        self.summary_agent = SummaryAgent()
        logger.info("GraphBuilder initialized")
    
    def build_graph(self):
        """검색 및 요약 그래프 생성"""
        logger.info("Building graph")
        # 그래프 빌더 초기화
        graph_builder = StateGraph(AgentState)
        
        # 노드 추가 (각 에이전트의 노드 함수 사용)
        graph_builder.add_node("search", self.search_agent.search_documents_node)
        graph_builder.add_node("summarize", self.summary_agent.summarize_results_node)
        
        # 엣지 연결
        graph_builder.add_edge(START, "search")
        graph_builder.add_edge("search", "summarize")
        graph_builder.add_edge("summarize", END)
        
        # 그래프 컴파일
        return graph_builder.compile()