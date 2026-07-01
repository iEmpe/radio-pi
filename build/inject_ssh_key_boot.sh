#!/usr/bin/env bash
# Wstrzyknij klucz SSH na Pi przez partycję boot (bez znajomości hasła).
# Włóż kartę SD do Maca, potem:
#   sudo ./build/inject_ssh_key_boot.sh /dev/diskN
#   lub: sudo ./build/inject_ssh_key_boot.sh ~/radio-pi-build/radio-pi-base.img
set -euo pipefail

TARGET="${1:-}"
PUBKEY="${2:-$HOME/.ssh/id_ed25519.pub}"
DISK=""
MNT=""

cleanup() {
  [ -n "$MNT" ] && diskutil unmount "$MNT" 2>/dev/null || true
  [ -n "$DISK" ] && hdiutil detach "$DISK" 2>/dev/null || true
}
trap cleanup EXIT

if [ -z "$TARGET" ] || [ ! -f "$PUBKEY" ]; then
  echo "Użycie: sudo $0 /dev/diskN" >&2
  echo "       sudo $0 /path/to/image.img" >&2
  exit 1
fi

KEY_LINE=$(cat "$PUBKEY")

if [ -f "$TARGET" ]; then
  OUT=$(hdiutil attach -nomount "$TARGET")
  DISK=$(echo "$OUT" | head -1 | awk '{print $1}' | sed -E 's/s[0-9]+$//')
  diskutil mount "${DISK}s1"
  MNT=$(diskutil info "${DISK}s1" | awk -F': *' '/Mount Point/{print $2}' | sed 's/^ *//')
else
  diskutil mount "${TARGET}s1"
  MNT=$(diskutil info "${TARGET}s1" | awk -F': *' '/Mount Point/{print $2}' | sed 's/^ *//')
fi

touch "$MNT/ssh"

cat > "$MNT/install_ssh_key.sh" <<SCRIPT
#!/bin/bash
set -e
mkdir -p /home/pi/.ssh
grep -qF '${KEY_LINE}' /home/pi/.ssh/authorized_keys 2>/dev/null || \\
  echo '${KEY_LINE}' >> /home/pi/.ssh/authorized_keys
chown -R pi:pi /home/pi/.ssh
chmod 700 /home/pi/.ssh
chmod 600 /home/pi/.ssh/authorized_keys
rm -f /boot/install_ssh_key.sh
sed -i 's| systemd.run=/boot/install_ssh_key.sh systemd.run_success_action=none systemd.unit=kernel-command-line.target||g' /boot/cmdline.txt 2>/dev/null || true
SCRIPT
chmod +x "$MNT/install_ssh_key.sh"

if ! grep -q install_ssh_key.sh "$MNT/cmdline.txt"; then
  CMDLINE=$(tr -d '\n' < "$MNT/cmdline.txt")
  printf '%s systemd.run=/boot/install_ssh_key.sh systemd.run_success_action=none systemd.unit=kernel-command-line.target' \
    "$CMDLINE" > "$MNT/cmdline.txt"
fi

echo "OK: klucz zostanie dodany przy następnym bootcie Pi."
echo "    Włóż kartę, uruchom Pi, poczekaj 60 s, potem:"
echo "    ssh pi@192.168.0.81"
