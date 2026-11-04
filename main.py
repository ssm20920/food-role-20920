import re
from collections import Counter, defaultdict
from itertools import combinations
import pandas as pd
import plotly.express as px
import requests
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


# 연관 규칙 계산
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

    return rules_df, total_tx, len(item_counts), unique_pairs_count


# 앱 실행
st.title("🍚 송탄고 급식 메뉴 연관 규칙 분석")

transactions, all_menus = load_and_process_data()
rules_df, total_days, total_menu_types, unique_pairs_count = calculate_rules(
    transactions
)

# 주요 지표 출력 (한 줄 표시)
st.markdown(
    f"**급식 일수:** {total_days}일 | **메뉴 종류 수:** {total_menu_types}개 | **함께 나온 적이 있는 메뉴 쌍의 수:** {unique_pairs_count}개"
)
st.divider()

# 사이드바 / 컨트롤 옵션
col1, col2 = st.columns([1, 1])

with col1:
    selected_menu = st.selectbox(
        "특정 메뉴 선택 (전체 보기: '전체')", ["전체"] + all_menus
    )

with col2:
    sort_by = st.selectbox(
        "정렬 기준 선택",
        ["향상도", "신뢰도", "동시"],
        index=0,
    )

# 메뉴 필터링
if selected_menu != "전체":
    filtered_df = rules_df[
        (rules_df["조건"] == selected_menu) | (rules_df["결과"] == selected_menu)
    ].copy()
else:
    filtered_df = rules_df.copy()

# 정렬 적용
filtered_df = filtered_
