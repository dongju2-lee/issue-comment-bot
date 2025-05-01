import vertexai
from vertexai.language_models import TextEmbeddingModel
from pymilvus import connections, Collection

# Milvus 연결 정보
MILVUS_HOST     = "localhost"
MILVUS_PORT     = "19530"
COLLECTION_NAME = "COLLECTION_NAME"

# Vertex AI 설정
VERTEX_PROJECT_ID = "USER-PROJECT-ID"
VERTEX_LOCATION   = "us-central1"
VERTEX_MODEL_ID   = "text-embedding-005"

def setup_vertex_ai():
    """Vertex AI 임베딩 모델 초기화"""
    vertexai.init(project=VERTEX_PROJECT_ID, location=VERTEX_LOCATION)
    model = TextEmbeddingModel.from_pretrained(VERTEX_MODEL_ID)
    return model

def main():
    # 1) Vertex AI 모델 로드
    model = setup_vertex_ai()
    
    # 2) Milvus 연결 및 컬렉션 로드
    connections.connect(host=MILVUS_HOST, port=MILVUS_PORT)
    collection = Collection(name=COLLECTION_NAME)
    collection.load()
    
    # 3) 검색할 자연어 질문
    query = "질문을 입력하세요"
    
    # 4) 질문을 임베딩
    embedding = model.get_embeddings([query])[0].values
    
    # 5) Milvus에 검색 요청
    search_params = {
        "metric_type": "COSINE",
        "params":       {"ef": 64}
    }

    expr = 'language == "ko"'
    results = collection.search(
        data=[embedding],            # 쿼리 벡터 리스트
        anns_field="vector",         # 컬렉션의 벡터 필드명
        param=search_params,
        limit=5,
        expr=expr,                    
        output_fields=["file_path", "title", "content"]
    )
    print(f"결과 : {results}")
    # 6) 결과 출력
    print(f"질의: {query}\n")
    for i, hits in enumerate(results[0], start=1):
        print(f"=== 결과 #{i} (score: {hits.score:.4f}) ===")
        print(f"경로 : {hits.entity.get('file_path')}")
        print(f"제목 : {hits.entity.get('title')}")
        snippet = hits.entity.get('content')[:2000].replace("\n", " ")
        print(f"내용 : {snippet}...\n")

if __name__ == "__main__":
    main()