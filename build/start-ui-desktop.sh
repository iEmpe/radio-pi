#!/bin/bash
# Uruchom aplikację na istniejącym pulpicie X11 (Bullseye desktop + LCD).
export DISPLAY=:0
export XAUTHORITY=/home/pi/.Xauthority
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export PULSE_SERVER="${PULSE_SERVER:-unix:${XDG_RUNTIME_DIR}/pulse/native}"

# Gniazdo jack 3,5 mm (zmień na auto lub HDMI jeśli audio idzie inną drogą)
export RADIO_AUDIO_DEVICE="${RADIO_AUDIO_DEVICE:-pulse/alsa_output.platform-bcm2835_audio.analog-stereo}"

for _ in $(seq 1 30); do
  xdpyinfo >/dev/null 2>&1 && break
  sleep 1
done

xset s off 2>/dev/null || true
xset -dpms 2>/dev/null || true
xset s noblank 2>/dev/null || true

# Usuń osierocone / zduplikowane procesy
pkill -f "python3 -m app.main" 2>/dev/null || true
pkill -f "mpv --input-ipc-server=/tmp/radio-pi-mpv.sock" 2>/dev/null || true
rm -f /tmp/radio-pi-mpv.sock /tmp/radio-pi-ui.lock

cd /opt/radio-pi
exec python3 -m app.main
