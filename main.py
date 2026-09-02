# =========================================================
# 영화 데이터 그래프 도감 2 - 분포와 관계
# =========================================================
# 구조 안내
#  0) 기본 설정
#  1) 데이터 불러오기 (load_data)
#  2) 공용 도구 (insight 문구 박스)
#  3) 그래프 구역들
#       section_01 : 장르별 영화 편수 (도넛)
#       section_02 : 장르 안의 영화 (트리맵, 크기=총 관객)
#       section_03 : 총 관객 분포 (히스토그램)
#       section_04 : 개봉일 스크린수 vs 총 관객 (산점도, 색=장르)
#       section_05 : 장르별 총 관객 (박스플롯, 10편 이상 장르만)
#       section_06 : ④의 버블 버전 (크기=첫 주 관객)
#       section_07 : 제작 국가 → 장르 (선버스트, 크기=편수)
#       ... 계속 추가
#  4) 메인 실행부
# =========================================================

import streamlit as st
import pandas as pd
import plotly.express as px

# ---------------------------------------------------------
# 0) 기본 설정
# ---------------------------------------------------------
st.set_page_config(
    page_title="영화 데이터 그래프 도감 2 - 분포와 관계",
    page_icon="🎬",
    layout="wide",
)

DATA_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/kobis_movies.csv"


# ---------------------------------------------------------
# 1) 데이터 불러오기
# ---------------------------------------------------------
@st.cache_data
def load_data(url: str = DATA_URL) -> pd.DataFrame:
    """
    1년간 박스오피스 10위권에 든 영화 216편의 요약표를 불러온다.
    - 장르가 '|'로 여러 개 적힌 영화는 첫 번째 장르만 쓴다.
    - 개봉일(8자리 숫자)은 진짜 날짜로 바꾼다.
    """
    df = pd.read_csv(url)

    # 장르: '드라마|코미디' -> '드라마' (첫 번째만)
    df["장르"] = df["genre"].astype(str).str.split("|").str[0].str.strip()

    # 국가도 여러 개일 수 있으니 첫 번째만 사용
    df["국가"] = df["nation"].astype(str).str.split("|").str[0].str.strip()

    # 개봉일: 20240101 -> 2024-01-01 (datetime)
    df["개봉일"] = pd.to_datetime(
        df["openDt"].astype(str), format="%Y%m%d", errors="coerce"
    )

    # 숫자 열 확실하게 숫자로
    num_cols = [
        "first_scrn", "first_show",
        "first_week_audi", "total_audi", "days_in_top10",
    ]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", "", regex=False),
                errors="coerce",
            )

    return df


# ---------------------------------------------------------
# 2) 공용 도구
# ---------------------------------------------------------
def insight_box(key: str, default_text: str = ""):
    """그래프 아래에 붙는 '이 그래프로 알 수 있는 것' 한 문장 자리."""
    st.markdown("**💡 이 그래프로 알 수 있는 것**")
    text = st.text_input(
        label="이 그래프로 알 수 있는 것",
        value=default_text,
        placeholder="예) 대부분의 영화는 관객이 적고, 아주 일부만 크게 흥행한다.",
        key=key,
        label_visibility="collapsed",
    )
    if text.strip():
        st.success(f"👉 {text}")
    else:
        st.caption("한 문장으로 적어 보세요. (무엇이 많은지 / 어떻게 퍼져 있는지 / 무엇과 관계있는지)")
    st.divider()


# ---------------------------------------------------------
# 3) 그래프 구역들
# ---------------------------------------------------------
def section_01_genre_donut(df: pd.DataFrame):
    """[구역 1] 장르별 영화 편수를 도넛 그래프로."""
    st.subheader("① 장르별 영화 편수 (도넛)")
    st.write("어떤 장르의 영화가 많이 개봉했는지 봅니다. 조각에 마우스를 올리면 **편수와 비율**이 보여요.")

    genre_count = df["장르"].value_counts().reset_index()
    genre_count.columns = ["장르", "편수"]

    fig = px.pie(
        genre_count,
        names="장르",
        values="편수",
        hole=0.45,                       # 가운데 구멍 -> 도넛
        title="장르별 영화 편수",
    )
    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>%{value}편 (%{percent})<extra></extra>",
        textinfo="label+percent",
    )
    st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    c1.metric("전체 영화 수", f"{len(df):,}편")
    c2.metric("가장 많은 장르", f"{genre_count.iloc[0]['장르']} ({genre_count.iloc[0]['편수']}편)")

    insight_box(key="insight_01")


def section_02_genre_treemap(df: pd.DataFrame):
    """[구역 2] 장르 안에 영화가 들어 있는 트리맵. 칸 크기 = 총 관객."""
    st.subheader("② 장르 안의 영화들 (트리맵)")
    st.write(
        "큰 칸(장르) 안에 작은 칸(영화)이 들어 있습니다. "
        "칸의 **크기는 총 관객수**예요. 칸을 클릭하면 그 장르만 확대해서 볼 수 있어요."
    )

    # 관객수가 없거나 0인 행은 트리맵에서 칸을 만들 수 없으니 제외
    tm = df.dropna(subset=["total_audi"])
    tm = tm[tm["total_audi"] > 0]

    fig = px.treemap(
        tm,
        path=[px.Constant("전체"), "장르", "movieNm"],   # 계층: 전체 > 장르 > 영화
        values="total_audi",
        color="장르",
        title="장르 → 영화 (칸 크기 = 총 관객수)",
    )
    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>총 관객: %{value:,}명<extra></extra>",
        textinfo="label",
    )
    fig.update_layout(margin=dict(t=60, l=10, r=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    st.caption("※ 칸이 너무 작아 이름이 안 보이면, 해당 장르 칸을 **클릭**해서 확대해 보세요.")

    insight_box(key="insight_02")


def section_03_total_audi_hist(df: pd.DataFrame):
    """[구역 3] 총 관객 히스토그램 + 자동 해설 문구."""
    st.subheader("③ 총 관객수 분포 (히스토그램)")
    st.write("영화들의 총 관객수가 **어느 구간에 몰려 있는지** 봅니다.")

    data = df.dropna(subset=["total_audi"])

    n_bins = st.slider("구간(막대) 개수", min_value=10, max_value=60, value=30, step=5,
                       key="sec03_bins")

    fig = px.histogram(
        data,
        x="total_audi",
        nbins=n_bins,
        title="총 관객수 히스토그램",
        labels={"total_audi": "총 관객수(명)", "count": "영화 편수"},
    )
    fig.update_traces(
        hovertemplate="관객수 구간: %{x}<br>영화 수: %{y}편<extra></extra>",
        marker_line_width=1,
        marker_line_color="white",
    )
    fig.update_layout(
        xaxis_title="총 관객수(명)",
        yaxis_title="영화 편수",
        xaxis_tickformat=",",
        bargap=0.05,
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── 자동 해설: 가장 많이 몰린 구간 찾기 ──────────────────
    # pd.cut으로 실제 구간을 나눠서 어느 구간에 가장 많은 영화가 있는지 계산
    binned = pd.cut(data["total_audi"], bins=n_bins)
    top_bin = binned.value_counts().sort_values(ascending=False).index[0]
    top_bin_count = binned.value_counts().max()
    low = int(top_bin.left) if top_bin.left > 0 else 0
    high = int(top_bin.right)

    # 가장 관객이 많은 영화
    best = data.loc[data["total_audi"].idxmax()]

    st.info(
        f"📊 **읽어 보기**\n\n"
        f"- 가장 많은 영화가 몰려 있는 구간은 "
        f"**약 {low:,}명 ~ {high:,}명**이고, 여기에 **{top_bin_count}편**이 들어 있습니다. "
        f"(전체 {len(data)}편의 {top_bin_count/len(data)*100:.1f}%)\n"
        f"- 관객이 가장 많은 영화는 **《{best['movieNm']}》**로 "
        f"총 **{int(best['total_audi']):,}명**입니다.\n"
        f"- 중앙값은 **{int(data['total_audi'].median()):,}명**, "
        f"평균은 **{int(data['total_audi'].mean()):,}명**이에요. "
        f"평균이 중앙값보다 훨씬 크다면, 일부 초대형 흥행작이 평균을 끌어올린 것입니다."
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("최다 관객 영화", best["movieNm"])
    c2.metric("그 영화의 총 관객", f"{int(best['total_audi']):,}명")
    c3.metric("전체 중앙값", f"{int(data['total_audi'].median()):,}명")

    insight_box(key="insight_03")


def section_04_scatter(df: pd.DataFrame):
    """[구역 4] 개봉일 스크린수 vs 총 관객 산점도. 색 = 장르."""
    st.subheader("④ 개봉일 스크린수 ↔ 총 관객수 (산점도)")
    st.write(
        "**많은 스크린에서 시작한 영화가 정말 관객도 많을까?** "
        "점에 마우스를 올리면 영화명이 보이고, 점 색은 장르입니다."
    )

    data = df.dropna(subset=["first_scrn", "total_audi"])

    fig = px.scatter(
        data,
        x="first_scrn",
        y="total_audi",
        color="장르",
        hover_name="movieNm",
        title="개봉일 스크린수와 총 관객수의 관계",
        labels={
            "first_scrn": "개봉일 스크린수(개)",
            "total_audi": "총 관객수(명)",
            "장르": "장르",
        },
        opacity=0.8,
    )
    fig.update_traces(
        marker=dict(size=10, line=dict(width=1, color="white")),
        hovertemplate="<b>%{hovertext}</b><br>"
                      "개봉일 스크린수: %{x:,}개<br>"
                      "총 관객수: %{y:,}명<extra></extra>",
    )
    fig.update_layout(
        xaxis_tickformat=",",
        yaxis_tickformat=",",
        legend_title_text="장르 (클릭=켜기/끄기)",
    )
    st.plotly_chart(fig, use_container_width=True)

    # 상관계수: 두 값이 함께 커지는 정도 (-1 ~ 1)
    corr = data["first_scrn"].corr(data["total_audi"])
    st.info(
        f"🔗 개봉일 스크린수와 총 관객수의 **상관계수는 {corr:.2f}** 입니다. "
        f"(1에 가까울수록 '스크린 많으면 관객도 많다'는 관계가 뚜렷함)"
    )

    insight_box(key="insight_04")


def section_05_genre_box(df: pd.DataFrame):
    """[구역 5] 영화 10편 이상인 장르만 골라 총 관객 박스플롯."""
    st.subheader("⑤ 장르별 총 관객수 (상자 그림)")
    st.write(
        "영화가 **10편 이상**인 장르만 골랐습니다. "
        "편수가 너무 적은 장르는 흩어진 모습을 믿기 어렵기 때문이에요. "
        "상자 밖으로 튀어나온 점(이상치)에 마우스를 올리면 영화명이 보입니다."
    )

    data = df.dropna(subset=["total_audi"])

    # 10편 이상인 장르만 남기기
    counts = data["장르"].value_counts()
    keep_genres = counts[counts >= 10].index.tolist()
    filtered = data[data["장르"].isin(keep_genres)]

    if filtered.empty:
        st.warning("영화가 10편 이상인 장르가 없습니다.")
        return

    st.caption(
        f"포함된 장르: {', '.join(f'{g}({counts[g]}편)' for g in keep_genres)}"
    )

    # 중앙값이 큰 장르부터 보이도록 순서 정하기
    order = (
        filtered.groupby("장르")["total_audi"].median()
        .sort_values(ascending=False).index.tolist()
    )

    fig = px.box(
        filtered,
        x="장르",
        y="total_audi",
        color="장르",
        points="outliers",              # 이상치 점만 표시
        hover_name="movieNm",           # 점에 올리면 영화명
        category_orders={"장르": order},
        title="장르별 총 관객수 분포 (10편 이상 장르만)",
        labels={"장르": "장르", "total_audi": "총 관객수(명)"},
    )
    fig.update_traces(
        hovertemplate="<b>%{hovertext}</b><br>총 관객: %{y:,}명<extra></extra>"
    )
    fig.update_layout(
        yaxis_tickformat=",",
        showlegend=False,
        xaxis_title="장르",
        yaxis_title="총 관객수(명)",
    )
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("📋 상자 그림 읽는 법"):
        st.markdown(
            "- **상자 가운데 선** = 중앙값 (딱 가운데 순위의 영화)\n"
            "- **상자의 아래/위** = 하위 25% / 상위 25% 지점\n"
            "- **수염(선)** = 대체로 평범한 범위\n"
            "- **바깥의 점** = 이상치. 유난히 잘 되거나 안 된 영화\n\n"
            "👉 상자가 **낮고 납작**하면 그 장르는 대부분 비슷비슷하고, "
            "**위로 길쭉**하면 편차가 큰 장르예요."
        )

    insight_box(key="insight_05")


def section_06_bubble(df: pd.DataFrame):
    """[구역 6] ④의 버블 버전. 점 크기 = 첫 주 관객."""
    st.subheader("⑥ 버블 그래프 — ④에 '첫 주 관객'을 점 크기로")
    st.write(
        "④번과 같은 산점도인데, **점의 크기**를 개봉 첫 주 관객수로 바꿨습니다. "
        "이제 한 그래프에서 **세 가지 정보**(스크린수 · 총 관객 · 첫 주 관객)를 동시에 볼 수 있어요."
    )

    data = df.dropna(subset=["first_scrn", "total_audi", "first_week_audi"])
    data = data[data["first_week_audi"] > 0]   # 크기는 0보다 커야 그려짐

    fig = px.scatter(
        data,
        x="first_scrn",
        y="total_audi",
        size="first_week_audi",          # 점 크기 = 첫 주 관객
        color="장르",
        hover_name="movieNm",
        size_max=45,
        title="개봉일 스크린수 · 총 관객수 · 첫 주 관객수(점 크기)",
        labels={
            "first_scrn": "개봉일 스크린수(개)",
            "total_audi": "총 관객수(명)",
            "first_week_audi": "첫 주 관객수(명)",
            "장르": "장르",
        },
        opacity=0.75,
        custom_data=["first_week_audi"],
    )
    fig.update_traces(
        hovertemplate="<b>%{hovertext}</b><br>"
                      "개봉일 스크린수: %{x:,}개<br>"
                      "총 관객수: %{y:,}명<br>"
                      "첫 주 관객수: %{customdata[0]:,}명<extra></extra>"
    )
    fig.update_layout(
        xaxis_tickformat=",",
        yaxis_tickformat=",",
        legend_title_text="장르 (클릭=켜기/끄기)",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.info(
        "🔍 **찾아보기:** 점이 **작은데 위쪽에 있는 영화**를 찾아보세요. "
        "첫 주에는 관객이 적었지만 결국 총 관객이 많아진, 이른바 **입소문 흥행작**일 가능성이 큽니다. "
        "반대로 **점이 큰데 아래쪽에 있는 영화**는 첫 주에 반짝하고 빨리 식은 경우겠죠."
    )

    insight_box(key="insight_06")


def section_07_sunburst(df: pd.DataFrame):
    """[구역 7] 제작 국가 → 장르 선버스트. 크기 = 영화 편수."""
    st.subheader("⑦ 제작 국가 → 장르 (선버스트)")
    st.write(
        "가운데에서 바깥으로 **국가 → 장르** 순서로 펼쳐집니다. "
        "칸의 크기는 **영화 편수**예요. 칸을 클릭하면 그 국가만 확대돼요."
    )

    # 편수를 세기 위해 개수 1인 열을 만들어 합계로 사용
    data = df.copy()
    data["편수"] = 1

    fig = px.sunburst(
        data,
        path=["국가", "장르"],
        values="편수",
        color="국가",
        title="제작 국가별 장르 구성 (칸 크기 = 영화 편수)",
    )
    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>"
                      "영화 편수: %{value}편<br>"
                      "전체 대비: %{percentRoot:.1%}<extra></extra>",
        insidetextorientation="radial",
    )
    fig.update_layout(margin=dict(t=60, l=10, r=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("📋 국가별 편수 표로 보기"):
        nation_table = (
            data["국가"].value_counts().reset_index()
        )
        nation_table.columns = ["제작 국가", "영화 편수"]
        nation_table["비율(%)"] = (
            nation_table["영화 편수"] / len(data) * 100
        ).round(1)
        nation_table.index = nation_table.index + 1
        nation_table.index.name = "순위"
        st.dataframe(nation_table, use_container_width=True)

    insight_box(key="insight_07")


# ---- 여기에 새 그래프 구역을 계속 추가하세요 ----------------
# def section_08_xxx(df: pd.DataFrame):
#     st.subheader("⑧ ...")
#     ...
#     insight_box(key="insight_08")
# ---------------------------------------------------------


# ---------------------------------------------------------
# 4) 메인 실행부
# ---------------------------------------------------------
def main():
    st.title("🎬 영화 데이터 그래프 도감 2 - 분포와 관계")
    st.caption("자료: 1년간 박스오피스 10위권에 든 영화 중 이 기간에 개봉한 216편 요약표")

    df = load_data()

    with st.expander("📋 원본 데이터 살펴보기"):
        st.write(
            f"영화 편수: **{len(df):,}편** / "
            f"장르 종류: **{df['장르'].nunique()}개** / "
            f"제작 국가: **{df['국가'].nunique()}개**"
        )
        st.dataframe(df.head(20), use_container_width=True)

    st.divider()

    section_01_genre_donut(df)
    section_02_genre_treemap(df)
    section_03_total_audi_hist(df)
    section_04_scatter(df)
    section_05_genre_box(df)
    section_06_bubble(df)
    section_07_sunburst(df)
    # section_08_xxx(df)     # 다음 그래프를 만들면 여기에 추가


if __name__ == "__main__":
    main()
