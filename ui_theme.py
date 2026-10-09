"""상상우리 운영 도구 공통 Streamlit 테마 (2026-10-09, DESIGN.md).

사용: st.set_page_config(...) 바로 다음에 `ui_theme.inject()`.
.streamlit/config.toml [theme] 은 streamlit_config_theme.toml 과 맞춘다.
Streamlit 1.58 기준 data-testid 선택자. 버전업으로 안 먹으면 devtools로 속성 확인.
"""
from __future__ import annotations

import streamlit as st

TOKENS = {
    "paper": "#F7F6F2", "mist": "#EEF1F0", "line": "#E2E5E3",
    "ink": "#0A191A", "ink_soft": "#4B5A5A",
    "teal": "#008585", "teal_dark": "#0A6B69", "teal_soft": "#DDF0EE",
    "navy": "#0F1E3A", "navy_950": "#0A1428",
    "danger": "#B42318", "danger_soft": "#FDECEC",
    "warn": "#B45309", "warn_soft": "#FEF3E2",
    "ok": "#1F6B3A", "ok_soft": "#E3F3E8",
}

# 차트용 카테고리 팔레트 (청록 → 남색 → 주황 → 회색 순, 대비 검증)
CHART_COLORS = ["#008585", "#0F1E3A", "#D97A2B", "#7A8C8B", "#4FB3AE", "#8B5E3C"]

CSS = """
@import url('https://cdn.jsdelivr.net/npm/pretendard@1.3.9/dist/web/static/pretendard.min.css');
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700;800&display=swap');
:root{--paper:#F7F6F2;--mist:#EEF1F0;--line:#E2E5E3;--ink:#0A191A;--ink-soft:#4B5A5A;--teal:#008585;--teal-dark:#0A6B69;--teal-soft:#DDF0EE;--navy:#0F1E3A;--navy-950:#0A1428;--danger:#B42318;--danger-soft:#FDECEC;--warn:#B45309;--warn-soft:#FEF3E2;--ok:#1F6B3A;--ok-soft:#E3F3E8}
html,body,[class*="st-"],.stApp,.stMarkdown,button,input,textarea,select{font-family:Pretendard,"Pretendard Variable","Noto Sans KR",-apple-system,"Segoe UI",sans-serif !important}
/* 머티리얼 아이콘 글꼴은 글꼴 통일에서 제외(안 그러면 아이콘 이름이 글자로 찍힘) */
[data-testid="stIconMaterial"],.material-symbols-rounded,span[class*="material-symbols"]{font-family:"Material Symbols Rounded" !important}
.stApp{background:var(--paper);color:var(--ink)}
[data-testid="stHeader"]{background:transparent}
.block-container{padding-top:1.6rem;padding-bottom:4rem;max-width:1380px}
h1,h2,h3{color:var(--ink);letter-spacing:-.02em;font-weight:800 !important}
h1{font-size:1.9rem !important}h2{font-size:1.45rem !important}h3{font-size:1.15rem !important}
p,li,label,.stMarkdown{color:var(--ink)}
.stCaption,[data-testid="stCaptionContainer"]{color:var(--ink-soft) !important}
a{color:var(--teal-dark)}
hr{border-color:var(--line) !important;margin:1.4rem 0 !important}

/* 사이드바 — 남색 */
section[data-testid="stSidebar"]{background:var(--navy-950);border-right:0}
section[data-testid="stSidebar"] *{color:rgba(255,255,255,.82)}
section[data-testid="stSidebar"] h1,section[data-testid="stSidebar"] h2,section[data-testid="stSidebar"] h3{color:#fff !important;font-size:1.05rem !important}
section[data-testid="stSidebar"] hr{border-color:rgba(255,255,255,.12) !important}
section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"]{background:rgba(255,255,255,.06);border:1px dashed rgba(255,255,255,.28);border-radius:12px}
section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button{background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.25);color:#fff;border-radius:999px}
section[data-testid="stSidebar"] [data-baseweb="input"],section[data-testid="stSidebar"] [data-baseweb="base-input"],section[data-testid="stSidebar"] [data-baseweb="select"]>div{background:rgba(255,255,255,.08) !important;border-color:rgba(255,255,255,.22) !important;border-radius:10px}
section[data-testid="stSidebar"] input{color:#fff !important}
section[data-testid="stSidebar"] [data-testid="stMetric"]{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12)}
section[data-testid="stSidebar"] [data-testid="stMetricValue"]{color:#fff}
section[data-testid="stSidebar"] [data-testid="stMetricLabel"] *{color:rgba(255,255,255,.7)}
section[data-testid="stSidebar"] .stButton>button{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.22);color:#fff}
section[data-testid="stSidebar"] [data-testid="stAlert"]{background:rgba(255,255,255,.08);border:0}
section[data-testid="stSidebar"] [data-testid="stAlert"] *{color:#fff}
section[data-testid="stSidebar"] .pill{background:rgba(255,255,255,.14) !important;border-color:rgba(255,255,255,.2) !important;color:#fff !important}
section[data-testid="stSidebar"] [data-testid="stNumberInput"] button,section[data-testid="stSidebar"] [data-testid="stNumberInputStepDown"],section[data-testid="stSidebar"] [data-testid="stNumberInputStepUp"]{background:rgba(255,255,255,.1) !important;border-color:rgba(255,255,255,.22) !important;color:#fff !important}
section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] *{color:rgba(255,255,255,.75)}
section[data-testid="stSidebar"] code{background:rgba(255,255,255,.14) !important;color:#fff !important;border-radius:6px;padding:1px 6px}

/* 탭 → 알약 내비 */
div[data-testid="stTabs"] [data-baseweb="tab-list"]{gap:4px;background:transparent;border-bottom:1px solid var(--line);padding-bottom:10px;margin-bottom:6px;flex-wrap:wrap}
div[data-testid="stTabs"] button[data-baseweb="tab"]{border-radius:999px;padding:7px 14px;height:auto;background:transparent;color:var(--ink-soft);font-weight:600;font-size:.92rem}
div[data-testid="stTabs"] button[data-baseweb="tab"]:hover{background:var(--mist);color:var(--ink)}
div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"]{background:var(--navy);color:#fff}
div[data-testid="stTabs"] button[data-baseweb="tab"] p{font-size:.92rem;color:inherit}
div[data-testid="stTabs"] [data-baseweb="tab-highlight"],div[data-testid="stTabs"] [data-baseweb="tab-border"]{display:none}

/* KPI 타일 */
div[data-testid="stMetric"]{background:#fff;border:1px solid var(--line);border-radius:16px;padding:16px 16px 14px;box-shadow:0 1px 2px rgba(10,20,40,.04)}
div[data-testid="stMetricLabel"] *{font-size:.86rem !important;color:var(--ink-soft) !important;font-weight:600}
div[data-testid="stMetricValue"]{font-size:1.9rem !important;font-weight:800;color:var(--navy);letter-spacing:-.03em;font-variant-numeric:tabular-nums}
div[data-testid="stMetricDelta"]{font-size:.78rem !important;font-weight:700}

/* 버튼 */
.stButton>button,.stDownloadButton>button,[data-testid="stFormSubmitButton"]>button,[data-testid="stBaseButton-secondary"]{border-radius:999px;border:1px solid var(--line);background:#fff;color:var(--ink);font-weight:600;min-height:42px;padding:0 16px}
.stButton>button:hover,.stDownloadButton>button:hover{border-color:var(--teal);color:var(--teal-dark);background:#fff}
button[kind="primary"],button[kind="primaryFormSubmit"],[data-testid="stBaseButton-primary"],[data-testid="stBaseButton-primaryFormSubmit"]{background:var(--navy) !important;border-color:var(--navy) !important;color:#fff !important}
/* 버튼 라벨은 <p>로 렌더링되어 본문 p 색 규칙에 덮이므로 흰색을 명시 */
button[kind="primary"] p,button[kind="primaryFormSubmit"] p,[data-testid="stBaseButton-primary"] p,[data-testid="stBaseButton-primaryFormSubmit"] p{color:#fff !important}
button[kind="primary"]:hover,button[kind="primaryFormSubmit"]:hover,[data-testid="stBaseButton-primary"]:hover,[data-testid="stBaseButton-primaryFormSubmit"]:hover{background:var(--teal-dark) !important;border-color:var(--teal-dark) !important}
.login-brand{font-size:1.55rem}

/* 입력 */
[data-baseweb="input"],[data-baseweb="base-input"],[data-baseweb="select"]>div,[data-baseweb="textarea"]{border-radius:10px !important;border-color:var(--line) !important;background:#fff}
[data-baseweb="input"]:focus-within,[data-baseweb="textarea"]:focus-within{border-color:var(--teal) !important;box-shadow:0 0 0 3px rgba(0,133,133,.16)}
.stSlider [data-baseweb="slider"] [role="slider"]{background:var(--teal);border-color:var(--teal)}

/* 표·컨테이너·알림 */
[data-testid="stDataFrame"],[data-testid="stTable"]{border:1px solid var(--line);border-radius:14px;overflow:hidden;background:#fff}
details[data-testid="stExpander"]{background:#fff;border:1px solid var(--line);border-radius:14px}
details[data-testid="stExpander"] summary{font-weight:600}
[data-testid="stAlert"]{border-radius:12px;border:0}
[data-testid="stForm"]{background:#fff;border:1px solid var(--line);border-radius:16px;padding:20px 22px}
code,.stCode,pre{font-size:.86rem}

/* 공통 커스텀 클래스 (app 쪽 st.markdown 에서 사용) */
.sec{font-size:1.08rem;font-weight:800;color:var(--ink);letter-spacing:-.01em;margin:10px 0 2px;display:flex;align-items:center;gap:8px}
.sec:before{content:"";width:4px;height:18px;border-radius:2px;background:var(--teal)}
.hint{color:var(--ink-soft);font-size:.86rem;margin-bottom:10px}
.pill{display:inline-block;padding:2px 9px;border-radius:999px;font-size:.78rem;font-weight:600;border:1px solid var(--line);background:var(--mist);color:var(--ink-soft);margin-right:6px}
.pill.teal{background:var(--teal-soft);color:var(--teal-dark);border-color:transparent}
.pill.red{background:var(--danger-soft);color:var(--danger);border-color:transparent}
.pill.amb{background:var(--warn-soft);color:var(--warn);border-color:transparent}
.pill.ok{background:var(--ok-soft);color:var(--ok);border-color:transparent}
.eyebrow{display:flex;align-items:center;gap:10px;color:var(--teal-dark);font-weight:500;font-size:.95rem;margin-bottom:2px}
.eyebrow:before{content:"";width:22px;height:2px;background:var(--teal)}
.card{background:#fff;border:1px solid var(--line);border-radius:16px;padding:18px 20px;box-shadow:0 1px 2px rgba(10,20,40,.04)}

/* 로그인 화면 */
.login-wrap{max-width:440px;margin:6vh auto 0}
.login-brand{font-size:1.35rem;font-weight:800;color:var(--navy);letter-spacing:-.01em;margin:0}
.login-brand small{display:block;font-size:.85rem;font-weight:500;color:var(--teal-dark);margin-top:3px}
.login-sub{color:var(--ink-soft);font-size:.9rem;margin:10px 0 16px}
.login-note{color:var(--ink-soft);font-size:.82rem;line-height:1.6}
.login-foot{margin-top:18px;text-align:center;color:var(--ink-soft);font-size:.78rem}

@media (max-width:640px){.block-container{padding-left:1rem;padding-right:1rem}div[data-testid="stMetricValue"]{font-size:1.5rem !important}}
"""


def inject(extra_css: str = "") -> None:
    """공통 CSS 주입. 앱 고유 규칙은 extra_css 로 덧붙인다."""
    st.markdown(f"<style>{CSS}{extra_css}</style>", unsafe_allow_html=True)


def eyebrow(text: str) -> None:
    st.markdown(f"<div class='eyebrow'>{text}</div>", unsafe_allow_html=True)


def pill(text: str, kind: str = "") -> str:
    """st.markdown(..., unsafe_allow_html=True) 안에 끼워 쓰는 상태 pill HTML."""
    return f"<span class='pill {kind}'>{text}</span>"
