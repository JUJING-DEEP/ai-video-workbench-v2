from __future__ import annotations

import base64
import json
from urllib import error, request


class NanoBananaError(Exception):
    status_code = 502


class NanoBananaInvalidKeyError(NanoBananaError):
    status_code = 401


class NanoBananaTimeoutError(NanoBananaError):
    status_code = 504


class NanoBananaProviderError(NanoBananaError):
    status_code = 502


class NanoBananaClient:
    def generate_image(self, prompt: str, api_key: str, base_url: str) -> bytes:
        payload = json.dumps({"prompt": prompt}).encode("utf-8")
        req = request.Request(
            base_url,
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=60) as response:
                content_type = response.headers.get("content-type", "")
                data = response.read()
        except TimeoutError as exc:
            raise NanoBananaTimeoutError("Nano Banana request timeout.") from exc
        except error.HTTPError as exc:
            if exc.code in {401, 403}:
                raise NanoBananaInvalidKeyError("Invalid Nano Banana API key.") from exc
            raise NanoBananaProviderError("Nano Banana provider error.") from exc
        except error.URLError as exc:
            raise NanoBananaProviderError("Nano Banana provider error.") from exc

        if "application/json" in content_type:
            body = json.loads(data.decode("utf-8"))
            image_base64 = body.get("image_base64")
            if not image_base64:
                raise NanoBananaProviderError("Nano Banana response did not include image_base64.")
            return base64.b64decode(image_base64)

        return data
