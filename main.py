import os
import json
import queue
import sys
import threading
import tkinter as tk

from decimal import Decimal, InvalidOperation
from pathlib import Path
from types import SimpleNamespace
from tkinter import filedialog, messagebox, ttk

from dotenv import load_dotenv

from agent.agent_loop import AgentLoop
from agent.deepseek_client import DeepSeekClient
from agent.cost_tracker import (
    CostTracker,
    BudgetExceededError,
)

from parsers.markdown_parser import (
    load_architecture_files,
)
from parsers.json_builder import (
    build_architecture_data,
    save_architecture_json,
)
from parsers.architecture_validator import (
    validate_architecture,
    save_validation_report,
)

from tools.project_validator import ProjectValidator
from tools.project_completeness import (
    ProjectCompletenessChecker,
)


# When packaged with PyInstaller, files live next to the .exe.
if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(sys.executable).resolve().parent
else:
    PROJECT_ROOT = Path(__file__).resolve().parent

# Default input files for both Python and packaged EXE
INPUTS_DIR = (
    PROJECT_ROOT / "inputs"
    if (PROJECT_ROOT / "inputs").is_dir()
    else PROJECT_ROOT.parent / "inputs"
)

load_dotenv(PROJECT_ROOT / ".env")

MODEL_NAME = os.getenv(
    "DEEPSEEK_MODEL",
    "deepseek-v4-pro",
)

PROFESSOR_BUDGET = Decimal("1.00")
SAFETY_BUDGET = Decimal("0.80")

MAX_OUTPUT_TOKENS = 6000
MAX_ITERATIONS = 14
MAX_TOOL_CALLS = 30


class MockDeepSeekClient:
    """Generate a small demo without API charges."""

    def __init__(self):
        self.call_count = 0

    def chat(
        self,
        messages,
        tools=None,
        tool_choice=None,
        max_output_tokens=None,
    ):
        self.call_count += 1

        usage = SimpleNamespace(
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
        )

        if self.call_count == 1:
            files = {
                "main.py": (
                    "import tkinter as tk\n\n"
                    "def create_window():\n"
                    "    root = tk.Tk()\n"
                    "    root.title('Space Fractions')\n"
                    "    tk.Label(\n"
                    "        root,\n"
                    "        text='Space Fractions'\n"
                    "    ).pack(pady=12)\n"
                    "    tk.Label(\n"
                    "        root,\n"
                    "        text='Mock project generated successfully.'\n"
                    "    ).pack(pady=8)\n"
                    "    return root\n\n"
                    "if __name__ == '__main__':\n"
                    "    create_window().mainloop()\n"
                ),
                "README.md": (
                    "# Space Fractions Mock\n\n"
                    "This is a mock-generated Tkinter demo.\n"
                    "It is not the complete educational game.\n"
                ),
                "requirements.txt": (
                    "# Tkinter is included with Python.\n"
                ),
                "tests/test_main.py": (
                    "from pathlib import Path\n\n"
                    "def test_main_exists():\n"
                    "    root = Path(__file__).resolve().parents[1]\n"
                    "    assert (root / 'main.py').is_file()\n"
                ),
            }

            calls = []

            for index, (filename, content) in enumerate(
                files.items(),
                start=1,
            ):
                calls.append(
                    SimpleNamespace(
                        id=f"mock_tool_{index}",
                        type="function",
                        function=SimpleNamespace(
                            name="write_file",
                            arguments=json.dumps({
                                "file_path": filename,
                                "content": content,
                            }),
                        ),
                    )
                )

            message = SimpleNamespace(
                role="assistant",
                content=None,
                tool_calls=calls,
            )
            finish_reason = "tool_calls"

        else:
            message = SimpleNamespace(
                role="assistant",
                content="Mock project files generated.",
                tool_calls=None,
            )
            finish_reason = "stop"

        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=message,
                    finish_reason=finish_reason,
                )
            ],
            usage=usage,
        )


class AICodeAgentApp:

    def __init__(self, root):
        self.root = root
        self.root.title(
            "AI Code Agent — Space Fractions"
        )
        self.root.geometry("860x850")
        self.root.minsize(760, 760)

        self.documentation_path = tk.StringVar(
            value=str(
                INPUTS_DIR
                / "Architecture_Documentation.md"
            )
        )

        self.diagrams_path = tk.StringVar(
            value=str(
                INPUTS_DIR
                / "Architecture_View.md"
            )
        )

        self.output_path = tk.StringVar(
            value=str(Path.home() / "AI-Code-Agent-Projects")
        )

        self.api_key = tk.StringVar(
            value=os.getenv("DEEPSEEK_API_KEY", "")
        )

        self.input_price = tk.StringVar(
            value=os.getenv("DEEPSEEK_INPUT_PRICE_PER_MILLION", "")
        )
        self.output_price = tk.StringVar(
            value=os.getenv("DEEPSEEK_OUTPUT_PRICE_PER_MILLION", "")
        )
        self.pricing_verified = tk.BooleanVar(
            value=os.getenv("DEEPSEEK_PRICING_VERIFIED", "") == "YES"
        )

        self.mock_mode = tk.BooleanVar(value=True)

        self.events = queue.Queue()
        self.is_running = False

        self.create_interface()
        self.root.after(100, self.process_events)

    def create_interface(self):
        frame = ttk.Frame(
            self.root,
            padding=20,
        )
        frame.pack(
            fill="both",
            expand=True,
        )

        ttk.Label(
            frame,
            text="AI Code Agent",
            font=("Segoe UI", 20, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            frame,
            text=(
                "Generate and validate Space Fractions "
                "from architecture documents."
            ),
        ).pack(
            anchor="w",
            pady=(4, 18),
        )

        self._file_row(
            frame,
            "Architecture Documentation",
            self.documentation_path,
        )

        self._file_row(
            frame,
            "Architecture Diagrams",
            self.diagrams_path,
        )

        self._file_row(
            frame,
            "Output Folder",
            self.output_path,
            folder=True,
        )

        ttk.Label(
            frame,
            text="DeepSeek API Key",
        ).pack(
            anchor="w",
            pady=(12, 3),
        )

        ttk.Entry(
            frame,
            textvariable=self.api_key,
            show="*",
        ).pack(fill="x")

        pricing_frame = ttk.LabelFrame(
            frame, text="Real Mode Pricing (USD per 1 million tokens)", padding=8
        )
        pricing_frame.pack(fill="x", pady=(10, 4))
        pricing_row = ttk.Frame(pricing_frame)
        pricing_row.pack(fill="x")
        ttk.Label(pricing_row, text="Input price").grid(row=0, column=0, sticky="w")
        ttk.Entry(pricing_row, textvariable=self.input_price, width=16).grid(
            row=1, column=0, padx=(0, 16), sticky="ew"
        )
        ttk.Label(pricing_row, text="Output price").grid(row=0, column=1, sticky="w")
        ttk.Entry(pricing_row, textvariable=self.output_price, width=16).grid(
            row=1, column=1, sticky="ew"
        )
        pricing_row.columnconfigure(0, weight=1)
        pricing_row.columnconfigure(1, weight=1)
        ttk.Checkbutton(
            pricing_frame,
            text="I verified these prices for the selected DeepSeek model",
            variable=self.pricing_verified,
        ).pack(anchor="w", pady=(6, 0))

        ttk.Checkbutton(
            frame,
            text="Mock Mode — no API charges",
            variable=self.mock_mode,
        ).pack(
            anchor="w",
            pady=(12, 4),
        )

        ttk.Label(
            frame,
            text=(
                f"Model: {MODEL_NAME} | "
                "Professor budget: $1.00 | "
                "Safety target: $0.80"
            ),
        ).pack(
            anchor="w",
            pady=(0, 12),
        )

        self.generate_button = ttk.Button(
            frame,
            text="Generate Project",
            command=self.generate_project,
        )
        self.generate_button.pack(
            fill="x",
            pady=(0, 12),
        )

        self.progress = ttk.Progressbar(
            frame,
            mode="determinate",
            maximum=100,
        )
        self.progress.pack(
            fill="x",
            pady=(0, 12),
        )

        ttk.Label(
            frame,
            text="Activity Log",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w")

        log_frame = ttk.Frame(frame)
        log_frame.pack(
            fill="both",
            expand=True,
            pady=(6, 0),
        )

        self.log_text = tk.Text(
            log_frame,
            wrap="word",
            state="disabled",
            height=15,
        )
        self.log_text.pack(
            side="left",
            fill="both",
            expand=True,
        )

        scrollbar = ttk.Scrollbar(
            log_frame,
            orient="vertical",
            command=self.log_text.yview,
        )
        scrollbar.pack(
            side="right",
            fill="y",
        )

        self.log_text.configure(
            yscrollcommand=scrollbar.set
        )

    def _file_row(
        self,
        parent,
        label,
        variable,
        folder=False,
    ):
        ttk.Label(
            parent,
            text=label,
        ).pack(
            anchor="w",
            pady=(7, 3),
        )

        row = ttk.Frame(parent)
        row.pack(fill="x")

        ttk.Entry(
            row,
            textvariable=variable,
        ).pack(
            side="left",
            fill="x",
            expand=True,
        )

        if folder:
            command = lambda: self.browse_output(
                variable
            )
        else:
            command = lambda: self.browse_file(
                variable
            )

        ttk.Button(
            row,
            text="Browse",
            command=command,
        ).pack(
            side="left",
            padx=(8, 0),
        )

    def browse_file(self, variable):
        path = filedialog.askopenfilename(
            title="Select Architecture File",
            filetypes=[
                ("Markdown Files", "*.md"),
                ("All Files", "*.*"),
            ],
        )
        if path:
            variable.set(path)

    def browse_output(self, variable=None):
        path = filedialog.askdirectory(
            title="Select Output Folder"
        )
        if path:
            if variable is None:
                self.output_path.set(path)
            else:
                variable.set(path)

    def add_log(self, message):
        self.log_text.configure(state="normal")
        self.log_text.insert(
            "end",
            str(message) + "\n",
        )
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def update_progress(self, value):
        self.progress["value"] = value

    def emit_log(self, message):
        self.events.put(("log", str(message)))

    def emit_progress(self, value):
        self.events.put(("progress", value))

    def process_events(self):
        try:
            while True:
                kind, payload = (
                    self.events.get_nowait()
                )

                if kind == "log":
                    self.add_log(payload)

                elif kind == "progress":
                    self.update_progress(payload)

                elif kind == "success":
                    self.is_running = False
                    self.generate_button.configure(
                        state="normal"
                    )
                    messagebox.showinfo(
                        "Generation Complete",
                        payload,
                    )

                elif kind == "error":
                    self.is_running = False
                    self.generate_button.configure(
                        state="normal"
                    )
                    messagebox.showerror(
                        "Generation Failed",
                        payload,
                    )

        except queue.Empty:
            pass

        self.root.after(
            100,
            self.process_events,
        )

    def generate_project(self):
        if self.is_running:
            return

        documentation = Path(
            self.documentation_path.get()
        ).expanduser()

        diagrams = Path(
            self.diagrams_path.get()
        ).expanduser()

        output_text = (
            self.output_path.get().strip()
        )

        if not output_text:
            messagebox.showerror(
                "Missing Output",
                "Select an output folder.",
            )
            return

        output = Path(
            output_text
        ).expanduser()

        mock = self.mock_mode.get()
        key = self.api_key.get().strip()

        if not documentation.is_file():
            messagebox.showerror(
                "Missing File",
                "Select a valid architecture documentation file.",
            )
            return

        if not diagrams.is_file():
            messagebox.showerror(
                "Missing File",
                "Select a valid architecture diagrams file.",
            )
            return

        if not mock:
            if not key:
                messagebox.showerror(
                    "Missing API Key",
                    "Enter a valid DeepSeek API key.",
                )
                return

            if not self.real_mode_ready():
                messagebox.showwarning(
                    "Real Mode Safety Lock",
                    "Real API mode is not configured yet.\n\n"
                    "Verify the model and token prices, "
                    "then enter valid prices above and "
                    "check the verification box.",
                )
                return

            confirmed = messagebox.askyesno(
                "Confirm Paid API Usage",
                "This will send paid requests to DeepSeek.\n\n"
                "The project has a $1 professor budget.\n"
                "The internal safety target is $0.80 per run.\n\n"
                "Estimated tracking is not a hard "
                "provider spending cap.\n\n"
                "Do you want to continue?",
            )

            if not confirmed:
                return

        self.is_running = True

        self.generate_button.configure(
            state="disabled"
        )

        self.update_progress(0)
        self.add_log(
            "Starting project generation..."
        )

        threading.Thread(
            target=self.process_project,
            args=(
                documentation,
                diagrams,
                output,
                mock,
                key,
            ),
            daemon=True,
        ).start()

    def _verified_prices(self):
        """Return verified, finite nonnegative prices from the GUI."""
        if not self.pricing_verified.get():
            raise ValueError("Confirm that DeepSeek model pricing is verified.")
        try:
            input_price = Decimal(self.input_price.get().strip())
            output_price = Decimal(self.output_price.get().strip())
        except (InvalidOperation, ValueError):
            raise ValueError("Enter numeric input and output prices.") from None
        if not all(p.is_finite() and p > 0 for p in (input_price, output_price)):
            raise ValueError("Both prices must be positive finite numbers.")
        return str(input_price), str(output_price)

    def real_mode_ready(self):
        """Require verified GUI pricing; no .env is needed on another PC."""
        try:
            self._verified_prices()
            return True
        except ValueError:
            return False

    def create_cost_tracker(self, mock=False):
        if mock:
            return CostTracker(budget_usd="1.00")

        input_price, output_price = self._verified_prices()
        # Save estimated spending under the user's profile, not beside the EXE.
        # This location works even if the EXE is in a protected directory.
        legacy_state = PROJECT_ROOT / "output" / "api_budget.json"
        state_file = (
            legacy_state if legacy_state.is_file()
            else Path.home() / ".ai-code-agent" / "api_budget.json"
        )
        state_file.parent.mkdir(parents=True, exist_ok=True)
        return CostTracker(
            budget_usd=str(SAFETY_BUDGET),
            input_price=input_price,
            output_price=output_price,
            state_file=state_file,
        )

    def create_project_directory(
        self,
        output_folder,
        mock,
    ):
        output_folder = Path(output_folder)

        output_folder.mkdir(
            parents=True,
            exist_ok=True,
        )

        resume_dir = os.getenv(
            "SPACE_FRACTIONS_RESUME_DIR", ""
        ).strip()

        if not mock and resume_dir:
            project = Path(resume_dir).expanduser().resolve()
            # Only resume a generated child of the selected output directory.
            if (
                project.parent != output_folder.resolve()
                or not project.name.startswith("SpaceFractions_")
            ):
                raise ValueError(
                    "Resume directory must be a SpaceFractions_ "
                    "child of Output Folder."
                )
            return project

        if mock:
            project = output_folder / "SpaceFractions_Mock"
        else:
            # Fixed folder: a failed run resumes instead of starting over.
            project = output_folder / "SpaceFractions_project"

        project.mkdir(
            parents=True,
            exist_ok=True,
        )

        return project

    def check_project_completeness(
        self,
        project_directory,
    ):
        self.emit_log(
            "Checking generated project completeness..."
        )

        checker = ProjectCompletenessChecker(
            project_directory
        )

        report = checker.check()

        report_path = (
            Path(project_directory)
            / "completeness_report.json"
        )

        report_path.write_text(
            json.dumps(
                report,
                indent=4,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        if report["status"] == "passed":
            self.emit_log(
                "PASS: Project completeness check."
            )
            self.emit_log(
                f"Checked {len(report['checked_files'])} "
                "required files."
            )
        else:
            self.emit_log(
                "FAIL: Project completeness check."
            )

            for filename in report["missing_files"]:
                self.emit_log(
                    f"Missing file: {filename}"
                )

            for filename in report["empty_files"]:
                self.emit_log(
                    f"Empty file: {filename}"
                )

            for error in report["syntax_errors"]:
                self.emit_log(
                    f"Syntax error in {error['file']}: "
                    f"{error['error']}"
                )

        self.emit_log(
            f"Completeness report saved: {report_path}"
        )

        return report

    def process_project(
        self,
        documentation,
        diagrams,
        output,
        mock,
        key,
    ):
        try:
            self.emit_log(
                "Loading architecture documentation..."
            )
            self.emit_progress(10)

            loaded_data = load_architecture_files(
                documentation,
                diagrams,
            )

            if not isinstance(loaded_data, dict):
                raise ValueError(
                    "Architecture loader must return a dictionary."
                )

            if (
                "documentation" not in loaded_data
                or "diagrams" not in loaded_data
            ):
                raise ValueError(
                    "Architecture loader must return "
                    "'documentation' and 'diagrams'."
                )

            architecture = build_architecture_data(
                loaded_data["documentation"],
                loaded_data["diagrams"],
            )

            self.emit_log(
                "Architecture parsed successfully."
            )

            output = Path(output)
            output.mkdir(
                parents=True,
                exist_ok=True,
            )

            save_architecture_json(
                architecture,
                output / "architecture_data.json",
            )

            self.emit_progress(30)

            validation = validate_architecture(
                architecture
            )

            save_validation_report(
                validation,
                output / "validation_report.json",
            )

            if validation.get("errors"):
                raise RuntimeError(
                    "Architecture validation failed. "
                    "Review validation_report.json."
                )

            self.emit_log(
                "Architecture validation passed."
            )
            self.emit_progress(45)

            if mock:
                client = MockDeepSeekClient()
                tracker = self.create_cost_tracker(
                    mock=True
                )
                self.emit_log(
                    "Running Mock Mode."
                )
            else:
                if not self.real_mode_ready():
                    raise RuntimeError(
                        "Real Mode safety configuration "
                        "is incomplete."
                    )

                client = DeepSeekClient(
                    api_key=key,
                    model=MODEL_NAME,
                )

                tracker = self.create_cost_tracker(
                    mock=False
                )

                self.emit_log(
                    f"Running Real Mode: {MODEL_NAME}"
                )
                self.emit_log(
                    "Cost estimates are persisted across runs. "
                    "Check the DeepSeek Usage page for actual total."
                )

            project_directory = (
                self.create_project_directory(
                    output,
                    mock=mock,
                )
            )

            self.emit_log(
                f"Project directory: "
                f"{project_directory}"
            )

            agent = AgentLoop(
                deepseek_client=client,
                project_directory=project_directory,
                cost_tracker=tracker,
                max_iterations=MAX_ITERATIONS,
                max_output_tokens=MAX_OUTPUT_TOKENS,
                max_tool_calls=MAX_TOOL_CALLS,
                require_usage=not mock,
                staged_generation=not mock,
            )

            self.emit_log(
                "Generating project files..."
            )

            result = agent.run(architecture)

            self.emit_log(
                f"Agent status: {result['status']}"
            )

            self.emit_log(
                f"Estimated API cost: "
                f"${tracker.get_summary()['estimated_cost_usd']:.6f}"
            )

            if result["status"] not in (
                "completed",
                "validation_skipped",
            ):
                raise RuntimeError(
                    "Agent did not complete: "
                    f"{result['status']}. "
                    f"{result.get('message', '')}"
                )

            if result["status"] == "validation_skipped":
                self.emit_log(
                    "NOTICE: Generated tests NOT executed; "
                    "syntax-only validation."
                )
            elif result["status"] == "completed" and not mock:
                self.emit_log(result.get("message", "Generated tests passed."))

            self.emit_progress(70)

            completeness = (
                self.check_project_completeness(
                    project_directory
                )
            )

            if completeness["status"] != "passed":
                raise RuntimeError(
                    "Generated project is incomplete. "
                    "Review completeness_report.json."
                )

            self.emit_progress(85)

            validator = ProjectValidator(
                project_directory
            )

            project_report = validator.validate(
                run_tests=False
            )

            validator.save_report(
                project_report,
                project_directory
                / "validation_report.json",
            )

            if (
                project_report.get("status") == "failed"
                or project_report.get("valid") is False
            ):
                raise RuntimeError(
                    "Project validation failed. "
                    "Review validation_report.json."
                )

            self.emit_log(
                "Static project validation completed."
            )

            self.emit_progress(100)

            mode_label = (
                "Mock" if mock else "Real"
            )

            self.emit_log(
                f"{mode_label} generation completed."
            )

            self.events.put((
                "success",
                (
                    f"{mode_label} generation finished.\n\n"
                    f"Location: {project_directory}\n\n"
                    "Static checks completed.\n"
                    "Run the generated project's tests "
                    "and application separately.\n\n"
                    f"Estimated API cost: "
                    f"${tracker.get_summary()['estimated_cost_usd']:.6f}"
                ),
            ))

        except BudgetExceededError as error:
            self.emit_log(
                f"BUDGET STOP: {error}"
            )
            self.events.put((
                "error",
                f"Budget protection stopped generation:\n{error}",
            ))

        except Exception as error:
            self.emit_log(
                f"ERROR: {error}"
            )
            self.events.put((
                "error",
                str(error),
            ))


if __name__ == "__main__":
    root = tk.Tk()
    app = AICodeAgentApp(root)
    root.mainloop()
