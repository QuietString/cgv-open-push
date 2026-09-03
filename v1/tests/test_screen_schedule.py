import json
import queue
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from cgv_open_push_global_variable import enabled_screen_targets

from cgv_open_push_screen import (
    add_schedules_to_snapshot,
    SchedulePoller,
    enqueue_added_schedules,
    matches_target,
)


FIXTURE = Path(__file__).parent / "fixtures" / "cgv_search_mov_scn_info.json"


def target(name, keyword):
    return {
        "name": name,
        "site_no": "0013",
        "site_name": "용산아이파크몰",
        "keywords": (keyword,),
    }


class ScreenScheduleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schedules = json.loads(FIXTURE.read_text(encoding="utf-8"))["data"]

    def test_current_response_fields_match_4dx_and_screenx_targets(self):
        self.assertTrue(matches_target(self.schedules[0], target("YONGSAN-4DX", "4DX")))
        self.assertTrue(
            matches_target(self.schedules[1], target("YONGSAN-SCREENX", "SCREENX"))
        )
        imax = dict(self.schedules[0], scnsNm="IMAX관", movkndDsplNm="IMAX LASER 2D")
        self.assertTrue(matches_target(imax, target("YONGSAN-IMAX", "IMAX")))

    def test_same_site_targets_share_one_request_per_date(self):
        targets = [target("YONGSAN-4DX", "4DX"), target("YONGSAN-SCREENX", "SCREENX")]
        calls = []
        sleeps = []
        clock = [0]

        def sleep(seconds):
            sleeps.append(seconds)
            clock[0] += seconds

        def fake_request(url, headers, params, target_name):
            calls.append((params, target_name))
            return [dict(schedule, scnYmd=params["scnYmd"]) for schedule in self.schedules]

        poller = SchedulePoller(
            "url",
            {},
            targets,
            queue.Queue(),
            lookahead_days=2,
            poll_interval_seconds=300,
            request_interval_seconds=0.25,
            retry_initial_seconds=60,
            retry_max_seconds=900,
            request_function=fake_request,
            sleep_function=sleep,
            clock=lambda: clock[0],
            today_function=lambda: date(2026, 9, 3),
        )
        poller.poll_once()

        self.assertEqual(2, len(calls))
        self.assertEqual(["20260903", "20260904"], [call[0]["scnYmd"] for call in calls])
        self.assertEqual([0.25], sleeps)
        self.assertEqual(2, len(poller.snapshots))
        for snapshot in poller.snapshots.values():
            self.assertEqual(1, len(snapshot["YONGSAN-4DX"]))
            self.assertEqual(1, len(snapshot["YONGSAN-SCREENX"]))

    @patch.dict("os.environ", {}, clear=True)
    def test_default_catalog_contains_only_requested_imax_theaters(self):
        targets = enabled_screen_targets()
        self.assertEqual(
            [("YONGSAN-IMAX", "0013"), ("WANGSIMNI-IMAX", "0074"), ("APGUJEONG-IMAX", "0040")],
            [(item["name"], item["site_no"]) for item in targets],
        )
        self.assertTrue(all(item["keywords"] == ("IMAX",) for item in targets))

    @patch.dict("os.environ", {"CGV_TARGET_NAMES": "APGUJEONG-IMAX,WANGSIMNI-IMAX"})
    def test_target_subset_uses_new_catalog(self):
        self.assertEqual(
            ["WANGSIMNI-IMAX", "APGUJEONG-IMAX"],
            [item["name"] for item in enabled_screen_targets()],
        )

    @patch.dict("os.environ", {"CGV_TARGET_NAMES": "YONGSAN-4DX"})
    def test_removed_target_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown CGV_TARGET_NAMES"):
            enabled_screen_targets()

    def test_one_added_schedule_queues_exactly_one_notification(self):
        targets = [target("YONGSAN-4DX", "4DX")]
        previous = {"YONGSAN-4DX": {}}
        current = {"YONGSAN-4DX": {}}
        add_schedules_to_snapshot(current, [self.schedules[0]], targets)
        message_queue = queue.Queue()

        count = enqueue_added_schedules(previous, current, targets, message_queue)

        self.assertEqual(1, count)
        self.assertEqual(1, message_queue.qsize())
        target_name, message = message_queue.get_nowait()
        self.assertEqual("YONGSAN-4DX", target_name)
        self.assertIn("2026-09-03 09:30 오디세이", message)

    def test_booking_controlled_schedule_is_added_only_after_opening(self):
        targets = [target("YONGSAN-4DX", "4DX")]
        controlled = dict(self.schedules[0], cntlYn="Y")
        previous = {"YONGSAN-4DX": {}}
        current = {"YONGSAN-4DX": {}}

        add_schedules_to_snapshot(previous, [controlled], targets)
        add_schedules_to_snapshot(current, [dict(controlled, cntlYn="N")], targets)

        message_queue = queue.Queue()
        count = enqueue_added_schedules(previous, current, targets, message_queue)
        self.assertEqual(1, count)
        self.assertEqual(1, message_queue.qsize())

    def test_first_scan_of_new_horizon_date_does_not_create_false_opening(self):
        targets = [target("YONGSAN-4DX", "4DX")]
        previous = {"YONGSAN-4DX": {}}
        current = {"YONGSAN-4DX": {}}
        next_horizon = dict(self.schedules[0], scnYmd="20260917")
        add_schedules_to_snapshot(current, [next_horizon], targets)
        message_queue = queue.Queue()

        count = enqueue_added_schedules(
            previous,
            current,
            targets,
            message_queue,
            previously_scanned_dates={"20260903", "20260904"},
        )

        self.assertEqual(0, count)
        self.assertTrue(message_queue.empty())


if __name__ == "__main__":
    unittest.main()
