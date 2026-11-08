from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QSettings
from PySide6.QtGui import QAction, QActionGroup, QFont, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QBoxLayout,
    QVBoxLayout,
    QWidget,
)

from flashcards import (
    ARCHIVED,
    LEVELS,
    TOP_LEVEL,
    FlashcardDeck,
    blank_sentence,
    level_icon,
    level_name,
)
import json
from datetime import date

from backup import make_backup, merge_progress, parse_import
from progress import ProgressStore
from theme import is_dark, main_style, set_dark
from adjectives import adjective_html, load_adjectives
from examples import examples_html, load_examples
from nouns import declension_html, load_declensions
from verbs import conjugation_html, load_conjugations
from quiz import ClozeDialog, QuizDialog, QuizSetupDialog
from sentences import (
    SentenceDialog,
    SentenceSetupDialog,
    load_sentences,
    pick_sentences,
)


# Neutral colours (semi-transparent grey) so the buttons look right in light and dark themes.
STAT_BUTTON_STYLE = """
QPushButton { background: transparent; border: none; border-radius: 8px;
              padding: 6px 10px; font-size: 13px; font-weight: 600; }
QPushButton:hover { background: rgba(128, 128, 128, 55); }
QPushButton:checked { background: rgba(128, 128, 128, 90); }
"""


class FlashcardWindow(QMainWindow):
    FILTER_NAMES = {
        FlashcardDeck.ALL: "all cards",
        FlashcardDeck.NEW: "new",
        FlashcardDeck.REVIEW: "to verify",
        FlashcardDeck.LEARNING: "learning",
        FlashcardDeck.ALMOST: "almost there",
        FlashcardDeck.KNOWN: "known",
        FlashcardDeck.ARCHIVE: "archived",
        FlashcardDeck.FAILED: "failed in quiz",
        FlashcardDeck.QUICK: "quick set",
        FlashcardDeck.SEARCH: "search results",
    }

    def __init__(self, json_path: Path, workspace=None):
        super().__init__()
        self.workspace = workspace      # a workspace.Workspace, or None for a plain words file

        self.setWindowTitle("Flashcards")
        self.resize(1000, 860)
        self.setMinimumSize(640, 520)

        self.json_path = Path(json_path)
        self.deck: FlashcardDeck | None = None
        self.revealed = False
        self.session_finished = False

        self.settings = QSettings("Flashcards", "Flashcards")
        self.english_first = self.settings.value("english_first", False, type=bool)
        self.show_examples = self.settings.value("show_examples", True, type=bool)
        self.show_grammar = self.settings.value("show_grammar", True, type=bool)
        self.conjugations: dict[str, list[dict]] = {}
        self.declensions: dict[str, list[dict]] = {}
        self.adjectives: dict[str, list[dict]] = {}
        self.examples: dict[str, list[tuple[str, str]]] = {}
        self.dark_mode = is_dark()
        self.setStyleSheet(main_style(self.dark_mode))

        self.progress_store = ProgressStore(
            workspace.stats_path if workspace else Path.home() / ".flashcards" / "progress.json"
        )

        self._build_ui()
        self._build_menu()
        self._load_file(self.json_path)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocus()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(35, 25, 35, 30)
        root.setSpacing(18)

        # Header
        header = QFrame()
        header.setObjectName("header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Vocabulary Flashcards")
        title.setObjectName("title")

        self.counter = QLabel()
        self.counter.setObjectName("counter")
        self.counter.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("search")
        self.search_edit.setPlaceholderText("Search…  (Ctrl+F)")
        self.search_edit.setClearButtonEnabled(True)
        # Only focused by clicking it or with Ctrl+F, never by default.
        self.search_edit.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.search_edit.textChanged.connect(self.on_search)
        # Enter leaves the box so Space / arrow keys work on the results.
        self.search_edit.returnPressed.connect(self.search_edit.clearFocus)

        vcenter = Qt.AlignmentFlag.AlignVCenter
        header_layout.addWidget(title, 0, vcenter)
        header_layout.addStretch()
        header_layout.addWidget(self.search_edit, 0, vcenter)

        root.addWidget(header)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        progress_row = QHBoxLayout()
        progress_row.setSpacing(12)
        progress_row.addWidget(self.progress, 1, Qt.AlignmentFlag.AlignVCenter)
        progress_row.addWidget(self.counter, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addLayout(progress_row)

        # Clickable counters: each one shows that category.
        stats_row = QHBoxLayout()
        stats_row.setSpacing(4)
        self.stat_buttons: dict[str, QPushButton] = {}
        stat_defs = [(FlashcardDeck.ALL, "all")]
        stat_defs += [(f"level{lv}", f"{icon}") for lv, _, icon in LEVELS]
        stat_defs.insert(5, (FlashcardDeck.NEW, "●"))
        for mode, _icon in stat_defs:
            button = QPushButton()
            button.setObjectName("stat")
            button.setCheckable(True)
            button.setFlat(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.setStyleSheet(STAT_BUTTON_STYLE)
            button.clicked.connect(lambda _=False, m=mode: self.set_filter(m))
            stats_row.addWidget(button)
            self.stat_buttons[mode] = button
        stats_row.addStretch()
        self.stats = QLabel()
        self.stats.setObjectName("stats")
        stats_row.addWidget(self.stats, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addLayout(stats_row)

        # Card
        self.card = QFrame()
        self.card.setObjectName("card")
        self.card.setMinimumHeight(150)

        # Everything on the card lives in ONE scroll area: it fills the room between
        # the counters and the buttons and only scrolls when the content really is
        # taller than the window (small windows, long tables).
        card_outer = QVBoxLayout(self.card)
        card_outer.setContentsMargins(0, 0, 0, 0)
        self.card_scroll = QScrollArea()
        self.card_scroll.setObjectName("cardscroll")
        self.card_scroll.setWidgetResizable(True)
        self.card_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.card_scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        card_body = QWidget()
        card_body.setObjectName("card_body")
        card_layout = QVBoxLayout(card_body)
        card_layout.setContentsMargins(40, 22, 40, 22)
        card_layout.setSpacing(10)

        self.language = QLabel("WORD")
        self.language.setObjectName("language")
        self.language.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.word_label = QLabel()
        self.word_label.setObjectName("word")
        self.word_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.word_label.setWordWrap(True)

        self.translation_label = QLabel()
        self.translation_label.setObjectName("translation")
        self.translation_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.translation_label.setWordWrap(True)
        self.translation_label.hide()

        self.sentence_label = QLabel()
        self.sentence_label.setObjectName("sentence")
        self.sentence_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sentence_label.setWordWrap(True)
        self.sentence_label.hide()

        self.sentence_tr_label = QLabel()
        self.sentence_tr_label.setObjectName("sentence_tr")
        self.sentence_tr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sentence_tr_label.setWordWrap(True)
        self.sentence_tr_label.hide()

        self.conj_label = QLabel()
        self.conj_label.setObjectName("conj")
        self.conj_label.setTextFormat(Qt.TextFormat.RichText)
        self.conj_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.examples_label = QLabel()
        self.examples_label.setObjectName("examples")
        self.examples_label.setTextFormat(Qt.TextFormat.RichText)
        self.examples_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.examples_label.setWordWrap(True)

        # Examples and tables: always one centred column; the card scrolls if needed.
        self.extras_box = QWidget()
        self.extras_box.setObjectName("extras_body")
        self.extras_layout = QBoxLayout(QBoxLayout.Direction.TopToBottom, self.extras_box)
        self.extras_layout.setContentsMargins(0, 0, 0, 0)
        self.extras_layout.setSpacing(14)
        self.extras_layout.addWidget(self.examples_label, 0, Qt.AlignmentFlag.AlignTop)
        self.extras_layout.addWidget(self.conj_label, 0, Qt.AlignmentFlag.AlignTop)
        self.extras_box.hide()

        card_layout.addStretch()
        card_layout.addWidget(self.language)
        card_layout.addWidget(self.word_label)
        card_layout.addSpacing(12)
        card_layout.addWidget(self.translation_label)
        card_layout.addWidget(self.sentence_label)
        card_layout.addWidget(self.sentence_tr_label)
        card_layout.addSpacing(6)
        card_layout.addWidget(self.extras_box)
        card_layout.addStretch()

        self.card_scroll.setWidget(card_body)
        card_outer.addWidget(self.card_scroll)

        root.addWidget(self.card, 1)

        # Main controls
        reveal_row = QHBoxLayout()
        reveal_row.setSpacing(10)

        self.prev_button = QPushButton("← Previous")
        self.prev_button.setObjectName("secondary")
        self.prev_button.clicked.connect(self.previous_card)

        self.reveal_button = QPushButton("Reveal  •  Space")
        self.reveal_button.setObjectName("reveal")
        self.reveal_button.clicked.connect(self.toggle_reveal)

        self.next_button = QPushButton("Next  →")
        self.next_button.setObjectName("secondary")
        self.next_button.clicked.connect(self.next_card)

        reveal_row.addWidget(self.prev_button)
        reveal_row.addStretch()
        reveal_row.addWidget(self.reveal_button)
        reveal_row.addStretch()
        reveal_row.addWidget(self.next_button)

        root.addLayout(reveal_row)

        # Answer buttons
        answer_row = QHBoxLayout()
        answer_row.setSpacing(10)

        self.level_buttons: list[QPushButton] = []
        for level, name, icon in LEVELS:
            button = QPushButton(f"{icon}  {name}  ({level + 1})")
            button.setObjectName(f"level{level}")
            button.clicked.connect(lambda _=False, lv=level: self.answer(lv))
            answer_row.addWidget(button)
            self.level_buttons.append(button)

        self.archive_button = QPushButton("▣  Archive  (5)")
        self.archive_button.setObjectName("secondary")
        self.archive_button.setToolTip("Hide this Known card from every view except Study → Show → Archived")
        self.archive_button.clicked.connect(lambda: self.answer(ARCHIVED))
        answer_row.addWidget(self.archive_button)

        root.addLayout(answer_row)

        self._set_answer_buttons_visible(False)

    def _build_menu(self):
        menu = self.menuBar()

        file_menu = menu.addMenu("&File")

        open_action = QAction("&Open JSON…", self)
        open_action.setShortcut(QKeySequence("Ctrl+O"))
        open_action.triggered.connect(self.open_json)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        add_words_action = QAction("&Add words…", self)
        add_words_action.triggered.connect(self.add_words)
        file_menu.addAction(add_words_action)

        export_action = QAction("&Export backup…", self)
        export_action.triggered.connect(self.export_backup)
        file_menu.addAction(export_action)

        import_action = QAction("&Import backup…", self)
        import_action.triggered.connect(self.import_backup)
        file_menu.addAction(import_action)

        file_menu.addSeparator()

        quit_action = QAction("&Quit", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        study_menu = menu.addMenu("&Study")

        shuffle_action = QAction("&Shuffle", self)
        shuffle_action.setShortcut(QKeySequence("S"))
        shuffle_action.triggered.connect(self.shuffle)
        study_menu.addAction(shuffle_action)

        restart_action = QAction("&Restart", self)
        restart_action.setShortcut(QKeySequence("R"))
        restart_action.triggered.connect(self.restart)
        study_menu.addAction(restart_action)

        study_menu.addSeparator()

        show_menu = study_menu.addMenu("S&how")
        self.filter_actions: dict[str, QAction] = {}
        group = QActionGroup(self)
        group.setExclusive(True)
        for mode, label, keys in (
            (FlashcardDeck.ALL, "&All cards", ["A"]),
            (FlashcardDeck.NEW, "&New (not answered yet)", ["N"]),
            (FlashcardDeck.REVIEW, "&To verify", ["W", "Ctrl+1"]),
            (FlashcardDeck.LEARNING, "&Learning", ["Ctrl+2"]),
            (FlashcardDeck.ALMOST, "Almost &there", ["Ctrl+3"]),
            (FlashcardDeck.KNOWN, "&Known", ["K", "Ctrl+4"]),
        ):
            action = QAction(label, self)
            action.setShortcuts([QKeySequence(k) for k in keys])
            action.setCheckable(True)
            action.setActionGroup(group)
            action.triggered.connect(lambda _=False, m=mode: self.set_filter(m))
            show_menu.addAction(action)
            self.filter_actions[mode] = action
        failed = QAction("&Failed in quiz (worst first)", self)
        failed.setShortcut(QKeySequence("F"))
        failed.setCheckable(True)
        failed.setActionGroup(group)
        failed.triggered.connect(lambda: self.set_filter(FlashcardDeck.FAILED))
        show_menu.addAction(failed)
        self.filter_actions[FlashcardDeck.FAILED] = failed

        show_menu.addSeparator()
        archived = QAction("Arc&hived (hidden everywhere else)", self)
        archived.setCheckable(True)
        archived.setActionGroup(group)
        archived.triggered.connect(lambda: self.set_filter(FlashcardDeck.ARCHIVE))
        show_menu.addAction(archived)
        self.filter_actions[FlashcardDeck.ARCHIVE] = archived

        # Not shown in any menu; only used to show "no filter selected" after a quick set.
        marker = QAction("quick set", self)
        marker.setCheckable(True)
        marker.setActionGroup(group)
        self.filter_actions[FlashcardDeck.QUICK] = marker

        quick_menu = study_menu.addMenu("&Quick set (10 random)")
        for label, levels, key in (
            ("from &To verify", {0}, "Q"),
            ("from &Learning", {1}, None),
            ("from &Almost there", {2}, None),
            ("from &Known", {3}, None),
            ("from &New", {None}, None),
            ("from &all cards", None, None),
        ):
            action = QAction(label, self)
            if key:
                action.setShortcut(QKeySequence(key))
            action.triggered.connect(lambda _=False, lv=levels: self.quick_set(lv))
            quick_menu.addAction(action)

        quiz_action = QAction("Type-the-answer &quiz…", self)
        quiz_action.setShortcut(QKeySequence("Ctrl+T"))
        quiz_action.triggered.connect(self.start_quiz)
        study_menu.addAction(quiz_action)

        cloze_action = QAction("&Fill-in-the-blank quiz…", self)
        cloze_action.setShortcut(QKeySequence("Ctrl+B"))
        cloze_action.triggered.connect(self.start_cloze)
        study_menu.addAction(cloze_action)

        sentence_action = QAction("&Sentence practice…", self)
        sentence_action.setShortcut(QKeySequence("Ctrl+P"))
        sentence_action.triggered.connect(self.start_sentences)
        study_menu.addAction(sentence_action)

        self.filter_actions[FlashcardDeck.ALL].setChecked(True)

        study_menu.addSeparator()

        self.direction_action = QAction("Show &English first (reveal shows Polish)", self)
        self.direction_action.setShortcut(QKeySequence("E"))
        self.direction_action.setCheckable(True)
        self.direction_action.setChecked(self.english_first)
        self.direction_action.toggled.connect(self.set_english_first)
        study_menu.addAction(self.direction_action)

        study_menu.addSeparator()

        search_action = QAction("Sear&ch cards…", self)
        search_action.setShortcut(QKeySequence("Ctrl+F"))
        search_action.triggered.connect(self.focus_search)
        study_menu.addAction(search_action)

        study_menu.addSeparator()

        reset_action = QAction("Reset saved &progress…", self)
        reset_action.triggered.connect(self.reset_progress)
        study_menu.addAction(reset_action)

        view_menu = menu.addMenu("&View")
        self.dark_action = QAction("&Dark mode", self)
        self.dark_action.setShortcut(QKeySequence("Ctrl+D"))
        self.dark_action.setCheckable(True)
        self.dark_action.setChecked(self.dark_mode)
        self.dark_action.toggled.connect(self.set_dark_mode)
        view_menu.addAction(self.dark_action)

        self.examples_action = QAction("Show extra &sentences", self)
        self.examples_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self.examples_action.setCheckable(True)
        self.examples_action.setChecked(self.show_examples)
        self.examples_action.toggled.connect(self.set_show_examples)
        view_menu.addAction(self.examples_action)

        self.grammar_action = QAction("Show &grammar tables", self)
        self.grammar_action.setShortcut(QKeySequence("Ctrl+Shift+G"))
        self.grammar_action.setCheckable(True)
        self.grammar_action.setChecked(self.show_grammar)
        self.grammar_action.toggled.connect(self.set_show_grammar)
        view_menu.addAction(self.grammar_action)

        dungeon_menu = menu.addMenu("&Dungeon")
        dungeon_action = QAction("&Enter the dungeon…", self)
        dungeon_action.setShortcut(QKeySequence("Ctrl+G"))
        dungeon_action.triggered.connect(self.start_dungeon)
        dungeon_menu.addAction(dungeon_action)

        card_menu = menu.addMenu("&Card")
        for level, name, icon in LEVELS:
            action = QAction(f"Move to {name}", self)
            action.setShortcut(QKeySequence(str(level + 1)))
            action.triggered.connect(lambda _=False, lv=level: self.answer(lv))
            card_menu.addAction(action)
        card_menu.addSeparator()
        self.archive_action = QAction("Archive (Known cards only)", self)
        self.archive_action.setShortcut(QKeySequence("5"))
        self.archive_action.triggered.connect(lambda: self.answer(ARCHIVED))
        card_menu.addAction(self.archive_action)

        help_menu = menu.addMenu("&Help")

        shortcuts_action = QAction("&Keyboard Shortcuts", self)
        shortcuts_action.triggered.connect(self.show_shortcuts)
        help_menu.addAction(shortcuts_action)

    def _load_file(self, path: Path):
        try:
            ws = self.workspace
            self.deck = FlashcardDeck.from_json(path, ws.progress_path if ws and path == ws.words_path else None)
            self.conjugations = load_conjugations(path.with_name("verbs.json"))
            self.declensions = load_declensions(path.with_name("nouns.json"))
            self.adjectives = load_adjectives(path.with_name("adjectives.json"))
            self.examples = load_examples(path.with_name("examples.json"))
            self.filter_actions[FlashcardDeck.ALL].setChecked(True)
            self.json_path = path
            self.session_finished = False
            self.revealed = False
            self._update_ui()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Could not load vocabulary",
                f"{exc}\n\nExpected format:\n"
                '[{"word": "pies", "translation": "dog"}]',
            )

    def export_backup(self):
        """Write your progress (and the dungeon save) to a file the phone app can import."""
        if not self.deck:
            return
        suggested = Path.home() / f"wordsnswords-backup-{date.today().isoformat()}.json"
        path, _ = QFileDialog.getSaveFileName(self, "Export backup", str(suggested), "JSON files (*.json)")
        if not path:
            return
        dungeon = None
        if self.workspace and self.workspace.dungeon_path.exists():
            try:
                dungeon = json.loads(self.workspace.dungeon_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                dungeon = None
        try:
            Path(path).write_text(json.dumps(make_backup(self.deck, dungeon), ensure_ascii=False, indent=2),
                                  encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(self, "Could not save the backup", str(exc))
            return
        QMessageBox.information(self, "Backup saved", f"Saved to {path}.\nOpen it in the phone app: More → Import.")

    def import_backup(self):
        """Take over the progress from a backup made on the phone (or on this PC)."""
        if not self.deck:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Import backup", str(Path.home()), "JSON files (*.json)")
        if not path:
            return
        try:
            cards, dungeon = parse_import(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Could not read the backup", str(exc))
            return
        box = QMessageBox(self)
        box.setWindowTitle("Import backup")
        box.setText(f"The backup has {len(cards)} cards"
                    + (" and a dungeon save." if dungeon else "."))
        box.setInformativeText("Merge keeps the more advanced level of each card.\n"
                               "Replace uses the backup's levels and, if it has one, its dungeon save.")
        merge = box.addButton("Merge", QMessageBox.ButtonRole.AcceptRole)
        replace = box.addButton("Replace", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.exec()
        clicked = box.clickedButton()
        if clicked not in (merge, replace):
            return
        result = merge_progress(self.deck, cards, "replace" if clicked is replace else "higher")
        self.deck.save()
        self.deck.set_mode(self.deck.mode)
        note = ""
        if clicked is replace and dungeon and self.workspace:
            try:
                self.workspace.dungeon_path.parent.mkdir(parents=True, exist_ok=True)
                self.workspace.dungeon_path.write_text(json.dumps(dungeon, ensure_ascii=False, indent=2), encoding="utf-8")
                note = "\nThe dungeon save was replaced."
            except OSError as exc:
                note = f"\nThe dungeon save could not be written: {exc}"
        self._update_ui()
        QMessageBox.information(
            self, "Backup imported",
            f"{result['updated']} cards updated, {result['unchanged']} unchanged, "
            f"{result['skipped']} not in your word list.{note}")

    def add_words(self):
        if not self.workspace:
            QMessageBox.information(self, "Add words", "Adding words needs the WordsNSwords folder (users/<name>/…).")
            return
        from addwords_ui import AddWordsDialog
        dialog = AddWordsDialog(self.workspace, self)
        dialog.exec()
        if dialog.changed:
            self._load_file(self.json_path)

    def open_json(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open vocabulary JSON",
            str(self.json_path.parent),
            "JSON files (*.json)",
        )

        if path:
            self.workspace = None       # a plain words file: levels are saved inside it, as before
            self._load_file(Path(path))

    def _update_ui(self):
        if not self.deck:
            return

        deck = self.deck
        self.revealed = False
        self.translation_label.hide()
        self.sentence_label.hide()
        self.sentence_tr_label.hide()
        self.extras_box.hide()
        self.reveal_button.setText("Reveal  •  Space")
        # Answer buttons work with or without revealing the card first.
        self._set_answer_buttons_visible(bool(deck.total) and not self.session_finished)

        # Progress = cards answered in the current pass / cards in the current view.
        answered = len(deck.results)
        self.progress.setValue(
            int(answered / deck.total * 100) if deck.total else 0
        )
        self._update_stats()

        if not deck.total:
            self.counter.setText("0 / 0")
            self.word_label.setStyleSheet("")
            searching = deck.mode == FlashcardDeck.SEARCH
            self.word_label.setText("No match" if searching else "No cards here 🎉")
            self.translation_label.setText("")
            self.language.setText("")
            self.sentence_label.setText(
                f"Nothing found for “{self.search_edit.text().strip()}”."
                if searching else "Choose Study → Show → All cards to see everything."
            )
            self.sentence_label.show()
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(False)
            self.reveal_button.setEnabled(False)
            self._set_archive_enabled(False)
            return

        self.reveal_button.setEnabled(True)
        card = deck.current
        self._set_archive_enabled(card.level == TOP_LEVEL and not self.session_finished)
        self.counter.setText(f"{deck.current_number} / {deck.total}")
        if self.english_first:
            front, back, lang = card.translation, card.word, "ENGLISH"
        else:
            front, back, lang = card.word, card.translation, "POLISH"
        self.word_label.setText(front)
        self.translation_label.setText(back)
        self.word_label.setStyleSheet(f"font-size: {self._font_px(front, 64, 48, 36)}px;")
        self.translation_label.setStyleSheet(
            f"font-size: {self._font_px(back, 40, 30, 24)}px;"
        )
        self.sentence_label.setText(card.sentence)
        self.sentence_tr_label.setText(card.sentence_translation)
        self.language.setText(f"{lang}  ·  {level_icon(card.level)} {level_name(card.level)}")
        if card.fails:
            self.language.setText(f"{self.language.text()}  ·  failed {card.fails}×")

        self.prev_button.setEnabled(deck.index > 0)
        self.next_button.setEnabled(not deck.is_last)

    def _update_stats(self):
        deck = self.deck
        labels = {FlashcardDeck.ALL: f"All {deck.active_count}"}
        for level, name, icon in LEVELS:
            labels[f"level{level}"] = f"{icon} {deck.level_count(level)} {name.lower()}"
        labels[FlashcardDeck.NEW] = f"● {deck.new_count} new"
        for mode, button in self.stat_buttons.items():
            button.setText(labels[mode])
            button.setChecked(deck.mode == mode)
        self.stats.setText(f"(showing: {self.FILTER_NAMES[deck.mode]})")
        self.filter_actions[FlashcardDeck.ARCHIVE].setText(
            f"Arc&hived – {deck.level_count(ARCHIVED)} (hidden everywhere else)"
        )

    @staticmethod
    def _font_px(text: str, large: int, medium: int, small: int) -> int:
        """Shrink the font for long cards so they still fit."""
        if len(text) <= 24:
            return large
        return medium if len(text) <= 45 else small

    def set_english_first(self, checked: bool):
        self.english_first = checked
        self.settings.setValue("english_first", checked)
        if self.deck:
            self._update_ui()

    def _set_answer_buttons_visible(self, visible: bool):
        for button in self.level_buttons:
            button.setEnabled(visible)
        if not visible:
            self._set_archive_enabled(False)

    def _set_archive_enabled(self, enabled: bool):
        """Archiving is only possible for a Known card."""
        self.archive_button.setEnabled(enabled)
        if hasattr(self, "archive_action"):  # the menu is built after the widgets
            self.archive_action.setEnabled(enabled)

    def toggle_reveal(self):
        if not self.deck or not self.deck.total or self.session_finished:
            return

        self.revealed = not self.revealed
        self.translation_label.setVisible(self.revealed)
        self.sentence_label.setVisible(self.revealed and bool(self.deck.current.sentence))

        self.sentence_tr_label.setVisible(
            self.revealed and bool(self.deck.current.sentence_translation)
        )
        self._show_extras(self.revealed)
        self.reveal_button.setText(
            "Hide  •  Space" if self.revealed else "Reveal  •  Space"
        )

    def answer(self, level: int):
        if not self.deck or not self.deck.total or self.session_finished:
            return
        if level == ARCHIVED and self.deck.current.level != TOP_LEVEL:
            return  # only Known cards can be archived

        try:
            self.deck.mark(level)
        except OSError as exc:
            QMessageBox.warning(
                self, "Could not save progress",
                f"Your answer was not written to {self.deck.path}:\n{exc}",
            )

        if self.deck.is_last:
            self._update_ui()
            self._finish_session()
        else:
            self.deck.next()
            self._update_ui()

    def next_card(self):
        if self.deck and not self.deck.is_last:
            self.deck.next()
            self._update_ui()

    def previous_card(self):
        if self.deck and self.deck.index > 0:
            self.deck.previous()
            self._update_ui()

    def shuffle(self):
        if not self.deck:
            return

        self.deck.shuffle()
        self.session_finished = False
        self._update_ui()

    def restart(self):
        if not self.deck:
            return

        self.deck.restart()
        self.session_finished = False
        self._update_ui()

    def set_filter(self, mode: str):
        if not self.deck:
            return

        self._clear_search()
        self.filter_actions[mode].setChecked(True)
        self.deck.set_mode(mode)
        self.session_finished = False
        self._update_ui()

    def quick_set(self, levels):
        """Study 10 random cards from the chosen level(s); None = every card."""
        if not self.deck:
            return

        if not self.deck.pool(levels):
            QMessageBox.information(
                self, "No cards", "There are no cards in that level yet.",
            )
            return

        self._clear_search()
        self.deck.quick_set(levels)
        self.filter_actions[FlashcardDeck.QUICK].setChecked(True)
        self.session_finished = False
        self._update_ui()

    def _clear_search(self):
        """Empty the search box without triggering a new search."""
        if self.search_edit.text():
            self.search_edit.blockSignals(True)
            self.search_edit.clear()
            self.search_edit.blockSignals(False)

    def on_search(self, text: str):
        if not self.deck:
            return
        if not text.strip():
            self.set_filter(FlashcardDeck.ALL)
            return
        self.deck.search(text)
        self.filter_actions[FlashcardDeck.QUICK].setChecked(True)  # no menu filter selected
        self.session_finished = False
        self._update_ui()

    def focus_search(self):
        self.search_edit.setFocus()
        self.search_edit.selectAll()

    def set_dark_mode(self, on: bool):
        self.dark_mode = on
        set_dark(on)
        self.setStyleSheet(main_style(on))

    def set_show_examples(self, on: bool):
        self.show_examples = on
        self.settings.setValue("show_examples", on)
        if self.deck is not None and self.deck.current is not None:
            self._show_extras(self.revealed)

    def set_show_grammar(self, on: bool):
        self.show_grammar = on
        self.settings.setValue("show_grammar", on)
        if self.deck is not None and self.deck.current is not None:
            self._show_extras(self.revealed)

    def _show_extras(self, show: bool):
        """Example sentences and verb / noun / adjective tables under the card."""
        word = self.deck.current.word
        muted = "#8b97a3" if self.dark_mode else "#7b8794"
        tables = []
        if self.show_grammar:
            if self.conjugations.get(word):
                tables.append(conjugation_html(self.conjugations[word], muted))
            if self.declensions.get(word):
                tables.append(declension_html(self.declensions[word], muted))
            if self.adjectives.get(word):
                tables.append(adjective_html(self.adjectives[word], muted))
        examples = self.examples.get(word) if self.show_examples else None
        if not show or not (tables or examples):
            self.extras_box.hide()
            return
        self.examples_label.setText(examples_html(examples, muted) if examples else "")
        self.examples_label.setVisible(bool(examples))
        self.conj_label.setText("<br>".join(tables))
        self.conj_label.setVisible(bool(tables))
        self.extras_box.show()
        self.card_scroll.verticalScrollBar().setValue(0)

    def _update_compact(self):
        """Smaller type on short windows so the card needs less scrolling."""
        if not hasattr(self, "word_label"):
            return
        h = self.height()
        sizes = {"word": 64, "translation": 40, "sentence": 24, "sentence_tr": 18}
        if h < 860:
            scale = max(0.6, h / 860)
            sizes = {k: max(14, int(v * scale)) for k, v in sizes.items()}
            style = {k: f"font-size: {v}px;" for k, v in sizes.items()}
        else:
            style = {k: "" for k in sizes}
        self.word_label.setStyleSheet(style["word"])
        self.translation_label.setStyleSheet(style["translation"])
        self.sentence_label.setStyleSheet(style["sentence"])
        self.sentence_tr_label.setStyleSheet(style["sentence_tr"])

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_compact()

    def _known_forms(self) -> dict[str, list[str]]:
        """Every inflected form from verbs.json / nouns.json, per card word."""
        forms: dict[str, list[str]] = {}
        for word, verbs in self.conjugations.items():
            forms.setdefault(word, []).extend(f for v in verbs for f in v["forms"] + v.get("past", []) + v.get("imperative", []) if f)
        for word, nouns in self.declensions.items():
            forms.setdefault(word, []).extend(
                f for n in nouns for f in n["singular"] + n["plural"] if f
            )
        for word, adjectives in self.adjectives.items():
            forms.setdefault(word, []).extend(
                f for a in adjectives for column in a["forms"].values() for f in column if f
            )
        return forms

    def start_cloze(self):
        if not self.deck:
            return

        forms = self._known_forms()
        allowed = {
            i for i, w in enumerate(self.deck.words)
            if any(
                blank_sentence(w, forms.get(w.word), pl) is not None
                for pl in [w.sentence] + [e[0] for e in self.examples.get(w.word, [])]
            )
        }
        setup = QuizSetupDialog(self.deck, self.english_first, self, allowed=allowed, cloze=True)
        if setup.exec() != QuizSetupDialog.DialogCode.Accepted:
            return

        ids = setup.card_ids()
        if not ids:
            QMessageBox.information(self, "No cards", "There are no cards for that selection.")
            return

        ClozeDialog(self.deck, ids, setup.ignore_accents(), self, forms, self.examples if self.show_examples else {}).exec()
        self._update_ui()

    def start_quiz(self):
        if not self.deck:
            return

        setup = QuizSetupDialog(self.deck, self.english_first, self)
        if setup.exec() != QuizSetupDialog.DialogCode.Accepted:
            return

        ids = setup.card_ids()
        if not ids:
            QMessageBox.information(
                self, "No cards", "There are no cards in the selected levels."
            )
            return

        QuizDialog(
            self.deck, ids, setup.english_prompt(), setup.ignore_accents(), self
        ).exec()
        self._update_ui()

    def start_dungeon(self):
        if not self.deck:
            return
        from dungeon.manager import save_path_for
        from dungeon_ui import DungeonWindow

        # The game only reads the deck; it saves to its own dungeon_progress.json.
        ws = self.workspace
        if ws:
            DungeonWindow(self.deck, ws.dungeon_path, self, hero_name=ws.user,
                          examples_path=ws.content_dir / "examples.json").exec()
        else:
            DungeonWindow(self.deck, save_path_for(self.json_path), self).exec()
        self._update_ui()

    def start_sentences(self):
        if not self.deck:
            return

        path = self.json_path.with_name("sentences.json")
        try:
            sentences = load_sentences(path)
        except (OSError, ValueError) as exc:
            QMessageBox.information(
                self,
                "No sentences",
                f"Could not read {path.name} next to your words file.\n\n{exc}",
            )
            return
        if not sentences:
            QMessageBox.information(self, "No sentences", f"{path.name} is empty.")
            return

        setup = SentenceSetupDialog(len(sentences), self.english_first, self)
        if setup.exec() != SentenceSetupDialog.DialogCode.Accepted:
            return

        items = pick_sentences(self.deck, sentences, setup.requested_count())
        SentenceDialog(self.deck, items, setup.english_prompt(), self).exec()

    def reset_progress(self):
        if not self.deck:
            return

        answer = QMessageBox.question(
            self,
            "Reset progress",
            "Remove all levels and quiz fail counts from the JSON file (every card becomes new)?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            self.deck.reset_progress()
        except OSError as exc:
            QMessageBox.warning(self, "Could not save", str(exc))
        self.session_finished = False
        self._update_ui()

    def _finish_session(self):
        self.session_finished = True

        known = self.deck.session_known
        unknown = self.deck.session_unknown
        total = known + unknown

        self.progress_store.update_session(total, known, unknown)

        percentage = round((known / total) * 100) if total else 0
        per_level = "\n".join(
            f"{icon} {name}: "
            f"{sum(1 for r in self.deck.results.values() if r == level)}"
            for level, name, icon in LEVELS
        )

        QMessageBox.information(
            self,
            "Session complete!",
            f"Great work!\n\n{per_level}\n"
            f"Known: {percentage}%\n\n"
            f"Use Study → Show to practise a level.",
        )

        self._set_answer_buttons_visible(False)

    def show_shortcuts(self):
        QMessageBox.information(
            self,
            "Keyboard shortcuts",
            "Space   Reveal / hide translation\n"
            "← / →   Previous / next card\n"
            "S       Shuffle\n"
            "R       Restart\n"
            "A / N   Show all / new cards\n"
            "Ctrl+1 … 4   Show to verify / learning / almost / known\n"
            "W / K   Show to verify / known\n"
            "1 2 3 4   Move card to To verify / Learning / Almost / Known\n"
            "5       Archive the card (Known cards only; see Study → Show → Archived)\n"
            "Q       Quick set: 10 random cards to verify (other levels: Study menu)\n"
            "Ctrl+T  Type-the-answer quiz\n"
            "Ctrl+B  Fill-in-the-blank quiz\n"
            "Ctrl+F  Search cards (Enter: back to the cards)\n"
            "Ctrl+D  Dark mode on / off\n"
            "Ctrl+P  Sentence practice\n"
            "F       Show cards failed in a quiz\n"
            "E       Switch English-first / Polish-first\n"
            "Ctrl+O  Open JSON\n"
            "Ctrl+Q  Quit",
        )

    def keyPressEvent(self, event):
        key = event.key()

        if key == Qt.Key.Key_Space:
            self.toggle_reveal()
            event.accept()
            return

        if key == Qt.Key.Key_Left:
            self.previous_card()
            event.accept()
            return

        if key == Qt.Key.Key_Right:
            self.next_card()
            event.accept()
            return

        super().keyPressEvent(event)
