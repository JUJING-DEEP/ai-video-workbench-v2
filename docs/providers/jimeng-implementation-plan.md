# Jimeng Production Implementation Plan

## Purpose

This plan splits production Jimeng REST work into reviewable follow-up PRs. It
does not implement signing, HTTP calls, provider registration, or business API
changes in this PR.

## PR24: V4 Signing

### Goal

Add a deterministic Volcengine V4 signing boundary for Jimeng REST requests.

### Scope

- Add a signer interface that accepts the existing Jimeng request shape.
- Prefer the official Volcengine SDK signing path if it can be isolated.
- If a local signer is required, implement it in a small dedicated module.
- Add fake-credential tests for canonical request construction, signed header
  presence, and redaction behavior.
- Preserve the current mock provider and offline adapter tests.

### Validation

- Unit tests using fake AK/SK only.
- Provider contract tests.
- `ruff check .`
- No real Jimeng network calls.

### Rollback Strategy

- Revert the signer module and tests.
- Keep the existing Jimeng REST adapter skeleton unchanged.
- Keep mock provider as default.

## PR25: Submit Task

### Goal

Implement Jimeng submit task behavior behind explicit opt-in configuration.

### Scope

- Build `CVSync2AsyncSubmitTask` requests from local shot settings.
- Sign submit requests through PR24's signer.
- Send requests through a fake-testable transport.
- Parse `data.task_id`.
- Map provider submit errors into local provider errors.
- Add cost guard checks before any real submit path can run.
- Avoid automatic submit retry unless official idempotency behavior is proven.

### Validation

- Fake HTTP submit success tests.
- Fake HTTP submit error tests.
- Cost guard tests.
- Provider contract tests.
- `ruff check .`
- Optional manual smoke test only when real credentials are supplied locally.

### Rollback Strategy

- Disable the production Jimeng provider flag.
- Revert submit integration while keeping signer tests if still useful.
- Do not alter completed mock-provider jobs.

## PR26: Poll Task

### Goal

Implement Jimeng async result polling and status mapping.

### Scope

- Build `CVSync2AsyncGetResult` poll requests.
- Sign poll requests through the shared signer.
- Parse `in_queue`, `generating`, `processing`, `done`, `not_found`, and
  `expired`.
- Extract provider `request_id` when present.
- Map retryable and non-retryable provider codes.
- Keep poll tests based on fake responses.

### Validation

- Fake HTTP poll status tests.
- Error mapping tests.
- Timeout and retry policy tests.
- Provider contract tests.
- `ruff check .`

### Rollback Strategy

- Disable production Jimeng polling.
- Keep submitted remote jobs visible as failed or manually recoverable local
  jobs if submit was already enabled.
- Do not resubmit automatically during rollback.

## PR27: Download Result

### Goal

Download completed Jimeng `video_url` results into durable local project
storage.

### Scope

- Validate `video_url`.
- Stream downloads with size and timeout limits.
- Persist files before marking local jobs completed.
- Treat provider URLs as short-lived 1-hour transfer URLs.
- Redact provider URLs in logs.
- Handle expired, missing, empty, or invalid downloads.

### Validation

- Fake download success tests.
- Expired/missing URL tests.
- Empty body and invalid content tests.
- Local output binding tests.
- `ruff check .`

### Rollback Strategy

- Disable production Jimeng completion.
- Preserve already downloaded local files.
- Fail incomplete jobs with a clear download rollback message.

## PR28: Production Integration

### Goal

Expose the production Jimeng REST provider as an explicit opt-in provider while
keeping the mock provider as the default.

### Scope

- Add provider selection only when explicitly configured.
- Wire signing, submit, poll, download, retry, timeout, rate limiting, and cost
  guards together.
- Add local setup documentation with placeholder environment variables.
- Add manual real-account smoke test instructions that skip by default.
- Add observability fields and redaction checks.

### Validation

- Existing provider contract tests.
- Existing backend tests.
- `ruff check .`
- Manual opt-in smoke test with one controlled low-cost job, only after
  operator approval.
- No default CI real-provider execution.

### Rollback Strategy

- Turn off the production Jimeng provider flag.
- Fall back to the mock provider for default development and tests.
- Keep already completed local outputs.
- Stop new remote submits immediately.
- Preserve audit logs for submitted remote task ids and provider request ids.

## Cross-PR Rules

- Do not make real Jimeng the default provider.
- Do not require real credentials for CI.
- Do not commit credentials or real tokens.
- Do not integrate Dreamina CLI as a backend provider.
- Do not hide cost or quota use behind automatic retries.
- Keep each PR reviewable and independently reversible.
