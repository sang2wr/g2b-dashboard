"""나라장터 입찰공고 대시보드"""
import streamlit as st
import pandas as pd
from datetime import datetime
import os

from api_client import fetch_notices

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

st.set_page_config(
    page_title="나라장터 공고 대시보드",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
/* ── 메트릭 카드 ── */
.metric-card {
  background:#f0f4ff; border-left:4px solid #1a56db;
  border-radius:8px; padding:14px 18px; margin-bottom:0;
}
.metric-title { font-size:13px; color:#6b7280; margin:0; }
.metric-value { font-size:28px; font-weight:700; color:#1a56db; margin:4px 0 0; }
.deadline-soon     { background:#fff3cd !important; border-left-color:#f59e0b !important; }
.deadline-critical { background:#fee2e2 !important; border-left-color:#ef4444 !important; }
.amount-card       { border-left-color:#065f46 !important; }

/* ── 반응형 메트릭 그리드 ── */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 10px;
  margin-bottom: 16px;
}

/* ── 조회 폼 박스 ── */
.search-box {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 20px 24px;
  margin-bottom: 24px;
}

/* ── 모바일 공통 ── */
@media (max-width: 768px) {
  .metric-title { font-size: 12px; }
  .metric-value { font-size: 22px; }

  .stTabs [data-baseweb="tab"] {
    font-size: 13px !important;
    padding: 8px 8px !important;
  }

  .stButton > button {
    min-height: 48px !important;
    font-size: 16px !important;
  }

  .stTextInput > div > div > input,
  .stTextArea textarea,
  .stSelectbox > div > div {
    font-size: 16px !important;
  }

  .stDataFrame { overflow-x: auto; }
}
</style>
""", unsafe_allow_html=True)


# ── 헬퍼 함수 ────────────────────────────────────────────────────
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

    q = st.text_input(
        "결과 내 검색",
        placeholder="공고명 · 기관명으로 필터...",
        key=f"q_{'all' if show_all else 'urg'}",
        label_visibility="collapsed",
    )
    fc1, fc2 = st.columns([3, 1])
    with fc1:
        sort_opt = st.selectbox(
            "정렬",
            ["마감일 빠른순", "마감일 느린순", "추정가격 높은순", "추정가격 낮은순", "공고일 최신순"],
            key=f"sort_{'all' if show_all else 'urg'}",
            label_visibility="collapsed",
        )
    with fc2:
        st.caption(f"**{len(df):,}건**")

    if q:
        mask = (
            df["공고명"].str.contains(q, case=False, na=False) |
            df["공고기관"].str.contains(q, case=False, na=False)
        )
        df = df[mask]
        st.caption(f"'{q}' 필터 결과: {len(df):,}건")

    sort_map = {
        "마감일 빠른순":   ("마감D-Day", True),
        "마감일 느린순":   ("마감D-Day", False),
        "추정가격 높은순": ("추정가격",  False),
        "추정가격 낮은순": ("추정가격",  True),
        "공고일 최신순":   ("공고일시",  False),
    }
    sort_col, sort_asc = sort_map[sort_opt]
    if sort_col in df.columns:
        df = df.sort_values(sort_col, ascending=sort_asc, na_position="last")

    base_cols  = ["공고일", "공고번호", "공고명", "공고기관", "추정가격_표시", "마감일", "마감D-Day", "공고링크"]
    extra_cols = ["수요기관", "담당자", "담당자연락처"] if show_all else []
    show_cols  = base_cols + extra_cols

    col_cfg = {
        "공고일":        st.column_config.TextColumn("공고일",   width=90),
        "공고번호":      st.column_config.TextColumn("공고번호", width=140),
        "공고명":        st.column_config.TextColumn("공고명",   width="large"),
        "공고기관":      st.column_config.TextColumn("공고기관", width=150),
        "추정가격_표시": st.column_config.TextColumn("추정가격", width=90),
        "마감일":        st.column_config.TextColumn("마감일",   width=90),
        "마감D-Day":     st.column_config.NumberColumn("D-Day",  width=60, format="%d일"),
        "공고링크":      st.column_config.LinkColumn("바로가기", display_text="→ 공고", width=80),
        "수요기관":      st.column_config.TextColumn("수요기관"),
        "담당자":        st.column_config.TextColumn("담당자",   width=80),
        "담당자연락처":  st.column_config.TextColumn("연락처",   width=120),
    }

    row_h = 35
    tbl_h = min(max(400, 38 + len(df) * row_h), 1400)

    st.dataframe(df[show_cols], column_config=col_cfg, hide_index=True,
                 use_container_width=True, height=tbl_h)

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


# ── 메인 ─────────────────────────────────────────────────────────
st.title("📋 나라장터 입찰공고 대시보드")

# ── 조회 폼 ──────────────────────────────────────────────────────
with st.form("search_form"):
    st.subheader("🔍 조회 조건")

    with st.expander("🔑 API 키 설정"):
        api_key = st.text_input(
            "공공데이터포털 API 키",
            value=DEFAULT_API_KEY,
            type="password",
            placeholder="발급받은 API 키 입력",
            help="data.go.kr → 나라장터 입찰공고정보서비스 활용신청 후 발급",
        )
        st.markdown("""
**발급 방법**: [data.go.kr](https://www.data.go.kr) 로그인 → `나라장터 입찰공고` 검색 → 활용신청 → 마이페이지 → 인증키 관리 → `Decoding 키` 복사
        """)

    kw_input = st.text_area(
        "키워드 (쉼표로 구분, OR 검색)",
        value="",
        height=80,
        placeholder="예) 스마트, 경로당, AI, 교육, 박람회",
    )

    c1, c2 = st.columns(2)
    with c1:
        min_amount_man = st.number_input(
            "최소 추정가격 (만원, 0=전체)",
            value=0, min_value=0, step=500,
        )
    with c2:
        days = st.number_input(
            "게시 기간 (일)",
            value=7, min_value=1, max_value=60, step=1,
        )

    excl_input = st.text_input(
        "제외 키워드 (쉼표로 구분)",
        value="",
        placeholder="예) 시담, 재공고",
    )

    submitted = st.form_submit_button("🔄 공고 조회", use_container_width=True, type="primary")

# ── 조회 처리 ─────────────────────────────────────────────────────
if submitted:
    keywords     = [k.strip() for k in kw_input.split(",") if k.strip()]
    exclude_words = [e.strip() for e in excl_input.split(",") if e.strip()]
    min_amount   = min_amount_man * 10_000

    if not api_key:
        st.error("🔑 API 키를 입력해주세요. 위의 'API 키 설정'을 열어 입력하세요.")
        st.stop()

    with st.spinner("나라장터에서 공고를 가져오는 중..."):
        df = fetch_notices(
            api_key=api_key,
            keywords=keywords,
            min_amount=min_amount,
            days=days,
            exclude_words=exclude_words,
        )
    st.session_state.df           = df
    st.session_state.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ── 결과 표시 ─────────────────────────────────────────────────────
if "df" not in st.session_state:
    st.info("⬆️ 조회 조건을 입력하고 **공고 조회** 버튼을 눌러주세요.")
    st.stop()

df: pd.DataFrame = st.session_state.df

if "last_updated" in st.session_state:
    st.caption(f"조회 시각: {st.session_state.last_updated}")

st.caption("💡 **공고 링크**: 나라장터 **로그아웃** 상태에서 클릭하면 공고 페이지로 바로 이동합니다. 로그인 상태라면 공고번호로 직접 검색하세요.")

if df.empty:
    st.warning("조건에 맞는 공고가 없습니다. 키워드나 기간을 조정해보세요.")
    st.stop()

# ── 요약 카드 ────────────────────────────────────────────────────
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

st.markdown(f"""
<div class="metrics-grid">
  <div class="metric-card">
    <p class="metric-title">전체 공고 수</p>
    <p class="metric-value">{total}건</p>
  </div>
  <div class="metric-card deadline-critical">
    <p class="metric-title">마감 3일 이내 🚨</p>
    <p class="metric-value">{d3}건</p>
  </div>
  <div class="metric-card deadline-soon">
    <p class="metric-title">마감 7일 이내 ⚠️</p>
    <p class="metric-value">{d7}건</p>
  </div>
  <div class="metric-card amount-card" style="color:#065f46;">
    <p class="metric-title">총 추정가격</p>
    <p class="metric-value" style="color:#065f46;">{total_amount/100_000_000:.1f}억</p>
  </div>
</div>
""", unsafe_allow_html=True)

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
