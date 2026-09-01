import json
import tempfile
import unittest
from pathlib import Path

import requests

from cgv_open_push_kakao import (
    KAKAO_MEMO_URL,
    KAKAO_TOKEN_URL,
    KakaoApiError,
    KakaoConfig,
    KakaoNotifier,
    KakaoTokenStore,
)


class FakeResponse:
    def __init__(self, data, status_code=200):
        self.data = data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self.data


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


def make_config(token_file):
    return KakaoConfig(
        rest_api_key="rest-api-key",
        client_secret="client-secret",
        redirect_uri="http://localhost:8765/oauth/kakao/callback",
        token_file=token_file,
        message_link_url="https://github.com/QuietString/cgv-open-push",
    )


class KakaoTokenStoreTests(unittest.TestCase):
    def test_refresh_preserves_refresh_token_when_response_omits_it(self):
        with tempfile.TemporaryDirectory() as directory:
            token_file = Path(directory) / "token.json"
            token_file.write_text(
                json.dumps(
                    {
                        "access_token": "old-access",
                        "refresh_token": "keep-refresh",
                        "expires_at": 1,
                    }
                ),
                encoding="utf-8",
            )
            session = FakeSession([FakeResponse({"access_token": "new-access", "expires_in": 3600})])
            store = KakaoTokenStore(make_config(token_file), session, clock=lambda: 100)

            self.assertEqual("new-access", store.get_access_token())
            saved = json.loads(token_file.read_text(encoding="utf-8"))
            self.assertEqual("keep-refresh", saved["refresh_token"])
            self.assertEqual(3700, saved["expires_at"])
            self.assertEqual(KAKAO_TOKEN_URL, session.calls[0][0])

    def test_valid_access_token_does_not_refresh(self):
        with tempfile.TemporaryDirectory() as directory:
            token_file = Path(directory) / "token.json"
            token_file.write_text(
                json.dumps(
                    {
                        "access_token": "valid-access",
                        "refresh_token": "refresh",
                        "expires_at": 1000,
                    }
                ),
                encoding="utf-8",
            )
            session = FakeSession([])
            store = KakaoTokenStore(make_config(token_file), session, clock=lambda: 100)

            self.assertEqual("valid-access", store.get_access_token())
            self.assertEqual([], session.calls)


class KakaoNotifierTests(unittest.TestCase):
    def test_send_uses_text_template_and_bearer_token(self):
        with tempfile.TemporaryDirectory() as directory:
            config = make_config(Path(directory) / "token.json")
            session = FakeSession([FakeResponse({"result_code": 0})])
            token_store = type("StaticTokenStore", (), {"get_access_token": lambda self: "access"})()
            notifier = KakaoNotifier(config, token_store=token_store, http_session=session)

            result = notifier.send("YONGSAN-IMAX", "예매 오픈 알림")

            self.assertEqual({"result_code": 0}, result)
            url, kwargs = session.calls[0]
            self.assertEqual(KAKAO_MEMO_URL, url)
            self.assertEqual("Bearer access", kwargs["headers"]["Authorization"])
            template = json.loads(kwargs["data"]["template_object"])
            self.assertEqual("text", template["object_type"])
            self.assertIn("YONGSAN-IMAX", template["text"])
            self.assertLessEqual(len(template["text"]), 200)

    def test_nonzero_result_code_is_an_error(self):
        with tempfile.TemporaryDirectory() as directory:
            config = make_config(Path(directory) / "token.json")
            session = FakeSession([FakeResponse({"result_code": -1})])
            token_store = type("StaticTokenStore", (), {"get_access_token": lambda self: "access"})()
            notifier = KakaoNotifier(config, token_store=token_store, http_session=session)

            with self.assertRaises(KakaoApiError):
                notifier.send("TEST", "message")

    def test_http_error_reports_required_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            config = make_config(Path(directory) / "token.json")
            session = FakeSession(
                [
                    FakeResponse(
                        {
                            "code": -402,
                            "msg": "insufficient scopes.",
                            "required_scopes": ["talk_message"],
                        },
                        status_code=403,
                    )
                ]
            )
            token_store = type("StaticTokenStore", (), {"get_access_token": lambda self: "access"})()
            notifier = KakaoNotifier(config, token_store=token_store, http_session=session)

            with self.assertRaisesRegex(KakaoApiError, "talk_message"):
                notifier.send("TEST", "message")


if __name__ == "__main__":
    unittest.main()
