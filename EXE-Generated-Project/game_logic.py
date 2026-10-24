"""Game logic for Space Fractions.

Provides fraction question generation, answer checking, and score tracking.
Fractions are represented using the standard library ``fractions.Fraction``
type so that exact rational arithmetic is preserved (never int or float).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from fractions import Fraction
from typing import List, Optional, Tuple


@dataclass
class Question:
    """A single fraction question.

    Attributes:
        prompt: Human-readable text of the question.
        options: List of answer choices as ``Fraction`` objects.
        answer: The correct answer as a ``Fraction``.
    """

    prompt: str
    options: List[Fraction]
    answer: Fraction


def _random_fraction(max_denominator: int = 12) -> Fraction:
    """Return a random positive proper fraction with a bounded denominator."""
    denominator = random.randint(2, max_denominator)
    numerator = random.randint(1, denominator - 1)
    return Fraction(numerator, denominator)


def generate_question(
    operation: Optional[str] = None,
    max_denominator: int = 12,
) -> Question:
    """Generate a random fraction question.

    Args:
        operation: One of ``"add"``, ``"subtract"``, ``"multiply"``,
            ``"divide"``, or ``None`` to pick one at random.
        max_denominator: Upper bound for generated denominators.

    Returns:
        A :class:`Question` with a prompt, four options, and the answer.
    """
    if operation is None:
        operation = random.choice(["add", "subtract", "multiply", "divide"])

    a = _random_fraction(max_denominator)
    b = _random_fraction(max_denominator)

    if operation == "add":
        answer = a + b
        symbol = "+"
    elif operation == "subtract":
        # Ensure a non-negative result.
        if a < b:
            a, b = b, a
        answer = a - b
        symbol = "-"
    elif operation == "multiply":
        answer = a * b
        symbol = "x"
    elif operation == "divide":
        answer = a / b
        symbol = "/"
    else:
        raise ValueError(f"Unsupported operation: {operation!r}")

    prompt = f"What is {a} {symbol} {b}?"

    options = _build_options(answer)
    return Question(prompt=prompt, options=options, answer=answer)


def _build_options(answer: Fraction) -> List[Fraction]:
    """Build a list of four distinct options including the correct answer."""
    options = {answer}
    while len(options) < 4:
        candidate = _random_fraction()
        # Avoid duplicates and avoid accidentally matching the answer.
        if candidate != answer:
            options.add(candidate)
    options_list = list(options)
    random.shuffle(options_list)
    return options_list


def check_answer(question: Question, selected: Fraction) -> bool:
    """Return ``True`` if ``selected`` equals the question's answer."""
    return selected == question.answer


@dataclass
class Game:
    """Tracks a player's score across a series of questions."""

    score: int = 0
    total: int = 0
    _questions: List[Question] = field(default_factory=list)

    def play(self) -> Question:
        """Generate and record a new question, returning it."""
        question = generate_question()
        self._questions.append(question)
        return question

    def submit(self, question: Question, selected: Fraction) -> bool:
        """Check an answer and update the running score.

        Returns:
            ``True`` if the answer was correct.
        """
        correct = check_answer(question, selected)
        self.total += 1
        if correct:
            self.score += 1
        return correct

    def view_score(self) -> int:
        """Return the current score (number of correct answers)."""
        return self.score

    def accuracy(self) -> float:
        """Return the fraction of correct answers as a float in [0, 1]."""
        if self.total == 0:
            return 0.0
        return self.score / self.total
