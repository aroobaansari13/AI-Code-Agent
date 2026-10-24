from fractions import Fraction

from game_logic import (
    Game,
    Score,
    check_answer,
    format_fraction,
    generate_question,
    parse_fraction,
)


def test_parse_and_format_fraction_roundtrip():
    assert parse_fraction(" 3 / 4 ") == Fraction(3, 4)
    assert parse_fraction("2") == Fraction(2, 1)
    assert format_fraction(Fraction(3, 4)) == "3/4"
    assert format_fraction(Fraction(4, 1)) == "4"


def test_generate_question_shape_and_answer():
    question = generate_question(max_denominator=6, num_options=3)
    assert set(question) == {"prompt", "options", "answer", "answer_text"}
    assert isinstance(question["answer"], Fraction)
    assert question["answer_text"] == format_fraction(question["answer"])
    assert question["answer_text"] in question["options"]
    assert len(question["options"]) == 3


def test_check_answer_accepts_str_and_fraction():
    assert check_answer("3/4", Fraction(3, 4)) is True
    assert check_answer(Fraction(1, 2), "1/4") is False
    assert check_answer(Fraction(6, 8), "3/4") is True


def test_score_and_game_flow():
    score = Score()
    assert score.record(True) == 1
    assert score.record(True) == 2
    assert score.record(False) == 0
    assert score.total() == 3
    assert score.percent() == (2 / 3) * 100.0
    assert score.best_streak == 2

    game = Game()
    question = game.new_question()
    assert isinstance(question, dict)
    assert game.submit_answer(question["answer_text"]) is True
    assert game.view_score() == 1
