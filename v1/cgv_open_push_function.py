import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from curl_cffi import requests as cgv_requests


CGV_REQUEST_TIMEOUT_SECONDS = 20
REQUIRED_SCHEDULE_FIELDS = (
    "siteNo",
    "scnYmd",
    "scnsNo",
    "scnSseq",
    "prodNo",
)


def save_log_info(log, is_log_file=False):
    if is_log_file:
        logging.info(log)
    print(f"[{datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')}] {log}", flush=True)


def save_log_error(log, is_log_file=True):
    if is_log_file:
        logging.error(log)
    print(f"[{datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')}] {log}", flush=True)


def calculate_response_delay(response):
    response_time = parsedate_to_datetime(response.headers["Date"])
    if response_time.tzinfo is None:
        response_time = response_time.replace(tzinfo=timezone.utc)
    return abs(datetime.now(timezone.utc) - response_time)


def get_request_to_cgv_api(url, headers, params, target_name, http_client=None):
    client = http_client or cgv_requests
    response = client.get(
        url=url,
        headers=headers,
        params=params,
        impersonate="chrome",
        timeout=CGV_REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "").lower()
    if "json" not in content_type:
        raise ValueError(
            f"{target_name} CGV response must be JSON, got {content_type or 'unknown'}"
        )
    if response.headers.get("Date"):
        save_log_info(
            f"{target_name} response delay : {calculate_response_delay(response)}",
            True,
        )

    try:
        payload = response.json()
    except ValueError as error:
        raise ValueError(f"{target_name} CGV response contains invalid JSON") from error

    if not isinstance(payload, dict):
        raise ValueError(f"{target_name} CGV response root must be an object")
    if payload.get("statusCode") != 0:
        raise ValueError(
            f"{target_name} CGV API error: statusCode={payload.get('statusCode')}, "
            f"statusMessage={payload.get('statusMessage')!r}"
        )

    schedules = payload.get("data")
    if not isinstance(schedules, list):
        raise ValueError(f"{target_name} CGV response data must be a list")
    for index, schedule in enumerate(schedules):
        if not isinstance(schedule, dict):
            raise ValueError(f"{target_name} CGV schedule at index {index} must be an object")
        missing = [field for field in REQUIRED_SCHEDULE_FIELDS if schedule.get(field) is None]
        if missing:
            raise ValueError(
                f"{target_name} CGV schedule at index {index} is missing "
                f"{', '.join(missing)}"
            )
    return schedules
