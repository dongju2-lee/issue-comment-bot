from typing import Dict, List, Any, TypedDict, Annotated
import operator
import os
from dotenv import load_dotenv
import vertexai
from vertexai.language_models import TextEmbeddingModel
from sklearn.feature_extraction.text import TfidfVectorizer
from pymilvus import MilvusClient, AnnSearchRequest, WeightedRanker, RRFRanker
from utils.logger import setup_logger

# 로거 설정
logger = setup_logger("search_agent")

# .env 파일 로드
load_dotenv()

# 환경 변수 설정
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
MILVUS_COLLECTION = os.getenv("MILVUS_COLLECTION", "mkdocs_hybrid_collection")
MILVUS_USER = os.getenv("MILVUS_USER", "root")
MILVUS_PASSWORD = os.getenv("MILVUS_PASSWORD", "Milvus")
VERTEX_PROJECT_ID = os.getenv("VERTEX_PROJECT_ID", "da-aiagent-dev")
VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")
VERTEX_EMBEDDING_MODEL = os.getenv("VERTEX_EMBEDDING_MODEL", "text-multilingual-embedding-002")

# AgentState 타입 정의 - 그래프에서 사용
class AgentState(TypedDict):
    query: str
    search_results: Annotated[List[Dict[str, Any]], operator.add]
    summary: str

class SearchAgent:
    """문서 검색을 수행하는 에이전트"""
    
    def __init__(self):
        # VertexAI 초기화
        vertexai.init(project=VERTEX_PROJECT_ID, location=VERTEX_LOCATION)
        self.embedding_model = TextEmbeddingModel.from_pretrained(VERTEX_EMBEDDING_MODEL)
        
        # Milvus 클라이언트 초기화
        self.milvus_client = MilvusClient(
            uri=f"http://{MILVUS_HOST}:{MILVUS_PORT}",
            token=f"{MILVUS_USER}:{MILVUS_PASSWORD}"
        )
        logger.info("SearchAgent initialized")
    
    async def hybrid_search(self, query: str, language="ko", top_k=20) -> List[Dict[str, Any]]:
        """하이브리드 검색 수행 (공식 API 문서 기반)"""
        logger.info(f"Performing hybrid search for query: {query}")
        
        try:
            # 1. 밀집 벡터 생성
            dense_embedding = self.embedding_model.get_embeddings([query])[0].values
            
            # 2. 희소 벡터 생성 (TF-IDF)
            vectorizer = TfidfVectorizer(max_features=5000)
            vectorizer.fit([query])
            sparse_matrix = vectorizer.transform([query])
            
            # 희소 벡터를 {인덱스: 값} 형태로 변환
            sparse_vector = {}
            for i, idx in enumerate(sparse_matrix.indices):
                sparse_vector[int(idx)] = float(sparse_matrix.data[i])
            
            # 3. 밀집 벡터 검색 파라미터 설정
            dense_search_param = {
                "data": [dense_embedding],
                "anns_field": "dense_vector",
                "param": {
                    "metric_type": "COSINE", 
                    "params": {}
                },
                "limit": top_k
            }
            dense_request = AnnSearchRequest(**dense_search_param)
            
            # 4. 희소 벡터 검색 파라미터 설정
            sparse_search_param = {
                "data": [sparse_vector],
                "anns_field": "sparse_vector",
                "param": {
                    "metric_type": "IP",
                    "params": {"drop_ratio_build": 0.2}
                },
                "limit": top_k
            }
            sparse_request = AnnSearchRequest(**sparse_search_param)

            # 5. RRF 재정렬기 설정
            ranker = RRFRanker(60)  # k=60
            
            # 6. 필터 표현식 설정 (언어 필터링)
            expr = f"language == '{language}'" if language else None
            
            # 7. 하이브리드 검색 실행
            results = self.milvus_client.hybrid_search(
                collection_name=MILVUS_COLLECTION,
                reqs=[sparse_request, dense_request],  # 검색 요청 리스트
                ranker=ranker,                        # 재정렬기
                limit=top_k,                          # 최종 결과 수
                output_fields=["file_path", "title", "content", "language"]
            )
            
            logger.info(f"Hybrid search completed. Found {len(results)} results")
            return results
        
        except Exception as e:
            logger.error(f"Error in hybrid search: {str(e)}")
            raise
    
    # 노드 함수 추가 - 이제 이 함수가 그래프의 노드로 사용됨
    async def search_documents_node(self, state: AgentState) -> AgentState:
        """사용자 쿼리로 문서 검색을 수행하는 노드"""
        logger.info("Executing search_documents node")
        query = state["query"]
        search_results = await self.hybrid_search(query)
        
        return {"search_results": search_results}