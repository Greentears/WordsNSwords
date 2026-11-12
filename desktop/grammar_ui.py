"""Grammar quiz windows (PC): choose what to practise, then fill in the blanks one by one."""
from __future__ import annotations

import random

from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QProgressBar, QPushButton, QVBoxLayout,
)

import grammar
from theme import dialog_style


class GrammarSetupDialog(QDialog):
    def __init__(self, pool: dict[str, list], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Grammar quiz")
        self.setStyleSheet(dialog_style())
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 24)
        root.setSpacing(12)
        title = QLabel("Grammar quiz")
        title.setObjectName("title")
        root.addWidget(title)
        intro = QLabel("Fill in the blank with the right ending, case or tense. The questions are made from "
                       "your own verb, noun and adjective tables.")
        intro.setObjectName("muted")
        intro.setWordWrap(True)
        root.addWidget(intro)
        self.boxes: dict[str, QCheckBox] = {}
        for cat in grammar.CATEGORIES:
            n = len(pool.get(cat, []))
            box = QCheckBox(f"{grammar.CATEGORY_NAMES[cat]}  ({n} questions)")
            box.setChecked(n > 0)
            box.setEnabled(n > 0)
            self.boxes[cat] = box
            root.addWidget(box)
        row = QHBoxLayout()
        row.addWidget(QLabel("Number of questions"))
        self.count = QLineEdit("10")
        self.count.setObjectName("count")
        self.count.setValidator(QIntValidator(1, 999, self))
        self.count.setFixedWidth(80)
        row.addWidget(self.count)
        row.addStretch()
        root.addLayout(row)
        start = QPushButton("Start")
        start.setObjectName("submit")
        start.setDefault(True)
        start.clicked.connect(self.accept)
        root.addWidget(start)

    def categories(self) -> list[str]:
        return [c for c, b in self.boxes.items() if b.isChecked()]

    def requested_count(self) -> int:
        try:
            return max(1, int(self.count.text()))
        except ValueError:
            return 10


class GrammarDialog(QDialog):
    def __init__(self, questions: list, language: str, parent=None):
        super().__init__(parent)
        self.questions = questions
        self.language = language
        self.position = 0
        self.score = 0
        self.checked = False
        self.misses: list[tuple] = []
        self.setWindowTitle("Grammar quiz")
        self.setStyleSheet(dialog_style())
        self.resize(640, 520)
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 20, 28, 24)
        root.setSpacing(14)
        top = QHBoxLayout()
        exit_button = QPushButton("✕  Exit")
        exit_button.setObjectName("exit")
        exit_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        exit_button.clicked.connect(self.reject)
        top.addWidget(exit_button)
        top.addStretch()
        self.progress_label = QLabel()
        self.progress_label.setObjectName("muted")
        top.addWidget(self.progress_label)
        root.addLayout(top)
        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setRange(0, len(questions))
        root.addWidget(self.bar)
        self.label = QLabel()
        self.label.setObjectName("pill")
        root.addWidget(self.label, alignment=Qt.AlignmentFlag.AlignLeft)
        self.hint = QLabel()
        self.hint.setObjectName("hint")
        root.addWidget(self.hint)
        self.stem = QLabel()
        self.stem.setObjectName("sentence_prompt")
        self.stem.setWordWrap(True)
        root.addWidget(self.stem)
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type the missing form…")
        self.input.returnPressed.connect(self._enter)
        root.addWidget(self.input)
        self.feedback = QLabel()
        self.feedback.setObjectName("feedback")
        self.feedback.setWordWrap(True)
        root.addWidget(self.feedback)
        root.addStretch()
        self.button = QPushButton("Check")
        self.button.setObjectName("submit")
        self.button.clicked.connect(self._enter)
        root.addWidget(self.button)
        self._show()

    def _show(self) -> None:
        if self.position >= len(self.questions):
            self._finish()
            return
        q = self.questions[self.position]
        self.checked = False
        self.progress_label.setText(f"{self.position + 1} / {len(self.questions)}")
        self.bar.setValue(self.position)
        self.label.setText(q.label)
        self.hint.setText(q.hint)
        self.hint.setVisible(bool(q.hint))
        self.stem.setText(q.stem)
        self.input.clear()
        self.input.setEnabled(True)
        self.input.setFocus()
        self.feedback.clear()
        self.button.setText("Check")

    def _enter(self) -> None:
        if self.position >= len(self.questions):
            self.accept()
            return
        q = self.questions[self.position]
        if self.checked:
            self.position += 1
            self._show()
            return
        result = grammar.check(q, self.input.text(), self.language)
        self.checked = True
        self.input.setEnabled(False)
        shown = q.answers[0]
        if result == "correct":
            self.score += 1
            self.feedback.setText("✔ Correct!")
        elif result == "accents":
            self.score += 1
            self.feedback.setText(f"✔ Right, mind the accents: {shown}")
        else:
            self.misses.append((q, self.input.text().strip()))
            self.feedback.setText(f"✘ {shown}" + (f"   (also: {', '.join(q.answers[1:])})" if len(q.answers) > 1 else ""))
        self.button.setText("Next")
        self.button.setFocus()

    def _finish(self) -> None:
        self.bar.setValue(len(self.questions))
        self.label.setText("Finished")
        self.hint.hide()
        self.input.hide()
        lines = [f"Score: {self.score} / {len(self.questions)}"]
        if self.misses:
            lines.append("")
            lines.append("To practise:")
            lines += [f"  {q.stem.replace('___', q.answers[0])}   ({q.label})" for q, _ in self.misses]
        self.stem.setText(lines[0])
        self.feedback.setText("\n".join(lines[1:]))
        self.progress_label.clear()
        self.button.setText("Close")
        self.checked = True
        self.position = len(self.questions)
