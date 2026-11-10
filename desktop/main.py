import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox

from ui import FlashcardWindow
from workspace import (DEFAULT_DECK, Workspace, choose_deck, decks_of, find_root, save_deck, save_user, saved_deck,
                       saved_user, slug)


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
    deck = choose_deck(root, name, saved_deck(root))
    if deck is None:       # several languages and none chosen yet
        choices = decks_of(root, name)
        deck, ok = QInputDialog.getItem(None, "WordsNSwords", "Which language?", choices, 0, False)
        if not ok:
            return None
    save_deck(root, deck)
    ws = Workspace(root, name, deck)
    if not ws.exists:
        answer = QMessageBox.question(
            None, "No word list found",
            f"There is no word list for \"{name}\" in the repository (users/{slug(name)}/{deck}).\n\n"
            "Create it from the starter deck? You can then add your own words to it.",
        )
        if answer != QMessageBox.StandardButton.Yes or not ws.create_from_template():
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
