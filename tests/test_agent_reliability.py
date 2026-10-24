
import json
from types import SimpleNamespace

from agent.agent_loop import AgentLoop


class FakeClient:
    """Return a failed write followed by a final response."""

    def __init__(self):
        self.calls = 0

    def chat(
        self,
        messages,
        tools=None,
        tool_choice=None,
        max_output_tokens=None,
    ):
        self.calls += 1

        if self.calls == 1:
            tool_call = SimpleNamespace(
                id="call_1",
                function=SimpleNamespace(
                    name="write_file",
                    arguments=json.dumps({
                        "path": "main.py",
                        "content": "print('hello')",
                    }),
                ),
            )

            message = SimpleNamespace(
                content=None,
                tool_calls=[tool_call],
            )

            reason = "tool_calls"

        else:
            message = SimpleNamespace(
                content="Project completed.",
                tool_calls=None,
            )

            reason = "stop"

        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=message,
                    finish_reason=reason,
                )
            ],
            usage=SimpleNamespace(
                prompt_tokens=0,
                completion_tokens=0,
            ),
        )


def test_failed_write_does_not_complete(tmp_path):
    agent = AgentLoop(
        deepseek_client=FakeClient(),
        project_directory=tmp_path,
    )

    result = agent.run({
        "project_name": "Space Fractions"
    })

    assert result["status"] == "tool_error"
    assert len(result["tool_errors"]) == 1
    assert result["tool_errors"][0]["tool"] == "write_file"
    assert not (tmp_path / "main.py").exists()


def test_successful_mock_has_no_tool_errors(tmp_path):
    from main import MockDeepSeekClient

    agent = AgentLoop(
        deepseek_client=MockDeepSeekClient(),
        project_directory=tmp_path,
    )

    result = agent.run({
        "project_name": "Space Fractions"
    })

    assert result["status"] == "completed"
    assert result["tool_errors"] == []
    assert (tmp_path / "main.py").is_file()
