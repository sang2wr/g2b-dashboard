"""나라장터 입찰공고 / 사전규격 API 클라이언트"""
import requests
import pandas as pd
from datetime import datetime, timedelta

BASE_URL = "http://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServcPPSSrch"
PRESPEC_URL = "http://apis.data.go.kr/1230000/PreSpecPublicInfoService/getPreSpecPublicInfoListServcPPSSrch"

# 응답 필드 → 한글 컬럼명 매핑
FIELD_MAP = {
    "bidNtceNo":           "공고번호",
    "bidNtceNm":           "공고명",
    "ntceInsttNm":         "공고기관",
    "dminsttNm":           "수요기관",
    "presmptPrce":         "추정가격",
    "asignBdgtAmt":        "배정예산",
    "bidNtceDt":           "공고일시",
    "bidBeginDt":          "입찰시작",
    "bidClseDt":           "입찰마감",
    "bidNtceUrl":          "공고URL",
    "ntceInsttOfclNm":     "담당자",
    "ntceInsttOfclTelNo":  "담당자연락처",
    "srvceDivNm":          "용역구분",
    "bidMethdNm":          "입찰방법",
    "ntceKindNm":          "공고종류",
}

# 사전규격 응답 필드 → 한글 컬럼명 매핑
PRESPEC_FIELD_MAP = {
    "bfSpecRgstnNo":      "등록번호",
    "bfSpecRgstnNm":      "사전규격명",
    "ntceInsttNm":        "공고기관",
    "dminsttNm":          "수요기관",
    "presmptPrce":        "추정가격",
    "bfSpecRgstnDt":      "공고일시",
    "opninRcptDdlnDt":    "의견접수마감",
    "ntceInsttOfclNm":    "담당자",
    "ntceInsttOfclTelNo": "담당자연락처",
    "bfSpecRegUrl":       "사전규격URL",
}


def fetch_notices(
    api_key: str,
    keywords: list[str],
    min_amount: int = 10_000_000,
    days: int = 7,
    exclude_words: list[str] | None = None,
) -> pd.DataFrame:
    """
    나라장터 용역 입찰공고를 키워드별로 조회 후 필터링한 DataFrame 반환.
    keywords : OR 검색 — 각 키워드마다 API 호출 후 합산
    """
    end_dt   = datetime.now()
    start_dt = end_dt - timedelta(days=days)
    bgnDt    = start_dt.strftime("%Y%m%d%H%M")
    endDt    = end_dt.strftime("%Y%m%d%H%M")

    all_rows: list[dict] = []

    for kw in keywords:
        page = 1
        while True:
            params = {
                "ServiceKey":  api_key,
                "type":        "json",
                "numOfRows":   "100",
                "pageNo":      str(page),
                "inqryDiv":    "1",
                "inqryBgnDt":  bgnDt,
                "inqryEndDt":  endDt,
                "bidNtceNm":   kw,
            }
            try:
                resp = requests.get(BASE_URL, params=params, timeout=15)
                resp.raise_for_status()
                body = resp.json().get("response", {}).get("body", {})
                items = body.get("items") or []
                if not items:
                    break
                all_rows.extend(items)
                total = int(body.get("totalCount", 0))
                if page * 100 >= total:
                    break
                page += 1
            except Exception as e:
                print(f"[API 오류] 키워드={kw} 페이지={page}: {e}")
                break

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)

    # 컬럼 한글화
    df = df.rename(columns={k: v for k, v in FIELD_MAP.items() if k in df.columns})

    # 중복 제거 (공고번호 기준)
    if "공고번호" in df.columns:
        df = df.drop_duplicates(subset=["공고번호"])

    # 추정가격 숫자 변환 및 금액 필터
    if "추정가격" in df.columns:
        df["추정가격"] = pd.to_numeric(df["추정가격"], errors="coerce").fillna(0).astype(int)
        df = df[df["추정가격"] >= min_amount]

    # 제외 키워드 (공고명 기준)
    if exclude_words and "공고명" in df.columns:
        pattern = "|".join(exclude_words)
        df = df[~df["공고명"].str.contains(pattern, na=False)]

    # 공고일시 파싱 & 정렬
    if "공고일시" in df.columns:
        df["공고일시"] = pd.to_datetime(df["공고일시"], errors="coerce")
        df = df.sort_values("공고일시", ascending=False)

    return df.reset_index(drop=True)


def fetch_prespec(
    api_key: str,
    keywords: list[str],
    min_amount: int = 0,
    days: int = 7,
    exclude_words: list[str] | None = None,
) -> pd.DataFrame:
    """
    나라장터 사전규격을 키워드별로 조회 후 필터링한 DataFrame 반환.
    keywords : OR 검색 — 각 키워드마다 API 호출 후 합산
    """
    end_dt   = datetime.now()
    start_dt = end_dt - timedelta(days=days)
    bgnDt    = start_dt.strftime("%Y%m%d%H%M")
    endDt    = end_dt.strftime("%Y%m%d%H%M")

    all_rows: list[dict] = []

    for kw in keywords:
        page = 1
        while True:
            params = {
                "ServiceKey":  api_key,
                "type":        "json",
                "numOfRows":   "100",
                "pageNo":      str(page),
                "inqryDiv":    "1",
                "inqryBgnDt":  bgnDt,
                "inqryEndDt":  endDt,
                "bidNtceNm":   kw,
            }
            try:
                resp = requests.get(PRESPEC_URL, params=params, timeout=15)
                resp.raise_for_status()
                body = resp.json().get("response", {}).get("body", {})
                items = body.get("items") or []
                if not items:
                    break
                all_rows.extend(items)
                total = int(body.get("totalCount", 0))
                if page * 100 >= total:
                    break
                page += 1
            except Exception as e:
                print(f"[사전규격 API 오류] 키워드={kw} 페이지={page}: {e}")
                break

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)
    df = df.rename(columns={k: v for k, v in PRESPEC_FIELD_MAP.items() if k in df.columns})

    if "등록번호" in df.columns:
        df = df.drop_duplicates(subset=["등록번호"])

    if "추정가격" in df.columns:
        df["추정가격"] = pd.to_numeric(df["추정가격"], errors="coerce").fillna(0).astype(int)
        if min_amount > 0:
            df = df[df["추정가격"] >= min_amount]

    if exclude_words and "사전규격명" in df.columns:
        pattern = "|".join(exclude_words)
        df = df[~df["사전규격명"].str.contains(pattern, na=False)]

    if "공고일시" in df.columns:
        df["공고일시"] = pd.to_datetime(df["공고일시"], errors="coerce")
        df = df.sort_values("공고일시", ascending=False)

    return df.reset_index(drop=True)


# ── 샘플 데이터 (API 키 없을 때) ─────────────────────────────────
def sample_data() -> pd.DataFrame:
    today = datetime.now()
    rows = [
        {"공고번호": "20260625-001", "공고명": "스마트 경로당 운영 지원 용역",           "공고기관": "서울 종로구",    "수요기관": "어르신복지과",    "추정가격": 85_000_000,  "공고일시": today - timedelta(days=0), "입찰마감": (today + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"),  "공고URL": "https://www.g2b.go.kr", "담당자": "김○○", "담당자연락처": "", "용역구분": "일반용역"},
        {"공고번호": "20260624-002", "공고명": "AI 기반 어르신 돌봄 서비스 구축 용역",   "공고기관": "경기 성남시",    "수요기관": "복지정책과",      "추정가격": 240_000_000, "공고일시": today - timedelta(days=1), "입찰마감": (today + timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S"),  "공고URL": "https://www.g2b.go.kr", "담당자": "이○○", "담당자연락처": "", "용역구분": "일반용역"},
        {"공고번호": "20260624-003", "공고명": "2026 디지털 교육 박람회 운영 용역",       "공고기관": "교육부",          "수요기관": "디지털교육기획과", "추정가격": 320_000_000, "공고일시": today - timedelta(days=1), "입찰마감": (today + timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S"), "공고URL": "https://www.g2b.go.kr", "담당자": "박○○", "담당자연락처": "", "용역구분": "일반용역"},
        {"공고번호": "20260623-004", "공고명": "스마트 AI 교육 콘텐츠 개발 용역",         "공고기관": "한국교육학술정보원", "수요기관": "교육콘텐츠팀",  "추정가격": 180_000_000, "공고일시": today - timedelta(days=2), "입찰마감": (today + timedelta(days=8)).strftime("%Y-%m-%d %H:%M:%S"),  "공고URL": "https://www.g2b.go.kr", "담당자": "최○○", "담당자연락처": "", "용역구분": "일반용역"},
        {"공고번호": "20260623-005", "공고명": "경로당 ICT 환경 개선 사업 용역",           "공고기관": "부산광역시",      "수요기관": "어르신복지과",    "추정가격": 92_000_000,  "공고일시": today - timedelta(days=2), "입찰마감": (today + timedelta(days=6)).strftime("%Y-%m-%d %H:%M:%S"),  "공고URL": "https://www.g2b.go.kr", "담당자": "정○○", "담당자연락처": "", "용역구분": "일반용역"},
        {"공고번호": "20260622-006", "공고명": "스마트 복지관 통합 플랫폼 구축 용역",     "공고기관": "인천광역시",      "수요기관": "복지정보화팀",    "추정가격": 410_000_000, "공고일시": today - timedelta(days=3), "입찰마감": (today + timedelta(days=14)).strftime("%Y-%m-%d %H:%M:%S"), "공고URL": "https://www.g2b.go.kr", "담당자": "강○○", "담당자연락처": "", "용역구분": "일반용역"},
        {"공고번호": "20260622-007", "공고명": "AI 교육 박람회 홍보 및 기획 용역",         "공고기관": "과학기술정보통신부", "수요기관": "정보통신정책과", "추정가격": 65_000_000,  "공고일시": today - timedelta(days=3), "입찰마감": (today + timedelta(days=4)).strftime("%Y-%m-%d %H:%M:%S"),  "공고URL": "https://www.g2b.go.kr", "담당자": "윤○○", "담당자연락처": "", "용역구분": "일반용역"},
        {"공고번호": "20260621-008", "공고명": "스마트 경로당 프로그램 강사 파견 용역",   "공고기관": "대구 달서구",     "수요기관": "노인복지과",      "추정가격": 38_000_000,  "공고일시": today - timedelta(days=4), "입찰마감": (today + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),  "공고URL": "https://www.g2b.go.kr", "담당자": "임○○", "담당자연락처": "", "용역구분": "일반용역"},
    ]
    df = pd.DataFrame(rows)
    df["공고일시"] = pd.to_datetime(df["공고일시"])
    return df.sort_values("공고일시", ascending=False).reset_index(drop=True)
