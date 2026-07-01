#!/usr/bin/env bash
# Find Raspberry Pi on the local network (SSH + Pi MAC prefixes + mDNS).
set -euo pipefail

SUBNET="${1:-}"
if [ -z "$SUBNET" ]; then
  IFACE="$(route -n get default 2>/dev/null | awk '/interface:/{print $2}')"
  IP="$(ipconfig getifaddr "$IFACE" 2>/dev/null || true)"
  if [ -z "$IP" ]; then
    echo "Podaj sieć, np.: $0 192.168.0.0/24" >&2
    exit 1
  fi
  BASE="$(echo "$IP" | cut -d. -f1-3)"
  SUBNET="${BASE}.0/24"
fi

echo "Skanuję $SUBNET …"
echo ""

if ! command -v nmap >/dev/null 2>&1; then
  echo "Zainstaluj nmap: brew install nmap" >&2
  exit 1
fi

echo "=== Hosty z otwartym SSH (port 22) ==="
FOUND=0
while read -r host; do
  [ -z "$host" ] && continue
  FOUND=1
  echo "  $host"
done < <(nmap -p 22 --open "$SUBNET" 2>/dev/null | awk '/Nmap scan report/{h=$NF} /22\/tcp open/{print h}')

if [ "$FOUND" -eq 0 ]; then
  echo "  (brak — Pi nie ma IP albo SSH wyłączone)"
fi

echo ""
echo "=== Urządzenia Raspberry Pi (MAC) ==="
nmap -sn "$SUBNET" 2>/dev/null | awk '
  /Nmap scan report/{h=$NF}
  /MAC Address/{if ($0 ~ /Raspberry|B8:27:EB|DC:A6:32|E4:5F:01|2C:CF:67/) print h, $0}
' || true

echo ""
echo "=== mDNS ==="
for name in radiopi.local raspberrypi.local; do
  if IP="$(ping -c 1 -t 2 "$name" 2>/dev/null | awk -F'[()]' '/PING/{print $2; exit}')" && [ -n "$IP" ]; then
    echo "  OK  $name → $IP"
  else
    echo "  —   $name"
  fi
done

echo ""
echo "Logowanie (z prepare_sdcard_image.sh):"
echo "  ssh pi@<IP>"
echo "  hasło: wartość PI_PASSWORD użyta przy budowie obrazu (domyślnie zmien_to_haslo)"
echo ""
echo "Jeśli hostname był zły (MacBook-… zamiast radiopi), użyj IP z routera lub:"
echo "  PI_HOSTNAME=radiopi ./build/prepare_sdcard_image.sh"
