<div align="center">

# CGV 예매 오픈 알리미

<p align="center">
  <img src="./img/logo.png" width="160"/>
</p>

by_0w0i0n0g0

image_by_<a href="https://kr.freepik.com/free-photo/3d-render-notification-bell-icon-new-email-message_34503708.htm#query=%EC%95%8C%EB%A6%BC%20%EC%95%84%EC%9D%B4%EC%BD%98&position=0&from_view=keyword&track=ais&uuid=0303dc60-e421-4177-8ab2-29b1326ae712">upklyak</a>

</div>

<br>
<br>

### 📢 안내

당분간 용산 CGV 특별관에 대한 예매 오픈 알리미만 운영될 예정입니다.

추가 건의나 문의사항은 [issues](https://github.com/0w0i0n0g0/cgv-open-push/issues)에 남겨주시면 남겨주시면 최대한 반영할 수 있도록 하겠습니다.

<br>

### 🎥 메가박스 예매 오픈 알리미도 확인해보세요!

[메가박스 예매 오픈 알리미](https://github.com/0w0i0n0g0/megabox-open-push)

<br>

### 🔎 현재 동작하고 있는 알리미는?

> (2026년 6월 기준)

- 용산아이파크몰 IMAX
- 용산아이파크몰 4DX
- 용산아이파크몰 SCREENX

<br>

### 📄 최근 업데이트 내역

**CGV 앱 리뉴얼에 맞추어 수정되었습니다!**

수정으로 인한 오류가 있을 수 있으니, 양해 부탁드립니다.

<br>
<br>

## 알림 받는 방법

현재 저장소의 `v1` 구현은 Discord 대신 카카오톡 공식 **나에게 보내기** API를 사용합니다.
카카오 디벨로퍼스 앱의 REST API 키·Client Secret과 최초 1회 OAuth 동의가 필요하며, 토큰은
Git에 포함되지 않는 Docker 데이터 볼륨에 저장합니다. 상세 설정과 검증 명령은
[빌드·테스트·실행 문서](Docs/Technical/BUILD_TEST_RUN.md)를 확인하세요.

CGV 리뉴얼 이후의 JSON 상영시간표를 조회하며, 기본 설정은 용산·여의도·센텀시티·서면·
영등포타임스퀘어·왕십리의 IMAX/4DX/SCREENX 9개 대상을 감시합니다. `CGV_TARGET_NAMES`로
필요한 대상만 선택할 수 있습니다.

<br>
<br>

## 사용 전 반드시 읽어주세요.

-  CGV 예매 오픈 알리미는 CGV의 특정 영화관, 특정 영화의 상영 일정을 주기적으로 갱신하여 변동사항을 확인하고, 변동사항이 발생하면 운영자의 카카오톡 `나와의 채팅방`으로 알림을 전송합니다.

- 이 서비스는 CGV와 어떠한 협의없이 제작되었으며, 인터넷을 통해 모두가 접근 가능하고 공개된 경로로만 정보를 취득합니다.

- 소스코드는 [**AGPL-3.0 license**](https://github.com/0w0i0n0g0/cgv-open-push/blob/main/LICENSE)로 배포되었습니다. 따라서 소스코드를 포함하거나 소스코드의 일부분을 사용, 수정, 2차 가공, 재배포할 때 해당 라이센스의 내용을 지켜주시기 바랍니다.

<br>
<br>

## Stack

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) ![Docker](https://img.shields.io/badge/docker-0db7ed.svg?style=for-the-badge&logo=docker&logoColor=white) ![KakaoTalk](https://img.shields.io/badge/KakaoTalk-FFCD00?style=for-the-badge&logo=kakaotalk&logoColor=000000)

<br>
<br>

## 개발 및 프로젝트 컨텍스트

- 에이전트·개발자용 컨텍스트 인덱스: [Docs/README.md](Docs/README.md)
- 현재 구현 상태: [Docs/Status/IMPLEMENTATION_STATUS.md](Docs/Status/IMPLEMENTATION_STATUS.md)
- 확인된 문제와 운영 위험: [Docs/Status/KNOWN_ISSUES.md](Docs/Status/KNOWN_ISSUES.md)
- 안전한 빌드·검증 절차: [Docs/Technical/BUILD_TEST_RUN.md](Docs/Technical/BUILD_TEST_RUN.md)
- 진행 중인 장기 작업: [Docs/Work/ACTIVE.md](Docs/Work/ACTIVE.md)

저장소에 추적된 `v1` 실행 코드는 현재 CGV JSON 일정 계약에 맞게 갱신되었습니다. 전체 기본
대상의 운영 검증 범위와 남은 위험은 위 구현 상태와 검증 기록을 확인해주세요.

<br>
<br>

## License

**AGPL-3.0 license**

Read full license [here](https://github.com/0w0i0n0g0/cgv-open-push/blob/main/LICENSE).
