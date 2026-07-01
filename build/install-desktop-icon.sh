#!/bin/bash
# Instaluje skrót Radio Pi na pulpicie użytkownika pi.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DESKTOP_SRC="$REPO_DIR/build/radio-pi.desktop"
DESKTOP_DST="/home/pi/Desktop/radio-pi.desktop"

chmod +x "$REPO_DIR/build/launch-radio.sh"

install -m 755 "$DESKTOP_SRC" "$DESKTOP_DST"
chown pi:pi "$DESKTOP_DST" 2>/dev/null || true

# LXDE / PCManFM — zaufany launcher na pulpicie
if command -v gio >/dev/null 2>&1; then
  gio set "$DESKTOP_DST" metadata::trusted true 2>/dev/null || true
fi

# Kopia w menu aplikacji (bez wymogu „zaufania”)
install -m 644 "$DESKTOP_SRC" /usr/share/applications/radio-pi.desktop

echo "Skrót zainstalowany: $DESKTOP_DST"
