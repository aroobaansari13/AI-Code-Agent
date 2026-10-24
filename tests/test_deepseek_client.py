
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from agent.deepseek_client import DeepSeekClient


def make_response(
    prompt_tokens=100,
    completion_tokens=50
):
    """Create a fake API response for testing."""

    return SimpleNamespace(
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens
        ),
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="Test response",
                    tool_calls=None
                )
            )
        ]
    )


@pytest.fixture
def deepseek_client():
    """Create a client without making real API calls."""

    client = DeepSeekClient(
        api_key="test-key",
        model="test-model"
    )

    client.client.chat.completions.create = Mock(
        return_value=make_response()
    )

    return client


def test_client_configuration(deepseek_client):
    assert deepseek_client.model == "test-model"


def test_chat_response(deepseek_client):
    response = deepseek_client.chat([
        {
            "role": "user",
            "content": "Hello"
        }
    ])

    assert response.choices[0].message.content == (
        "Test response"
    )


def test_token_usage(deepseek_client):
    deepseek_client.chat([
        {
            "role": "user",
            "content": "Hello"
        }
    ])

    usage = deepseek_client.get_usage()

    assert usage["input_tokens"] == 100
    assert usage["output_tokens"] == 50
    assert usage["total_tokens"] == 150


def test_cumulative_token_usage(deepseek_client):
    messages = [
        {
            "role": "user",
            "content": "Hello"
        }
    ]

    deepseek_client.chat(messages)
    deepseek_client.chat(messages)

    usage = deepseek_client.get_usage()

    assert usage["input_tokens"] == 200
    assert usage["output_tokens"] == 100
    assert usage["total_tokens"] == 300


def test_reject_empty_messages(deepseek_client):
    with pytest.raises(ValueError):
        deepseek_client.chat([])


def test_tool_parameters(deepseek_client):
    messages = [
        {
            "role": "user",
            "content": "Create a Python file."
        }
    ]

    tools = [
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Write a project file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string"
                        },
                        "content": {
                            "type": "string"
                        }
                    },
                    "required": [
                        "file_path",
                        "content"
                    ]
                }
            }
        }
    ]

    deepseek_client.chat(
        messages,
        tools=tools,
        tool_choice="auto"
    )

    call_kwargs = (
        deepseek_client.client.chat.completions.create
        .call_args.kwargs
    )

    assert call_kwargs["tools"] == tools
    assert call_kwargs["tool_choice"] == "auto"


def test_missing_api_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    with pytest.raises(ValueError):
        DeepSeekClient(api_key="")


def test_max_output_tokens(deepseek_client):
    deepseek_client.chat(
        messages=[
            {
                "role": "user",
                "content": "Generate Python code."
            }
        ],
        max_output_tokens=1500
    )

    call_kwargs = (
        deepseek_client.client.chat.completions.create
        .call_args.kwargs
    )

    assert call_kwargs["max_tokens"] == 1500


def test_invalid_max_output_tokens(deepseek_client):
    with pytest.raises(ValueError):
        deepseek_client.chat(
            messages=[
                {
                    "role": "user",
                    "content": "Hello"
                }
            ],
            max_output_tokens=-5
        )
