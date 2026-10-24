# AI Code Agent - Space Fractions

## Project Overview

This project is a simple AI code agent designed to build a functional software project based on architectural documentation.

The primary objective was to explore how coding agents operate beyond a basic AI prompt. Instead of merely returning code as plain text, the application reads architectural files, organizes their content, interacts with an LLM, generates project files, and verifies the final output.

## How It Works

The application follows a simple coding agent workflow:

1. The user selects architecture documentation and UML diagram files.

2. The application reads these files and converts the relevant information into a structured JSON format.

3. The architecture is validated before code generation begins.

4. The agent sends the project requirements to DeepSeek via its API.

5. The model responds with instructions for creating the project files.

6. The agent processes the tool calls and writes the files to the selected output directory.

7. The generated project is checked for completeness and common implementation errors.

8. The validation results and generation details are saved for review.

The agent may make multiple API calls during the generation process. This allows it to continue working on the project rather than relying on a single response.

## Main Features

Windows desktop interface developed with Tkinter

DeepSeek API key configuration

Architecture documentation and UML file selection

User-defined output directory

Markdown-to-JSON preprocessing

Architecture validation

Multi-step code generation using an agent loop

File creation through agent tools

Project completeness and static validation checks

Limited automatic correction of detected code issues

Mock Mode for testing without API charges

Estimated API cost tracking and budget protection

Activity logs and generation progress


## Implementation Approach

Agent Loop
The agent loop is the core component of the application.

It manages communication between the language model and the available tools. When the model requests an action that is supported, the agent executes it, records the result, and continues the process.

This loop also includes limits on iterations, tool calls, and output tokens to prevent uncontrolled execution.

## Open Source References

Before developing this project, I examined the following repositories to understand how AI coding agents are designed:

Claude Code (Anthropic): https://github.com/anthropics/claude-code

How Claude Code Works: https://github.com/Windy3f3f3f3f/how-claude-code-works

Claw Code: https://github.com/ultraworkers/claw-code

The core concepts I focused on include the 'agent loop,' 'tool execution,' 'file operations,' and 'validation.'

Leveraging these concepts, I have developed a simple coding agent that integrates the DeepSeek API. This project is not an exact replica of Claude Code; rather, it focuses primarily on the features essential for building an agent-based architecture.

## Tool Execution

The application provides tools for working with project files. Instead of returning code that the user would have to manually copy, these tools allow for the creation of actual source files.

Tool execution is handled separately from API communication, which simplifies the management and testing of the workflow.

## Architecture Processing

Prior to the generation process, both input files are processed:

`Architecture_Documentation.md` contains project requirements and architectural details.

`Architecture_View.md` contains details regarding UML diagrams.

This information is converted into a structured JSON format and validated before being passed to the generation process.

## Validation and Error Handling

Generated files are checked for completeness and syntax-related issues. The agent also includes limited repair logic to address specific execution errors.

These checks help identify issues early, though they do not guarantee that every generated application will be free of bugs.

## Technologies Used

Technology          Purpose

Python              Main application development

Tkinter             Windows desktop GUI

DeepSeek API        AI-based code generation

JSON                Structured architecture representation

Pytest              Automated testing

PyInstaller         Windows executable packaging


## Project Structure

AI-Code-Agent/
├── agent/
│   ├── __init__.py
│   ├── agent_loop.py
│   ├── api_preflight.py
│   ├── cost_tracker.py
│   └── deepseek_client.py
├── parsers/
│   ├── __init__.py
│   ├── architecture_validator.py
│   ├── json_builder.py
│   ├── markdown_parser.py
│   └── plantuml_parser.py
├── tools/
├── tests/
├── inputs/
│   ├── Architecture_Documentation.md
│   └── Architecture_View.md
├── main.py
├── requirements.txt
├── AI-Code-Agent.spec
├── .gitignore
└── README.md

The agent directory consists of a generation workflow and API integration. The parser directory handles architectural processing, while the tools directory contains project-related utilities. Automated tests are stored within the tests directory.

## Running the Windows Application

A packaged Windows executable is provided separately from the source code.

1. Download and extract the Windows application ZIP file.

2. Open the extracted folder.

3. Double-click `AI-Code-Agent.exe`.

4. Enter a valid DeepSeek API key.

5. Select the architecture documentation and UML diagram files.

6. Choose an output directory.

7. Enter the input and output token prices and confirm that they have been verified for the selected model.

8. Disable "Mock Mode" to enable actual API-based generation.

9. Click "Generate Project" and confirm the API usage prompt.

The application saves the generated project to the selected output directory.

You do not need to install Python to run the packaged Windows application. An internet connection and valid API access are required for "Real Mode."


## Running from Source

For development or testing, Python is required.

Install the project dependencies:

```python -m pip install -r requirements.txt```

Launch the application:

```python main.py```

Run the automated tests:

```python -m pytest tests -q```


## API Usage and Budget Tracking

The application includes tracking of estimated API costs to help control expenses during code generation.

The project utilizes a budget of $1.00, and an internal estimated cost limit of $0.80.

The cost tracker calculates estimated expenses based on reported token usage and configured input/output token prices. The application also requests confirmation before initiating any API-based generation.

Estimated API spending is stored locally and maintained across application runs.

Important: Estimated cost tracking does not constitute a guaranteed billing limit. Actual API charges should be verified via your DeepSeek account usage and billing records. Each installation maintains its own local tracking state.

API keys are not included in the distributed application or any public repository.

## Testing

The application was tested using both 'mock' mode and 'real' mode.

Mock mode was used to verify the generation workflow without making paid API requests.

Real mode was used to build the 'Space Fractions' project using the provided architecture files. The generated application was launched locally, and its automated tests passed during the evaluation.

The packaged executable was also tested from a separate desktop folder to confirm that the interface could locate the accompanying architecture files.

## Generated Output

The agent creates a project folder at a location selected by the user. In accordance with architectural requirements, this output includes the following:

Project source code

Application entry point

Supporting modules

requirements.txt

README.md

Automated test files

Validation and completion reports

The generated project is stored separately from the agent application. It does not need to be placed inside the 'dist' folder of the executable.


## Conclusion

This project helped explore how an AI coding agent can transform architectural documentation into a structured software development workflow.

The most critical aspect of the implementation was integrating the model with actual file operations and validation steps, rather than treating code generation merely as a single, immediate response task.

The resulting desktop application provides a practical way to experiment with architecture driven project generation, while keeping the processes such as logs, validation reports, and cost estimation tracking fully visible.



