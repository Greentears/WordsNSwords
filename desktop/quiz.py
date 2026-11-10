"""Typed-answer quiz: setup dialog + quiz dialog."""
from __future__ import annotations

import language
import random

from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from flashcards import (
    BLANK,
    LEVELS,
    MIX_WEIGHTS,
    FlashcardDeck,
    blank_sentence,
    check_answer,
    level_name,
)
from theme import dialog_style


class QuizSetupDialog(QDialog):
    """Choose which levels to quiz, how many cards, and in which direction."""

    NEW_KEY = "new"

    def __init__(self, deck: FlashcardDeck, english_first: bool, parent=None,
                 allowed: set | None = None, cloze: bool = False):
        super().__init__(parent)
        self.deck = deck
        self.allowed = allowed  # restrict the quiz to these card ids (None = no limit)
        self.cloze = cloze
        self.setWindowTitle("Fill in the blank" if cloze else "Quiz")
        self.setStyleSheet(dialog_style())
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel(
            "Which cards do you want in the fill-in-the-blank quiz?" if cloze
            else "Which cards do you want in the quiz?"
        )
        title.setObjectName("title")
        layout.addWidget(title)

        self.mix_check = QCheckBox("Smart mix – a bit of everything, mostly “Almost there”")
        self.mix_check.toggled.connect(self._on_mix_toggled)
        layout.addWidget(self.mix_check)
        self.mix_hint = QLabel(
            "Mix: ~45% Almost there, 35% Learning, 20% To verify (Known and New are left out)"
        )
        self.mix_hint.setObjectName("muted")
        self.mix_hint.setWordWrap(True)
        layout.addWidget(self.mix_hint)
        layout.addSpacing(4)

        self.checks: dict[object, QCheckBox] = {}
        for level, name, icon in LEVELS:
            count = len(deck.pool({level}, allowed))
            box = QCheckBox(f"{icon}  {name}  ({count})")
            box.setChecked(level in (0, 1, 2))
            box.toggled.connect(self._refresh_available)
            layout.addWidget(box)
            self.checks[level] = box
        new_box = QCheckBox(f"●  New  ({len(deck.pool({None}, allowed))})")
        new_box.toggled.connect(self._refresh_available)
        layout.addWidget(new_box)
        self.checks[self.NEW_KEY] = new_box

        self.available_label = QLabel()
        self.available_label.setObjectName("muted")
        layout.addWidget(self.available_label)

        count_row = QHBoxLayout()
        count_row.addWidget(QLabel("Number of cards:"))
        self.count_edit = QLineEdit("10")
        self.count_edit.setObjectName("count")
        self.count_edit.setValidator(QIntValidator(1, 9999, self))
        self.count_edit.setFixedWidth(90)
        count_row.addWidget(self.count_edit)
        self.all_check = QCheckBox("All of them")
        self.all_check.toggled.connect(
            lambda on: self.count_edit.setEnabled(not on)
        )
        count_row.addWidget(self.all_check)
        count_row.addStretch()
        layout.addLayout(count_row)

        layout.addSpacing(6)
        self.radio_en = QRadioButton(f"Show English  →  type the {language.name()} word")
        self.radio_en.setChecked(True)
        self.radio_pl = QRadioButton(f"Show {language.name()}  →  type the English word")
        if cloze:
            note = QLabel(
                "You get a Polish sentence with one word missing (its dictionary form "
                "and meaning are shown as a hint). Type the missing word in the right form."
            )
            note.setObjectName("muted")
            note.setWordWrap(True)
            layout.addWidget(note)
        else:
            layout.addWidget(self.radio_en)
            layout.addWidget(self.radio_pl)
        layout.addSpacing(6)

        self.accents_check = QCheckBox(f"Accept answers without {language.name()} accents ({language.accents()})")
        self.accents_check.setChecked(True)
        layout.addWidget(self.accents_check)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        start = buttons.button(QDialogButtonBox.StandardButton.Ok)
        start.setText("Start quiz")
        start.setObjectName("submit")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setObjectName("idk")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._refresh_available()

    # -- helpers ----------------------------------------------------------
    def _on_mix_toggled(self, on: bool):
        for box in self.checks.values():
            box.setEnabled(not on)
        self.all_check.setEnabled(not on)
        if on:
            self.all_check.setChecked(False)
        self._refresh_available()

    def requested_count(self) -> int:
        try:
            return max(1, int(self.count_edit.text()))
        except ValueError:
            return 10

    def selected_levels(self) -> set:
        levels: set = set()
        for key, box in self.checks.items():
            if box.isChecked():
                levels.add(None if key == self.NEW_KEY else key)
        return levels

    def _refresh_available(self):
        if self.mix_check.isChecked():
            self.available_label.setText(
                f"Mixed from {sum(len(self.deck.pool({k}, self.allowed)) for k in MIX_WEIGHTS)} cards"
            )
            return
        levels = self.selected_levels()
        n = len(self.deck.pool(levels, self.allowed)) if levels else 0
        self.available_label.setText(f"{n} cards available with this selection")

    # -- results ----------------------------------------------------------
    def card_ids(self) -> list[int]:
        if self.mix_check.isChecked():
            return self.deck.mixed_sample(self.requested_count(), allowed=self.allowed)
        pool = self.deck.pool(self.selected_levels(), self.allowed)
        random.shuffle(pool)
        if self.all_check.isChecked():
            return pool
        return pool[: self.requested_count()]

    def english_prompt(self) -> bool:
        return self.radio_en.isChecked()

    def ignore_accents(self) -> bool:
        return self.accents_check.isChecked()


class QuizDialog(QDialog):
    """Ask cards one by one; the answer has to be typed."""

    def __init__(self, deck: FlashcardDeck, ids: list[int], english_prompt: bool,
                 ignore_accents: bool, parent=None):
        super().__init__(parent)
        self.deck = deck
        self.ids = ids
        self.english_prompt = english_prompt
        self.ignore_accents = ignore_accents
        self.position = 0
        self.results: list[tuple[int, bool]] = []
        self.answered = False  # True while the feedback for a card is shown
        self.save_warned = False

        self.setWindowTitle("Quiz")
        self.setStyleSheet(dialog_style())
        self.resize(560, 700)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 20, 28, 24)
        root.setSpacing(14)

        top = QHBoxLayout()
        self.exit_button = QPushButton("✕  Exit")
        self.exit_button.setObjectName("exit")
        self.exit_button.clicked.connect(self.reject)
        top.addWidget(self.exit_button)
        top.addStretch()
        root.addLayout(top)

        progress_row = QHBoxLayout()
        progress_label = QLabel("Progress")
        progress_label.setObjectName("muted")
        self.counter = QLabel()
        self.counter.setObjectName("muted")
        progress_row.addWidget(progress_label)
        progress_row.addStretch()
        progress_row.addWidget(self.counter)
        root.addLayout(progress_row)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setRange(0, max(1, len(ids)))
        root.addWidget(self.progress)

        card = QFrame()
        card.setObjectName("quizcard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 28, 24, 24)
        card_layout.setSpacing(14)

        self.prompt = QLabel()
        self.prompt.setObjectName("prompt")
        self.prompt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.prompt.setWordWrap(True)
        card_layout.addWidget(self.prompt)

        pill_row = QHBoxLayout()
        pill_row.addStretch()
        self.pill = QLabel()
        self.pill.setObjectName("pill")
        pill_row.addWidget(self.pill)
        pill_row.addStretch()
        card_layout.addLayout(pill_row)

        self.input = QLineEdit()
        self.input.returnPressed.connect(self._on_enter)
        card_layout.addWidget(self.input)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.submit_button = QPushButton("Submit Answer")
        self.submit_button.setObjectName("submit")
        self.submit_button.clicked.connect(self.submit)
        self.idk_button = QPushButton("I don't know")
        self.idk_button.setObjectName("idk")
        self.idk_button.clicked.connect(self.dont_know)
        self.next_button = QPushButton("Next  →")
        self.next_button.setObjectName("next")
        self.next_button.clicked.connect(self.next_card)
        buttons.addWidget(self.submit_button)
        buttons.addWidget(self.idk_button)
        self._extra_buttons(buttons)
        buttons.addWidget(self.next_button)
        buttons.addStretch()
        card_layout.addLayout(buttons)

        self.hint = QLabel()
        self.hint.setObjectName("hint")
        self.hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.hint)

        self.feedback = QLabel()
        self.feedback.setObjectName("feedback")
        self.feedback.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.feedback.setWordWrap(True)
        card_layout.addWidget(self.feedback)

        self.sentence = QLabel()
        self.sentence.setObjectName("sentence")
        self.sentence.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sentence.setWordWrap(True)
        card_layout.addWidget(self.sentence)

        self.sentence_tr = QLabel()
        self.sentence_tr.setObjectName("sentence_tr")
        self.sentence_tr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sentence_tr.setWordWrap(True)
        card_layout.addWidget(self.sentence_tr)

        card_layout.addStretch()
        root.addWidget(card)
        root.addStretch()

        self._show_card()

    def _reveal_sentence(self, word) -> tuple[str, str]:
        """(polish, english) shown after answering."""
        return word.sentence, word.sentence_translation

    def _extra_buttons(self, row) -> None:
        """Hook for subclasses to add buttons next to "I don't know"."""

    # -- card sides ---------------------------------------------------------
    def _prompt_text(self, word) -> str:
        return word.translation if self.english_prompt else word.word

    def _expected_text(self, word) -> str:
        return word.word if self.english_prompt else word.translation

    # -- flow ---------------------------------------------------------------
    def _show_card(self):
        word = self.deck.words[self.ids[self.position]]
        self.answered = False

        text = self._prompt_text(word)
        size = 40 if len(text) <= 24 else 30 if len(text) <= 45 else 24
        self.prompt.setStyleSheet(f"font-size: {size}px;")
        self.prompt.setText(text)

        if word.level is None:
            self.pill.setText("New")
        else:
            self.pill.setText(level_name(word.level).capitalize())

        self.counter.setText(f"{self.position + 1} of {len(self.ids)}")
        self.progress.setValue(self.position)

        self.input.clear()
        self.input.setReadOnly(False)
        self.input.setPlaceholderText(
            f"Type the {language.name()} word…" if self.english_prompt else "Type the English word…"
        )
        self.submit_button.show()
        self.idk_button.show()
        self.next_button.hide()
        self.hint.setText("Press Enter to submit “I don't know”")
        self.feedback.clear()
        self.sentence.clear()
        self.sentence_tr.clear()
        self.input.setFocus()

    def _on_enter(self):
        if self.answered:
            self.next_card()
        elif self.input.text().strip():
            self.submit()
        else:
            self.dont_know()

    def submit(self):
        if self.answered:
            return
        if not self.input.text().strip():
            self.dont_know()
            return
        word = self.deck.words[self.ids[self.position]]
        ok, exact = check_answer(
            self.input.text(), self._expected_text(word), self.ignore_accents
        )
        self._show_feedback(ok, exact)

    def dont_know(self):
        if self.answered:
            return
        self._show_feedback(False, False)

    def _show_feedback(self, ok: bool, exact: bool):
        word_id = self.ids[self.position]
        word = self.deck.words[word_id]
        expected = self._expected_text(word)
        self.answered = True
        self.results.append((word_id, ok))

        if ok:
            self.feedback.setStyleSheet("color: #2d8a5a;")
            text = "✓  Correct!"
            if not exact:
                text += f"\nSpelling: {expected}"
            self.feedback.setText(text)
        else:
            try:
                self.deck.record_fail(word_id)
            except OSError as exc:
                if not self.save_warned:
                    self.save_warned = True
                    QMessageBox.warning(self, "Could not save", str(exc))
            self.feedback.setStyleSheet("color: #c0453f;")
            self.feedback.setText(
                f"✕  Correct answer: {expected}\n(failed {word.fails}× so far)"
            )

        pl, en = self._reveal_sentence(word)
        self.sentence.setText(pl)
        self.sentence_tr.setText(en)

        self.input.setReadOnly(True)
        self.submit_button.hide()
        self.idk_button.hide()
        self.next_button.setText(
            "Finish" if self.position >= len(self.ids) - 1 else "Next  →"
        )
        self.next_button.show()
        self.hint.setText("Press Enter for the next card")
        self.progress.setValue(self.position + 1)
        self.next_button.setFocus()

    def next_card(self):
        if not self.answered:
            return
        if self.position >= len(self.ids) - 1:
            self._finish()
            return
        self.position += 1
        self._show_card()

    def _finish(self):
        correct = sum(1 for _, ok in self.results if ok)
        failed = [self.deck.words[i] for i, ok in self.results if not ok]
        lines = [f"Score: {correct} / {len(self.results)}"]
        if failed:
            lines.append("\nTo practise more:")
            lines += [f"• {w.word} – {w.translation} ({w.fails}×)" for w in failed]
        QMessageBox.information(self, "Quiz finished", "\n".join(lines))
        self.accept()


class ClozeDialog(QuizDialog):
    """Fill in the blank: a Polish sentence with one word missing.

    The blank is followed by the English meaning of the word to write, e.g.
    "W tym parku nie _____ (to allow / to let) psom biegać". The Hint button
    reveals the English sentence and the dictionary form.
    """

    def __init__(self, deck: FlashcardDeck, ids: list[int], ignore_accents: bool, parent=None,
                 forms: dict[str, list[str]] | None = None,
                 examples: dict[str, list[tuple[str, str]]] | None = None):
        self.forms = forms or {}  # card word -> known forms (conjugation / declension)
        self.examples = examples or {}  # card word -> extra (polish, english) sentences
        self._chosen: dict[str, tuple[str, str]] = {}  # card word -> sentence used this session
        super().__init__(deck, ids, True, ignore_accents, parent)

    def _reveal_sentence(self, word) -> tuple[str, str]:
        return self._current_sentence()

    def _extra_buttons(self, row) -> None:
        self.hint_button = QPushButton("💡  Hint")
        self.hint_button.setObjectName("idk")
        self.hint_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.hint_button.setShortcut("Ctrl+H")
        self.hint_button.setToolTip("Show the English sentence and the dictionary form (Ctrl+H)")
        self.hint_button.clicked.connect(self.show_hint)
        row.addWidget(self.hint_button)

    def _current_word(self):
        return self.deck.words[self.ids[self.position]]

    def _current_sentence(self) -> tuple[str, str]:
        """(polish, english): the card's sentence or one of its extra examples, picked
        at random once per card and kept for the whole session."""
        word = self._current_word()
        if word.word not in self._chosen:
            options = [(word.sentence, word.sentence_translation)] + list(self.examples.get(word.word, []))
            random.shuffle(options)
            forms = self.forms.get(word.word)
            usable = [o for o in options if blank_sentence(word, forms, o[0]) is not None]
            self._chosen[word.word] = usable[0] if usable else (word.sentence, word.sentence_translation)
        return self._chosen[word.word]

    def _current_blank(self) -> tuple[str, str]:
        """(sentence with a blank, text that belongs in the blank) for this card."""
        word = self._current_word()
        return blank_sentence(word, self.forms.get(word.word), self._current_sentence()[0]) or ("", "")

    def _prompt_text(self, word) -> str:
        sentence = self._current_blank()[0]
        return sentence.replace(BLANK, f"{BLANK} ({self._current_word().translation})", 1)

    def _expected_text(self, word) -> str:
        return self._current_blank()[1]

    def _show_card(self):
        super()._show_card()
        self.prompt.setStyleSheet("font-size: 26px;")
        self.input.setPlaceholderText("Type the missing word…")
        self.hint_button.show()

    def show_hint(self):
        if self.answered:
            return
        word = self._current_word()
        self.sentence_tr.setText(
            f"“{self._current_sentence()[1]}”\n\nDictionary form: {word.word}"
        )

    def _show_feedback(self, ok: bool, exact: bool):
        super()._show_feedback(ok, exact)
        self.hint_button.hide()
