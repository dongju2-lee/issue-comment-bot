import streamlit as st
import pandas as pd
import requests
import json
import datetime
from collections import Counter
import os
from dotenv import load_dotenv
from streamlit.logger import get_logger
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

logger = get_logger(__name__)
# .env 파일 로드
load_dotenv()



# 사이드바에 날짜 범위 선택 옵션 추가
st.sidebar.title("설정")
date_range_option = st.sidebar.selectbox(
    "데이터 표시 기간",
    options=["최근 7일", "최근 15일", "최근 30일"],
    index=0  # 기본값은 7일
)

# 선택한 옵션에 따라 날짜 범위 설정
today = datetime.datetime.now().date()
if date_range_option == "최근 7일":
    start_date = today - datetime.timedelta(days=7)
    days_to_filter = 7
elif date_range_option == "최근 15일":
    start_date = today - datetime.timedelta(days=15)
    days_to_filter = 15
else:  # 최근 30일
    start_date = today - datetime.timedelta(days=30)
    days_to_filter = 30

start_date_str = start_date.isoformat()
logger.info(f"시작 날짜: {start_date_str}")

# API 서버 주소 설정
api_server = os.getenv("API_SERVER", "http://localhost:8001")

# API로부터 데이터 가져오기
@st.cache_data(ttl=300)  # 5분간 캐싱
def fetch_data(api_url):
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()  # 오류 발생시 예외 발생
        data = response.json()
        logger.info(f"API 데이터 {len(data)}개 가져옴: {api_url}")
        return data
    except requests.exceptions.RequestException as e:
        st.error(f"API 호출 중 오류 발생: {e}")
        return []

# 작업의 날짜를 추출하는 함수
def extract_task_date(task):
    """작업에서 날짜를 추출하는 함수 (성공 및 실패 작업 모두 처리)"""
    # 성공한 작업 (requested_at 필드가 바로 접근 가능)
    if "requested_at" in task:
        return task["requested_at"].split("T")[0]
    
    # 실패한 작업 (original_payload > issue > created_at에 접근)
    if "original_payload" in task and isinstance(task["original_payload"], dict):
        payload = task["original_payload"]
        if "issue" in payload and isinstance(payload["issue"], dict):
            issue = payload["issue"]
            if "created_at" in issue:
                # GitHub API의 날짜 형식: "2025-04-30T01:13:19Z"
                return issue["created_at"].split("T")[0]
    
    # 날짜를 찾을 수 없는 경우
    logger.warning(f"날짜를 찾을 수 없는 작업: {task.get('task_id', '알 수 없음')}")
    return None

# 작업의 요청자를 추출하는 함수
def extract_requester(task):
    """작업에서 요청자 정보를 추출하는 함수 (성공 및 실패 작업 모두 처리)"""
    # 성공한 작업
    if "requester" in task:
        return task["requester"]
    
    # 실패한 작업
    if "original_payload" in task and isinstance(task["original_payload"], dict):
        payload = task["original_payload"]
        if "issue" in payload and isinstance(payload["issue"], dict):
            issue = payload["issue"]
            if "user" in issue and isinstance(issue["user"], dict):
                return issue["user"].get("login", "unknown")
    
    return "unknown"

# 작업의 저장소를 추출하는 함수
def extract_repository(task):
    """작업에서 저장소 정보를 추출하는 함수 (성공 및 실패 작업 모두 처리)"""
    # 성공한 작업
    if "repository" in task:
        return task["repository"]
    
    # 실패한 작업
    if "original_payload" in task and isinstance(task["original_payload"], dict):
        payload = task["original_payload"]
        if "repository" in payload and isinstance(payload["repository"], dict):
            return payload["repository"].get("full_name", "unknown")
    
    return "unknown"

# 특정 기간 내 데이터만 필터링하는 함수
def filter_data_by_date(tasks, start_date_str):
    filtered_tasks = []
    
    for task in tasks:
        # 날짜 추출
        task_date_str = extract_task_date(task)
        if not task_date_str:
            continue
        
        try:
            # 날짜 비교
            if task_date_str >= start_date_str:
                # 필터링된 작업에 요청자와 저장소 정보 표준화하여 추가
                # 메타데이터를 작업에 직접 추가하여 나중에 통계 함수에서 동일하게 접근 가능
                if "requester" not in task:
                    task["requester"] = extract_requester(task)
                
                if "repository" not in task:
                    task["repository"] = extract_repository(task)
                
                if "requested_at" not in task and task_date_str:
                    # 표준화된 형식으로 requested_at 추가
                    task["requested_at"] = f"{task_date_str}T00:00:00"
                
                filtered_tasks.append(task)
                logger.debug(f"필터링 통과: {task.get('task_id', 'unknown')}")
        except Exception as e:
            logger.error(f"날짜 필터링 중 오류: {e}, 작업: {task.get('task_id', 'unknown')}")
    
    logger.info(f"원본 작업 {len(tasks)}개 중 {len(filtered_tasks)}개 필터링됨 (시작일: {start_date_str})")
    return filtered_tasks

# 데이터 분석 함수들
def count_tasks_by_date(tasks):
    dates = [extract_task_date(task) for task in tasks if extract_task_date(task)]
    date_counter = Counter(dates)
    df = pd.DataFrame({
        "날짜": list(date_counter.keys()),
        "요청수": list(date_counter.values())
    })
    if df.empty:
        return pd.DataFrame(columns=["날짜", "요청수"])
    df["날짜"] = pd.to_datetime(df["날짜"])
    df = df.sort_values("날짜")
    return df

def get_top_requesters(tasks, top_n=5):
    requesters = [task.get("requester", "unknown") for task in tasks]
    counter = Counter(requesters)
    return counter.most_common(top_n)

def get_top_repositories(tasks, top_n=5):
    repos = [task.get("repository", "unknown") for task in tasks]
    counter = Counter(repos)
    return counter.most_common(top_n)

# 데이터 로딩 버튼
if st.button("데이터 새로고침"):
    st.cache_data.clear()
    st.success("캐시가 초기화되었습니다. 데이터를 다시 불러옵니다.")

# 데이터 가져오기
with st.spinner("데이터를 불러오는 중..."):
    completed_tasks = fetch_data(f"{api_server}/tasks/completed")
    failed_tasks = fetch_data(f"{api_server}/tasks/failed")
    
    # API 응답 구조 확인
    if failed_tasks:
        sample_task = failed_tasks[0]
        logger.info(f"샘플 실패 작업: {sample_task.keys()}")
        if "original_payload" in sample_task:
            payload = sample_task["original_payload"]
            if "issue" in payload:
                issue = payload["issue"]
                logger.info(f"실패 작업 날짜: {issue.get('created_at')}")
    
    all_tasks = completed_tasks + failed_tasks
    
    # 선택한 날짜 범위로 데이터 필터링
    completed_tasks_filtered = filter_data_by_date(completed_tasks, start_date_str)
    failed_tasks_filtered = filter_data_by_date(failed_tasks, start_date_str)
    all_tasks_filtered = completed_tasks_filtered + failed_tasks_filtered
    
    # 필터링 결과 로깅
    logger.info(f"원본 실패 작업: {len(failed_tasks)}개, 필터링 후: {len(failed_tasks_filtered)}개")
    logger.info(f"원본 완료 작업: {len(completed_tasks)}개, 필터링 후: {len(completed_tasks_filtered)}개")


# 메트릭 표시 - 총 건수, 성공 건수, 실패 건수 (필터링된 데이터 기준)
if all_tasks_filtered:
    # 메인 타이틀
    st.title("Issue-Bot 통계 대시보드")
    st.write(f"데이터 범위: {date_range_option}")
    
    # 요약 메트릭
    col1, col2, col3, col4 = st.columns(4)
    
    # 총 요청 건수
    with col1:
        st.metric(
            label="총 요청 건수",
            value=len(all_tasks_filtered),
            delta=None,
            border=True
        )
    
    # 성공 건수
    with col2:
        success_rate = f"{(len(completed_tasks_filtered) / len(all_tasks_filtered) * 100):.1f}%" if all_tasks_filtered else "0.0%"
        st.metric(
            label="성공 건수",
            value=len(completed_tasks_filtered),
            delta=success_rate,
            border=True
        )
    
    # 실패 건수
    with col3:
        failure_rate = f"{(len(failed_tasks_filtered) / len(all_tasks_filtered) * 100):.1f}%" if all_tasks_filtered else "0.0%"
        st.metric(
            label="실패 건수",
            value=len(failed_tasks_filtered),
            delta=failure_rate,
            delta_color="inverse",  # 실패율은 낮을수록 좋으므로 색상 반전
            border=True
        )
    
    # 성공률
    with col4:
        if all_tasks_filtered:
            success_percentage = (len(completed_tasks_filtered) / len(all_tasks_filtered)) * 100
            st.metric(
                label="성공률",
                value=f"{success_percentage:.1f}%",
                border=True
            )
    
    # 구분선 추가
    st.divider()
    
    # 일별 요청 건수 차트
    st.subheader(f"일별 요청 건수 추이 ({date_range_option})")
    
    all_df = count_tasks_by_date(all_tasks_filtered)
    completed_df = count_tasks_by_date(completed_tasks_filtered)
    failed_df = count_tasks_by_date(failed_tasks_filtered)
    
    # 데이터가 있는 경우에만 차트 표시
    if not all_df.empty:
        # 날짜 범위 설정 (선택한 날짜 범위에 맞게)
        end_date = today
        
        # 데이터프레임 병합
        date_range = pd.date_range(start=start_date, end=end_date)
        chart_df = pd.DataFrame({"날짜": date_range})
        
        # 각 데이터프레임 병합
        chart_df = chart_df.merge(all_df, on="날짜", how="left").fillna(0)
        
        # 성공 데이터가 있으면 병합
        if not completed_df.empty:
            chart_df = chart_df.merge(
                completed_df.rename(columns={"요청수": "성공"}), 
                on="날짜", 
                how="left"
            ).fillna(0)
        else:
            chart_df["성공"] = 0
            
        # 실패 데이터가 있으면 병합
        if not failed_df.empty:
            chart_df = chart_df.merge(
                failed_df.rename(columns={"요청수": "실패"}), 
                on="날짜", 
                how="left"
            ).fillna(0)
        else:
            chart_df["실패"] = 0

        # 날짜를 최신순으로 정렬 (오늘날짜가 맨 오른쪽에 오도록)
        chart_df = chart_df.sort_values("날짜")
        
        # 날짜 형식을 더 간결하게 변경 (ex. "04-30")
        chart_df["표시날짜"] = chart_df["날짜"].dt.strftime("%m-%d")
        
        # 차트 표시 (기본 라인 차트 사용)
        st.line_chart(
            chart_df,
            x="표시날짜",
            y=["성공", "요청수", "실패"],
            color=["#5470C6", "#91CC75", "#EE6666"]  # 파란색(성공), 초록색(요청수), 빨간색(실패)
        )
    else:
        st.warning(f"{date_range_option} 동안의 요청 데이터가 없습니다.")
    
    # 구분선 추가
    st.divider()
    
    # 요청자 및 레포지토리 통계
    st.subheader(f"사용자 및 리포지토리 통계 ({date_range_option})")
    
    # 사용자 통계 및 레포지토리 통계를 나란히 배치
    col1, col2 = st.columns(2)
    
    with col1:
        # 사용자 활동 통계
        st.markdown("### 사용자 활동 통계")
        
        # 설정한 기간 동안의 활성 사용자
        selected_period_requesters = set()
        
        # 일주일 전부터 설정한 기간 이전까지의 사용자
        comparison_period_start = start_date - datetime.timedelta(days=7)
        comparison_period_end = start_date
        comparison_period_requesters = set()
        
        comparison_period_start_str = comparison_period_start.isoformat()
        comparison_period_end_str = comparison_period_end.isoformat()
        
        # 모든 작업에서 통일된 방식으로 날짜와 요청자 추출
        for task in all_tasks:
            task_date = extract_task_date(task)
            if not task_date:
                continue
                
            requester = extract_requester(task)
            
            # 설정한 기간 내 사용자
            if task_date >= start_date_str:
                selected_period_requesters.add(requester)
            
            # 비교 기간 내 사용자 (설정한 기간보다 일주일 전)
            if comparison_period_start_str <= task_date < comparison_period_end_str:
                comparison_period_requesters.add(requester)
        
        # 현재 기간 사용자 수
        current_count = len(selected_period_requesters)
        
        # 비교 기간 사용자 수 
        prev_count = len(comparison_period_requesters)
        
        # 증감률 계산 및 표시
        if prev_count > 0:
            change_rate = ((current_count - prev_count) / prev_count) * 100
            delta_text = f"{change_rate:.1f}% 이전 7일 대비"
        else:
            delta_text = "아직 데이터 산정 불가 (7일 이상 데이터 필요)"
        
        st.metric(
            label=f"{date_range_option} 활성 사용자 수",
            value=current_count,
            delta=delta_text,
            border=True
        )
        
        # 상위 요청자 표시
        st.markdown("### 가장 활발한 사용자 Top 5")
        top_requesters = get_top_requesters(all_tasks_filtered)
        
        if top_requesters:
            # 파이 차트용 데이터프레임 생성
            requester_df = pd.DataFrame(top_requesters, columns=["사용자", "요청수"])
            
            # 파이 차트 생성
            fig = px.pie(
                requester_df, 
                values="요청수", 
                names="사용자",
                title="사용자별 요청 비율",
                hole=0.4,  # 도넛 차트 스타일
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            
            # 차트 레이아웃 향상
            fig.update_traces(
                textposition='inside', 
                textinfo='percent+label',
                hoverinfo='label+percent+value',
                textfont_size=12,
                marker=dict(line=dict(color='#FFFFFF', width=1))
            )
            fig.update_layout(
                legend=dict(
                    orientation="h", 
                    yanchor="bottom", 
                    y=-0.2, 
                    xanchor="center", 
                    x=0.5,
                    font=dict(size=10)
                ),
                margin=dict(l=20, r=20, t=40, b=20),
                annotations=[dict(
                    text='사용자 비율',
                    showarrow=False,
                    font_size=14
                )]
            )
            
            # 차트 표시
            st.plotly_chart(fig, use_container_width=True)
            

        else:
            st.info("활발한 사용자 데이터가 없습니다.")
    
    with col2:
        # 리포지토리 통계
        st.markdown("### 리포지토리 통계")
        
        # 총 리포지토리 수 표시
        unique_repos = set([task.get("repository", "unknown") for task in all_tasks_filtered])
        st.metric(
            label=f"총 활성 리포지토리 수 ({date_range_option})",
            value=len(unique_repos),
            border=True
        )
        
        # 상위 리포지토리 표시
        st.markdown("### 가장 많이 요청된 리포지토리 Top 5")
        top_repos = get_top_repositories(all_tasks_filtered)
        
        if top_repos:
            # 파이 차트용 데이터프레임 생성
            repo_df = pd.DataFrame(top_repos, columns=["리포지토리", "요청수"])
            
            # 파이 차트 생성
            fig = px.pie(
                repo_df, 
                values="요청수", 
                names="리포지토리",
                title="리포지토리별 요청 비율",
                hole=0.4,  # 도넛 차트 스타일
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            
            # 차트 레이아웃 향상
            fig.update_traces(
                textposition='inside', 
                textinfo='percent+label',
                hoverinfo='label+percent+value',
                textfont_size=12,
                marker=dict(line=dict(color='#FFFFFF', width=1))
            )
            fig.update_layout(
                legend=dict(
                    orientation="h", 
                    yanchor="bottom", 
                    y=-0.2, 
                    xanchor="center", 
                    x=0.5,
                    font=dict(size=10)
                ),
                margin=dict(l=20, r=20, t=40, b=20),
                annotations=[dict(
                    text='리포지토리 비율',
                    showarrow=False,
                    font_size=14
                )]
            )
            
            # 차트 표시
            st.plotly_chart(fig, use_container_width=True)

        else:
            st.info("리포지토리 데이터가 없습니다.")
    
else:
    st.warning("데이터를 불러올 수 없습니다. API 서버 주소를 확인하고 새로고침 버튼을 눌러주세요.")