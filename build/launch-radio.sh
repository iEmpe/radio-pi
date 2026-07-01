#!/bin/bash
# Uruchom Radio Pi z pulpitu (nakładka na istniejącym pulpicie X11).
set -euo pipefail

export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-/home/pi/.Xauthority}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export PULSE_SERVER="${PULSE_SERVER:-unix:${XDG_RUNTIME_DIR}/pulse/native}"
export RADIO_AUDIO_DEVICE="${RADIO_AUDIO_DEVICE:-pulse/alsa_output.platform-bcm2835_audio.analog-stereo}"

# Jedna instancja — jeśli działa, nie uruchamiaj drugiej
if pgrep -f "python3 -m app.main" >/dev/null 2>&1; then
  exit 0
fi

pkill -f "mpv --input-ipc-server=/tmp/radio-pi-mpv.sock" 2>/dev/null || true
rm -f /tmp/radio-pi-mpv.sock /tmp/radio-pi-ui.lock

cd /opt/radio-pi
exec python3 -m app.main
