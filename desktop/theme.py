"""Light / dark colour themes for the main window and the dialogs."""
from __future__ import annotations

import re

from PySide6.QtCore import QSettings


def is_dark() -> bool:
    """Whether dark mode was chosen (remembered between runs)."""
    return bool(QSettings("Flashcards", "Flashcards").value("dark_mode", False, type=bool))


def set_dark(on: bool) -> None:
    QSettings("Flashcards", "Flashcards").setValue("dark_mode", on)


def _fill(template: str, palette: dict) -> str:
    return re.sub(r"@(\w+)", lambda m: palette[m.group(1)], template)


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

MAIN_LIGHT = dict(
    BG="#f4f6f8", TEXT="#17202a", HEADER="#ffffff", BORDER="#e1e5e9", MUTED="#66717d",
    TRACK="#e4e8ec", CARD="#ffffff", CARDB="#e0e5ea", LANG="#7b8794", TRANS="#3578e5",
    SENT="#5a6672", SENTTR="#8a95a1", REVEAL="#17202a", REVEALTXT="#ffffff",
    REVEALH="#2c3945", SEC="#e7ebef", SECTXT="#33404c", SECH="#dce2e7",
    DISB="#e5e8eb", DISF="#a4abb2", INPUT="#ffffff",
)
MAIN_DARK = dict(
    BG="#14171a", TEXT="#e6e9ec", HEADER="#1c2126", BORDER="#2c333a", MUTED="#9aa5b1",
    TRACK="#2c333a", CARD="#1c2126", CARDB="#2c333a", LANG="#8b97a3", TRANS="#6ea2ff",
    SENT="#aab4be", SENTTR="#8793a0", REVEAL="#e6e9ec", REVEALTXT="#14171a",
    REVEALH="#ffffff", SEC="#2c333a", SECTXT="#d5dbe1", SECH="#38424c",
    DISB="#22282e", DISF="#5d6670", INPUT="#1c2126",
)

MAIN_TEMPLATE = """
QMainWindow, QWidget {
    background: @BG;
    color: @TEXT;
    font-family: "Segoe UI", Arial, sans-serif;
}
QLabel { background: transparent; }
QFrame#header { background: @HEADER; border-bottom: 1px solid @BORDER; }
QLabel#title { font-size: 24px; font-weight: 700; }
QLabel#counter { color: @MUTED; font-size: 14px; }
QLabel#stats { color: @MUTED; font-size: 13px; }
QProgressBar { background: @TRACK; border: none; border-radius: 5px; height: 9px; text-align: center; }
QProgressBar::chunk { background: #3578e5; border-radius: 5px; }
QFrame#card { background: @CARD; border: 1px solid @CARDB; border-radius: 20px; }
QLabel#language { color: @LANG; font-size: 13px; font-weight: 600; }
QLabel#word { font-size: 64px; font-weight: 700; }
QLabel#translation { color: @TRANS; font-size: 40px; font-weight: 600; }
QLabel#sentence { color: @SENT; font-size: 24px; font-style: italic; }
QLabel#sentence_tr { color: @SENTTR; font-size: 18px; }
QScrollArea#cardscroll, QWidget#card_body, QWidget#extras_body { background: transparent; border: none; }
QScrollArea#cardscroll > QWidget > QWidget { background: transparent; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 6px 2px; }
QScrollBar::handle:vertical { background: @LANG; border-radius: 4px; min-height: 30px; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px 6px; }
QScrollBar::handle:horizontal { background: @LANG; border-radius: 4px; min-width: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QPushButton { border: none; border-radius: 10px; padding: 11px 18px; font-size: 14px; font-weight: 600; }
QPushButton#reveal { background: @REVEAL; color: @REVEALTXT; }
QPushButton#reveal:hover { background: @REVEALH; }
QPushButton#level0 { background: #e55353; color: white; }
QPushButton#level0:hover { background: #cc4141; }
QPushButton#level1 { background: #e8913a; color: white; }
QPushButton#level1:hover { background: #cf7e2c; }
QPushButton#level2 { background: #8fb339; color: white; }
QPushButton#level2:hover { background: #7b9c2d; }
QPushButton#level3 { background: #2da66a; color: white; }
QPushButton#level3:hover { background: #249258; }
QPushButton#secondary { background: @SEC; color: @SECTXT; }
QPushButton#secondary:hover { background: @SECH; }
QPushButton:disabled { background: @DISB; color: @DISF; }
QLineEdit#search { background: @INPUT; border: 1px solid @BORDER; border-radius: 9px;
                   padding: 7px 12px; font-size: 14px; color: @TEXT; min-width: 230px; }
QLineEdit#search:focus { border: 1px solid #3578e5; }
QMenuBar { background: @HEADER; color: @TEXT; border-bottom: 1px solid @BORDER; }
QMenuBar::item { background: transparent; padding: 4px 10px; }
QMenuBar::item:selected { background: @SEC; }
QMenu { background: @HEADER; color: @TEXT; border: 1px solid @BORDER; }
QMenu::item { padding: 5px 24px; }
QMenu::item:selected { background: @SEC; }
QMenu::item:disabled { color: @DISF; }
QMenu::separator { height: 1px; background: @BORDER; margin: 4px 8px; }
QMessageBox QPushButton { background: @SEC; color: @SECTXT; min-width: 70px; }
QMessageBox QPushButton:hover { background: @SECH; }
"""


def main_style(dark: bool) -> str:
    return _fill(MAIN_TEMPLATE, MAIN_DARK if dark else MAIN_LIGHT)


# ---------------------------------------------------------------------------
# Dialogs (quiz, fill-in-the-blank, sentence practice)
# ---------------------------------------------------------------------------

DIALOG_LIGHT = dict(
    BG="#faf8f5", TEXT="#3d3329", MUTED="#8a7d6e", SOFT="#e8e2d9", SENT="#5e5347",
    CARD="#fbfaf7", CARDB="#e5e0d8", INPUT="#ffffff", INPUTB="#e0dacf", SEL="#d9cdbb",
    FOCUS="#b8a78f", ACC="#8c7a63", ACCH="#7a6a55", BTN="#e5dfd6", BTNH="#d9d2c7",
    IDK="#6b5f52", EXITH="#efeae2", DISF="#b5aa9c", DISB="#f1ede6", ONACC="#ffffff",
)
DIALOG_DARK = dict(
    BG="#1f1d1a", TEXT="#ece6dc", MUTED="#a39a8c", SOFT="#3a362f", SENT="#cfc6b8",
    CARD="#26231f", CARDB="#3a362f", INPUT="#2f2b26", INPUTB="#4a443b", SEL="#5a4f40",
    FOCUS="#a8946f", ACC="#8c7a63", ACCH="#a08c72", BTN="#3a362f", BTNH="#4a443b",
    IDK="#d5ccbd", EXITH="#2f2b26", DISF="#6f675b", DISB="#2a2723", ONACC="#ffffff",
)

DIALOG_TEMPLATE = """
QDialog { background: @BG; }
QDialog QWidget { color: @TEXT; font-family: "Segoe UI", Arial, sans-serif; }
QLabel { background: transparent; }
QLabel#title { font-size: 18px; font-weight: 700; color: @TEXT; }
QLabel#muted { color: @MUTED; font-size: 14px; }
QLabel#hint { color: @MUTED; font-size: 13px; }
QLabel#prompt { font-size: 40px; font-weight: 700; color: @TEXT; }
QLabel#pill { background: @SOFT; color: @TEXT; border-radius: 11px;
              padding: 3px 12px; font-size: 13px; font-weight: 700; }
QLabel#feedback { font-size: 20px; font-weight: 700; }
QLabel#sentence { color: @SENT; font-size: 18px; font-style: italic; }
QLabel#sentence_tr { color: @MUTED; font-size: 15px; }
QLabel#sentence_prompt { font-size: 28px; font-weight: 700; color: @TEXT; }
QLabel#sentence_answer { font-size: 22px; color: @SENT; }
QFrame#quizcard { background: @CARD; border: 1px solid @CARDB; border-radius: 16px; }
QLineEdit { background: @INPUT; border: 1px solid @INPUTB; border-radius: 10px;
            padding: 12px 14px; font-size: 20px; color: @TEXT;
            selection-background-color: @SEL; selection-color: @TEXT; }
QLineEdit:focus { border: 1px solid @FOCUS; }
QProgressBar { background: @SOFT; border: none; border-radius: 4px; max-height: 8px; }
QProgressBar::chunk { background: @ACC; border-radius: 4px; }
QPushButton { background: @BTN; color: @TEXT; border: none; border-radius: 9px;
              padding: 12px 20px; font-size: 14px; font-weight: 700; }
QPushButton:hover { background: @BTNH; }
QPushButton#submit { background: @ACC; color: @ONACC; }
QPushButton#submit:hover { background: @ACCH; }
QPushButton#idk { background: @BTN; color: @IDK; }
QPushButton#idk:hover { background: @BTNH; }
QPushButton#next { background: @ACC; color: @ONACC; }
QPushButton#next:hover { background: @ACCH; }
QPushButton#exit { background: transparent; color: @IDK; padding: 6px 10px; }
QPushButton#exit:hover { color: @TEXT; background: @EXITH; }
QPushButton:disabled { background: @DISB; color: @DISF; }
QCheckBox, QRadioButton { font-size: 15px; color: @TEXT; spacing: 10px; background: transparent; }
QCheckBox:disabled, QRadioButton:disabled { color: @DISF; }
QCheckBox::indicator, QRadioButton::indicator { width: 18px; height: 18px;
              border: 2px solid @FOCUS; background: @INPUT; }
QCheckBox::indicator { border-radius: 5px; }
QRadioButton::indicator { border-radius: 10px; }
QCheckBox::indicator:checked, QRadioButton::indicator:checked { background: @ACC;
              border: 2px solid @ACC; }
QLineEdit#count { padding: 8px 10px; font-size: 16px; border-radius: 8px; }
QLineEdit#count:disabled { color: @DISF; background: @DISB; }
QMessageBox { background: @BG; }
"""


def dialog_style(dark: bool | None = None) -> str:
    """Stylesheet for dialogs; follows the saved dark-mode choice by default."""
    if dark is None:
        dark = is_dark()
    return _fill(DIALOG_TEMPLATE, DIALOG_DARK if dark else DIALOG_LIGHT)
