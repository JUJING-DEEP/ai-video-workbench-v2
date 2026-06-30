from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

import pytest


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_JIMENG_SPIKE") != "1",
    reason="Jimeng real API spike is opt-in; set RUN_JIMENG_SPIKE=1 to run.",
)


REQUIRED_ENV_VARS = (
    "JIMENG_ACCESS_KEY",
    "JIMENG_SECRET_KEY",
    "JIMENG_ENDPOINT",
    "JIMENG_MODEL",
)


@dataclass(frozen=True)
class JimengSpikeConfig:
    access_key_present: bool
    secret_key_present: bool
    endpoint: str
    model: str


def _read_spike_config() -> JimengSpikeConfig:
    missing = [name for name in REQUIRED_ENV_VARS if not os.getenv(name, "").strip()]
    if missing:
        pytest.fail(
            "Jimeng spike is enabled but required environment variables are missing: "
            + ", ".join(missing)
        )

    endpoint = os.environ["JIMENG_ENDPOINT"].strip()
    parsed = urlparse(endpoint)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        pytest.fail("JIMENG_ENDPOINT must be a valid http(s) URL.")

    return JimengSpikeConfig(
        access_key_present=bool(os.environ["JIMENG_ACCESS_KEY"].strip()),
        secret_key_present=bool(os.environ["JIMENG_SECRET_KEY"].strip()),
        endpoint=endpoint.rstrip("/") + "/",
        model=os.environ["JIMENG_MODEL"].strip(),
    )


def _assert_endpoint_reachable(endpoint: str) -> int:
    request = Request(endpoint, method="HEAD")
    try:
        with urlopen(request, timeout=10) as response:
            return response.status
    except HTTPError as exc:
        return exc.code
    except (TimeoutError, socket.timeout) as exc:
        pytest.fail(f"JIMENG_ENDPOINT timed out during reachability check: {exc}")
    except URLError as exc:
        pytest.fail(f"JIMENG_ENDPOINT could not be reached: {exc.reason}")


def _build_submit_contract(config: JimengSpikeConfig) -> dict:
    return {
        "endpoint": urljoin(config.endpoint, "submit"),
        "model": config.model,
        "credentials": {
            "access_key_present": config.access_key_present,
            "secret_key_present": config.secret_key_present,
        },
        "input": {
            "keyframe_url": "https://example.invalid/spike/keyframe.png",
            "prompt": "Jimeng feasibility spike contract construction only.",
            "duration_seconds": 2,
        },
    }


def _build_poll_contract(config: JimengSpikeConfig) -> dict:
    return {
        "endpoint": urljoin(config.endpoint, "result"),
        "model": config.model,
        "submit_id": "spike-submit-id-placeholder",
    }


def _build_download_contract() -> dict:
    return {
        "result_url": "https://example.invalid/spike/result.mp4",
        "expected_content_type": "video/mp4",
    }


def test_jimeng_real_api_feasibility_contracts_are_constructable():
    config = _read_spike_config()

    status = _assert_endpoint_reachable(config.endpoint)
    assert 100 <= status < 500, f"JIMENG_ENDPOINT returned unexpected status: {status}"

    submit_contract = _build_submit_contract(config)
    poll_contract = _build_poll_contract(config)
    download_contract = _build_download_contract()

    assert submit_contract["endpoint"].startswith(config.endpoint)
    assert submit_contract["credentials"] == {
        "access_key_present": True,
        "secret_key_present": True,
    }
    assert submit_contract["model"] == config.model
    assert submit_contract["input"]["keyframe_url"]

    assert poll_contract["endpoint"].startswith(config.endpoint)
    assert poll_contract["submit_id"]
    assert poll_contract["model"] == config.model

    assert download_contract["result_url"].startswith("https://")
    assert download_contract["expected_content_type"] == "video/mp4"
