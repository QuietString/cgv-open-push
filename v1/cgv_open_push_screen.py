import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from cgv_open_push_function import (
    get_request_to_cgv_api,
    save_log_error,
    save_log_info,
)
from cgv_open_push_global_variable import CGV_COMPANY_CODE


KST = timezone(timedelta(hours=9))
SCREEN_MATCH_FIELDS = (
    "scnsNm",
    "expoScnsNm",
    "movkndDsplNm",
    "movkndDsplEnm",
    "expoProdNm",
    "movNm",
)


def dates_to_scan(lookahead_days, today=None):
    first_day = today or datetime.now(KST).date()
    return [
        (first_day + timedelta(days=offset)).strftime("%Y%m%d")
        for offset in range(lookahead_days)
    ]


def schedule_key(schedule):
    return tuple(
        str(schedule[field])
        for field in ("siteNo", "scnYmd", "scnsNo", "scnSseq", "prodNo")
    )


def matches_target(schedule, target):
    searchable = " ".join(str(schedule.get(field, "")) for field in SCREEN_MATCH_FIELDS).upper()
    return any(keyword.upper() in searchable for keyword in target["keywords"])


def add_schedules_to_snapshot(snapshot, schedules, targets):
    for schedule in schedules:
        if schedule.get("cntlYn") == "Y":
            continue
        for target in targets:
            if schedule.get("siteNo") == target["site_no"] and matches_target(schedule, target):
                snapshot[target["name"]][schedule_key(schedule)] = schedule


def schedule_request_params(site_no, scn_ymd):
    return {
        "coCd": CGV_COMPANY_CODE,
        "siteNo": site_no,
        "scnYmd": scn_ymd,
        "scnsNo": "",
        "scnSseq": "",
        "rtctlScopCd": "08",
        "custNo": "",
    }


def describe_schedule(schedule):
    raw_date = str(schedule.get("scnYmd", ""))
    date_text = (
        f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
        if len(raw_date) == 8
        else raw_date
    )
    raw_time = str(schedule.get("scnsrtTm", ""))
    time_text = f"{raw_time[:2]}:{raw_time[2:]}" if len(raw_time) == 4 else raw_time
    movie = schedule.get("movNm") or schedule.get("expoProdNm") or "영화명 미상"
    screen = schedule.get("expoScnsNm") or schedule.get("scnsNm") or "상영관 미상"
    return f"{date_text} {time_text} {movie} ({screen})"


def enqueue_added_schedules(
    previous,
    current,
    targets,
    message_queue,
    previously_scanned_dates=None,
):
    notification_count = 0
    for target in targets:
        target_name = target["name"]
        added_keys = current[target_name].keys() - previous[target_name].keys()
        if previously_scanned_dates is not None:
            added_keys = {
                key for key in added_keys if key[1] in previously_scanned_dates
            }
        if not added_keys:
            continue

        added = sorted(
            (current[target_name][key] for key in added_keys),
            key=lambda schedule: (
                str(schedule.get("scnYmd", "")),
                str(schedule.get("scnsrtTm", "")),
                str(schedule.get("prodNo", "")),
            ),
        )
        descriptions = [describe_schedule(schedule) for schedule in added[:3]]
        suffix = f" 외 {len(added) - 3}개" if len(added) > 3 else ""
        message_queue.put([target_name, f"예매 오픈: {'; '.join(descriptions)}{suffix}"])
        notification_count += 1
    return notification_count


@dataclass(frozen=True)
class RequestRetry:
    next_attempt_at: float
    delay_seconds: float


class SchedulePoller:
    """One sequential worker with independent site/date baselines and retry deadlines."""

    def __init__(
        self,
        url,
        headers,
        targets,
        message_queue,
        lookahead_days,
        poll_interval_seconds,
        request_interval_seconds,
        retry_initial_seconds,
        retry_max_seconds,
        *,
        request_function=None,
        clock=None,
        sleep_function=None,
        today_function=None,
    ):
        self.url = url
        self.headers = headers
        self.targets_by_site = defaultdict(list)
        for target in targets:
            self.targets_by_site[target["site_no"]].append(target)
        self.message_queue = message_queue
        self.lookahead_days = lookahead_days
        self.poll_interval_seconds = poll_interval_seconds
        self.request_interval_seconds = request_interval_seconds
        self.retry_initial_seconds = retry_initial_seconds
        self.retry_max_seconds = retry_max_seconds
        self.request = request_function or get_request_to_cgv_api
        self.clock = clock or time.monotonic
        self.sleep = sleep_function or time.sleep
        self.today = today_function or (lambda: datetime.now(KST).date())
        self.snapshots = {}
        self.retries = {}
        self.next_poll_at = self.clock()
        self.next_request_at = self.next_poll_at

    def poll_once(self):
        """Run a normal round or only due retries; flush alerts after each theater."""
        cycle_started = self.clock()
        dates = dates_to_scan(self.lookahead_days, today=self.today())
        active_jobs = {(site, day) for site in self.targets_by_site for day in dates}
        self.snapshots = {key: value for key, value in self.snapshots.items() if key in active_jobs}
        self.retries = {key: value for key, value in self.retries.items() if key in active_jobs}
        normal_round = cycle_started >= self.next_poll_at
        if normal_round:
            self.next_poll_at = cycle_started + self.poll_interval_seconds

        attempts = 0
        for site_no, targets in self.targets_by_site.items():
            due = []
            for day in dates:
                key = (site_no, day)
                retry = self.retries.get(key)
                if (retry and retry.next_attempt_at <= cycle_started) or (
                    normal_round and retry is None
                ):
                    due.append(key)
            if not due:
                continue

            previous = {target["name"]: {} for target in targets}
            current = {target["name"]: {} for target in targets}
            initialized_dates = set()
            successful = {}
            for key in due:
                delay = self.next_request_at - self.clock()
                if delay > 0:
                    self.sleep(delay)
                attempts += 1
                try:
                    schedules = self.request(
                        self.url, self.headers, schedule_request_params(*key), f"{key[0]}:{key[1]}"
                    )
                    # CGV can include a co-located CINE de CHEF site in the same response.
                    schedules = [
                        schedule for schedule in schedules
                        if str(schedule["siteNo"]) == key[0] and str(schedule["scnYmd"]) == key[1]
                    ]
                    snapshot = {target["name"]: {} for target in targets}
                    add_schedules_to_snapshot(snapshot, schedules, targets)
                except Exception as error:
                    last_retry = self.retries.get(key)
                    retry_delay = min(
                        last_retry.delay_seconds * 2 if last_retry else self.retry_initial_seconds,
                        self.retry_max_seconds,
                    )
                    self.retries[key] = RequestRetry(self.clock() + retry_delay, retry_delay)
                    save_log_error(
                        f"CGV request failed {key[0]}:{key[1]}; retry in {retry_delay}s: {error}"
                    )
                    continue
                finally:
                    # The spacing limit also covers failed requests, theaters, and retry-only passes.
                    self.next_request_at = self.clock() + self.request_interval_seconds

                successful[key] = snapshot
                if key in self.snapshots:
                    initialized_dates.add(key[1])
                    for target in targets:
                        name = target["name"]
                        previous[name].update(self.snapshots[key][name])
                for target in targets:
                    name = target["name"]
                    current[name].update(snapshot[name])

            # Failed dates never enter this comparison or replace their last successful baseline.
            enqueue_added_schedules(
                previous, current, targets, self.message_queue,
                previously_scanned_dates=initialized_dates,
            )
            for key, snapshot in successful.items():
                self.snapshots[key] = snapshot
                self.retries.pop(key, None)
            for target in targets:
                count = sum(
                    len(snapshot[target["name"]])
                    for key, snapshot in self.snapshots.items() if key[0] == site_no
                )
                save_log_info(
                    f"{target['name']} schedule count : {count}; "
                    f"refreshed dates : {len(successful)}; failed dates : {len(due) - len(successful)}"
                )
        return attempts

    def seconds_until_next_pass(self):
        deadlines = [self.next_poll_at]
        deadlines.extend(retry.next_attempt_at for retry in self.retries.values())
        # Revisit the KST horizon regularly so expired-date retries and snapshots are discarded.
        return min(60, max(0, min(deadlines) - self.clock()))

    def run(self):
        while True:
            self.poll_once()
            self.sleep(self.seconds_until_next_pass())


def screen_main(
    url,
    headers,
    targets,
    message_queue,
    lookahead_days,
    poll_interval_seconds,
    request_interval_seconds,
    retry_initial_seconds,
    retry_max_seconds,
):
    SchedulePoller(
        url, headers, targets, message_queue, lookahead_days, poll_interval_seconds,
        request_interval_seconds, retry_initial_seconds, retry_max_seconds,
    ).run()
