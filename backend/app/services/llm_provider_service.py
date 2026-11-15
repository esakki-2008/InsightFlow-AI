from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


NVIDIA_CHAT_COMPLETIONS_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
DEFAULT_NVIDIA_MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"


def test_nvidia_connection(api_key: str, model: str = DEFAULT_NVIDIA_MODEL) -> dict:
    """Verify a user-supplied NVIDIA API key without storing or logging it."""
    key = (api_key or "").strip()
    selected_model = (model or DEFAULT_NVIDIA_MODEL).strip()

    if not key:
        raise ValueError("Enter your NVIDIA API key.")
    if len(key) > 512 or any(char.isspace() for char in key):
        raise ValueError("The NVIDIA API key format is invalid.")
    if not selected_model or len(selected_model) > 200:
        raise ValueError("Enter a valid NVIDIA model identifier.")

    payload = {
        "model": selected_model,
        "messages": [
            {
                "role": "user",
                "content": "Reply with exactly: InsightFlow connection successful",
            }
        ],
        "max_tokens": 32,
        "temperature": 0,
        "stream": False,
    }
    request = Request(
        NVIDIA_CHAT_COMPLETIONS_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        # Do not return provider response bodies: they may contain sensitive details.
        if exc.code in (401, 403):
            raise ValueError("NVIDIA rejected this API key. Check that it is valid and active.") from exc
        if exc.code == 404:
            raise ValueError("NVIDIA could not find this model. Check the model identifier.") from exc
        if exc.code == 429:
            raise ValueError("NVIDIA rate limit or quota reached. Try again later or check your API quota.") from exc
        raise ValueError(f"NVIDIA API request failed with status {exc.code}.") from exc
    except (TimeoutError, URLError) as exc:
        raise ValueError("Could not reach NVIDIA. Check your internet connection and try again.") from exc
    except (json.JSONDecodeError, UnicodeDecodeError, KeyError, TypeError) as exc:
        raise ValueError("NVIDIA returned an unexpected response.") from exc

    choices = result.get("choices") or []
    if not choices or not isinstance(choices[0].get("message", {}).get("content"), str):
        raise ValueError("NVIDIA responded, but no text response was returned.")

    return {
        "provider": "NVIDIA",
        "model": selected_model,
        "connected": True,
        "message": "NVIDIA API connection successful. Your key was used for this request only and was not saved.",
    }
