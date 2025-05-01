# Issue-Bot: Q&A 봇

Issue-Bot은 GitHub 이슈 코멘트를 모니터링하고 자동으로 응답하는 AI 기반 봇 시스템입니다. 특히 클라우드 프로비저닝 시스템에 관한 질문에 답변하기 위해 설계되었습니다.

## 시스템 아키텍처

이 프로젝트는 세 가지 주요 구성 요소로 이루어져 있습니다:

1. **milvus-utils**: Milvus 벡터 데이터베이스를 관리하는 유틸리티 스크립트
2. **langgraph**: LangChain 및 LangGraph 기반 AI 에이전트 시스템
3. **api-server**: GitHub 웹훅을 처리하고 작업 큐를 관리하는 FastAPI 서버

### 기술 스택

- **백엔드**: Python, FastAPI
- **AI/ML**: LangChain, LangGraph, Google Vertex AI (Gemini 2.5 Pro)
- **벡터 데이터베이스**: Milvus
- **기타**: GitHub API, 비동기 작업 처리

## 주요 기능

- GitHub 이슈 코멘트를 웹훅으로 수신
- 코멘트 내 질문을 분석하여 관련 정보를 Milvus 벡터 데이터베이스에서 검색
- Google Vertex AI의 Gemini 2.5 Pro 모델을 사용한 응답 생성
- 응답을 GitHub 이슈에 댓글로 게시
- 각주 형태로 참고 문서 링크 제공

## 컴포넌트 세부 설명

### milvus-utils

Milvus 벡터 데이터베이스 관리를 위한 유틸리티 스크립트 모음입니다.

- **searching_data.py**: Vertex AI의 임베딩 모델을 사용하여 Milvus에서 유사도 검색 수행
- **push_using_gemini.py**: Gemini를 사용하여 데이터를 Milvus에 푸시
- **list_collections.py**: Milvus 컬렉션 목록 조회
- **delete_collection.py**: Milvus 컬렉션 삭제

### langgraph

LangChain과 LangGraph를 기반으로 하는 AI 에이전트 시스템입니다.

- **agents/**: 
  - **summary_agent.py**: 검색 결과를 요약하고 사용자 질문에 대한 응답 생성
  - **search_agent.py**: 사용자 질문을 벡터 데이터베이스에서 검색
- **graphs/**: 
  - **builder.py**: 에이전트들의 워크플로우를 정의하는 그래프 구성

### api-server

GitHub 웹훅을 처리하고 작업 큐를 관리하는 FastAPI 기반 서버입니다.

- **main.py**: FastAPI 애플리케이션의 메인 진입점
- **apis/**: 
  - **webhook.py**: GitHub 웹훅 처리 API
  - **task.py**: 작업 관리 API
  - **admin.py**: 관리 기능 API
  - **ping.py**: 헬스 체크 API
- **services/**: 
  - **processor.py**: 작업 처리 로직
  - **queue.py**: 작업 큐 관리
  - **llm.py**: LLM(대규모 언어 모델) 호출 서비스
  - **github.py**: GitHub API 연동

## 설치 및 설정

### 사전 요구사항

- Python 3.8 이상
- Milvus 서버
- Google Cloud 계정 (Vertex AI 액세스)
- GitHub 계정 (웹훅 설정)

### 환경 설정

1. 각 디렉토리의 requirements.txt 파일을 사용하여 필요한 패키지 설치:

```bash
# Milvus 유틸리티
cd milvus-utils
pip install -r requirements.txt

# LangGraph 에이전트
cd ../langgraph
pip install -r requirements.txt

# API 서버
cd ../api-server
pip install -r requirements.txt
```

2. 환경 변수 설정:
각 디렉토리의 `.env.example` 파일을 `.env`로 복사하고 필요한 값 설정

```bash
# api-server 및 langgraph 디렉토리에서
cp .env.example .env
```

주요 환경 변수:
- `VERTEX_PROJECT_ID`: Google Cloud 프로젝트 ID
- `VERTEX_LOCATION`: Vertex AI 위치
- `VERTEX_LLM_MODEL`: 사용할 Vertex AI 모델 (기본값: gemini-2.5-pro)
- `GITHUB_TOKEN`: GitHub API 액세스 토큰
- `MILVUS_HOST`: Milvus 서버 호스트
- `MILVUS_PORT`: Milvus 서버 포트

## 실행 방법

### Milvus 데이터 준비

```bash
cd milvus-utils
python push_using_gemini.py
```

### API 서버 실행

```bash
cd api-server
python main.py
```

### GitHub 웹훅 설정

1. GitHub 리포지토리 설정에서 웹훅 추가
2. 페이로드 URL: `https://[your-server]/api/webhook`
3. 콘텐츠 유형: `application/json`
4. 이슈 코멘트 이벤트 선택

## 작동 원리

1. 사용자가 GitHub 이슈에 코멘트를 남기면 웹훅이 API 서버로 전송됩니다.
2. API 서버는 코멘트 내용을 작업 큐에 추가합니다.
3. 작업 처리기가 큐에서 작업을 가져와 LangGraph 에이전트에 전달합니다.
4. 검색 에이전트는 질문을 벡터화하여 Milvus에서 관련 정보를 검색합니다.
5. 요약 에이전트는 검색 결과를 바탕으로 응답을 생성합니다.
6. 생성된 응답은 GitHub API를 통해 원본 이슈에 코멘트로 게시됩니다.

## 참고사항

- 이 봇은 클라우드 시스템에 관한 질문에 특화되어 있습니다.
- 응답에는 정보 출처를 나타내는 각주가 포함됩니다.
- 문서 URL은 별도 정의된 형식으로 변환됩니다.
- gcloud cli를 이용해서 로컬에서 vertexai사용을 위한 인증이 되어있어야 합니다.
## 라이선스

내부 프로젝트용으로 라이선스 정보는 별도로 명시되어 있지 않습니다. 