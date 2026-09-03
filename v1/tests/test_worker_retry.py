import queue
import unittest
from datetime import date
from unittest.mock import patch

from cgv_open_push_global_variable import SCREEN_TARGETS
from cgv_open_push_screen import SchedulePoller


class FakeClock:
    def __init__(self):
        self.now = 0
        self.day = date(2026, 9, 3)
        self.sleeps = []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def schedule(params, number="1", **changes):
    return {
        "siteNo": params["siteNo"],
        "scnYmd": params["scnYmd"],
        "scnsNo": "001",
        "scnSseq": number,
        "prodNo": "movie-1",
        "scnsNm": "IMAX관",
        "movNm": "테스트 영화",
        "scnsrtTm": "1200",
        "cntlYn": "N",
        **changes,
    }


class WorkerRetryTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.messages = queue.Queue()
        self.calls = []
        self.failures = set()
        self.rows = {}
        self.extra_rows = []
        self.before_request = None
        self.log_patch = patch("cgv_open_push_screen.save_log_info")
        self.error_patch = patch("cgv_open_push_screen.save_log_error")
        self.log_patch.start()
        self.error_patch.start()
        self.addCleanup(self.log_patch.stop)
        self.addCleanup(self.error_patch.stop)

    def request(self, url, headers, params, target_name):
        key = (params["siteNo"], params["scnYmd"])
        self.calls.append((key, self.clock()))
        if self.before_request:
            self.before_request(key)
        if key in self.failures:
            raise RuntimeError("injected request failure")
        return [schedule(params, number) for number in self.rows.get(key, ["1"])] + self.extra_rows

    def make_poller(self, **overrides):
        options = dict(
            url="url", headers={}, targets=SCREEN_TARGETS, message_queue=self.messages,
            lookahead_days=1, poll_interval_seconds=300, request_interval_seconds=0,
            retry_initial_seconds=60, retry_max_seconds=900, request_function=self.request,
            clock=self.clock, sleep_function=self.clock.sleep, today_function=lambda: self.clock.day,
        )
        options.update(overrides)
        return SchedulePoller(**options)

    def test_only_failed_request_retries_and_other_sites_continue(self):
        failed = ("0013", "20260903")
        self.failures.add(failed)
        poller = self.make_poller(lookahead_days=2)
        self.assertEqual(6, poller.poll_once())
        self.assertEqual(5, len(poller.snapshots))
        self.assertEqual([failed], list(poller.retries))
        self.clock.now = 59
        self.assertEqual(0, poller.poll_once())
        self.clock.now = 60
        self.failures.clear()
        self.assertEqual(1, poller.poll_once())
        self.assertEqual(failed, self.calls[-1][0])
        self.assertEqual(7, len(self.calls))
        self.assertFalse(poller.retries)
        self.assertTrue(self.messages.empty())

    def test_each_theater_alert_is_queued_before_next_theater_request(self):
        poller = self.make_poller(lookahead_days=2)
        poller.poll_once()
        self.clock.now = 300
        for site in ("0013", "0074", "0040"):
            for day in ("20260903", "20260904"):
                self.rows[(site, day)] = ["1", "2"]

        def check_queue(key):
            if key == ("0074", "20260903"):
                self.assertEqual(1, self.messages.qsize())
            elif key == ("0040", "20260903"):
                self.assertEqual(2, self.messages.qsize())

        self.before_request = check_queue
        poller.poll_once()
        self.assertEqual(3, self.messages.qsize())
        self.assertEqual(
            ["YONGSAN-IMAX", "WANGSIMNI-IMAX", "APGUJEONG-IMAX"],
            [self.messages.get_nowait()[0] for _ in range(3)],
        )

    def test_failure_keeps_baseline_and_does_not_suppress_other_dates_or_theaters(self):
        poller = self.make_poller(lookahead_days=2)
        poller.poll_once()
        failed = ("0013", "20260903")
        original = poller.snapshots[failed]
        self.failures.add(failed)
        self.rows[("0013", "20260904")] = ["1", "2"]
        self.rows[("0074", "20260903")] = ["1", "2"]
        self.clock.now = 300
        self.assertEqual(6, poller.poll_once())
        self.assertIs(original, poller.snapshots[failed])
        self.assertEqual(
            ["YONGSAN-IMAX", "WANGSIMNI-IMAX"],
            [self.messages.get_nowait()[0] for _ in range(2)],
        )
        self.clock.now = 360
        self.failures.clear()
        self.rows[failed] = ["1", "2"]
        self.assertEqual(1, poller.poll_once())
        self.assertEqual("YONGSAN-IMAX", self.messages.get_nowait()[0])
        self.clock.now = 600
        poller.poll_once()
        self.assertTrue(self.messages.empty())

    def test_unchanged_recovery_does_not_realert_existing_schedules(self):
        poller = self.make_poller()
        poller.poll_once()
        self.failures.add(("0013", "20260903"))
        self.clock.now = 300
        poller.poll_once()
        self.clock.now = 360
        self.failures.clear()
        poller.poll_once()
        self.assertTrue(self.messages.empty())

    def test_first_success_after_initial_failure_establishes_only_that_date_baseline(self):
        failed = ("0013", "20260903")
        self.failures.add(failed)
        poller = self.make_poller(lookahead_days=2)
        poller.poll_once()
        self.clock.now = 300
        self.failures.clear()
        self.rows[("0013", "20260904")] = ["1", "2"]
        poller.poll_once()
        name, message = self.messages.get_nowait()
        self.assertEqual("YONGSAN-IMAX", name)
        self.assertIn("2026-09-04", message)
        self.assertNotIn("2026-09-03", message)
        self.assertTrue(self.messages.empty())

    def test_retry_backoff_is_per_request_capped_and_not_bypassed_by_normal_round(self):
        failed = ("0013", "20260903")
        self.failures.add(failed)
        poller = self.make_poller()
        poller.poll_once()
        for now, delay in ((60, 120), (180, 240), (420, 480), (900, 900), (1800, 900)):
            self.clock.now = now
            poller.poll_once()
            self.assertEqual(delay, poller.retries[failed].delay_seconds)
            self.assertEqual(now + delay, poller.retries[failed].next_attempt_at)
            if now == 180:
                self.clock.now = 300
                self.assertEqual(2, poller.poll_once())
                self.assertEqual(420, poller.retries[failed].next_attempt_at)
        self.failures.clear()
        self.clock.now = 2700
        poller.poll_once()
        self.assertNotIn(failed, poller.retries)
        self.failures.add(failed)
        self.clock.now = 3000
        poller.poll_once()
        self.assertEqual(60, poller.retries[failed].delay_seconds)

    def test_global_spacing_covers_failures_sites_and_retry_passes(self):
        failed = ("0013", "20260903")
        self.failures.add(failed)
        poller = self.make_poller(request_interval_seconds=1, retry_initial_seconds=1)
        poller.poll_once()
        self.assertEqual([0, 1, 2], [when for _, when in self.calls])
        self.failures.clear()
        self.assertEqual(1, poller.poll_once())
        self.assertEqual((failed, 3), self.calls[-1])

    def test_rollover_drops_expired_retries_and_new_date_is_baselined(self):
        failed = ("0013", "20260903")
        self.failures.add(failed)
        poller = self.make_poller(lookahead_days=2)
        poller.poll_once()
        self.clock.day = date(2026, 9, 4)
        self.clock.now = 60
        self.assertEqual(0, poller.poll_once())
        self.assertNotIn(failed, poller.retries)
        self.assertTrue(all(key[1] != "20260903" for key in poller.snapshots))
        self.clock.now = 300
        self.assertEqual(6, poller.poll_once())
        self.assertTrue(self.messages.empty())

    def test_successful_empty_response_remains_an_initialized_baseline(self):
        key = ("0013", "20260903")
        self.rows[key] = []
        poller = self.make_poller()
        poller.poll_once()
        self.clock.now = 300
        self.rows[key] = ["1"]
        poller.poll_once()
        self.assertEqual("YONGSAN-IMAX", self.messages.get_nowait()[0])

    def test_retry_timer_and_normal_round_do_not_generate_duplicate_requests(self):
        key = ("0013", "20260903")
        self.failures.add(key)
        poller = self.make_poller(retry_initial_seconds=300)
        poller.poll_once()
        self.clock.now = 300
        self.assertEqual(3, poller.poll_once())
        self.assertEqual(1, sum(call == (key, 300) for call in self.calls))

    def test_idle_wakeups_do_not_poll_healthy_requests(self):
        poller = self.make_poller()
        poller.poll_once()
        self.assertEqual(60, poller.seconds_until_next_pass())
        for now in (60, 120, 180, 240, 299):
            self.clock.now = now
            self.assertEqual(0, poller.poll_once())
        self.assertEqual(1, poller.seconds_until_next_pass())
        self.clock.now = 300
        self.assertEqual(3, poller.poll_once())

    def test_mixed_site_and_date_rows_are_filtered_without_failing_the_request(self):
        self.extra_rows = [
            schedule({"siteNo": "P001", "scnYmd": "20260903"}),
            schedule({"siteNo": "0040", "scnYmd": "20260904"}),
        ]
        poller = self.make_poller()
        self.assertEqual(3, poller.poll_once())
        self.assertFalse(poller.retries)
        self.assertEqual(1, len(poller.snapshots[("0040", "20260903")]["APGUJEONG-IMAX"]))
        self.clock.now = 300
        poller.poll_once()
        self.assertTrue(self.messages.empty())


if __name__ == "__main__":
    unittest.main()
