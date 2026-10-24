"""Space Fractions - desktop Tkinter UI.

A simple educational game that presents fraction questions and tracks
the player's score. Uses game_logic.py for all game rules.
"""

import tkinter as tk
from fractions import Fraction

from game_logic import Game, Question, check_answer, generate_question


class SpaceFractionsApp:
    """Tkinter application for the Space Fractions game."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Space Fractions")
        self.root.geometry("520x420")

        self.game = Game()
        self.question: Question | None = None

        self._build_widgets()
        self._next_question()

    def _build_widgets(self) -> None:
        self.prompt_label = tk.Label(
            self.root, text="", font=("Helvetica", 18), wraplength=480
        )
        self.prompt_label.pack(pady=20)

        self.option_var = tk.StringVar(value="")
        self.option_buttons: list[tk.Radiobutton] = []
        self.option_frame = tk.Frame(self.root)
        self.option_frame.pack(pady=10)

        self.feedback_label = tk.Label(
            self.root, text="", font=("Helvetica", 12), fg="blue"
        )
        self.feedback_label.pack(pady=10)

        self.submit_button = tk.Button(
            self.root, text="Submit", command=self._on_submit
        )
        self.submit_button.pack(pady=10)

        self.score_label = tk.Label(
            self.root, text="Score: 0 / 0", font=("Helvetica", 12)
        )
        self.score_label.pack(pady=10)

    def _next_question(self) -> None:
        self.question = generate_question()
        self.prompt_label.config(text=self.question.prompt)

        for button in self.option_buttons:
            button.destroy()
        self.option_buttons.clear()

        self.option_var.set("")
        for option in self.question.options:
            button = tk.Radiobutton(
                self.option_frame,
                text=str(option),
                variable=self.option_var,
                value=str(option),
                font=("Helvetica", 14),
            )
            button.pack(anchor="w")
            self.option_buttons.append(button)

        self.feedback_label.config(text="")
        self._update_score()

    def _on_submit(self) -> None:
        if self.question is None:
            return

        selected_text = self.option_var.get()
        if not selected_text:
            self.feedback_label.config(text="Please select an answer.", fg="red")
            return

        selected = Fraction(selected_text)
        correct = check_answer(self.question, selected)
        self.game.submit(self.question, selected)

        if correct:
            self.feedback_label.config(text="Correct!", fg="green")
        else:
            self.feedback_label.config(
                text=f"Incorrect. The answer was {self.question.answer}.", fg="red"
            )

        self._update_score()
        self.root.after(1500, self._next_question)

    def _update_score(self) -> None:
        score = self.game.view_score()
        total = self.game.total
        self.score_label.config(text=f"Score: {score} / {total}")


def main() -> None:
    root = tk.Tk()
    SpaceFractionsApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
