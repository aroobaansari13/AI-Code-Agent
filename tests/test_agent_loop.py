import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from agent.agent_loop import AgentLoop
from agent.cost_tracker import (
    CostTracker,
    BudgetExceededError,
)


def make_response(
    content=None,
    tool_calls=None,
    usage=True,
    prompt_tokens=100,
    completion_tokens=50,
):
    """Build a fake model response."""

    message = SimpleNamespace(
        role="assistant",
        content=content,
        tool_calls=tool_calls,
    )

    if usage:
        token_usage = SimpleNamespace(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
    else:
        token_usage = None

    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=message,
                finish_reason="stop",
            )
        ],
        usage=token_usage,
    )


def make_tool_call(
    name,
    arguments,
    call_id="call_1",
):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(
            name=name,
            arguments=json.dumps(arguments),
        ),
    )


# =========================================================
# EXISTING AGENT TESTS
# =========================================================


def test_agent_finishes_without_tools(tmp_path):
    client = Mock()

    client.chat.return_value = make_response(
        content="Project planning completed."
    )

    agent = AgentLoop(
        deepseek_client=client,
        project_directory=tmp_path,
    )

    result = agent.run({
        "project_name": "Space Fractions"
    })

    assert result["status"] == "completed"
    assert result["iterations"] == 1
    assert result["files"] == []


def test_agent_creates_file(tmp_path):
    client = Mock()

    client.chat.side_effect = [
        make_response(
            tool_calls=[
                make_tool_call(
                    "write_file",
                    {
                        "file_path": "main.py",
                        "content": (
                            "print('Space Fractions')"
                        ),
                    },
                )
            ]
        ),
        make_response(
            content=(
                "The project file has been created."
            )
        ),
    ]

    agent = AgentLoop(
        deepseek_client=client,
        project_directory=tmp_path,
    )

    result = agent.run({
        "project_name": "Space Fractions"
    })

    assert result["status"] == "completed"
    assert "main.py" in result["files"]

    assert (
        tmp_path / "main.py"
    ).read_text(encoding="utf-8") == (
        "print('Space Fractions')"
    )


def test_agent_blocks_unsafe_path(tmp_path):
    client = Mock()

    client.chat.side_effect = [
        make_response(
            tool_calls=[
                make_tool_call(
                    "write_file",
                    {
                        "file_path": "../unsafe.py",
                        "content": "print('unsafe')",
                    },
                )
            ]
        ),
        make_response(
            content=(
                "Unsafe operation was rejected."
            )
        ),
    ]

    agent = AgentLoop(
        deepseek_client=client,
        project_directory=tmp_path,
    )

    result = agent.run({
        "project_name": "Space Fractions"
    })

    assert result["status"] == "tool_error"
    assert result["files"] == []
    assert len(result["tool_errors"]) == 1
    assert (
        result["tool_errors"][0]["tool"]
        == "write_file"
    )

    assert not (
        tmp_path.parent / "unsafe.py"
    ).exists()

    assert not (
        tmp_path / "unsafe.py"
    ).exists()


def test_agent_iteration_limit(tmp_path):
    client = Mock()

    client.chat.return_value = make_response(
        tool_calls=[
            make_tool_call(
                "list_files",
                {},
            )
        ]
    )

    agent = AgentLoop(
        deepseek_client=client,
        project_directory=tmp_path,
        max_iterations=2,
    )

    result = agent.run({
        "project_name": "Space Fractions"
    })

    assert result["status"] == "iteration_limit"
    assert result["iterations"] == 2
    assert client.chat.call_count == 2


def test_unknown_tool(tmp_path):
    agent = AgentLoop(
        deepseek_client=Mock(),
        project_directory=tmp_path,
    )

    result = agent.execute_tool(
        "delete_everything",
        {},
    )

    assert result["status"] == "error"


def test_invalid_tool_arguments(tmp_path):
    agent = AgentLoop(
        deepseek_client=Mock(),
        project_directory=tmp_path,
    )

    result = agent.execute_tool(
        "write_file",
        None,
    )

    assert result["status"] == "error"


def test_reject_invalid_architecture(tmp_path):
    agent = AgentLoop(
        deepseek_client=Mock(),
        project_directory=tmp_path,
    )

    with pytest.raises(ValueError):
        agent.run("invalid architecture")


def test_agent_passes_output_limit(tmp_path):
    client = Mock()

    client.chat.return_value = make_response(
        content="Task completed."
    )

    agent = AgentLoop(
        deepseek_client=client,
        project_directory=tmp_path,
        max_output_tokens=1500,
    )

    agent.run({
        "project_name": "Space Fractions"
    })

    assert (
        client.chat.call_args.kwargs[
            "max_output_tokens"
        ]
        == 1500
    )


def test_input_token_estimation(tmp_path):
    agent = AgentLoop(
        deepseek_client=Mock(),
        project_directory=tmp_path,
    )

    estimate = agent.estimate_input_tokens()

    assert isinstance(estimate, int)
    assert estimate > 0


def test_tool_call_limit(tmp_path):
    client = Mock()

    client.chat.return_value = make_response(
        tool_calls=[
            make_tool_call(
                "list_files",
                {},
                "call_1",
            ),
            make_tool_call(
                "list_files",
                {},
                "call_2",
            ),
        ]
    )

    agent = AgentLoop(
        deepseek_client=client,
        project_directory=tmp_path,
        max_tool_calls=1,
    )

    result = agent.run({
        "project_name": "Space Fractions"
    })

    assert result["status"] == "tool_limit"
    assert agent.tool_calls_used == 0


def test_incomplete_response(tmp_path):
    client = Mock()

    response = make_response(
        content="Incomplete generated code..."
    )

    response.choices[0].finish_reason = "length"
    client.chat.return_value = response

    agent = AgentLoop(
        deepseek_client=client,
        project_directory=tmp_path,
    )

    result = agent.run({
        "project_name": "Space Fractions"
    })

    assert result["status"] == "incomplete_response"


# =========================================================
# PART 27B — NEW API BUDGET SAFETY TESTS
# =========================================================


def test_budget_blocks_request_before_api_call(
    tmp_path,
):
    """No API request when estimated budget is too low."""

    client = Mock()

    tracker = CostTracker(
        budget_usd="0.000001",
    )

    agent = AgentLoop(
        deepseek_client=client,
        project_directory=tmp_path,
        cost_tracker=tracker,
        max_output_tokens=2000,
    )

    with pytest.raises(BudgetExceededError):
        agent.run({
            "project_name": "Space Fractions"
        })

    client.chat.assert_not_called()


def test_real_mode_records_api_usage(tmp_path):
    """Real Mode records usage reported by the API."""

    client = Mock()

    client.chat.return_value = make_response(
        content="Done.",
        prompt_tokens=500,
        completion_tokens=250,
    )

    tracker = CostTracker(
        budget_usd="1.00",
    )

    agent = AgentLoop(
        deepseek_client=client,
        project_directory=tmp_path,
        cost_tracker=tracker,
        require_usage=True,
    )

    result = agent.run({
        "project_name": "Space Fractions"
    })

    summary = tracker.get_summary()

    assert result["status"] == "completed"
    assert summary["requests"] == 1
    assert summary["input_tokens"] == 500
    assert summary["output_tokens"] == 250
    assert summary["total_tokens"] == 750
    assert summary["estimated_cost_usd"] > 0


def test_real_mode_requires_token_usage(tmp_path):
    """Real Mode stops if token usage is missing."""

    client = Mock()

    client.chat.return_value = make_response(
        content="Done.",
        usage=False,
    )

    agent = AgentLoop(
        deepseek_client=client,
        project_directory=tmp_path,
        require_usage=True,
    )

    with pytest.raises(
        RuntimeError,
        match="token usage",
    ):
        agent.run({
            "project_name": "Space Fractions"
        })

    assert client.chat.call_count == 1


def test_real_mode_rejects_incomplete_usage(tmp_path):
    """Incomplete token usage must stop Real Mode."""

    client = Mock()

    client.chat.return_value = make_response(
        content="Done.",
        prompt_tokens=None,
        completion_tokens=50,
    )

    agent = AgentLoop(
        deepseek_client=client,
        project_directory=tmp_path,
        require_usage=True,
    )

    with pytest.raises(
        RuntimeError,
        match="Incomplete API token usage",
    ):
        agent.run({
            "project_name": "Space Fractions"
        })

    assert client.chat.call_count == 1


def test_budget_usage_persists_across_runs(
    tmp_path,
):
    """Recorded API usage survives tracker recreation."""

    client = Mock()

    client.chat.return_value = make_response(
        content="Done.",
        prompt_tokens=1000,
        completion_tokens=500,
    )

    state_file = (
        tmp_path / "api_budget.json"
    )

    tracker = CostTracker(
        budget_usd="1.00",
        state_file=state_file,
    )

    
    project_directory = tmp_path / "project"
    project_directory.mkdir()

    agent = AgentLoop(
        deepseek_client=client,
        project_directory=project_directory,
        cost_tracker=tracker,
        require_usage=True,
    )


    agent.run({
        "project_name": "Space Fractions"
    })

    assert state_file.is_file()

    restored = CostTracker(
        budget_usd="1.00",
        state_file=state_file,
    )

    summary = restored.get_summary()

    assert summary["requests"] == 1
    assert summary["input_tokens"] == 1000
    assert summary["output_tokens"] == 500
    assert summary["estimated_cost_usd"] > 0


def test_budget_stops_second_request(
    tmp_path,
):
    """Agent must not send a second unaffordable request."""

    client = Mock()

    client.chat.side_effect = [
        make_response(
            tool_calls=[
                make_tool_call(
                    "list_files",
                    {},
                )
            ],
            prompt_tokens=1000,
            completion_tokens=1000,
        ),
        make_response(
            content="Done.",
        ),
    ]

    tracker = CostTracker(
        budget_usd="0.012",
    )

    agent = AgentLoop(
        deepseek_client=client,
        project_directory=tmp_path,
        cost_tracker=tracker,
        max_output_tokens=2000,
        require_usage=True,
    )

    with pytest.raises(BudgetExceededError):
        agent.run({
            "project_name": "Space Fractions"
        })

    assert client.chat.call_count == 1
    assert tracker.get_summary()["requests"] == 1


def test_api_error_stops_agent_without_retry(
    tmp_path,
):
    """AgentLoop does not retry after a client error."""

    client = Mock()

    client.chat.side_effect = RuntimeError(
        "DeepSeek API error: insufficient balance."
    )

    agent = AgentLoop(
        deepseek_client=client,
        project_directory=tmp_path,
        require_usage=True,
    )

    with pytest.raises(
        RuntimeError,
        match="insufficient balance",
    ):
        agent.run({
            "project_name": "Space Fractions"
        })

    assert client.chat.call_count == 1
