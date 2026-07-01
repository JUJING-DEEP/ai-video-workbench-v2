from datetime import datetime, timezone

from app.video_workbench.providers.volcengine_v4_signer import (
    ALGORITHM,
    build_authorization_header,
    build_canonical_headers,
    build_canonical_query_string,
    build_canonical_request,
    build_credential_scope,
    build_signed_headers,
    build_string_to_sign,
    generate_x_date,
    hmac_sha256,
    hmac_sha256_hex,
    sha256_hex,
    sign_request,
)


FIXED_TIME = datetime(2026, 6, 30, 12, 34, 56, tzinfo=timezone.utc)
EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_payload_hash_handles_empty_payload():
    assert sha256_hex(b"") == EMPTY_SHA256
    assert sha256_hex("") == EMPTY_SHA256


def test_payload_hash_handles_unicode_payload():
    assert sha256_hex('{"prompt":"即梦 video"}') == "cabc14b5ba19a3437c67cb84f3f1df02ae7a8052d6cd054866b847eca26c33fc"


def test_query_ordering_uses_encoded_key_and_value_order():
    query = {
        "Version": "2022-08-31",
        "Action": "CVSync2AsyncSubmitTask",
        "space value": "a b",
        "symbol": "a/b",
    }

    assert (
        build_canonical_query_string(query)
        == "Action=CVSync2AsyncSubmitTask&Version=2022-08-31&space%20value=a%20b&symbol=a%2Fb"
    )


def test_canonical_headers_are_lowercase_trimmed_collapsed_and_ordered():
    headers = {
        "X-Date": "20260630T123456Z",
        "Content-Type": " application/json ",
        "Host": "visual.volcengineapi.com",
        "X-Custom": " alpha   beta ",
    }

    assert build_canonical_headers(headers) == (
        "content-type:application/json\n"
        "host:visual.volcengineapi.com\n"
        "x-custom:alpha beta\n"
        "x-date:20260630T123456Z\n"
    )
    assert build_signed_headers(headers) == "content-type;host;x-custom;x-date"


def test_canonical_request_is_deterministic():
    canonical_request = build_canonical_request(
        method="post",
        path="/",
        query={
            "Version": "2022-08-31",
            "Action": "CVSync2AsyncSubmitTask",
        },
        headers={
            "X-Date": "20260630T123456Z",
            "Content-Type": "application/json",
            "Host": "visual.volcengineapi.com",
        },
        payload_hash=sha256_hex('{"req_key":"jimeng_ti2v_v30_pro"}'),
    )

    assert canonical_request == (
        "POST\n"
        "/\n"
        "Action=CVSync2AsyncSubmitTask&Version=2022-08-31\n"
        "content-type:application/json\n"
        "host:visual.volcengineapi.com\n"
        "x-date:20260630T123456Z\n"
        "\n"
        "content-type;host;x-date\n"
        "1d39c1c255be84278c03fedf00bec1b28b20f834df2f15ec6f2bfcc68fc9f91b"
    )


def test_credential_scope_uses_date_region_service_and_request_suffix():
    assert build_credential_scope("20260630", "cn-north-1", "cv") == "20260630/cn-north-1/cv/request"


def test_string_to_sign_uses_canonical_request_hash():
    canonical_request = (
        "POST\n"
        "/\n"
        "Action=CVSync2AsyncSubmitTask&Version=2022-08-31\n"
        "content-type:application/json\n"
        "host:visual.volcengineapi.com\n"
        "x-date:20260630T123456Z\n"
        "\n"
        "content-type;host;x-date\n"
        "1d39c1c255be84278c03fedf00bec1b28b20f834df2f15ec6f2bfcc68fc9f91b"
    )

    assert build_string_to_sign(
        x_date="20260630T123456Z",
        credential_scope="20260630/cn-north-1/cv/request",
        canonical_request=canonical_request,
    ) == (
        "HMAC-SHA256\n"
        "20260630T123456Z\n"
        "20260630/cn-north-1/cv/request\n"
        "f2b7ee1072dc54c85f9e56bdd111a665ef07e732f4d0307d6cd2ae6613ddf096"
    )


def test_authorization_header_contains_algorithm_credential_headers_and_signature():
    authorization = build_authorization_header(
        access_key="AKLT_TEST",
        credential_scope="20260630/cn-north-1/cv/request",
        signed_headers="content-type;host;x-date",
        signature="7b7f1c0b1ba375922f4e83d5b9115c4c01029fe199be3085432937f8f5805b95",
    )

    assert authorization == (
        "HMAC-SHA256 "
        "Credential=AKLT_TEST/20260630/cn-north-1/cv/request, "
        "SignedHeaders=content-type;host;x-date, "
        "Signature=7b7f1c0b1ba375922f4e83d5b9115c4c01029fe199be3085432937f8f5805b95"
    )


def test_hmac_helpers_return_bytes_and_hex():
    assert hmac_sha256(b"key", "message") == bytes.fromhex(
        "6e9ef29b75fffc5b7abae527d58fdadb2fe42e7219011976917343065f58ed4a"
    )
    assert hmac_sha256_hex(b"key", "message") == "6e9ef29b75fffc5b7abae527d58fdadb2fe42e7219011976917343065f58ed4a"


def test_x_date_generation_uses_utc_basic_format():
    assert generate_x_date(FIXED_TIME) == "20260630T123456Z"


def test_sign_request_is_deterministic_and_does_not_mutate_input_headers():
    headers = {
        "Content-Type": "application/json",
        "Host": "visual.volcengineapi.com",
    }

    signed = sign_request(
        method="POST",
        path="/",
        query={
            "Version": "2022-08-31",
            "Action": "CVSync2AsyncSubmitTask",
        },
        headers=headers,
        payload='{"req_key":"jimeng_ti2v_v30_pro"}',
        access_key="AKLT_TEST",
        secret_key="SECRET_TEST",
        region="cn-north-1",
        service="cv",
        request_datetime=FIXED_TIME,
    )

    assert headers == {
        "Content-Type": "application/json",
        "Host": "visual.volcengineapi.com",
    }
    assert signed.x_date == "20260630T123456Z"
    assert signed.signed_headers == "content-type;host;x-date"
    assert signed.credential_scope == "20260630/cn-north-1/cv/request"
    assert signed.signature == "b8eaae52af2ca6ee281a8e32c44572d8413b07c1214026339c37339cc20ad82d"
    assert signed.headers["X-Date"] == "20260630T123456Z"
    assert signed.headers["Authorization"] == (
        f"{ALGORITHM} "
        "Credential=AKLT_TEST/20260630/cn-north-1/cv/request, "
        "SignedHeaders=content-type;host;x-date, "
        "Signature=b8eaae52af2ca6ee281a8e32c44572d8413b07c1214026339c37339cc20ad82d"
    )
