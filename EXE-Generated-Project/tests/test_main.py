import tkinter as tk
from fractions import Fraction
from unittest.mock import MagicMock, patch

from main import SpaceFractionsApp


def _make_app():
    root = MagicMock(spec=tk.Tk)
    with patch("main.generate_question") as gen:
        gen.return_value = MagicMock(
            prompt="1/2 + 1/4", options=["3/4", "1/2"], answer=Fraction(3, 4)
        )
        app = SpaceFractionsApp(root)
    return app


def test_init_builds_widgets_and_loads_question():
    app = _make_app()
    assert app.question is not None
    assert app.game.total == 0


def test_on_submit_no_selection_shows_feedback():
    app = _make_app()
    app.option_var.get.return_value = ""
    app._on_submit()
    app.feedback_label.config.assert_called_once()


def test_on_submit_correct_answer_updates_score():
    app = _make_app()
    app.option_var.get.return_value = "3/4"
    app._on_submit()
    assert app.game.view_score() == 1
    app.root.after.assert_called_once()
