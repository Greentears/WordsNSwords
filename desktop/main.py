import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox

from ui import FlashcardWindow
import language
from workspace import (Workspace, choose_deck, decks_of, find_root, is_new_name, save_deck, save_user, saved_deck,
                       saved_user, slug, template_decks)


def _ask_name(root: Path, current: str = "") -> str | None:
    name, ok = QInputDialog.getText(
        None, "WordsNSwords", "Your name (it is also your hero's name):", text=current)
    name = name.strip()
    if not ok or not slug(name):
        return None
    save_user(root, name)
    return name


def _workspace(root: Path) -> Workspace | None:
    """The words of the saved name, created from the starter deck if the repo has none yet."""
    name = saved_user(root) or _ask_name(root)
    if not name:
        return None
    if is_new_name(root, name):            # nobody by this name yet: pick a language, start from its starter deck
        return _new_user(root, name)
    deck = choose_deck(root, name, saved_deck(root))
    if deck is None:       # several languages and none chosen yet
        choices = decks_of(root, name)
        deck, ok = QInputDialog.getItem(None, "WordsNSwords", "Which language?", choices, 0, False)
        if not ok:
            return None
    save_deck(root, deck)
    ws = Workspace(root, name, deck)
    if not ws.exists:                      # no words for this name and language: pick a language, then the starter deck
        return _new_user(root, name)
    return ws


def _language_label(deck: str) -> str:
    code = deck.split("-")[0]
    return language.NAMES.get(code, code.upper())


def _new_user(root: Path, name: str) -> Workspace | None:
    decks = template_decks(root)
    if len(decks) == 1:
        deck = decks[0]
    else:
        labels = [_language_label(d) for d in decks]
        label, ok = QInputDialog.getItem(
            None, "WordsNSwords",
            f"Welcome, {name}! Which language do you want to learn?\n"
            "You start with a small starter deck of 20 words and can add your own later.",
            labels, 0, False)
        if not ok:
            return None
        deck = decks[labels.index(label)]
    save_deck(root, deck)
    ws = Workspace(root, name, deck)
    if not ws.create_from_template():
        QMessageBox.warning(None, "No starter deck", f"There is no starter deck for {_language_label(deck)} in users/_template.")
        return None
    return ws


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("WordsNSwords")

    # When packaged as an .exe, look next to the executable; otherwise next to this file.
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent

    root = find_root(base)
    if root is None:
        # No repository around (a loose copy): the old behaviour, words.json next to the program.
        window = FlashcardWindow(base / "words.json")
    else:
        workspace = _workspace(root)
        if workspace is None:
            sys.exit(0)
        window = FlashcardWindow(workspace.words_path, workspace)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
