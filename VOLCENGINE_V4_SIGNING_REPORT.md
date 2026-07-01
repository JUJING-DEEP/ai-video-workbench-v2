# Volcengine V4 Signing Report

## Test Coverage

Added deterministic provider contract tests for:

- Payload SHA-256 hashing, including empty and Unicode payloads.
- Canonical query string ordering and URL encoding.
- Canonical header lowercasing, trimming, space collapsing, and ordering.
- Signed header list construction.
- Canonical request construction.
- Credential scope construction.
- String-to-sign construction.
- Authorization header construction.
- HMAC byte and hex helpers.
- UTC `X-Date` generation.
- Full request signing with fixed AK/SK, timestamp, region, service, headers,
  query, and payload.
- Input header immutability during signing.

The tests use fake credentials only and do not perform HTTP requests.

## Remaining Gaps

- No real Volcengine request has been sent.
- No official SDK golden vector has been imported into the test suite yet.
- Temporary session token handling is not implemented.
- Provider integration is not wired.
- HTTP transport, retry, timeout, and error mapping remain future work.
- Jimeng submit, poll, and download flows remain out of scope for this PR.

## Recommendation

It is reasonable to start the Submit API PR after review, with two boundaries:

- Submit work should use fake HTTP responses first and keep real Jimeng calls
  opt-in only.
- Before enabling any real account smoke test, compare this signer against an
  official SDK request or official signing example.
