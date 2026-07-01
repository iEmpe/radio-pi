#!/usr/bin/env bash
# Radio Pi — szybki health check (bez zmian w systemie).
set -euo pipefail

REPORT="${1:-/tmp/radio-pi-health.txt}"
WARN=0

warn() { echo "  [!] $*"; WARN=$((WARN + 1)); }
ok()   { echo "  [ok] $*"; }

{
  echo "=============================================="
  echo "  Radio Pi — health check"
  echo "  $(date -Iseconds)"
  echo "=============================================="
  echo

  echo "==> System"
  hostname
  if command -v vcgencmd >/dev/null 2>&1; then
    echo "  Temp: $(vcgencmd measure_temp 2>/dev/null || echo '?')"
    throttled="$(vcgencmd get_throttled 2>/dev/null || echo '')"
    [[ -n "$throttled" ]] && echo "  Throttle: $throttled"
  fi
  uptime
  df -h / | tail -1
  free -h | head -2
  echo

  echo "==> Radio Pi"
  if systemctl is-active radio-ui.service >/dev/null 2>&1; then
    ok "radio-ui.service active"
  else
    warn "radio-ui.service NOT active"
  fi
  if pgrep -f "python3 -m app.main" >/dev/null 2>&1; then
    ok "proces UI działa"
  else
    warn "brak procesu python3 -m app.main"
  fi
  if pgrep -x mpv >/dev/null 2>&1; then
    ok "mpv działa"
  else
    warn "mpv nie działa"
  fi
  if python3 -c "import numpy" >/dev/null 2>&1; then
    ok "numpy $(python3 -c 'import numpy; print(numpy.__version__)')"
  else
    warn "numpy niedostępny — equalizer wyłączony"
  fi
  if [[ -f /opt/radio-pi/app/data/last_station.json ]]; then
    ok "last_station: $(python3 -c "import json; print(json.load(open('/opt/radio-pi/app/data/last_station.json'))['name'])")"
  else
    echo "  [--] brak last_station.json"
  fi
  echo

  echo "==> VLC"
  if command -v vlc >/dev/null 2>&1; then
    ok "vlc $(vlc --version 2>/dev/null | head -1 || echo installed)"
    plugins="$(dpkg -l 2>/dev/null | grep -cE '^ii\s+vlc' || true)"
    echo "  pakiety vlc: $plugins"
    for pkg in vlc-plugin-access-extra vlc-plugin-svg libavcodec-extra; do
      if dpkg-query -W -f='${Status}' "$pkg" 2>/dev/null | grep -q "install ok installed"; then
        ok "$pkg"
      else
        warn "brak $pkg"
      fi
    done
  else
    warn "vlc nie zainstalowany"
  fi
  echo

  echo "==> Sieć / audio"
  nmcli -t -f DEVICE,TYPE,STATE dev 2>/dev/null | head -8 || true
  PA_ENV=()
  if [[ -n "${SUDO_UID:-}" ]]; then
    PA_ENV=(sudo -u "${SUDO_USER:-pi}" "PULSE_SERVER=unix:/run/user/$(id -u "${SUDO_USER:-pi}")/pulse/native")
  fi
  if "${PA_ENV[@]}" pactl info 2>/dev/null | grep -E 'Server Name|Default Sink' >/dev/null; then
    "${PA_ENV[@]}" pactl info 2>/dev/null | grep -E 'Server Name|Default Sink'
    ok "PulseAudio"
  elif pactl info 2>/dev/null | grep -E 'Server Name|Default Sink' >/dev/null; then
    pactl info 2>/dev/null | grep -E 'Server Name|Default Sink'
    ok "PulseAudio"
  else
    warn "PulseAudio niedostępny (sprawdź sesję graficzną pi)"
  fi
  echo

  echo "==> Usługi z błędami"
  failed="$(systemctl --failed --no-legend --plain 2>/dev/null | awk '{print $1}' | grep -v '^$' || true)"
  if [[ -z "$failed" ]]; then
    ok "brak failed units"
  else
    while read -r unit; do
      [[ -n "$unit" ]] && warn "failed: $unit"
    done <<< "$failed"
  fi
  echo

  echo "==> Ostatnie błędy radio-ui (5 linii WARNING/ERROR)"
  journalctl -u radio-ui.service -p warning..err -n 5 --no-pager 2>/dev/null || true
  echo

  echo "==> Podsumowanie"
  if (( WARN == 0 )); then
    echo "  STATUS: OK (0 ostrzeżeń)"
  else
    echo "  STATUS: $WARN ostrzeżeń — uruchom: sudo /opt/radio-pi/build/pi-maintenance.sh"
  fi
  echo "=============================================="
} | tee "$REPORT"

echo "Raport: $REPORT"
exit "$WARN"
