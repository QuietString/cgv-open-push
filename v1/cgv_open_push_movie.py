import time

from cgv_open_push_function import (
    extract_playdays,
    extract_text_between_tag,
    get_request_to_cgv_api,
    save_log_error,
    save_log_info,
)
from diff_match_patch import diff_match_patch


def find_changes(previous, current, tag):
    dmp = diff_match_patch()
    changes = dmp.diff_main(previous, current)
    dmp.diff_cleanupSemantic(changes)
    added = ""
    deleted = ""

    for operation, value in changes:
        extracted = extract_text_between_tag(value, tag)
        if operation == 1:
            added += extracted or f"{value}, "
        elif operation == -1:
            deleted += extracted or f"{value}, "
    return added, deleted


def movie_main(url, cookies, headers, json_data, target_name, message_queue):
    previous = None
    retry_delay = 60

    while True:
        try:
            response = get_request_to_cgv_api(url, cookies, headers, json_data, target_name)
            location = extract_text_between_tag(response, "THEATER_NM")
            screen_type = extract_text_between_tag(response, "RATING_NM")
            movie = extract_text_between_tag(response, "MOVIE_GROUP_NM")
            save_log_info(
                f"{target_name} response : 위치 : {location}, 유형 : {screen_type}, 영화 : {movie}"
            )
            current = extract_playdays(response)

            if previous is not None and previous != current:
                added, deleted = find_changes(previous, current, "FORMAT_DATE")
                if added:
                    save_log_info(f"{target_name} added item : {added.encode()}")
                    message_queue.put([target_name, f"예매 오픈 알림 : {added}"])
                if deleted:
                    save_log_info(f"{target_name} deleted item : {deleted.encode()}")

            previous = current
            retry_delay = 60
            time.sleep(300)
        except Exception as error:
            save_log_error(f"{target_name} error : {error}")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 900)
