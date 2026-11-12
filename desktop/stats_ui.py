"""The hero's stats window: spend the points you get on level-up, see what they do, reset them."""
from __future__ import annotations

from PySide6.QtWidgets import (QDialog, QFrame, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout)

from dungeon import config, stats as stat_rules


class StatsDialog(QDialog):
    def __init__(self, gm, parent=None):
        super().__init__(parent)
        self.gm = gm
        self.setWindowTitle("Stats")
        self.resize(560, 560)
        self.layout_ = QVBoxLayout(self)
        self.layout_.setSpacing(8)
        self.pending = {key: 0 for key in stat_rules.STAT_KEYS}    # chosen, not applied until "Close & confirm"
        self.refresh()

    def _pending_total(self) -> int:
        return sum(self.pending.values())

    def _clear(self) -> None:
        while self.layout_.count():
            item = self.layout_.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._delete_layout(item.layout())

    def _delete_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def refresh(self, note: str = "") -> None:
        self._clear()
        p = self.gm.player
        left = p.stat_points - self._pending_total()
        shown = {key: p.stats[key] + self.pending[key] for key in stat_rules.STAT_KEYS}
        title = QLabel(f"{p.name}  ·  Level {p.level}      🪙 {p.coins}")
        title.setObjectName("title")
        self.layout_.addWidget(title)
        points = (f"✨ {left} point{'s' if left != 1 else ''} to spend" if left
                  else "All points placed. Press Close & confirm to apply them." if p.stat_points
                  else f"No points to spend. You get {stat_rules.POINTS_PER_LEVEL} per level.")
        self.layout_.addWidget(QLabel(points))
        if note:
            self.layout_.addWidget(QLabel(note))
        for key in stat_rules.STAT_KEYS:
            frame = QFrame()
            frame.setObjectName("panel")
            row = QHBoxLayout(frame)
            text = QVBoxLayout()
            extra = f" <span style='color:#f2c14e'>(+{self.pending[key]})</span>" if self.pending[key] else ""
            name = QLabel(f"<b>{stat_rules.STAT_NAMES[key]}: {shown[key]}</b>{extra}")
            desc = QLabel(stat_rules.DESCRIPTIONS[key])
            desc.setWordWrap(True)
            now = QLabel(stat_rules.effect_text(key, shown, config.SELL_FRACTION))
            now.setWordWrap(True)
            text.addWidget(name)
            text.addWidget(desc)
            text.addWidget(now)
            row.addLayout(text, 1)
            if self.pending[key]:
                back = QPushButton("−1")
                back.setToolTip("Take one chosen point back")
                back.clicked.connect(lambda _=False, k=key: self._stage(k, -1))
                row.addWidget(back)
            for amount in (1, 5):
                if amount == 5 and left <= 5:
                    continue
                button = QPushButton(f"+{amount}")
                button.setEnabled(left >= amount)
                button.clicked.connect(lambda _=False, k=key, n=amount: self._stage(k, n))
                row.addWidget(button)
            self.layout_.addWidget(frame)
        spent = sum(p.stats.values())
        cost = self.gm.respec_cost
        reset = QPushButton(f"Reset points ({cost} coins)" if cost else "Reset points (first one is free)")
        reset.setEnabled(spent > 0 and not self._pending_total())
        reset.clicked.connect(self._respec)
        self.layout_.addWidget(reset)
        self.layout_.addStretch()
        close = QPushButton("Close && confirm" if self._pending_total() else "Close")
        close.clicked.connect(self._confirm)
        self.layout_.addWidget(close)

    def _stage(self, stat: str, amount: int) -> None:
        """Choose (or take back) points; nothing is applied until Close & confirm."""
        left = self.gm.player.stat_points - self._pending_total()
        self.pending[stat] = max(0, self.pending[stat] + (amount if amount < 0 else min(amount, left)))
        self.refresh()

    def _confirm(self) -> None:
        try:
            for stat, amount in self.pending.items():
                if amount:
                    self.gm.spend_point(stat, amount)
        except ValueError as exc:
            self.pending = {key: 0 for key in stat_rules.STAT_KEYS}
            self.refresh(str(exc))
            return
        self.pending = {key: 0 for key in stat_rules.STAT_KEYS}
        self.accept()

    def reject(self) -> None:
        """Closing the window another way (X, Esc) leaves the chosen points unapplied."""
        if self._pending_total() and QMessageBox.question(
                self, "Leave without confirming?",
                f"The {self._pending_total()} point(s) you chose will not be applied.") != QMessageBox.StandardButton.Yes:
            return
        super().reject()

    def _respec(self) -> None:
        cost = self.gm.respec_cost
        spent = sum(self.gm.player.stats.values())
        text = (f"This costs {cost} coins and gives all {spent} spent points back." if cost
                else f"The first reset is free. All {spent} spent points come back.")
        if QMessageBox.question(self, "Reset your points?", text) != QMessageBox.StandardButton.Yes:
            return
        try:
            self.gm.respec()
            self.refresh("Points reset. Spend them again.")
        except ValueError as exc:
            self.refresh(str(exc))
