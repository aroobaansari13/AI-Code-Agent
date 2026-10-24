
import ast
import json
import subprocess
import sys

from datetime import datetime, timezone
from pathlib import Path


class ProjectValidator:
    """Validate generated Python project files."""

    REQUIRED_FILES = [
        "main.py",
        "README.md",
        "requirements.txt"
    ]

    def __init__(self, project_directory):
        self.project_directory = Path(
            project_directory
        ).resolve()

        if not self.project_directory.is_dir():
            raise ValueError(
                "Project directory does not exist."
            )

    def check_required_files(self):
        """Check whether essential project files exist."""

        missing = []

        for filename in self.REQUIRED_FILES:
            file_path = (
                self.project_directory / filename
            )

            if not file_path.is_file():
                missing.append(filename)

        return {
            "passed": len(missing) == 0,
            "missing_files": missing
        }

    def check_python_syntax(self):
        """Check syntax without executing Python files."""

        results = []

        python_files = sorted(
            self.project_directory.rglob("*.py")
        )

        for file_path in python_files:
            relative_path = file_path.relative_to(
                self.project_directory
            ).as_posix()

            try:
                source = file_path.read_text(
                    encoding="utf-8"
                )

                ast.parse(
                    source,
                    filename=relative_path
                )

                results.append({
                    "file": relative_path,
                    "passed": True,
                    "error": None
                })

            except (SyntaxError, UnicodeError, OSError) as error:
                results.append({
                    "file": relative_path,
                    "passed": False,
                    "error": str(error)
                })

        return {
            "passed": (
                len(python_files) > 0
                and all(
                    item["passed"]
                    for item in results
                )
            ),
            "files_checked": len(python_files),
            "results": results
        }

    def run_tests(self, timeout=30):
        """
        Run pytest in a separate process.

        Only use this for trusted code because pytest
        executes the generated project tests.
        """

        tests_directory = (
            self.project_directory / "tests"
        )

        if not tests_directory.is_dir():
            return {
                "passed": False,
                "status": "missing_tests",
                "output": "No tests directory found."
            }

        try:
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    str(tests_directory),
                    "-q"
                ],
                cwd=self.project_directory,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )

            return {
                "passed": completed.returncode == 0,
                "status": (
                    "passed"
                    if completed.returncode == 0
                    else "failed"
                ),
                "output": (
                    completed.stdout
                    + "\n"
                    + completed.stderr
                )[-10000:]
            }

        except subprocess.TimeoutExpired:
            return {
                "passed": False,
                "status": "timeout",
                "output": (
                    "Tests exceeded the time limit."
                )
            }

        except OSError as error:
            return {
                "passed": False,
                "status": "error",
                "output": str(error)
            }

    def validate(self, run_tests=False):
        """Generate a project validation report."""

        required = self.check_required_files()
        syntax = self.check_python_syntax()

        if run_tests:
            tests = self.run_tests()
        else:
            tests = {
                "passed": None,
                "status": "not_run",
                "output": (
                    "Test execution was skipped."
                )
            }

        overall_passed = (
            required["passed"]
            and syntax["passed"]
            and (
                tests["passed"]
                if run_tests
                else True
            )
        )

        return {
            "project_directory": str(
                self.project_directory
            ),
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "required_files": required,
            "python_syntax": syntax,
            "tests": tests,
            "overall_passed": overall_passed
        }

    def save_report(self, report, output_path):
        """Save validation results as JSON."""

        output_path = Path(output_path)
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        output_path.write_text(
            json.dumps(
                report,
                indent=4,
                ensure_ascii=False
            ),
            encoding="utf-8"
        )

        return output_path
