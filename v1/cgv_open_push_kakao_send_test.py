import os

from cgv_open_push_kakao import KakaoConfig, KakaoNotifier


def main():
    message = os.environ.get(
        "KAKAO_TEST_MESSAGE",
        "CGV IMAX 예매 오픈 알리미 테스트 메시지입니다.",
    )
    notifier = KakaoNotifier(KakaoConfig.from_env())
    notifier.send("TEST", message)
    print("Kakao self-message test succeeded.", flush=True)


if __name__ == "__main__":
    main()
