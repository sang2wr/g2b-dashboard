"""나라장터 공고 URL 해석기 (서버 사이드 SSO base_uri 추출)"""
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote
import requests
import threading
import socket

PORT = 8502
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)


def resolve_notice_url(bid_no: str, bid_ord: str = "000") -> str:
    """SSO 첫 302 리다이렉트에서 base_uri(bodyDataKey 포함)를 추출해 반환.
    서버 사이드에서 호출 — 나라장터 쿠키가 없으므로 base_uri 경로로 분기됨."""
    src = (
        f"https://www.g2b.go.kr/link/PNPE027_01/single/"
        f"?bidPbancNo={bid_no}&bidPbancOrd={bid_ord}"
    )
    try:
        s = requests.Session()
        s.headers["User-Agent"] = UA
        r0 = s.get(src, timeout=10, allow_redirects=False)
        if r0.status_code == 302:
            sso_params = parse_qs(urlparse(r0.headers.get("Location", "")).query)
            base_uri_enc = sso_params.get("base_uri", [""])[0]
            if base_uri_enc:
                return unquote(base_uri_enc)
    except Exception:
        pass
    return src  # 폴백: 직접 SSO 링크


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            params = parse_qs(urlparse(self.path).query)
            bid_no  = params.get("no",  [""])[0]
            bid_ord = params.get("ord", ["000"])[0]

            if not bid_no:
                self.send_response(400); self.end_headers(); return

            src = (
                f"https://www.g2b.go.kr/link/PNPE027_01/single/"
                f"?bidPbancNo={bid_no}&bidPbancOrd={bid_ord}"
            )

            # SSO 첫 리다이렉트만 받아 base_uri(bodyDataKey 포함) 추출
            # key는 브라우저 세션으로 나라장터가 자체 발급 → "공고정보 없음" 오류 해결
            s = requests.Session()
            s.headers["User-Agent"] = UA
            r0 = s.get(src, timeout=10, allow_redirects=False)

            target = None
            if r0.status_code == 302:
                sso_loc = r0.headers.get("Location", "")
                sso_params = parse_qs(urlparse(sso_loc).query)
                base_uri_enc = sso_params.get("base_uri", [""])[0]
                if base_uri_enc:
                    target = unquote(base_uri_enc)  # bodyDataKey 포함, key 없음

            if not target:
                # 폴백: 전체 리다이렉트 따라가기
                r = s.get(src, timeout=12, allow_redirects=True)
                target = r.url

            self.send_response(302)
            self.send_header("Location", target)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

        except Exception:
            # 프록시가 g2b.go.kr에 연결 못할 때 직접 SSO 링크로 폴백
            params = parse_qs(urlparse(self.path).query)
            bid_no  = params.get("no",  [""])[0]
            bid_ord = params.get("ord", ["000"])[0]
            fallback = (
                f"https://www.g2b.go.kr/link/PNPE027_01/single/"
                f"?bidPbancNo={bid_no}&bidPbancOrd={bid_ord}"
            )
            self.send_response(302)
            self.send_header("Location", fallback)
            self.end_headers()

    def log_message(self, *args):
        pass


def _is_running():
    try:
        s = socket.create_connection(("localhost", PORT), timeout=0.5)
        s.close(); return True
    except OSError:
        return False


def ensure_running():
    if _is_running():
        return
    threading.Thread(
        target=lambda: HTTPServer(("localhost", PORT), Handler).serve_forever(),
        daemon=True,
    ).start()


PROXY_BASE = f"http://localhost:{PORT}"
