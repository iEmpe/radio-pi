#!/usr/bin/env python3
"""Probe stream metadata for all configured stations."""
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

STATIONS = Path(__file__).resolve().parent.parent / "app" / "data" / "stations.json"
SOCK = "/tmp/meta-probe.sock"


def mpv_cmd(args, timeout=12):
    payload = '{"command": [' + ", ".join(f'"{a}"' for a in args) + "]}\n"
    try:
        r = subprocess.run(
            ["socat", "-", f"UNIX-CONNECT:{SOCK}"],
            input=payload.encode(),
            capture_output=True,
            timeout=timeout,
        )
        if r.stdout:
            line = r.stdout.decode().strip().splitlines()[-1]
            return json.loads(line)
    except Exception as e:
        return {"error": str(e)}
    return {}


def resolve_url(url: str) -> str:
    if not url.lower().endswith((".pls", ".m3u", ".m3u8")):
        return url
    try:
        r = subprocess.run(
            ["curl", "-sL", "--max-time", "8", url],
            capture_output=True,
            text=True,
            timeout=10,
        )
        for line in r.stdout.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                return line
    except Exception:
        pass
    return url


def icy_headers(url: str) -> dict:
    try:
        r = subprocess.run(
            ["curl", "-sI", "--max-time", "8", url],
            capture_output=True,
            text=True,
            timeout=10,
        )
        h = {}
        for line in r.stdout.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                k = k.strip().lower()
                if k.startswith("icy-") or k in ("content-type", "server"):
                    h[k] = v.strip()
        return h
    except Exception:
        return {}


def probe_station(st: dict) -> dict:
    name = st.get("name", "?")
    raw_url = st.get("url", "")
    url = resolve_url(raw_url)
    result = {
        "name": name,
        "config_country": st.get("country", ""),
        "config_tags": st.get("tags", ""),
        "resolved_url": url[:80],
        "icy": {},
        "metadata": {},
        "media_title": "",
        "audio_bitrate": None,
        "codec": "",
    }

    result["icy"] = icy_headers(url)

    # start mpv idle
    log = open("/tmp/meta-probe.log", "w")
    proc = subprocess.Popen(
        [
            "mpv", f"--input-ipc-server={SOCK}", "--no-video", "--idle=yes",
            "--really-quiet", f"--audio-device=null",
        ],
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    try:
        for _ in range(20):
            if Path(SOCK).exists():
                break
            time.sleep(0.1)
        mpv_cmd(["loadfile", url, "replace"])
        time.sleep(6)
        meta = mpv_cmd(["get_property", "metadata"])
        if meta.get("error") == "success":
            result["metadata"] = meta.get("data") or {}
        mt = mpv_cmd(["get_property", "media-title"])
        if mt.get("error") == "success":
            result["media_title"] = mt.get("data") or ""
        br = mpv_cmd(["get_property", "audio-bitrate"])
        if br.get("error") == "success" and br.get("data"):
            result["audio_bitrate"] = br.get("data")
        ac = mpv_cmd(["get_property", "audio-codec"])
        if ac.get("error") == "success":
            result["codec"] = ac.get("data") or ""
        mpv_cmd(["stop"])
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        Path(SOCK).unlink(missing_ok=True)

    return result


def main():
    stations = json.loads(STATIONS.read_text(encoding="utf-8"))
    out = []
    for i, st in enumerate(stations):
        print(f"[{i+1}/{len(stations)}] {st['name']}...", flush=True)
        out.append(probe_station(st))
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
