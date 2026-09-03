"""Movie-name watcher compatibility wrapper for the renewed JSON schedule source.

Movie-specific targets are currently not configured. A future target can use the same target shape as
screen targets with a movie title in ``keywords`` and call ``movie_main`` with the current worker
arguments.
"""

from cgv_open_push_screen import screen_main


def movie_main(
    url,
    headers,
    target,
    message_queue,
    lookahead_days,
    poll_interval_seconds,
    request_interval_seconds,
    retry_initial_seconds,
    retry_max_seconds,
):
    return screen_main(
        url,
        headers,
        [target],
        message_queue,
        lookahead_days,
        poll_interval_seconds,
        request_interval_seconds,
        retry_initial_seconds,
        retry_max_seconds,
    )
