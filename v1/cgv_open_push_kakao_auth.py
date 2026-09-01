import html
import os
import secrets
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from cgv_open_push_kakao import (
    KAKAO_TOKEN_URL,
    KakaoApiError,
    KakaoConfig,
    KakaoTokenStore,
)


AUTHORIZE_URL = "https://kauth.kakao.com/oauth/authorize"


def exchange_authorization_code(config, code):
    response = requests.post(
        KAKAO_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "client_id": config.rest_api_key,
            "client_secret": config.client_secret,
            "redirect_uri": config.redirect_uri,
            "code": code,
        },
        timeout=config.request_timeout_seconds,
    )
    try:
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as error:
        raise KakaoApiError("Kakao authorization-code exchange failed") from error


def main():
    config = KakaoConfig.from_env()
    redirect = urlparse(config.redirect_uri)
    if redirect.hostname not in {"localhost", "127.0.0.1"}:
        raise ValueError("The local OAuth helper requires a localhost redirect URI")

    port = redirect.port or (443 if redirect.scheme == "https" else 80)
    callback_path = redirect.path or "/"
    state = secrets.token_urlsafe(32)
    authorization_url = f"{AUTHORIZE_URL}?{urlencode({'response_type': 'code', 'client_id': config.rest_api_key, 'redirect_uri': config.redirect_uri, 'scope': 'talk_message', 'state': state})}"
    result = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            request_url = urlparse(self.path)
            query = parse_qs(request_url.query)
            status = 200
            message = "카카오 인증이 완료되었습니다. 이 창을 닫아도 됩니다."

            try:
                if request_url.path != callback_path:
                    raise ValueError("Unexpected callback path")
                if query.get("state", [""])[0] != state:
                    raise ValueError("OAuth state did not match")
                if "error" in query:
                    raise ValueError(query.get("error_description", query["error"])[0])
                code = query.get("code", [""])[0]
                if not code:
                    raise ValueError("Authorization code is missing")

                token_response = exchange_authorization_code(config, code)
                KakaoTokenStore(config).save_token_response(token_response)
                result["ok"] = True
            except Exception as error:
                status = 400
                result["error"] = error
                message = f"카카오 인증에 실패했습니다: {error}"

            body = (
                "<!doctype html><html lang='ko'><meta charset='utf-8'>"
                f"<title>카카오 인증</title><body><h1>{html.escape(message)}</h1></body></html>"
            ).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            return

    bind_host = os.environ.get("KAKAO_AUTH_BIND_HOST", "0.0.0.0")
    server = HTTPServer((bind_host, port), CallbackHandler)
    print("Open this URL to authorize Kakao self-message access:", flush=True)
    print(authorization_url, flush=True)
    print(f"Waiting for one callback on {config.redirect_uri}", flush=True)
    server.handle_request()
    server.server_close()

    if not result.get("ok"):
        raise result.get("error", RuntimeError("Kakao authorization did not complete"))
    print(f"Kakao token saved to {config.token_file}", flush=True)


if __name__ == "__main__":
    main()
