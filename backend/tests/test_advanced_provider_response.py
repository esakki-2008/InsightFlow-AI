from __future__ import annotations

import pytest

from app.services import advanced_question_service as service


def test_provider_chat_returns_only_user_facing_content(monkeypatch):
    monkeypatch.setattr(
        service,
        "_post_json",
        lambda *args, **kwargs: {
            "choices": [{
                "message": {
                    "content": "The average BMI is 26.4.",
                    "reasoning_content": "PRIVATE INTERNAL REASONING",
                }
            }]
        },
    )

    answer = service._provider_chat(
        api_key="test-key",
        model="test-model",
        messages=[],
        base_url="https://provider.example/v1",
    )

    assert answer == "The average BMI is 26.4."
    assert "PRIVATE INTERNAL REASONING" not in answer


def test_provider_chat_rejects_reasoning_only_response(monkeypatch):
    monkeypatch.setattr(
        service,
        "_post_json",
        lambda *args, **kwargs: {
            "choices": [{
                "message": {
                    "content": None,
                    "reasoning_content": "PRIVATE INTERNAL REASONING",
                }
            }]
        },
    )

    with pytest.raises(ValueError, match="no user-facing answer"):
        service._provider_chat(
            api_key="test-key",
            model="test-model",
            messages=[],
            base_url="https://provider.example/v1",
        )
