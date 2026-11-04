import re
from collections import Counter
from itertools import combinations
import pandas as pd
import plotly.express as px
import streamlit as st

# 페이지 기본 설정
st.set_page_config(page_title="급식 규칙 찾기", layout="wide")
st.title("🍽️ 급식 연관 규칙 분석기")

# 데이터 로드 주소
DATA_URL = "https://raw.githubusercontent.com/it-teacher-go/data-share-/main/songtan_meals_184.csv"


@st.cache_data
def load_and_process_data():
    # CSV 로드
    df = pd.read_csv(DATA_URL, encoding="utf-8")

    baskets = []
    all_items = set()

    for menu_str in df["메뉴"].dropna():
        if not isinstance(menu_str, str):
            continue

        # 세로줄(|) 구분자로 메뉴 분리
        raw_items = menu_str.split("|")
        cleaned_items = set()

        for item in raw_items:
            # 괄호 및 괄호 내부 텍스트 제거 + 양끝 공백 제거
            cleaned = re.sub(r"\(.*?\)", "", item).strip()
            if cleaned:
                cleaned_items.add(cleaned)
                all_items.add(cleaned)

        if cleaned_items:
            baskets.append(cleaned_items)

    total_baskets = len(baskets)

    # 1. 개별 메뉴 등장 횟수 계산
    item_counts = Counter()
    for basket in baskets:
        for item in basket:
            item_counts[item] += 1

    # 2. 동시 출현 메뉴 쌍 횟수 계산
    pair_counts = Counter()
    for basket in baskets:
        if len(basket) >= 2:
            for item1, item2 in combinations(sorted(basket), 2):
                pair_counts[(item1, item2)] += 1

    # 3. 연관 규칙 계산 (A -> B, B -> A)
    rules_list = []
    for (item1, item2), count in pair_counts.items():
        support = count / total_baskets

        # A -> B 규칙
        conf_a_b = count / item_counts[item1]
        lift_a_b = conf_a_b / (item_counts[item2] / total_baskets)
        rules_list.append(
            {
                "조건": item1,
                "결과": item2,
                "동시": count,
                "지지도": round(support, 4),
                "신뢰도": round(conf_a_b, 4),
                "향상도": round(lift_a_b, 4),
            }
        )

        # B -> A 규칙 (조건-결과 반대)
        conf_b_a = count / item_counts[item2]
        lift_b_a = conf_b_a / (item_counts[item1] / total_baskets)
        rules_list.append(
            {
                "조건": item2,
                "결과": item1,
                "동시": count,
                "지지도": round(support, 4),
                "신뢰도": round(conf_b_a, 4),
                "향상도": round(lift_b_a, 4),
            }
        )

    rules_df = pd.DataFrame(rules_list)

    return (
        total_baskets,
        len(all_items),
        len(pair_counts),
        rules_df,
        sorted(list(all_items)),
        item_counts,
        pair_counts,
    )


# 데이터 파싱 수행 (튜플 언패킹 괄호 완전 닫음)
processed_data = load_and_process_data()
total_days = processed_data[0]
total_menu_types = processed_data[1]
total_pairs = processed_data[2]
rules_df = processed_data[3]
all_menu_list = processed_data[4]
item_counts = processed_data[5]
pair_counts = processed_data[6]

# 요약 정보 표시
st.markdown(
    f"**급식 일수:** {total_days}일 &nbsp;|&nbsp; **메뉴 종류 수:** {total_menu_types}개 &nbsp;|&nbsp; **함께 나온 메뉴 쌍 수:** {total_pairs}쌍"
)
st.write("---")

# 컨트롤바 영역 (필터링, 슬라이더, 정렬)
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    selected_menu = st.selectbox(
        "메뉴 선택 (전체 보기 또는 특정 메뉴 포함 규칙 필터링):",
        ["전체"] + all_menu_list,
    )

with col2:
    min_cooccurrence = st.slider(
        "최소 동시 일수:", min_value=1, max_value=10, value=1
    )

with col3:
    sort_by = st.selectbox("정렬 기준:", ["향상도", "신뢰도", "동시"])

# 동시 일수 필터링
filtered_df = rules_df[rules_df["동시"] >= min_cooccurrence].copy()

# 특정 메뉴 선택 필터링
if selected_menu != "전체":
    filtered_df = filtered_df[
        (filtered_df["조건"] == selected_menu) | (filtered_df["결과"] == selected_menu)
    ]

# 필터링 후 남은 규칙 수 안내
st.info(f"💡 현재 조건에 맞게 남은 규칙: **{len(filtered_df)}개**")

# 정렬
filtered_df = filtered_df.sort_values(by=sort_by, ascending=False).reset_index(drop=True)

# Plotly 가로 막대그래프 (향상도 Top 10)
st.subheader("📊 향상도 상위 10개 규칙")
top10_df = filtered_df.sort_values(by="향상도", ascending=False).head(10).copy()

if not top10_df.empty:
    top10_df["규칙"] = top10_df["조건"] + " ➔ " + top10_df["결과"]
    top10_df = top10_df.sort_values(by="향상도", ascending=True)

    fig = px.bar(
        top10_df,
        x="향상도",
        y="규칙",
        orientation="h",
        text="향상도",
        title=f"향상도 Top 10 ({'전체' if selected_menu == '전체' else selected_menu})",
        labels={"향상도": "향상도 (Lift)", "규칙": "메뉴 규칙 (조건 ➔ 결과)"},
    )
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("선택한 조건에 해당하는 규칙이 없습니다.")

# 규칙 데이터표 출력
st.subheader("📋 연관 규칙 데이터")
st.dataframe(filtered_df, use_container_width=True)

st.write("---")

# 함께 나온 적 없는 짝 기능
st.subheader("🚫 함께 나온 적 없는 짝 찾아보기")

target_menu = st.selectbox(
    "조회할 대상 메뉴를 선택하세요:",
    all_menu_list,
    key="unpaired_menu_select",
)

target_days = item_counts[target_menu]

# 대상 메뉴와 함께 출현한 적 있는 메뉴 집합
