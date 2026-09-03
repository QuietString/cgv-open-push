# Architecture decision records

> Status: Active
>
> Owner: Project team
>
> Last verified: 2026-09-03
>
> Verified against: `Docs/Decisions/`

Three ADRs have been accepted; ADR-0003 updates the polling portions of ADR-0002.

Create an ADR from [`../Templates/ADR_TEMPLATE.md`](../Templates/ADR_TEMPLATE.md) when a decision:

- is expensive to reverse;
- affects polling, process supervision, state, delivery, or several components;
- establishes a project-wide configuration or testing convention;
- changes external compatibility, deployment, security, or delivery guarantees;
- chooses among meaningful alternatives future sessions may otherwise revisit.

Use sequential IDs such as `ADR-0001-notification-boundary.md`. Keep rejected and superseded records
when their rationale remains useful. Small local implementation choices do not need an ADR.

## Index

| ADR | State | Decision date | Summary |
|---|---|---|---|
| [`ADR-0001`](ADR-0001-kakao-self-message.md) | Accepted | 2026-09-01 | Use Kakao self-message as the notification transport |
| [`ADR-0002`](ADR-0002-current-cgv-json-contract.md) | Accepted | 2026-09-03 | Use the renewed CGV JSON booking contract and a browser-compatible client |
| [`ADR-0003`](ADR-0003-isolated-site-date-retries.md) | Accepted | 2026-09-03 | Limit targets to three IMAX theaters and isolate site/date retries and notifications |
