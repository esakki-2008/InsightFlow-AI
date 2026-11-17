"""Secure NVIDIA API connection check using bounded, non-redirecting HTTPS."""

from __future__ import annotations

import http.client
import json
import socket
import ssl
from urllib.parse import urlsplit


NVIDIA_CHAT_COMPLETIONS_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
DEFAULT_NVIDIA_MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"
CONNECTION_TIMEOUT_SECONDS = 15
MAX_RESPONSE_BYTES = 1_000_000


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
        "max_tokens": 128,
        "temperature": 0,
        "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
    }

    endpoint = urlsplit(NVIDIA_CHAT_COMPLETIONS_URL)
    connection = http.client.HTTPSConnection(
        endpoint.hostname,
        port=endpoint.port or 443,
        timeout=CONNECTION_TIMEOUT_SECONDS,
        context=ssl.create_default_context(),
    )
    try:
        connection.request(
            "POST",
            endpoint.path,
            body=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        # HTTPSConnection does not follow redirects. Treat every 3xx as an error
        # so the API key can never be forwarded to a redirect destination.
        response = connection.getresponse()
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError("NVIDIA returned a response that exceeded the allowed size.")

        if response.status < 200 or response.status >= 300:
            if response.status in (401, 403):
                raise ValueError(
                    "NVIDIA rejected this API key or account access. Check that it is valid and active."
                )
            if response.status == 404:
                raise ValueError("NVIDIA could not find this model. Check the model identifier.")
            if response.status == 429:
                raise ValueError("NVIDIA rate limit or quota reached. Try again later or check your API quota.")
            raise ValueError(f"NVIDIA API request failed with status {response.status}.")

        try:
            result = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError("NVIDIA returned an unexpected response.") from exc
        if not isinstance(result, dict):
            raise ValueError("NVIDIA returned an unexpected response.")
    except ValueError:
        raise
    except (TimeoutError, socket.timeout) as exc:
        raise ValueError("Could not reach NVIDIA. Check your internet connection and try again.") from exc
    except (OSError, http.client.HTTPException) as exc:
        raise ValueError("Could not reach NVIDIA. Check your internet connection and try again.") from exc
    finally:
        connection.close()

    choices = result.get("choices") or []
    if not choices or not isinstance(choices[0], dict):
        raise ValueError("NVIDIA returned no completion choices.")

    message = choices[0].get("message") or {}
    content = message.get("content")
    reasoning_content = message.get("reasoning_content")

    # Some reasoning models return their reasoning separately from the final text.
    # For a connection smoke test, either non-empty text field confirms a response.
    has_content = isinstance(content, str) and bool(content.strip())
    has_reasoning = isinstance(reasoning_content, str) and bool(reasoning_content.strip())
    if not has_content and not has_reasoning:
        finish_reason = choices[0].get("finish_reason")
        if finish_reason == "length":
            raise ValueError("NVIDIA reached the token limit before returning text. Increase max_tokens and retry.")
        raise ValueError("NVIDIA responded, but returned neither message content nor reasoning text.")

    return {
        "provider": "NVIDIA",
        "model": selected_model,
        "connected": True,
        "message": "NVIDIA API connection successful. Your key was used for this request only and was not saved.",
    }
