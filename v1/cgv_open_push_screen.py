import time
from collections import defaultdict
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


def collect_schedule_snapshot(
    url,
    headers,
    targets,
    lookahead_days,
    request_interval_seconds,
    request_function=None,
    sleep_function=time.sleep,
    today=None,
):
    request_function = request_function or get_request_to_cgv_api
    snapshot = {target["name"]: {} for target in targets}
    targets_by_site = defaultdict(list)
    for target in targets:
        targets_by_site[target["site_no"]].append(target)

    jobs = [
        (site_no, scn_ymd, site_targets)
        for site_no, site_targets in targets_by_site.items()
        for scn_ymd in dates_to_scan(lookahead_days, today=today)
    ]
    for index, (site_no, scn_ymd, site_targets) in enumerate(jobs):
        params = {
            "coCd": CGV_COMPANY_CODE,
            "siteNo": site_no,
            "scnYmd": scn_ymd,
            "scnsNo": "",
            "scnSseq": "",
            "rtctlScopCd": "08",
            "custNo": "",
        }
        schedules = request_function(url, headers, params, f"{site_no}:{scn_ymd}")
        add_schedules_to_snapshot(snapshot, schedules, site_targets)
        if request_interval_seconds and index < len(jobs) - 1:
            sleep_function(request_interval_seconds)
    return snapshot


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
    previous = None
    previous_dates = None
    retry_delay = retry_initial_seconds

    while True:
        cycle_started = time.monotonic()
        try:
            current_day = datetime.now(KST).date()
            current_dates = set(dates_to_scan(lookahead_days, today=current_day))
            current = collect_schedule_snapshot(
                url,
                headers,
                targets,
                lookahead_days,
                request_interval_seconds,
                today=current_day,
            )
            for target in targets:
                save_log_info(
                    f"{target['name']} schedule count : {len(current[target['name']])}"
                )

            if previous is not None:
                enqueue_added_schedules(
                    previous,
                    current,
                    targets,
                    message_queue,
                    previously_scanned_dates=previous_dates,
                )
            previous = current
            previous_dates = current_dates
            retry_delay = retry_initial_seconds
            elapsed = time.monotonic() - cycle_started
            time.sleep(max(0, poll_interval_seconds - elapsed))
        except Exception as error:
            save_log_error(f"CGV schedule worker error : {error}")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, retry_max_seconds)
