import os
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import Dict, Any

from graphs.builder import GraphBuilder, AgentState
from utils.logger import setup_logger

# 로거 설정
logger = setup_logger("app")

# .env 파일 로드
load_dotenv()

# Pydantic 모델 정의
class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    query: str
    summary: str

# FastAPI 앱 초기화
app = FastAPI(title="문서 검색 및 요약 API")

# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한하세요
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 그래프 빌더 초기화
graph_builder = GraphBuilder()

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up the application")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down the application")

# 기본 루트 엔드포인트
@app.get("/")
async def root():
    return {"message": "문서 검색 및 요약 API에 오신 것을 환영합니다"}

# 검색 엔드포인트
@app.post("/search", response_model=QueryResponse)
async def search_endpoint(request: QueryRequest):
    """
    쿼리에 기반하여 문서를 검색하고 요약하는 엔드포인트
    """
    try:
        logger.info(f"Received search request: {request.query}")
        
        # 그래프 생성
        graph = graph_builder.build_graph()
        
        # 초기 상태 설정
        initial_state = {"query": request.query, "search_results": [], "summary": ""}
        
        # 그래프 실행 (비동기)
        result = await graph.ainvoke(initial_state)
        
        logger.info(f"Search completed for query: {request.query}")
        return {"query": request.query, "summary": result["summary"]}
    
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 메인 실행 부분
if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)