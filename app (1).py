import streamlit as st
import numpy as np
import pandas as pd
from datetime import datetime, date
from math import log

st.set_page_config(page_title="이 약 먹어도 될까?", page_icon="💊", layout="wide")

DRUGS = {
"타이레놀정500mg":{"ingredients":{"아세트아미노펜":500},"group":"비NSAID 해열진통제","dose":"1회 1~2정, 4~6시간 간격, 1일 3~4회","interval":4,"max_times":4,"max_units":None},
"이지엔6 에이스":{"ingredients":{"아세트아미노펜":325},"group":"비NSAID 해열진통제","dose":"1회 2캡슐, 4~6시간 간격, 1일 3~4회","interval":4,"max_times":4,"max_units":None},
"이지엔6 애니":{"ingredients":{"이부프로펜":200},"group":"NSAID","dose":"경증·중등도 통증: 1회 1~2캡슐, 1일 3~4회","interval":None,"max_times":4,"max_units":None},
"이지엔6 이브":{"ingredients":{"이부프로펜":200,"파마브롬":25},"group":"NSAID 복합제","dose":"만 15세 이상 1회 1~2캡슐, 4시간 이상 간격, 1일 1~3회","interval":4,"max_times":3,"max_units":None},
"이지엔6 프로":{"ingredients":{"덱시부프로펜":300},"group":"NSAID","dose":"성인 1회 1캡슐, 1일 2~4회, 1일 4캡슐(1,200mg) 초과 금지","interval":None,"max_times":4,"max_units":4},
"애드빌 리퀴겔":{"ingredients":{"이부프로펜":200},"group":"NSAID","dose":"경증·중등도 통증: 성인 1회 1~2캡슐, 1일 3~4회","interval":None,"max_times":4,"max_units":None},
"탁센":{"ingredients":{"나프록센":250},"group":"NSAID","dose":"월경곤란증: 초회 2캡슐, 이후 6~8시간마다 1캡슐","interval":6,"max_times":None,"max_units":None},
"게보린정":{"ingredients":{"아세트아미노펜":300,"이소프로필안티피린":150,"카페인":50},"group":"복합 진통제","dose":"성인 1회 1정, 4시간 이상 간격, 1일 3회까지","interval":4,"max_times":3,"max_units":None},
"게보린 소프트":{"ingredients":{"이부프로펜":250,"파마브롬":25},"group":"NSAID 복합제","dose":"1회 1캡슐, 4시간 이상 간격, 1일 1~3회","interval":4,"max_times":3,"max_units":None},
"펜잘큐정":{"ingredients":{"아세트아미노펜":300,"에텐자미드":200,"카페인무수물":50},"group":"복합 진통제","dose":"만 15세 이상 1회 1정, 1일 3회, 4시간 이상 간격, 빈속을 피하여 복용","interval":4,"max_times":3,"max_units":None},
}
NSAIDS={"이부프로펜","덱시부프로펜","나프록센"}

# 아세트아미노펜만 국내 의약품 허가사항(식약처 의약품통합정보시스템)에
# 명확한 성분 단위 1일 최대량(4,000mg, 간손상 위험 경고)이 있어
# 이 성분에 한해 누적량 계산을 적용한다.
# 다른 성분은 문헌마다 자율관리 기준 수치가 달라, 제품별 공식 허가사항
# (interval / max_times / max_units)만으로 판단한다.
DAILY_MAX_MG = {
    "아세트아미노펜": 4000,
}

# 문헌상 반감기가 비교적 명확히 확인되는 성분만 약물 농도 모델에 포함한다.
# (이소프로필안티피린, 파마브롬, 에텐자미드, 카페인무수물 등은
#  신뢰할 만한 반감기 자료를 확인하지 못해 모델링하지 않는다.)
HALF_LIFE_HOURS = {
    "아세트아미노펜": 2.5,   # 화학Ⅱ 탐구에서 사용한 값(약 150분)과 동일
    "아세틸살리실산": 0.33,  # 화학Ⅱ 탐구에서 사용한 값(약 20분)과 동일
    "이부프로펜": 2.0,
    "나프록센": 14.0,
    "카페인": 5.0,
}
NOT_MODELED = ["이소프로필안티피린", "파마브롬", "에텐자미드", "카페인무수물", "덱시부프로펜"]

def esc(text):
    """물결표(~)가 Streamlit 마크다운에서 아래첨자로 오인되어
    글씨가 겹쳐 보이는 문제를 막기 위한 이스케이프 처리."""
    return text.replace("~", "\\~")

if "records" not in st.session_state: st.session_state.records=[]

def alert_card(level, title, summary, detail_lines=None):
    """레벨별 색상 카드 + '왜 이런 결과인가요?' 근거 펼침 영역을 함께 그림"""
    icon = {"red": "🔴", "orange": "🟠", "yellow": "🟡"}[level]
    box = st.error if level == "red" else st.warning
    box(f"{icon} **{title}**\n\n{summary}")
    if detail_lines:
        with st.expander("왜 이런 결과인가요?"):
            for line in detail_lines:
                st.write(line)

def check_new_drug(records, new_drug, new_units, now):
    """지금 먹으려는 약(new_drug) 하나를 기존 기록(records)과 비교해 판정한다.
    반환값: [(level, title, summary, detail_lines), ...]
    level: red > orange > yellow 순으로 심각도가 높다고 간주함(표시 순서용)."""
    results = []
    new_ing = DRUGS[new_drug]["ingredients"]

    # 1단계) 동일 유효성분 중복 확인
    for ing in new_ing:
        prior = sorted({r["drug"] for r in records
                         if ing in DRUGS[r["drug"]]["ingredients"] and r["drug"] != new_drug})
        if prior:
            detail = [
                f"확인된 사항 · 동일 성분({ing}) 중복",
                f"이전 약 · {', '.join(prior)} → {ing}",
                f"추가 약 · {new_drug} → {ing}",
                "같은 성분을 서로 다른 제품명으로 중복 복용하면 1일 최대량을 인지하지 못한 채 초과할 위험이 있습니다.",
            ]
            results.append(("red", "동일 유효성분 중복 확인",
                             f"{ing} 성분이 이미 기록된 {', '.join(prior)}와(과) 중복됩니다.", detail))

    # 2단계) 동일·유사 약물 계열(NSAID) 병용 주의
    new_nsaid = {i for i in new_ing if i in NSAIDS}
    if new_nsaid:
        prior_nsaid = {i for r in records for i in DRUGS[r["drug"]]["ingredients"]
                       if i in NSAIDS and i not in new_nsaid}
        if prior_nsaid:
            prior_drug_names = sorted({r["drug"] for r in records
                                        if any(i in prior_nsaid for i in DRUGS[r["drug"]]["ingredients"])})
            detail = [
                "확인된 사항 · 동일 NSAID 계열 중복",
                f"이전 약 · {', '.join(prior_drug_names)} → {', '.join(sorted(prior_nsaid))} → NSAID",
                f"추가 약 · {new_drug} → {', '.join(sorted(new_nsaid))} → NSAID",
                "두 약은 성분은 다르지만 같은 약물 계열(NSAID)에 속합니다. 함께 복용하면 위장 자극·출혈 등 부작용 위험이 커질 수 있습니다.",
            ]
            results.append(("orange", "동일·유사 약물 계열 병용 주의",
                             f"이미 기록된 {', '.join(sorted(prior_nsaid))}과(와) 새로 선택한 "
                             f"{', '.join(sorted(new_nsaid))} 모두 NSAID 계열입니다.", detail))

    # 3단계) 제품의 공식 복용 기준 추가 확인 (간격 / 1일 횟수 / 1일 최대량)
    same_product = sorted([r for r in records if r["drug"] == new_drug], key=lambda r: r["dt"])
    interval = DRUGS[new_drug]["interval"]
    if same_product and interval:
        last = same_product[-1]
        gap = (now - last["dt"]).total_seconds() / 3600
        if gap < interval:
            remaining = interval - gap
            results.append(("yellow", "제품의 공식 복용 기준 추가 확인",
                             f"{new_drug}: 마지막 복용 후 {gap:.1f}시간 지났습니다. "
                             f"등록된 최소 간격은 {interval}시간이므로 약 {remaining:.1f}시간 더 기다리세요.", None))

    today = now.date()
    today_same = [r for r in same_product if r["dt"].date() == today]
    max_times = DRUGS[new_drug]["max_times"]
    max_units = DRUGS[new_drug]["max_units"]

    if max_times and len(today_same) + 1 > max_times:
        results.append(("yellow", "제품의 공식 복용 기준 추가 확인",
                         f"{new_drug}: 오늘 이미 {len(today_same)}회 복용했습니다. "
                         f"지금 먹으면 {len(today_same)+1}회로, 등록된 1일 최대 {max_times}회를 넘습니다.", None))

    if max_units:
        today_units = sum(r["units"] for r in today_same) + new_units
        if today_units > max_units:
            results.append(("yellow", "제품의 공식 복용 기준 추가 확인",
                             f"{new_drug}: 지금 복용분을 포함하면 오늘 총 {today_units:g}정/캡슐로, "
                             f"등록된 최대 {max_units:g}정/캡슐을 넘습니다.", None))

    # 3-1단계) 성분 단위 1일 누적량 확인 (아세트아미노펜만, 공식 최대량 4,000mg 근거 명확)
    for ing, limit in DAILY_MAX_MG.items():
        if ing not in new_ing:
            continue
        today_mg = 0.0
        for r in records:
            if r["dt"].date() == today and ing in DRUGS[r["drug"]]["ingredients"]:
                today_mg += DRUGS[r["drug"]]["ingredients"][ing] * r["units"]
        today_mg += DRUGS[new_drug]["ingredients"][ing] * new_units
        if today_mg > limit:
            results.append(("red", "성분 누적 최대량 확인",
                             f"{ing} 오늘 누적 예상량 {today_mg:g}mg — 허가사항상 1일 최대 {limit:g}mg을 초과합니다. "
                             "간손상 등 심각한 부작용 위험이 있습니다.",
                             [f"확인된 사항 · {ing} 1일 누적 초과",
                              f"오늘 누적(지금 복용분 포함) · {today_mg:g}mg / 최대 {limit:g}mg"]))

    return results

st.title("💊 Pill Checker")
st.caption("만 15세 이상 사용자를 위한 생리통 진통제 성분·복용기록 확인 도구")
st.info("성분 중복, 동일·유사 약물 계열 병용, 제품별 공식 복용 기준을 확인합니다. '안전함' 또는 '복용 가능함'을 판정하지 않습니다.")

tab1, tab2, tab3, tab4 = st.tabs(["💊 복약 확인", "📋 제품·성분 데이터", "📊 약물 농도 모델", "📚 탐구 원리와 한계"])

with tab1:
    st.subheader("1. 복용 기록")
    st.caption("오늘 이미 먹은 약을 추가해 주세요.")

    drug=st.selectbox("제품 선택",list(DRUGS), key="record_drug")
    x=DRUGS[drug]
    st.write("**유효성분:** "+" · ".join(f"{k} {v:g} mg" for k,v in x["ingredients"].items()))
    st.write(f"**공식 용법·용량 요약:** {esc(x['dose'])}")

    c1,c2,c3=st.columns(3)
    units=c1.number_input("복용 수량",0.5,10.0,1.0,0.5, key="record_units")
    d=c2.date_input("복용 날짜",date.today(), key="record_date")
    t=c3.time_input("복용 시각", key="record_time")

    if st.button("기록 추가",type="primary",use_container_width=True):
        st.session_state.records.append({"drug":drug,"units":float(units),"dt":datetime.combine(d,t)})
        st.success("복용 기록을 추가했습니다.")

    if st.session_state.records:
        st.markdown("**복용 타임라인**")
        for r in sorted(st.session_state.records,key=lambda x:x["dt"]):
            ingredients=", ".join(f"{i} {mg*r['units']:g}mg" for i,mg in DRUGS[r["drug"]]["ingredients"].items())
            st.write(f"**{r['dt']:%Y-%m-%d %H:%M}** · {r['drug']} {r['units']:g}정/캡슐 · {ingredients}")
        if st.button("전체 기록 삭제"):
            st.session_state.records=[]; st.rerun()

    st.divider()

    st.subheader("2. 지금 먹으려는 약")
    st.caption("위 기록과 비교해 성분·계열 중복, 복용 기준을 확인해요.")

    new_drug = st.selectbox("지금 먹을 약", list(DRUGS), key="new_drug")
    nx = DRUGS[new_drug]
    st.write("**유효성분:** "+" · ".join(f"{k} {v:g} mg" for k,v in nx["ingredients"].items()))
    st.write(f"**공식 용법·용량 요약:** {esc(nx['dose'])}")
    new_units = st.number_input("복용 예정 수량", 0.5, 10.0, 1.0, 0.5, key="new_units")

    if st.button("지금 먹어도 되는지 확인하기", type="primary", use_container_width=True):
        now = datetime.now()
        results = check_new_drug(st.session_state.records, new_drug, float(new_units), now)

        if not st.session_state.records:
            st.success("🟢 아직 기록된 복용 이력이 없어 확인할 중복이 없습니다.")
        elif not results:
            st.success("🟢 현재 입력된 기록에서 등록된 중복·병용 주의 항목이 확인되지 않았습니다.")
        else:
            # red -> orange -> yellow 순으로 정렬해 심각도 높은 항목을 먼저 보여줌
            order = {"red": 0, "orange": 1, "yellow": 2}
            for level, title, summary, detail in sorted(results, key=lambda r: order[r[0]]):
                alert_card(level, title, summary, detail)

        st.session_state["_pending_new"] = {"drug": new_drug, "units": float(new_units), "dt": now}

    if st.session_state.get("_pending_new"):
        if st.button("지금 복용으로 기록에 추가"):
            st.session_state.records.append(st.session_state.pop("_pending_new"))
            st.success("복용 기록에 추가했습니다.")
            st.rerun()

with tab2:
    for name,x in DRUGS.items():
        with st.expander(name):
            st.write("**유효성분:** "+" · ".join(f"{k} {v:g} mg" for k,v in x["ingredients"].items()))
            st.write(f"**분류:** {x['group']}")
            st.write(f"**공식 용법·용량 요약:** {esc(x['dose'])}")
            st.caption("허가사항에 명시되지 않은 간격·최대량은 임의로 계산하지 않았습니다.")

with tab3:
    st.subheader("약물 농도 모델 (1차 소실 모델)")
    st.caption("화학Ⅱ·미적분 탐구에서 다룬 1차 반응속도식 C(t) = C₀ × e^(−kt)을 그대로 시각화합니다.")

    modeled = list(HALF_LIFE_HOURS.keys())
    ing_choice = st.selectbox("성분 선택 (문헌상 반감기가 확인된 성분만 표시)", modeled)
    c0 = st.number_input("초기 복용량(mg)", 10.0, 2000.0, 500.0, 10.0)

    half_life = HALF_LIFE_HOURS[ing_choice]
    k = log(2) / half_life
    t = np.linspace(0, 24, 241)
    c = c0 * np.exp(-k * t)
    df = pd.DataFrame({"혈중 농도(mg, 이론값)": c}, index=pd.Index(t, name="시간(h)"))
    st.line_chart(df)
    st.caption(f"{ing_choice}의 반감기 {half_life}시간을 기준으로 계산한 이론적 감소 곡선입니다.")

    st.warning(
        "⚠ 이 그래프는 혈중농도의 이론적 감소를 나타낼 뿐, 실제 복용 가능 시점을 결정하지 않습니다. "
        "약효 지속시간과 혈중농도 소실은 일치하지 않을 수 있습니다."
    )
    st.caption("모델링하지 않은 성분(신뢰할 만한 반감기 자료를 확인하지 못함): " + ", ".join(NOT_MODELED))

with tab4:
    st.markdown("""### 판정 구조
1. **동일 유효성분 중복 확인** 🔴
2. **동일·유사 약물 계열 병용 주의** 🟠
3. **제품의 공식 복용 기준 추가 확인** 🟡 (최소 간격, 1일 횟수, 제품별 최대량 — 허가사항에 없는 값은 임의 계산하지 않음)
4. **성분 누적 최대량 확인** 🔴 (아세트아미노펜에 한해 공식 1일 최대량 4,000mg 기준으로 누적 계산)
5. **해당 없음** 🟢 (현재 입력된 기록에서 등록된 중복·병용 주의 항목이 확인되지 않음 — '안전함'·'복용 가능'으로 표현하지 않음)

### 한계
이 프로그램은 만 15세 이상을 대상으로 한 교육·정보 제공용 탐구 도구입니다. 체중, 임신 여부, 알레르기, 간·신장 기능, 위장관 질환, 다른 복용약 등 개인별 임상 변수를 반영하지 않으며 처방·진단·개인별 복용 결정을 대신하지 않습니다. 성분 중복이 확인되지 않았다고 해서 복용 가능성을 프로그램이 보장하지 않으며, 약물 농도 모델 역시 이론적 감소 추세를 보여줄 뿐 실제 복용 가능 시점을 결정하지 않습니다.
""")
