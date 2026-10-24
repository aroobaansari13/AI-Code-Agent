import json
import math
import os
import subprocess
import sys
from pathlib import Path

from agent.cost_tracker import (
    CostTracker,
    BudgetExceededError,
)
from tools.file_tools import FileTools


FILE_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List generated project files.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a generated project file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                },
                "required": ["file_path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a project file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": [
                    "file_path",
                    "content",
                ],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace one exact text match in a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "old_text": {"type": "string"},
                    "new_text": {"type": "string"},
                },
                "required": [
                    "file_path",
                    "old_text",
                    "new_text",
                ],
                "additionalProperties": False,
            },
        },
    },
]


SYSTEM_PROMPT = """
You are AI Code Agent, a software development assistant.

Your task is to generate a working Python Tkinter
application from supplied software architecture data.

Rules:
1. Use the provided architecture as the source of truth.
2. Create project files using the available file tools.
3. Keep all generated files inside the project directory.
4. Produce readable, maintainable Python code.
5. Include a README.md, requirements.txt and tests.
6. Do not request or expose API keys.
7. Do not execute shell commands.
8. Report incomplete work accurately.
"""


class AgentLoop:
    """Run an AI coding agent with controlled file tools."""

    def __init__(
        self,
        deepseek_client,
        project_directory,
        cost_tracker=None,
        max_iterations=10,
        max_output_tokens=2000,
        max_tool_calls=30,
        require_usage=False,
        staged_generation=False,
    ):
        if (
            isinstance(max_iterations, bool)
            or not isinstance(max_iterations, int)
            or max_iterations < 1
        ):
            raise ValueError(
                "max_iterations must be at least 1."
            )

        if (
            isinstance(max_output_tokens, bool)
            or not isinstance(max_output_tokens, int)
            or max_output_tokens < 1
        ):
            raise ValueError(
                "max_output_tokens must be positive."
            )

        if (
            isinstance(max_tool_calls, bool)
            or not isinstance(max_tool_calls, int)
            or max_tool_calls < 1
        ):
            raise ValueError(
                "max_tool_calls must be a positive integer."
            )

        if not isinstance(require_usage, bool):
            raise ValueError(
                "require_usage must be a boolean."
            )

        self.deepseek = deepseek_client
        self.file_tools = FileTools(project_directory)
        self.project_directory = Path(project_directory)

        self.cost_tracker = (
            cost_tracker
            if cost_tracker is not None
            else CostTracker()
        )

        self.max_iterations = max_iterations
        self.max_output_tokens = max_output_tokens
        self.max_tool_calls = max_tool_calls
        self.require_usage = require_usage
        self.staged_generation = staged_generation

        self.tool_calls_used = 0
        self.tool_errors = []

        self.messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            }
        ]

    def execute_tool(self, tool_name, arguments):
        """Execute an allowed file operation."""

        allowed_tools = {
            "list_files": self.file_tools.list_files,
            "read_file": self.file_tools.read_file,
            "write_file": self.file_tools.write_file,
            "edit_file": self.file_tools.edit_file,
        }

        if tool_name not in allowed_tools:
            return {
                "status": "error",
                "message": f"Unknown tool: {tool_name}",
            }

        if not isinstance(arguments, dict):
            return {
                "status": "error",
                "message": (
                    "Tool arguments must be an object."
                ),
            }

        try:
            result = allowed_tools[tool_name](**arguments)

            return {
                "status": "success",
                "result": result,
            }

        except (
            ValueError,
            TypeError,
            FileNotFoundError,
            OSError,
        ) as error:
            return {
                "status": "error",
                "message": str(error),
            }

    def estimate_input_tokens(self):
        """Estimate tokens from messages and tool schemas."""

        serialized_messages = json.dumps(
            self.messages,
            ensure_ascii=False,
        )

        message_tokens = math.ceil(
            len(
                serialized_messages.encode("utf-8")
            ) / 3
        )

        tool_schema_tokens = math.ceil(
            len(
                json.dumps(
                    FILE_TOOLS_SCHEMA
                ).encode("utf-8")
            ) / 3
        )

        return (
            message_tokens
            + tool_schema_tokens
            + 500
        )

    def _run_staged(self, architecture_data):
        """Generate six files one by one, with one retry per file."""
        import ast

        self.tool_calls_used = 0
        self.tool_errors = []

        stages = [
            ("game_logic.py",
             "Implement fraction generation, checking, and score logic."),
            ("main.py",
             "Build a runnable desktop Tkinter UI using game_logic.py. "
             "Define a class named SpaceFractionsApp that takes a root window, "
             "and a main() function called under if __name__ == '__main__'. "
             "Desktop only: ignore web, microservices, Redis, Kubernetes and Docker."),
            ("tests/test_game_logic.py",
             "Write pytest tests matching game_logic.py's real API."),
            ("tests/test_main.py",
             "Write a SHORT pytest file, maximum 60 lines. "
             "Test SpaceFractionsApp without creating a Tkinter window. "
             "Use monkeypatch or unittest.mock. Include only 2-3 focused tests. "
             "IMPORTANT: a normal method is NOT a MagicMock; patch a method "
             "before calling assert_called_once. Do not assert next_question "
             "runs during submit_answer unless main.py explicitly calls it. "
             "Check the real UI flow: submit_answer enables the Next button."),
            ("README.md",
             "Write a concise README under 80 lines covering setup, "
             "running the game, testing, and architecture."),
            ("requirements.txt",
             "List only required external packages. "
             "Include pytest. Do not include tkinter."),
        ]

        architecture_json = json.dumps(architecture_data, ensure_ascii=False)
        completed = []
        requests = 0

        # Resume: keep only existing, non-empty, syntax-valid files.
        for filename, _purpose in stages:
            path = self.project_directory / filename
            if not path.is_file() or not path.read_text(encoding="utf-8").strip():
                continue
            if filename.endswith(".py"):
                try:
                    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                except SyntaxError:
                    continue
            completed.append(filename)

        def outcome(status, message):
            return {
                "status": status,
                "message": message,
                "iterations": requests,
                "files": self.file_tools.list_files(),
                "tool_errors": self.tool_errors.copy(),
                "cost": self.cost_tracker.get_summary(),
            }

        def read_head(path, limit=7000):
            try:
                return (self.project_directory / path).read_text(
                    encoding="utf-8")[:limit]
            except (OSError, UnicodeError):
                return ""

        def api_summary(path):
            try:
                text = (self.project_directory / path).read_text(encoding="utf-8")
                tree = ast.parse(text)
            except Exception:
                return ""
            lines = []
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    lines.append("class " + node.name + ":")
                    if any(isinstance(dec, ast.Name) and dec.id == "dataclass"
                           for dec in node.decorator_list):
                        for field_node in node.body:
                            if isinstance(field_node, ast.AnnAssign) and isinstance(field_node.target, ast.Name):
                                field_name = field_node.target.id
                                required = " (required)" if field_node.value is None else " (default)"
                                lines.append("    field " + field_name + required)
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            lines.append("    def " + item.name
                                         + "(" + ast.unparse(item.args) + ")")
                elif isinstance(node, ast.FunctionDef):
                    lines.append("def " + node.name
                                 + "(" + ast.unparse(node.args) + ")")
            return "\n".join(lines)

        def generate_file(filename, purpose, extra_context=""):
            nonlocal requests
            if requests >= self.max_iterations:
                return "iteration_limit", "Maximum API requests reached."
            if self.tool_calls_used >= self.max_tool_calls:
                return "tool_limit", "Maximum file operations reached."

            if filename.startswith("tests/"):
                purpose += (" Keep tests short: at most 4 focused test functions, "
                            "under 85 lines, no long comments or fixtures. "
                            "Never open a real Tkinter window.")

            related = ""
            if filename == "tests/test_game_logic.py":
                related += "\nExisting game_logic.py:\n" + read_head("game_logic.py")
            else:
                if filename != "game_logic.py" and "game_logic.py" in completed:
                    related += "\ngame_logic.py API:\n" + api_summary("game_logic.py")
                if filename.startswith("tests/") and "main.py" in completed:
                    related += "\nmain.py API:\n" + api_summary("main.py")
                    if filename == "tests/test_main.py":
                        related += "\nActual main.py implementation:\n" + read_head("main.py", 14000)

            self.messages = [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT + (
                        "\nCreate exactly ONE requested file using one write_file tool call. "
                        "Never create other files. Keep the file compact and valid. "
                        "Tests must match actual function signatures and types. "
                        "Before writing a file, inspect the provided APIs of previously generated files. "
                        "Every constructor call must supply all required arguments. "
                        "Every method call must match its actual signature. "
                        "Do not invent class constructors, attributes, or methods. "
                        "Ensure main.py is compatible with game_logic.py. "
                        "Use no tool_choice parameter."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Space Fractions architecture:\n" + architecture_json
                        + "\nAlready generated: " + ", ".join(completed)
                        + "\nCreate or repair ONLY " + filename + ". " + purpose
                        + "\nCall write_file once with file_path=" + filename
                        + ". Do not assume Fraction is an int or float."
                        + related + extra_context
                    ),
                },
            ]
            self.cost_tracker.check_budget(
                self.estimate_input_tokens(), self.max_output_tokens
            )
            response = self.deepseek.chat(
                messages=self.messages,
                tools=[FILE_TOOLS_SCHEMA[2]],
                max_output_tokens=self.max_output_tokens,
            )
            requests += 1

            usage = getattr(response, "usage", None)
            if usage is None or getattr(usage, "prompt_tokens", None) is None:
                if self.require_usage:
                    raise RuntimeError(
                        "Real API response did not include token usage. Generation stopped."
                    )
                return "missing_usage", "API token usage missing."
            if getattr(usage, "completion_tokens", None) is None:
                if self.require_usage:
                    raise RuntimeError("Incomplete API token usage. Generation stopped.")
                return "missing_usage", "API token usage incomplete."
            self.cost_tracker.record_usage(
                usage.prompt_tokens, usage.completion_tokens
            )
            print(filename, "| in:", usage.prompt_tokens,
                  "| out:", usage.completion_tokens,
                  "| finish:", getattr(response.choices[0], "finish_reason", None)
                  if response.choices else None)
            if self.cost_tracker.get_summary()["budget_exceeded"]:
                raise BudgetExceededError("Estimated API budget exceeded; stopped.")

            if not response.choices:
                return "incomplete_response", "API returned no choices."
            choice = response.choices[0]
            if getattr(choice, "finish_reason", None) == "length":
                return "incomplete_response", "Output limit reached for " + filename
            calls = getattr(choice.message, "tool_calls", None) or []
            if len(calls) != 1 or calls[0].function.name != "write_file":
                return "incomplete_response", "Expected one write_file call for " + filename
            try:
                args = json.loads(calls[0].function.arguments)
            except (ValueError, TypeError):
                return "incomplete_response", "Invalid tool arguments for " + filename
            if (
                not isinstance(args, dict)
                or args.get("file_path") != filename
                or not isinstance(args.get("content"), str)
                or not args["content"].strip()
            ):
                return "tool_error", "Wrong path or empty file for " + filename

            result = self.execute_tool("write_file", args)
            self.tool_calls_used += 1
            if result["status"] != "success":
                self.tool_errors.append({
                    "tool": "write_file",
                    "file_path": filename,
                    "message": result["message"],
                })
                return "tool_error", "File write failed for " + filename
            return None, None

        for filename, purpose in stages:
            if filename in completed:
                continue
            extra = ""
            for attempt in range(2):
                status, error = generate_file(filename, purpose, extra)
                print(filename, "attempt", attempt + 1, "->", status or "OK",
                      "| cost so far: $",
                      self.cost_tracker.get_summary()["estimated_cost_usd"])
                if status is None:
                    break
                if status == "tool_error":
                    break
                extra = ("\nThe previous attempt failed: " + str(error)
                         + " Make this file shorter and strictly valid.")
            if status is not None:
                return outcome(status, error)
            completed.append(filename)

        # Static validation never imports or executes AI-generated code.
        def static_issues():
            parsed = {}
            for filename, _purpose in stages:
                if filename.endswith(".py"):
                    try:
                        parsed[filename] = ast.parse(
                            (self.project_directory / filename).read_text(encoding="utf-8"),
                            filename=filename,
                        )
                    except (SyntaxError, OSError, UnicodeError) as exc:
                        return [(filename, "Invalid Python syntax: " + str(exc))]

            game_tree = parsed.get("game_logic.py")
            main_tree = parsed.get("main.py")
            if game_tree is None or main_tree is None:
                return []
            issues = []
            for node in game_tree.body:
                if not isinstance(node, ast.ClassDef) or node.name != "Game":
                    continue
                if not any(
                    isinstance(dec, ast.Name) and dec.id == "dataclass"
                    or isinstance(dec, ast.Attribute) and dec.attr == "dataclass"
                    for dec in node.decorator_list
                ):
                    continue
                required = [
                    item.target.id for item in node.body
                    if isinstance(item, ast.AnnAssign)
                    and isinstance(item.target, ast.Name) and item.value is None
                ]
                for call in ast.walk(main_tree):
                    if not (isinstance(call, ast.Call)
                            and isinstance(call.func, ast.Name)
                            and call.func.id == "Game"):
                        continue
                    if any(isinstance(arg, ast.Starred) for arg in call.args) or any(
                        kw.arg is None for kw in call.keywords
                    ):
                        continue
                    supplied = {kw.arg for kw in call.keywords}
                    missing = [field for field in required[len(call.args):]
                               if field not in supplied]
                    if missing:
                        issues.append(("main.py", "line " + str(call.lineno)
                                       + ": Game constructor missing required arguments: "
                                       + ", ".join(missing)))

            # Detect the observed Fraction-to-str join error when options are
            # sourced from a Fraction-typed collection. Conservative heuristic.
            fraction_collections = set()
            for node in ast.walk(game_tree):
                if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                    annotation = ast.unparse(node.annotation)
                    if "Fraction" in annotation and ("List[" in annotation
                            or "list[" in annotation or "Sequence[" in annotation):
                        fraction_collections.add(node.target.id)
            fraction_vars = set()
            for node in ast.walk(main_tree):
                if isinstance(node, ast.Assign) and isinstance(node.value, ast.Attribute):
                    if node.value.attr in fraction_collections:
                        fraction_vars.update(target.id for target in node.targets
                                             if isinstance(target, ast.Name))
            for node in ast.walk(main_tree):
                if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "join" and node.args):
                    continue
                arg = node.args[0]
                if isinstance(arg, ast.Name) and arg.id in fraction_vars:
                    issues.append(("main.py", "line " + str(node.lineno)
                                   + ": join() receives Fraction objects; convert each to str"))
            return issues

        # At most two paid source repairs. Existing files are kept on API failure.
        for repair_number in range(3):
            issues = static_issues()
            if not issues:
                break
            filename, issue = issues[0]
            # Preserve the original syntax-validation contract: report invalid
            # generated Python rather than making unexpected paid repair calls.
            if issue.startswith("Invalid Python syntax:"):
                return outcome("validation_failed", filename + ": " + issue)
            if repair_number == 2:
                return outcome("validation_failed", filename + ": " + issue
                               + " (repair attempts exhausted)")
            if filename not in ("main.py", "game_logic.py"):
                return outcome("validation_failed", filename + ": " + issue)
            original = read_head(filename, 24000)
            context = ("\nSTATIC VALIDATION ERROR: " + issue
                       + "\nRepair the existing source, not its tests. "
                       + "Preserve all working functionality and public APIs. "
                       + "Do not execute code. Return the COMPLETE corrected file."
                       + "\nExisting " + filename + ":\n" + original
                       + "\nRelated game_logic.py:\n" + read_head("game_logic.py", 18000)
                       + "\nRelated main.py:\n" + read_head("main.py", 18000))
            status, error = generate_file(
                filename, "Repair static validation failure without changing unrelated behavior.",
                context,
            )
            if status is not None:
                return outcome(status, "Source repair failed: " + str(error))

        # Opt-in only: pytest imports and executes AI-generated Python code.
        # This is a local subprocess, NOT a security sandbox.
        if os.getenv("SPACE_FRACTIONS_RUN_GENERATED_TESTS", "").upper() != "YES":
            return outcome(
                "validation_skipped",
                "Six files generated and static compatibility checks passed. "
                "Generated tests were NOT executed. Set SPACE_FRACTIONS_RUN_GENERATED_TESTS=YES "
                "only after reviewing/trusting the generated code; local pytest "
                "execution is NOT sandboxed.",
            )

        def run_generated_tests():
            env = os.environ.copy()
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pytest", "tests", "-q",
                     "-p", "no:cacheprovider"],
                    cwd=str(self.project_directory),
                    env=env, capture_output=True, text=True,
                    timeout=30, check=False,
                )
            except subprocess.TimeoutExpired:
                return False, "Generated tests timed out after 30 seconds."
            except OSError as exc:
                return False, "Could not start pytest: " + str(exc)
            log = (result.stdout + "\n" + result.stderr)[-9000:]
            return result.returncode == 0, log

        passed, report = run_generated_tests()
        if passed:
            return outcome("completed", "Generated tests passed:\n" + report[-1800:])

        # One targeted AI repair, and only for an identifiable failing test file.
        # Do not automatically rewrite the working game to satisfy a bad test.
        failed_test = None
        if "tests/test_main.py" in report or "tests\\test_main.py" in report:
            failed_test = "tests/test_main.py"
        elif ("tests/test_game_logic.py" in report
              or "tests\\test_game_logic.py" in report):
            failed_test = "tests/test_game_logic.py"

        if failed_test is None:
            return outcome("tests_failed", "Tests failed; no safe targeted repair.\n" + report[-3500:])

        original = read_head(failed_test, 7000)
        repair_context = (
            "\nREPAIR TASK: Previous generated test file failed. "
            "Fix test assumptions to match actual source behavior; "
            "do not weaken assertions just to pass. "
            "Only rewrite the requested test file.\n"
            "Previous test file:\n" + original +
            "\nActual pytest failure:\n" + report[-4500:]
        )
        status, error = generate_file(
            failed_test,
            "Repair failing tests to reflect real application behavior; "
            "keep meaningful assertions and avoid real Tk windows.",
            repair_context,
        )
        if status is not None:
            return outcome(status, "Test repair failed: " + str(error))
        try:
            ast.parse((self.project_directory / failed_test).read_text(encoding="utf-8"))
        except (SyntaxError, OSError, UnicodeError) as exc:
            return outcome("validation_failed", "Repaired test has invalid syntax: " + str(exc))
        passed, report = run_generated_tests()
        if passed:
            return outcome("completed", "AI repaired generated tests; tests passed:\n" + report[-1800:])
        return outcome("tests_failed", "Tests still fail after one repair:\n" + report[-3500:])

    def run(self, architecture_data):
        """Process architecture data through the agent loop."""

        if not isinstance(architecture_data, dict):
            raise ValueError(
                "Architecture data must be a dictionary."
            )
        if self.staged_generation:
            return self._run_staged(architecture_data)

        # Reset counters and errors for each run.
        self.tool_calls_used = 0
        self.tool_errors = []

        self.messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": (
                    "Generate the Space Fractions project "
                    "from this architecture:\n"
                    + json.dumps(
                        architecture_data,
                        ensure_ascii=False,
                    )
                ),
            },
        ]

        for iteration in range(self.max_iterations):

            estimated_input_tokens = (
                self.estimate_input_tokens()
            )

            # Check estimated budget before each request.
            # This is not a guaranteed hard spending cap.
            self.cost_tracker.check_budget(
                estimated_input_tokens,
                self.max_output_tokens,
            )

            response = self.deepseek.chat(
                messages=self.messages,
                tools=FILE_TOOLS_SCHEMA,
                max_output_tokens=self.max_output_tokens,
            )

            # Record API-reported token usage.
            usage = getattr(response, "usage", None)

            if usage is None:
                if self.require_usage:
                    raise RuntimeError(
                        "Real API response did not include "
                        "token usage. Generation stopped."
                    )
            else:
                prompt_tokens = getattr(
                    usage, "prompt_tokens", None
                )
                completion_tokens = getattr(
                    usage, "completion_tokens", None
                )

                if (
                    prompt_tokens is None
                    or completion_tokens is None
                ):
                    if self.require_usage:
                        raise RuntimeError(
                            "Incomplete API token usage. "
                            "Generation stopped."
                        )
                else:
                    self.cost_tracker.record_usage(
                        prompt_tokens,
                        completion_tokens,
                    )

            # Stop if reported estimated spending exceeds
            # the configured budget.
            if self.cost_tracker.get_summary()[
                "budget_exceeded"
            ]:
                raise BudgetExceededError(
                    "Estimated API budget exceeded. "
                    "Agent stopped."
                )

            if not response.choices:
                raise RuntimeError(
                    "The model returned no choices."
                )

            choice = response.choices[0]
            message = choice.message

            finish_reason = getattr(
                choice,
                "finish_reason",
                None,
            )

            if finish_reason == "length":
                return {
                    "status": "incomplete_response",
                    "message": (
                        "The model reached its output token "
                        "limit. Generation stopped to avoid "
                        "processing incomplete code."
                    ),
                    "iterations": iteration + 1,
                    "files": self.file_tools.list_files(),
                    "tool_errors": self.tool_errors.copy(),
                    "cost": self.cost_tracker.get_summary(),
                }

            # Preserve assistant tool-call message.
            if hasattr(message, "model_dump"):
                assistant_message = message.model_dump(
                    exclude_none=True
                )
            else:
                assistant_message = {
                    "role": "assistant",
                    "content": message.content,
                }

                if message.tool_calls:
                    assistant_message["tool_calls"] = [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {
                                "name": call.function.name,
                                "arguments": (
                                    call.function.arguments
                                ),
                            },
                        }
                        for call in message.tool_calls
                    ]

            self.messages.append(assistant_message)

            tool_calls = message.tool_calls or []

            # Model finished without requesting tools.
            if not tool_calls:

                # Do not report success if a tool failed.
                if self.tool_errors:
                    return {
                        "status": "tool_error",
                        "message": (
                            "One or more file operations "
                            "failed. Review tool_errors "
                            "before continuing."
                        ),
                        "iterations": iteration + 1,
                        "files": self.file_tools.list_files(),
                        "tool_errors": self.tool_errors.copy(),
                        "cost": self.cost_tracker.get_summary(),
                    }

                return {
                    "status": "completed",
                    "message": message.content or "",
                    "iterations": iteration + 1,
                    "files": self.file_tools.list_files(),
                    "tool_errors": [],
                    "cost": self.cost_tracker.get_summary(),
                }

            # Prevent excessive tool operations.
            if (
                self.tool_calls_used + len(tool_calls)
                > self.max_tool_calls
            ):
                return {
                    "status": "tool_limit",
                    "message": (
                        "Maximum tool-call limit reached. "
                        "Generation stopped."
                    ),
                    "iterations": iteration + 1,
                    "files": self.file_tools.list_files(),
                    "tool_errors": self.tool_errors.copy(),
                    "cost": self.cost_tracker.get_summary(),
                }

            for call in tool_calls:

                self.tool_calls_used += 1

                try:
                    arguments = json.loads(
                        call.function.arguments
                    )

                except (
                    json.JSONDecodeError,
                    TypeError,
                ):
                    arguments = None

                result = self.execute_tool(
                    call.function.name,
                    arguments,
                )

                # Track failed tool operations.
                if result["status"] == "error":
                    self.tool_errors.append({
                        "tool": call.function.name,
                        "arguments": arguments,
                        "message": result["message"],
                    })

                self.messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(
                        result,
                        ensure_ascii=False,
                    ),
                })

        return {
            "status": "iteration_limit",
            "message": (
                "Agent reached the maximum iteration "
                "limit before completing its task."
            ),
            "iterations": self.max_iterations,
            "files": self.file_tools.list_files(),
            "tool_errors": self.tool_errors.copy(),
            "cost": self.cost_tracker.get_summary(),
        }