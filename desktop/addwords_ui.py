"""File -> Add words...: type words, copy the prompt for an AI, paste its answer, check it, add it."""
from __future__ import annotations

import json

from PySide6.QtWidgets import (QApplication, QDialog, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton,
                               QVBoxLayout)

import github_pr
import newwords
from addwords import build_prompt, problems_message, summary


class AddWordsDialog(QDialog):
    def __init__(self, workspace, parent=None):
        super().__init__(parent)
        self.workspace = workspace
        self.changed = False
        self._last_errors: list[str] = []
        self.setWindowTitle("Add words")
        self.resize(640, 700)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("1. Type the words (one per line).  2. Copy the prompt into an AI chat.  "
                                "3. Paste its answer below."))
        self.words_edit = QPlainTextEdit()
        self.words_edit.setPlaceholderText("bać się\nbiletomat\nkwaśny / kwaśno")
        layout.addWidget(self.words_edit, 2)
        copy_button = QPushButton("Copy the prompt")
        copy_button.clicked.connect(self.copy_prompt)
        layout.addWidget(copy_button)
        self.answer_edit = QPlainTextEdit()
        self.answer_edit.setPlaceholderText("Paste the AI's answer here")
        layout.addWidget(self.answer_edit, 3)
        self.check_button = QPushButton("Check and add")
        self.check_button.clicked.connect(self.check)
        layout.addWidget(self.check_button)
        self.result = QLabel()
        self.result.setWordWrap(True)
        layout.addWidget(self.result)
        self.copy_errors_button = QPushButton("Copy the problems for the AI")
        self.copy_errors_button.clicked.connect(self.copy_errors)
        self.copy_errors_button.hide()
        layout.addWidget(self.copy_errors_button)

        # ---- send for review (the token stays in local/github_token.txt, which git ignores)
        self.pending_label = QLabel()
        layout.addWidget(self.pending_label)
        self.token_edit = QLineEdit()
        self.token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_edit.setPlaceholderText(f"GitHub token for {github_pr.GITHUB_REPO} (Contents + Pull requests, read & write). "
                                           "Kept only on this computer.")
        layout.addWidget(self.token_edit)
        self.save_token_button = QPushButton("Save token")
        self.save_token_button.clicked.connect(self.save_token)
        layout.addWidget(self.save_token_button)
        self.send_button = QPushButton("Send for review")
        self.send_button.clicked.connect(self.send)
        layout.addWidget(self.send_button)
        self.remove_token_button = QPushButton("Remove token")
        self.remove_token_button.clicked.connect(self.remove_token)
        layout.addWidget(self.remove_token_button)
        self.copy_added_button = QPushButton("Copy what I added instead")
        self.copy_added_button.clicked.connect(self.copy_added)
        layout.addWidget(self.copy_added_button)
        self.link_label = QLabel()
        self.link_label.setOpenExternalLinks(True)
        self.link_label.setWordWrap(True)
        layout.addWidget(self.link_label)
        self.refresh_send()

    def refresh_send(self):
        pending = github_pr.load_pending(self.workspace)
        has_token = bool(github_pr.load_token(self.workspace.root))
        self.pending_label.setText(f"{len(pending)} answer(s) added here, not sent yet." if pending else "")
        for widget in (self.pending_label, self.copy_added_button):
            widget.setVisible(bool(pending))
        self.token_edit.setVisible(bool(pending) and not has_token)
        self.save_token_button.setVisible(bool(pending) and not has_token)
        self.send_button.setVisible(bool(pending) and has_token)
        self.remove_token_button.setVisible(bool(pending) and has_token)

    def save_token(self):
        if self.token_edit.text().strip():
            github_pr.save_token(self.workspace.root, self.token_edit.text())
            self.token_edit.clear()
            self.refresh_send()

    def remove_token(self):
        github_pr.remove_token(self.workspace.root)
        self.refresh_send()

    def send(self):
        pending = github_pr.load_pending(self.workspace)
        self.send_button.setEnabled(False)
        self.link_label.setText("Sending…")
        QApplication.processEvents()
        r = github_pr.send_for_review(github_pr.load_token(self.workspace.root), self.workspace.slug_name, self.workspace.deck, pending)
        self.send_button.setEnabled(True)
        if r["ok"]:
            github_pr.save_pending(self.workspace, [])
            self.link_label.setText(f'Sent! A pull request is open on GitHub: <a href="{r["url"]}">{r["url"]}</a>')
        else:
            if r.get("nothing_new"):
                github_pr.save_pending(self.workspace, [])
            self.link_label.setText(r["error"])
        self.refresh_send()

    def copy_added(self):
        QApplication.clipboard().setText(json.dumps(github_pr.combine(github_pr.load_pending(self.workspace)), ensure_ascii=False, indent=2))
        self.link_label.setText("Copied. Send it to the owner of the repository.")

    def copy_prompt(self):
        try:
            text = build_prompt(self.workspace.root, self.workspace.deck, self.words_edit.toPlainText())
        except (ValueError, OSError) as exc:
            QMessageBox.information(self, "Add words", str(exc))
            return
        QApplication.clipboard().setText(text)
        self.result.setText("Prompt copied. Paste it into your AI.")

    def check(self):
        text = self.answer_edit.toPlainText().strip()
        if not text:
            self.result.setText("Paste the AI's answer first.")
            return
        errors, counts = newwords.check_and_merge(self.workspace.content_dir, text)
        self.copy_errors_button.setVisible(bool(errors))
        if errors:
            self._last_errors = errors
            shown = "\n".join(f"• {e}" for e in errors[:12]) + (f"\n… and {len(errors) - 12} more" if len(errors) > 12 else "")
            self.result.setText(f"{len(errors)} problem(s) found. Nothing was added.\n{shown}")
            return
        self.changed = True
        data, _ = newwords.parse_answer(text)
        github_pr.save_pending(self.workspace, [*github_pr.load_pending(self.workspace), data])
        self.refresh_send()
        self.result.setText(summary(counts))
        self.answer_edit.clear()
        self.words_edit.clear()

    def copy_errors(self):
        QApplication.clipboard().setText(problems_message(self._last_errors))
        self.result.setText(self.result.text() + "\n\nCopied. Paste it back to the AI.")
