
import re
from pathlib import Path


def extract_plantuml_blocks(content):
    """Extract complete PlantUML blocks from Markdown."""

    pattern = r"@startuml\s+([^\r\n]*)(.*?)@enduml"

    matches = re.finditer(
        pattern,
        content,
        flags=re.DOTALL | re.IGNORECASE
    )

    blocks = []

    for match in matches:
        blocks.append({
            "name": match.group(1).strip(),
            "source": match.group(2).strip()
        })

    return blocks


def identify_diagram_type(name, content):
    """Identify a diagram using its declared name and content."""

    name_lower = name.lower()

    diagram_types = {
        "usecase": "Use Case",
        "class": "Class",
        "object": "Object",
        "state": "State",
        "activity": "Activity",
        "sequence": "Sequence",
        "collaboration": "Collaboration",
        "package": "Package",
        "component": "Component",
        "deployment": "Deployment",
        "container": "Container"
    }

    for keyword, diagram_type in diagram_types.items():
        if name_lower.startswith(keyword):
            return diagram_type

    # Fallback for diagrams without descriptive names.
    if re.search(r"^\s*usecase\s+", content, re.I | re.M):
        return "Use Case"

    if re.search(r"^\s*class\s+", content, re.I | re.M):
        return "Class"

    if re.search(r"^\s*object\s+", content, re.I | re.M):
        return "Object"

    if re.search(r"^\s*node\s+", content, re.I | re.M):
        return "Deployment"

    if re.search(r"^\s*package\s+", content, re.I | re.M):
        return "Package"

    if re.search(r"^\s*state\s+", content, re.I | re.M):
        return "State"

    if re.search(r"^\s*participant\s+", content, re.I | re.M):
        return "Sequence"

    if re.search(r"^\s*start\s*$", content, re.I | re.M):
        return "Activity"

    return "Unknown"


def extract_elements(content):
    """Extract actors, classes, participants and other elements."""

    pattern = (
        r'^\s*(actor|usecase|class|object|state|'
        r'participant|package|component|artifact|'
        r'node|container)\s+'
        r'(?:"([^"]+)"|([A-Za-z_][A-Za-z0-9_]*))'
        r'(?:\s+as\s+(?:"([^"]+)"|'
        r'(\([A-Za-z_][A-Za-z0-9_]*\))|'
        r'([A-Za-z_][A-Za-z0-9_]*)))?'
    )

    elements = []

    for match in re.finditer(
        pattern,
        content,
        flags=re.MULTILINE | re.IGNORECASE
    ):
        element_type = match.group(1).lower()
        name = match.group(2) or match.group(3)

        alias = (
            match.group(4)
            or match.group(5)
            or match.group(6)
        )

        elements.append({
            "type": element_type,
            "name": name,
            "alias": alias
        })

    return elements


def extract_relationships(content):
    """Extract UML links, associations and messages."""

    relationships = []

    arrow_pattern = (
        r'^\s*'
        r'("[^"]+"|\([A-Za-z_][A-Za-z0-9_]*\)|'
        r'[A-Za-z_][A-Za-z0-9_]*)'
        r'\s*'
        r'(--\*|-->|->>|<--|->|<-|--|\.\.>)'
        r'\s*'
        r'("[^"]+"|\([A-Za-z_][A-Za-z0-9_]*\)|'
        r'[A-Za-z_][A-Za-z0-9_]*)'
        r'(?:\s*:\s*(.*))?'
        r'\s*$'
    )

    for match in re.finditer(
        arrow_pattern,
        content,
        flags=re.MULTILINE
    ):
        relationships.append({
            "source": match.group(1).strip('"()'),
            "relationship": match.group(2),
            "target": match.group(3).strip('"()'),
            "label": (match.group(4) or "").strip()
        })

    return relationships


def extract_activities(content):
    """Extract activity steps and decisions."""

    activities = []

    for line in content.splitlines():
        line = line.strip()

        if line.startswith(":") and line.endswith(";"):
            activities.append({
                "type": "action",
                "text": line[1:-1].strip()
            })

        elif line.lower().startswith("if "):
            activities.append({
                "type": "decision",
                "text": line
            })

        elif line.lower().startswith("else"):
            activities.append({
                "type": "branch",
                "text": line
            })

    return activities


def extract_class_members(content):
    """Extract attributes and methods from class bodies."""

    classes = {}

    class_pattern = (
        r'\bclass\s+([A-Za-z_][A-Za-z0-9_]*)'
        r'\s*\{(.*?)\}'
    )

    for match in re.finditer(
        class_pattern,
        content,
        flags=re.DOTALL
    ):
        class_name = match.group(1)
        body = match.group(2)

        attributes = []
        methods = []

        for line in body.splitlines():
            line = line.strip()

            if not line:
                continue

            if "(" in line and ")" in line:
                methods.append(line)
            else:
                attributes.append(line)

        classes[class_name] = {
            "attributes": attributes,
            "methods": methods
        }

    return classes


def parse_plantuml(content):
    """Convert PlantUML diagrams into structured data."""

    blocks = extract_plantuml_blocks(content)
    diagrams = []

    for index, block in enumerate(blocks, start=1):
        diagram_type = identify_diagram_type(
            block["name"],
            block["source"]
        )

        diagrams.append({
            "id": index,
            "name": block["name"],
            "type": diagram_type,
            "elements": extract_elements(block["source"]),
            "relationships": extract_relationships(
                block["source"]
            ),
            "activities": extract_activities(
                block["source"]
            ) if diagram_type == "Activity" else [],
            "classes": extract_class_members(
                block["source"]
            ) if diagram_type == "Class" else {},
            "source": block["source"]
        })

    return diagrams


if __name__ == "__main__":
    input_file = (
        Path(__file__).resolve().parent.parent
        / "inputs"
        / "Architecture_View.md"
    )

    if not input_file.is_file():
        print(f"File not found: {input_file}")

    else:
        content = input_file.read_text(
            encoding="utf-8-sig"
        )

        diagrams = parse_plantuml(content)

        print(
            f"\nPlantUML diagrams found: {len(diagrams)}\n"
        )

        for diagram in diagrams:
            print(
                f"Diagram {diagram['id']}: "
                f"{diagram['type']} "
                f"({diagram['name']})"
            )

            print(
                f"  Elements: {len(diagram['elements'])}"
            )

            print(
                f"  Relationships: "
                f"{len(diagram['relationships'])}"
            )

            if diagram["type"] == "Activity":
                print(
                    f"  Activities: "
                    f"{len(diagram['activities'])}"
                )

            if diagram["type"] == "Class":
                print(
                    f"  Classes with members: "
                    f"{len(diagram['classes'])}"
                )
