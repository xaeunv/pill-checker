import streamlit as st

# ---------------------------------------------------
# 1단계: 제품명 -> 성분 매핑 (Colab에서 만든 것과 동일)
# ---------------------------------------------------
drug_ingredients = {
    "타이레놀": ["아세트아미노펜"],
    "펜잘": ["아세트아미노펜"],
    "게보린": ["아세트아미노펜", "이소프로필안티피린", "카페인"],
    "이지엔6": ["이부프로펜"],
    "이지엔6에이스": ["아세트아미노펜"],
    "애드빌": ["이부프로펜"],
    "부루펜": ["이부프로펜"],
    "탁센": ["나프록센"],
    "아스피린": ["아세틸살리실산"],
}

# ---------------------------------------------------
# 성분별 최소 복용 간격 (시간)
# 주의: 아래 값은 대표값입니다. 실제로는 의약품안전나라·
# 약학정보원에서 각 성분의 정확한 첨부문서 기준을 확인해서
# 바꿔주세요.
# ---------------------------------------------------
min_interval = {
    "아세트아미노펜": 4,
    "이부프로펜": 6,
    "나프록센": 8,
    "아세틸살리실산": 4,
    "이소프로필안티피린": 4,
    "카페인": 4,
}

# ---------------------------------------------------
# 페이지 기본 설정
# ---------------------------------------------------
st.set_page_config(page_title="이 약, 같이 먹어도 될까?", page_icon="💊")

st.title("💊 이 약, 같이 먹어도 될까?")
st.caption("서로 다른 이름의 진통제도 같은 성분을 담고 있을 수 있어요. "
           "복용 기록을 남기면 성분 중복과 복용 간격을 확인해 드립니다.")

st.warning(
    "이 도구는 처방이 아닙니다. 등록된 성분과 공식 복용 간격 기준을 바탕으로 "
    "중복 복용 가능성을 안내하는 교육·확인용 도구예요. 체중, 간·신장 기능, "
    "병용 약물 등 개인차는 반영하지 않으니 정확한 복용은 약사·의사와 상담하세요."
)

# ---------------------------------------------------
# 세션 상태: 페이지를 새로고침해도 복용 기록이 유지되도록 저장
# (Streamlit은 매번 코드를 처음부터 다시 실행하기 때문에,
#  st.session_state에 저장해두지 않으면 기록이 계속 사라짐)
# ---------------------------------------------------
if "taken_list" not in st.session_state:
    st.session_state.taken_list = []  # [{"drug": ..., "hours_ago": ...}, ...]

# ---------------------------------------------------
# 2단계: 복용 기록 입력
# ---------------------------------------------------
st.header("1. 복용 기록")

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    taken_drug = st.selectbox("먹은 약", list(drug_ingredients.keys()), key="taken_select")
with col2:
    hours_ago = st.number_input("몇 시간 전", min_value=0.0, step=0.5, value=0.0)
with col3:
    st.write("")  # 버튼 위치를 아래로 살짝 맞추기 위한 빈 줄
    st.write("")
    if st.button("추가하기"):
        st.session_state.taken_list.append({"drug": taken_drug, "hours_ago": hours_ago})

# 지금까지 추가된 복용 기록 보여주기
if len(st.session_state.taken_list) == 0:
    st.info("아직 기록된 약이 없어요.")
else:
    for i, entry in enumerate(st.session_state.taken_list):
        ingredients = ", ".join(drug_ingredients[entry["drug"]])
        col_a, col_b = st.columns([5, 1])
        with col_a:
            st.write(f"**{entry['drug']}** — {entry['hours_ago']}시간 전 · 성분: {ingredients}")
        with col_b:
            if st.button("삭제", key=f"remove_{i}"):
                st.session_state.taken_list.pop(i)
                st.rerun()

# ---------------------------------------------------
# 3단계: 지금 먹으려는 약 확인
# ---------------------------------------------------
st.header("2. 지금 먹으려는 약")
new_drug = st.selectbox("약 선택", list(drug_ingredients.keys()), key="new_select")

if st.button("지금 먹어도 되는지 확인하기", type="primary"):
    new_ingredients = drug_ingredients[new_drug]
    warnings = []

    # 이미 먹은 약들과 성분이 겹치는지, 겹친다면 간격이 지났는지 확인
    for entry in st.session_state.taken_list:
        taken_ingredients = drug_ingredients[entry["drug"]]
        for ingredient in taken_ingredients:
            if ingredient in new_ingredients:
                need_to_wait = min_interval[ingredient]
                remaining = need_to_wait - entry["hours_ago"]
                if remaining > 0:
                    warnings.append(
                        {"ingredient": ingredient, "from": entry["drug"], "remaining": remaining}
                    )

    # 결과 보여주기
    if len(st.session_state.taken_list) == 0:
        st.success("✓ 복용 가능 — 아직 기록된 복용 이력이 없어 확인할 중복이 없습니다.")
    elif len(warnings) == 0:
        st.success("✓ 복용 가능 — 기록된 약과 겹치는 성분이 없거나, 안전한 복용 간격이 이미 지났습니다.")
    else:
        st.error("⚠ 잠시 기다려 주세요")
        for w in warnings:
            st.write(
                f"- **{w['ingredient']}** 성분이 {w['from']}과 중복돼요 — "
                f"약 {w['remaining']:.1f}시간 더 기다려 주세요."
            )
