import streamlit as st
import requests
import pandas as pd
import re
from datetime import date, timedelta
import plotly.express as px


# --------------------------------------------------
# 기본 설정
# --------------------------------------------------
st.set_page_config(
    page_title="학교 급식 원산지 탐구",
    page_icon="🍚",
    layout="wide"
)

st.title("🍚 학교 급식 원산지 탐구")
st.write("주변 학교 급식에 쓰인 재료들의 원산지를 살펴봅니다.")


# --------------------------------------------------
# 나이스 API 설정
# --------------------------------------------------
BASE_URL = "https://open.neis.go.kr/hub"

try:
    API_KEY = st.secrets["NEIS_KEY"]
except Exception:
    API_KEY = ""


# --------------------------------------------------
# 학교 검색
# --------------------------------------------------
def search_school(school_name):
    url = f"{BASE_URL}/schoolInfo"

    params = {
        "KEY": API_KEY,
        "Type": "json",
        "pIndex": 1,
        "pSize": 5,
        "SCHUL_NM": school_name
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()

    data = response.json()

    if "schoolInfo" not in data:
        return pd.DataFrame()

    try:
        rows = data["schoolInfo"][1]["row"]
    except (KeyError, IndexError):
        return pd.DataFrame()

    return pd.DataFrame(rows)


# --------------------------------------------------
# 급식 데이터 가져오기
# --------------------------------------------------
def get_meals(atpt_code, school_code, start_date, end_date):

    all_rows = []
    page = 1

    while True:

        url = f"{BASE_URL}/mealServiceDietInfo"

        params = {
            "KEY": API_KEY,
            "Type": "json",
            "ATPT_OFCDC_SC_CODE": atpt_code,
            "SD_SCHUL_CODE": school_code,
            "MMEAL_SC_CODE": "2",
            "MLSV_FROM_YMD": start_date,
            "MLSV_TO_YMD": end_date,
            "pSize": 1000,
            "pIndex": page
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        if "mealServiceDietInfo" not in data:
            break

        try:
            head = data["mealServiceDietInfo"][0]["head"]
            rows = data["mealServiceDietInfo"][1]["row"]
        except (KeyError, IndexError):
            break

        all_rows.extend(rows)

        # 전체 데이터 개수 확인
        total_count = 0

        try:
            for item in head:
                if "list_total_count" in item:
                    total_count = int(item["list_total_count"])
                    break
        except Exception:
            pass

        if len(all_rows) >= total_count or len(rows) < 1000:
            break

        page += 1

    return pd.DataFrame(all_rows)


# --------------------------------------------------
# 원산지 정보에서 국가 추출
# --------------------------------------------------
def extract_origins(text):

    if not isinstance(text, str):
        return []

    origins = []

    # 줄바꿈 / <br/> 등 정리
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)

    lines = text.splitlines()

    for line in lines:

        line = line.strip()

        if not line:
            continue

        # 예:
        # 쌀 : 국내산
        # 돼지고기 : 국내산
        # 쇠고기 : 호주산
        # 닭고기 : 국내산
        if ":" in line:
            parts = line.split(":", 1)
            origin = parts[1].strip()

        elif "：" in line:
            parts = line.split("：", 1)
            origin = parts[1].strip()

        else:
            continue

        # 여러 국가가 섞여 있는 경우
        # 쉼표, / 등으로 나누어 처리
        origin_parts = re.split(r"[,/]", origin)

        for item in origin_parts:

            item = item.strip()

            if not item:
                continue

            # 괄호 안 설명 제거
            item = re.sub(r"\([^)]*\)", "", item).strip()

            # 대표적인 표기 정리
            if "국내산" in item or "국산" in item:
                origins.append("국내산")
            elif "호주" in item:
                origins.append("호주")
            elif "미국" in item:
                origins.append("미국")
            elif "중국" in item:
                origins.append("중국")
            elif "브라질" in item:
                origins.append("브라질")
            elif "뉴질랜드" in item:
                origins.append("뉴질랜드")
            elif "캐나다" in item:
                origins.append("캐나다")
            elif "스페인" in item:
                origins.append("스페인")
            elif "러시아" in item:
                origins.append("러시아")
            elif "베트남" in item:
                origins.append("베트남")
            elif "필리핀" in item:
                origins.append("필리핀")
            elif "태국" in item:
                origins.append("태국")
            elif "칠레" in item:
                origins.append("칠레")
            elif "아르헨티나" in item:
                origins.append("아르헨티나")
            elif "독일" in item:
                origins.append("독일")
            elif "이탈리아" in item:
                origins.append("이탈리아")
            elif "프랑스" in item:
                origins.append("프랑스")
            elif "영국" in item:
                origins.append("영국")
            elif "일본" in item:
                origins.append("일본")
            else:
                # '국내산 및 호주산' 같은 경우를 위해
                # 국가명이 포함되어 있으면 그대로 사용
                if "산" in item:
                    origins.append(item)

    return origins


# --------------------------------------------------
# API 키 확인
# --------------------------------------------------
if not API_KEY:
    st.error("NEIS_KEY가 설정되어 있지 않습니다.")
    st.info(
        "Streamlit Cloud의 Settings → Secrets에서 "
        "NEIS_KEY를 추가해 주세요."
    )
    st.stop()


# --------------------------------------------------
# 학교 입력
# --------------------------------------------------
st.subheader("1. 학교 찾기")

school_name = st.text_input(
    "학교 이름을 입력하세요",
    placeholder="예: ○○중학교"
)

if school_name:

    try:
        schools = search_school(school_name)

        if schools.empty:
            st.warning("검색된 학교가 없습니다.")
            st.stop()

        # 학교 선택용 표시
        school_options = []

        for _, row in schools.iterrows():
            name = row.get("SCHUL_NM", "")
            location = row.get("LCTN_SC_NM", "")
            school_options.append(f"{name} ({location})")

        selected = st.selectbox(
            "학교를 선택하세요",
            school_options
        )

        selected_index = school_options.index(selected)
        school = schools.iloc[selected_index]

        school_name_real = school["SCHUL_NM"]
        atpt_code = school["ATPT_OFCDC_SC_CODE"]
        school_code = school["SD_SCHUL_CODE"]

        st.success(f"선택한 학교: {school_name_real}")

    except Exception as e:
        st.error("학교 정보를 가져오는 중 문제가 발생했습니다.")
        st.stop()


    # --------------------------------------------------
    # 기간 선택
    # --------------------------------------------------
    st.subheader("2. 조사 기간")

    today = date.today()
    default_start = today - timedelta(days=30)

    col1, col2 = st.columns(2)

    with col1:
        start = st.date_input(
            "시작일",
            value=default_start,
            max_value=today
        )

    with col2:
        end = st.date_input(
            "끝일",
            value=today,
            max_value=today
        )

    if start > end:
        st.error("시작일이 끝일보다 늦을 수 없습니다.")
        st.stop()


    # --------------------------------------------------
    # 급식 조회
    # --------------------------------------------------
    if st.button("🍚 급식 원산지 분석하기", type="primary"):

        start_str = start.strftime("%Y%m%d")
        end_str = end.strftime("%Y%m%d")

        with st.spinner("급식 정보를 가져오고 있습니다..."):

            try:
                meals = get_meals(
                    atpt_code,
                    school_code,
                    start_str,
                    end_str
                )
            except Exception as e:
                st.error("급식 정보를 가져오는 중 오류가 발생했습니다.")
                st.stop()


        if meals.empty:
            st.warning(
                "선택한 기간에 중식 급식 자료가 없습니다."
            )
            st.stop()


        # --------------------------------------------------
        # 원산지 정보 확인
        # --------------------------------------------------
        origin_column = None

        # 나이스 데이터에서 사용되는 원산지 컬럼을 우선 확인
        for column in [
            "ORPLC_INFO",
            "ORPLC_INFO"
        ]:
            if column in meals.columns:
                origin_column = column
                break

        if origin_column is None:
            st.error(
                "급식 자료에서 원산지 정보 열을 찾지 못했습니다."
            )
            st.stop()


        # --------------------------------------------------
        # 원산지 추출
        # --------------------------------------------------
        origin_list = []

        for _, row in meals.iterrows():

            origins = extract_origins(
                row.get(origin_column, "")
            )

            for origin in origins:
                origin_list.append({
                    "급식일": row.get("MLSV_YMD", ""),
                    "원산지": origin
                })


        origin_df = pd.DataFrame(origin_list)


        if origin_df.empty:
            st.warning(
                "선택한 기간의 급식 자료에서 "
                "분석할 원산지 정보를 찾지 못했습니다."
            )
            st.stop()


        # --------------------------------------------------
        # 원산지별 집계
        # --------------------------------------------------
        counts = (
            origin_df["원산지"]
            .value_counts()
            .reset_index()
        )

        counts.columns = ["원산지", "등장 횟수"]

        counts = counts.sort_values(
            "등장 횟수",
            ascending=False
        )


        # --------------------------------------------------
        # 가장 많이 나온 원산지
        # --------------------------------------------------
        top_origin = counts.iloc[0]["원산지"]
        top_count = counts.iloc[0]["등장 횟수"]


        st.divider()

        st.subheader("3. 분석 결과")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "급식일 수",
                f"{len(meals):,}일"
            )

        with col2:
            st.metric(
                "확인한 원산지 기록",
                f"{len(origin_df):,}건"
            )

        with col3:
            st.metric(
                "가장 많이 나온 원산지",
                top_origin
            )


        st.success(
            f"🥇 가장 많이 등장한 원산지는 **{top_origin}**입니다. "
            f"총 **{top_count:,}회** 확인되었습니다."
        )


        # --------------------------------------------------
        # 그래프
        # --------------------------------------------------
        st.subheader("4. 원산지별 등장 횟수")

        fig = px.bar(
            counts,
            x="원산지",
            y="등장 횟수",
            text="등장 횟수",
            title="급식에 등장한 원산지"
        )

        fig.update_traces(
            textposition="outside"
        )

        fig.update_layout(
            xaxis_title="원산지",
            yaxis_title="등장 횟수",
            hovermode="x unified"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


        st.write(
            "**이 그래프로 알 수 있는 것:** "
            "선택한 기간 동안 학교 급식 재료의 원산지가 "
            "어디에 많이 분포하는지 비교할 수 있습니다."
        )


        # --------------------------------------------------
        # 집계표
        # --------------------------------------------------
        st.subheader("5. 원산지별 집계표")

        display_df = counts.copy()

        display_df["등장 비율"] = (
            display_df["등장 횟수"]
            / display_df["등장 횟수"].sum()
            * 100
        ).round(1)

        display_df["등장 횟수"] = (
            display_df["등장 횟수"]
            .map(lambda x: f"{x:,}")
        )

        display_df["등장 비율"] = (
            display_df["등장 비율"]
            .map(lambda x: f"{x}%")
        )

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )


        # --------------------------------------------------
        # 원산지 원자료
        # --------------------------------------------------
        with st.expander("원산지 기록 자세히 보기"):

            detail = origin_df.copy()

            detail["급식일"] = pd.to_datetime(
                detail["급식일"],
                format="%Y%m%d",
                errors="coerce"
            ).dt.strftime("%Y-%m-%d")

            st.dataframe(
                detail,
                use_container_width=True,
                hide_index=True
            )

import re
from collections import Counter

import pandas as pd
import requests
import plotly.express as px
import streamlit as st


# --------------------------------------------------
# 기본 설정
# --------------------------------------------------

st.set_page_config(
    page_title="학교 급식 원산지 분석",
    page_icon="🍚",
    layout="wide"
)

st.title("🍚 학교 급식 원산지 분석")
st.subheader("주변 학교 급식에 쓰인 재료들 중 가장 많은 원산지는 어디일까?")

st.write(
    "학교 이름을 입력하면 나이스 교육정보 개방 포털에서 "
    "학교와 급식 정보를 찾아 원산지를 분석합니다."
)


# --------------------------------------------------
# NEIS API
# --------------------------------------------------

SCHOOL_API = "https://open.neis.go.kr/hub/schoolInfo"
MEAL_API = "https://open.neis.go.kr/hub/mealServiceDietInfo"


# --------------------------------------------------
# 학교 검색
# --------------------------------------------------

@st.cache_data(ttl=3600)
def find_school(school_name):
    params = {
        "Type": "json",
        "SCHUL_NM": school_name,
    }

    response = requests.get(SCHOOL_API, params=params, timeout=10)
    response.raise_for_status()

    data = response.json()

    try:
        rows = data["schoolInfo"][1]["row"]
    except (KeyError, IndexError):
        return pd.DataFrame()

    result = []

    for row in rows:
        result.append({
            "학교명": row.get("SCHUL_NM", ""),
            "교육청코드": row.get("ATPT_OFCDC_SC_CODE", ""),
            "학교코드": row.get("SD_SCHUL_CODE", ""),
            "지역": row.get("LCTN_SC_NM", ""),
        })

    return pd.DataFrame(result)


# --------------------------------------------------
# 급식 데이터 가져오기
# --------------------------------------------------

@st.cache_data(ttl=3600)
def get_meals(office_code, school_code, start_date, end_date):

    params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": office_code,
        "SD_SCHUL_CODE": school_code,
        "MMEAL_SC_CODE": "2",
        "MLSV_FROM_YMD": start_date,
        "MLSV_TO_YMD": end_date,
        "pSize": "1000",
        "pIndex": "1",
    }

    response = requests.get(MEAL_API, params=params, timeout=10)
    response.raise_for_status()

    data = response.json()

    if "mealServiceDietInfo" not in data:
        return pd.DataFrame()

    try:
        rows = data["mealServiceDietInfo"][1]["row"]
    except (KeyError, IndexError):
        return pd.DataFrame()

    result = []

    for row in rows:
        result.append({
            "급식일": row.get("MLSV_YMD", ""),
            "메뉴": row.get("DDISH_NM", ""),
            "원산지": row.get("ORPLC_INFO", ""),
            "칼로리": row.get("CAL_INFO", ""),
        })

    return pd.DataFrame(result)


# --------------------------------------------------
# 원산지 추출
# --------------------------------------------------

def normalize_origin(origin):
    """
    원산지 표현을 몇 가지 대표적인 형태로 통일한다.
    """

    origin = origin.strip()

    if not origin:
        return None

    # 국내산 / 국내 / 국산 표현 통일
    if re.search(r"국내산|국산|국내", origin):
        return "국내산"

    # 수입산이라는 표현
    if re.search(r"수입산|수입", origin):
        return "수입산"

    # 주요 국가명
    countries = [
        "미국",
        "호주",
        "캐나다",
        "뉴질랜드",
        "중국",
        "베트남",
        "브라질",
        "스페인",
        "프랑스",
        "이탈리아",
        "러시아",
        "노르웨이",
        "태국",
        "필리핀",
        "칠레",
        "아르헨티나",
        "멕시코",
        "독일",
        "인도",
        "인도네시아",
        "대만",
        "일본",
        "터키",
        "덴마크",
        "핀란드",
        "폴란드",
        "우크라이나",
    ]

    for country in countries:
        if country in origin:
            return country

    return None


def extract_origins(origin_text):
    """
    ORPLC_INFO에서 원산지 표현을 찾아 리스트로 반환한다.

    예:
    쌀 : 국내산
    돼지고기 : 국내산
    쇠고기 : 호주산

    → 국내산, 국내산, 호주
    """

    if not origin_text:
        return []

    # HTML 줄바꿈 제거
    text = re.sub(r"<br\s*/?>", "\n", origin_text, flags=re.IGNORECASE)

    # 여러 줄 또는 쉼표 등으로 분리
    parts = re.split(r"[\n,;]+", text)

    origins = []

    for part in parts:
        part = part.strip()

        if not part:
            continue

        # 괄호 안의 원산지도 검사
        normalized = normalize_origin(part)

        if normalized:
            origins.append(normalized)

    return origins


# --------------------------------------------------
# 입력
# --------------------------------------------------

st.markdown("---")

st.header("1. 분석할 학교를 입력하세요")

school_input = st.text_input(
    "학교 이름",
    placeholder="예: ○○중학교, ○○고등학교",
    help="여러 학교를 비교하려면 쉼표(,)로 구분하세요."
)

col1, col2 = st.columns(2)

with col1:
    start_date = st.date_input(
        "조회 시작일",
        value=pd.Timestamp.today() - pd.Timedelta(days=30)
    )

with col2:
    end_date = st.date_input(
        "조회 종료일",
        value=pd.Timestamp.today()
    )


if start_date > end_date:
    st.error("조회 시작일은 종료일보다 빠르거나 같아야 합니다.")
    st.stop()


if not school_input.strip():
    st.info("학교 이름을 입력하면 분석을 시작할 수 있습니다.")
    st.stop()


school_names = [
    name.strip()
    for name in school_input.split(",")
    if name.strip()
]


# --------------------------------------------------
# 학교 검색
# --------------------------------------------------

st.header("2. 학교 찾기")

school_results = []

for name in school_names:

    try:
        schools = find_school(name)

        if schools.empty:
            st.warning(f"'{name}' 학교를 찾지 못했습니다.")
            continue

        # 정확히 일치하는 학교가 있으면 우선 사용
        exact = schools[schools["학교명"] == name]

        if not exact.empty:
            selected = exact.iloc[0]
        else:
            selected = schools.iloc[0]

        school_results.append(selected)

    except Exception as e:
        st.error(f"'{name}' 검색 중 오류가 발생했습니다: {e}")


if not school_results:
    st.stop()


school_df = pd.DataFrame(school_results).drop_duplicates(
    subset=["학교명", "학교코드"]
)

st.dataframe(
    school_df,
    use_container_width=True,
    hide_index=True
)


# --------------------------------------------------
# 급식 데이터 수집
# --------------------------------------------------

st.header("3. 급식 원산지 데이터 가져오기")

all_meals = []

progress = st.progress(0)

for i, school in school_df.iterrows():

    try:
        meals = get_meals(
            school["교육청코드"],
            school["학교코드"],
            start_date.strftime("%Y%m%d"),
            end_date.strftime("%Y%m%d")
        )

        if not meals.empty:
            meals.insert(0, "학교명", school["학교명"])
            meals.insert(1, "지역", school["지역"])

            all_meals.append(meals)

    except Exception as e:
        st.warning(
            f"{school['학교명']}의 급식 데이터를 가져오는 중 오류가 발생했습니다: {e}"
        )

    progress.progress(
        int((i + 1) / len(school_df) * 100)
    )

progress.empty()


if not all_meals:
    st.warning(
        "선택한 기간에 급식 데이터가 없습니다. "
        "조회 기간이나 학교 이름을 확인해 주세요."
    )
    st.stop()


meal_df = pd.concat(all_meals, ignore_index=True)


# --------------------------------------------------
# 원산지 분석
# --------------------------------------------------

origin_counter = Counter()

origin_rows = []

for _, row in meal_df.iterrows():

    origins = extract_origins(row["원산지"])

    for origin in origins:
        origin_counter[origin] += 1

        origin_rows.append({
            "학교명": row["학교명"],
            "급식일": row["급식일"],
            "원산지": origin
        })


if not origin_counter:
    st.warning(
        "조회된 급식 데이터에서 원산지 정보를 찾지 못했습니다."
    )
    st.info(
        "학교에 따라 원산지 정보가 제공되지 않을 수도 있습니다."
    )

    st.subheader("조회된 급식 데이터")
    st.dataframe(
        meal_df,
        use_container_width=True,
        hide_index=True
    )

    st.stop()


origin_df = pd.DataFrame(
    origin_counter.items(),
    columns=["원산지", "사용 횟수"]
).sort_values(
    "사용 횟수",
    ascending=False
).reset_index(drop=True)


# --------------------------------------------------
# 결과
# --------------------------------------------------

st.markdown("---")
st.header("4. 어떤 원산지가 가장 많이 등장했을까?")


top_origin = origin_df.iloc[0]["원산지"]
top_count = int(origin_df.iloc[0]["사용 횟수"])


st.metric(
    "가장 많이 등장한 원산지",
    top_origin,
    f"{top_count}회"
)


fig = px.bar(
    origin_df,
    x="원산지",
    y="사용 횟수",
    text="사용 횟수",
    title="학교 급식 원산지별 사용 횟수"
)

fig.update_traces(
    textposition="outside"
)

fig.update_layout(
    xaxis_title="원산지",
    yaxis_title="사용 횟수",
    height=500
)

st.plotly_chart(
    fig,
    use_container_width=True
)


# --------------------------------------------------
# 학교별 원산지
# --------------------------------------------------

st.header("5. 학교별 원산지 사용 현황")

school_origin_df = pd.DataFrame(origin_rows)

if not school_origin_df.empty:

    school_origin_pivot = pd.crosstab(
        school_origin_df["학교명"],
        school_origin_df["원산지"]
    )

    st.dataframe(
        school_origin_pivot,
        use_container_width=True
    )


# --------------------------------------------------
# 원산지 정보 상세
# --------------------------------------------------

st.header("6. 실제 급식 원산지 정보")

detail_df = meal_df[
    ["학교명", "급식일", "메뉴", "원산지", "칼로리"]
].copy()

detail_df["메뉴"] = (
    detail_df["메뉴"]
    .astype(str)
    .str.replace("<br/>", "\n", regex=False)
    .str.replace("<br>", "\n", regex=False)
)

st.dataframe(
    detail_df,
    use_container_width=True,
    hide_index=True
)


# --------------------------------------------------
# 설명
# --------------------------------------------------

st.markdown("---")

st.caption(
    "※ 원산지 사용 횟수는 나이스 급식정보의 ORPLC_INFO에 기록된 원산지 항목을 기준으로 집계합니다."
)

st.caption(
    "※ 같은 원산지가 여러 급식일의 여러 재료에 등장하면 각각 1회씩 집계됩니다."
)

st.caption(
    "※ 학교마다 원산지 정보의 작성 방식이 달라 실제 재료의 종류나 양을 의미하는 통계는 아닙니다."
)
