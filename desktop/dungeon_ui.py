"""Vocabulary Dungeon window (PySide6). All game rules live in the `dungeon` package;
this file only shows the state of `GameManager` and forwards the player's actions."""
from __future__ import annotations

import language
import sys
from html import escape
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from dungeon.battle import ACTIVE, DEFEAT, VICTORY, AnswerResult
from dungeon.dungeons import DUNGEONS
from dungeon import config
from dungeon.items import ARMOR, CHARM, COMPANION, ITEMS, WEAPON
from dungeon.manager import GameManager, RoomOutcome
from dungeon.models import BOSS, REST, TREASURE
from art import HEROES, OUTDOOR_DUNGEONS, art_file, background_file, hero_file, scene_file, ui_file
from dungeon.sprites import SIZE, SPRITE_KEYS, hero_pixels, sprite_pixels

MAP, COMBAT, MESSAGE, SHOP, INVENTORY = 0, 1, 2, 3, 4

STYLE = """
QDialog, QWidget#page { background: #14121f; }
QWidget#pageart { background: transparent; }
QLabel { color: #e8e3ff; font-size: 14px; }
QLabel#title { color: #f2c14e; font-size: 24px; font-weight: bold; }
QLabel#subtitle { color: #a9a0cf; font-size: 13px; }
QLabel#prompt { color: #ffffff; font-size: 34px; font-weight: bold; }
QLabel#caption { color: #a9a0cf; font-size: 13px; }
QLabel#name { color: #f2c14e; font-size: 16px; font-weight: bold; }
QLabel#feedback { font-size: 15px; min-height: 40px; }
QLabel#hint { color: #8fd3ff; font-size: 14px; }
QLabel#missed { color: #ffb86b; font-size: 14px; }
QFrame#panel { background: #221d33; border: 2px solid #3a3157; border-radius: 6px; }
QFrame#board { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #1e1a2b, stop:1 #100d19);
               border: 2px solid #5a4a2e; border-radius: 6px; }
QFrame#slot { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #2b2336, stop:1 #14101c);
              border: 2px solid #8a7140; border-radius: 3px; }
QFrame#slot[empty="true"] { border-color: #3a3157; background: #14101c; }
QLabel#companion_icon { font-size: 44px; }
QLabel#slot_icon { font-size: 34px; }
QLabel#slot_name { color: #f2c14e; font-size: 11px; }
QLabel#slot_empty { color: #5d5580; font-size: 11px; }
QFrame#arena { background: qradialgradient(cx:0.5, cy:0.55, radius:0.8, fx:0.5, fy:0.55, stop:0 #2c2440, stop:1 #0c0a14); border: 2px solid #3a3157; border-radius: 6px; }
QLabel#room { color: #e8e3ff; font-size: 14px; padding: 6px 10px; border-radius: 4px; }
QLabel#room[state="done"] { color: #5ed38a; }
QLabel#room[state="current"] { background: #3a3157; color: #f2c14e; font-weight: bold; }
QLabel#room[state="todo"] { color: #7d74a6; }
QLineEdit { background: #0f0d18; color: #ffffff; border: 2px solid #3a3157;
            border-radius: 4px; padding: 8px; font-size: 18px; }
QLineEdit:focus { border-color: #f2c14e; }
QPushButton { background: #3a3157; color: #e8e3ff; border: 2px solid #52467d;
              border-radius: 4px; padding: 8px 18px; font-size: 14px; }
QPushButton:hover { background: #4a3f70; }
QPushButton:disabled { color: #7d74a6; background: #221d33; }
QPushButton#primary { background: #f2c14e; color: #1b1030; border-color: #f2c14e; font-weight: bold; }
QPushButton#primary:hover { background: #ffd56b; }
QProgressBar { background: #0f0d18; border: 2px solid #3a3157; border-radius: 4px;
               color: #ffffff; text-align: center; min-height: 18px; font-size: 12px; }
QProgressBar#hp::chunk { background: #5ed38a; }
QProgressBar#enemyhp::chunk { background: #ee5f5f; }
QProgressBar#xp::chunk { background: #6aa6ff; }
QLabel#timer { color: #ffb86b; font-size: 18px; font-weight: bold; }
QLabel#ability { color: #ffb86b; font-size: 12px; }
QLabel#section { color: #f2c14e; font-size: 16px; font-weight: bold; padding-top: 8px; }
QFrame#shoprow { background: #221d33; border: 1px solid #3a3157; border-radius: 4px; }
QFrame#shoprow QLabel { background: transparent; }
QPushButton#item { padding: 5px 10px; font-size: 13px; }
QPushButton#dungeon { padding: 8px 12px; }
QPushButton#dungeon:checked { background: #f2c14e; color: #1b1030; border-color: #f2c14e; }
QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; border: none; }
"""

GOOD, BAD, NEUTRAL = "#5ed38a", "#ee5f5f", "#e8e3ff"


def _asset_dir() -> Path:
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
    return base / "assets"


def hero_pixmap(scale: int = 8, gender: str | None = None, weapon: bool = False,
                armor: bool = False) -> QPixmap:
    """The hero picture for his gender and gear, `scale * 36` pixels tall. Without the new art it
    falls back to assets/hero.png, then to the pixel sprite."""
    path = hero_file(gender, weapon, armor) if gender else None
    if path is None:
        path = _asset_dir() / "hero.png"
    image = QPixmap(str(path))
    if image.isNull():
        return sprite_pixmap("hero", scale, hero_pixels(None, None, None), _fallback=True)
    return image.scaledToHeight(scale * 36, Qt.TransformationMode.SmoothTransformation)


_PIXMAPS: dict[tuple[str, str, int], QPixmap] = {}


def art_pixmap(kind: str, key: str, size: int) -> QPixmap | None:
    """A picture from assets/art, fitted into size x size (None when there is none)."""
    cached = _PIXMAPS.get((kind, key, size))
    if cached is not None:
        return cached
    path = art_file(kind, key)
    image = QPixmap(str(path)) if path else QPixmap()
    if image.isNull():
        return None
    image = image.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)
    _PIXMAPS[(kind, key, size)] = image
    return image


def item_pixmap(item, size: int) -> QPixmap | None:
    """The picture of an item or companion, if it has one."""
    return art_pixmap("companions" if item.slot == COMPANION else "items", item.key, size)


def item_icon_html(item, size: int = 22) -> str:
    """The icon for rich text: the picture if there is one, else the emoji."""
    path = art_file("companions" if item.slot == COMPANION else "items", item.key)
    if path:
        return f"<img src='{path.as_uri()}' width='{size}' height='{size}'> "
    return f"{item.icon} " if item.icon else ""


def sprite_pixmap(key: str, scale: int = 8, pixels=None, _fallback: bool = False) -> QPixmap:
    """A monster, companion or scene sprite: its picture if there is one, else the pixel sprite."""
    if key == "hero" and not _fallback:
        return hero_pixmap(scale)
    if pixels is None:
        for kind, factor in (("monsters", 1.3), ("companions", 1.0)):
            art = art_pixmap(kind, key, round(SIZE * scale * factor))
            if art:
                return art
        if key not in SPRITE_KEYS:      # a monster that has no picture and no drawing yet
            key = "slime"
    image = QImage(SIZE, SIZE, QImage.Format.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))
    for y, row in enumerate(pixels if pixels is not None else sprite_pixels(key)):
        for x, colour in enumerate(row):
            if colour:
                image.setPixelColor(x, y, QColor(colour))
    return QPixmap.fromImage(image).scaled(
        SIZE * scale, SIZE * scale, Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.FastTransformation,
    )


ITEM_ICONS = {
    "letter_scroll": "📜", "count_rune": "🔢", "oracle_eye": "🔮", "small_potion": "🧪",
    "big_potion": "⚗️", "fire_bomb": "💣", "lightning": "⚡", "meteor": "☄️",
    "ward_scroll": "🛡️", "passage_scroll": "🌀", "wisdom_tome": "📖", "golden_idol": "🗿",
}
SLOT_ICONS = {WEAPON: "🗡️", ARMOR: "🥋", CHARM: "📿", COMPANION: "🐾"}


def item_icon(item) -> str:
    return item.icon or ITEM_ICONS.get(item.key) or SLOT_ICONS.get(item.slot, "✦")


def _label(text: str = "", name: str | None = None, wrap: bool = False) -> QLabel:
    label = QLabel(text)
    if name:
        label.setObjectName(name)
    label.setWordWrap(wrap)
    return label


def _button(text: str, slot, primary: bool = False) -> QPushButton:
    button = QPushButton(text)
    if primary:
        button.setObjectName("primary")
    button.clicked.connect(slot)
    return button


def _bar(name: str) -> QProgressBar:
    bar = QProgressBar()
    bar.setObjectName(name)
    return bar


def _set_bar(bar: QProgressBar, value: int, maximum: int) -> None:
    bar.setRange(0, max(1, maximum))
    bar.setValue(max(0, min(value, maximum)))
    bar.setFormat(f"{max(0, value)} / {maximum}")




def _clear(layout) -> None:
    """Remove and delete every widget in a layout."""
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.setParent(None)      # leave the layout at once, not at the next event loop
            widget.deleteLater()
        elif item.layout() is not None:
            _clear(item.layout())


class ArtPanel(QFrame):
    """A frame with a picture behind its contents (the stone panel behind the hero and the slots)."""

    def __init__(self, picture: Path | None, dim: int = 90):
        super().__init__()
        self._picture = QPixmap(str(picture)) if picture else QPixmap()
        self._dim = dim
        if not self._picture.isNull():     # the picture is drawn first; the frame draws no fill over it
            self.setStyleSheet("QFrame#board { background: transparent; border: 2px solid #5a4a2e; "
                               "border-radius: 6px; }")

    def paintEvent(self, event) -> None:
        if self._picture.isNull():
            return super().paintEvent(event)
        painter = QPainter(self)
        painter.drawPixmap(self.rect(), self._picture)
        painter.fillRect(self.rect(), QColor(8, 6, 14, self._dim))     # keeps text readable
        painter.end()
        super().paintEvent(event)


def _slot_frame_style(width: int, height: int) -> str:
    """Stylesheet that draws the slot's picture frame (tall slots use the taller frames)."""
    ratio = height / max(1, width)
    name = "slot_weapon" if ratio > 2.5 else "slot_armor" if ratio > 1.5 else "slot_square"
    path = ui_file(name)
    if not path:
        return ""
    return (f"QFrame#slot {{ border-image: url('{path.as_posix()}') 26 26 26 26 stretch stretch; "
            f"border-width: 13px; border-style: solid; background: #0d0b13; }}")


class HeroChoice(QDialog):
    """Shown the first time a player enters the dungeon: click the hero you want. It is final."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Choose your hero")
        self.setStyleSheet(STYLE)
        self.choice: str | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 22)
        title = _label("Choose your hero", "title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        note = _label("Click the hero you want to play. You can't change this later.", "caption")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(note)
        row = QHBoxLayout()
        for gender, name in (("f", "Heroine"), ("m", "Hero")):
            button = QPushButton()
            button.setFlat(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setIcon(hero_pixmap(11, gender))
            button.setIconSize(hero_pixmap(11, gender).size())
            button.setToolTip(f"Play as the {name.lower()}")
            button.clicked.connect(lambda _=False, g=gender: self._pick(g))
            column = QVBoxLayout()
            column.addWidget(button, 0, Qt.AlignmentFlag.AlignCenter)
            caption = _label(name, "name")
            caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
            column.addWidget(caption)
            row.addLayout(column)
        layout.addLayout(row)

    def _pick(self, gender: str) -> None:
        self.choice = gender
        self.accept()


class DungeonWindow(QDialog):
    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        dungeon = getattr(self.gm, "dungeon", None)
        if dungeon is None or self.stack.currentIndex() not in (MAP, COMBAT, MESSAGE):
            return
        key = self._scene if (self._scene and self.stack.currentIndex() == MESSAGE) else dungeon.key
        if key not in self._backdrops:
            path = background_file(key)
            self._backdrops[key] = QPixmap(str(path)) if path else QPixmap()
        picture = self._backdrops[key]
        if picture.isNull():
            return
        painter = QPainter(self)
        scaled = picture.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                Qt.TransformationMode.SmoothTransformation)
        painter.drawPixmap((self.width() - scaled.width()) // 2, (self.height() - scaled.height()) // 2, scaled)
        painter.fillRect(self.rect(), QColor(8, 6, 14, 165))       # dark layer so the text stays readable
        painter.end()

    def __init__(self, deck, save_path, parent=None, hero_name=None, examples_path=None,
                 hero_gender=None):
        super().__init__(parent)
        self.hero_gender = hero_gender
        self.setWindowTitle("Vocabulary Dungeon")
        self.setStyleSheet(STYLE)
        self.resize(900, 800)
        self.setMinimumSize(760, 720)
        self.gm = GameManager(deck, save_path, hero_name=hero_name, examples_path=examples_path)
        self.dungeon_key = self._default_dungeon()
        self.shop_mode = "buy"
        self.remaining = 0

        self.clock = QTimer(self)
        self.clock.setInterval(1000)
        self.clock.timeout.connect(self._tick)

        self.stack = QStackedWidget()
        self._backdrops: dict[str, QPixmap] = {}
        self._scene: str | None = None        # rest / treasure picture for the room just cleared
        self.stack.addWidget(self._build_map())
        self.stack.addWidget(self._build_combat())
        self.stack.addWidget(self._build_message())
        for index in (MAP, COMBAT, MESSAGE):               # let the dungeon scenery show through
            self.stack.widget(index).setObjectName("pageart")
        self.stack.addWidget(self._build_shop())
        self.stack.addWidget(self._build_inventory())
        self.stack.currentChanged.connect(lambda _index: self.update())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)
        self._show_map()

    def _default_dungeon(self) -> str:
        """Resume the dungeon in progress, else the first open one that isn't finished yet."""
        statuses = self.gm.dungeons()
        for pick in (lambda s: s.in_progress and not s.unavailable and s.kind == "story",
                     lambda s: not s.unavailable and not s.completed and s.kind == "story",
                     lambda s: not s.unavailable and s.kind == "story",
                     lambda s: not s.unavailable):
            for s in statuses:
                if pick(s):
                    return s.key
        return statuses[0].key

    # ------------------------------------------------------------------ pages
    def _page(self) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        page.setObjectName("page")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(12)
        return page, layout

    def _player_panel(self) -> tuple[QFrame, dict[str, QWidget]]:
        panel = QFrame()
        panel.setObjectName("panel")
        row = QHBoxLayout(panel)
        row.setContentsMargins(14, 10, 14, 10)
        widgets: dict[str, QWidget] = {
            "name": _label(name="name"), "hp": _bar("hp"), "xp": _bar("xp"),
            "coins": _label(name="name"),
        }
        row.addWidget(widgets["name"])
        row.addWidget(_label("HP", "caption"))
        row.addWidget(widgets["hp"], 1)
        row.addWidget(_label("XP", "caption"))
        row.addWidget(widgets["xp"], 1)
        row.addWidget(widgets["coins"])
        return panel, widgets

    def _refresh_player(self, widgets: dict[str, QWidget]) -> None:
        p = self.gm.player
        widgets["name"].setText(f"{p.name}  Lv {p.level}")
        _set_bar(widgets["hp"], p.hp, p.max_hp)
        _set_bar(widgets["xp"], p.xp, p.xp_needed)
        widgets["coins"].setText(f"🪙 {p.coins}" + (f"     ✨ {p.stat_points} stat point(s) to spend" if p.stat_points else ""))

    # -- map
    def _build_map(self) -> QWidget:
        page, layout = self._page()
        self.map_title = _label(name="title")
        self.map_desc = _label(name="subtitle", wrap=True)
        self.dungeon_row = QGridLayout()
        layout.addLayout(self.dungeon_row)
        layout.addWidget(self.map_title)
        layout.addWidget(self.map_desc)
        panel, self.map_player = self._player_panel()
        layout.addWidget(panel)
        self.gear_label = _label(name="caption", wrap=True)
        layout.addWidget(self.gear_label)

        self.rooms_box = QFrame()
        self.rooms_box.setObjectName("panel")
        self.rooms_layout = QVBoxLayout(self.rooms_box)
        self.rooms_layout.setContentsMargins(12, 10, 12, 10)
        self.rooms_layout.setSpacing(2)
        layout.addWidget(self.rooms_box, 1)

        self.map_missed = _label(name="missed")
        self.map_stats = _label(name="caption", wrap=True)
        layout.addWidget(self.map_missed)
        layout.addWidget(self.map_stats)

        buttons = QHBoxLayout()
        self.enter_button = _button("Begin", self._enter_dungeon, primary=True)
        buttons.addWidget(self.enter_button)
        buttons.addWidget(_button("Inventory", self._show_inventory))
        self.stats_button = _button("Stats", self._open_stats)
        buttons.addWidget(self.stats_button)
        buttons.addWidget(_button("Shop", self._open_shop))
        buttons.addStretch()
        buttons.addWidget(_button("Leave dungeon", self.reject))
        layout.addLayout(buttons)
        return page

    def _pick_dungeon(self, key: str) -> None:
        self.dungeon_key = key
        self._show_map()

    def _show_map(self) -> None:
        self.clock.stop()
        gm = self.gm
        self.stats_button.setText(f"Stats ({gm.player.stat_points})" if gm.player.stat_points else "Stats")
        statuses = {s.key: s for s in gm.dungeons()}
        status = statuses[self.dungeon_key]
        dungeon = DUNGEONS[self.dungeon_key]

        _clear(self.dungeon_row)
        for n, st in enumerate(statuses.values()):
            if st.unavailable:
                text = f"🔒 {st.name}"
            elif st.endless:
                text = f"{st.name}  (best floor {st.best})"
            else:
                text = st.name + ("  ✔" if st.completed else "")
            button = QPushButton(text)
            button.setObjectName("dungeon")
            button.setCheckable(True)
            button.setChecked(st.key == self.dungeon_key)
            button.clicked.connect(lambda _=False, k=st.key: self._pick_dungeon(k))
            self.dungeon_row.addWidget(button, n // 3, n % 3)

        self.map_title.setText(status.name)
        suffix = f"  (needs level {status.min_level})" if status.min_level > 1 else ""
        self.map_desc.setText(status.description + suffix)
        self._refresh_player(self.map_player)
        p = gm.player
        bits = [f"Attack {p.attack_power}"]
        if p.gear_reduction:
            bits.append(f"Armor {p.gear_reduction}")
        names = [ITEMS[k].name for k in gm.inventory.equipped.values()]
        bits.append("Equipped: " + (", ".join(names) if names else "nothing"))
        carried = sum(gm.inventory.counts.values())
        bits.append(f"{carried} item{'s' if carried != 1 else ''} in your bag")
        self.gear_label.setText("   ·   ".join(bits))

        _clear(self.rooms_layout)
        if status.endless:
            self._show_tower_floors(dungeon, status)
            finished = False
        else:
            finished = status.room >= status.total_rooms
            for i, room in enumerate(dungeon.rooms):
                self._room_label(i, room, "done" if finished or i < status.room else
                                 "current" if i == status.room else "todo")

        n = gm.missed_count
        self.map_missed.setText(f"Words to practise: {n}" if n else "No missed words. Nice!")
        s = gm.stats
        self.map_stats.setText(
            f"Monsters defeated: {s['monsters_defeated']}   ·   "
            f"Correct: {s['correct_answers']}   Wrong: {s['wrong_answers']}   ·   "
            f"Deaths: {s['deaths']}   ·   Dungeons completed: {s['dungeons_completed']}"
        )
        if status.unavailable:
            self.enter_button.setText(status.unavailable)
        elif status.endless:
            self.enter_button.setText(f"Continue (floor {status.room + 1})" if status.in_progress
                                      else "Climb the tower")
        else:
            self.enter_button.setText(
                "Play again" if finished else "Continue" if status.in_progress else "Begin")
        self.enter_button.setEnabled(not status.unavailable)
        self.stack.setCurrentIndex(MAP)

    def _room_label(self, index: int, room, state: str) -> None:
        icon = {BOSS: "👑", TREASURE: "💰", REST: "🔥"}.get(room.kind, "⚔")
        mark = {"done": "✔", "current": "▶"}.get(state, "·")
        who = f"  ({config.MONSTERS[room.monster].name})" if room.is_fight else ""
        loot = f"  🎁 {ITEMS[room.drop].name}" if room.drop else ""
        title = room.title if room.title.startswith("Floor") else f"Room {index + 1}: {room.title}"
        label = _label(f"{mark}  {icon}  {title}{who}{loot}", "room")
        label.setProperty("state", state)
        self.rooms_layout.addWidget(label)

    def _show_tower_floors(self, dungeon, status) -> None:
        """An endless dungeon: show the floor before, the current one and the next few."""
        first = max(0, status.room - 1)
        for i in range(first, status.room + 6):
            self._room_label(i, dungeon.room(i), "done" if i < status.room else
                             "current" if i == status.room else "todo")
        self.rooms_layout.addWidget(_label(f"Best floor so far: {status.best}", "caption"))

    def _enter_dungeon(self) -> None:
        if not self.gm.has_words:
            self._message("No words to ask",
                          "The deck has no usable cards (archived cards and cards without a "
                          "translation are skipped).", None, button="Back to the map")
            return
        try:
            self.gm.select_dungeon(self.dungeon_key)
        except ValueError:
            return
        self._enter_room()

    def _enter_room(self) -> None:
        outcome = self.gm.enter_room()
        if outcome is not None:  # treasure or rest room, resolved at once
            self._show_outcome(outcome)
            return
        self._start_fight()

    # -- shop
    def _build_shop(self) -> QWidget:
        page, layout = self._page()
        header = QHBoxLayout()
        header.addWidget(_label("Shop", "title"))
        header.addStretch()
        self.shop_coins = _label(name="name")
        header.addWidget(self.shop_coins)
        layout.addLayout(header)
        tabs = QHBoxLayout()
        self.buy_tab = QPushButton("Buy")
        self.sell_tab = QPushButton("Sell")
        for tab, mode in ((self.buy_tab, "buy"), (self.sell_tab, "sell")):
            tab.setObjectName("dungeon")
            tab.setCheckable(True)
            tab.clicked.connect(lambda _=False, m=mode: self._set_shop_mode(m))
            tabs.addWidget(tab)
        tabs.addStretch()
        layout.addLayout(tabs)
        self.shop_note = _label(name="subtitle", wrap=True)
        layout.addWidget(self.shop_note)

        self.shop_scroll = QScrollArea()
        self.shop_scroll.setWidgetResizable(True)
        body = QWidget()
        self.shop_layout = QVBoxLayout(body)
        self.shop_layout.setContentsMargins(0, 0, 8, 0)
        self.shop_layout.setSpacing(6)
        self.shop_scroll.setWidget(body)
        layout.addWidget(self.shop_scroll, 1)
        layout.addWidget(_button("Back to map", self._show_map, primary=True))
        return page

    def _open_stats(self) -> None:
        from stats_ui import StatsDialog
        StatsDialog(self.gm, self).exec()
        self._show_map()

    def _open_shop(self) -> None:
        self.shop_mode = "buy"
        self._show_shop()

    def _set_shop_mode(self, mode: str) -> None:
        self.shop_mode = mode
        self._show_shop()

    def _show_shop(self, note: str = "") -> None:
        self.clock.stop()
        keep = self.shop_scroll.verticalScrollBar().value()
        selling = self.shop_mode == "sell"
        self.buy_tab.setChecked(not selling)
        self.sell_tab.setChecked(selling)
        default = (f"Sell your things for {round(config.SELL_FRACTION * 100)}% of their price."
                   if selling else "Items are used during fights. Equipment is permanent.")
        self.shop_note.setText(note if isinstance(note, str) and note else default)
        self.shop_coins.setText(f"🪙 {self.gm.player.coins}   ·   Lv {self.gm.player.level}")
        _clear(self.shop_layout)
        if selling:
            self._fill_sell_tab()
            return
        entries = self.gm.shop()
        sections = (
            ("One-time items", lambda e: not e.item.is_equipment),
            ("Weapons", lambda e: e.item.slot == WEAPON),
            ("Armor", lambda e: e.item.slot == ARMOR),
            ("Charms", lambda e: e.item.slot == CHARM),
            ("Companions (one at a time)", lambda e: e.item.slot == COMPANION),
        )
        for title, pick in sections:
            self.shop_layout.addWidget(_label(title, "section"))
            for entry in entries:
                if pick(entry):
                    self.shop_layout.addWidget(self._shop_row(entry))
        self.shop_layout.addStretch()
        self.stack.setCurrentIndex(SHOP)
        QTimer.singleShot(0, lambda: self.shop_scroll.verticalScrollBar().setValue(keep))

    def _shop_row(self, entry) -> QFrame:
        item = entry.item
        row = QFrame()
        row.setObjectName("shoprow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(10, 6, 10, 6)
        extra = f"  ·  you have {entry.count}" if entry.count else ""
        price = (f"<span style='color:#f2c14e'>{item.price} coins</span>  ·  level {item.level}"
                 if item.shop else "<span style='color:#f2c14e'>Tower trophy</span>")
        icon = item_icon_html(item)
        text = _label(f"<b>{icon}{escape(item.name)}</b> — {escape(item.description)}<br>"
                      f"{price}{extra}", wrap=True)
        text.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(text, 1)
        if entry.owned:
            if entry.equipped:
                button = QPushButton("Equipped")
                button.setEnabled(False)
            else:
                button = _button("Equip", lambda _=False, k=item.key: self._equip(k))
        elif entry.problem:
            button = QPushButton(entry.problem)
            button.setEnabled(False)
        else:
            button = _button("Buy", lambda _=False, k=item.key: self._buy(k), primary=True)
        button.setMinimumWidth(140)
        layout.addWidget(button)
        return row

    def _fill_sell_tab(self) -> None:
        entries = self.gm.sellable()
        if not entries:
            self.shop_layout.addWidget(_label("You have nothing to sell.", "caption"))
        for entry in entries:
            item = entry.item
            row = QFrame()
            row.setObjectName("shoprow")
            layout = QHBoxLayout(row)
            layout.setContentsMargins(10, 6, 10, 6)
            icon = item_icon_html(item)
            extra = (f"  ·  you have {entry.count}" if not item.is_equipment
                     else "  ·  equipped" if entry.equipped else "")
            text = _label(f"<b>{icon}{escape(item.name)}</b> — {escape(item.description)}<br>"
                          f"<span style='color:#f2c14e'>Sells for {entry.value} coins</span>{extra}",
                          wrap=True)
            text.setTextFormat(Qt.TextFormat.RichText)
            layout.addWidget(text, 1)
            button = _button(f"Sell for {entry.value}", lambda _=False, k=item.key: self._sell(k))
            button.setMinimumWidth(140)
            layout.addWidget(button)
            self.shop_layout.addWidget(row)
        self.shop_layout.addStretch()
        self.stack.setCurrentIndex(SHOP)

    def _sell(self, key: str) -> None:
        item = ITEMS[key]
        if item.is_equipment and self.gm.inventory.is_equipped(key) or item.price >= 1000:
            answer = QMessageBox.question(
                self, "Sell", f"Sell {item.name} for {self.gm.inventory.sell_value(item)} coins?")
            if answer != QMessageBox.StandardButton.Yes:
                return
        try:
            note = self.gm.sell(key)
        except ValueError as exc:
            note = str(exc)
        self._show_shop(note)

    def _buy(self, key: str) -> None:
        try:
            note = self.gm.buy(key)
        except ValueError as exc:
            note = str(exc)
        self._show_shop(note)

    def _equip(self, key: str) -> None:
        self.gm.equip(key)
        self._show_shop(f"Equipped {ITEMS[key].name}.")

    # -- inventory
    def _slot(self, item, caption: str, width: int = 96, height: int = 96,
              badge: str = "") -> QFrame:
        """One square of the paper doll: the item's icon in a dark, gold-rimmed frame."""
        slot = QFrame()
        slot.setObjectName("slot")
        slot.setProperty("empty", "false" if item else "true")
        slot.setFixedSize(width, height)
        frame = _slot_frame_style(width, height)
        if frame:
            slot.setStyleSheet(frame)
        box = QVBoxLayout(slot)
        box.setContentsMargins(*(((16, 16, 16, 14) if frame else (4, 4, 4, 4))))
        box.setSpacing(0)
        art = item_pixmap(item, max(32, min(width, height) - 30)) if item else None
        icon = _label("" if item and (item.slot == COMPANION or art) else (item_icon(item) if item else ""),
                      "slot_icon")
        if art:
            icon.setPixmap(art)
        elif item and item.slot == COMPANION:
            icon.setPixmap(sprite_pixmap(item.key, 2))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box.addWidget(icon, 1)
        text = (f"{item.name}{badge}" if item else caption)
        name = _label(text, "slot_name" if item else "slot_empty", wrap=True)
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box.addWidget(name)
        if item:
            slot.setToolTip(f"{item.name}\n{item.description}")
        else:
            slot.setToolTip(caption)
        return slot

    def _build_inventory(self) -> QWidget:
        page, layout = self._page()
        layout.addWidget(_label("Inventory", "title"))
        panel, self.inv_player = self._player_panel()
        layout.addWidget(panel)

        main = QHBoxLayout()
        main.setSpacing(14)
        # left: the hero, drawn with his gear
        hero_box = ArtPanel(ui_file("panel"))
        hero_box.setObjectName("board")
        hero_col = QVBoxLayout(hero_box)
        hero_col.setContentsMargins(14, 12, 14, 12)
        self.inv_hero = QLabel()
        self.inv_hero.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.inv_hero.setMinimumSize(260, 260)
        hero_col.addWidget(self.inv_hero)
        self.inv_stats = _label(name="caption", wrap=True)
        self.inv_stats.setTextFormat(Qt.TextFormat.RichText)
        hero_col.addWidget(self.inv_stats)
        hero_col.addStretch()
        main.addWidget(hero_box, 2)
        # right: the Path of Exile style doll
        board = ArtPanel(ui_file("panel"))
        board.setObjectName("board")
        self.inv_grid = QGridLayout(board)
        self.inv_grid.setContentsMargins(14, 12, 14, 12)
        self.inv_grid.setSpacing(8)
        main.addWidget(board, 3)
        layout.addLayout(main)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        self.inv_layout = QVBoxLayout(body)
        self.inv_layout.setContentsMargins(0, 0, 8, 0)
        self.inv_layout.setSpacing(6)
        scroll.setWidget(body)
        layout.addWidget(scroll, 1)
        buttons = QHBoxLayout()
        buttons.addWidget(_button("Back to map", self._show_map, primary=True))
        buttons.addWidget(_button("Shop", self._open_shop))
        buttons.addStretch()
        layout.addLayout(buttons)
        return page

    def _show_inventory(self) -> None:
        self.clock.stop()
        gm = self.gm
        p = gm.player
        self._refresh_player(self.inv_player)
        inv = gm.inventory
        worn = {slot: ITEMS[k] for slot, k in inv.equipped.items()}

        # Paper doll (Path of Exile style): weapon | companion over armor | charm, then the belt.
        _clear(self.inv_grid)
        self.inv_hero.setPixmap(self._hero_pixmap(8))
        self.inv_grid.addWidget(self._slot(worn.get(WEAPON), "Weapon", 100, 300), 0, 0, 3, 1)
        self.inv_grid.addWidget(self._slot(worn.get(COMPANION), "Companion", 100, 100), 0, 1)
        self.inv_grid.addWidget(self._slot(worn.get(ARMOR), "Armor", 100, 200), 1, 1, 2, 1)
        self.inv_grid.addWidget(self._slot(worn.get(CHARM), "Charm", 100, 100), 0, 2)
        bag = [(ITEMS[k], n) for k, n in inv.counts.items()]
        total = max(8, -(-len(bag) // 4) * 4)
        belt_box = QWidget()
        belt = QGridLayout(belt_box)
        belt.setContentsMargins(0, 0, 0, 0)
        belt.setSpacing(6)
        for n_slot in range(total):
            if n_slot < len(bag):
                item, n = bag[n_slot]
                belt.addWidget(self._slot(item, "", 72, 72, f" ×{n}"), n_slot // 4, n_slot % 4)
            else:
                belt.addWidget(self._slot(None, "·", 72, 72), n_slot // 4, n_slot % 4)
        rows = total // 4
        belt_box.setFixedSize(4 * 72 + 3 * 6, rows * 72 + (rows - 1) * 6)   # known size from the start
        self.inv_grid.addWidget(belt_box, 3, 0, 1, 3, Qt.AlignmentFlag.AlignHCenter)

        t = inv.totals()
        lines = [f"<b>{escape(p.name)}</b> — level {p.level}  ·  Attack {p.attack_power}  ·  "
                 f"Max HP {p.max_hp}  ·  Armor {p.gear_reduction}"]
        extras = []
        if t.xp_pct:
            extras.append(f"+{t.xp_pct}% XP")
        if t.coin_pct:
            extras.append(f"+{t.coin_pct}% coins")
        if t.time:
            extras.append(f"+{t.time}s per timed question")
        if t.dodge_pct:
            extras.append(f"{t.dodge_pct}% dodge")
        if t.heal_on_correct:
            extras.append(f"heal {t.heal_on_correct} HP per correct answer")
        if t.bonus_damage:
            extras.append(f"+{t.bonus_damage} damage")
        if t.phoenix:
            extras.append("phoenix revival")
        if t.start_ward:
            extras.append("starts fights with a ward")
        if extras:
            lines.append("Bonuses: " + ", ".join(extras))
        lines.append(f"Companion: {escape(t.companion)}" if t.companion else "Companion: none")
        self.inv_stats.setText("<br>".join(lines))

        _clear(self.inv_layout)
        spare = [ITEMS[k] for k in sorted(inv.owned) if not inv.is_equipped(k)]
        self.inv_layout.addWidget(_label("In your stash (not equipped)", "section"))
        if not spare:
            self.inv_layout.addWidget(_label("Nothing else. Buy or find more gear!", "caption"))
        for item in spare:
            row = QHBoxLayout()
            label = _label(f"{item_icon_html(item, 28) or item_icon(item) + ' '}<b>{escape(item.name)}</b> — {escape(item.description)}",
                           wrap=True)
            label.setTextFormat(Qt.TextFormat.RichText)
            row.addWidget(label, 1)
            row.addWidget(_button("Equip", lambda _=False, k=item.key: self._equip_inventory(k)))
            holder = QWidget()
            holder.setLayout(row)
            self.inv_layout.addWidget(holder)
        self.inv_layout.addStretch()
        self.stack.setCurrentIndex(INVENTORY)
        self._relayout(self.stack.widget(INVENTORY))
        QTimer.singleShot(0, lambda: self._relayout(self.stack.widget(INVENTORY)))

    def _relayout(self, page) -> None:
        """Make Qt lay the page out now: a page filled while hidden is otherwise laid out
        with stale sizes until the window is moved or resized."""
        for layout in (self.inv_grid, self.inv_layout, page.layout()):
            if layout is not None:
                layout.invalidate()
                layout.activate()
        page.updateGeometry()
        page.adjustSize()

    def _equip_inventory(self, key: str) -> None:
        self.gm.equip(key)
        self._show_inventory()

    # -- combat
    def _build_combat(self) -> QWidget:
        page, layout = self._page()
        panel, self.fight_player = self._player_panel()
        layout.addWidget(panel)

        arena = QFrame()
        arena.setObjectName("arena")
        arena_row = QHBoxLayout(arena)
        arena_row.setContentsMargins(20, 10, 20, 10)
        self.hero_sprite = QLabel()
        self.hero_sprite.setPixmap(self._hero_pixmap(7))
        self.hero_sprite.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.monster_sprite = QLabel()
        self.monster_sprite.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.monster_name = _label(name="name")
        self.monster_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.monster_abilities = _label(name="ability", wrap=True)
        self.monster_abilities.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.monster_hp = _bar("enemyhp")
        monster_col = QVBoxLayout()
        monster_col.addWidget(self.monster_name)
        monster_col.addWidget(self.monster_sprite)
        monster_col.addWidget(self.monster_hp)
        monster_col.addWidget(self.monster_abilities)
        self.companion_icon = _label(name="companion_icon")
        self.companion_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.companion_label = _label(name="ability")
        self.companion_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hero_name = _label(name="name")
        self.hero_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hero_hp = _bar("hp")
        hero_col = QVBoxLayout()     # same layout as the monster's: name, picture, health bar
        hero_col.addWidget(self.hero_name)
        hero_col.addWidget(self.hero_sprite)
        hero_col.addWidget(self.hero_hp)
        hero_col.addWidget(self.companion_icon)
        hero_col.addWidget(self.companion_label)
        arena_row.addLayout(hero_col, 1)
        arena_row.addWidget(_label("VS", "title"))
        arena_row.addLayout(monster_col, 1)
        layout.addWidget(arena)

        self.fight_feedback = _label(name="feedback", wrap=True)
        layout.addWidget(self.fight_feedback)
        caption_row = QHBoxLayout()
        self.prompt_caption = _label(name="caption")
        self.timer_label = _label(name="timer")
        caption_row.addWidget(self.prompt_caption)
        caption_row.addStretch()
        caption_row.addWidget(self.timer_label)
        layout.addLayout(caption_row)
        self.prompt = _label(name="prompt", wrap=True)
        layout.addWidget(self.prompt)
        self.hint_label = _label(name="hint", wrap=True)
        self.hint_label.setTextFormat(Qt.TextFormat.RichText)
        self.hint_label.hide()
        layout.addWidget(self.hint_label)

        self.answer_edit = QLineEdit()
        self.answer_edit.returnPressed.connect(self._submit)
        layout.addWidget(self.answer_edit)

        buttons = QHBoxLayout()
        self.submit_button = _button("Attack", self._submit, primary=True)
        self.skip_button = _button("Skip", self._skip)
        buttons.addWidget(self.submit_button)
        buttons.addWidget(self.skip_button)
        buttons.addStretch()
        buttons.addWidget(_button("Back to map", self._leave_fight))
        layout.addLayout(buttons)

        self.item_row = QHBoxLayout()
        layout.addLayout(self.item_row)
        return page

    def _hero_pixmap(self, scale: int) -> QPixmap:
        """The hero as he looks with the weapon and armor he currently wears."""
        worn = self.gm.inventory.equipped
        return hero_pixmap(scale, self.hero_gender, bool(worn.get(WEAPON)), bool(worn.get(ARMOR)))

    def _start_fight(self) -> None:
        self.hero_sprite.setPixmap(self._hero_pixmap(7))
        spec = self.gm.battle.monster.spec
        self.monster_sprite.setPixmap(sprite_pixmap(spec.key, 6))
        self.monster_name.setText(spec.name + ("  (boss)" if spec.boss else ""))
        self.monster_abilities.setText(" · ".join(spec.abilities))
        companion = self.gm.inventory.equipped.get(COMPANION)
        if companion:
            self.companion_icon.setPixmap(sprite_pixmap(companion, 3))
        self.companion_icon.setVisible(bool(companion))
        self.companion_label.setText(ITEMS[companion].name if companion else "")
        self.fight_feedback.setText(f"A {spec.name} blocks your way!")
        self.fight_feedback.setStyleSheet(f"color: {NEUTRAL};")
        self._refresh_fight()
        self.stack.setCurrentIndex(COMBAT)
        self._ask()

    def _refresh_fight(self) -> None:
        battle = self.gm.battle
        self._refresh_player(self.fight_player)
        p = self.gm.player
        self.hero_name.setText(f"{p.name}  Lv {p.level}")
        _set_bar(self.hero_hp, p.hp, p.max_hp)
        _set_bar(self.monster_hp, battle.monster.hp, battle.monster.max_hp)
        self._refresh_items()

    def _refresh_items(self) -> None:
        _clear(self.item_row)
        carried = self.gm.usable_items()
        if carried:
            self.item_row.addWidget(_label("Items:", "caption"))
        for item, count in carried:
            button = QPushButton(f"{item.name} ×{count}")
            button.setObjectName("item")
            button.setToolTip(item.description)
            button.clicked.connect(lambda _=False, k=item.key: self._use_item(k))
            self.item_row.addWidget(button)
        self.item_row.addStretch()

    def _ask(self) -> None:
        question = self.gm.next_question()
        if question is None:
            self.clock.stop()
            self._message("No words to ask", "No usable cards are left in the deck.", None,
                          button="Back to the map")
            return
        lang = question.target_language
        if question.is_cloze:
            self.prompt_caption.setText(f"Fill in the blank (meaning of the missing word: {question.gloss})")
            self.answer_edit.setPlaceholderText(f"Type the missing {language.name()} word and press Enter")
            self.prompt.setStyleSheet("font-size: 22px;")
        else:
            self.prompt_caption.setText(f"Translate into {lang}:")
            self.answer_edit.setPlaceholderText(f"Type the {lang} translation and press Enter")
            self.prompt.setStyleSheet("")
        self.prompt.setText(question.prompt)
        self.hint_label.hide()
        self.answer_edit.clear()
        if question.time_limit:
            self.remaining = question.time_limit
            self._show_time()
            self.clock.start()
        else:
            self.clock.stop()
            self.timer_label.setText("")
        if question.show_first:  # Scholar's Monocle
            self._show_hint(self.gm.battle.hint_text())
        self.answer_edit.setFocus()

    def _show_time(self) -> None:
        self.timer_label.setText(f"⏳ {self.remaining}s")

    def _tick(self) -> None:
        battle = self.gm.battle
        if battle is None or battle.state != ACTIVE or battle.question is None:
            self.clock.stop()
            return
        self.remaining -= 1
        self._show_time()
        if self.remaining <= 0:
            self.clock.stop()
            self._apply(self.gm.timeout())

    def _submit(self) -> None:
        text = self.answer_edit.text().strip()
        if not text or self.gm.battle is None or self.gm.battle.state != ACTIVE:
            return  # an empty Enter is ignored; use Skip to give up
        self._apply(self.gm.answer(text))

    def _skip(self) -> None:
        if self.gm.battle is not None and self.gm.battle.state == ACTIVE:
            self._apply(self.gm.skip())

    def _show_hint(self, text: str) -> None:
        self.hint_label.setText("💡 " + escape(text).replace("\n", "<br>"))
        self.hint_label.show()

    def _use_item(self, key: str) -> None:
        result = self.gm.use_item(key)
        self.fight_feedback.setText(result.message)
        self.fight_feedback.setStyleSheet(f"color: {GOOD if result.ok else BAD};")
        if not result.ok:
            return
        if result.hint:
            self._show_hint(result.hint)
        self._refresh_fight()
        if result.result is not None:      # Passage Scroll: on to the next word
            self._ask()
        elif result.state == VICTORY:
            self.clock.stop()
            self._show_outcome(self.gm.outcome, lead=result.message)
            return
        self.answer_edit.setFocus()

    def _apply(self, result: AnswerResult) -> None:
        self.clock.stop()
        self.fight_feedback.setText(result.message)
        self.fight_feedback.setStyleSheet(f"color: {GOOD if result.correct else BAD};")
        self._refresh_fight()
        self._flash(self.monster_sprite if result.correct else self.hero_sprite)
        if result.state == VICTORY:
            self._show_outcome(self.gm.outcome, lead=result.message)
        elif result.state == DEFEAT:
            self._defeat(result.message)
        else:
            self._ask()

    def _flash(self, sprite: QLabel) -> None:
        sprite.setStyleSheet("background: #7a2530; border-radius: 6px;")
        QTimer.singleShot(180, lambda: sprite.setStyleSheet(""))

    def _leave_fight(self) -> None:
        self.clock.stop()
        self.gm.leave()
        self._show_map()

    # -- messages (victory, defeat, treasure, rest, completion)
    def _build_message(self) -> QWidget:
        page, layout = self._page()
        layout.addStretch()
        self.msg_sprite = QLabel()
        self.msg_sprite.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.msg_title = _label(name="title")
        self.msg_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.msg_body = _label(wrap=True)
        self.msg_body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.msg_body.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self.msg_sprite)
        layout.addWidget(self.msg_title)
        layout.addWidget(self.msg_body)
        buttons = QHBoxLayout()
        buttons.addStretch()
        self.msg_primary = QPushButton()
        self.msg_primary.setObjectName("primary")
        self.msg_primary.clicked.connect(lambda: self._on_message(0))
        self.msg_secondary = QPushButton()
        self.msg_secondary.clicked.connect(lambda: self._on_message(1))
        buttons.addWidget(self.msg_primary)
        buttons.addWidget(self.msg_secondary)
        buttons.addStretch()
        layout.addLayout(buttons)
        layout.addStretch()
        self._callbacks = [self._show_map, self._show_map]
        return page

    def _message(self, title: str, body: str, sprite: str | None, button: str = "Continue",
                 on_primary=None, secondary: str | None = None, on_secondary=None) -> None:
        self.clock.stop()
        self._scene = None
        if sprite:
            self.msg_sprite.setPixmap(sprite_pixmap(sprite, 8))
            self.msg_sprite.show()
        else:
            self.msg_sprite.hide()
        self.msg_title.setText(title)
        self.msg_body.setText(body)
        self.msg_primary.setText(button)
        self.msg_secondary.setText(secondary or "")
        self.msg_secondary.setVisible(bool(secondary))
        self._callbacks = [on_primary or self._show_map, on_secondary or self._show_map]
        self.stack.setCurrentIndex(MESSAGE)
        self.msg_primary.setFocus()

    def _on_message(self, index: int) -> None:
        self._callbacks[index]()

    @staticmethod
    def _html(lines: list[str]) -> str:
        return "<br>".join(escape(line) for line in lines if line)

    def _failed_lines(self) -> list[str]:
        """After a review fight: every word you failed, with its meaning."""
        if self.gm.dungeon is None or self.gm.dungeon.kind != "review":
            return []
        failed = self.gm.review_failed_words
        if not failed:
            return ["", "No words failed. Perfect review!"]
        return ["", f"Words you failed ({len(failed)}):", *[f"{word} = {meaning}" for word, meaning in failed]]

    def _show_outcome(self, outcome: RoomOutcome, lead: str = "") -> None:
        if outcome.dungeon_completed:
            self._completion(outcome)
            return
        titles = {TREASURE: "Treasure!", REST: "A moment of rest"}
        sprite = {TREASURE: "treasure", REST: "rest"}.get(outcome.kind)
        title = titles.get(outcome.kind, "Victory!")
        scene = None
        if sprite is not None and scene_file(sprite, self.gm.dungeon.key):   # a picture of the place
            scene = f"{sprite}_" + ("outdoor" if self.gm.dungeon.key in OUTDOOR_DUNGEONS else "indoor")
            sprite = None
        elif sprite is None:
            sprite = self.gm.battle.monster.spec.key if self.gm.battle else None
        self._message(title, self._html([lead, *outcome.messages]), sprite,
                      button="Next floor" if self.gm.dungeon.endless else "Next room",
                      on_primary=self._enter_room,
                      secondary="Back to map", on_secondary=self._to_map)
        self._scene = scene
        self.update()

    def _to_map(self) -> None:
        self.gm.leave()
        self._show_map()

    def _defeat(self, lead: str) -> None:
        self._message("Defeated...",
                      self._html([lead, "You wake up at the dungeon entrance, fully healed. "
                                  "The monster has recovered too.", *self._failed_lines()]),
                      "hero", button="Try again", on_primary=self._retry,
                      secondary="Back to map", on_secondary=self._to_map)

    def _retry(self) -> None:
        self.gm.retry()
        self._start_fight()

    def _completion(self, outcome: RoomOutcome) -> None:
        run = outcome.run
        p = self.gm.player
        review = self.gm.dungeon is not None and self.gm.dungeon.kind == "review"   # its reward is already listed once above
        lines = [
            *outcome.messages, "",
            f"Monsters defeated: {run.get('monsters', 0)}",
            *([f"Missed words cleared: {run['cleared']}"] if run.get("cleared") else []),
            f"Correct answers: {run.get('correct', 0)}   Wrong answers: {run.get('wrong', 0)}",
            *([] if review else [f"XP earned: {run.get('xp', 0)}   Coins earned: {run.get('coins', 0)}"]),
            f"You are now level {p.level} with {p.coins} coins.",
            f"Words to practise: {self.gm.missed_count}",
            *self._failed_lines(),
        ]
        sprite = self.gm.battle.monster.spec.key if self.gm.battle else "hero"
        self._message("Dungeon completed!", self._html(lines), sprite, button="Back to map",
                      on_primary=self._to_map, secondary="Visit the shop",
                      on_secondary=self._open_shop)

    # --------------------------------------------------------------- closing
    def reject(self) -> None:
        # Esc during a fight returns to the map instead of closing the window.
        if self.stack.currentIndex() == COMBAT:
            self._leave_fight()
            return
        if self.stack.currentIndex() in (SHOP, INVENTORY):
            self._show_map()
            return
        self.clock.stop()
        self.gm.leave()
        super().reject()

    def closeEvent(self, event) -> None:
        self.clock.stop()
        self.gm.leave()
        super().closeEvent(event)
