# Volcengine V4 Signing

## Purpose

This document describes the standalone Volcengine V4 signing library added for
future Jimeng REST integration.

The signer is independent from the Jimeng provider. It does not send HTTP
requests, does not call Jimeng, does not consume quota, and does not require
real AK/SK credentials in tests.

## Signing Process

The signer follows a deterministic V4-style HMAC-SHA256 flow:

1. Generate or accept an `X-Date` timestamp in UTC basic format:
   `YYYYMMDDTHHMMSSZ`.
2. Hash the request payload with SHA-256.
3. Build the canonical query string by URL-encoding keys and values, then
   sorting by encoded key and value.
4. Build canonical headers by lowercasing header names, trimming values,
   collapsing repeated spaces, and sorting by header name.
5. Build the signed header list from the canonical header names.
6. Build the canonical request:

   ```text
   HTTP_METHOD
   canonical_path
   canonical_query_string
   canonical_headers
   signed_headers
   payload_hash
   ```

7. Build the credential scope:

   ```text
   YYYYMMDD/region/service/request
   ```

8. Build the string to sign:

   ```text
   HMAC-SHA256
   X-Date
   credential_scope
   sha256(canonical_request)
   ```

9. Derive the signing key through the HMAC chain:

   ```text
   kDate = HMAC(secret_key, YYYYMMDD)
   kRegion = HMAC(kDate, region)
   kService = HMAC(kRegion, service)
   kSigning = HMAC(kService, request)
   ```

10. Sign the string to sign with `kSigning`.
11. Build the Authorization header:

    ```text
    HMAC-SHA256 Credential=<access_key>/<scope>, SignedHeaders=<headers>, Signature=<signature>
    ```

## Request Flow

Future provider integration should use the signer as a pure transformation:

1. Provider adapter builds an unsigned request object.
2. Signing layer receives method, path, query, headers, payload, region, service,
   AK, SK, and timestamp.
3. Signing layer returns copied headers containing `X-Date` and
   `Authorization`.
4. HTTP transport sends the signed request.

The signer deliberately returns diagnostic fields such as canonical request,
string to sign, credential scope, signed headers, and signature so tests can
assert deterministic behavior. Production logging must not emit those fields by
default.

## Security Notes

- Never commit real AK/SK values.
- Tests must use fake credentials only.
- Do not log `secret_key`.
- Do not log raw Authorization headers in production.
- Do not log canonical request or string-to-sign values when they may contain
  sensitive headers, media URLs, prompts, or request bodies.
- Treat the signer as local computation only; it must not perform network I/O.
- Keep provider enablement and real Jimeng requests in later PRs behind
  explicit opt-in controls.

## Test Strategy

The signer is covered by deterministic unit tests for:

- Empty payload hashing.
- Unicode payload hashing.
- Canonical query ordering.
- Canonical header normalization and ordering.
- Signed header generation.
- Canonical request construction.
- Credential scope construction.
- String-to-sign construction.
- Authorization header construction.
- HMAC byte and hex helpers.
- UTC `X-Date` generation.
- Full deterministic signing without mutating input headers.

The test suite does not use real credentials, does not contact Volcengine, and
does not require network access.
