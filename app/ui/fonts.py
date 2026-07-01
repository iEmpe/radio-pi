"""Bundled font loading — JetBrains Mono (UI) and Impact (clock)."""

from __future__ import annotations

from pathlib import Path

from PyQt5.QtGui import QFont, QFontDatabase

FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"

UI_FONT_CANDIDATES: tuple[tuple[str, str, str], ...] = (
    ("JetBrainsMono-Regular.ttf", "JetBrainsMono-Bold.ttf", "JetBrains Mono"),
    ("FiraCode-Regular.ttf", "FiraCode-Bold.ttf", "Fira Code"),
)

CLOCK_FONT_FAMILY = "Impact"

_ui_family: str | None = None
_clock_family: str | None = None
_ui_loaded = False
_clock_loaded = False


def _register(path: Path) -> list[str]:
    if not path.is_file():
        return []
    font_id = QFontDatabase.addApplicationFont(str(path))
    if font_id < 0:
        return []
    return QFontDatabase.applicationFontFamilies(font_id)


def ensure_fonts_loaded() -> str:
    """Load UI monospace fonts once; return CSS/Qt family name."""
    global _ui_family, _ui_loaded
    if _ui_loaded and _ui_family:
        return _ui_family

    for regular_name, bold_name, family_hint in UI_FONT_CANDIDATES:
        regular_path = FONTS_DIR / regular_name
        if not regular_path.is_file():
            continue
        families = _register(regular_path)
        bold_path = FONTS_DIR / bold_name
        if bold_path.is_file():
            _register(bold_path)
        if families:
            _ui_family = families[0]
            break
        if family_hint in QFontDatabase().families():
            _ui_family = family_hint
            break

    if not _ui_family:
        _ui_family = "monospace"

    _ui_loaded = True
    return _ui_family


def ensure_clock_font_loaded() -> str:
    """Load Impact Regular for the header clock."""
    global _clock_family, _clock_loaded
    if _clock_loaded and _clock_family:
        return _clock_family

    ensure_fonts_loaded()
    if CLOCK_FONT_FAMILY in QFontDatabase().families():
        _clock_family = CLOCK_FONT_FAMILY
    else:
        _clock_family = ensure_fonts_loaded()

    _clock_loaded = True
    return _clock_family


def ensure_dseg_loaded() -> str:
    """Backward-compatible alias for the clock font loader."""
    return ensure_clock_font_loaded()


def font_family() -> str:
    return ensure_fonts_loaded()


def dseg_family() -> str:
    return ensure_clock_font_loaded()


def ui_font(size_px: int, *, bold: bool = False) -> QFont:
    family = ensure_fonts_loaded()
    font = QFont(family, size_px)
    font.setStyleHint(QFont.Monospace)
    font.setFixedPitch(True)
    font.setBold(bold)
    font.setWeight(QFont.Bold if bold else QFont.Normal)
    return font


def clock_font(size_px: int) -> QFont:
    """Impact Regular — minimal display clock."""
    font = QFont(ensure_clock_font_loaded(), size_px)
    font.setStyleHint(QFont.SansSerif)
    font.setBold(False)
    font.setWeight(QFont.Normal)
    return font


def stylesheet(size_px: int, color: str, *, bold: bool = False) -> str:
    family = ensure_fonts_loaded()
    weight = "bold" if bold else "normal"
    return (
        f"color: {color}; font-family: '{family}'; "
        f"font-size: {size_px}px; font-weight: {weight};"
    )
