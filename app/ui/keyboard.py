"""On-screen keyboard for WiFi password entry (480×320).

Printable ASCII (letters, digits, space, punctuation) plus Polish diacritics.
Layers keep every key on screen: letters, symbols (#+=), Polish (ąę).
"""

from __future__ import annotations

import string

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.ui.fonts import font_family
from app.ui.theme import FONT_SIZE_SMALL, IPOD_BG, IPOD_LINE, IPOD_SELECT, IPOD_TEXT

_KEY_H = 26

_LETTER_ROWS = (
    "1234567890",
    "qwertyuiop",
    "asdfghjkl",
    "zxcvbnm",
)
# 32 ASCII punctuation marks, 8 per row — string.punctuation.
_SYMBOL_ROWS = (
    "!@#$%^&*",
    "()-_=+[]",
    "{}|\\:;\"'",
    ",.<>/?`~",
)
_POLISH_ROWS = ("ąćęłńóśźż",)

_PUNCT = set(string.punctuation)


def _covered_punctuation() -> set[str]:
    return set("".join(_SYMBOL_ROWS))


class OnScreenKeyboard(QWidget):
    key_pressed = pyqtSignal(str)
    backspace_pressed = pyqtSignal()
    done_pressed = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        missing = _PUNCT - _covered_punctuation()
        extra = _covered_punctuation() - _PUNCT
        if missing or extra:
            raise RuntimeError(f"keyboard symbols mismatch missing={sorted(missing)} extra={sorted(extra)}")

        self._shift = False
        self._layer = "letters"
        self._letter_keys: list[tuple[QPushButton, str]] = []
        self._polish_keys: list[tuple[QPushButton, str]] = []

        self.setStyleSheet(f"background: {IPOD_BG};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._page(_LETTER_ROWS, self._letter_keys, letters=True))
        self._stack.addWidget(self._page(_SYMBOL_ROWS, None, letters=False))
        self._stack.addWidget(self._page(_POLISH_ROWS, self._polish_keys, letters=True))
        layout.addWidget(self._stack)

        bottom = QHBoxLayout()
        bottom.setSpacing(2)
        self._sym_btn = self._control("#+=", self._toggle_symbols)
        self._shift_btn = self._control("Aa", self._toggle_shift)
        self._pl_btn = self._control("ąę", self._toggle_polish)
        space = self._control("spacja", lambda: self.key_pressed.emit(" "))
        delete = self._control("DEL", self.backspace_pressed.emit)
        ok = self._control("OK", self.done_pressed.emit, accent=True)
        bottom.addWidget(self._sym_btn)
        bottom.addWidget(self._shift_btn)
        bottom.addWidget(self._pl_btn)
        bottom.addWidget(space, stretch=1)
        bottom.addWidget(delete)
        bottom.addWidget(ok)
        layout.addLayout(bottom)
        self._refresh_shift()

    def _page(self, rows: tuple[str, ...], store: list | None, letters: bool) -> QWidget:
        page = QWidget()
        box = QVBoxLayout(page)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(2)
        for row_keys in rows:
            row = QHBoxLayout()
            row.setSpacing(2)
            for ch in row_keys:
                btn = self._char_key(ch)
                row.addWidget(btn, stretch=1)
                if store is not None and letters and ch.isalpha():
                    store.append((btn, ch))
            box.addLayout(row)
        box.addStretch(1)
        return page

    def _char_key(self, ch: str) -> QPushButton:
        btn = self._button(self._label(ch))
        btn.setProperty("char", ch)
        btn.clicked.connect(lambda _=False, b=btn: self.key_pressed.emit(str(b.property("char"))))
        return btn

    def _control(self, label: str, slot, accent: bool = False) -> QPushButton:
        btn = self._button(label, accent=accent)
        btn.setMinimumWidth(36)
        btn.clicked.connect(slot)
        return btn

    def _button(self, label: str, accent: bool = False, active: bool = False) -> QPushButton:
        btn = QPushButton(label)
        btn.setFixedHeight(_KEY_H)
        btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn.setStyleSheet(self._css(accent=accent, active=active))
        return btn

    def _css(self, accent: bool = False, active: bool = False) -> str:
        bg = IPOD_SELECT if accent or active else IPOD_BG
        fg = "white" if accent or active else IPOD_TEXT
        weight = "600" if accent or active else "400"
        return (
            f"QPushButton {{ background: {bg}; color: {fg}; border: 1px solid {IPOD_LINE};"
            f"font-family: '{font_family()}'; font-size: {FONT_SIZE_SMALL}px;"
            f"font-weight: {weight}; padding: 0px; margin: 0px; }}"
        )

    @staticmethod
    def _label(ch: str) -> str:
        # Qt treats '&' as a shortcut marker and would hide the character.
        if ch == "&":
            return "&&"
        return ch

    def _toggle_shift(self) -> None:
        if self._layer == "symbols":
            return
        self._shift = not self._shift
        self._refresh_shift()

    def _toggle_symbols(self) -> None:
        self._set_layer("letters" if self._layer == "symbols" else "symbols")

    def _toggle_polish(self) -> None:
        self._set_layer("letters" if self._layer == "polish" else "polish")

    def _set_layer(self, layer: str) -> None:
        self._layer = layer
        self._stack.setCurrentIndex({"letters": 0, "symbols": 1, "polish": 2}[layer])
        self._sym_btn.setText("abc" if layer == "symbols" else "#+=")
        self._pl_btn.setText("abc" if layer == "polish" else "ąę")
        self._shift_btn.setEnabled(layer != "symbols")
        if layer == "symbols" and self._shift:
            self._shift = False
            self._refresh_shift()
        else:
            self._paint_shift_button()

    def _refresh_shift(self) -> None:
        upper = self._shift
        for btn, base in (*self._letter_keys, *self._polish_keys):
            shown = base.upper() if upper else base
            btn.setProperty("char", shown)
            btn.setText(self._label(shown))
        self._paint_shift_button()

    def _paint_shift_button(self) -> None:
        self._shift_btn.setText("AA" if self._shift else "Aa")
        self._shift_btn.setStyleSheet(self._css(active=self._shift))
