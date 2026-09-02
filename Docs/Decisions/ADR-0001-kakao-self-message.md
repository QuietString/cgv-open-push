# ADR-0001: Use Kakao self-message as the notification transport

- Status: Accepted
- Date: 2026-09-01
- Owners/approvers: Project owner
- Related tasks/context: [`../Work/Archive/TASK-0001-kakao-self-message.md`](../Work/Archive/TASK-0001-kakao-self-message.md), [`../Technical/ARCHITECTURE.md`](../Technical/ARCHITECTURE.md)
- Supersedes/superseded by: N/A

## Context

The tracked service sends alerts only through Discord. The project owner wants alerts in the owner's
KakaoTalk "나와의 채팅방" and has created Kakao Developers app `1564042` for this service.

## Decision drivers

- Use an official Kakao API rather than browser automation or an unofficial KakaoTalk client.
- Deliver only to the authenticated owner's own chat; public or friend broadcast is unnecessary.
- Support unattended Docker operation through token refresh without committing secrets.
- Keep CGV polling/change detection independent from message transport.

## Considered options

### Discord bot

- Benefits: already implemented and supports channel routing.
- Costs and risks: does not meet the owner's desired notification destination.

### KakaoTalk self-message REST API

- Benefits: official API, appropriate for one authenticated user's own chat, simple HTTP delivery.
- Costs and risks: requires interactive initial OAuth, access-token refresh, durable secret storage,
  and a registered product link.

### Kakao AlimTalk

- Benefits: designed for service-to-user informational messages at scale.
- Costs and risks: business/channel/dealer/template requirements are unnecessary for this personal use.

## Decision

Use Kakao's official self-message REST API as the tracked notification transport. Perform initial OAuth
with a separate helper, persist tokens in an ignored mounted file, automatically refresh access tokens,
and preserve a notification boundary so another transport can be added later without changing watchers.

## Consequences

### Positive

- Alerts arrive in the project owner's own KakaoTalk chat.
- No unofficial Kakao protocol or UI automation is required for runtime delivery.
- Transport authentication and delivery can be tested independently of CGV polling.

### Negative and risks

- The owner must approve Kakao consent once and again if the app connection or refresh token expires.
- Token storage becomes mutable runtime state that must survive container replacement.
- Basic text messages are limited to 200 characters and require a registered product link.

## Validation and revisit conditions

The implementation was accepted after nine focused tests passed, Kakao returned `result_code: 0` for
one owner-approved live message, and the owner confirmed its arrival on 2026-09-01. Revisit if delivery
expands beyond the owner's account, in which case AlimTalk or another service-to-user transport requires
a new decision.
