import os


CGV_API_URL = "https://cgv.co.kr/api/v1/booking/searchMovScnInfo"
CGV_COMPANY_CODE = "A420"
CGV_HEADERS = {
    "Accept": "application/json",
    "Accept-Language": "ko-KR",
    "Referer": "https://cgv.co.kr/cnm/movieBook/cinema",
}


def _positive_int(name, default):
    value = int(os.environ.get(name, str(default)))
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


def _non_negative_float(name, default):
    value = float(os.environ.get(name, str(default)))
    if value < 0:
        raise ValueError(f"{name} must be zero or greater")
    return value


CGV_LOOKAHEAD_DAYS = _positive_int("CGV_LOOKAHEAD_DAYS", 14)
CGV_POLL_INTERVAL_SECONDS = _positive_int("CGV_POLL_INTERVAL_SECONDS", 300)
CGV_REQUEST_INTERVAL_SECONDS = _non_negative_float("CGV_REQUEST_INTERVAL_SECONDS", 1)
CGV_RETRY_INITIAL_SECONDS = _positive_int("CGV_RETRY_INITIAL_SECONDS", 60)
CGV_RETRY_MAX_SECONDS = _positive_int("CGV_RETRY_MAX_SECONDS", 900)


# Site numbers were verified against the renewed CGV public theater list on 2026-09-03.
SCREEN_TARGETS = [
    {
        "name": "YONGSAN-IMAX",
        "site_no": "0013",
        "site_name": "용산아이파크몰",
        "keywords": ("IMAX",),
    },
    {
        "name": "WANGSIMNI-IMAX",
        "site_no": "0074",
        "site_name": "왕십리",
        "keywords": ("IMAX",),
    },
    {
        "name": "APGUJEONG-IMAX",
        "site_no": "0040",
        "site_name": "압구정",
        "keywords": ("IMAX",),
    },
]


def enabled_screen_targets():
    configured = os.environ.get("CGV_TARGET_NAMES", "").strip()
    if not configured:
        return SCREEN_TARGETS

    names = {name.strip().upper() for name in configured.split(",") if name.strip()}
    targets = [target for target in SCREEN_TARGETS if target["name"] in names]
    unknown = names - {target["name"] for target in SCREEN_TARGETS}
    if unknown:
        raise ValueError(f"Unknown CGV_TARGET_NAMES: {', '.join(sorted(unknown))}")
    if not targets:
        raise ValueError("CGV_TARGET_NAMES did not enable any targets")
    return targets
