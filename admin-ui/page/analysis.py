import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import datetime
import re
import os
from dotenv import load_dotenv
from collections import Counter
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# .env 파일 로드
load_dotenv()

# API 서버 주소 설정
api_server = os.getenv("API_SERVER", "http://localhost:8001")


# 필요한 패키지 설치 확인 및 설치
import sys
import subprocess

@st.cache_resource
def install_packages():
    packages = ['wordcloud', 'matplotlib']
    for package in packages:
        try:
            __import__(package)
        except ImportError:
            st.info(f"{package} 패키지를 설치 중입니다...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    st.success("필요한 패키지가 설치되었습니다!")

# 패키지 설치 실행
with st.spinner("필요한 패키지를 확인 중입니다..."):
    install_packages()

# 이제 필요한 패키지를 import
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import io
import base64

# CSS 스타일 추가 (한글 표시 문제 해결용)
st.markdown("""
<style>
    /* 텍스트 영역의 텍스트 색상을 검정색으로 변경 */
    .stTextArea textarea {
        color: black !important;
        font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif !important;
    }
    
    /* 사용자 정의 텍스트 상자 스타일 */
    .black-text-box {
        background-color: #f0f2f6;
        border-radius: 0.5rem;
        padding: 1rem;
        color: black;
        border: 1px solid #e0e0e0;
        margin-bottom: 1rem;
        white-space: pre-wrap;
        overflow-y: auto;
        font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
    }
</style>
""", unsafe_allow_html=True)

# API로부터 데이터 가져오기
@st.cache_data(ttl=300)  # 5분간 캐싱
def fetch_completed_tasks(api_url):
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        st.error(f"API 호출 중 오류 발생: {e}")
        return []

# 단순한 정규식으로 단어 추출하는 함수
def extract_words(texts):
    if not texts:
        return []
    
    all_words = []
    for text in texts:
        if not text or not isinstance(text, str):
            continue
        
        # 한글 단어(2글자 이상) 또는 영어 단어(2글자 이상) 추출
        korean_words = re.findall(r'[가-힣]{2,}', text)
        english_words = re.findall(r'[a-zA-Z]{2,}', text)
        
        # 모든 단어 합치기 (숫자 제외, 대소문자 통일)
        words = korean_words + [word.lower() for word in english_words]
        
        # 불용어 필터링 (필요시 확장)
        stop_words = {'and', 'the', 'is', 'in', 'to', 'a', 'of', 'for', '이', '그', '저', '이것', '그것', '저것'}
        filtered_words = [word for word in words if word.lower() not in stop_words and len(word) > 1]
        
        all_words.extend(filtered_words)
    
    return all_words

# WordCloud 생성 함수
def generate_wordcloud(word_counts, title):
    # 한글 폰트 경로 지정 (시스템에 따라 경로가 다를 수 있음)
    # macOS 경로
    mac_font_path = '/Library/Fonts/AppleGothic.ttf'
    # Windows 경로
    win_font_path = 'C:/Windows/Fonts/malgun.ttf'
    # 기본 폰트 경로
    default_font_path = fm.findfont(fm.FontProperties(family=['Malgun Gothic', 'Arial', 'AppleGothic', 'sans-serif']))
    
    # 폰트 경로 결정
    font_path = default_font_path
    if os.path.exists(mac_font_path):
        font_path = mac_font_path
    elif os.path.exists(win_font_path):
        font_path = win_font_path
    
    st.write(f"사용 중인 폰트: {font_path}")  # 디버깅용 - 실제 사용 폰트 확인
    
    # WordCloud 생성
    try:
        wordcloud = WordCloud(
            font_path=font_path,
            width=800, 
            height=400, 
            background_color='white',
            max_words=100,
            max_font_size=150,
            random_state=42,
            normalize_plurals=False,  # 복수형 정규화 비활성화 (한글에 불필요)
            collocations=False  # 복합어 비활성화 (한글에 부적합할 수 있음)
        ).generate_from_frequencies(word_counts)
        
        # Matplotlib 그림 생성
        plt.rcParams['font.family'] = 'AppleGothic, Malgun Gothic, NanumGothic'  # matplotlib 폰트 설정
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.set_title(title, fontsize=15)
        ax.axis('off')
        
        # 이미지를 스트림릿에 표시하기 위해 변환
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode()
        plt.close(fig)
        
        return img_str
    
    except Exception as e:
        st.error(f"워드클라우드 생성 중 오류: {str(e)}")
        # 오류 발생 시 빈 이미지 반환
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, "워드클라우드 생성 실패", fontsize=15, ha='center')
        ax.axis('off')
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode()
        plt.close(fig)
        return img_str

# 기간 선택 위젯
st.subheader("분석할 기간을 선택하세요")

# 오늘 날짜 가져오기
today = datetime.datetime.now()
this_year = today.year
next_year = today.year + 1

# 최소 날짜 설정 (3개월 전)
three_months_ago = today - datetime.timedelta(days=90)
min_date = three_months_ago.date()

# 기본 날짜 설정 (현재 월의 1일부터 오늘까지)
start_of_month = datetime.date(this_year, today.month, 1)
# 기본 시작일이 3개월 이전이면 최소 날짜로 조정
if start_of_month < min_date:
    start_of_month = min_date

# 날짜 범위 선택
date_range = st.date_input(
    "기간 선택",
    (start_of_month, today.date()),
    min_date,  # 최소 날짜: 3개월 전
    today.date(),  # 최대 날짜: 오늘
    format="YYYY.MM.DD",
)

if len(date_range) == 2:
    start_date, end_date = date_range
    st.write(f"선택한 기간: {start_date.strftime('%Y년 %m월 %d일')} ~ {end_date.strftime('%Y년 %m월 %d일')}")
else:
    st.warning("날짜 범위를 선택해주세요.")
    start_date = end_date = None

# 분석 시작 버튼
if start_date and end_date:
    if st.button("데이터 분석 시작"):
        with st.spinner("데이터를 가져오고 분석하는 중..."):
            # 완료된 작업 가져오기
            completed_tasks = fetch_completed_tasks(f"{api_server}/tasks/completed")
            
            # 날짜 필터링
            filtered_tasks = []
            for task in completed_tasks:
                if "requested_at" in task:
                    task_date_str = task["requested_at"].split("T")[0]
                    task_date = datetime.datetime.strptime(task_date_str, "%Y-%m-%d").date()
                    if start_date <= task_date <= end_date:
                        filtered_tasks.append(task)
            
            if filtered_tasks:
                # 데이터 분석 시작
                st.success(f"총 {len(filtered_tasks)}개의 작업을 분석합니다.")
                
                # 데이터 프레임 생성
                df = pd.DataFrame(filtered_tasks)
                
                # 단어 분포 분석 섹션
                st.markdown("## 단어 분포 분석")
                
                # 제목과 본문 텍스트 합치기
                all_titles = df['issue_title'].tolist()
                all_bodies = df['issue_body'].tolist()
                combined_texts = all_titles + all_bodies
                
                # 합친 텍스트에서 단어 추출
                combined_words = extract_words(combined_texts)
                combined_counts = Counter(combined_words)
                
                if combined_counts:
                    # WordCloud 생성 및 표시
                    img_str = generate_wordcloud(combined_counts, "제목+본문 단어 분포")
                    st.markdown(f'<img src="data:image/png;base64,{img_str}" style="width:100%">', unsafe_allow_html=True)
                    
                    # 상위 15개 단어 막대 그래프
                    top_15_combined = dict(combined_counts.most_common(15))
                    fig = px.bar(
                        x=list(top_15_combined.keys()),
                        y=list(top_15_combined.values()),
                        labels={'x': '단어', 'y': '빈도'},
                        title="제목과 본문에서 가장 많이 사용된 단어 TOP 15"
                    )
                    fig.update_layout(xaxis_title="", yaxis_title="")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("제목과 본문에서 추출할 수 있는 단어가 없습니다.")
                
                # 구분선 추가
                st.divider()
                
                # 기존 제목/본문 개별 분석
                st.subheader("LLM을 이용하여 사용자의 질문 및 답변 내용 분석")
                
                # LLM 분석 섹션 추가
                st.write("이 섹션에서는 LLM을 이용하여 사용자의 질문과 응답 내용을 분석합니다.")
                
                # 분석 시작 버튼
                if st.button("LLM 분석 시작"):
                    with st.spinner("LLM을 이용하여 데이터 분석 중..."):
                        try:
                            # API 호출
                            analysis_url = f"{api_server}/analysis"
                            
                            # API 요청 데이터 준비
                            request_data = {
                                "start_date": start_date.isoformat(),
                                "end_date": end_date.isoformat(),
                                "tasks": filtered_tasks
                            }
                            
                            # API 호출
                            response = requests.post(
                                analysis_url, 
                                json=request_data,
                                timeout=300  # 분석에 시간이 걸릴 수 있으므로 타임아웃을 길게 설정
                            )
                            
                            # 응답 확인
                            if response.status_code == 200:
                                analysis_result = response.json()
                                
                                # 분석 결과 표시
                                st.success("LLM 분석이 완료되었습니다!")
                                
                                # 분석 결과 표시 영역 (마크다운 대신 텍스트 영역 사용)
                                st.markdown("### LLM 분석 결과")
                                st.text_area(
                                    label="",
                                    value=analysis_result.get("analysis", "분석 결과가 없습니다."),
                                    height=300,
                                    key="analysis_result"
                                )
                                
                                # 추가 분석 정보가 있을 경우 표시 (마크다운 대신 텍스트 영역 사용)
                                if "additional_insights" in analysis_result:
                                    st.markdown("### 추가 인사이트")
                                    st.text_area(
                                        label="",
                                        value=analysis_result.get("additional_insights", ""),
                                        height=200,
                                        key="additional_insights"
                                    )
                            else:
                                st.error(f"API 호출 오류: {response.status_code} - {response.text}")
                        except Exception as e:
                            st.error(f"분석 중 오류가 발생했습니다: {str(e)}")
                
                # 분석 도움말
                with st.expander("LLM 분석에 대하여"):
                    st.markdown("""
                    ### LLM 분석이란?
                    
                    대규모 언어 모델(LLM)을 사용하여 선택한 기간 내의 이슈 제목과 본문을 심층 분석합니다.
                    이 분석을 통해 다음과 같은 인사이트를 얻을 수 있습니다:
                    
                    - 자주 질문되는 주제와 패턴
                    - 사용자 질문의 복잡성 및 난이도 평가
                    - 답변 품질 및 효과성 분석
                    - 질문-답변 쌍의 상관관계 분석
                    - 개선이 필요한 영역 식별
                    
                    분석에는 1-2분 정도 소요될 수 있습니다.
                    """)
               
            else:
                st.warning(f"선택한 기간 ({start_date} ~ {end_date}) 동안의 데이터가 없습니다.")
else:
    st.info("시작일과 종료일을 모두 선택해주세요.")

# 참고 자료 및 도움말
with st.expander("분석 도움말"):
    st.markdown("""
    ### 분석 방법
    
    #### 단어 분포 분석
    - 제목과 본문에서 자주 등장하는 단어들을 추출하여 시각화합니다.
    - 단순 정규식을 사용하여 한글과 영어 단어를 추출합니다(2글자 이상).
    - 단어 구름(WordCloud)은 단어의 빈도수에 비례하여 크기가 결정됩니다.
    - 제목과 본문을 통합 분석하여 전체적인 키워드를 파악할 수 있습니다.
    - 한글의 경우 폰트를 다운받으셔야 합니다.
    """)