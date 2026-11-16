"""Native Gemini and Anthropic text-generation adapters using the pinned HTTPS transport."""
from __future__ import annotations

import re
from urllib.parse import quote, urlsplit

from app.services.openai_compatible_service import _post_json_with_headers


PROTOCOL_GEMINI = "native_gemini"
PROTOCOL_ANTHROPIC = "native_anthropic"
SUPPORTED_NATIVE_PROTOCOLS = {PROTOCOL_GEMINI, PROTOCOL_ANTHROPIC}


def _validate_inputs(api_key: str, model: str, base_url: str) -> tuple[str, str, str]:
    key = (api_key or "").strip()
    selected_model = (model or "").strip()
    endpoint = (base_url or "").strip().rstrip("/")
    parsed = urlsplit(endpoint)
    if not key or len(key) > 4096 or any(ch.isspace() for ch in key):
        raise ValueError("The saved API key is invalid.")
    if not selected_model or len(selected_model) > 200 or not re.fullmatch(r"[A-Za-z0-9._:-]+", selected_model):
        raise ValueError("Enter a valid model identifier.")
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Provider endpoints must use a valid HTTPS URL without embedded credentials, query parameters, or fragments.")
    hostname = parsed.hostname.lower()
    if hostname == "localhost" or hostname.endswith((".localhost", ".local", ".internal")):
        raise ValueError("Local and internal provider endpoints are not allowed.")
    return key, selected_model, endpoint


def _text_messages(messages: list[dict]) -> tuple[str, list[dict]]:
    system_parts: list[str] = []
    converted: list[dict] = []
    for item in messages:
        role = item.get("role")
        content = item.get("content")
        if not isinstance(content, str):
            raise ValueError("Only text messages are supported by this provider adapter.")
        if role == "system":
            system_parts.append(content)
        elif role in {"user", "assistant"}:
            converted.append({"role": role, "content": content})
        else:
            raise ValueError("Unsupported message role for this provider.")
    if not converted or converted[-1]["role"] != "user":
        raise ValueError("Provider requests must end with a user message.")
    return "\n\n".join(system_parts), converted


def native_provider_chat(
    protocol: str,
    api_key: str,
    model: str,
    messages: list[dict],
    base_url: str,
    max_tokens: int = 700,
) -> str:
    """Generate one text completion using the selected provider's native REST contract."""
    key, selected_model, endpoint = _validate_inputs(api_key, model, base_url)
    system_text, conversation = _text_messages(messages)

    if protocol == PROTOCOL_GEMINI:
        if conversation and conversation[0]["role"] == "assistant":
            raise ValueError("Gemini conversations must begin with a user message.")
        contents = [
            {"role": "model" if item["role"] == "assistant" else "user",
             "parts": [{"text": item["content"]}]}
            for item in conversation
        ]
        payload = {
            "contents": contents,
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.1},
        }
        if system_text:
            payload["systemInstruction"] = {"parts": [{"text": system_text}]}
        model_path = selected_model.removeprefix("models/")
        url = f"{endpoint}/v1beta/models/{quote(model_path, safe='')}:generateContent"
        result = _post_json_with_headers(url, payload, {"x-goog-api-key": key})
        candidates = result.get("candidates") or []
        if not candidates or not isinstance(candidates[0], dict):
            raise ValueError("Gemini returned no completion candidates.")
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = "\n".join(part.get("text", "") for part in parts if isinstance(part, dict))
    elif protocol == PROTOCOL_ANTHROPIC:
        payload = {
            "model": selected_model,
            "max_tokens": max(1, min(int(max_tokens), 4096)),
            "messages": conversation,
        }
        if system_text:
            payload["system"] = system_text
        url = f"{endpoint}/v1/messages"
        result = _post_json_with_headers(
            url,
            payload,
            {"x-api-key": key, "anthropic-version": "2023-06-01"},
        )
        blocks = result.get("content") or []
        text = "\n".join(block.get("text", "") for block in blocks
                          if isinstance(block, dict) and block.get("type") == "text")
    else:
        raise ValueError("The selected native AI provider protocol is not supported.")

    if not isinstance(text, str) or not text.strip():
        raise ValueError("The provider returned an empty response. Try again.")
    return text.strip()


def test_native_provider_connection(
    protocol: str,
    api_key: str,
    model: str,
    base_url: str,
    provider_name: str,
) -> dict:
    """Verify a native provider key with a minimal prompt without exposing the key."""
    native_provider_chat(
        protocol=protocol,
        api_key=api_key,
        model=model,
        base_url=base_url,
        messages=[{"role": "user", "content": "Reply with exactly: OK"}],
        max_tokens=16,
    )
    return {
        "provider": (provider_name or "AI provider")[:80],
        "model": model,
        "connected": True,
        "message": "Provider connection successful. Your API key was used for this test and was not returned.",
    }
