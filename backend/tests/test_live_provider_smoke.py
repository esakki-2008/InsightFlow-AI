"""Opt-in live smoke tests for configured AI providers.

These tests are skipped unless INSIGHTFLOW_LIVE_PROVIDER_TESTS=1 and the
provider-specific environment variables are present. Never place credentials
in source control or print them from test code.
"""
import json
import os

import pytest

from app.services.native_provider_service import (
    PROTOCOL_ANTHROPIC,
    PROTOCOL_GEMINI,
    test_native_provider_connection as run_native_provider_connection,
)
from app.services.openai_compatible_service import test_openai_compatible_connection as run_openai_compatible_connection


LIVE_TESTS_ENABLED = os.getenv("INSIGHTFLOW_LIVE_PROVIDER_TESTS", "").strip() == "1"


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        pytest.skip(f"Set {name} locally to run this live provider check.")
    return value


def _optional_headers() -> dict[str, str] | None:
    raw = os.getenv("INSIGHTFLOW_LIVE_PROVIDER_HEADERS", "").strip()
    if not raw:
        return None
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        pytest.fail("INSIGHTFLOW_LIVE_PROVIDER_HEADERS must contain valid JSON.")
    if not isinstance(value, dict) or not all(
        isinstance(name, str) and isinstance(header_value, str)
        for name, header_value in value.items()
    ):
        pytest.fail("INSIGHTFLOW_LIVE_PROVIDER_HEADERS must be a JSON object of string values.")
    return value


pytestmark = pytest.mark.skipif(
    not LIVE_TESTS_ENABLED,
    reason="Live provider checks are opt-in; set INSIGHTFLOW_LIVE_PROVIDER_TESTS=1.",
)


def test_live_openai_compatible_provider():
    result = run_openai_compatible_connection(
        api_key=_required("INSIGHTFLOW_LIVE_OPENAI_API_KEY"),
        base_url=_required("INSIGHTFLOW_LIVE_OPENAI_BASE_URL"),
        model=_required("INSIGHTFLOW_LIVE_OPENAI_MODEL"),
        provider_name="Live OpenAI-compatible provider",
        custom_headers=_optional_headers(),
    )
    assert result.get("connected") is True


def test_live_gemini_native_provider():
    result = run_native_provider_connection(
        protocol=PROTOCOL_GEMINI,
        api_key=_required("INSIGHTFLOW_LIVE_GEMINI_API_KEY"),
        base_url=os.getenv("INSIGHTFLOW_LIVE_GEMINI_BASE_URL", "https://generativelanguage.googleapis.com"),
        model=_required("INSIGHTFLOW_LIVE_GEMINI_MODEL"),
        provider_name="Live Gemini",
    )
    assert result.get("connected") is True


def test_live_anthropic_native_provider():
    result = test_native_provider_connection(
        protocol=PROTOCOL_ANTHROPIC,
        api_key=_required("INSIGHTFLOW_LIVE_ANTHROPIC_API_KEY"),
        base_url=os.getenv("INSIGHTFLOW_LIVE_ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
        model=_required("INSIGHTFLOW_LIVE_ANTHROPIC_MODEL"),
        provider_name="Live Anthropic",
    )
    assert result.get("connected") is True
