import logging
import multiprocessing
import queue
import time
from logging.handlers import RotatingFileHandler

from cgv_open_push_function import save_log_error, save_log_info
from cgv_open_push_global_variable import (
    CGV_API_URL,
    CGV_HEADERS,
    CGV_LOOKAHEAD_DAYS,
    CGV_POLL_INTERVAL_SECONDS,
    CGV_REQUEST_INTERVAL_SECONDS,
    CGV_RETRY_INITIAL_SECONDS,
    CGV_RETRY_MAX_SECONDS,
    enabled_screen_targets,
)
from cgv_open_push_kakao import KakaoConfig, KakaoNotifier
from cgv_open_push_screen import screen_main
from cgv_open_push_status import run_status_server


def configure_logging():
    handlers = [
        RotatingFileHandler(
            "cgv-open-push.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
    ]
    logging.basicConfig(
        handlers=handlers,
        level=logging.INFO,
        format="%(asctime)s:%(levelname)s:%(message)s",
    )


def start_processes(message_queue):
    processes = []

    status_process = multiprocessing.Process(
        target=run_status_server,
        name="status-server",
    )
    processes.append(status_process)
    status_process.start()

    targets = enabled_screen_targets()
    schedule_process = multiprocessing.Process(
        target=screen_main,
        args=(
            CGV_API_URL,
            CGV_HEADERS,
            targets,
            message_queue,
            CGV_LOOKAHEAD_DAYS,
            CGV_POLL_INTERVAL_SECONDS,
            CGV_REQUEST_INTERVAL_SECONDS,
            CGV_RETRY_INITIAL_SECONDS,
            CGV_RETRY_MAX_SECONDS,
        ),
        name="cgv-schedule-worker",
    )
    processes.append(schedule_process)
    schedule_process.start()

    return processes


def stop_processes(processes):
    for process in processes:
        if process.is_alive():
            process.terminate()
    for process in processes:
        process.join(timeout=10)


def send_with_retry(notifier, target_name, message, attempts=3):
    for attempt in range(1, attempts + 1):
        try:
            notifier.send(target_name, message)
            save_log_info(f"Kakao message sent for {target_name}", True)
            return
        except Exception as error:
            save_log_error(
                f"Kakao message attempt {attempt}/{attempts} failed for {target_name}: {error}"
            )
            if attempt < attempts:
                time.sleep(5 * attempt)
    raise RuntimeError(f"Kakao message delivery failed for {target_name}")


def run_message_loop(message_queue, notifier, processes):
    send_with_retry(notifier, "LOG", "cgv-open-push server started...")
    while True:
        try:
            target_name, message = message_queue.get(timeout=1)
        except queue.Empty:
            failed = [process.name for process in processes if process.exitcode not in {None, 0}]
            if failed:
                raise RuntimeError(f"Child process stopped unexpectedly: {', '.join(failed)}")
            continue
        send_with_retry(notifier, target_name, message)


def main():
    configure_logging()
    notifier = KakaoNotifier(KakaoConfig.from_env())
    message_queue = multiprocessing.Queue()
    processes = start_processes(message_queue)

    try:
        run_message_loop(message_queue, notifier, processes)
    except KeyboardInterrupt:
        save_log_info("Shutdown requested", True)
    finally:
        stop_processes(processes)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
