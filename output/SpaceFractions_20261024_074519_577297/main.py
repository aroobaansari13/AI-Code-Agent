"""Space Fractions - a Tkinter UI for the fraction practice game.

This module uses :mod:`game_logic` for all game state, question generation,
and answer checking. The UI never assumes a ``Fraction`` is an ``int`` or
``float``; fractions are handled only through the helpers exported by
``game_logic``.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from game_logic import Game, Score

# Number of questions per completed session.
QUESTIONS_PER_SESSION = 5


class SpaceFractionsApp:
    """Main Tkinter application window."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Space Fractions")
        self.root.geometry("640x440")
        self.root.minsize(520, 380)

        self.game: Game | None = None
        self.questions_asked = 0
        self.option_buttons: list[tk.Button] = []

        self._build_styles()
        self._build_menu_frame()
        self._build_game_frame()
        self._build_results_frame()
        self.show_menu()

    # ------------------------------------------------------------------ UI
    def _build_styles(self) -> None:
        self.colors = {
            "bg": "#0b1026",
            "panel": "#1a2340",
            "accent": "#7c5cff",
            "correct": "#2ecc71",
            "wrong": "#e74c3c",
            "text": "#eef2ff",
            "muted": "#a9b4d6",
        }

    def _frame(self, parent: tk.Widget) -> tk.Frame:
        frame = tk.Frame(parent, bg=self.colors["bg"], padx=24, pady=24)
        return frame

    def _label(
        self,
        parent: tk.Widget,
        text: str,
        size: int = 14,
        fg: str | None = None,
        bold: bool = False,
    ) -> tk.Label:
        return tk.Label(
            parent,
            text=text,
            font=("TkDefaultFont", size, "bold" if bold else "normal"),
            bg=self.colors["bg"],
            fg=fg or self.colors["text"],
            wraplength=540,
            justify="left",
        )

    def _clear_widgets(self, frame: tk.Frame) -> None:
        for child in frame.winfo_children():
            child.destroy()

    # ------------------------------------------------------------- menu
    def _build_menu_frame(self) -> None:
        self.menu_frame = self._frame(self.root)
        self._label(self.menu_frame, "Space Fractions", size=28, bold=True).pack(
            pady=(20, 6)
        )
        self._label(
            self.menu_frame,
            "An educational game to help sixth-grade students "
            "practice simplifying fractions.",
            size=13,
            fg=self.colors["muted"],
        ).pack(pady=(0, 24))

        tk.Button(
            self.menu_frame,
            text="▶  Play Game",
            command=self.start_game,
            font=("TkDefaultFont", 14, "bold"),
            bg=self.colors["accent"],
            fg=self.colors["text"],
            activebackground="#9370ff",
            activeforeground=self.colors["text"],
            relief="flat",
            padx=24,
            pady=10,
        ).pack(pady=8)

        tk.Button(
            self.menu_frame,
            text="❓  View Help",
            command=self.show_help,
            font=("TkDefaultFont", 12),
            bg=self.colors["panel"],
            fg=self.colors["text"],
            activebackground="#26325c",
            activeforeground=self.colors["text"],
            relief="flat",
            padx=24,
            pady=8,
        ).pack(pady=6)

        tk.Button(
            self.menu_frame,
            text="✕  Quit",
            command=self.root.destroy,
            font=("TkDefaultFont", 12),
            bg=self.colors["panel"],
            fg=self.colors["text"],
            activebackground="#26325c",
            activeforeground=self.colors["text"],
            relief="flat",
            padx=24,
            pady=8,
        ).pack(pady=6)

    def _build_game_frame(self) -> None:
        self.game_frame = self._frame(self.root)

        self.score_label = self._label(self.game_frame, "", size=12, fg=self.colors["muted"])
        self.score_label.pack(anchor="w")

        self.prompt_label = self._label(self.game_frame, "", size=18, bold=True)
        self.prompt_label.pack(pady=(24, 18))

        self.options_panel = tk.Frame(self.game_frame, bg=self.colors["bg"])
        self.options_panel.pack(fill="x", pady=(0, 16))

        self.feedback_label = self._label(self.game_frame, "", size=13, fg=self.colors["muted"])
        self.feedback_label.pack(pady=(4, 8))

        self.next_button = tk.Button(
            self.game_frame,
            text="Next Question ➜",
            command=self.next_question,
            font=("TkDefaultFont", 12, "bold"),
            bg=self.colors["accent"],
            fg=self.colors["text"],
            activebackground="#9370ff",
            activeforeground=self.colors["text"],
            relief="flat",
            padx=18,
            pady=8,
            state="disabled",
        )
        self.next_button.pack(pady=(4, 0))

    def _build_results_frame(self) -> None:
        self.results_frame = self._frame(self.root)

    # ------------------------------------------------------- navigation
    def _show_frame(self, frame: tk.Frame) -> None:
        for f in (self.menu_frame, self.game_frame, self.results_frame):
            f.pack_forget()
        frame.pack(fill="both", expand=True)

    def show_menu(self) -> None:
        self._show_frame(self.menu_frame)

    def show_help(self) -> None:
        messagebox.showinfo(
            "How to Play",
            "Each question shows a fraction that can be simplified.\n\n"
            "Choose the option that represents the fraction in lowest "
            "terms.\n\n"
            "You will answer 5 questions per session. Watch your streak "
            "and accuracy!",
            parent=self.root,
        )

    # ------------------------------------------------------------- game
    def start_game(self) -> None:
        self.game = Game()
        self.questions_asked = 0
        self._show_frame(self.game_frame)
        self.next_question()

    def _update_score(self) -> None:
        if self.game is None:
            return
        score: Score = self.game.score
        self.score_label.config(
            text=(
                f"Score: {score.correct} correct / {score.incorrect} incorrect   "
                f"Streak: {score.streak}   Accuracy: {score.percent():.1f}%"
            )
        )

    def next_question(self) -> None:
        if self.game is None:
            return

        if self.questions_asked >= QUESTIONS_PER_SESSION:
            self.show_results()
            return

        question = self.game.new_question()
        self.questions_asked += 1

        self.prompt_label.config(text=question["prompt"])
        self.feedback_label.config(text="")
        self.next_button.config(state="disabled")
        self._update_score()

        for button in self.option_buttons:
            button.destroy()
        self.option_buttons.clear()

        for option_text in question["options"]:
            button = tk.Button(
                self.options_panel,
                text=option_text,
                command=lambda opt=option_text: self.submit_answer(opt),
                font=("TkDefaultFont", 13),
                bg=self.colors["panel"],
                fg=self.colors["text"],
                activebackground="#26325c",
                activeforeground=self.colors["text"],
                relief="flat",
                padx=12,
                pady=8,
            )
            button.pack(fill="x", pady=4)
            self.option_buttons.append(button)

    def submit_answer(self, option_text: str) -> None:
        if self.game is None:
            return

        is_correct = self.game.submit_answer(option_text)

        for button in self.option_buttons:
            button.config(state="disabled")

        if is_correct:
            self.feedback_label.config(
                text="✓ Correct! Well done.", fg=self.colors["correct"]
            )
        else:
            answer_text = self.game.current_question["answer_text"]
            self.feedback_label.config(
                text=f"✗ Not quite. The answer is {answer_text}.",
                fg=self.colors["wrong"],
            )

        self._update_score()
        if self.questions_asked >= QUESTIONS_PER_SESSION:
            self.next_button.config(text="See Results ➜")
        self.next_button.config(state="normal")

    def show_results(self) -> None:
        if self.game is None:
            return

        self._clear_widgets(self.results_frame)
        score = self.game.score

        self._label(
            self.results_frame, "Mission Complete!", size=26, bold=True
        ).pack(pady=(20, 12))

        self._label(
            self.results_frame,
            f"You answered {score.correct} of {score.total()} questions correctly.",
            size=14,
        ).pack(pady=4)

        self._label(
            self.results_frame,
            f"Accuracy: {score.percent():.1f}%",
            size=14,
            fg=self.colors["muted"],
        ).pack(pady=4)

        self._label(
            self.results_frame,
            f"Best streak: {score.best_streak}",
            size=14,
            fg=self.colors["muted"],
        ).pack(pady=4)

        tk.Button(
            self.results_frame,
            text="Play Again",
            command=self.start_game,
            font=("TkDefaultFont", 13, "bold"),
            bg=self.colors["accent"],
            fg=self.colors["text"],
            activebackground="#9370ff",
            activeforeground=self.colors["text"],
            relief="flat",
            padx=22,
            pady=9,
        ).pack(pady=(20, 8))

        tk.Button(
            self.results_frame,
            text="Back to Menu",
            command=self.show_menu,
            font=("TkDefaultFont", 12),
            bg=self.colors["panel"],
            fg=self.colors["text"],
            activebackground="#26325c",
            activeforeground=self.colors["text"],
            relief="flat",
            padx=22,
            pady=8,
        ).pack(pady=6)

        self._show_frame(self.results_frame)


def main() -> None:
    root = tk.Tk()
    SpaceFractionsApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
