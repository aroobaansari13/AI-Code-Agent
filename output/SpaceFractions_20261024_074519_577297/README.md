# Space Fractions

An educational Tkinter game that helps sixth-grade students practice fractions.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

No API keys or external services are required.

## Running the Game

```bash
python main.py
```

The game presents fraction questions, accepts answers as fractions
(e.g. `3/4`), and tracks your score. Answer using the input field and
submit button.

## Testing

```bash
python -m pytest
```

Tests cover the core game logic (`tests/test_game_logic.py`) and the
application entry point (`tests/test_main.py`).

## Architecture

The system follows a microservices-oriented design, mapped here to a
single desktop application:

| Component | Responsibility |
| --- | --- |
| `GameComponent` | Game logic and user interaction (`game_logic.py`) |
| `QuestionComponent` | Question generation and management |
| `UserComponent` | Player identity and score tracking |
| `AdminComponent` | Question updates (admin role) |

### Core API (`game_logic.py`)

- `generate_fraction(max_denominator=12, allow_zero=False, allow_improper=False)`
- `format_fraction(value)` — renders a `Fraction` as a string
- `parse_fraction(text)` — parses a string into a `Fraction`
- `generate_question(max_denominator=12, num_options=4)`
- `check_answer(user_answer, correct_answer)`
- `Score` — `record`, `total`, `percent`, `reset`
- `Game` — `new_question`, `submit_answer`, `view_score`

Fractions are represented with `fractions.Fraction` (never assumed to be
`int` or `float`).

### Key Requirements

- **FR-1** Play game — implemented by `Game` and the Tkinter UI.
- **NFR-1** Performance — lightweight in-memory state, responsive UI.
- **ASR-1** Data durability — score state is isolated and resettable.
- **ASR-2** Security — no secrets or network calls in the client.

See the architecture documentation for the full microservices,
deployment, and security design (OpenAPI, protobuf, Kubernetes, SQL).
