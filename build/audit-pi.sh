#!/usr/bin/env bash
# Radio Pi — audyt systemu (uruchom na Pi: sudo ./build/audit-pi.sh)
set -euo pipefail

REPORT="${1:-/tmp/radio-pi-audit.txt}"

{
  echo "=============================================="
  echo "  Radio Pi — audyt systemu"
  echo "  $(date -Iseconds)"
  echo "=============================================="
  echo

  echo "==> System"
  hostname
  uname -a
  if [ -f /etc/os-release ]; then
    grep -E '^(PRETTY_NAME|VERSION)=' /etc/os-release
  fi
  echo

  echo "==> CPU / temperatura"
  if command -v vcgencmd >/dev/null 2>&1; then
    vcgencmd measure_temp
    vcgencmd get_throttled 2>/dev/null || true
  fi
  uptime
  echo

  echo "==> Pamięć i dysk"
  free -h
  df -h / /boot 2>/dev/null || df -h /
  echo

  echo "==> Usługi Radio Pi"
  for svc in radio-ui radio-hotspot bluetooth NetworkManager; do
    printf "  %-18s " "$svc"
    systemctl is-active "$svc" 2>/dev/null || echo "inactive"
  done
  echo

  echo "==> Usługi z błędami"
  systemctl --failed --no-pager 2>/dev/null || true
  echo

  echo "==> Sieć"
  nmcli -t -f DEVICE,TYPE,STATE dev 2>/dev/null || ip -br link
  echo
  ip -4 -br addr 2>/dev/null | head -6
  echo

  echo "==> Bluetooth"
  if command -v bluetoothctl >/dev/null 2>&1; then
    bluetoothctl show 2>/dev/null | grep -E 'Powered|Discoverable|Pairable' || true
  fi
  echo

  echo "==> Audio (PulseAudio / mpv)"
  pactl info 2>/dev/null | grep -E 'Server Name|Default Sink' || echo "  PulseAudio niedostępny"
  pgrep -a mpv 2>/dev/null || echo "  mpv nie działa"
  echo

  echo "==> Top 8 procesów (RAM)"
  ps aux --sort=-%mem | head -9
  echo

  echo "==> Ostatnie logi radio-ui (20 linii)"
  journalctl -u radio-ui.service -n 20 --no-pager 2>/dev/null || true
  echo

  echo "==> Stacje skonfigurowane"
  if [ -f /opt/radio-pi/app/data/stations.json ]; then
    python3 -c "
import json
from pathlib import Path
data = json.loads(Path('/opt/radio-pi/app/data/stations.json').read_text())
print(f'  Liczba stacji: {len(data)}')
for s in data[:12]:
    print(f\"  - {s['name']}\")
if len(data) > 12:
    print(f'  ... i {len(data)-12} więcej')
"
  else
    echo "  Brak stations.json"
  fi
  echo

  echo "==> Podsumowanie"
  echo "  Projekt: /opt/radio-pi"
  echo "  UI:      systemctl status radio-ui"
  echo "=============================================="
} | tee "$REPORT"

echo "Raport zapisany: $REPORT"
