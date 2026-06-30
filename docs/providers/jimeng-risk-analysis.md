# Jimeng Production Risk Analysis

## Purpose

This document identifies risks that could block or delay production Jimeng REST
integration for v1.1. It is documentation only and does not change runtime
behavior.

## Technical Risks

### V4 Signing Mismatch

Risk: a local signer may differ from Volcengine's expected canonical request,
header selection, timestamp, or credential scope behavior.

Impact: all real submit and poll requests fail authentication.

Mitigation:

- Prefer official SDK signing when possible.
- Add fixed signing tests using official examples or SDK-generated output.
- Keep signing isolated from business logic.

Rollback:

- Disable production Jimeng provider.
- Keep adapter skeleton and mock provider unchanged.

### Submit Idempotency Unknown

Risk: automatic submit retry after timeout may create duplicate billable remote
jobs if the first submit succeeded but the response was lost.

Impact: unexpected cost and duplicate outputs.

Mitigation:

- Do not automatically retry submit until official idempotency behavior is
  confirmed.
- Record phase-specific timeout errors.
- Require explicit user/operator resubmission.

Rollback:

- Disable submit retries.
- Fail uncertain jobs with a clear manual recovery message.

### Download Window Too Short

Risk: `video_url` is valid for only 1 hour, and local download may be delayed by
worker backlog, network failures, or process restarts.

Impact: completed remote jobs cannot be persisted locally.

Mitigation:

- Start download immediately after completed poll.
- Bound queue time for download work.
- Retry downloads only inside the validity window.
- Persist local files before marking jobs completed.

Rollback:

- Fail the local job as download expired.
- Require explicit resubmission rather than reusing the expired URL.

## Operational Risks

### Credential Exposure

Risk: AK/SK, signed headers, or provider URLs appear in logs, traces, test
output, screenshots, or PR descriptions.

Impact: account compromise, unauthorized spending, and incident response work.

Mitigation:

- Centralize redaction.
- Add tests for redacted provider settings.
- Review logs in staging before production rollout.
- Keep real credentials out of CI.

Rollback:

- Rotate exposed keys immediately.
- Disable provider while investigating.
- Remove leaked values from deployment and local environments.

### Insufficient Monitoring

Risk: production failures are only visible as generic local job failures.

Impact: slow diagnosis and poor user recovery guidance.

Mitigation:

- Track submit, poll, download, retry, timeout, and rate-limit metrics.
- Capture provider request ids.
- Keep phase-specific error categories.

Rollback:

- Disable real provider until observability gaps are closed.

## Cost Risks

### Duplicate or Excessive Submits

Risk: retries, batch operations, or repeated user actions submit more real jobs
than intended.

Impact: unexpected billing.

Mitigation:

- Provider disabled by default.
- Per-run submit cap.
- Per-project daily submit cap.
- Estimated cost display or audit metadata.
- No automatic submit retry without idempotency proof.

Rollback:

- Disable provider flag.
- Lower submit caps to zero.
- Preserve local audit records for cost reconciliation.

### Duration-Based Cost Surprise

Risk: longer `frames` settings increase generated seconds and cost.

Impact: a small number of jobs can become expensive.

Mitigation:

- Validate supported frame values.
- Warn or block longer durations unless explicitly allowed.
- Record estimated generated seconds.

Rollback:

- Restrict provider to the shortest supported duration.
- Disable production provider for projects without a budget cap.

## API Compatibility Risks

### Model Key Changes

Risk: `jimeng_ti2v_v30_pro` changes behavior, is renamed, or is superseded.

Impact: submit failures or unexpected generation behavior.

Mitigation:

- Keep `req_key` configurable.
- Document default `req_key`.
- Add fake tests for request construction, not hard-coded business assumptions.

Rollback:

- Change provider configuration back to a known working `req_key`.
- Disable production provider if no supported key is available.

### Response Shape Changes

Risk: submit or poll responses change field names, status values, or error
codes.

Impact: parser failures or incorrect local status mapping.

Mitigation:

- Fail closed on unknown statuses.
- Preserve raw provider code and request id in sanitized diagnostics.
- Keep response parser tests close to official examples.

Rollback:

- Disable provider.
- Patch parser in a focused follow-up PR.

## Quota Risks

### QPS and Concurrency Limits

Risk: public docs do not provide a stable per-account QPS value, and default
video generation concurrency may be low.

Impact: 429 errors, slow jobs, and user-visible failures.

Mitigation:

- Default submit concurrency to 1.
- Back off on `50429` and `50430`.
- Make rate limits configurable.
- Avoid treating rate-limit errors as input failures.

Rollback:

- Reduce concurrency to zero by disabling provider.
- Keep pending local jobs from auto-resubmitting.

### Account Quota or Arrears

Risk: account quota, resource packs, or billing state prevents generation.

Impact: real provider unavailable despite correct code.

Mitigation:

- Document manual quota checks.
- Surface provider billing/quota errors separately when identifiable.
- Keep mock provider available for development.

Rollback:

- Disable real provider until account state is corrected.

## Rollback Strategy

Production rollback should be designed before rollout:

1. Disable the production Jimeng provider flag.
2. Stop new submits immediately.
3. Continue or fail already submitted jobs according to phase:
   - Submitted but not completed: keep polling only if cost and operator policy
     allow it.
   - Completed with valid `video_url`: download if still inside the validity
     window.
   - Expired or missing URL: mark failed with a recovery message.
4. Preserve completed local outputs.
5. Preserve sanitized audit data: local job id, remote `task_id`, provider
   request id, phase, and provider code.
6. Rotate credentials if rollback is triggered by a security concern.
7. Keep mock provider as the default path for CI and local development.
