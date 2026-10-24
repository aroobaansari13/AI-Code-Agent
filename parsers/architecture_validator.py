
import json
import re
from pathlib import Path


REQUIRED_DIAGRAM_TYPES = {
    "Use Case",
    "Class",
    "Object",
    "State",
    "Activity",
    "Sequence",
    "Collaboration",
    "Package",
    "Component",
    "Deployment",
    "Container"
}


def make_issue(code, severity, message, recommendation):
    """Create a consistent validation issue."""

    return {
        "code": code,
        "severity": severity,
        "message": message,
        "recommendation": recommendation
    }


def validate_architecture(data):
    """Check architecture completeness and consistency."""

    issues = []
    assumptions = []

    diagrams = data.get("diagrams", [])
    requirements = data.get("requirements", [])
    classes = data.get("classes", {})
    actors = data.get("actors", [])
    components = data.get("components", [])
    workflows = data.get("workflows", [])

    diagram_types = {
        diagram.get("type")
        for diagram in diagrams
    }

    # Check required diagram categories.
    missing_types = sorted(
        REQUIRED_DIAGRAM_TYPES - diagram_types
    )

    if missing_types:
        issues.append(make_issue(
            "ARCH-001",
            "error",
            "Some required diagram types are missing.",
            "Add or review: " + ", ".join(missing_types)
        ))

    # Check whether any diagram was not recognized.
    unknown_diagrams = [
        diagram.get("name", "Unnamed diagram")
        for diagram in diagrams
        if diagram.get("type") == "Unknown"
    ]

    if unknown_diagrams:
        issues.append(make_issue(
            "ARCH-002",
            "warning",
            "Some diagrams could not be classified.",
            "Review: " + ", ".join(unknown_diagrams)
        ))

    # Check extracted requirements.
    if not requirements:
        issues.append(make_issue(
            "REQ-001",
            "error",
            "No requirement identifiers were extracted.",
            "Review the requirements in the architecture documentation."
        ))

    # Check actors.
    if not actors:
        issues.append(make_issue(
            "ACT-001",
            "warning",
            "No actors were identified.",
            "Review the Use Case diagram."
        ))

    # Check classes.
    if not classes:
        issues.append(make_issue(
            "CLS-001",
            "error",
            "No classes were extracted.",
            "Review the Class diagram."
        ))

    # Check components.
    if not components:
        issues.append(make_issue(
            "CMP-001",
            "warning",
            "No software components were identified.",
            "Review the Component diagram."
        ))

    # Check workflows.
    if not workflows:
        issues.append(make_issue(
            "FLOW-001",
            "warning",
            "No workflows were extracted.",
            "Review the Sequence and Activity diagrams."
        ))

    # Check for missing methods used in sequence messages.
    class_methods = {}

    for class_name, class_data in classes.items():
        methods = set()

        for method in class_data.get("methods", []):
            match = re.search(
                r"([A-Za-z_][A-Za-z0-9_]*)\s*\(",
                method
            )

            if match:
                methods.add(match.group(1))

        class_methods[class_name.lower()] = methods

    reported_methods = set()

    for workflow in workflows:
        if workflow.get("type") not in (
            "Sequence",
            "Collaboration"
        ):
            continue

        for message in workflow.get("messages", []):
            target = message.get("target", "").lower()
            label = message.get("label", "")

            method_match = re.match(
                r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(",
                label
            )

            if not method_match:
                continue

            method_name = method_match.group(1)

            if target not in class_methods:
                continue

            if method_name in class_methods[target]:
                continue

            issue_key = (target, method_name)

            if issue_key in reported_methods:
                continue

            reported_methods.add(issue_key)

            issues.append(make_issue(
                "CLS-002",
                "warning",
                (
                    f"The method '{method_name}()' is used "
                    f"by '{target}' in a workflow but is "
                    "not declared in its class."
                ),
                (
                    "Review the class definition and "
                    "confirm the required method."
                )
            ))

    # Check whether the architecture specifies a desktop UI.
    documentation_sections = data.get(
        "documentation", {}
    ).get("sections", [])

    documentation_text = "\n".join(
        section.get("heading", "") + "\n" +
        section.get("content", "")
        for section in documentation_sections
    ).lower()

    if not any(
        keyword in documentation_text
        for keyword in (
            "desktop application",
            "desktop app",
            "tkinter",
            "pyqt",
            "pyside"
        )
    ):
        issues.append(make_issue(
            "UI-001",
            "warning",
            "An explicit desktop UI implementation was not identified.",
            (
                "The evaluation requires a desktop application. "
                "Document the chosen desktop technology and "
                "any changes to the original architecture."
            )
        ))

    # Review scoring details without inventing a scoring rule.
    if "score" in documentation_text:
        if not re.search(
            r"\b\d+\s+points?\b|"
            r"\b\d+\s+marks?\b|"
            r"\b\d+\s+points?\s+per\s+correct\b",
            documentation_text
        ):
            issues.append(make_issue(
                "GAME-001",
                "info",
                "A precise scoring rule was not automatically identified.",
                (
                    "Confirm how correct and incorrect answers "
                    "affect the player's score."
                )
            ))

    assumptions.append({
        "topic": "Desktop implementation",
        "status": "proposed",
        "description": (
            "A Python desktop interface is a possible "
            "implementation approach. This is not a "
            "requirement extracted from the diagrams."
        )
    })

    return {
        "valid": not any(
            issue["severity"] == "error"
            for issue in issues
        ),
        "summary": {
            "diagrams": len(diagrams),
            "diagram_categories": len(diagram_types),
            "requirements": len(requirements),
            "classes": len(classes),
            "components": len(components),
            "workflows": len(workflows),
            "errors": sum(
                issue["severity"] == "error"
                for issue in issues
            ),
            "warnings": sum(
                issue["severity"] == "warning"
                for issue in issues
            ),
            "information": sum(
                issue["severity"] == "info"
                for issue in issues
            )
        },
        "issues": issues,
        "assumptions": assumptions
    }


def save_validation_report(report, output_path):
    """Save the validation results as JSON."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(
            report,
            file,
            indent=2,
            ensure_ascii=False
        )

    return path


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent

    architecture_path = (
        project_root / "output" / "architecture_data.json"
    )

    report_path = (
        project_root / "output" / "validation_report.json"
    )

    try:
        with architecture_path.open(
            "r",
            encoding="utf-8"
        ) as file:
            architecture = json.load(file)

        report = validate_architecture(architecture)

        saved_path = save_validation_report(
            report,
            report_path
        )

        print("\nArchitecture Validation Report")
        print("-" * 35)

        print(
            f"Diagrams: {report['summary']['diagrams']}"
        )
        print(
            f"Errors: {report['summary']['errors']}"
        )
        print(
            f"Warnings: {report['summary']['warnings']}"
        )
        print(
            f"Information: {report['summary']['information']}"
        )

        print("\nFindings:")

        if not report["issues"]:
            print("No issues detected by the current checks.")

        for issue in report["issues"]:
            print(
                f"\n[{issue['severity'].upper()}] "
                f"{issue['code']}"
            )
            print(issue["message"])
            print(
                f"Recommendation: {issue['recommendation']}"
            )

        print(f"\nReport saved to: {saved_path}")

    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"\nValidation failed: {error}")
