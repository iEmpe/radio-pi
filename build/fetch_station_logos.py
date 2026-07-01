#!/usr/bin/env python3
"""Download station favicons into app/assets/stations/."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
STATIONS = REPO / "app" / "data" / "stations.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Cache station logos as PNG files.")
    parser.add_argument(
        "--force-all",
        action="store_true",
        help="Re-download all logos (ignore monthly cache)",
    )
    args = parser.parse_args()

    sys.path.insert(0, str(REPO))
    from app.stations.logos import cached_logo_path, download_station_logo

    stations = json.loads(STATIONS.read_text(encoding="utf-8"))
    ok = 0
    for st in stations:
        name = st.get("name", "?")
        if download_station_logo(st, force=args.force_all):
            path = cached_logo_path(st)
            print(f"ok: {name} -> {path.name if path else '?'}")
            ok += 1
        else:
            print(f"fail: {name}")
    print(f"Done: {ok}/{len(stations)} logos")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
