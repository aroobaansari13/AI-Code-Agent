from fractions import Fraction

from game_logic import Game, Question, check_answer, generate_question


def test_generate_question_returns_valid_question():
    q = generate_question(operation="add", max_denominator=12)
    assert isinstance(q, Question)
    assert isinstance(q.answer, Fraction)
    assert len(q.options) == 4
    assert q.answer in q.options
    assert len(set(q.options)) == 4


def test_generate_question_supported_operations():
    for op in ["add", "subtract", "multiply", "divide"]:
        q = generate_question(operation=op)
        assert isinstance(q.answer, Fraction)
        assert q.answer >= 0


def test_generate_question_rejects_unknown_operation():
    try:
        generate_question(operation="bogus")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for unsupported operation")


def test_check_answer_and_game_score():
    q = Question(prompt="What is 1/2 + 1/2?", options=[Fraction(1, 2), Fraction(1, 1)], answer=Fraction(1, 1))
    assert check_answer(q, Fraction(1, 1)) is True
    assert check_answer(q, Fraction(1, 2)) is False

    game = Game()
    assert game.view_score() == 0
    assert game.accuracy() == 0.0
    assert game.submit(q, Fraction(1, 1)) is True
    assert game.submit(q, Fraction(1, 2)) is False
    assert game.view_score() == 1
    assert game.accuracy() == 0.5
