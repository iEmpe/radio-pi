#!/usr/bin/env python3
"""Fetch and validate radio stations from Radio-Browser API."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

from app.stations.validate import validate_stream

API_BASE = "https://de1.api.radio-browser.info/json"
OUTPUT = Path(__file__).resolve().parent.parent / "app" / "data" / "stations.json"
TIMEOUT = 6

GUARANTEED = [
    {
        "name": "SomaFM Groove Salad",
        "url": "https://ice1.somafm.com/groovesalad-256-mp3",
        "country": "United States",
        "tags": "ambient, electronic, chill",
        "favicon_url": "https://somafm.com/favicon.ico",
        "homepage": "https://somafm.com/groovesalad/",
    },
    {
        "name": "SomaFM Lush",
        "url": "https://ice1.somafm.com/lush-128-mp3",
        "country": "United States",
        "tags": "ambient, downtempo",
        "favicon_url": "https://somafm.com/favicon.ico",
        "homepage": "https://somafm.com/lush/",
    },
    {
        "name": "KEXP Seattle",
        "url": "https://kexp-mp3-128.streamguys1.com/kexp128.mp3",
        "country": "United States",
        "tags": "indie, alternative",
        "favicon_url": "https://www.kexp.org/favicon.ico",
        "homepage": "https://www.kexp.org/",
    },
]

DNB_STATIONS = [
    {
        "name": "UKF UK Bass Radio",
        "url": "https://www.ukbassradio.com/stream",
        "country": "United Kingdom",
        "tags": "ukf,drum and bass,uk bass",
        "favicon_url": "https://www.ukbassradio.com/favicon.ico",
        "homepage": "https://www.ukbassradio.com/",
    },
    {
        "name": "Bassdrive",
        "url": "http://bassdrive.com/bassdrive.m3u",
        "country": "United States",
        "tags": "drum and bass,jungle,24/7",
        "favicon_url": "https://www.bassdrive.com/favicon.ico",
        "homepage": "https://www.bassdrive.com/",
    },
    {
        "name": "Kool FM",
        "url": "https://admin.stream.rinse.fm/proxy/kool/stream",
        "country": "United Kingdom",
        "tags": "jungle,drum and bass,london",
        "favicon_url": "https://www.rinse.fm/favicon.ico",
        "homepage": "https://www.rinse.fm/shows/kool-fm/",
    },
    {
        "name": "DnBRadio",
        "url": "https://azura.drmnbss.org:8000/radio.mp3",
        "country": "United States",
        "tags": "drum and bass,jungle,dj sets",
        "favicon_url": "https://dnbradio.com/favicon.ico",
        "homepage": "https://dnbradio.com/",
    },
    {
        "name": "BBC Radio 1",
        "url": (
            "http://a.files.bbci.co.uk/ms6/live/3441A116-B12E-4D2F-ACA8-C1984642FA4B"
            "/audio/simulcast/hls/nonuk/pc_hd_abr_v2/cf/bbc_radio_one.m3u8"
        ),
        "country": "United Kingdom",
        "tags": "drum and bass,mainstream,bbc",
        "favicon_url": "https://www.bbc.co.uk/favicon.ico",
        "homepage": "https://www.bbc.co.uk/sounds/play/live/bbc_radio_one",
    },
    {
        "name": "BBC Radio 1Xtra",
        "url": (
            "http://as-hls-ww-live.akamaized.net/pool_92079267/live/ww/bbc_1xtra"
            "/bbc_1xtra.isml/bbc_1xtra-audio%3d128000.norewind.m3u8"
        ),
        "country": "United Kingdom",
        "tags": "drum and bass,hip hop,urban,bbc",
        "favicon_url": "https://www.bbc.co.uk/favicon.ico",
        "homepage": "https://www.bbc.co.uk/sounds/play/live/bbc_1xtra",
    },
    {
        "name": "DI.FM Drum & Bass",
        "url": "http://listen.di.fm/public3/drumandbass.pls",
        "country": "United States",
        "tags": "drum and bass,electronic,commercial-free",
        "favicon_url": "https://www.di.fm/favicon.ico",
        "homepage": "https://www.di.fm/channels/drumandbass",
    },
    {
        "name": "DI.FM Liquid DnB",
        "url": "http://listen.di.fm/public3/liquiddnb.pls",
        "country": "United States",
        "tags": "liquid,drum and bass,vocal",
        "favicon_url": "https://www.di.fm/favicon.ico",
        "homepage": "https://www.di.fm/channels/liquiddnb",
    },
    {
        "name": "Different Drumz DnB",
        "url": "http://differentdrumz.radioca.st/stream",
        "country": "United Kingdom",
        "tags": "liquid,soulful,drum and bass",
        "favicon_url": "https://www.differentdrumz.co.uk/favicon.ico",
        "homepage": "https://www.differentdrumz.co.uk/",
    },
    {
        "name": "Liqui Radio",
        "url": "http://stream.zeno.fm/ug59eq099yzuv",
        "country": "Europe",
        "tags": "liquid,vocal,drum and bass",
        "favicon_url": "",
        "homepage": "https://www.liquiradio.com/",
    },
]

PL_TARGET = 15
INTL_TARGET = 12


def fetch_json(path: str, params: dict | None = None) -> List[dict]:
    resp = requests.get(
        f"{API_BASE}{path}",
        params=params or {},
        timeout=15,
        headers={"User-Agent": "radio-pi-fetch/1.0"},
    )
    resp.raise_for_status()
    return resp.json()


def to_entry(st: dict) -> Dict[str, str]:
    return {
        "name": st.get("name", "Unknown"),
        "url": st.get("url", ""),
        "country": st.get("country", ""),
        "tags": st.get("tags", ""),
        "favicon_url": st.get("favicon", ""),
        "homepage": st.get("homepage", ""),
    }


def collect_candidates() -> List[dict]:
    candidates: List[dict] = []

    pl = fetch_json("/stations/bycountry/Poland", {
        "order": "clickcount", "reverse": "true", "limit": 40,
    })
    for st in pl:
        if st.get("lastcheckok") == 1 and st.get("url"):
            candidates.append(to_entry(st))

    for tag in ("pop", "news", "jazz"):
        foreign = fetch_json("/stations/bytag/" + tag, {
            "order": "clickcount", "reverse": "true", "limit": 20,
        })
        for st in foreign:
            if st.get("lastcheckok") == 1 and st.get("url"):
                candidates.append(to_entry(st))

    for name in ("BBC", "NPR", "SomaFM", "KEXP"):
        named = fetch_json("/stations/search", {
            "name": name, "order": "clickcount", "reverse": "true", "limit": 5,
        })
        for st in named:
            if st.get("lastcheckok") == 1 and st.get("url"):
                candidates.append(to_entry(st))

    return candidates


def build_list() -> List[dict]:
    seen_urls: set[str] = set()
    seen_names: set[str] = set()
    result: List[dict] = []

    def add(entry: dict) -> bool:
        url = entry.get("url", "")
        name = (entry.get("name") or "").strip()
        norm_name = name.casefold()
        if not url or url in seen_urls or norm_name in seen_names:
            return False
        ok, detail = validate_stream(url)
        if not ok:
            print(f"  REJECT {name}: {detail} — {url}", file=sys.stderr)
            return False
        seen_urls.add(url)
        seen_names.add(norm_name)
        result.append(entry)
        print(f"  OK     {name} ({detail})")
        return True

    print("==> Drum & Bass stations")
    for st in DNB_STATIONS:
        add(st)

    print("==> Guaranteed stations")
    for g in GUARANTEED:
        add(g)

    print("==> Fetching candidates from Radio-Browser")
    candidates = collect_candidates()

    print("==> Polish stations")
    pl_count = sum(1 for s in result if s.get("country") == "Poland")
    for c in candidates:
        if pl_count >= PL_TARGET:
            break
        if c.get("country") == "Poland":
            if add(c):
                pl_count += 1

    print("==> International stations")
    intl_count = sum(1 for s in result if s.get("country") != "Poland")
    for c in candidates:
        if intl_count >= INTL_TARGET:
            break
        if c.get("country") != "Poland":
            if add(c):
                intl_count += 1

    return result


def main() -> int:
    stations = build_list()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(stations, f, indent=2, ensure_ascii=False)
    print(f"\nWrote {len(stations)} stations to {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
