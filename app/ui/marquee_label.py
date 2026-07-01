"""Scrolling single-line label for now-playing text."""

from __future__ import annotations

import time

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QColor, QFontMetrics, QPainter
from PyQt5.QtWidgets import QSizePolicy, QWidget

from app.ui.fonts import ui_font
from app.ui.theme import FONT_SIZE_SMALL, TEXT


class MarqueeLabel(QWidget):
    """Monospace marquee — wall-clock ticker, optionally driven by a parent timer."""

    def __init__(
        self,
        parent=None,
        *,
        ticker: bool = False,
        external_drive: bool = False,
        refresh_ms: int = 16,
        speed_px_s: float = 18.0,
        scroll_px: int = 1,
        scroll_ms: int = 50,
        loop_sep: str = "   ",
        background: str | None = None,
    ) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._ticker = ticker
        self._external_drive = external_drive
        self._refresh_ms = max(8, refresh_ms)
        self._speed_px_s = max(1.0, speed_px_s)
        self._scroll_px = max(1, scroll_px)
        self._scroll_ms = max(20, scroll_ms)
        self._loop_sep = loop_sep
        self._text = ""
        self._offset = 0.0
        self._anim_origin = time.monotonic()
        self._gap = 32
        self._font = ui_font(FONT_SIZE_SMALL)
        self._color = QColor(TEXT)
        self._bg = QColor(background) if background else None
        self._scrolling = False
        self._ticker_active = False
        self._seg_w = 0

        if self._bg is not None:
            self.setAttribute(Qt.WA_OpaquePaintEvent, True)
            self.setAttribute(Qt.WA_NoSystemBackground, True)

        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.PreciseTimer)
        self._timer.timeout.connect(self._on_frame)

    def text(self) -> str:
        return self._text

    def set_style(self, style: str) -> None:
        del style

    def set_font(self, family: str, size_px: int, color: str) -> None:
        del family
        self._font = ui_font(size_px)
        self._color = QColor(color)
        if self._text:
            self._apply_text(self._text, reset_anim=False)

    def set_text(self, text: str) -> None:
        text = text.strip()
        if text == self._text:
            return
        self._apply_text(text, reset_anim=True)

    def tick(self) -> None:
        """Advance ticker animation; call from a parent UI timer when external_drive=True."""
        if not self._scrolling or not self._text:
            return
        self.update()

    def _apply_text(self, text: str, *, reset_anim: bool) -> None:
        self._text = text
        if reset_anim:
            self._anim_origin = time.monotonic()
            self._offset = 0.0
            self._ticker_active = False

        if not self._text:
            self._scrolling = False
            self._seg_w = 0
            if not self._external_drive:
                self._timer.stop()
            self.update()
            return

        self._recompute_scroll()
        self.update()

    def _segment(self) -> str:
        if self._ticker:
            return f"{self._text}{self._loop_sep}"
        return self._text

    def _segment_width(self) -> int:
        return QFontMetrics(self._font).horizontalAdvance(self._segment())

    def _text_width(self) -> int:
        return QFontMetrics(self._font).horizontalAdvance(self._text)

    def _needs_scroll(self) -> bool:
        if not self._text:
            return False
        if self._ticker:
            if self._ticker_active:
                return True
            w = self.width()
            if w <= 1:
                return False
            return self._segment_width() > w
        return self._text_width() > max(1, self.width())

    def _scroll_offset(self) -> float:
        if self._ticker:
            if self._seg_w <= 0:
                return 0.0
            elapsed = time.monotonic() - self._anim_origin
            return (elapsed * self._speed_px_s) % self._seg_w
        return self._offset

    def _recompute_scroll(self) -> None:
        if self._ticker:
            self._seg_w = self._segment_width()

        if self._needs_scroll():
            self._scrolling = True
            if self._ticker:
                self._ticker_active = True
            if not self._external_drive:
                interval = self._refresh_ms if self._ticker else self._scroll_ms
                if not self._timer.isActive():
                    self._timer.start(interval)
        elif not self._ticker_active:
            self._scrolling = False
            if not self._external_drive:
                self._timer.stop()
            self._offset = 0.0

    def resizeEvent(self, event) -> None:  # noqa: ANN001, N802
        super().resizeEvent(event)
        if not self._text or self.width() <= 1:
            return
        if self._ticker:
            self._seg_w = self._segment_width()
        self._recompute_scroll()

    def showEvent(self, event) -> None:  # noqa: ANN001, N802
        super().showEvent(event)
        if self._text:
            self._recompute_scroll()

    def _paint_ticker(self, p: QPainter, baseline: int) -> None:
        seg_w = self._seg_w or self._segment_width()
        if seg_w <= 0:
            return
        segment = self._segment()
        offset = self._scroll_offset()
        p.save()
        p.translate(-offset, 0)
        x = 0
        limit = self.width() + seg_w
        while x < limit:
            p.drawText(x, baseline, segment)
            x += seg_w
        p.restore()

    def _paint_center(self, p: QPainter, fm: QFontMetrics, baseline: int) -> None:
        text_w = fm.horizontalAdvance(self._text)
        avail = max(1, self.width())
        cycle = text_w + self._gap
        offset = self._offset % cycle
        p.save()
        p.translate(-offset, 0)
        base_x = (avail - text_w) // 2
        p.drawText(base_x, baseline, self._text)
        p.drawText(base_x + cycle, baseline, self._text)
        p.restore()

    def paintEvent(self, event) -> None:  # noqa: ANN001, N802
        del event
        if not self._text:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.TextAntialiasing)
        if self._bg is not None:
            p.fillRect(self.rect(), self._bg)
        p.setClipRect(self.rect())
        p.setFont(self._font)
        p.setPen(self._color)

        fm = QFontMetrics(self._font)
        baseline = (self.height() + fm.ascent() - fm.descent()) // 2

        if not self._scrolling:
            text_w = fm.horizontalAdvance(self._text)
            x = (max(1, self.width()) - text_w) // 2
            p.drawText(x, baseline, self._text)
        elif self._ticker:
            self._paint_ticker(p, baseline)
        else:
            self._paint_center(p, fm, baseline)

        p.end()

    def _on_frame(self) -> None:
        if not self._scrolling or not self._text:
            return
        if self._ticker:
            self.update()
            return
        self._offset += self._scroll_px
        self.update()
