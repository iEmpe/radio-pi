"""Download and cache station logos."""

from __future__ import annotations

import re
import time
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests

from app.stations.validate import stream_domain

REPO_ROOT = Path(__file__).resolve().parent.parent
LOGO_DIR = REPO_ROOT / "assets" / "stations"
API_BASE = "https://de1.api.radio-browser.info/json"
LOGO_TTL_DAYS = 30
SESSION = requests.Session()
SESSION.headers["User-Agent"] = "radio-pi/1.0"


def station_slug(name: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", name.lower())
    slug = re.sub(r"[\s_]+", "-", slug).strip("-")
    return slug or "station"


def logo_path(station: Dict) -> Path:
    return LOGO_DIR / f"{station_slug(station.get('name', ''))}.png"


def icon_domain(station: Dict) -> str:
    homepage = (station.get("homepage") or "").strip()
    if homepage:
        domain = stream_domain(homepage)
        if domain:
            return domain
    return stream_domain(station.get("url", ""))


def cached_logo_path(station: Dict) -> Optional[Path]:
    slug = station_slug(station.get("name", ""))
    for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
        path = LOGO_DIR / f"{slug}{ext}"
        if path.exists() and path.stat().st_size > 0:
            return path
    return None


def logo_needs_refresh(station: Dict, ttl_days: int = LOGO_TTL_DAYS) -> bool:
    """True when logo is missing, or cached file is older than *ttl_days*."""
    path = cached_logo_path(station)
    if not path:
        return True
    age_s = time.time() - path.stat().st_mtime
    return age_s >= ttl_days * 86400


def has_logo(station: Dict) -> bool:
    return cached_logo_path(station) is not None


def _to_png(data: bytes) -> Optional[bytes]:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return data
    try:
        from PIL import Image
    except ImportError:
        return data if data[:3] == b"\xff\xd8\xff" else None
    try:
        img = Image.open(BytesIO(data))
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA")
        img.thumbnail((64, 64), Image.Resampling.LANCZOS)
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None


def _fetch_bytes(url: str, timeout: int = 15) -> Optional[bytes]:
    try:
        resp = SESSION.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.content
    except requests.RequestException:
        return None


def _radio_browser_favicon(name: str, timeout: int = 8) -> str:
    try:
        resp = SESSION.get(
            f"{API_BASE}/stations/search",
            params={"name": name, "limit": 5},
            timeout=timeout,
        )
        resp.raise_for_status()
        for item in resp.json():
            fav = (item.get("favicon") or "").strip()
            if fav:
                return fav
    except requests.RequestException:
        pass
    return ""


def _homepage_favicon(url: str) -> str:
    domain = stream_domain(url)
    if not domain:
        return ""
    for candidate in (
        f"https://{domain}/favicon.ico",
        f"https://{domain}/apple-touch-icon.png",
        f"https://www.{domain}/favicon.ico",
        f"https://www.google.com/s2/favicons?domain={domain}&sz=128",
    ):
        data = _fetch_bytes(candidate, timeout=8)
        if data and _to_png(data):
            return candidate
    return f"https://www.google.com/s2/favicons?domain={domain}&sz=128"


def discover_favicon_url(station: Dict) -> str:
    explicit = (station.get("favicon_url") or "").strip()
    if explicit:
        return explicit
    homepage = (station.get("homepage") or "").strip()
    if homepage:
        return urljoin(homepage, "/favicon.ico")
    rb = _radio_browser_favicon(station.get("name", ""))
    if rb:
        return rb
    return _homepage_favicon(station.get("url", ""))


def _save_logo_bytes(station: Dict, data: bytes) -> bool:
    LOGO_DIR.mkdir(parents=True, exist_ok=True)
    slug = station_slug(station.get("name", ""))
    png = _to_png(data)
    if png:
        (LOGO_DIR / f"{slug}.png").write_bytes(png)
        return True
    if data[:6] in (b"GIF87a", b"GIF89a"):
        (LOGO_DIR / f"{slug}.gif").write_bytes(data)
        return True
    if data[:3] == b"\xff\xd8\xff":
        (LOGO_DIR / f"{slug}.jpg").write_bytes(data)
        return True
    if data[:4] == b"RIFF" and len(data) > 12 and data[8:12] == b"WEBP":
        (LOGO_DIR / f"{slug}.webp").write_bytes(data)
        return True
    return False


def download_station_logo(
    station: Dict,
    *,
    force: bool = False,
    request_timeout: int = 8,
) -> bool:
    """Cache logo for station. Returns True when a logo file exists after call."""
    LOGO_DIR.mkdir(parents=True, exist_ok=True)
    if not force and has_logo(station) and not logo_needs_refresh(station):
        return True

    for url in _icon_candidates(station, request_timeout=request_timeout):
        data = _fetch_bytes(url, timeout=request_timeout)
        if not data:
            continue
        if _save_logo_bytes(station, data):
            return True
    return has_logo(station)


def _icon_candidates(station: Dict, *, request_timeout: int = 8) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []

    def add(url: str) -> None:
        url = (url or "").strip()
        if url and url not in seen:
            seen.add(url)
            out.append(url)

    add(station.get("favicon_url", ""))
    homepage = (station.get("homepage") or "").strip()
    if homepage:
        add(urljoin(homepage, "/favicon.ico"))
        add(urljoin(homepage, "/apple-touch-icon.png"))
    add(_radio_browser_favicon(station.get("name", ""), timeout=request_timeout))
    domain = icon_domain(station)
    if domain:
        add(f"https://www.google.com/s2/favicons?domain={domain}&sz=128")
        add(f"https://{domain}/favicon.ico")
        add(f"https://{domain}/apple-touch-icon.png")
        if not domain.startswith("www."):
            add(f"https://www.{domain}/favicon.ico")
    return out
