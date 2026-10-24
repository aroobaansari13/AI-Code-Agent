import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def app():
    with patch("main.tk"):
        from main import SpaceFractionsApp

        root = MagicMock()
        instance = SpaceFractionsApp(root)
        return instance


def test_init_builds_menu(app):
    assert app.root is not None
    assert app.menu_frame is not None
    assert app.game_frame is not None


def test_start_game_creates_game(app):
    app._show_frame = MagicMock()
    app.next_question = MagicMock()

    app.start_game()

    assert app.game is not None
    app._show_frame.assert_called_once_with(app.game_frame)
    app.next_question.assert_called_once()


def test_submit_answer_updates_score(app):
    app.game = MagicMock()
    app.game.submit_answer.return_value = True

    app._update_score = MagicMock()
    app.next_question = MagicMock()

    app.submit_answer("1/2")

    app.game.submit_answer.assert_called_once_with("1/2")
    app._update_score.assert_called_once()
    app.next_question.assert_not_called()
    app.next_button.config.assert_any_call(state="normal")