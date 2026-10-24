
from pathlib import Path
import ast


class ProjectCompletenessChecker:
    """Check whether a generated project has its basic files."""

    REQUIRED_FILES = (
        "main.py",
        "README.md",
        "requirements.txt",
        "tests/test_main.py",
    )

    def __init__(self, project_directory):
        self.project_directory = Path(project_directory)

    def check(self):
        missing_files = []
        empty_files = []
        syntax_errors = []
        checked_files = []

        root = self.project_directory.resolve()

        for relative_path in self.REQUIRED_FILES:
            file_path = root / relative_path

            if not file_path.is_file():
                missing_files.append(relative_path)
                continue

            checked_files.append(relative_path)

            if file_path.stat().st_size == 0:
                empty_files.append(relative_path)
                continue

            if file_path.suffix == ".py":
                try:
                    source = file_path.read_text(
                        encoding="utf-8"
                    )
                    ast.parse(
                        source,
                        filename=str(file_path)
                    )
                except (SyntaxError, UnicodeError) as error:
                    syntax_errors.append({
                        "file": relative_path,
                        "error": str(error),
                    })

        passed = (
            not missing_files
            and not empty_files
            and not syntax_errors
        )

        return {
            "status": "passed" if passed else "failed",
            "required_files": list(self.REQUIRED_FILES),
            "checked_files": checked_files,
            "missing_files": missing_files,
            "empty_files": empty_files,
            "syntax_errors": syntax_errors,
        }
