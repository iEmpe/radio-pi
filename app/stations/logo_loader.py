"""Startup logo preparation — monthly cache, 15 s budget, splash status."""

from __future__ import annotations

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from PyQt5.QtCore import QThread, pyqtSignal

from app.stations.logos import (
    LOGO_TTL_DAYS,
    download_station_logo,
    has_logo,
    logo_needs_refresh,
)

logger = logging.getLogger(__name__)

STARTUP_BUDGET_S = 15
StatusCallback = Callable[[str, str], None]

STATIONS_PATH = Path(__file__).resolve().parent.parent / "data" / "stations.json"


def load_stations(path: Path = STATIONS_PATH) -> List[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def prepare_startup_logos(
    stations: List[dict],
    *,
    budget_s: float = STARTUP_BUDGET_S,
    on_status: Optional[StatusCallback] = None,
) -> Tuple[int, int]:
    """Fetch missing or stale logos within *budget_s* seconds. Returns (ok, total)."""
    total = len(stations)
    if total == 0:
        if on_status:
            on_status("Radio Pi", "Brak stacji")
        return 0, 0

    pending = [st for st in stations if logo_needs_refresh(st)]
    cached = total - len(pending)

    if on_status:
        on_status("Radio Pi", f"Stacje: {total}")
        if not pending:
            on_status("Gotowe", f"Logo w cache ({cached}/{total})")
            return sum(1 for st in stations if has_logo(st)), total
        on_status(
            "Pobieranie logo",
            f"Do pobrania: {len(pending)} · max {int(budget_s)} s",
        )

    deadline = time.monotonic() + budget_s
    attempted = 0

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {}
        for st in pending:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            per_timeout = max(2, min(5, int(remaining)))
            fut = pool.submit(download_station_logo, st, request_timeout=per_timeout)
            futures[fut] = st

        if not futures:
            ok = sum(1 for st in stations if has_logo(st))
            if on_status:
                on_status("Uruchamianie…", f"Logo: {ok}/{total}")
            return ok, total

        try:
            for fut in as_completed(
                futures, timeout=max(0.1, deadline - time.monotonic())
            ):
                st = futures[fut]
                attempted += 1
                name = st.get("name", "?")
                try:
                    ok = fut.result()
                    detail = f"{name} · {attempted}/{len(futures)}"
                    if not ok:
                        detail += " (brak)"
                except Exception as exc:
                    logger.warning("Logo fetch error %s: %s", name, exc)
                    detail = f"{name} · błąd"
                if on_status:
                    on_status("Pobieranie logo", detail)
        except TimeoutError:
            if on_status:
                on_status("Pobieranie logo", "Limit czasu — uruchamiam UI")

    ok = sum(1 for st in stations if has_logo(st))
    if on_status:
        on_status("Uruchamianie…", f"Logo: {ok}/{total}")
    return ok, total


class LogoStartupThread(QThread):
    """Load station logos before the main UI is shown."""

    status_changed = pyqtSignal(str, str)
    finished_loading = pyqtSignal(int, int)

    def __init__(self, stations_path: Path = STATIONS_PATH) -> None:
        super().__init__()
        self._path = stations_path

    def run(self) -> None:
        try:
            stations = load_stations(self._path)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Cannot read stations: %s", exc)
            self.status_changed.emit("Błąd", "Nie można wczytać stacji")
            self.finished_loading.emit(0, 0)
            return

        def report(main: str, detail: str = "") -> None:
            self.status_changed.emit(main, detail)

        ok, total = prepare_startup_logos(
            stations,
            budget_s=STARTUP_BUDGET_S,
            on_status=report,
        )
        logger.info("Startup logos: %d/%d", ok, total)
        self.finished_loading.emit(ok, total)
