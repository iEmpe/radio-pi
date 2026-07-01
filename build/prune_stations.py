#!/usr/bin/env python3
"""Remove dead streams from app/data/stations.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
STATIONS = REPO / "app" / "data" / "stations.json"


def main() -> int:
    sys.path.insert(0, str(REPO))
    from app.stations.validate import validate_stream

    data = json.loads(STATIONS.read_text(encoding="utf-8"))
    kept = []
    seen_urls: set[str] = set()
    seen_names: set[str] = set()

    for st in data:
        name = (st.get("name") or "").strip()
        url = st.get("url", "")
        norm = name.casefold()
        if not name or not url:
            print(f"DROP empty: {name!r}")
            continue
        if url in seen_urls or norm in seen_names:
            print(f"DROP duplicate: {name}")
            continue
        ok, detail = validate_stream(url)
        if not ok:
            print(f"DROP dead: {name} ({detail})")
            continue
        seen_urls.add(url)
        seen_names.add(norm)
        kept.append(st)
        print(f"KEEP {name} ({detail})")

    STATIONS.write_text(json.dumps(kept, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\n{len(data)} -> {len(kept)} stations")
    return 0


if __name__ == "__main__":
    sys.exit(main())
