"""나라장터 입찰공고 대시보드"""
import streamlit as st
import pandas as pd
from datetime import datetime
import os

from api_client import fetch_notices, fetch_prespec


@st.cache_data
def load_keyword_presets():
    """search.xlsx에서 우선순위별 키워드 로드"""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "search.xlsx")
    try:
        df = pd.read_excel(path)
        p1 = df.iloc[:, 0].dropna().astype(str).str.strip().tolist()
        p2 = df.iloc[:, 1].dropna().astype(str).str.strip().tolist()
        p3 = df.iloc[:, 2].dropna().astype(str).str.strip().tolist()
        return p1, p2, p3
    except Exception:
        return [], [], []

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


# 사전규격 공개 목록 페이지 (등록번호 파라미터로 해당 항목 조회)
PRESPEC_LINK_BASE = "https://www.g2b.go.kr/pb/pn/pbsy/publicpbsy028m01.do"


def show_table(data: pd.DataFrame, show_all: bool = True):
    df = data.copy()

    def _g2b_url(row):
        url = str(row.get("공고URL", "") or "")
        return url if url.startswith("http") else ""

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


def show_prespec_table(data: pd.DataFrame, tab_key: str = "all"):
    df = data.copy()

    def _ps_url(row):
        reg_no = str(row.get("등록번호", "") or "")
        return f"{PRESPEC_LINK_BASE}?bfSpecRgstNo={reg_no}" if reg_no else ""

    df["사전규격링크"] = df.apply(_ps_url, axis=1)
    df["추정가격_표시"] = df["추정가격"].apply(_amt_str)
    df["의견마감일"] = df["의견접수마감"].astype(str).str[:10] if "의견접수마감" in df.columns else ""
    df["공고일"] = df["공고일시"].astype(str).str[:10]

    q = st.text_input(
        "결과 내 검색",
        placeholder="사전규격명 · 기관명으로 필터...",
        key=f"ps_q_{tab_key}",
        label_visibility="collapsed",
    )
    fc1, fc2 = st.columns([3, 1])
    with fc1:
        sort_opt = st.selectbox(
            "정렬",
            ["의견마감 빠른순", "의견마감 느린순", "추정가격 높은순", "추정가격 낮은순", "등록일 최신순"],
            key=f"ps_sort_{tab_key}",
            label_visibility="collapsed",
        )
    with fc2:
        st.caption(f"**{len(df):,}건**")

    if q:
        mask = (
            df["사전규격명"].str.contains(q, case=False, na=False) |
            df["공고기관"].str.contains(q, case=False, na=False)
        )
        df = df[mask]
        st.caption(f"'{q}' 필터 결과: {len(df):,}건")

    sort_map = {
        "의견마감 빠른순": ("마감D-Day", True),
        "의견마감 느린순": ("마감D-Day", False),
        "추정가격 높은순": ("추정가격",  False),
        "추정가격 낮은순": ("추정가격",  True),
        "등록일 최신순":   ("공고일시",  False),
    }
    sort_col, sort_asc = sort_map[sort_opt]
    if sort_col in df.columns:
        df = df.sort_values(sort_col, ascending=sort_asc, na_position="last")

    base_cols  = ["공고일", "등록번호", "사전규격명", "공고기관", "추정가격_표시", "의견마감일", "마감D-Day", "사전규격링크"]
    extra_cols = ["수요기관", "담당자", "담당자연락처"]
    show_cols  = [c for c in base_cols + extra_cols if c in df.columns]

    col_cfg = {
        "공고일":        st.column_config.TextColumn("등록일",     width=90),
        "등록번호":      st.column_config.TextColumn("등록번호",   width=160),
        "사전규격명":    st.column_config.TextColumn("사전규격명", width="large"),
        "공고기관":      st.column_config.TextColumn("공고기관",   width=150),
        "추정가격_표시": st.column_config.TextColumn("추정가격",   width=90),
        "의견마감일":    st.column_config.TextColumn("의견마감",   width=90),
        "마감D-Day":     st.column_config.NumberColumn("D-Day",    width=60, format="%d일"),
        "사전규격링크":  st.column_config.LinkColumn("바로가기",   display_text="→ 규격", width=80),
        "수요기관":      st.column_config.TextColumn("수요기관"),
        "담당자":        st.column_config.TextColumn("담당자",     width=80),
        "담당자연락처":  st.column_config.TextColumn("연락처",     width=120),
    }

    row_h = 35
    tbl_h = min(max(400, 38 + len(df) * row_h), 1400)
    st.dataframe(df[show_cols], column_config=col_cfg, hide_index=True,
                 use_container_width=True, height=tbl_h)

    csv = data.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        "⬇️ CSV로 저장",
        data=csv,
        file_name=f"나라장터_사전규격_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        key=f"ps_csv_{tab_key}",
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
st.title("상상우리 나라장터 조회")

# ── API 키: 사이드바에 숨김 ───────────────────────────────────────
with st.sidebar:
    st.subheader("🔑 API 키 설정")
    api_key = st.text_input(
        "공공데이터포털 API 키",
        value=DEFAULT_API_KEY,
        type="password",
        placeholder="발급받은 API 키 입력",
        help="data.go.kr → 나라장터 활용신청 후 발급한 Decoding 키",
    )

# ── 조회 폼 ──────────────────────────────────────────────────────
with st.form("search_form"):
    st.subheader("🔍 조회 조건")

    p1_kws, p2_kws, p3_kws = load_keyword_presets()

    if p1_kws or p2_kws or p3_kws:
        st.markdown("**🔖 우선순위별 키워드 선택** (OR 검색 — 선택한 키워드 중 하나라도 포함된 공고 조회)")
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            sel1 = st.multiselect(
                "🥇 1순위",
                options=p1_kws,
                default=[],
                help="핵심 키워드 — 이 중 하나 이상 포함 시 우선 조회",
                placeholder="1순위 키워드 선택...",
            )
        with col_p2:
            sel2 = st.multiselect(
                "🥈 2순위",
                options=p2_kws,
                default=[],
                help="보조 키워드",
                placeholder="2순위 키워드 선택...",
            )
        with col_p3:
            sel3 = st.multiselect(
                "🥉 3순위",
                options=p3_kws,
                default=[],
                help="참고 키워드",
                placeholder="3순위 키워드 선택...",
            )
    else:
        sel1, sel2, sel3 = [], [], []

    kw_input = st.text_input(
        "추가 키워드 (쉼표로 구분, OR 검색)",
        value="",
        placeholder="위 목록에 없는 키워드 직접 입력 — 예) 박람회, 세미나",
    )

    c1, c2 = st.columns(2)
    with c1:
        min_amount_man = st.number_input(
            "최소 추정가격 (만원, 0=전체)",
            value=5000, min_value=0, step=500,
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
    preset_kws   = sel1 + sel2 + sel3
    custom_kws   = [k.strip() for k in kw_input.split(",") if k.strip()]
    # 중복 제거, 순서 유지 (1순위 → 2순위 → 3순위 → 추가)
    seen = set()
    keywords = []
    for kw in preset_kws + custom_kws:
        if kw not in seen:
            seen.add(kw)
            keywords.append(kw)
    exclude_words = [e.strip() for e in excl_input.split(",") if e.strip()]
    min_amount   = min_amount_man * 10_000

    if not api_key:
        st.error("🔑 API 키를 입력해주세요. 왼쪽 사이드바(☰)의 'API 키 설정'에 입력하세요.")
        st.stop()

    with st.spinner("나라장터에서 입찰공고 및 사전규격을 가져오는 중..."):
        df = fetch_notices(
            api_key=api_key,
            keywords=keywords,
            min_amount=min_amount,
            days=days,
            exclude_words=exclude_words,
        )
        try:
            df_prespec, prespec_err, prespec_raw = fetch_prespec(
                api_key=api_key,
                keywords=keywords,
                min_amount=min_amount,
                days=days,
                exclude_words=exclude_words,
            )
        except Exception as e:
            df_prespec = pd.DataFrame()
            prespec_err = f"fetch_prespec 실행 오류: {type(e).__name__}: {e}"
            prespec_raw = 0

    st.session_state.df              = df
    st.session_state.df_prespec      = df_prespec
    st.session_state.prespec_error   = prespec_err
    st.session_state.prespec_raw     = prespec_raw
    st.session_state.last_updated    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.search_keywords = keywords

# ── 결과 표시 ─────────────────────────────────────────────────────
if "df" not in st.session_state:
    st.info("⬆️ 조회 조건을 입력하고 **공고 조회** 버튼을 눌러주세요.")
    st.stop()

if "last_updated" in st.session_state:
    st.caption(f"조회 시각: {st.session_state.last_updated}")

st.caption("💡 **링크**: 나라장터 **로그아웃** 상태에서 클릭하면 페이지로 바로 이동합니다. 로그인 상태라면 번호로 직접 검색하세요.")

today = datetime.now()

top_tab1, top_tab2 = st.tabs(["📋 입찰공고", "📑 사전규격"])

# ── 입찰공고 탭 ──────────────────────────────────────────────────
with top_tab1:
    df: pd.DataFrame = st.session_state.df

    if df.empty:
        st.warning("조건에 맞는 입찰공고가 없습니다. 키워드나 기간을 조정해보세요.")
    else:
        df = df.copy()
        df["마감D-Day"] = df["입찰마감"].apply(
            lambda x: int((pd.to_datetime(x, errors="coerce") - today).days)
            if pd.notnull(pd.to_datetime(x, errors="coerce")) else None
        )
        df = df[df["마감D-Day"].isna() | (df["마감D-Day"] >= 0)]

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

# ── 사전규격 탭 ──────────────────────────────────────────────────
with top_tab2:
    df_ps: pd.DataFrame = st.session_state.get("df_prespec", pd.DataFrame())
    prespec_err  = st.session_state.get("prespec_error")
    prespec_raw  = st.session_state.get("prespec_raw", 0)
    search_kws   = st.session_state.get("search_keywords", [])

    # 에러 발생 시 명확하게 표시
    if prespec_err:
        st.error(f"사전규격 조회 오류: {prespec_err}")
        st.info("""**API 오류가 발생했다면 활용신청을 확인하세요.**
1. [공공데이터포털](https://www.data.go.kr) 로그인
2. **"조달청 나라장터 사전규격정보서비스"** 검색 → 활용신청
3. 입찰공고 API와 **별도 신청** 필요 (같은 키 사용)
4. 승인 후 마이페이지 → 개발계정 → `Decoding 키` 확인""")

    if df_ps.empty and not prespec_err:
        if prespec_raw > 0:
            st.warning(f"API에서 {prespec_raw:,}건을 가져왔으나 키워드 필터 후 결과가 없습니다. 키워드를 변경해보세요.")
        else:
            st.warning("조건에 맞는 사전규격이 없습니다. 기간을 늘리거나 키워드를 조정해보세요.")
            if not prespec_err:
                st.info("""**사전규격이 조회되지 않는다면:**
1. [공공데이터포털](https://www.data.go.kr) → **"조달청 나라장터 사전규격정보서비스"** 활용신청 (입찰공고와 별도)
2. 승인 후 동일한 API 키 사용 가능
3. 활용 승인까지 최대 1~2일 소요""")

    if not df_ps.empty:
        df_ps = df_ps.copy()

        # 의견접수마감 D-Day 계산
        if "의견접수마감" in df_ps.columns:
            def _calc_dday(x):
                try:
                    ts = pd.to_datetime(x, errors="coerce")
                    if pd.isnull(ts):
                        return None
                    delta = ts.replace(tzinfo=None) - today
                    return delta.days
                except Exception:
                    return None
            df_ps["마감D-Day"] = df_ps["의견접수마감"].apply(_calc_dday)
        else:
            df_ps["마감D-Day"] = None

        # 업무구분 필터 (사전규격 탭 내)
        if "업무구분" in df_ps.columns:
            biz_types = sorted(df_ps["업무구분"].dropna().unique().tolist())
            if biz_types:
                sel_biz = st.multiselect(
                    "업무구분 필터",
                    options=biz_types,
                    default=[],
                    placeholder="전체 (선택하면 해당 구분만 표시)",
                    key="ps_biz_filter",
                )
                if sel_biz:
                    df_ps = df_ps[df_ps["업무구분"].isin(sel_biz)]

        # 검색 키워드 표시
        if search_kws:
            st.caption(f"검색 키워드: {', '.join(search_kws)} | API 조회 {prespec_raw:,}건 → 키워드 필터 후 {len(df_ps):,}건")

        ps_total  = len(df_ps)
        d_col     = "마감D-Day"
        ps_d3     = int((df_ps[d_col].notna() & (df_ps[d_col] <= 3)  & (df_ps[d_col] >= 0)).sum()) if d_col in df_ps.columns else 0
        ps_d7     = int((df_ps[d_col].notna() & (df_ps[d_col] <= 7)  & (df_ps[d_col] >= 0)).sum()) if d_col in df_ps.columns else 0
        ps_amount = int(df_ps["추정가격"].sum()) if "추정가격" in df_ps.columns else 0

        st.markdown(f"""
<div class="metrics-grid">
  <div class="metric-card">
    <p class="metric-title">전체 사전규격</p>
    <p class="metric-value">{ps_total}건</p>
  </div>
  <div class="metric-card deadline-critical">
    <p class="metric-title">의견마감 3일 이내 🚨</p>
    <p class="metric-value">{ps_d3}건</p>
  </div>
  <div class="metric-card deadline-soon">
    <p class="metric-title">의견마감 7일 이내 ⚠️</p>
    <p class="metric-value">{ps_d7}건</p>
  </div>
  <div class="metric-card amount-card" style="color:#065f46;">
    <p class="metric-title">총 추정가격</p>
    <p class="metric-value" style="color:#065f46;">{ps_amount/100_000_000:.1f}억</p>
  </div>
</div>
""", unsafe_allow_html=True)

        st.divider()

        ps_tab1, ps_tab2, ps_tab3 = st.tabs(["📑 전체 목록", "🚨 의견마감 임박 (7일)", "📊 통계"])

        with ps_tab1:
            show_prespec_table(df_ps, tab_key="all")

        with ps_tab2:
            urgent_ps = df_ps[
                df_ps["마감D-Day"].notna() &
                (df_ps["마감D-Day"] <= 7) &
                (df_ps["마감D-Day"] >= 0)
            ].sort_values("마감D-Day") if "마감D-Day" in df_ps.columns else pd.DataFrame()

            if urgent_ps.empty:
                st.success("✅ 7일 이내 의견마감 사전규격이 없습니다.")
                st.caption("의견접수 기간이 보통 5~7일이므로, 이미 마감된 건이 많을 수 있습니다. 전체 목록 탭을 확인하세요.")
            else:
                st.warning(f"의견마감 7일 이내 사전규격 **{len(urgent_ps)}건** — 빨리 확인하세요!")
                show_prespec_table(urgent_ps, tab_key="urg")

        with ps_tab3:
            show_stats(df_ps)
