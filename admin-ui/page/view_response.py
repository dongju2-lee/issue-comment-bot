import streamlit as st
import datetime
import requests
import pandas as pd
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# API 서버 주소 설정
api_server = os.getenv("API_SERVER", "http://localhost:8001")

# CSS 스타일 추가 - 텍스트 색상을 검정색으로 변경
st.markdown("""
<style>
    /* 텍스트 영역의 텍스트 색상을 검정색으로 변경 */
    .stTextArea textarea {
        color: black !important;
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
    }
</style>
""", unsafe_allow_html=True)

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

# 날짜 선택 위젯
st.subheader("검색을 원하는 기간을 선택하세요 (최대 3개월 전까지)")
date_range = st.date_input(
    "기간 선택",
    (start_of_month, today.date()),
    min_date,  # 최소 날짜: 3개월 전
    today.date(),  # 최대 날짜: 오늘
    format="YYYY.MM.DD",
)

# API로부터 데이터 가져오기
@st.cache_data(ttl=300)  # 5분간 캐싱
def fetch_completed_tasks(api_url):
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()  # 오류 발생시 예외 발생
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        st.error(f"API 호출 중 오류 발생: {e}")
        return []

# 날짜 필터링 함수
def filter_tasks_by_date(tasks, start_date, end_date):
    filtered_tasks = []
    for task in tasks:
        if "requested_at" in task:
            task_date_str = task["requested_at"].split("T")[0]
            if start_date.isoformat() <= task_date_str <= end_date.isoformat():
                filtered_tasks.append(task)
    return filtered_tasks

# 데이터 검색 버튼
if len(date_range) == 2:
    start_date, end_date = date_range
    st.write(f"선택한 기간: {start_date.strftime('%Y년 %m월 %d일')} ~ {end_date.strftime('%Y년 %m월 %d일')}")
    
    if st.button("이 기간의 응답 이력 검색"):
        with st.spinner("데이터를 불러오는 중..."):
            # 완료된 작업 가져오기
            completed_tasks = fetch_completed_tasks(f"{api_server}/tasks/completed")
            
            # 선택한 기간으로 필터링
            filtered_tasks = filter_tasks_by_date(completed_tasks, start_date, end_date)
            
            if filtered_tasks:
                st.success(f"{len(filtered_tasks)}개의 응답 이력을 찾았습니다.")
                
                # 데이터 추출 및 표시
                for i, task in enumerate(filtered_tasks):
                    with st.expander(f"#{i+1}: {task.get('issue_title', '제목 없음')}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("**요청 정보**")
                            st.markdown(f"**저장소:** {task.get('repository', '정보 없음')}")
                            st.markdown(f"**요청자:** {task.get('requester', '정보 없음')}")
                            st.markdown(f"**요청 시간:** {task.get('requested_at', '정보 없음').replace('T', ' ').split('.')[0]}")
                        
                        with col2:
                            st.markdown("**이슈 정보**")
                            st.markdown(f"**이슈 ID:** {task.get('issue_number', '정보 없음')}")
                            st.markdown(f"**상태:** {'완료' if task.get('status') == 'completed' else task.get('status', '정보 없음')}")
                        
                        st.markdown("---")
                        st.markdown(f"**제목:** *{task.get('issue_title', '제목 정보 없음')}*")
                        
                        # 이슈 내용 표시 (text_area 대신 사용자 정의 스타일의 div 사용)
                        st.markdown("**이슈 내용**")
                        issue_body = task.get('issue_body', '내용 정보 없음')
                        st.markdown(f'<div class="black-text-box" style="height: 200px;">{issue_body}</div>', unsafe_allow_html=True)
                        
                        # LLM 응답 표시 (text_area 대신 사용자 정의 스타일의 div 사용)
                        st.markdown("**LLM 응답**")
                        llm_response = task.get('llm_response', '응답 정보 없음')
                        st.markdown(f'<div class="black-text-box" style="height: 400px;">{llm_response}</div>', unsafe_allow_html=True)
            else:
                st.warning(f"선택한 기간 ({start_date} ~ {end_date}) 동안의 응답 이력이 없습니다.")
else:
    st.write("시작일과 종료일을 모두 선택해주세요.")

# 구분선 추가
st.divider()

# 추가 정보
with st.expander("사용 안내"):
    st.markdown("""
    - 검색을 원하는 기간을 선택하고 '이 기간의 응답 이력 검색' 버튼을 클릭하세요.
    - 결과는 최신순으로 정렬됩니다.
    - 각 항목을 클릭하면 상세 내용을 확인할 수 있습니다.
    - 이슈 제목과 저장소 이름으로 필터링할 수 있는 기능은 추후 추가될 예정입니다.
    """)