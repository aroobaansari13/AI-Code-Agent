# Space Fractions

An educational game that helps sixth-grade students practice fraction-solving skills.
Built with Python and Tkinter.

## Setup

```bash
# Create and activate a virtual environment (optional but recommended)
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Running the Game

```bash
python main.py
```

The game presents a series of fraction questions. Select an answer from the
provided options to submit your response. Your score and accuracy are tracked
as you play.

## Testing

```bash
python -m pytest
```

Tests cover the game logic (`tests/test_game_logic.py`) and the UI wiring
(`tests/test_main.py`).

## Architecture

The system follows a microservices style, decomposed into three components:

- **GameComponent** — game logic and user interaction (owns game state).
- **QuestionComponent** — question management and data persistence.
- **UserComponent** — user authentication and authorization.

This Python/Tkinter implementation maps those responsibilities onto two
modules:

- `game_logic.py` — core domain model:
  - `Question` — holds `prompt`, `options`, and `answer` (a `Fraction`).
  - `generate_question(operation=None, max_denominator=12)` — builds a question.
  - `check_answer(question, selected)` — validates a submitted answer.
  - `Game` — tracks `score`, `total`, and questions; exposes `play()`,
    `submit()`, `view_score()`, and `accuracy()`.
- `main.py` — Tkinter user interface that drives the game loop.

### Key design notes

- Fractions are represented with `fractions.Fraction` (never assumed to be
  `int` or `float`), preserving exact arithmetic.
- The architecture specifies cloud deployment (Kubernetes, PostgreSQL, Redis,
  OAuth2, Prometheus). This local implementation focuses on the game logic and
  UI; persistence and auth are represented by the component boundaries above.

## Requirements Traceability

| ID | Requirement | Component |
| --- | --- | --- |
| FR-1 | Play game | GameComponent |
| NFR-1 | Performance | GameComponent |
| ASR-1 | Data durability | QuestionComponent |
| ASR-2 | Security | UserComponent |
