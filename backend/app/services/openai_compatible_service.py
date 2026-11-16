"""Safe OpenAI-compatible chat-completions connection checks.

Custom endpoints are resolved to public IP addresses and the TLS connection is
pinned to the validated address. Redirects are never followed.
"""
from __future__ import annotations

import http.client
import ipaddress
import json
import socket
import ssl
from urllib.parse import urlsplit


MAX_RESPONSE_BYTES = 1_000_000
CONNECTION_TIMEOUT_SECONDS = 15


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """HTTPSConnection that connects to a previously validated public IP."""

    def __init__(self, hostname: str, port: int, address: str, timeout: int = CONNECTION_TIMEOUT_SECONDS):
        super().__init__(hostname, port=port, timeout=timeout, context=ssl.create_default_context())
        self._validated_address = address

    def connect(self):
        raw_socket = socket.create_connection(
            (self._validated_address, self.port),
            self.timeout,
            self.source_address,
        )
        self.sock = self._context.wrap_socket(raw_socket, server_hostname=self.host)


def _resolve_public_address(hostname: str) -> str:
    """Resolve once and reject the hostname if any answer is not globally routable."""
    try:
        answers = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError("The provider hostname could not be resolved.") from exc

    addresses: list[str] = []
    for answer in answers:
        address = answer[4][0]
        try:
            parsed = ipaddress.ip_address(address)
        except ValueError as exc:
            raise ValueError("The provider hostname resolved to an invalid address.") from exc
        if not parsed.is_global:
            raise ValueError("Provider endpoints must resolve only to public IP addresses.")
        if address not in addresses:
            addresses.append(address)

    if not addresses:
        raise ValueError("The provider hostname did not resolve to a public IP address.")
    return addresses[0]


def _post_json(url: str, api_key: str, payload: dict) -> dict:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Provider endpoints must use HTTPS.")
    hostname = parsed.hostname
    address = _resolve_public_address(hostname)
    port = parsed.port or 443
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query

    connection = _PinnedHTTPSConnection(hostname, port, address)
    body = json.dumps(payload).encode("utf-8")
    try:
        connection.request(
            "POST",
            path,
            body=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Host": parsed.netloc,
            },
        )
        response = connection.getresponse()
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError("The provider response was too large.")
        if response.status < 200 or response.status >= 300:
            if response.status in (401, 403):
                raise ValueError("The provider rejected this API key or account access.")
            if response.status == 404:
                raise ValueError("The provider endpoint or model was not found. Check the base URL and model ID.")
            if response.status == 429:
                raise ValueError("The provider rate limit or quota was reached.")
            raise ValueError(f"The provider returned HTTP {response.status}.")
        try:
            result = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError("The provider returned an invalid JSON response.") from exc
        if not isinstance(result, dict):
            raise ValueError("The provider returned an unexpected response.")
        return result
    except (TimeoutError, socket.timeout) as exc:
        raise ValueError("The provider connection timed out.") from exc
    except OSError as exc:
        raise ValueError("Could not connect to the provider endpoint.") from exc
    finally:
        connection.close()


def test_openai_compatible_connection(
    api_key: str,
    base_url: str,
    model: str,
    provider_name: str = "OpenAI-compatible provider",
) -> dict:
    """Send a minimal chat-completions request without exposing or persisting the key."""
    key = (api_key or "").strip()
    selected_model = (model or "").strip()
    endpoint = (base_url or "").strip().rstrip("/")
    if not key or len(key) > 4096 or any(char.isspace() for char in key):
        raise ValueError("The saved API key is invalid.")
    if not selected_model or len(selected_model) > 200:
        raise ValueError("Enter a valid model identifier.")
    parsed = urlsplit(endpoint)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Provider endpoints must use a valid HTTPS URL without embedded credentials.")
    if parsed.query or parsed.fragment:
        raise ValueError("Provider base URLs cannot contain query parameters or fragments.")
    hostname = parsed.hostname.lower()
    if hostname in {"localhost"} or hostname.endswith((".localhost", ".local", ".internal")):
        raise ValueError("Local and internal provider endpoints are not allowed.")
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        raise ValueError("Use a public provider hostname, not an IP address.")

    completion_url = endpoint if parsed.path.rstrip("/").endswith("/chat/completions") else endpoint + "/chat/completions"
    payload = {
        "model": selected_model,
        "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
        "max_tokens": 16,
        "temperature": 0,
        "stream": False,
    }
    result = _post_json(completion_url, key, payload)
    choices = result.get("choices") or []
    if not choices or not isinstance(choices[0], dict):
        raise ValueError("The provider returned no completion choices.")
    message = choices[0].get("message") or {}
    if not isinstance(message, dict) or not (
        isinstance(message.get("content"), str) and message["content"].strip()
    ):
        raise ValueError("The provider responded, but returned no message content.")
    return {
        "provider": provider_name[:80],
        "model": selected_model,
        "connected": True,
        "message": "Provider connection successful. Your API key was used for this test and was not returned.",
    }
