#!/usr/bin/env bash
# Fix hostname on boot partition (SD card or .img) — macOS bug: HOSTNAME=MacBook-…
# Usage: PI_HOSTNAME=radiopi sudo ./build/patch_hostname.sh /dev/diskN
#    or: PI_HOSTNAME=radiopi sudo ./build/patch_hostname.sh ~/radio-pi-build/radio-pi-base.img
set -euo pipefail

TARGET="${1:-}"
PI_HOSTNAME="${PI_HOSTNAME:-radiopi}"
MNT=""

cleanup() {
  [ -n "$MNT" ] && diskutil unmount "$MNT" 2>/dev/null || true
  [ -n "${DISK:-}" ] && hdiutil detach "$DISK" 2>/dev/null || true
}
trap cleanup EXIT

if [ -z "$TARGET" ]; then
  echo "Użycie: PI_HOSTNAME=radiopi sudo $0 /dev/diskN" >&2
  exit 1
fi

if [ -f "$TARGET" ]; then
  OUT=$(hdiutil attach -nomount "$TARGET")
  DISK=$(echo "$OUT" | head -1 | awk '{print $1}' | sed -E 's/s[0-9]+$//')
  diskutil mount "${DISK}s1"
  MNT=$(diskutil info "${DISK}s1" | awk -F': *' '/Mount Point/{print $2}' | sed 's/^ *//')
else
  diskutil mount "${TARGET}s1"
  MNT=$(diskutil info "${TARGET}s1" | awk -F': *' '/Mount Point/{print $2}' | sed 's/^ *//')
fi

echo "$PI_HOSTNAME" > "$MNT/hostname"
touch "$MNT/ssh"
echo "Hostname ustawiony na: $PI_HOSTNAME (partycja: $MNT)"
