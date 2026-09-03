import unittest
from unittest.mock import patch

from cgv_open_push_function import (
    CGV_REQUEST_TIMEOUT_SECONDS,
    get_request_to_cgv_api,
)


class FakeResponse:
    def __init__(self, content_type, payload):
        self.headers = {"Content-Type": content_type}
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


def schedule():
    return {
        "siteNo": "0013",
        "scnYmd": "20260903",
        "scnsNo": "003",
        "scnSseq": "1",
        "prodNo": "20054744",
    }


class CgvRequestTests(unittest.TestCase):
    @patch("cgv_open_push_function.cgv_requests.get")
    def test_extracts_current_json_schedule_with_chrome_impersonation(self, get):
        get.return_value = FakeResponse(
            "application/json; charset=utf-8",
            {"statusCode": 0, "statusMessage": "조회 되었습니다.", "data": [schedule()]},
        )

        result = get_request_to_cgv_api(
            "https://cgv.co.kr/api/v1/booking/searchMovScnInfo",
            {"Accept": "application/json"},
            {"siteNo": "0013", "scnYmd": "20260903"},
            "0013:20260903",
        )

        self.assertEqual([schedule()], result)
        self.assertEqual("chrome", get.call_args.kwargs["impersonate"])
        self.assertEqual(CGV_REQUEST_TIMEOUT_SECONDS, get.call_args.kwargs["timeout"])

    @patch("cgv_open_push_function.cgv_requests.get")
    def test_rejects_non_json_response(self, get):
        get.return_value = FakeResponse("text/html", {})

        with self.assertRaisesRegex(ValueError, "must be JSON"):
            get_request_to_cgv_api("url", {}, {}, "TARGET")

    @patch("cgv_open_push_function.cgv_requests.get")
    def test_rejects_api_error_status(self, get):
        get.return_value = FakeResponse(
            "application/json",
            {"statusCode": -1, "statusMessage": "invalid", "data": []},
        )

        with self.assertRaisesRegex(ValueError, "statusCode=-1"):
            get_request_to_cgv_api("url", {}, {}, "TARGET")

    @patch("cgv_open_push_function.cgv_requests.get")
    def test_rejects_missing_schedule_identity(self, get):
        broken = schedule()
        del broken["scnSseq"]
        get.return_value = FakeResponse(
            "application/json",
            {"statusCode": 0, "statusMessage": "ok", "data": [broken]},
        )

        with self.assertRaisesRegex(ValueError, "missing scnSseq"):
            get_request_to_cgv_api("url", {}, {}, "TARGET")


if __name__ == "__main__":
    unittest.main()
