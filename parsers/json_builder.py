
import json
import re
from pathlib import Path

from parsers.markdown_parser import load_architecture_files
from parsers.plantuml_parser import parse_plantuml


def extract_sections(content):
    """Extract Markdown headings and their content."""

    sections = []
    current_section = None

    for line in content.splitlines():
        match = re.match(r"^\s*(#{1,6})\s+(.+?)\s*$", line)

        if match:
            if current_section is not None:
                current_section["content"] = (
                    "\n".join(current_section["lines"]).strip()
                )
                del current_section["lines"]
                sections.append(current_section)

            current_section = {
                "heading": match.group(2).strip(),
                "level": len(match.group(1)),
                "lines": []
            }

        elif current_section is not None:
            current_section["lines"].append(line)

    if current_section is not None:
        current_section["content"] = (
            "\n".join(current_section["lines"]).strip()
        )
        del current_section["lines"]
        sections.append(current_section)

    return sections


def extract_requirements(sections):
    """Collect sections containing requirement identifiers."""

    requirements = []
    seen = set()

    requirement_pattern = re.compile(
        r"\b(?:FR|NFR|ASR)[-_ ]?\d+\b",
        flags=re.IGNORECASE
    )

    for section in sections:
        text = (
            section["heading"] + "\n" + section["content"]
        )

        for match in requirement_pattern.finditer(text):
            requirement_id = re.sub(
                r"[-_ ]",
                "-",
                match.group(0).upper()
            )

            if requirement_id in seen:
                continue

            seen.add(requirement_id)

            requirements.append({
                "id": requirement_id,
                "section": section["heading"],
                "description": section["content"].strip()
            })

    return requirements


def build_architecture_data(documentation, diagrams_content):
    """Build structured architecture data from source files."""

    sections = extract_sections(documentation)
    diagrams = parse_plantuml(diagrams_content)

    actors = []
    classes = {}
    components = []
    workflows = []
    states = []
    packages = []
    deployment = []

    for diagram in diagrams:
        diagram_type = diagram["type"]

        if diagram_type == "Use Case":
            actors.extend(
                element
                for element in diagram["elements"]
                if element["type"] == "actor"
            )

        elif diagram_type == "Class":
            classes.update(diagram["classes"])

        elif diagram_type == "Component":
            components.extend(diagram["elements"])

        elif diagram_type in ("Sequence", "Collaboration"):
            workflows.append({
                "name": diagram["name"],
                "type": diagram_type,
                "participants": diagram["elements"],
                "messages": diagram["relationships"]
            })

        elif diagram_type == "Activity":
            workflows.append({
                "name": diagram["name"],
                "type": "Activity",
                "steps": diagram["activities"]
            })

        elif diagram_type == "State":
            states.append({
                "name": diagram["name"],
                "states": diagram["elements"],
                "transitions": diagram["relationships"]
            })

        elif diagram_type == "Package":
            packages.extend(diagram["elements"])

        elif diagram_type in ("Deployment", "Container"):
            deployment.append({
                "name": diagram["name"],
                "type": diagram_type,
                "elements": diagram["elements"],
                "relationships": diagram["relationships"]
            })

    return {
        "project": {
            "name": "Space Fractions",
            "description": (
                "An educational game designed to help "
                "students practice fractions."
            )
        },
        "documentation": {
            "sections": sections
        },
        "requirements": extract_requirements(sections),
        "actors": actors,
        "classes": classes,
        "components": components,
        "workflows": workflows,
        "states": states,
        "packages": packages,
        "deployment": deployment,
        "diagrams": diagrams,
        "assumptions": [],
        "architecture_gaps": []
    }


def save_architecture_json(data, output_path):
    """Save structured architecture data as a JSON file."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False
        )

    return path


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent

    documentation_path = (
        project_root / "inputs" / "Architecture_Documentation.md"
    )

    diagrams_path = (
        project_root / "inputs" / "Architecture_View.md"
    )

    output_path = (
        project_root / "output" / "architecture_data.json"
    )

    try:
        files = load_architecture_files(
            documentation_path,
            diagrams_path
        )

        architecture = build_architecture_data(
            files["documentation"],
            files["diagrams"]
        )

        saved_file = save_architecture_json(
            architecture,
            output_path
        )

        print("\nArchitecture data created successfully.")
        print(f"Saved to: {saved_file}")
        print(
            f"Documentation sections: "
            f"{len(architecture['documentation']['sections'])}"
        )
        print(
            f"Requirements: {len(architecture['requirements'])}"
        )
        print(
            f"Actors: {len(architecture['actors'])}"
        )
        print(
            f"Classes: {len(architecture['classes'])}"
        )
        print(
            f"Components: {len(architecture['components'])}"
        )
        print(
            f"Workflows: {len(architecture['workflows'])}"
        )
        print(
            f"State diagrams: {len(architecture['states'])}"
        )
        print(
            f"Total diagrams: {len(architecture['diagrams'])}"
        )

    except (OSError, ValueError) as error:
        print(f"\nUnable to build architecture data: {error}")
