
from pathlib import Path


class FileTools:
    """Manage generated project files inside a safe directory."""

    def __init__(self, project_directory):
        self.project_directory = Path(
            project_directory
        ).resolve()

        if not self.project_directory.is_dir():
            raise ValueError(
                "The project directory does not exist."
            )

    def safe_path(self, file_path):
        """Keep file operations inside the project directory."""

        relative_path = Path(file_path)

        if relative_path.is_absolute():
            raise ValueError(
                "Absolute file paths are not allowed."
            )

        full_path = (
            self.project_directory / relative_path
        ).resolve()

        if not full_path.is_relative_to(self.project_directory):
            raise ValueError(
                "Access outside the project directory is not allowed."
            )

        return full_path

    def list_files(self):
        """List files in the generated project directory."""

        files = []

        for path in self.project_directory.rglob("*"):
            if path.is_file():
                files.append(
                    path.relative_to(
                        self.project_directory
                    ).as_posix()
                )

        return sorted(files)

    def read_file(self, file_path):
        """Read an existing UTF-8 text file."""

        path = self.safe_path(file_path)

        if not path.is_file():
            raise FileNotFoundError(
                f"File not found: {file_path}"
            )

        return path.read_text(encoding="utf-8")

    def write_file(self, file_path, content):
        """Create or overwrite a project file."""

        if not isinstance(content, str):
            raise TypeError(
                "File content must be text."
            )

        path = self.safe_path(file_path)

        path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        path.write_text(
            content,
            encoding="utf-8"
        )

        return {
            "status": "success",
            "file": path.relative_to(
                self.project_directory
            ).as_posix(),
            "message": "File saved successfully."
        }

    def edit_file(self, file_path, old_text, new_text):
        """Replace one exact text occurrence in a file."""

        path = self.safe_path(file_path)

        if not path.is_file():
            raise FileNotFoundError(
                f"File not found: {file_path}"
            )

        if not old_text:
            raise ValueError(
                "The text to replace cannot be empty."
            )

        content = path.read_text(encoding="utf-8")

        occurrences = content.count(old_text)

        if occurrences == 0:
            raise ValueError(
                "The text to replace was not found."
            )

        if occurrences > 1:
            raise ValueError(
                "The text appears more than once. "
                "Provide a more specific match."
            )

        updated_content = content.replace(
            old_text,
            new_text,
            1
        )

        path.write_text(
            updated_content,
            encoding="utf-8"
        )

        return {
            "status": "success",
            "file": path.relative_to(
                self.project_directory
            ).as_posix(),
            "message": "File updated successfully."
        }


if __name__ == "__main__":
    project_root = (
        Path(__file__).resolve().parent.parent
    )

    # Use a separate directory for this local test.
    test_directory = (
        project_root / "output" / "file_tools_test"
    )

    test_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    tools = FileTools(test_directory)

    print("\nTesting AI Code Agent File Tools")
    print("-" * 35)

    # Test 1: Create a file.
    tools.write_file(
        "game/main.py",
        'print("Welcome to Space Fractions!")\n'
    )

    print("1. File created successfully.")

    # Test 2: Read the file.
    content = tools.read_file("game/main.py")

    print("2. File read successfully.")
    print(f"   Content: {content.strip()}")

    # Test 3: Edit the file.
    tools.edit_file(
        "game/main.py",
        "Welcome to Space Fractions!",
        "Let's Play Space Fractions!"
    )

    print("3. File updated successfully.")

    # Test 4: List files.
    files = tools.list_files()

    print("4. Project files:")
    for file in files:
        print(f"   - {file}")

    # Test 5: Block access outside the project.
    try:
        tools.read_file("../architecture_data.json")

    except ValueError:
        print("5. Unsafe file access blocked.")

    print("\nFile tools test completed.")
