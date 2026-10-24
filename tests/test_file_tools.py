
import pytest

from tools.file_tools import FileTools


@pytest.fixture
def file_tools(tmp_path):
    """Create an isolated project folder for each test."""
    return FileTools(tmp_path)


def test_write_file(file_tools, tmp_path):
    """A file should be created with the correct content."""

    result = file_tools.write_file(
        "game/main.py",
        'print("Hello, Space Fractions!")\n'
    )

    saved_file = tmp_path / "game" / "main.py"

    assert saved_file.exists()
    assert saved_file.read_text(encoding="utf-8") == (
        'print("Hello, Space Fractions!")\n'
    )
    assert result["status"] == "success"


def test_read_file(file_tools):
    """An existing file should return its content."""

    file_tools.write_file(
        "README.md",
        "Space Fractions is a desktop learning game."
    )

    content = file_tools.read_file("README.md")

    assert content == (
        "Space Fractions is a desktop learning game."
    )


def test_edit_file(file_tools):
    """An exact text match should be replaced."""

    file_tools.write_file(
        "config.txt",
        "Difficulty: Easy"
    )

    result = file_tools.edit_file(
        "config.txt",
        "Easy",
        "Medium"
    )

    assert result["status"] == "success"
    assert file_tools.read_file("config.txt") == (
        "Difficulty: Medium"
    )


def test_list_files(file_tools):
    """Files should be listed using relative paths."""

    file_tools.write_file("README.md", "Project information")
    file_tools.write_file("game/main.py", "print('Ready')")

    files = file_tools.list_files()

    assert files == [
        "README.md",
        "game/main.py"
    ]


def test_block_parent_directory(file_tools):
    """The agent must not access parent directories."""

    with pytest.raises(ValueError):
        file_tools.read_file("../private.txt")


def test_block_absolute_path(file_tools, tmp_path):
    """Absolute paths must not be accepted."""

    absolute_path = tmp_path / "secret.txt"

    with pytest.raises(ValueError):
        file_tools.read_file(str(absolute_path))


def test_read_missing_file(file_tools):
    """Reading a missing file should raise an error."""

    with pytest.raises(FileNotFoundError):
        file_tools.read_file("missing.py")


def test_edit_missing_text(file_tools):
    """Editing should fail if the requested text is absent."""

    file_tools.write_file(
        "example.py",
        "print('Hello')"
    )

    with pytest.raises(ValueError):
        file_tools.edit_file(
            "example.py",
            "Goodbye",
            "Welcome"
        )


def test_edit_ambiguous_text(file_tools):
    """Editing should fail when the text appears twice."""

    file_tools.write_file(
        "example.txt",
        "hello hello"
    )

    with pytest.raises(ValueError):
        file_tools.edit_file(
            "example.txt",
            "hello",
            "welcome"
        )


def test_reject_non_text_content(file_tools):
    """Only text content should be written."""

    with pytest.raises(TypeError):
        file_tools.write_file(
            "data.txt",
            {"message": "Hello"}
        )