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


# 데이터 파싱 수행
(
    total_days,
    total_menu_types,
    total_pairs,
    rules_df,
