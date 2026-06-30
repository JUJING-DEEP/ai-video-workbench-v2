# Jimeng Production Integration Design

## Purpose

This document designs the production integration path for the Volcano Engine
Jimeng REST provider after the v1.1 adapter skeleton.

It is an integration readiness review, not an implementation PR. It does not
add signing code, real HTTP calls, provider registration changes, API changes,
database changes, or CI real-provider execution.

## Current Baseline

The current REST adapter skeleton covers the offline contract only:

- Endpoint: `https://visual.volcengineapi.com`
- Submit action: `CVSync2AsyncSubmitTask`
- Poll action: `CVSync2AsyncGetResult`
- Version: `2022-08-31`
- Region: `cn-north-1`
- Service: `cv`
- Default `req_key`: `jimeng_ti2v_v30_pro`
- Submit success returns `data.task_id`
- Poll success returns `data.status`
- Completed poll returns `data.video_url`
- `video_url` is valid for 1 hour

The mock provider remains the default deterministic provider. Dreamina CLI is
only a local manual debugging tool and is not part of the backend provider
architecture.

## Production Architecture

### Components

The production REST provider should be split into narrow layers:

| Layer | Responsibility |
| --- | --- |
| Provider facade | Implements the existing video provider contract and coordinates submit, poll, and download. |
| Request builder | Builds Jimeng submit and poll request shapes from local shot settings. |
| Signing adapter | Signs Volcano Engine REST requests with AK/SK without leaking secrets. |
| HTTP transport | Sends signed requests, applies timeouts, retries, and response size limits. |
| Response parser | Maps Jimeng response codes, statuses, task ids, and video URLs into local provider results. |
| Download manager | Downloads the short-lived `video_url` and stores a local durable copy. |
| Cost guard | Enforces local per-run and per-project budget limits before submit. |
| Rate limiter | Prevents avoidable 429s and honors account concurrency constraints. |

The production provider should remain opt-in until it has signing, error
mapping, cost controls, and manual real-account validation.

### Authentication

Jimeng REST uses Volcano Engine AK/SK signing, not bearer tokens and not the
Dreamina CLI OAuth session.

Required request identity:

- `access_key`: Volcano Engine AccessKeyID.
- `secret_key`: Volcano Engine AccessKeySecret.
- `region`: `cn-north-1`.
- `service`: `cv`.
- `version`: `2022-08-31`.

The provider must not send unsigned production requests. If signing is missing,
the provider should fail before any network call with a clear configuration
error.

### Credential Lifecycle

Credentials should be loaded at runtime from the environment or a local secret
store, never from committed files.

Recommended lifecycle:

1. Operator creates a least-privilege Volcano Engine credential for Visual
   Service / Jimeng access.
2. Operator stores AK/SK outside the repository.
3. Backend reads credentials at process startup or provider initialization.
4. Provider validates only presence and shape locally.
5. First signed API call validates whether the credential is accepted by the
   provider.
6. Operator rotates credentials on a regular schedule and immediately after any
   suspected exposure.
7. Old credentials are removed from local environment, deployment secrets, and
   provider settings.

The project should support credential replacement without database migration.
If credentials are stored in provider settings later, they should be encrypted
at rest and redacted in all read APIs.

### Signing Flow

The signing adapter should be isolated behind a small interface:

```text
sign(request, credentials) -> signed_request
```

Input:

- HTTP method.
- Endpoint host and path.
- Query parameters including `Action` and `Version`.
- JSON body bytes.
- Region.
- Service.
- Access key id.
- Secret key.

Output:

- The same request with signed headers and timestamp fields required by Volcano
  Engine.

Design rules:

- Prefer the official Volcano SDK signing implementation if it can be used
  without pulling real network behavior into tests.
- If a local signer is required, implement it as a dedicated module with fixed
  test vectors from official documentation or SDK behavior.
- Signing tests must use fake credentials.
- Never log canonical requests that include raw secrets.
- Never expose `secret_key` in exceptions, traces, or debug payloads.

### Volcengine V4 Signing Overview

Volcengine API requests use a V4-style AK/SK signing process. The production
provider should treat signing as a separate deterministic transformation from
an unsigned Jimeng request into a signed HTTP request.

At a high level, the signer must:

1. Normalize method, path, query parameters, selected headers, and hashed body.
2. Build the canonical request.
3. Build the string-to-sign using the request timestamp, region, service, and
   credential scope.
4. Derive the signing key from the secret key, date, region, and service.
5. Produce the signature.
6. Add the required signed headers before the HTTP transport sends the request.

Production implementation should verify these details against official
Volcengine SDK behavior or official signing documentation before any real
provider call is enabled. The adapter skeleton's `signing_required=True` marker
is only a boundary signal; it is not a signing implementation.

### Retry Policy

Retries should apply only after the request has been signed and sent by the HTTP
transport. Request building and local validation failures are not retryable.

Recommended retry behavior:

| Condition | Retry |
| --- | --- |
| Network timeout before response | Yes, bounded retry for idempotent poll/download; submit requires idempotency decision. |
| HTTP 429 / code `50429` QPS limit | Yes, exponential backoff with jitter. |
| HTTP 429 / code `50430` concurrency limit | Yes, slower backoff and local concurrency reduction. |
| HTTP 500 / code `50500` internal error | Yes, bounded retry. |
| HTTP 500 / code `50501` algorithm/RPC error | Yes, bounded retry. |
| code `50511`, `50516`, `50517`, `50519` post-check failures | Retry only when product semantics allow resubmission and budget guard approves. |
| Input validation or safety codes `50411`, `50412`, `50413`, `50518` | No. |
| `not_found` or `expired` poll status | No for the same task; resubmit only as an explicit new job. |

Submit retry is the risky case because duplicate submit calls can create
duplicate billable jobs if the provider accepted the first request but the
client timed out. Production submit should either avoid automatic submit retry
or require an idempotency strategy confirmed from official docs.

### Timeout Policy

Use separate timeouts for each lifecycle phase:

| Phase | Recommended timeout |
| --- | --- |
| Submit request | 10 seconds connect/read budget. |
| Poll request | 10 seconds connect/read budget. |
| Poll lifecycle | Existing local job timeout policy, with a provider-specific upper bound. |
| Download request | 60 seconds initial response timeout. |
| Download lifecycle | Bound by file size and the 1-hour `video_url` validity window. |

Timeout errors should preserve the phase name so users can distinguish submit,
poll, and download failures.

### Rate Limiting

The public research found default/free concurrency documented as 1 for video
generation and paid concurrency documented as 2 for several products, but no
stable public per-account QPS value.

Initial production limits should be conservative:

- Global Jimeng submit concurrency default: 1.
- Per-project Jimeng submit concurrency default: 1.
- Poll concurrency can be higher, but should still be bounded.
- Poll interval should start slow enough to avoid waste, for example 5 to 10
  seconds, then back off for long-running jobs.
- 429 responses should reduce local concurrency temporarily.

Rate limit values should be configurable but default-safe.

### Cost Control

Jimeng video generation is billed only when a video is successfully returned,
with public pricing tied to generated duration. The researched 3.0 Pro price is
`1 RMB / second`.

Production cost controls should include:

- Provider disabled by default unless explicitly enabled.
- Per-run maximum number of real submits.
- Per-project daily maximum number of real submits.
- Optional per-project budget cap expressed in estimated RMB.
- Duration validation before submit, based on `frames`.
- Clear warning when `frames=241` or other longer-duration settings are used.
- No automatic retry of submit without explicit policy because duplicate jobs
  may duplicate cost.

The provider should record estimated cost metadata for audit, but must not
require billing APIs for v1.1 readiness.

### Job Lifecycle

Local lifecycle should map Jimeng async task semantics into the existing
provider contract:

1. Build submit request from shot keyframe URL, prompt, `req_key`, frames, and
   aspect ratio.
2. Sign and send submit request.
3. Parse `data.task_id`.
4. Store the provider task id as the remote submit id.
5. Poll with `req_key` and `task_id`.
6. Map remote status:
   - `in_queue` -> local `processing`.
   - `generating` -> local `processing`.
   - `processing` -> local `processing`.
   - `done` with valid `video_url` -> download phase.
   - `done` without valid `video_url` -> provider error.
   - `not_found` -> provider error.
   - `expired` -> provider error.
7. Download and persist video.
8. Mark local job completed only after the durable local copy exists.

The local provider should not mark a job completed merely because Jimeng
returned `done`; completion requires successful download and local binding.

### Download Lifecycle

The `video_url` returned by poll is a short-lived provider URL valid for 1
hour. Treat it as a transfer URL, not as a durable asset.

Download rules:

- Validate scheme and host before download.
- Start download immediately after completed poll.
- Use streaming download with size limits.
- Persist to project-controlled storage before updating local output state.
- Verify non-empty content.
- Prefer content-type checks when the provider sends them.
- Do not expose the provider URL in public logs or user-facing export data.
- If download fails because the URL expired, surface a clear provider error and
  require resubmission instead of trying to reuse the URL.

### Error Mapping

Provider errors should be mapped into actionable local categories:

| Jimeng condition | Local category | User-facing behavior |
| --- | --- | --- |
| Missing AK/SK | configuration error | Ask operator to configure credentials. |
| Signing failure | configuration error | Report signing setup failure without secrets. |
| Input image pre-check `50411` | validation error | Ask user to change image. |
| Input text pre-check `50412` | validation error | Ask user to change prompt. |
| Sensitive/copyright text `50413` | policy error | Ask user to revise prompt. |
| Copyright image `50518` | policy error | Ask user to replace image. |
| QPS `50429` | rate-limit error | Retry/back off if budget allows. |
| Concurrency `50430` | rate-limit error | Back off and lower concurrency. |
| Internal `50500` / `50501` | transient provider error | Retry bounded times. |
| Poll `not_found` | remote task error | Fail current job; do not keep polling. |
| Poll `expired` | remote task error | Fail current job; require resubmit. |
| Missing/invalid `video_url` | provider contract error | Fail current job and capture request id. |
| Download timeout | download error | Retry only within URL validity window. |

Capture provider `request_id` when present. It is safe to log request ids, but
not signed headers, raw canonical requests, `video_url`, or credential values.

### Logging Strategy

Logging should help operators debug request lifecycle issues without exposing
credentials, signed request material, or short-lived provider URLs.

Recommended log fields:

- Local project id or job id.
- Provider name: `jimeng_rest`.
- Lifecycle phase: `submit`, `poll`, or `download`.
- Remote `task_id` only after successful submit.
- Provider `request_id` when present.
- Remote status such as `in_queue`, `generating`, or `done`.
- Local mapped status.
- Retry attempt number.
- Duration in milliseconds.
- Error category and sanitized provider code.

Fields that must be redacted or omitted:

- `secret_key`.
- Full Authorization or signature headers.
- Raw canonical request strings.
- Full `video_url`.
- Prompt or user media URLs when logs may leave the trusted boundary.
- Any environment variable value that contains credentials.

### Observability

Production readiness should include metrics that make provider health,
latency, and cost pressure visible without requiring access to raw logs.

Recommended metrics:

- Submit count by result: success, validation failure, provider failure,
  timeout, and rate limited.
- Poll count by remote status.
- Download count by result.
- Submit latency histogram.
- Poll latency histogram.
- Download latency histogram.
- End-to-end generation duration from submit to local file persistence.
- Retry count by phase and error code.
- Rate-limit events by provider code.
- Estimated generated seconds and estimated cost by project.
- Active Jimeng jobs and queued Jimeng jobs.

Recommended traces:

- One trace per local generation job.
- Spans for submit, each poll request, and download.
- Sanitized attributes only; never include secrets or signed headers.

### Failure Recovery

Recovery should be phase-specific:

- Submit validation failure: fail fast and ask the user to change input.
- Submit timeout before confirmed task id: do not blindly resubmit unless
  official idempotency behavior is confirmed.
- Submit provider 429: back off and keep the local job pending if policy allows.
- Poll timeout: retry within the local job timeout window.
- Poll `not_found`: fail the current job; do not keep polling the same task.
- Poll `expired`: fail the current job; require explicit resubmission.
- Completed poll with invalid `video_url`: fail as provider contract error.
- Download timeout: retry only while the 1-hour URL window is still credible.
- Download expired URL: fail the current job and require resubmission.

All recovery paths should preserve the local job's audit trail: last provider
code, last provider request id, phase, retry count, and sanitized message.

## Security Checklist

### AK/SK Storage

- Store AK/SK outside the repository.
- Do not put AK/SK in README examples, fixtures, tests, snapshots, or PR
  descriptions.
- Prefer deployment secret managers or local environment variables.
- If credentials are later stored in provider settings, encrypt them at rest.
- Redact secret values in all API responses and admin views.

### Secret Rotation

- Support replacing AK/SK without schema changes.
- Document a rotation runbook.
- Rotate immediately after any suspected log, shell history, or PR exposure.
- Keep old and new credentials separate during rollout.
- Remove retired credentials from local shells, deployment secrets, and CI
  variables.

### Logging Redaction

- Never log `secret_key`.
- Never log full signed headers.
- Never log Authorization-like headers.
- Never log raw canonical signing strings if they include sensitive material.
- Avoid logging `video_url`; if needed, log only the host and a redacted path.
- Redact provider settings by key name, including `access_key`, `secret_key`,
  `token`, `authorization`, `signature`, and `credential`.

### Credential Validation

- Validate presence and non-empty shape locally.
- Fail before network if signing is not implemented.
- Do not add a CI test that requires real credentials.
- Use fake AK/SK in unit tests.
- Use opt-in manual smoke tests only for real account validation.

### Least Privilege

- Use a dedicated Volcano Engine sub-account or access key for this provider.
- Grant only Visual Service / Jimeng permissions needed for submit and poll.
- Do not reuse personal admin AK/SK.
- Keep production and development credentials separate.
- Restrict who can read deployment secrets.

## Implementation Plan

### PR A: Signing Adapter

Goal: add an isolated Volcano signing boundary without sending requests.

Scope:

- Add a signing interface consumed by the existing Jimeng REST request object.
- Prefer wrapping official SDK signing if practical.
- Add fake-credential unit tests for signed header presence and redaction.
- Add documentation for signing limitations.

Out of scope:

- Real HTTP calls.
- Provider registration.
- Real account tests in CI.

Validation:

- Unit tests with fake credentials.
- `ruff check .`

### PR B: HTTP Transport

Goal: add a reusable, testable transport that can send signed Jimeng requests
behind explicit opt-in configuration.

Scope:

- Add timeout configuration.
- Add response parsing hooks.
- Add fake HTTP tests for status codes, JSON decode failures, and request ids.
- Keep real network calls disabled in CI.

Out of scope:

- Submit integration into business workflows.
- Real quota-consuming calls.

Validation:

- Fake transport tests.
- Provider contract tests.
- `ruff check .`

### PR C: Submit Integration

Goal: implement production submit flow behind an explicit provider setting.

Scope:

- Build request with `CVSync2AsyncSubmitTask`.
- Sign request.
- Send through transport.
- Parse and store `task_id`.
- Apply cost guard before submit.
- Avoid automatic submit retry unless idempotency is confirmed.

Out of scope:

- Download handling.
- Default provider replacement.

Validation:

- Fake HTTP submit success and failure tests.
- Cost guard tests.
- Manual opt-in spike only if credentials are supplied locally.

### PR D: Poll Integration

Goal: implement production poll flow and remote status mapping.

Scope:

- Build request with `CVSync2AsyncGetResult`.
- Sign request.
- Parse `in_queue`, `generating`, `processing`, `done`, `not_found`, and
  `expired`.
- Map provider errors and retryable errors.
- Capture request ids when present.

Out of scope:

- Download persistence.
- UI changes.

Validation:

- Fake HTTP poll tests.
- Error mapping tests.
- Provider contract tests.

### PR E: Download Integration

Goal: download completed Jimeng `video_url` into durable local project storage.

Scope:

- Validate `video_url`.
- Stream download with timeout and size limits.
- Persist local video before marking job completed.
- Handle expired URL failures clearly.
- Avoid logging provider URLs.

Out of scope:

- Public asset hosting.
- UI download changes.

Validation:

- Fake download tests.
- Expired/missing URL tests.
- Local storage binding tests.

### PR F: Provider Integration Gate

Goal: expose the production Jimeng REST provider as an explicit opt-in provider.

Scope:

- Add provider selection only when configured.
- Keep mock provider as the default.
- Add documentation for local opt-in setup.
- Add manual smoke-test instructions that are skipped by default.

Out of scope:

- Default CI real API tests.
- Dreamina CLI provider.
- UI feature changes unless already supported by existing provider settings.

Validation:

- Existing provider contract tests.
- Existing backend tests.
- Manual opt-in smoke test with a small controlled job, only when approved.

## v1.1 Risk Analysis

The following risks can block production Jimeng integration from entering v1.1:

- Official signing behavior cannot be verified against stable docs or SDK test
  vectors in time.
- Submit retry idempotency remains unclear, making safe retry and cost control
  insufficient.
- Real account QPS, concurrency, or quota limits differ from public docs and
  cause unreliable job behavior.
- Billing/cost guard requirements are not implemented before real submit is
  exposed.
- `video_url` download cannot be reliably completed and persisted inside the
  1-hour validity window.
- Error responses lack stable structure across failure classes, preventing clear
  user-facing remediation.
- Required provider settings would expose AK/SK through logs, APIs, config
  files, or admin surfaces.
- Manual real-account validation cannot be completed without excessive account
  setup, quota purchase, or OAuth-like manual steps.
- Official Jimeng REST docs change model keys, request fields, or response
  fields before implementation completes.
- Provider integration would require API, database, or UI changes larger than
  the v1.1 scope.

If any of these remain unresolved, v1.1 should keep Jimeng REST behind the
adapter skeleton and manual research docs, with the mock provider unchanged as
the default.
