import unittest
from unittest.mock import patch

import cgv_open_push_screen


class StopLoop(BaseException):
    pass


class WorkerRetryTests(unittest.TestCase):
    def test_request_failures_use_bounded_exponential_backoff(self):
        cases = (
            (
                cgv_open_push_screen,
                cgv_open_push_screen.screen_main,
                (
                    "url",
                    {},
                    [
                        {
                            "name": "TARGET",
                            "site_no": "0013",
                            "site_name": "용산아이파크몰",
                            "keywords": ("IMAX",),
                        }
                    ],
                    object(),
                    1,
                    300,
                    0,
                    60,
                    900,
                ),
            ),
        )
        for module, worker, args in cases:
            with self.subTest(module=module.__name__):
                delays = []

                def stop_after_three_retries(delay):
                    delays.append(delay)
                    if len(delays) == 3:
                        raise StopLoop

                with (
                    patch.object(
                        module,
                        "get_request_to_cgv_api",
                        side_effect=RuntimeError("injected request failure"),
                    ) as request_mock,
                    patch.object(module.time, "sleep", side_effect=stop_after_three_retries),
                    patch.object(module, "save_log_error"),
                ):
                    with self.assertRaises(StopLoop):
                        worker(*args)

                self.assertEqual([60, 120, 240], delays)
                self.assertEqual(3, request_mock.call_count)


if __name__ == "__main__":
    unittest.main()
