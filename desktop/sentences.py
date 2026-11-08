"""Sentence practice: new example sentences built from your words."""
from __future__ import annotations

import json
import random
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from flashcards import MIX_WEIGHTS, FlashcardDeck, level_name
from theme import dialog_style


def load_sentences(path: Path) -> list[dict]:
    """Read sentences.json: [{"pl": ..., "en": ..., "words": ["card word", ...]}]."""
    with Path(path).open(encoding="utf-8") as f:
        data = json.load(f)
    return [
        s for s in data
        if isinstance(s, dict) and s.get("pl") and s.get("en")
    ]


def pick_sentences(deck: FlashcardDeck, sentences: list[dict], size: int) -> list[dict]:
    """Choose `size` sentences, favouring those that mix words from several levels.

    A sentence's weight is the sum of the smart-mix weights of its words that are
    still being learned (To verify / Learning / Almost there). Sentences that only
    contain Known or New words are skipped, unless nothing else is left.
    """
    by_word = {w.word: w for w in deck.words}

    def weight(sentence: dict) -> float:
        levels = [
            by_word[t].level for t in sentence.get("words", []) if t in by_word
        ]
        learning = [lv for lv in levels if lv in MIX_WEIGHTS]
        if not learning:
            return 0.0
        total = float(sum(MIX_WEIGHTS[lv] for lv in learning))
        if len(set(learning)) > 1:
            total *= 1.5  # reward a real mix of categories
        return total

    weighted = [(s, weight(s)) for s in sentences]
    candidates = [(s, w) for s, w in weighted if w > 0]
    if not candidates:
        candidates = [(s, 1.0) for s in sentences]
    # Weighted random order without replacement (Efraimidis-Spirakis).
    keyed = sorted(candidates, key=lambda sw: random.random() ** (1.0 / sw[1]), reverse=True)
    return [s for s, _ in keyed[:size]]


class SentenceSetupDialog(QDialog):
    def __init__(self, available: int, english_first: bool, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sentence practice")
        self.setStyleSheet(dialog_style())
        self.setMinimumWidth(440)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel("Practise with new sentences")
        title.setObjectName("title")
        layout.addWidget(title)
        info = QLabel(
            "Sentences mix words from To verify, Learning and Almost there "
            "(mostly Almost there), plus a few extra words to make them natural. "
            f"{available} sentences available."
        )
        info.setObjectName("muted")
        info.setWordWrap(True)
        layout.addWidget(info)

        row = QHBoxLayout()
        row.addWidget(QLabel("Number of sentences:"))
        self.count_edit = QLineEdit("10")
        self.count_edit.setObjectName("count")
        self.count_edit.setValidator(QIntValidator(1, 9999, self))
        self.count_edit.setFixedWidth(90)
        row.addWidget(self.count_edit)
        row.addStretch()
        layout.addLayout(row)

        self.radio_en = QRadioButton("Show English  →  say / think the Polish, then reveal")
        self.radio_pl = QRadioButton("Show Polish  →  translate it, then reveal")
        (self.radio_en if english_first else self.radio_pl).setChecked(True)
        layout.addWidget(self.radio_en)
        layout.addWidget(self.radio_pl)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        start = buttons.button(QDialogButtonBox.StandardButton.Ok)
        start.setText("Start")
        start.setObjectName("submit")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setObjectName("idk")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def requested_count(self) -> int:
        try:
            return max(1, int(self.count_edit.text()))
        except ValueError:
            return 10

    def english_prompt(self) -> bool:
        return self.radio_en.isChecked()


class SentenceDialog(QDialog):
    """Show sentences one by one; reveal shows the translation and the card words."""

    def __init__(self, deck: FlashcardDeck, items: list[dict], english_prompt: bool, parent=None):
        super().__init__(parent)
        self.deck = deck
        self.items = items
        self.english_prompt = english_prompt
        self.position = 0
        self.revealed = False
        self.by_word = {w.word: w for w in deck.words}

        self.setWindowTitle("Sentence practice")
        self.setStyleSheet(dialog_style())
        self.resize(640, 560)

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
        self.bar.setRange(0, len(items))
        root.addWidget(self.bar)

        self.lang_label = QLabel()
        self.lang_label.setObjectName("pill")
        self.lang_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        root.addWidget(self.lang_label, alignment=Qt.AlignmentFlag.AlignLeft)

        self.prompt = QLabel()
        self.prompt.setObjectName("sentence_prompt")
        self.prompt.setWordWrap(True)
        root.addWidget(self.prompt)

        self.answer = QLabel()
        self.answer.setObjectName("sentence_answer")
        self.answer.setWordWrap(True)
        root.addWidget(self.answer)

        self.words_label = QLabel()
        self.words_label.setObjectName("muted")
        self.words_label.setWordWrap(True)
        self.words_label.setTextFormat(Qt.TextFormat.RichText)
        root.addWidget(self.words_label)

        root.addStretch()

        buttons = QHBoxLayout()
        self.back_button = QPushButton("←  Previous")
        self.back_button.setObjectName("idk")
        self.back_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.back_button.clicked.connect(self.previous)
        self.main_button = QPushButton("Reveal")
        self.main_button.setObjectName("submit")
        self.main_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.main_button.clicked.connect(self.advance)
        buttons.addWidget(self.back_button)
        buttons.addWidget(self.main_button, 1)
        root.addLayout(buttons)

        hint = QLabel("Space / Enter: reveal, then next   ·   ←: previous")
        hint.setObjectName("hint")
        root.addWidget(hint)

        self._show()

    # -- display ----------------------------------------------------------
    def _word_line(self, key: str) -> str:
        card = self.by_word.get(key)
        if card is None:
            return ""
        level = level_name(card.level)
        return f"<b>{card.word}</b> – {card.translation} <i>({level})</i>"

    def _show(self):
        item = self.items[self.position]
        total = len(self.items)
        self.progress_label.setText(f"{self.position + 1} of {total}")
        self.bar.setValue(self.position + 1)
        prompt, answer = (item["en"], item["pl"]) if self.english_prompt else (item["pl"], item["en"])
        self.lang_label.setText("English" if self.english_prompt else "Polish")
        self.prompt.setText(prompt)
        self.answer.setText(answer)
        lines = [line for line in (self._word_line(t) for t in item.get("words", [])) if line]
        self.words_label.setText("<br>".join(lines))
        self.back_button.setEnabled(self.position > 0)
        self.revealed = False
        self._apply_reveal()

    def _apply_reveal(self):
        self.answer.setVisible(self.revealed)
        self.words_label.setVisible(self.revealed)
        last = self.position == len(self.items) - 1
        if not self.revealed:
            self.main_button.setText("Reveal")
        else:
            self.main_button.setText("Finish" if last else "Next  →")

    # -- actions ----------------------------------------------------------
    def advance(self):
        if not self.revealed:
            self.revealed = True
            self._apply_reveal()
            return
        if self.position >= len(self.items) - 1:
            self.accept()
            return
        self.position += 1
        self._show()

    def previous(self):
        if self.position > 0:
            self.position -= 1
            self._show()

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.advance()
        elif key == Qt.Key.Key_Left:
            self.previous()
        else:
            super().keyPressEvent(event)
