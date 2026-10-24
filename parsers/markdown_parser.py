
from pathlib import Path


def read_markdown_file(file_path):
    """Read a Markdown file and return its contents."""

    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(
            f"File not found: {path}"
        )

    if path.suffix.lower() != ".md":
        raise ValueError(
            "Please select a Markdown (.md) file."
        )

    try:
        content = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError(
            f"Unable to read the file as UTF-8: {path.name}"
        ) from error

    if not content.strip():
        raise ValueError(
            f"The selected file is empty: {path.name}"
        )

    return content


def load_architecture_files(documentation_path, diagrams_path):
    """Load the architecture documentation and diagrams."""

    documentation = read_markdown_file(documentation_path)
    diagrams = read_markdown_file(diagrams_path)

    return {
        "documentation": documentation,
        "diagrams": diagrams
    }
