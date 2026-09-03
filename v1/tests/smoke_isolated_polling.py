"""Bounded Linux-container smoke: real processes/queue, fake CGV and Kakao, no network needed."""

import json
import multiprocessing
import queue
import time
from collections import Counter
from urllib.request import urlopen

import cgv_open_push_main as main
import cgv_open_push_screen as screen


def run_smoke():
    if multiprocessing.get_start_method() != "fork":
        raise RuntimeError("Run this smoke inside the documented Linux Docker image")
    events = multiprocessing.Queue()
    requests_by_key = Counter()
    delivered = []

    def fake_request(url, headers, params, target_name):
        key = (params["siteNo"], params["scnYmd"])
        requests_by_key[key] += 1
        attempt = requests_by_key[key]
        events.put((key[0], attempt))
        screen.save_log_info(f"SMOKE request {target_name} attempt={attempt}", True)
        if key[0] == "0013" and attempt == 2:
            raise RuntimeError("injected one-date failure")
        if attempt == 1:
            return []
        return [{
            "siteNo": key[0], "scnYmd": key[1], "scnsNo": "001", "scnSseq": "1",
            "prodNo": "smoke-only", "scnsNm": "IMAX관", "movNm": "테스트 영화",
            "scnsrtTm": "1200", "cntlYn": "N",
        }]

    def fake_send(self, target_name, message):
        delivered.append(target_name)
        return {"result_code": 0}

    def bounded_message_loop(message_queue, notifier, processes):
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            assert len(processes) == 2 and all(process.is_alive() for process in processes)
            try:
                target_name, message = message_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            main.send_with_retry(notifier, target_name, message)
        assert Counter(delivered) == Counter({
            "YONGSAN-IMAX": 1, "WANGSIMNI-IMAX": 1, "APGUJEONG-IMAX": 1,
        }), delivered
        with urlopen("http://127.0.0.1:5000/healthz", timeout=2) as response:
            assert response.status == 200
        trace = []
        while True:
            try:
                trace.append(events.get(timeout=0.1))
            except queue.Empty:
                break
        assert trace[:7] == [
            ("0013", 1), ("0074", 1), ("0040", 1),
            ("0013", 2), ("0074", 2), ("0040", 2), ("0013", 3),
        ], trace
        print("ISOLATED_SMOKE_OK " + json.dumps({
            "alerts": delivered, "requests": trace, "python_processes": 3, "health": 200,
        }), flush=True)

    screen.get_request_to_cgv_api = fake_request
    main.KakaoNotifier.send = fake_send
    main.run_message_loop = bounded_message_loop
    main.CGV_LOOKAHEAD_DAYS = 1
    main.CGV_POLL_INTERVAL_SECONDS = 3
    main.CGV_REQUEST_INTERVAL_SECONDS = 0.05
    main.CGV_RETRY_INITIAL_SECONDS = 1
    main.CGV_RETRY_MAX_SECONDS = 4
    main.main()


if __name__ == "__main__":
    run_smoke()
