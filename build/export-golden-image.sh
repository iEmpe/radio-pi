#!/usr/bin/env bash
# Eksport gotowego obrazu SD z działającego Radio Pi (uruchom NA Raspberry Pi).
# Tworzy skompresowany obraz CAŁEJ karty SD (boot + root) do klonowania.
#
# Wymaga: sudo, ~8 GB wolnego miejsca (najlepiej pendrive: OUTPUT_DIR=/media/pi/NAZWA)
#
# Użycie:
#   sudo OUTPUT_DIR=/media/pi/USB ./build/export-golden-image.sh
#
# Pobranie na Mac:
#   scp pi@<IP>:/home/pi/radio-pi-images/radio-pi-golden-*.img.xz .
#   scp pi@<IP>:/home/pi/radio-pi-images/radio-pi-golden-*.manifest.txt .
#
# Flash: Raspberry Pi Imager → Use custom → wybierz .img.xz (lub rozpakuj xz najpierw)
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Uruchom: sudo $0"
  exit 1
fi

PI_USER="${SUDO_USER:-pi}"
PI_HOME="$(getent passwd "$PI_USER" | cut -d: -f6)"
STAMP="$(date +%Y%m%d-%H%M)"
OUTPUT_DIR="${OUTPUT_DIR:-$PI_HOME/radio-pi-images}"
RAW_IMG="$OUTPUT_DIR/radio-pi-golden-${STAMP}.img"
XZ_IMG="${RAW_IMG}.xz"
MANIFEST="$OUTPUT_DIR/radio-pi-golden-${STAMP}.manifest.txt"

mkdir -p "$OUTPUT_DIR"
chown "$PI_USER:$PI_USER" "$OUTPUT_DIR" 2>/dev/null || true

echo "==> Radio Pi — eksport obrazu złotego (cała karta SD)"
echo "    Urządzenie: /dev/mmcblk0"
echo "    Cel:        $XZ_IMG"
echo

AVAIL_KB="$(df -k "$OUTPUT_DIR" | awk 'NR==2 {print $4}')"
if (( AVAIL_KB < 8000000 )); then
  echo "WARN: Mało miejsca w $OUTPUT_DIR ($(df -h "$OUTPUT_DIR" | tail -1))"
  echo "      Zalecane: sudo OUTPUT_DIR=/media/pi/USB $0"
  read -r -p "Kontynuować mimo to? [y/N] " ans
  [[ "${ans,,}" == "y" ]] || exit 1
fi

echo "==> Zatrzymanie radia (krótko)"
systemctl stop radio-ui.service 2>/dev/null || true
sync

echo "==> Zrzut /dev/mmcblk0 + kompresja xz (15–60 min na Pi 3)"
dd if=/dev/mmcblk0 bs=4M status=progress conv=fsync | xz -9 -T0 > "$XZ_IMG"

echo "==> Manifest"
{
  echo "Radio Pi golden image (full SD card)"
  echo "Created: $(date -Iseconds)"
  echo "Hostname: $(hostname)"
  echo "Kernel: $(uname -r)"
  grep -E '^(PRETTY_NAME|VERSION_ID)=' /etc/os-release 2>/dev/null || true
  echo "Source: /dev/mmcblk0"
  echo "Image: $(basename "$XZ_IMG")"
  echo "Size: $(ls -lh "$XZ_IMG" | awk '{print $5}')"
  echo "SHA256: $(sha256sum "$XZ_IMG" | awk '{print $1}')"
  echo
  echo "=== Zawartość obrazu ==="
  echo "- Raspberry Pi OS Legacy Bullseye (desktop + LCD Waveshare 3.2\")"
  echo "- Radio Pi UI (/opt/radio-pi, autostart systemd)"
  echo "- VLC + pełne kodeki (pendrive)"
  echo "- NetworkManager, WiFi/BT skonfigurowane"
  echo "- Ostatnia stacja:"
  cat /opt/radio-pi/app/data/last_station.json 2>/dev/null || echo "  (brak)"
  echo
  echo "=== Flash ==="
  echo "Raspberry Pi Imager → Use custom → $(basename "$XZ_IMG")"
  echo
  echo "UWAGA: Obraz może zawierać Twoje hasła WiFi i klucze SSH."
  echo "       Zmień hasło pi po sklonowaniu: passwd"
} | tee "$MANIFEST"

chown "$PI_USER:$PI_USER" "$XZ_IMG" "$MANIFEST" 2>/dev/null || true

echo "==> Uruchamianie radia"
systemctl start radio-ui.service 2>/dev/null || true

echo
echo "Gotowe:"
ls -lh "$XZ_IMG" "$MANIFEST"
