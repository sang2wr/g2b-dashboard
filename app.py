"""나라장터 입찰공고 대시보드"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

from api_client import fetch_notices, sample_data

# API 키 로드 (Streamlit Secrets → .env 순서로 시도)
def _load_env_key() -> str:
    try:
        return st.secrets.get("G2B_API_KEY", "") or ""
    except Exception:
        pass
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        for line in open(env_path, encoding="utf-8"):
            line = line.strip()
            if line.startswith("G2B_API_KEY="):
                return line.split("=", 1)[1].strip()
    return ""

DEFAULT_API_KEY = _load_env_key()

# ── 페이지 설정 ──────────────────────────────────────────────────
st.set_page_config(
    page_title="나라장터 공고 대시보드",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.metric-card {
  background:#f0f4ff; border-left:4px solid #1a56db;
  border-radius:8px; padding:14px 18px; margin-bottom:8px;
}
.metric-title { font-size:13px; color:#6b7280; margin:0; }
.metric-value { font-size:28px; font-weight:700; color:#1a56db; margin:4px 0 0; }
.deadline-soon  { background:#fff3cd !important; border-left-color:#f59e0b !important; }
.deadline-critical { background:#fee2e2 !important; border-left-color:#ef4444 !important; }
.amount-card { border-left-color:#065f46 !important; }
</style>
""", unsafe_allow_html=True)


# ── 헬퍼 함수 ────────────────────────────────────────────────────
def _dday_label(dday) -> str:
    if dday is None:
        return "-"
    try:
        d = int(dday)
        return f"D-{abs(d)}" if d <= 0 else f"D-{d}"
    except Exception:
        return "-"


def _amt_str(amt) -> str:
    try:
        v = int(amt or 0)
        return f"{v/100_000_000:.1f}억" if v >= 100_000_000 else f"{v//10_000:,}만"
    except Exception:
        return "-"


G2B_LINK_BASE = "https://www.g2b.go.kr/link/PNPE027_01/single/"


def show_table(data: pd.DataFrame, show_all: bool = True):
    df = data.copy()

    def _g2b_url(row):
        bid_no  = str(row.get("공고번호", "") or "")
        bid_ord = str(row.get("bidNtceOrd", "000") or "000")
        return f"{G2B_LINK_BASE}?bidPbancNo={bid_no}&bidPbancOrd={bid_ord}" if bid_no else ""

    df["공고링크"] = df.apply(_g2b_url, axis=1)
    df["추정가격_표시"] = df["추정가격"].apply(_amt_str)
    df["마감일"] = df["입찰마감"].astype(str).str[:10]
    df["공고일"] = df["공고일시"].astype(str).str[:10]

    base_cols  = ["공고일", "공고번호", "공고명", "공고기관", "추정가격_표시", "마감일", "마감D-Day", "공고링크"]
    extra_cols = ["수요기관", "담당자", "담당자연락처"] if show_all else []
    show_cols  = base_cols + extra_cols

    col_cfg = {
        "공고일":       st.column_config.TextColumn("공고일",    width=90),
        "공고번호":     st.column_config.TextColumn("공고번호",  width=140),
        "공고명":       st.column_config.TextColumn("공고명",    width="large"),
        "공고기관":     st.column_config.TextColumn("공고기관",  width=150),
        "추정가격_표시":st.column_config.TextColumn("추정가격",  width=90),
        "마감일":       st.column_config.TextColumn("마감일",    width=90),
        "마감D-Day":    st.column_config.NumberColumn("D-Day",   width=60, format="%d일"),
        "공고링크":     st.column_config.LinkColumn(
                            "바로가기",
                            display_text="→ 공고",
                            width=80,
                        ),
        "수요기관":     st.column_config.TextColumn("수요기관"),
        "담당자":       st.column_config.TextColumn("담당자",    width=80),
        "담당자연락처": st.column_config.TextColumn("연락처",    width=120),
    }

    st.dataframe(
        df[show_cols],
        column_config=col_cfg,
        hide_index=True,
        use_container_width=True,
        height=580,
    )
    st.caption(f"총 {len(data):,}건")

    csv = data.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        "⬇️ CSV로 저장",
        data=csv,
        file_name=f"나라장터_공고_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        key=f"csv_{'all' if show_all else 'urg'}",
    )


def show_stats(data: pd.DataFrame):
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("공고기관별 건수 (상위 10)")
        if "공고기관" in data.columns:
            st.bar_chart(data["공고기관"].value_counts().head(10))

    with col_b:
        st.subheader("추정가격 구간별 분포")
        if "추정가격" in data.columns:
            bins = pd.cut(
                data["추정가격"],
                bins=[0, 5e7, 1e8, 3e8, 5e8, float("inf")],
                labels=["5천만↓", "5천~1억", "1~3억", "3~5억", "5억↑"],
            )
            st.bar_chart(bins.value_counts().sort_index())

    if "공고일시" in data.columns:
        st.subheader("일자별 공고 건수")
        daily = (
            data.assign(날짜=data["공고일시"].dt.date)
            .groupby("날짜").size().rename("건수")
        )
        st.bar_chart(daily)


# ── 사이드바 ─────────────────────────────────────────────────────
with st.sidebar:
    st.title("🔍 검색 조건")

    api_key = st.text_input(
        "공공데이터포털 API 키",
        value=DEFAULT_API_KEY,
        type="password",
        placeholder="발급받은 API 키 입력",
        help="data.go.kr → 조달청_나라장터 입찰공고정보서비스 활용신청 후 발급",
    )

    st.divider()
    st.subheader("📌 키워드 (OR 검색)")
    kw_input = st.text_area(
        "키워드 (쉼표 구분)",
        value="스마트, 경로당, AI, 교육, 박람회",
        height=90,
        help="공고명에 하나라도 포함되면 포함",
    )
    keywords = [k.strip() for k in kw_input.split(",") if k.strip()]

    st.subheader("💰 최소 추정가격")
    min_amount_man = st.number_input("만원 이상", value=1000, min_value=0, step=100)
    min_amount = min_amount_man * 10_000

    st.subheader("📅 게시 기간")
    days = st.slider("최근 N일", min_value=1, max_value=30, value=7)

    st.subheader("🚫 제외 키워드")
    excl_input = st.text_input("제외 단어 (쉼표 구분)", value="시담")
    exclude_words = [e.strip() for e in excl_input.split(",") if e.strip()]

    st.divider()
    search_btn = st.button("🔄 공고 조회", use_container_width=True, type="primary")

    with st.expander("📖 API 키 발급 방법"):
        st.markdown("""
1. **[data.go.kr](https://www.data.go.kr)** 로그인
2. 검색창에 **`나라장터 입찰공고`** 검색
3. **나라장터 입찰공고정보 서비스** 클릭
4. **활용신청** → 즉시 발급 (자동승인)
5. **마이페이지 → 인증키 관리**에서
   `Decoding 키` 복사
6. 위 입력창에 붙여넣기 후 조회
        """)

# ── 메인 ─────────────────────────────────────────────────────────
st.title("📋 나라장터 입찰공고 대시보드")

# 초기 샘플 로드
if "df" not in st.session_state:
    st.session_state.df       = sample_data()
    st.session_state.is_sample = True

# 조회 버튼 처리
if search_btn:
    if not api_key:
        with st.spinner("샘플 데이터 필터링 중..."):
            df = sample_data()
            if exclude_words:
                df = df[~df["공고명"].str.contains("|".join(exclude_words), na=False)]
            if keywords:
                df = df[df["공고명"].str.contains("|".join(keywords), na=False)]
            df = df[df["추정가격"] >= min_amount]
        st.session_state.df        = df
        st.session_state.is_sample = True
        st.warning("⚠️ API 키 없음 → 샘플 데이터로 표시합니다.")
    else:
        with st.spinner("나라장터에서 공고를 가져오는 중..."):
            df = fetch_notices(
                api_key=api_key,
                keywords=keywords,
                min_amount=min_amount,
                days=days,
                exclude_words=exclude_words,
            )
        st.session_state.df        = df
        st.session_state.is_sample = False
    st.session_state.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.rerun()

df: pd.DataFrame = st.session_state.df
is_sample: bool  = st.session_state.get("is_sample", True)

# 상태 표시
status_col, time_col = st.columns([5, 1])
with time_col:
    if "last_updated" in st.session_state:
        st.caption(f"조회: {st.session_state.last_updated}")

if is_sample:
    st.info("📌 **샘플 데이터** 표시 중 — 왼쪽에 API 키 입력 후 '공고 조회'를 누르면 실시간 데이터를 불러옵니다.")

st.caption("💡 **공고 링크**: 나라장터 **로그아웃** 상태에서 클릭하면 공고 페이지로 바로 이동합니다. 로그인 상태라면 공고번호를 복사해 나라장터에서 직접 검색하세요.")

# ── 요약 카드 ────────────────────────────────────────────────────
if not df.empty:
    today = datetime.now()

    df = df.copy()
    df["마감D-Day"] = df["입찰마감"].apply(
        lambda x: int((pd.to_datetime(x, errors="coerce") - today).days)
        if pd.notnull(pd.to_datetime(x, errors="coerce")) else None
    )

    total        = len(df)
    d3           = int((df["마감D-Day"].notna() & (df["마감D-Day"] <= 3) & (df["마감D-Day"] >= 0)).sum())
    d7           = int((df["마감D-Day"].notna() & (df["마감D-Day"] <= 7) & (df["마감D-Day"] >= 0)).sum())
    total_amount = df["추정가격"].sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="metric-card"><p class="metric-title">전체 공고 수</p><p class="metric-value">{total}건</p></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="metric-card deadline-critical"><p class="metric-title">마감 3일 이내 🚨</p><p class="metric-value">{d3}건</p></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="metric-card deadline-soon"><p class="metric-title">마감 7일 이내 ⚠️</p><p class="metric-value">{d7}건</p></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="metric-card amount-card"><p class="metric-title">총 추정가격</p><p class="metric-value">{total_amount/100_000_000:.1f}억</p></div>', unsafe_allow_html=True)

    st.divider()

    tab1, tab2, tab3 = st.tabs(["📋 전체 목록", "🚨 마감 임박 (7일)", "📊 통계"])

    with tab1:
        show_table(df, show_all=True)

    with tab2:
        urgent = df[df["마감D-Day"].notna() & (df["마감D-Day"] <= 7) & (df["마감D-Day"] >= 0)].sort_values("마감D-Day")
        if urgent.empty:
            st.success("✅ 7일 이내 마감 공고가 없습니다.")
        else:
            st.warning(f"마감 7일 이내 공고 **{len(urgent)}건** — 빨리 확인하세요!")
            show_table(urgent, show_all=False)

    with tab3:
        show_stats(df)

else:
    st.markdown("### 조건에 맞는 공고가 없습니다.")
    st.caption("왼쪽 사이드바에서 조건을 변경하고 **공고 조회** 버튼을 눌러주세요.")
