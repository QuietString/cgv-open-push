import unittest
from unittest.mock import patch

from cgv_open_push_function import get_request_to_cgv_api


class FakeResponse:
    def __init__(self, content_type, payload):
        self.headers = {"Content-Type": content_type}
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class CgvRequestTests(unittest.TestCase):
    @patch("cgv_open_push_function.requests.post")
    def test_extracts_json_wrapped_xml_with_bounded_timeout(self, post):
        post.return_value = FakeResponse(
            "application/json; charset=utf-8",
            {"d": {"DATA": "<Schedule />"}},
        )

        result = get_request_to_cgv_api("url", {}, {}, {}, "TARGET")

        self.assertEqual("<Schedule />", result)
        self.assertEqual((5, 15), post.call_args.kwargs["timeout"])

    @patch("cgv_open_push_function.requests.post")
    def test_rejects_non_json_response(self, post):
        post.return_value = FakeResponse("text/html", {})

        with self.assertRaisesRegex(ValueError, "must be JSON"):
            get_request_to_cgv_api("url", {}, {}, {}, "TARGET")

    @patch("cgv_open_push_function.requests.post")
    def test_rejects_missing_embedded_xml(self, post):
        post.return_value = FakeResponse("application/json", {"d": {}})

        with self.assertRaisesRegex(ValueError, "missing d.DATA"):
            get_request_to_cgv_api("url", {}, {}, {}, "TARGET")


if __name__ == "__main__":
    unittest.main()
