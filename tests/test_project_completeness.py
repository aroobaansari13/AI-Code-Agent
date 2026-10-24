
from tools.project_completeness import (
    ProjectCompletenessChecker,
)


def create_valid_project(tmp_path):
    (tmp_path / "tests").mkdir()

    (tmp_path / "main.py").write_text(
        "print('Space Fractions')",
        encoding="utf-8",
    )

    (tmp_path / "README.md").write_text(
        "# Space Fractions",
        encoding="utf-8",
    )

    (tmp_path / "requirements.txt").write_text(
        "# Tkinter is included with Python",
        encoding="utf-8",
    )

    (tmp_path / "tests" / "test_main.py").write_text(
        "def test_example():\n    assert True\n",
        encoding="utf-8",
    )


def test_complete_project_passes(tmp_path):
    create_valid_project(tmp_path)

    checker = ProjectCompletenessChecker(tmp_path)
    result = checker.check()

    assert result["status"] == "passed"
    assert result["missing_files"] == []
    assert result["syntax_errors"] == []


def test_missing_files_detected(tmp_path):
    checker = ProjectCompletenessChecker(tmp_path)
    result = checker.check()

    assert result["status"] == "failed"
    assert "main.py" in result["missing_files"]


def test_empty_file_detected(tmp_path):
    create_valid_project(tmp_path)

    (tmp_path / "README.md").write_text(
        "",
        encoding="utf-8",
    )

    checker = ProjectCompletenessChecker(tmp_path)
    result = checker.check()

    assert result["status"] == "failed"
    assert "README.md" in result["empty_files"]


def test_python_syntax_error_detected(tmp_path):
    create_valid_project(tmp_path)

    (tmp_path / "main.py").write_text(
        "def broken(:\n    pass",
        encoding="utf-8",
    )

    checker = ProjectCompletenessChecker(tmp_path)
    result = checker.check()

    assert result["status"] == "failed"
    assert len(result["syntax_errors"]) == 1
    assert result["syntax_errors"][0]["file"] == "main.py"
