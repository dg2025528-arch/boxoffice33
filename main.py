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
#       section_08 : 흥행 등급별 특징 비교 (무엇이 달랐나?)
#       section_09 : 뒷심 지수 (선형 축으로 격차를 드라마틱하게)  ← 수정
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
        hole=0.45,
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

    tm = df.dropna(subset=["total_audi"])
    tm = tm[tm["total_audi"] > 0]

    fig = px.treemap(
        tm,
        path=[px.Constant("전체"), "장르", "movieNm"],
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

    binned = pd.cut(data["total_audi"], bins=n_bins)
    top_bin = binned.value_counts().sort_values(ascending=False).index[0]
    top_bin_count = binned.value_counts().max()
    low = int(top_bin.left) if top_bin.left > 0 else 0
    high = int(top_bin.right)

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

    counts = data["장르"].value_counts()
    keep_genres = counts[counts >= 10].index.tolist()
    filtered = data[data["장르"].isin(keep_genres)]

    if filtered.empty:
        st.warning("영화가 10편 이상인 장르가 없습니다.")
        return

    st.caption(
        f"포함된 장르: {', '.join(f'{g}({counts[g]}편)' for g in keep_genres)}"
    )

    order = (
        filtered.groupby("장르")["total_audi"].median()
        .sort_values(ascending=False).index.tolist()
    )

    fig = px.box(
        filtered,
        x="장르",
        y="total_audi",
        color="장르",
        points="outliers",
        hover_name="movieNm",
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
    data = data[data["first_week_audi"] > 0]

    fig = px.scatter(
        data,
        x="first_scrn",
        y="total_audi",
        size="first_week_audi",
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
        nation_table = data["국가"].value_counts().reset_index()
        nation_table.columns = ["제작 국가", "영화 편수"]
        nation_table["비율(%)"] = (
            nation_table["영화 편수"] / len(data) * 100
        ).round(1)
        nation_table.index = nation_table.index + 1
        nation_table.index.name = "순위"
        st.dataframe(nation_table, use_container_width=True)

    insight_box(key="insight_07")


def section_08_success_compare(df: pd.DataFrame):
    """
    [구역 8] 흥행 등급별로 특징이 얼마나 다른지 비교하기.

    ★ 먼저 알아둘 것 (아주 중요!)
      이 데이터는 '박스오피스 10위권에 든 영화'만 모은 것이다.
      즉 '실패한 영화'는 애초에 데이터에 없다 -> 생존자 편향(survivorship bias).
      그래서 "인기 영화 vs 비인기 영화"를 비교할 수는 없다.
      대신 "성공한 영화들 안에서도 초대박과 평범함을 가른 것은 무엇인가"를 물을 수 있다.

    ★ 원인과 결과를 구분하자
      - 개봉 '전'에 정해지는 값  : first_scrn, first_show   -> 원인 후보
      - 개봉 '초반' 반응        : first_week_audi          -> 중간
      - 흥행의 '결과'           : days_in_top10, total_audi -> 결과
    """
    st.subheader("⑧ 흥행 등급별로 무엇이 달랐나? (원인 찾기)")

    st.warning(
        "⚠️ **먼저 알아둘 것 — 생존자 편향**\n\n"
        "이 데이터는 **10위권에 든 영화 216편만** 모은 것입니다. "
        "10위권에 한 번도 못 든 영화는 아예 들어 있지 않아요.\n\n"
        "그래서 *\"인기 영화 vs 비인기 영화\"* 는 비교할 수 없습니다. "
        "대신 이렇게 물어봅시다 👇\n\n"
        "> **\"성공한 영화들 중에서도, 유독 크게 흥행한 영화는 무엇이 달랐을까?\"**"
    )

    data = df.dropna(subset=["total_audi"]).copy()

    q1 = data["total_audi"].quantile(0.25)
    q3 = data["total_audi"].quantile(0.75)

    def grade(x):
        if x >= q3:
            return "상위 25% (대흥행)"
        elif x >= q1:
            return "중간 50%"
        else:
            return "하위 25%"

    data["흥행등급"] = data["total_audi"].apply(grade)
    grade_order = ["하위 25%", "중간 50%", "상위 25% (대흥행)"]

    st.caption(
        f"기준선 — 하위 25%: {int(q1):,}명 미만 / "
        f"상위 25%: {int(q3):,}명 이상"
    )

    metric_options = {
        "개봉일 스크린수 (first_scrn)": "first_scrn",
        "개봉일 상영횟수 (first_show)": "first_show",
        "첫 주 관객수 (first_week_audi)": "first_week_audi",
        "10위권 유지 일수 (days_in_top10)": "days_in_top10",
    }
    picked_label = st.selectbox(
        "비교해 볼 항목을 고르세요",
        options=list(metric_options.keys()),
        key="sec08_metric",
    )
    picked_col = metric_options[picked_label]

    plot_data = data.dropna(subset=[picked_col])

    fig = px.box(
        plot_data,
        x="흥행등급",
        y=picked_col,
        color="흥행등급",
        points="all",
        hover_name="movieNm",
        category_orders={"흥행등급": grade_order},
        title=f"흥행 등급별 {picked_label} 분포",
        labels={"흥행등급": "흥행 등급", picked_col: picked_label},
    )
    fig.update_traces(
        hovertemplate="<b>%{hovertext}</b><br>"
                      f"{picked_label}: " + "%{y:,}<extra></extra>",
        marker=dict(opacity=0.5, size=6),
    )
    fig.update_layout(
        showlegend=False,
        yaxis_tickformat=",",
        xaxis_title="흥행 등급 (총 관객 기준)",
    )
    st.plotly_chart(fig, use_container_width=True)

    summary = (
        plot_data.groupby("흥행등급")[picked_col]
        .agg(중앙값="median", 평균="mean", 편수="count")
        .reindex(grade_order)
        .reset_index()
    )

    st.markdown("**📊 그룹별 요약 (중앙값으로 비교하는 게 안전해요)**")
    show = summary.copy()
    show["중앙값"] = show["중앙값"].map(lambda v: f"{v:,.0f}")
    show["평균"] = show["평균"].map(lambda v: f"{v:,.0f}")
    st.dataframe(show, use_container_width=True, hide_index=True)

    top_med = summary.loc[summary["흥행등급"] == "상위 25% (대흥행)", "중앙값"].values[0]
    bot_med = summary.loc[summary["흥행등급"] == "하위 25%", "중앙값"].values[0]
    if bot_med and bot_med > 0:
        ratio = top_med / bot_med
        st.info(
            f"📌 **상위 25% 그룹의 {picked_label} 중앙값은 "
            f"하위 25% 그룹의 약 {ratio:.1f}배**입니다."
        )

    st.markdown("**🔎 네 가지 항목을 한 번에 비교하기**")
    st.caption(
        "항목마다 단위가 달라서(개 / 회 / 명 / 일) 직접 비교가 어렵습니다. "
        "그래서 **'하위 25% 그룹의 중앙값 = 1'로 놓고 몇 배인지**로 바꿔서 그렸어요."
    )

    rows = []
    for label, col in metric_options.items():
        med = data.groupby("흥행등급")[col].median().reindex(grade_order)
        base = med["하위 25%"]
        if pd.isna(base) or base == 0:
            continue
        for g in grade_order:
            rows.append({
                "항목": label.split(" (")[0],
                "흥행등급": g,
                "배수": med[g] / base,
                "실제값": med[g],
            })
    ratio_df = pd.DataFrame(rows)

    fig2 = px.bar(
        ratio_df,
        x="항목",
        y="배수",
        color="흥행등급",
        barmode="group",
        category_orders={"흥행등급": grade_order},
        title="하위 25% 그룹을 1로 놓았을 때, 각 그룹의 중앙값 배수",
        labels={"배수": "하위 25% 대비 배수", "항목": "비교 항목"},
        custom_data=["실제값"],
    )
    fig2.update_traces(
        hovertemplate="<b>%{x}</b><br>"
                      "%{fullData.name}<br>"
                      "배수: %{y:.2f}배<br>"
                      "실제 중앙값: %{customdata[0]:,.0f}<extra></extra>"
    )
    fig2.update_layout(yaxis_title="하위 25% 대비 배수", legend_title_text="흥행 등급")
    st.plotly_chart(fig2, use_container_width=True)

    st.success(
        "🧭 **해석할 때 주의할 점**\n\n"
        "- **개봉일 스크린수·상영횟수**가 크게 차이 난다면 → 개봉 *전*의 조건이 흥행과 관련 있다는 뜻.\n"
        "- **10위권 유지 일수**가 크게 차이 나는 건 당연합니다. 흥행했으니 오래 남은 것이니까요. "
        "이건 **원인이 아니라 결과**예요.\n"
        "- 차이가 보인다고 해서 **원인이라고 단정할 수는 없습니다.** "
        "스크린을 많이 줘서 흥행한 걸까요, 흥행할 것 같아서 스크린을 많이 준 걸까요? 🤔"
    )

    insight_box(key="insight_08")


def section_09_word_of_mouth(df: pd.DataFrame):
    """
    [구역 9] 뒷심 지수 = 총 관객 ÷ 첫 주 관객.

    ★ 이번 수정: 로그 축 -> 선형 축(일반 축)
      - 로그 축: 작은 영화도 넓게 펼쳐져 관계 파악에 좋지만, 초대박의 위엄이 죽는다.
      - 선형 축: 초대박 영화가 저 멀리 혼자 튀어나가서 '격차'가 극적으로 보인다.
      - 대신 작은 영화들이 왼쪽 아래에 뭉치므로, '확대 보기'와 '로그 전환'을 옵션으로 둔다.
    """
    st.subheader("⑨ 인기의 두 종류 — '첫 주 폭발형' vs '입소문 장기형'")
    st.write(
        "**뒷심 지수 = 총 관객 ÷ 첫 주 관객**을 만들었습니다.\n\n"
        "- 지수가 **크면** → 첫 주엔 조용했지만 **입소문으로 길게 흥행**한 영화\n"
        "- 지수가 **작으면** → 첫 주에 관객이 몰렸다가 **빠르게 식은** 영화"
    )

    data = df.dropna(subset=["total_audi", "first_week_audi", "days_in_top10"]).copy()
    data = data[data["first_week_audi"] > 0]

    # 뒷심 지수 만들기
    data["뒷심지수"] = data["total_audi"] / data["first_week_audi"]

    median_wom = data["뒷심지수"].median()
    data["흥행유형"] = data["뒷심지수"].apply(
        lambda v: "입소문 장기형" if v >= median_wom else "첫 주 폭발형"
    )

    # ── 보기 옵션 ────────────────────────────────────────
    c1, c2 = st.columns([1, 1])
    with c1:
        use_log = st.checkbox(
            "로그 축으로 보기 (뭉친 부분 펼치기)",
            value=False,
            key="sec09_log",
            help="끄면(기본) 선형 축 — 초대박 영화의 격차가 극적으로 보입니다. "
                 "켜면 로그 축 — 작은 영화들도 넓게 펼쳐집니다.",
        )
    with c2:
        zoom_in = st.checkbox(
            "확대 보기 (상위 5% 초대형 흥행작 잠시 빼기)",
            value=False,
            key="sec09_zoom",
            help="선형 축에서 왼쪽 아래에 뭉쳐 보이는 영화들을 자세히 보고 싶을 때 켜세요.",
        )

    plot_data = data.copy()
    if zoom_in:
        cut = plot_data["total_audi"].quantile(0.95)
        hidden = plot_data[plot_data["total_audi"] >= cut]
        plot_data = plot_data[plot_data["total_audi"] < cut]
        st.caption(
            f"🔍 확대 보기 중 — 총 관객 {int(cut):,}명 이상인 "
            f"**{len(hidden)}편**을 잠시 숨겼습니다: "
            + ", ".join(f"《{n}》" for n in hidden["movieNm"].head(6))
        )

    # ── 산점도: x=첫 주 관객, y=총 관객 / 색=유형 / 크기=유지일수 ──
    fig = px.scatter(
        plot_data,
        x="first_week_audi",
        y="total_audi",
        color="흥행유형",
        size="days_in_top10",
        hover_name="movieNm",
        size_max=34,
        log_x=use_log,
        log_y=use_log,
        color_discrete_map={
            "입소문 장기형": "#2E8B57",   # 초록
            "첫 주 폭발형": "#DC143C",    # 빨강
        },
        title="첫 주 관객 ↔ 총 관객 (점 크기 = 10위권 유지 일수)",
        labels={
            "first_week_audi": "첫 주 관객수(명)",
            "total_audi": "총 관객수(명)",
            "흥행유형": "흥행 유형",
        },
        custom_data=["뒷심지수", "days_in_top10", "장르"],
        opacity=0.8,
    )
    fig.update_traces(
        hovertemplate="<b>%{hovertext}</b> (%{customdata[2]})<br>"
                      "첫 주 관객: %{x:,}명<br>"
                      "총 관객: %{y:,}명<br>"
                      "뒷심 지수: %{customdata[0]:.2f}배<br>"
                      "10위권 유지: %{customdata[1]:.0f}일<extra></extra>",
        marker=dict(line=dict(width=1, color="white")),
    )

    # ── 기준선(대각선) 긋기: 총 관객이 첫 주의 몇 배인지 눈으로 보기 ──
    # 선형 축일 때만 의미가 잘 살아나므로, 로그일 때도 함께 그려 준다.
    if not plot_data.empty:
        x_max = plot_data["first_week_audi"].max() * 1.05
        y_max = plot_data["total_audi"].max() * 1.05

        for mult, dash, color in [(1, "dot", "gray"),
                                  (2, "dash", "#888"),
                                  (5, "dashdot", "#aaa")]:
            # y = mult * x 직선이 그래프 안에 들어오는 구간까지만 그린다
            x_end = min(x_max, y_max / mult)
            fig.add_scatter(
                x=[0, x_end],
                y=[0, mult * x_end],
                mode="lines",
                line=dict(dash=dash, color=color, width=1.5),
                name=f"총 관객 = 첫 주 × {mult}",
                hoverinfo="skip",
                showlegend=True,
            )

    fig.update_layout(
        xaxis_tickformat=",",
        yaxis_tickformat=",",
        legend_title_text="구분 (클릭=켜기/끄기)",
        height=560,
    )
    st.plotly_chart(fig, use_container_width=True)

    if use_log:
        st.caption(
            "📐 지금은 **로그 축**입니다. 눈금이 1만→10만→100만처럼 **곱하기**로 커져서, "
            "작은 영화들도 넓게 펼쳐져 보입니다."
        )
    else:
        st.caption(
            "📐 지금은 **선형 축(일반 축)**입니다. 눈금이 100만→200만→300만처럼 "
            "**더하기**로 커져서, 초대형 흥행작이 얼마나 압도적인지 그대로 드러납니다. "
            "대신 작은 영화들은 왼쪽 아래에 뭉쳐 보이죠. "
            "→ 그럴 땐 위의 **확대 보기**를 켜 보세요."
        )

    st.caption(
        f"※ 점선은 기준선입니다. 점이 **위쪽 선에 가까울수록** 첫 주 대비 여러 배 성장한 영화예요. "
        f"뒷심 지수 중앙값 **{median_wom:.2f}배**를 기준으로 두 유형(색)을 나눴습니다."
    )

    # ── 뒷심 지수 TOP / BOTTOM 10 ────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**🌱 뒷심 지수 TOP 10 (입소문 흥행)**")
        top10 = data.nlargest(10, "뒷심지수").sort_values("뒷심지수")
        f1 = px.bar(
            top10,
            x="뒷심지수", y="movieNm", orientation="h",
            labels={"뒷심지수": "뒷심 지수(배)", "movieNm": ""},
            custom_data=["total_audi", "first_week_audi", "days_in_top10"],
        )
        f1.update_traces(
            marker_color="#2E8B57",
            hovertemplate="<b>%{y}</b><br>"
                          "뒷심 지수: %{x:.2f}배<br>"
                          "총 관객: %{customdata[0]:,}명<br>"
                          "첫 주 관객: %{customdata[1]:,}명<br>"
                          "10위권 유지: %{customdata[2]:.0f}일<extra></extra>",
        )
        f1.update_layout(height=400, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(f1, use_container_width=True)

    with col2:
        st.markdown("**💥 뒷심 지수 BOTTOM 10 (첫 주 반짝)**")
        bot10 = data.nsmallest(10, "뒷심지수").sort_values("뒷심지수", ascending=False)
        f2 = px.bar(
            bot10,
            x="뒷심지수", y="movieNm", orientation="h",
            labels={"뒷심지수": "뒷심 지수(배)", "movieNm": ""},
            custom_data=["total_audi", "first_week_audi", "days_in_top10"],
        )
        f2.update_traces(
            marker_color="#DC143C",
            hovertemplate="<b>%{y}</b><br>"
                          "뒷심 지수: %{x:.2f}배<br>"
                          "총 관객: %{customdata[0]:,}명<br>"
                          "첫 주 관객: %{customdata[1]:,}명<br>"
                          "10위권 유지: %{customdata[2]:.0f}일<extra></extra>",
        )
        f2.update_layout(height=400, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(f2, use_container_width=True)

    st.info(
        "🤔 **생각해 보기**\n\n"
        "위 두 그룹의 **장르**를 비교해 보세요. "
        "입소문으로 오래 가는 장르와, 첫 주에 몰리는 장르가 서로 다른가요?\n\n"
        "혹시 뒷심 지수가 큰 영화는 **개봉일 스크린수가 적었던** 영화는 아닐까요? "
        "④번 산점도로 돌아가 확인해 보세요."
    )

    insight_box(key="insight_09")


# ---- 여기에 새 그래프 구역을 계속 추가하세요 ----------------
# def section_10_xxx(df: pd.DataFrame):
#     st.subheader("⑩ ...")
#     ...
#     insight_box(key="insight_10")
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
    section_08_success_compare(df)
    section_09_word_of_mouth(df)
    # section_10_xxx(df)     # 다음 그래프를 만들면 여기에 추가


if __name__ == "__main__":
    main()
