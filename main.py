import re
from collections import Counter
from itertools import combinations
import pandas as pd
import plotly.express as px
import streamlit as st

# 페이지 설정
st.set_page_config(page_title="급식 규칙 찾기", layout="wide")
st.title("🍽️ 급식 연관 규칙 분석기")

# 데이터 로드
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

        # 세로줄(|)로 분리
        raw_items = menu_str.split("|")
        cleaned_items = set()

        for item in raw_items:
            # 괄호 및 괄호 안 내용 제거 후 앞뒤 공백 제거
            cleaned = re.sub(r"\(.*?\)", "", item).strip()
            if cleaned:
                cleaned_items.add(cleaned)
                all_items.add(cleaned)

        if cleaned_items:
            baskets.append(cleaned_items)

    total_baskets = len(baskets)

    # 개별 아이템 출현 빈도 계산
    item_counts = Counter()
    for basket in baskets:
        for item in basket:
            item_counts[item] += 1

    # 메뉴 쌍(동시 출현) 빈도 계산
    pair_counts = Counter()
    for basket in baskets:
        if len(basket) >= 2:
            for item1, item2 in combinations(sorted(basket), 2):
                pair_counts[(item1, item2)] += 1

    # 연관 규칙 데이터프레임 생성
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

        # B -> A 규칙 (조건과 결과 변경)
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


# 데이터 준비
(
    total_days,
    total_menu_types,
    total_pairs,
    rules_df,
    all_menu_list,
    item_counts,
    pair_counts,
) = load_and_process_data()

# 요약 정보 출력
st.markdown(
    f"**급식 일수:** {total_days}일 &nbsp;|&nbsp; **메뉴 종류 수:** {total_menu_types}개 &nbsp;|&nbsp; **함께 나온 메뉴 쌍 수:** {total_pairs}쌍"
)
st.write("---")

# 컨트롤 서브바 (필터링, 슬라이더 및 정렬)
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

# 데이터 필터링 (최소 동시 일수 및 특정 메뉴 조건 적용)
filtered_df = rules_df[rules_df["동시"] >= min_cooccurrence].copy()

if selected_menu != "전체":
    filtered_df = filtered_df[
        (filtered_df["조건"] == selected_menu) | (filtered_df["결과"] == selected_menu)
    ]

# 남은 규칙 개수 안내
st.info(f"💡 현재 조건에 맞게 남은 규칙: **{len(filtered_df)}개**")

# 정렬 수행
filtered_df = filtered_df.sort_values(by=sort_by, ascending=False).reset_index(drop=True)

# Plotly 가로 막대그래프 (상위 10개)
st.subheader("📊 향상도 상위 10개 규칙")
top10_df = filtered_df.sort_values(by="향상도", ascending=False).head(10).copy()

if not top10_df.empty:
    top10_df["규칙"] = top10_df["조건"] + " ➔ " + top10_df["결과"]
    top10_df = top10_df.sort_values(by="향상도", ascending=True)  # 그래프 표시 순서

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

# 규칙 데이터 표 출력
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

# 함께 나온 적이 있는 메뉴 목록 수집
together_menus = set()
for (item1, item2), count in pair_counts.items():
    if count > 0:
        if item1 == target_menu:
            together_menus.add(item2)
        elif item2 == target_menu:
            together_menus.add(item1)

# 한번도 함께 나온 적이 없고 혼자서는 10일 이상 나온 메뉴 추출
never_together = []
for menu, count in item_counts.items():
    if menu != target_menu and menu not in together_menus and count >= 10:
        never_together.append({"메뉴": menu, "제공 일수": count})

never_df = (
    pd.DataFrame(never_together)
    .sort_values(by="제공 일수", ascending=False)
    .reset_index(drop=True)
)

st.markdown(f"**[{target_menu}]** 메뉴가 나온 날 수: **{target_days}일**")

if not never_df.empty:
    st.write(
        f"**[{target_menu}]**와 단 한 번도 함께 나오지 않았지만, **10일 이상 제공된 메뉴 목록**:"
    )
    st.dataframe(never_df, use_container_width=True)
else:
    st.write(
        f"**[{target_menu}]**와 함께 나온 적 없으면서 10일 이상 제공된 메뉴가 없습니다."
    )
