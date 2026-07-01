from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import re
from typing import Mapping
from urllib.parse import quote

ALGORITHM = "HMAC-SHA256"
REQUEST_SUFFIX = "request"
_HEADER_SPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class VolcengineSignedRequest:
    headers: dict
    canonical_request: str
    string_to_sign: str
    credential_scope: str
    signed_headers: str
    signature: str
    x_date: str


def _to_bytes(value: bytes | str) -> bytes:
    if isinstance(value, bytes):
        return value
    return str(value).encode("utf-8")


def sha256_hex(value: bytes | str) -> str:
    return hashlib.sha256(_to_bytes(value)).hexdigest()


def hmac_sha256(key: bytes | str, message: bytes | str) -> bytes:
    return hmac.new(_to_bytes(key), _to_bytes(message), hashlib.sha256).digest()


def hmac_sha256_hex(key: bytes | str, message: bytes | str) -> str:
    return hmac.new(_to_bytes(key), _to_bytes(message), hashlib.sha256).hexdigest()


def _encode_query_part(value: object) -> str:
    return quote(str(value), safe="-_.~")


def build_canonical_query_string(query: Mapping[str, object]) -> str:
    encoded = [
        (_encode_query_part(key), _encode_query_part(value))
        for key, value in query.items()
    ]
    return "&".join(f"{key}={value}" for key, value in sorted(encoded))


def _normalize_header_value(value: object) -> str:
    return _HEADER_SPACE_RE.sub(" ", str(value).strip())


def _canonical_header_items(headers: Mapping[str, object]) -> list[tuple[str, str]]:
    return sorted(
        (str(name).strip().lower(), _normalize_header_value(value))
        for name, value in headers.items()
    )


def build_canonical_headers(headers: Mapping[str, object]) -> str:
    return "".join(f"{name}:{value}\n" for name, value in _canonical_header_items(headers))


def build_signed_headers(headers: Mapping[str, object]) -> str:
    return ";".join(name for name, _value in _canonical_header_items(headers))


def build_canonical_request(
    method: str,
    path: str,
    query: Mapping[str, object],
    headers: Mapping[str, object],
    payload_hash: str,
) -> str:
    return "\n".join(
        [
            method.upper(),
            path or "/",
            build_canonical_query_string(query),
            build_canonical_headers(headers),
            build_signed_headers(headers),
            payload_hash,
        ]
    )


def build_credential_scope(date_stamp: str, region: str, service: str) -> str:
    return f"{date_stamp}/{region}/{service}/{REQUEST_SUFFIX}"


def build_string_to_sign(
    x_date: str,
    credential_scope: str,
    canonical_request: str,
) -> str:
    return "\n".join(
        [
            ALGORITHM,
            x_date,
            credential_scope,
            sha256_hex(canonical_request),
        ]
    )


def _derive_signing_key(secret_key: str, date_stamp: str, region: str, service: str) -> bytes:
    date_key = hmac_sha256(secret_key, date_stamp)
    region_key = hmac_sha256(date_key, region)
    service_key = hmac_sha256(region_key, service)
    return hmac_sha256(service_key, REQUEST_SUFFIX)


def build_authorization_header(
    access_key: str,
    credential_scope: str,
    signed_headers: str,
    signature: str,
) -> str:
    return (
        f"{ALGORITHM} "
        f"Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, "
        f"Signature={signature}"
    )


def generate_x_date(request_datetime: datetime | None = None) -> str:
    value = request_datetime or datetime.now(timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sign_request(
    method: str,
    path: str,
    query: Mapping[str, object],
    headers: Mapping[str, object],
    payload: bytes | str,
    access_key: str,
    secret_key: str,
    region: str,
    service: str,
    request_datetime: datetime | None = None,
) -> VolcengineSignedRequest:
    x_date = generate_x_date(request_datetime)
    date_stamp = x_date[:8]
    signed_request_headers = dict(headers)
    signed_request_headers["X-Date"] = x_date

    canonical_request = build_canonical_request(
        method=method,
        path=path,
        query=query,
        headers=signed_request_headers,
        payload_hash=sha256_hex(payload),
    )
    credential_scope = build_credential_scope(date_stamp, region, service)
    string_to_sign = build_string_to_sign(x_date, credential_scope, canonical_request)
    signing_key = _derive_signing_key(secret_key, date_stamp, region, service)
    signature = hmac_sha256_hex(signing_key, string_to_sign)
    signed_headers = build_signed_headers(signed_request_headers)
    signed_request_headers["Authorization"] = build_authorization_header(
        access_key=access_key,
        credential_scope=credential_scope,
        signed_headers=signed_headers,
        signature=signature,
    )

    return VolcengineSignedRequest(
        headers=signed_request_headers,
        canonical_request=canonical_request,
        string_to_sign=string_to_sign,
        credential_scope=credential_scope,
        signed_headers=signed_headers,
        signature=signature,
        x_date=x_date,
    )
