import streamlit as st
from datetime import datetime, date

st.set_page_config(page_title="Pill Checker", page_icon="💊", layout="wide")

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

if "records" not in st.session_state: st.session_state.records=[]

def analyze(records):
    alerts=[]
    ip={}
    for r in records:
        for ing in DRUGS[r["drug"]]["ingredients"]: ip.setdefault(ing,set()).add(r["drug"])
    for ing,products in ip.items():
        if len(products)>=2:
            alerts.append(("red","동일 유효성분 중복 확인",f"{ing}이(가) 여러 제품에 포함됩니다: {', '.join(sorted(products))}"))
    nsaids={ing for r in records for ing in DRUGS[r["drug"]]["ingredients"] if ing in NSAIDS}
    if len(nsaids)>=2:
        alerts.append(("orange","동일·유사 약물 계열 병용 주의",f"서로 다른 NSAID 계열 성분이 함께 기록되었습니다: {', '.join(sorted(nsaids))}"))
    for drug in DRUGS:
        rs=sorted([r for r in records if r["drug"]==drug],key=lambda x:x["dt"])
        iv=DRUGS[drug]["interval"]
        if iv:
            for a,b in zip(rs,rs[1:]):
                if a["dt"].date()==b["dt"].date():
                    gap=(b["dt"]-a["dt"]).total_seconds()/3600
                    if gap<iv: alerts.append(("yellow","제품별 공식 복용 간격 확인",f"{drug}: 기록 간격 {gap:.1f}시간으로 등록된 최소 간격 {iv}시간보다 짧습니다."))
        for day in {r["dt"].date() for r in rs}:
            dayrs=[r for r in rs if r["dt"].date()==day]
            mt=DRUGS[drug]["max_times"]
            mu=DRUGS[drug]["max_units"]
            if mt and len(dayrs)>mt: alerts.append(("yellow","1일 복용 횟수 확인",f"{day} {drug}: {len(dayrs)}회 기록되어 등록된 1일 최대 {mt}회를 넘습니다."))
            if mu and sum(r["units"] for r in dayrs)>mu: alerts.append(("yellow","1일 최대량 확인",f"{day} {drug}: 총 {sum(r['units'] for r in dayrs):g}정/캡슐로 등록된 최대 {mu:g}정/캡슐을 넘습니다."))
    return alerts

st.title("💊 Pill Checker")
st.caption("만 15세 이상 사용자를 위한 생리통 진통제 성분·복용기록 확인 도구")
st.info("성분 중복, 동일·유사 약물 계열 병용, 제품별 공식 복용 기준을 확인합니다. ‘안전함’ 또는 ‘복용 가능함’을 판정하지 않습니다.")

tab1,tab2,tab3=st.tabs(["복용 기록 확인","제품·성분 데이터","탐구 원리와 한계"])
with tab1:
    drug=st.selectbox("제품 선택",list(DRUGS))
    x=DRUGS[drug]
    st.write("**유효성분:** "+" · ".join(f"{k} {v:g} mg" for k,v in x["ingredients"].items()))
    st.write(f"**공식 용법·용량 요약:** {x['dose']}")
    c1,c2,c3=st.columns(3)
    units=c1.number_input("복용 수량",0.5,10.0,1.0,0.5)
    d=c2.date_input("복용 날짜",date.today())
    t=c3.time_input("복용 시각")
    if st.button("기록 추가",type="primary",use_container_width=True):
        st.session_state.records.append({"drug":drug,"units":float(units),"dt":datetime.combine(d,t)})
        st.success("복용 기록을 추가했습니다.")
    if st.session_state.records:
        st.subheader("복용 타임라인")
        for r in sorted(st.session_state.records,key=lambda x:x["dt"]):
            ingredients=", ".join(f"{i} {mg*r['units']:g}mg" for i,mg in DRUGS[r["drug"]]["ingredients"].items())
            st.write(f"**{r['dt']:%Y-%m-%d %H:%M}** · {r['drug']} {r['units']:g}정/캡슐 · {ingredients}")
        st.subheader("확인 결과")
        alerts=analyze(st.session_state.records)
        if not alerts:
            st.success("🟢 현재 입력 기록에서 등록된 중복·병용 주의·제품별 기준 초과 항목이 확인되지 않았습니다.")
            st.caption("의학적 안전성 또는 복용 가능 여부를 의미하지 않습니다.")
        for level,title,msg in alerts:
            if level=="red": st.error(f"🔴 **{title}**\n\n{msg}")
            elif level=="orange": st.warning(f"🟠 **{title}**\n\n{msg}")
            else: st.warning(f"🟡 **{title}**\n\n{msg}")
        if st.button("전체 기록 삭제"):
            st.session_state.records=[]; st.rerun()

with tab2:
    for name,x in DRUGS.items():
        with st.expander(name):
            st.write("**유효성분:** "+" · ".join(f"{k} {v:g} mg" for k,v in x["ingredients"].items()))
            st.write(f"**분류:** {x['group']}")
            st.write(f"**공식 용법·용량 요약:** {x['dose']}")
            st.caption("허가사항에 명시되지 않은 간격·최대량은 임의로 계산하지 않았습니다.")

with tab3:
    st.markdown("""### 판정 구조
1. **동일 유효성분 중복 확인**
2. **동일·유사 약물 계열 병용 주의**
3. **제품별 공식 복용 기준 확인**
4. **허가사항에 없는 값은 임의 계산하지 않음**

### 한계
이 프로그램은 만 15세 이상을 대상으로 한 교육·정보 제공용 탐구 도구입니다. 체중, 임신 여부, 알레르기, 간·신장 기능, 위장관 질환, 다른 복용약 등 개인별 임상 변수를 반영하지 않으며 처방·진단·개인별 복용 결정을 대신하지 않습니다.
""")
