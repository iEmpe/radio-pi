#!/usr/bin/env bash
# Zrzuty ekranu z działającego UI na Pi (wymaga DISPLAY=:0, scrot).
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$REPO_DIR/docs/screenshots"
mkdir -p "$OUT"

export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-/home/pi/.Xauthority}"

if ! command -v scrot >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo apt-get install -y scrot
fi

echo "==> Screenshot głównego UI"
scrot -o "$OUT/02-main-playing-pi.png" -d 2

echo "==> Screenshot menu WiFi (otwórz ręcznie WiFi na ekranie, potem Enter)"
read -r -p "Naciśnij Enter gdy menu WiFi jest otwarte…"
scrot -o "$OUT/04-wifi-menu-pi.png"

echo "Zapisano w $OUT"
