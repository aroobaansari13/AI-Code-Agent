
from tools.project_validator import ProjectValidator


def create_sample_project(tmp_path):
    (tmp_path / "main.py").write_text(
        "print('Hello')\n",
        encoding="utf-8"
    )

    (tmp_path / "README.md").write_text(
        "# Sample Project\n",
        encoding="utf-8"
    )

    (tmp_path / "requirements.txt").write_text(
        "",
        encoding="utf-8"
    )

    return ProjectValidator(tmp_path)


def test_required_files_pass(tmp_path):
    validator = create_sample_project(tmp_path)

    result = validator.check_required_files()

    assert result["passed"] is True
    assert result["missing_files"] == []


def test_required_files_missing(tmp_path):
    validator = ProjectValidator(tmp_path)

    result = validator.check_required_files()

    assert result["passed"] is False
    assert "main.py" in result["missing_files"]


def test_valid_python_syntax(tmp_path):
    validator = create_sample_project(tmp_path)

    result = validator.check_python_syntax()

    assert result["passed"] is True
    assert result["files_checked"] == 1


def test_invalid_python_syntax(tmp_path):
    validator = create_sample_project(tmp_path)

    (tmp_path / "main.py").write_text(
        "def broken(:\n",
        encoding="utf-8"
    )

    result = validator.check_python_syntax()

    assert result["passed"] is False


def test_validation_without_execution(tmp_path):
    validator = create_sample_project(tmp_path)

    result = validator.validate(
        run_tests=False
    )

    assert result["overall_passed"] is True
    assert result["tests"]["status"] == "not_run"


def test_missing_tests_directory(tmp_path):
    validator = create_sample_project(tmp_path)

    result = validator.run_tests()

    assert result["passed"] is False
    assert result["status"] == "missing_tests"


def test_save_validation_report(tmp_path):
    validator = create_sample_project(tmp_path)

    report = validator.validate(
        run_tests=False
    )

    report_path = validator.save_report(
        report,
        tmp_path / "validation.json"
    )

    assert report_path.is_file()
