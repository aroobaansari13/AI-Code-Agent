
import json
from pathlib import Path

from main import MockDeepSeekClient
from agent.agent_loop import AgentLoop
from agent.cost_tracker import CostTracker
from tools.project_validator import ProjectValidator


def generate_mock_project(tmp_path):
    """
    Run the complete mock generation workflow.

    Debugging information is printed to identify
    why files might not be created.
    """

    project_directory = tmp_path / "SpaceFractions_Mock"
    project_directory.mkdir()

    client = MockDeepSeekClient()

    agent = AgentLoop(
        deepseek_client=client,
        project_directory=project_directory,
        cost_tracker=CostTracker(budget_usd=1.00),
        max_iterations=10,
        max_output_tokens=2000,
        max_tool_calls=30,
    )

    architecture = {
        "project_name": "Space Fractions",
        "diagrams": [],
        "requirements": [
            "Create a Python Tkinter application."
        ],
    }

    result = agent.run(architecture)

    # ---------------------------------
    # DEBUGGING INFORMATION
    # ---------------------------------

    print("\n========== DEBUG START ==========")
    print("Agent result:", result)
    print("Mock client calls:", client.call_count)

    generated_files = [
        str(path.relative_to(project_directory))
        for path in project_directory.rglob("*")
        if path.is_file()
    ]

    print("Generated files:", generated_files)
    print("Project directory:", project_directory)
    print("========== DEBUG END ==========\n")

    return project_directory, result


def test_mock_agent_completes(tmp_path):
    project_directory, result = generate_mock_project(
        tmp_path
    )

    assert result["status"] == "completed"
    assert result["iterations"] == 2
    assert result["cost"]["estimated_cost_usd"] == 0.0


def test_mock_agent_creates_required_files(tmp_path):
    project_directory, result = generate_mock_project(
        tmp_path
    )

    expected_files = [
        "main.py",
        "README.md",
        "requirements.txt",
        "tests/test_main.py",
    ]

    for filename in expected_files:
        assert (
            project_directory / filename
        ).is_file()


def test_mock_agent_creates_exactly_four_files(tmp_path):
    project_directory, result = generate_mock_project(
        tmp_path
    )

    actual_files = [
        path
        for path in project_directory.rglob("*")
        if path.is_file()
    ]

    assert len(actual_files) == 4


def test_generated_project_syntax(tmp_path):
    project_directory, result = generate_mock_project(
        tmp_path
    )

    validator = ProjectValidator(project_directory)

    syntax_result = validator.check_python_syntax()

    assert syntax_result["passed"] is True
    assert syntax_result["files_checked"] == 2


def test_generated_project_validation(tmp_path):
    project_directory, result = generate_mock_project(
        tmp_path
    )

    validator = ProjectValidator(project_directory)

    report = validator.validate(
        run_tests=False
    )

    assert report["overall_passed"] is True
    assert report["required_files"]["passed"] is True
    assert report["python_syntax"]["passed"] is True
    assert report["tests"]["status"] == "not_run"


def test_validation_report_saved(tmp_path):
    project_directory, result = generate_mock_project(
        tmp_path
    )

    validator = ProjectValidator(project_directory)

    report = validator.validate(
        run_tests=False
    )

    report_path = validator.save_report(
        report,
        project_directory / "validation_report.json"
    )

    assert report_path.is_file()

    saved_report = json.loads(
        report_path.read_text(encoding="utf-8")
    )

    assert saved_report["overall_passed"] is True


def test_invalid_generated_code_detected(tmp_path):
    project_directory, result = generate_mock_project(
        tmp_path
    )

    (project_directory / "main.py").write_text(
        "def broken(:\n",
        encoding="utf-8"
    )

    validator = ProjectValidator(project_directory)

    report = validator.validate(
        run_tests=False
    )

    assert report["overall_passed"] is False
    assert report["python_syntax"]["passed"] is False


def test_missing_required_file_detected(tmp_path):
    project_directory, result = generate_mock_project(
        tmp_path
    )

    (project_directory / "README.md").unlink()

    validator = ProjectValidator(project_directory)

    report = validator.validate(
        run_tests=False
    )

    assert report["overall_passed"] is False
    assert "README.md" in report[
        "required_files"
    ]["missing_files"]


def test_mock_agent_tool_limit(tmp_path):
    project_directory = tmp_path / "limited_project"
    project_directory.mkdir()

    agent = AgentLoop(
        deepseek_client=MockDeepSeekClient(),
        project_directory=project_directory,
        max_tool_calls=2
    )

    result = agent.run({
        "project_name": "Space Fractions"
    })

    assert result["status"] == "tool_limit"
    assert agent.tool_calls_used == 0

    assert not (
        project_directory / "main.py"
    ).exists()


def test_mock_agent_cost_tracking(tmp_path):
    project_directory, result = generate_mock_project(
        tmp_path
    )

    cost = result["cost"]

    assert cost["requests"] == 2
    assert cost["input_tokens"] == 0
    assert cost["output_tokens"] == 0
    assert cost["estimated_cost_usd"] == 0.0
