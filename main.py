import re
from collections import Counter, defaultdict
from itertools import combinations
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="급식 규칙 찾기", layout="wide")


# 데이터 로드 및 전처리
@st.cache_data
def load_and_process_data():
    url = "https://raw.githubusercontent.com/it-teacher-go/data-share-/main/songtan_meals_184.csv"
    df = pd.read_csv(url, encoding="utf-8")

    transactions = []
    all_menus = set()

    for raw_menu in df["메뉴"].dropna():
        # 세로줄(|)로 메뉴 분리
        items = raw_menu.split("|")
        cleaned_items = []
        for item in items:
            # 괄호 및 괄호 안 내용 제거 및 공백 정리
            cleaned = re.sub(r"\(.*?\)", "", item).strip()
            if cleaned:
                cleaned_items.append(cleaned)

        # 하루 식단 내 중복 메뉴 제거
        unique_items = list(set(cleaned_items))
        if unique_items:
            transactions.append(unique_items)
            all_menus.update(unique_items)

    return transactions, sorted(list(all_menus))


# 연관 규칙 및 메뉴별 출현 횟수 계산
@st.cache_data
def calculate_rules(transactions):
    total_tx = len(transactions)

    item_counts = Counter()
    pair_counts = defaultdict(int)

    for tx in transactions:
        for item in tx:
            item_counts[item] += 1
        for item1, item2 in combinations(tx, 2):
            pair_counts[tuple(sorted([item1, item2]))] += 1

    rules = []
    for (item1, item2), count in pair_counts.items():
        supp = count / total_tx

        # item1 -> item2
        conf1 = count / item_counts[item1]
        lift1 = conf1 / (item_counts[item2] / total_tx)
        rules.append(
            {
                "조건": item1,
                "결과": item2,
                "동시": count,
                "지지도": round(supp, 4),
                "신뢰도": round(conf1, 4),
                "향상도": round(lift1, 4),
            }
        )

        # item2 -> item1
        conf2 = count / item_counts[item2]
        lift2 = conf2 / (item_counts[item1] / total_tx)
        rules.append(
            {
                "조건": item2,
                "결과": item1,
                "동시": count,
                "지지도": round(supp, 4),
                "신뢰도": round(conf2, 4),
                "향상도": round(lift2, 4),
            }
        )

    rules_df = pd.DataFrame(rules)
    unique_pairs_count = len(pair_counts)

    return rules_df, total_tx, item_counts, unique_pairs_count


# 데이터 처리
transactions, all_menus = load_and_process_data()
rules_df, total_days, item_counts, unique_pairs_count = calculate_rules(
    transactions
)

st.title("🍚 송탄고 급식 메뉴 연관 규칙 분석")

# 1. 상단 주요 지표 출력 (한 줄 표시)
st.markdown(
    f"**급식 일수:** {total_days}일 | **메뉴 종류 수:** {len(item_counts)}개 | **함께 나온 적이 있는 메뉴 쌍의 수:** {unique_pairs_count}개"
)
st.divider()

# 2. 사이드바 / 컨트롤 옵션 (필터링 및 정렬 설정)
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    selected_menu = st.selectbox(
        "특정 메뉴 좁혀보기", ["전체"] + all_menus, index=0
    )

with col2:
    sort_by = st.selectbox(
        "정렬 기준 선택",
        ["향상도", "신뢰도", "동시"],
        index=0,
    )

with col3:
    min_cooccur = st.slider(
        "최소 동시 일수 선택", min_value=1, max_value=10, value=1, step=1
    )

# 조건별 데이터 필터링
filtered_df = rules_df.copy()

# 최소 동시 일수 필터 적용
filtered_df = filtered_df[filtered_df["동시"] >= min_cooccur]

# 메뉴 좁혀보기 필터 적용
if selected_menu != "전체":
    filtered_df = filtered_df[
        (filtered_df["조건"] == selected_menu)
        | (filtered_df["결과"] == selected_menu)
    ]

# 정렬 적용
filtered_df = filtered_df.sort_values(by=sort_by, ascending=False).reset_index(
    drop=True
)

# 표에 남은 규칙 개수 안내 문구 출력
st.info(f"💡 현재 조건(최소 동시 일수 {min_cooccur}일 이상)에 해당하는 연관 규칙은 총 **{len(filtered_df)}**개입니다.")

# 3. 향상도 상위 10개 Plotly 가로 막대그래프
st.subheader("📊 향상도 상위 10개 메뉴 쌍")

top_10_lift = filtered_df.sort_values(by="향상도", ascending=False).head(10)

if not top_10_lift.empty:
    top_10_lift = top_10_lift.copy()
    top_10_lift["규칙"] = top_10_lift["조건"] + " ➡️ " + top_10_lift["결과"]

    fig = px.bar(
        top_10_lift.sort_values(by="향상도", ascending=True),
        x="향상도",
        y="규칙",
        orientation="h",
        text="향상도",
        title=f"{'전체' if selected_menu == '전체' else selected_menu} 기준 향상도 Top 10",
        labels={"향상도": "향상도 (Lift)", "규칙": "메뉴 규칙"},
    )
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("조건을 만족하는 연관 규칙 데이터가 없습니다.")

# 4. 연관 규칙 표 출력
st.subheader("📋 메뉴 연관 규칙 목록")
st.dataframe(filtered_df, use_container_width=True)

st.divider()

# 5. 함께 나온 적 없는 짝 섹션
st.subheader("🔍 함께 나온 적 없는 짝 찾기")

target_menu = st.selectbox(
    "조회할 메뉴를 선택하세요",
    all_menus,
    key="unpaired_menu_select",
)

if target_menu:
    target_days = item_counts[target_menu]
    st.write(f"📌 **선택한 메뉴:** `{target_menu}` (총 **{target_days}일** 출현)")

    # 선택한 메뉴와 함께 나온 적이 있는 모든 메뉴 수집
    co_occurred_menus = set()
    for tx in transactions:
        if target_menu in tx:
            co_occurred_menus.update(tx)

    # 조건에 맞는 메뉴 탐색:
    # 1. 대상 메뉴와 한 번도 같이 나온 적 없음 (co_occurred_menus에 미포함)
    # 2. 혼자서(단독으로) 10일 이상 출현함 (item_counts >= 10)
    unpaired_list = []
    for menu, count in item_counts.items():
        if menu not in co_occurred_menus and count >= 10:
            unpaired_list.append({"메뉴": menu, "출현 일수": count})

    unpaired_df = pd.DataFrame(unpaired_list)

    if not unpaired_df.empty:
        # 나온 날(출현 일수)이 많은 순으로 정렬
        unpaired_df = unpaired_df.sort_values(
            by="출현 일수", ascending=False
        ).reset_index(drop=True)
        st.dataframe(unpaired_df, use_container_width=True)
    else:
        st.write("해당 메뉴와 한 번도 함께 나오지 않았으면서 10일 이상 나온 메뉴가 없습니다.")
