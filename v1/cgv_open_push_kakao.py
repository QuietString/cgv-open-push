import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests


KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_MEMO_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
DEFAULT_LINK_URL = "https://github.com/QuietString/cgv-open-push"


class KakaoConfigurationError(ValueError):
    pass


class KakaoApiError(RuntimeError):
    pass


def _required_env(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise KakaoConfigurationError(f"Required environment variable is missing: {name}")
    return value


@dataclass(frozen=True)
class KakaoConfig:
    rest_api_key: str
    client_secret: str
    redirect_uri: str
    token_file: Path
    message_link_url: str = DEFAULT_LINK_URL
    request_timeout_seconds: float = 15.0
    refresh_margin_seconds: int = 300

    @classmethod
    def from_env(cls):
        redirect_uri = _required_env("KAKAO_REDIRECT_URI")
        message_link_url = os.environ.get("KAKAO_MESSAGE_LINK_URL", DEFAULT_LINK_URL).strip()

        for name, url in {
            "KAKAO_REDIRECT_URI": redirect_uri,
            "KAKAO_MESSAGE_LINK_URL": message_link_url,
        }.items():
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise KakaoConfigurationError(f"{name} must be an absolute HTTP(S) URL")

        return cls(
            rest_api_key=_required_env("KAKAO_REST_API_KEY"),
            client_secret=_required_env("KAKAO_CLIENT_SECRET"),
            redirect_uri=redirect_uri,
            token_file=Path(os.environ.get("KAKAO_TOKEN_FILE", "/data/kakao-token.json")),
            message_link_url=message_link_url,
            request_timeout_seconds=float(os.environ.get("KAKAO_REQUEST_TIMEOUT_SECONDS", "15")),
            refresh_margin_seconds=int(os.environ.get("KAKAO_REFRESH_MARGIN_SECONDS", "300")),
        )


class KakaoTokenStore:
    def __init__(self, config, http_session=None, clock=None):
        self.config = config
        self.http = http_session or requests.Session()
        self.clock = clock or time.time

    def load(self):
        if not self.config.token_file.exists():
            raise KakaoConfigurationError(
                f"Kakao token file does not exist: {self.config.token_file}. "
                "Run cgv_open_push_kakao_auth.py first."
            )
        try:
            return json.loads(self.config.token_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise KakaoConfigurationError(
                f"Unable to read Kakao token file: {self.config.token_file}"
            ) from error

    def save_token_response(self, response_data, previous=None):
        now = int(self.clock())
        merged = dict(previous or {})
        merged.update(response_data)

        if not merged.get("access_token") or not merged.get("refresh_token"):
            raise KakaoApiError("Kakao token response did not include required tokens")

        if "expires_in" in response_data:
            merged["expires_at"] = now + int(response_data["expires_in"])
        if "refresh_token_expires_in" in response_data:
            merged["refresh_token_expires_at"] = now + int(
                response_data["refresh_token_expires_in"]
            )
        merged["updated_at"] = now

        token_file = self.config.token_file
        token_file.parent.mkdir(parents=True, exist_ok=True)
        temporary_file = token_file.with_name(f"{token_file.name}.tmp")
        temporary_file.write_text(
            json.dumps(merged, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        try:
            os.chmod(temporary_file, 0o600)
        except OSError:
            pass
        os.replace(temporary_file, token_file)
        return merged

    def refresh(self, current=None):
        current = current or self.load()
        refresh_token = current.get("refresh_token")
        if not refresh_token:
            raise KakaoConfigurationError("Kakao refresh token is missing")

        response = self.http.post(
            KAKAO_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "client_id": self.config.rest_api_key,
                "client_secret": self.config.client_secret,
                "refresh_token": refresh_token,
            },
            timeout=self.config.request_timeout_seconds,
        )
        try:
            response.raise_for_status()
            response_data = response.json()
        except (requests.RequestException, ValueError) as error:
            raise KakaoApiError("Kakao access-token refresh failed") from error
        return self.save_token_response(response_data, previous=current)

    def get_access_token(self):
        token_data = self.load()
        expires_at = int(token_data.get("expires_at", 0))
        if expires_at > int(self.clock()) + self.config.refresh_margin_seconds:
            access_token = token_data.get("access_token")
            if access_token:
                return access_token
        return self.refresh(token_data)["access_token"]


class KakaoNotifier:
    def __init__(self, config, token_store=None, http_session=None):
        self.config = config
        self.http = http_session or requests.Session()
        self.token_store = token_store or KakaoTokenStore(config, self.http)

    @staticmethod
    def format_alert(target_name, message):
        text = f"[{target_name}]\n{message}"
        if len(text) <= 200:
            return text
        return f"{text[:197]}..."

    def send(self, target_name, message):
        text = self.format_alert(target_name, message)
        link = {
            "web_url": self.config.message_link_url,
            "mobile_web_url": self.config.message_link_url,
        }
        template = {
            "object_type": "text",
            "text": text,
            "link": link,
            "button_title": "프로젝트 보기",
        }
        response = self.http.post(
            KAKAO_MEMO_URL,
            headers={"Authorization": f"Bearer {self.token_store.get_access_token()}"},
            data={"template_object": json.dumps(template, ensure_ascii=False)},
            timeout=self.config.request_timeout_seconds,
        )
        try:
            response.raise_for_status()
            response_data = response.json()
        except (requests.RequestException, ValueError) as error:
            try:
                error_data = response.json()
            except ValueError:
                error_data = {}
            details = [f"HTTP {response.status_code}"]
            for key in ("code", "msg", "required_scopes", "allowed_scopes"):
                if key in error_data:
                    details.append(f"{key}={error_data[key]}")
            raise KakaoApiError(
                f"Kakao self-message request failed ({', '.join(details)})"
            ) from error

        if response_data.get("result_code") != 0:
            raise KakaoApiError(
                f"Kakao self-message returned result_code={response_data.get('result_code')}"
            )
        return response_data
