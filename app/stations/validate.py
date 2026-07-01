"""Validate internet radio stream URLs."""

from __future__ import annotations

import subprocess
from typing import Tuple
from urllib.parse import urlparse

import requests

TIMEOUT = 8


def validate_stream(url: str) -> Tuple[bool, str]:
    """Return (ok, detail) for a stream / playlist URL."""
    if not url:
        return False, "empty url"

    code = ""
    try:
        result = subprocess.run(
            [
                "curl", "--max-time", str(TIMEOUT),
                "-sS", "-L", "-r", "0-4096",
                "-o", "/dev/null", "-w", "%{http_code}", url,
            ],
            capture_output=True,
            text=True,
            timeout=TIMEOUT + 2,
            check=False,
        )
        lines = [ln.strip() for ln in result.stdout.splitlines() if ln.strip()]
        code = lines[-1] if lines else ""
        if code.isdigit() and 100 <= int(code) < 400:
            return True, code
        if result.returncode != 0:
            detail = code if code.isdigit() and int(code) > 0 else f"curl exit {result.returncode}"
            return False, detail
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return _requests_check(url, str(exc))

    if code.isdigit() and int(code) >= 400:
        return False, f"http {code}"
    if not code or code == "000":
        return False, "no response"

    try:
        resp = requests.head(url, timeout=TIMEOUT, allow_redirects=True)
        if resp.status_code < 400:
            return True, str(resp.status_code)
        with requests.get(url, stream=True, timeout=TIMEOUT) as stream:
            if stream.status_code < 400:
                next(stream.iter_content(1024), None)
                return True, str(stream.status_code)
            return False, f"http {stream.status_code}"
    except requests.RequestException as exc:
        return False, str(exc)


def _requests_check(url: str, fallback: str) -> Tuple[bool, str]:
    try:
        resp = requests.head(url, timeout=TIMEOUT, allow_redirects=True)
        if resp.status_code < 400:
            return True, str(resp.status_code)
        with requests.get(url, stream=True, timeout=TIMEOUT) as stream:
            if stream.status_code < 400:
                next(stream.iter_content(1024), None)
                return True, str(stream.status_code)
            return False, f"http {stream.status_code}"
    except requests.RequestException:
        return False, fallback


def stream_domain(url: str) -> str:
    host = urlparse(url).hostname or ""
    if host.startswith("www."):
        host = host[4:]
    return host
