"""Game logic for Space Fractions.

Provides fraction generation, answer checking, and score tracking.

Fractions are always handled with :class:`fractions.Fraction` (never as
``int`` or ``float``) so that ``1/3`` is compared exactly and reduced
forms remain correct.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Union

FractionLike = Union[str, Fraction]


def generate_fraction(
    max_denominator: int = 12,
    allow_zero: bool = False,
    allow_improper: bool = False,
) -> Fraction:
    """Return a random reduced fraction.

    By default the result is a proper fraction (numerator smaller than
    denominator). Both numerator and denominator are bounded by
    ``max_denominator``. The returned value is reduced automatically by
    :class:`Fraction`.
    """
    if max_denominator < 2:
        raise ValueError("max_denominator must be at least 2")

    denominator = random.randint(2, max_denominator)
    min_numerator = 0 if allow_zero else 1
    max_numerator = (
        max_denominator if allow_improper else denominator - 1
    )
    if max_numerator < min_numerator:
        max_numerator = min_numerator

    numerator = random.randint(min_numerator, max_numerator)
    return Fraction(numerator, denominator)


def format_fraction(value: Fraction) -> str:
    """Return a user-friendly string for a Fraction.

    Whole numbers are shown without a denominator (``2`` not ``2/1``).
    """
    if not isinstance(value, Fraction):
        raise TypeError("value must be a Fraction")
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def parse_fraction(text: str) -> Fraction:
    """Parse a fraction string into a :class:`Fraction`.

    Accepts forms such as ``"3/4"``, ``" 3 / 4 "``, and whole numbers
    like ``"2"``. Decimal input is intentionally rejected.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    cleaned = text.strip()
    if not cleaned:
        raise ValueError("fraction text is empty")

    if "/" in cleaned:
        numerator_text, denominator_text = cleaned.split("/", 1)
        numerator = int(numerator_text.strip())
        denominator = int(denominator_text.strip())
        if denominator == 0:
            raise ValueError("denominator cannot be zero")
        return Fraction(numerator, denominator)

    return Fraction(int(cleaned))


def generate_question(max_denominator: int = 12, num_options: int = 4) -> dict:
    """Generate a fraction simplification question.

    Returns a dictionary with keys ``prompt``, ``options``, ``answer``,
    and ``answer_text``. ``answer`` is a :class:`Fraction` while
    ``options`` and ``answer_text`` are strings ready for display.
    """
    if num_options < 2:
        raise ValueError("num_options must be at least 2")

    # Start from a reduced fraction, then present an equivalent,
    # non-reduced form for the player to simplify.
    answer = generate_fraction(max_denominator=max_denominator)
    multiplier = random.randint(2, 4)
    shown_numerator = answer.numerator * multiplier
    shown_denominator = answer.denominator * multiplier

    prompt = (
        f"Simplify {shown_numerator}/{shown_denominator} to lowest terms."
    )

    options: set[str] = {format_fraction(answer)}
    while len(options) < num_options:
        distractor = generate_fraction(max_denominator=max_denominator)
        options.add(format_fraction(distractor))

    option_list = list(options)
    random.shuffle(option_list)

    return {
        "prompt": prompt,
        "options": option_list,
        "answer": answer,
        "answer_text": format_fraction(answer),
    }


def check_answer(user_answer: FractionLike, correct_answer: FractionLike) -> bool:
    """Return ``True`` when the user's answer equals the correct answer.

    Inputs may be strings (``"3/4"``) or :class:`Fraction` instances.
    Comparison uses exact fraction equality.
    """
    user = parse_fraction(user_answer) if isinstance(user_answer, str) else user_answer
    correct = (
        parse_fraction(correct_answer)
        if isinstance(correct_answer, str)
        else correct_answer
    )

    if not isinstance(user, Fraction):
        raise TypeError("user_answer must be a Fraction or str")
    if not isinstance(correct, Fraction):
        raise TypeError("correct_answer must be a Fraction or str")

    return user == correct


@dataclass
class Score:
    """Track correct/incorrect counts, streaks, and accuracy."""

    correct: int = 0
    incorrect: int = 0
    streak: int = 0
    best_streak: int = 0
    history: list = field(default_factory=list)

    def record(self, is_correct: bool) -> int:
        """Record a result and return the current streak."""
        self.history.append(bool(is_correct))
        if is_correct:
            self.correct += 1
            self.streak += 1
            self.best_streak = max(self.best_streak, self.streak)
        else:
            self.incorrect += 1
            self.streak = 0
        return self.streak

    def total(self) -> int:
        """Return the number of answered questions."""
        return self.correct + self.incorrect

    def percent(self) -> float:
        """Return accuracy as a percentage (0-100)."""
        total = self.total()
        if total == 0:
            return 0.0
        return self.correct / total * 100.0

    def reset(self) -> None:
        """Reset all counters and history."""
        self.correct = 0
        self.incorrect = 0
        self.streak = 0
        self.best_streak = 0
        self.history = []


@dataclass
class Game:
    """Small game session that ties questions and score together."""

    max_denominator: int = 12
    score: Score = field(default_factory=Score)
    current_question: dict | None = None

    def new_question(self) -> dict:
        """Start a new question and return it."""
        self.current_question = generate_question(
            max_denominator=self.max_denominator
        )
        return self.current_question

    def submit_answer(self, user_answer: FractionLike) -> bool:
        """Check the answer against the current question and score it."""
        if self.current_question is None:
            raise RuntimeError("no current question; call new_question() first")
        is_correct = check_answer(user_answer, self.current_question["answer"])
        self.score.record(is_correct)
        return is_correct

    def view_score(self) -> int:
        """Return the number of correct answers."""
        return self.score.correct


if __name__ == "__main__":  # pragma: no cover - quick smoke test
    question = generate_question()
    print(question["prompt"])
    print("Options:", ", ".join(question["options"]))
    print("Answer:", question["answer_text"])
    print("Check correct answer:", check_answer(question["answer_text"], question["answer"]))
    print("Check wrong answer:", check_answer("1/1", question["answer"]))
