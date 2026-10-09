#!/usr/bin/env bash
# Pobierz obraz złoty SD z działającego Pi bezpośrednio na Mac (bez miejsca na karcie Pi).
#
# Użycie:
#   PI_HOST=192.168.0.81 ./build/pull-golden-image-from-mac.sh
#
# Wynik: ~/Downloads/radio-pi-golden-YYYYMMDD.img.gz
# Czas: ~1–3 h (Pi 3 + WiFi/Ethernet). Radio na chwilę się zatrzyma.
set -euo pipefail

PI_HOST="${PI_HOST:-192.168.0.81}"
PI_USER="${PI_USER:-pi}"
STAMP="$(date +%Y%m%d-%H%M)"
OUT="${OUT:-$HOME/Downloads/radio-pi-golden-${STAMP}.img.gz}"
LOG="${OUT%.img.gz}.pull.log"

echo "==> Pobieranie obrazu z ${PI_USER}@${PI_HOST}"
echo "    Cel: $OUT"
echo "    Log: $LOG"
echo "    (może potrwać 1–3 godziny)"
echo

ssh -o ConnectTimeout=15 "${PI_USER}@${PI_HOST}" \
  'sudo systemctl stop radio-ui.service 2>/dev/null; sync; sudo dd if=/dev/mmcblk0 bs=4M status=progress | gzip -6' \
  > "$OUT" 2> "$LOG" || {
    echo "Błąd pobierania — sprawdź $LOG"
    ssh "${PI_USER}@${PI_HOST}" "sudo systemctl start radio-ui.service" 2>/dev/null || true
    exit 1
  }

ssh "${PI_USER}@${PI_HOST}" "sudo systemctl start radio-ui.service" 2>/dev/null || true

echo "==> SHA256"
shasum -a 256 "$OUT" | tee "${OUT%.img.gz}.sha256"

echo
echo "Gotowe: $OUT"
echo "Flash: Raspberry Pi Imager → Use custom → wybierz plik .img.gz"
ls -lh "$OUT"
