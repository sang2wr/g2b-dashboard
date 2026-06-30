# 나라장터 입찰공고 대시보드 개발 대화 기록

## 프로젝트 개요
- **목적**: 나라장터 G2B OpenAPI를 이용한 입찰공고 실시간 대시보드
- **기술 스택**: Python + Streamlit, 나라장터 OpenAPI
- **작업 디렉터리**: `C:\Users\82104\g2b_dashboard\`

---

## 주요 파일 구성

| 파일 | 역할 |
|------|------|
| `app.py` | Streamlit 메인 앱 (UI, 필터, 테이블, 통계) |
| `api_client.py` | 나라장터 API 연동, 데이터 정규화 |
| `proxy.py` | 공고 URL 프록시 서버 (localhost:8502) |
| `.env` | API 키 저장 (`G2B_API_KEY=...`) |

---

## API 정보

- **엔드포인트**: `http://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServcPPSSrch`
- **API Key**: `fc7967b7c6bf52786fd564daeced70409bb05255b1739d1b4f2bf981bb4c6a8a`
- **주요 필드**:
  - `bidNtceNo` → 공고번호
  - `bidNtceNm` → 공고명
  - `ntceInsttNm` → 공고기관
  - `dminsttNm` → 수요기관
  - `presmptPrce` → 추정가격
  - `bidNtceDt` → 공고일시
  - `bidClseDt` → 입찰마감
  - `bidNtceUrl` → 공고URL (`/link/PNPE027_01/single/` 형식)
  - `bidNtceOrd` → 공고순번 (보통 "000")

---

## 해결한 문제들

### 1. Streamlit 이메일 프롬프트 문제
- **증상**: Streamlit 최초 실행 시 이메일 입력 프롬프트로 대기
- **해결**: `~/.streamlit/credentials.toml`에 `email = ""` 추가

### 2. API 연동
- 318건 실시간 데이터 정상 조회 확인
- 키워드 OR 검색, 최소 추정가격 필터, 기간 필터, 제외 키워드 구현

### 3. iframe 링크 차단 문제
- **증상**: `st.components.html()` 내 샌드박스 iframe에서 `target="_blank"` 링크 차단
- **해결**: `st.link_button` → `st.markdown(unsafe_allow_html=True)` HTML 테이블 순으로 전환

---

## 미해결 → 최종 해결한 문제들

### 문제 1: 공고 링크 클릭 시 "공고정보가 없다" 팝업

**원인 분석**:
```
브라우저 → /link/ URL → SSO(sso.g2b.go.kr) → ?
  - 브라우저에 기존 나라장터 쿠키 있음 → relay=홈페이지 → 홈페이지 이동
  - 브라우저에 쿠키 없음 → base_uri=공고URL → 공고 이동
```

**기존 proxy.py 문제**:
```python
# 전체 리다이렉트 따라가서 key 포함 URL 취득
r = s.get(src, timeout=12, allow_redirects=True)
resolved = r.url  # bodyDataKey + key 포함
# key는 Python 세션 전용 → 브라우저에서 사용 시 "공고정보가 없다"
```

**최종 proxy.py 수정 (핵심)**:
```python
# 첫 번째 302만 받아 SSO URL의 base_uri 파라미터 추출
r0 = s.get(src, timeout=10, allow_redirects=False)

if r0.status_code == 302:
    sso_loc = r0.headers.get("Location", "")
    sso_params = parse_qs(urlparse(sso_loc).query)
    base_uri_enc = sso_params.get("base_uri", [""])[0]
    if base_uri_enc:
        target = unquote(base_uri_enc)  # bodyDataKey 포함, key 없음
        # 브라우저가 이 URL로 가면 나라장터가 브라우저 세션용 key 신규 발급
```

**원리**: `base_uri`에는 `bodyDataKey`(공고 식별자)는 있지만 `key`(세션 전용)는 없음 → 브라우저가 자체 세션으로 `key` 발급하여 공고 정상 표시

---

### 문제 2: 한글 문자 깨짐 ("스마트 경로당" → "스마트 교통당")

**원인**: `st.markdown(unsafe_allow_html=True)` + HTML 테이블 방식에서 Streamlit 마크다운 파서가 일부 한글 유니코드 문자를 오처리

**해결**: HTML 테이블 방식 → `st.dataframe` + `st.column_config.LinkColumn` 방식으로 전환

```python
# 수정 전 (HTML 테이블 → 한글 깨짐)
name = _html.escape(str(row.get("공고명", "") or ""))
# ... HTML 문자열 조합 ...
st.markdown(table_html, unsafe_allow_html=True)

# 수정 후 (st.dataframe → 한글 네이티브 처리)
df["공고링크"] = df.apply(_proxy_url, axis=1)
col_cfg = {
    "공고명": st.column_config.TextColumn("공고명", width="large"),
    "공고링크": st.column_config.LinkColumn("공고 바로가기", display_text="→ 공고보기"),
    ...
}
st.dataframe(df[show_cols], column_config=col_cfg, hide_index=True)
```

---

## 최종 아키텍처 (데이터 흐름)

```
[사용자 브라우저]
       ↓ localhost:8501
[Streamlit 앱 (app.py)]
       ↓ API 조회
[나라장터 OpenAPI (apis.data.go.kr)]
       ↓ 공고 데이터 반환
[app.py - st.dataframe 표시]
       ↓ "→ 공고보기" 클릭
[프록시 서버 (proxy.py, localhost:8502)]
       ↓ allow_redirects=False로 첫 302만 받음
[나라장터 SSO URL에서 base_uri 추출]
       ↓ 302 redirect → base_uri
[나라장터 공고 상세 페이지]
```

---

## 실행 방법

```powershell
# g2b_dashboard 폴더에서
cd C:\Users\82104\g2b_dashboard
python -m streamlit run app.py --server.port 8501
```

브라우저에서 `http://localhost:8501` 접속

---

## 주요 발견 사항 / 트러블슈팅 노트

1. **나라장터 SSO 동작**: 브라우저 세션 쿠키 유무에 따라 `relay`(홈) vs `base_uri`(공고) 분기
2. **proxy.py daemon thread**: Streamlit 프로세스가 종료되면 daemon 스레드도 함께 종료 → Streamlit 재시작 시 자동 복구
3. **Claude Code 샌드박스**: 테스트 환경에서 g2b.go.kr(포트 443) 직접 접근 불가 (방화벽 `codex_sandbox_offline_block_outbound`). Streamlit 프로세스는 사용자 환경에서 실행되므로 프록시는 정상 작동
4. **API URL 필드**: `bidNtceUrl`과 `bidNtceDtlUrl` 모두 동일한 `/link/PNPE027_01/single/` URL 반환. 직접 공고 페이지 URL은 API에서 제공하지 않음
5. **중복 CSV 다운로드 버튼**: 코드 실수로 두 번 생성된 버튼 제거

---

## 사이드바 기본 설정

| 항목 | 기본값 |
|------|--------|
| 키워드 (OR) | 스마트, 경로당, AI, 교육, 박람회 |
| 최소 추정가격 | 1,000만원 |
| 최근 기간 | 7일 |
| 제외 키워드 | 시담 |

---

*기록 생성일: 2026-06-25*

---

## 2026-06-26 세션 기록

### 앱 실행 확인

- `ipchal.md` 파일 내용 확인
- 앱 실행 명령:
  ```powershell
  cd C:\Users\82104\g2b_dashboard
  python -m streamlit run app.py --server.port 8501
  ```
- **결과**: `http://localhost:8501` 정상 접속 확인
  - 샘플 데이터 표시 중 (전체 공고 8건, 마감 3일 이내 2건, 마감 7일 이내 6건, 총 추정가격 14.3억)
  - 사이드바 API 키 입력 후 "공고 조회" 클릭 시 실시간 데이터 조회 가능
  - 탭 구성: 전체 목록 / 마감 임박(7일) / 통계

*기록 추가일: 2026-06-26*

---

## 2026-06-26 세션 2 — 공고 링크 디버깅 및 proxy 수정

### 발견한 버그: proxy가 app.py에 연결되지 않았음

기존 `app.py`는 `proxy.py`를 import하지 않고 직접 g2b.go.kr 링크를 생성하고 있었음.

**수정 내용 (app.py)**:
```python
# 수정 전
from api_client import fetch_notices, sample_data
G2B_LINK_BASE = "https://www.g2b.go.kr/link/PNPE027_01/single/"
# ... _g2b_url에서 G2B_LINK_BASE 사용

# 수정 후
from api_client import fetch_notices, sample_data
import proxy as _proxy
_proxy.ensure_running()
# ... _g2b_url에서 _proxy.PROXY_BASE 사용 (localhost:8502)
```

링크 URL 변경:
- 이전: `https://www.g2b.go.kr/link/.../single/?bidPbancNo=...`
- 이후: `http://localhost:8502/?no=...&ord=...`

---

### Claude Code 샌드박스 네트워크 제한 문제

**증상**: proxy가 502 반환, 브라우저에서 공고 링크 클릭 시 에러 페이지

**원인**:
- Claude Code 샌드박스 환경에서 HTTPS (포트 443) 아웃바운드 차단
- `www.g2b.go.kr`, `www.data.go.kr`, `www.korea.go.kr` 등 모든 정부 HTTPS 사이트 연결 불가
- Claude Code가 시작한 Streamlit 프로세스도 같은 네트워크 제한 상속
- 단, HTTP (포트 80) — API 호출(`apis.data.go.kr`)은 정상 동작

**proxy.py 추가 수정 — 폴백 처리**:
```python
# 수정 전: 연결 실패 시 502 반환
except Exception:
    self.send_response(502); self.end_headers()

# 수정 후: 연결 실패 시 직접 SSO 링크로 302 리다이렉트
except Exception:
    fallback = f"https://www.g2b.go.kr/link/PNPE027_01/single/?bidPbancNo={bid_no}&bidPbancOrd={bid_ord}"
    self.send_response(302)
    self.send_header("Location", fallback)
    self.end_headers()
```

---

### 환경별 동작 차이

| 실행 환경 | proxy 동작 | 공고 링크 결과 |
|----------|-----------|--------------|
| Claude Code가 시작한 앱 | g2b.go.kr 연결 불가 → 폴백(직접 SSO 링크) | 나라장터 로그인 상태면 홈, 로그아웃이면 공고 페이지 |
| 사용자가 직접 실행한 앱 | proxy 정상 작동 | base_uri 추출 → 공고 페이지 바로 이동 |

**결론**: 사용자가 Claude Code 없이 직접 아래 명령으로 실행해야 proxy가 정상 작동함:
```powershell
cd C:\Users\82104\g2b_dashboard
python -m streamlit run app.py --server.port 8501
```

*기록 추가일: 2026-06-26 (세션 2)*

---

## 배포 정보

- **플랫폼**: Streamlit Community Cloud
- **배포 URL**: https://g2b-dashboard-gnh9bmrne9le7miyleowff.streamlit.app/
- **배포 완료일**: 2026-06-26

---

## 2026-06-26 세션 3 — 클라우드 배포 후 공고 링크 문제 해결

### 문제: 배포 환경에서 공고 링크 클릭 시 에러

**증상**: `→ 공고보기` 클릭 시 `{"ErrorMsg":"에러가 발생하였습니다.","ErrorCode":-1}` 반환

**원인 분석**:
- 클라우드 배포 시 `proxy.py`는 Streamlit Cloud 서버의 `localhost:8502`에서 실행
- 링크 URL이 `http://localhost:8502/?no=...` 형태 → 사용자 **브라우저**가 자기 PC의 localhost에 접속 시도 → 연결 거부

**1차 시도 — 서버 사이드 URL 사전 해석 (실패)**:
```python
# proxy.py에 resolve_notice_url() 함수 추가
# ThreadPoolExecutor로 병렬 해석 후 _resolved_url 컬럼에 저장
```
- 결과: 여전히 에러 (`bodyDataKey` 두 개 + `key` 포함된 URL)
- **근본 원인**: `bodyDataKey`도 서버 세션에 종속된 값 → 브라우저 세션에서 사용 불가
  - SSO 리다이렉트 체인: `/link/` → SSO(`base_uri` 추출) → `/link/?bodyDataKey=A` → SSO 재처리(`bodyDataKey=B`, `key=...`) → 에러
  - `base_uri` 자체도 `/link/` URL이라 브라우저가 방문 시 SSO를 한 번 더 거치면서 두 번째 `bodyDataKey` + `key` 추가됨

**최종 해결 — 직접 SSO 링크 사용**:
```python
G2B_LINK_BASE = "https://www.g2b.go.kr/link/PNPE027_01/single/"

def _g2b_url(row):
    bid_no  = str(row.get("공고번호", "") or "")
    bid_ord = str(row.get("bidNtceOrd", "000") or "000")
    return f"{G2B_LINK_BASE}?bidPbancNo={bid_no}&bidPbancOrd={bid_ord}" if bid_no else ""
```

**환경별 동작**:
| 상태 | 결과 |
|------|------|
| 나라장터 **로그아웃** | 공고 페이지 바로 이동 ✓ |
| 나라장터 **로그인** | 나라장터 홈으로 이동 (공고번호 복사 후 검색 필요) |

- 테이블에 **공고번호 컬럼** 추가하여 로그인 상태 대응
- `proxy.py`는 로컬 실행용으로 유지 (클라우드에서는 미사용)

---

## 2026-06-26 세션 4 — 검색 편의성 및 테이블 스크롤 개선

### 변경 내용

**테이블 높이 동적 조정**:
```python
row_h = 35
tbl_h = min(max(400, 38 + len(df) * row_h), 1400)
st.dataframe(..., height=tbl_h)
```
- 이전: 고정 580px → 이후: 행 수 기반 동적 (최소 400 ~ 최대 1400px)

**결과 내 빠른 검색 추가**:
```python
q = st.text_input("결과 내 검색", placeholder="공고명 · 기관명으로 필터...")
if q:
    mask = df["공고명"].str.contains(q, ...) | df["공고기관"].str.contains(q, ...)
    df = df[mask]
```

**정렬 옵션 추가**:
- 마감일 빠른순 / 느린순
- 추정가격 높은순 / 낮은순
- 공고일 최신순

**사이드바 개편**:
- 조회 조건(키워드, 금액, 기간, 제외어)을 상단으로 이동
- API 키 설정을 `st.expander`로 접기 처리
- 기간 설정: 슬라이더(max 30일) → 숫자 입력(max 60일)

*기록 추가일: 2026-06-26 (세션 3·4)*

---

## 2026-06-26 세션 5 — 모바일 최적화 및 UX 개선

### 변경 1: 모바일 최적화

**`initial_sidebar_state`**: `expanded` → `collapsed` (모바일에서 사이드바가 화면 절반 차지하는 문제 해결)

**메트릭 카드 반응형 그리드**:
- 기존: `st.columns(4)` — 모바일에서 초소형 4칸
- 변경: CSS grid `repeat(auto-fit, minmax(140px, 1fr))` — 화면 너비에 따라 자동 2×2 또는 4×1

**모바일 CSS 추가**:
```css
@media (max-width: 768px) {
  .stButton > button { min-height: 48px !important; font-size: 16px !important; }
  .stTextInput > div > div > input, .stTextArea textarea {
    font-size: 16px !important; /* iOS 자동 줌 방지 */
  }
}
```

**검색/정렬 컨트롤**: 3열(검색·정렬·건수) → 검색 1행 + 정렬/건수 2열

**사이드바 입력 필드**: 금액·기간 2열 나란히 → 단일 열 (터치 편의)

---

### 변경 2: 조회조건 UX 개선

**구조 재설계**:
- 기존: 조회조건이 사이드바에 숨겨져 있음 (모바일에서 찾기 어려움)
- 변경: 메인 화면 상단에 `st.form("search_form")`으로 항상 표시

**사이드바 제거**: 모든 조회조건·API키 설정을 메인 폼으로 이동

**기본값 모두 제거**:
| 항목 | 이전 기본값 | 변경 후 |
|------|------------|---------|
| 키워드 | `스마트, 경로당, AI, 교육, 박람회` | 빈 값 |
| 최소 추정가격 | `1,000만원` | `0` (전체) |
| 제외 키워드 | `시담` | 빈 값 |

**샘플 데이터 제거**:
- 기존: 앱 진입 시 샘플 데이터 8건 자동 표시
- 변경: "조회 조건을 입력하고 공고 조회 버튼을 눌러주세요" 안내 표시
- `sample_data()` import 제거

**API 키 없을 때**: 샘플 데이터 대체 → 에러 메시지 표시 후 `st.stop()`

---

### 변경 3: 마감일 지난 공고 자동 제외

```python
# D-Day 계산 후 음수(마감 지난 것) 필터
df = df[df["마감D-Day"].isna() | (df["마감D-Day"] >= 0)]
```
- 마감일 정보가 있고 D-Day < 0인 공고는 결과에서 자동 제외
- 마감일 정보 없는 공고(isna)는 그대로 표시

---

### 커밋 이력

| 커밋 | 내용 |
|------|------|
| `6c8f9ff` | 모바일 최적화: 반응형 메트릭 그리드, 사이드바 기본 닫힘, 터치 타겟 개선 |
| `8a49581` | UX 개선: 조회조건 메인화면 이동, 기본값 제거, 샘플 데이터 제거 |
| `4213df6` | 마감일 지난 공고 자동 제외 (D-Day 음수 필터) |

*기록 추가일: 2026-06-26 (세션 5)*

---

## 2026-06-29 세션 6 — search.xlsx 우선순위 키워드 멀티셀렉트 추가

### 변경 목적

기존에는 키워드를 쉼표로 직접 타이핑해야 했음.
`search.xlsx` 파일에 1~3순위로 분류된 키워드를 멀티셀렉트 위젯으로 손쉽게 선택할 수 있도록 개선.

### search.xlsx 구조

| 1순위 (31개) | 2순위 (16개) | 3순위 (11개) |
|-------------|-------------|-------------|
| AI, 튜터, 경로당, 늘봄, 디지털, 청년, 포용, 리터러시, 시니어, 장년, 중년, 일자리, 경력, 단절, 은퇴, 퇴직, 퇴사, 재기, 도전, 전직, 취업, 노하우, 상생, 매칭, 프로보노, 재능, 어르신, 새싹, 노인, 고령 | 혁신, 사회적, 공간, 희망, 힐링, 체인지, 임팩트, 캠프, 격차, 부트, 제작, 기부, 스페이스, 메이커, 소셜벤처, 취약 | 시티즌, 엘더리, 40대, 50대, 60대, 40플러스, 50플러스, 60플러스, 연장자, 실버, 에이징 |

### 주요 변경 내용

**`requirements.txt`**:
```
openpyxl>=3.1.0  # 추가
```

**`app.py` — `load_keyword_presets()` 함수 추가**:
```python
@st.cache_data
def load_keyword_presets():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "search.xlsx")
    try:
        df = pd.read_excel(path)
        p1 = df.iloc[:, 0].dropna().astype(str).str.strip().tolist()
        p2 = df.iloc[:, 1].dropna().astype(str).str.strip().tolist()
        p3 = df.iloc[:, 2].dropna().astype(str).str.strip().tolist()
        return p1, p2, p3
    except Exception:
        return [], [], []
```

**`app.py` — 조회 폼 키워드 입력 교체**:
```python
# 수정 전: 텍스트 직접 입력
kw_input = st.text_area("키워드 (쉼표로 구분, OR 검색)", ...)

# 수정 후: 우선순위별 multiselect + 추가 입력
p1_kws, p2_kws, p3_kws = load_keyword_presets()
col_p1, col_p2, col_p3 = st.columns(3)
with col_p1:
    sel1 = st.multiselect("🥇 1순위", options=p1_kws, default=[])
with col_p2:
    sel2 = st.multiselect("🥈 2순위", options=p2_kws, default=[])
with col_p3:
    sel3 = st.multiselect("🥉 3순위", options=p3_kws, default=[])
kw_input = st.text_input("추가 키워드 (쉼표로 구분, OR 검색)", ...)
```

**`app.py` — 키워드 합산 (중복 제거)**:
```python
preset_kws = sel1 + sel2 + sel3
custom_kws = [k.strip() for k in kw_input.split(",") if k.strip()]
# 순서 유지 중복 제거: 1순위 → 2순위 → 3순위 → 추가
seen = set()
keywords = []
for kw in preset_kws + custom_kws:
    if kw not in seen:
        seen.add(kw)
        keywords.append(kw)
```

### 커밋 및 배포

| 커밋 | 내용 |
|------|------|
| `31a7c3f` | feat: search.xlsx 우선순위 키워드 멀티셀렉트 추가 |

- `search.xlsx` 파일도 git에 포함하여 Streamlit Cloud에서 읽을 수 있도록 커밋
- `@st.cache_data` 적용으로 앱 재시작 없이 Excel 변경 시 자동 반영
- GitHub push → Streamlit Cloud 자동 배포 완료

*기록 추가일: 2026-06-29 (세션 6)*

---

## 2026-06-29 세션 7 — 사전규격정보서비스 검색 탭 추가

### 변경 목적

기존 입찰공고 검색에 더해, 나라장터 **사전규격정보서비스** 검색 기능 추가.
동일한 키워드·기간·금액 조건으로 입찰공고와 사전규격을 동시에 조회.

### API 정보

- **엔드포인트**: `http://apis.data.go.kr/1230000/PreSpecPublicInfoService/getPreSpecPublicInfoListServcPPSSrch`
- **파라미터**: 입찰공고와 동일 (`ServiceKey`, `type`, `numOfRows`, `pageNo`, `inqryDiv`, `inqryBgnDt`, `inqryEndDt`, `bidNtceNm`)
- **주요 응답 필드**:
  - `bfSpecRgstnNo` → 등록번호
  - `bfSpecRgstnNm` → 사전규격명
  - `ntceInsttNm` → 공고기관
  - `dminsttNm` → 수요기관
  - `presmptPrce` → 추정가격
  - `bfSpecRgstnDt` → 공고일시 (등록일시)
  - `opninRcptDdlnDt` → 의견접수마감
  - `bfSpecRegUrl` → 사전규격URL

### 주요 변경 내용

**`api_client.py`**:
- `PRESPEC_URL` 상수 추가
- `PRESPEC_FIELD_MAP` 필드 매핑 추가
- `fetch_prespec()` 함수 추가 (fetch_notices와 동일 구조)
  - `등록번호` 기준 중복 제거
  - 추정가격 필터 (min_amount > 0 일 때만 적용)
  - 사전규격명 기준 제외 키워드 필터

**`app.py`**:
- `fetch_prespec` import 추가
- `PRESPEC_LINK_BASE = "https://www.g2b.go.kr/link/PNPE028_01/single/"` 추가
- `show_prespec_table()` 함수 추가
  - 등록번호, 사전규격명, 의견마감일, 마감D-Day, 바로가기 링크 컬럼
  - 의견마감 기준 D-Day 계산 및 마감 지난 항목 자동 제외
  - 결과 내 검색, 정렬(의견마감/추정가격/등록일), CSV 다운로드
- 결과 영역 구조 개편:
  - 기존: 메트릭 + 탭(전체/마감임박/통계) 단일 구조
  - 변경: **최상위 탭 "📋 입찰공고" / "📑 사전규격"** 으로 분리
  - 각 탭 내 동일 구조: 메트릭 카드 + 서브탭(전체목록/마감임박/통계)
- 공고 조회 시 입찰공고 + 사전규격 동시 조회

### 커밋 및 배포

| 커밋 | 내용 |
|------|------|
| `556c4bc` | feat: 사전규격정보서비스 검색 탭 추가 |

- GitHub push → Streamlit Cloud 자동 배포 완료

*기록 추가일: 2026-06-29 (세션 7)*

---

## 2026-06-29 세션 8 — 사전규격 버그 수정 및 UI 개선

### 1. 사전규격 API 필드명 수정

**배경**: 세션 7에서 추가한 사전규격 탭이 실제 API 응답과 필드명이 달라 조회 오류 발생.

**변경 내용 (`api_client.py`)**:
- `PRESPEC_FIELD_MAP` 실제 응답 필드명으로 전면 수정
  - `bfSpecRgstnNo` → `bfSpecRgstNo` (등록번호)
  - `bfSpecRgstnNm` → `prdctClsfcNoNm` (사전규격명)
  - `ntceInsttNm` → `orderInsttNm` (공고기관)
  - `dminsttNm` → `rlDminsttNm` (수요기관)
  - `presmptPrce` → `asignBdgtAmt` (추정가격)
  - `bfSpecRgstnDt` → `rcptDt` (공고일시)
  - `opninRcptDdlnDt` → `opninRgstClseDt` (의견접수마감)
  - `bfSpecRegUrl` 제거 (사전규격 URL API 미제공)
  - `bsnsDivNm` 추가 (업무구분)
- PRESPEC_URL 엔드포인트 수정: `PreSpecPublicInfoService` → `HrcspSsstndrdInfoService/getPublicPrcureThngInfoServcPPSSrch`
- 키워드 필터를 `bidNtceNm` 파라미터 대신 클라이언트 사이드 `str.contains` 로 변경 (API가 키워드 파라미터 미지원)

### 2. 사전규격 마감일 필터 제거

- 의견접수 기간이 보통 5~7일이라 D-Day 필터 적용 시 대부분 필터링됨 → 마감일 기준 자동 제외 로직 제거
- "의견마감 임박(7일)" 서브탭은 유지 (건 있을 때만 표시)

### 3. 사전규격 바로가기 링크 개선

- **1차**: 공개 목록 페이지(`/PNPBID_01`) → 링크 문제
- **최종**: `specDocFileUrl1` ~ `specDocFileUrl5` 필드에서 첫 번째 유효 HTTP URL 사용 → 사양서 문서 직접 다운로드

```python
def _ps_url(row):
    for i in range(1, 6):
        url = str(row.get(f"specDocFileUrl{i}", "") or "")
        if url.startswith("http"):
            return url
    return ""
```

### 4. UI/UX 개선

| 항목 | 변경 전 | 변경 후 |
|------|---------|---------|
| 앱 제목 | "나라장터 공고 대시보드" | "상상우리 나라장터 조회" |
| API 키 위치 | 메인 화면 폼 내부 | 사이드바(☰) 이동 → 화면 여백 확보 |
| 기본 최소 추정가격 | 0원(전체) | 5,000만원 |
| 업무구분 필터 | 없음 | 사전규격 탭 내 multiselect 추가 |
| 사전규격 에러 안내 | 단순 에러 메시지 | 공공데이터포털 활용신청 단계별 안내 추가 |

### 커밋 이력

| 커밋 | 내용 |
|------|------|
| `86c5eef` | debug: import 오류 원인 확인용 try-except 추가 |
| `fe4ebb5` | fix: 사전규격 API 엔드포인트 및 필드명 수정 |
| `71a2114` | fix: 사전규격 필드명 및 키워드 필터링 방식 수정 |
| `068c9d2` | fix: 사전규격 마감일 필터 제거 (의견기간 5~7일로 짧아 전부 걸러짐) |
| `3549955` | fix: 사전규격 에러 표시, Python 호환성, 업무구분 필터 추가 |
| `cefee4c` | ui: 제목 변경, API키 사이드바 이동, 기본 최소가격 5천만원 |
| `22a9ea4` | fix: 입찰공고·사전규격 바로가기 링크 경로 수정 |
| `9230c5e` | fix: 사전규격 바로가기를 공개 목록 페이지로 변경 |
| `77997f5` | fix: 사전규격 바로가기를 specDocFileUrl1-5 직접 문서 링크로 변경 |

*기록 추가일: 2026-06-30 (세션 8)*

---

## 2026-06-30 세션 9 — search.xlsx 4컬럼 반영 및 동적 멀티셀렉트

### 변경 목적

기존 `search.xlsx`는 `1순위 / 2순위 / 3순위` 3개 컬럼이었으나, **대표님** 컬럼이 첫 번째 열로 추가되어 4컬럼 구조로 변경됨.  
기존 `app.py`는 컬럼을 인덱스(0,1,2)로 고정 읽어 3개만 로드하는 구조라 4컬럼을 제대로 반영하지 못함.  
→ 컬럼 수에 관계없이 Excel 헤더 이름을 그대로 레이블로 사용하는 **동적 구조**로 전환.

### search.xlsx 현재 구조

| 대표님 (24개) | 1순위 (31개) | 2순위 (16개) | 3순위 (11개) |
|-------------|-------------|-------------|-------------|
| 일자리, 퇴직, 은퇴, 이직, 전직, 구직, 설계, 경력, 장년, 중년, 시니어, 부머, 노인, 어르신, 스마트, 경로당, 재취업, 취업, 창업, 멘토링, 인턴십, 사회적, 디지털, 박람회 | AI, 튜터, 경로당, 늘봄, 디지털, 청년, 포용, 리터러시, 시니어, 장년, 중년, 일자리, 경력, 단절, 은퇴, 퇴직, 퇴사, 재기, 도전, 전직, 취업, 경력, 노하우, 상생, 매칭, 프로보노, 재능, 어르신, 새싹, 노인, 고령 | 혁신, 사회적, 공간, 희망, 힐링, 체인지, 임팩트, 캠프, 격차, 부트, 제작, 기부, 스페이스, 메이커, 소셜벤처, 취약 | 시티즌, 엘더리, 40대, 50대, 60대, 40플러스, 50플러스, 60플러스, 연장자, 실버, 에이징 |

### 변경 내용 (`app.py`)

**`load_keyword_presets()` 리턴 구조 변경**:
```python
# 변경 전: 3개 리스트 고정 반환
def load_keyword_presets():
    p1 = df.iloc[:, 0].dropna()...
    p2 = df.iloc[:, 1].dropna()...
    p3 = df.iloc[:, 2].dropna()...
    return p1, p2, p3

# 변경 후: (컬럼명, 키워드목록) 튜플 리스트 — 컬럼 수 동적
def load_keyword_presets():
    result = []
    for col in df.columns:
        vals = df[col].dropna().astype(str).str.strip().tolist()
        if vals:
            result.append((str(col), vals))
    return result
```

**UI 멀티셀렉트 동적 생성**:
```python
# 변경 전: 3개 하드코딩
col_p1, col_p2, col_p3 = st.columns(3)
sel1 = st.multiselect("🥇 1순위", options=p1_kws, ...)
sel2 = st.multiselect("🥈 2순위", options=p2_kws, ...)
sel3 = st.multiselect("🥉 3순위", options=p3_kws, ...)

# 변경 후: 컬럼 수에 맞게 동적 생성
grp_cols = st.columns(len(preset_groups))
sel_all = []
for i, (grp_name, options) in enumerate(preset_groups):
    with grp_cols[i]:
        sel = st.multiselect(grp_name, options=options, ..., key=f"ms_grp_{i}")
        sel_all.extend(sel)
```

**키워드 집계**:
```python
# 변경 전
preset_kws = sel1 + sel2 + sel3

# 변경 후
preset_kws = sel_all
```

*기록 추가일: 2026-06-30 (세션 9)*

---

## 2026-06-30 세션 10 — 대화 기록 최종 정리

### 진행 내용

1. `ipchal.md` 파일 내용 확인
2. `search.xlsx` 4컬럼 구조 확인 (대표님 컬럼 신규 추가 확인)
3. `app.py` 동적 멀티셀렉트 업데이트 (세션 9)
4. `ipchal.md` 세션 8 · 9 기록 추가 및 커밋 (`b7a8ccc`)
5. GitHub push → Streamlit Cloud 자동 배포 완료
6. 대화 내용 최종 반영 (세션 10)

### 커밋 이력

| 커밋 | 내용 |
|------|------|
| `b7a8ccc` | feat: search.xlsx 4컬럼 동적 반영 및 ipchal.md 세션 8·9 기록 추가 |

*기록 추가일: 2026-06-30 (세션 10)*
