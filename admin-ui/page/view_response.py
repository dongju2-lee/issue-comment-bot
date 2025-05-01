import streamlit as st

# 입력 페이지 내용
st.write("체중과 키를 입력하여 BMI를 계산해 보세요.")

# 이전 입력값 가져오기
weight = st.number_input(
    "체중 (kg): ", 
    min_value=0.0, 
    max_value=500.0, 
    value=st.session_state.weight,
    step=0.1,
    help="체중을 킬로그램 단위로 입력하세요."
)

height = st.number_input(
    "키 (m): ", 
    min_value=0.0, 
    max_value=3.0, 
    value=st.session_state.height,
    step=0.01,
    help="키를 미터 단위로 입력하세요. 예: 1.75"
)

# 값을 세션 상태에 저장
if st.button("저장"):
    if height <= 0 or weight <= 0:
        st.error("키와 체중은 0보다 커야 합니다.")
    else:
        st.session_state.weight = weight
        st.session_state.height = height
        st.success("입력이 저장되었습니다! 이제 '결과 페이지'로 이동하여 BMI를 확인하세요.")

# 추가 정보
with st.expander("BMI란?"):
    st.write("""
    체질량 지수(BMI)는 체중과 키를 기반으로 한 신체 지방의 측정치입니다.
    이는 체중(kg)을 신장(m)의 제곱으로 나누어 계산합니다.
    
    **수식**: BMI = 체중(kg) / (키(m) × 키(m))
    """)
    
    st.write("**BMI 범주:**")
    st.write("- 저체중: 18.5 미만")
    st.write("- 정상: 18.5-24.9")
    st.write("- 과체중: 25-29.9")
    st.write("- 비만: 30 이상")