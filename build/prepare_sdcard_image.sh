#!/usr/bin/env bash
# Prepare Raspberry Pi OS Lite (Bullseye 32-bit) SD image on macOS.
# Uses hdiutil/diskutil — NO losetup/WSL.
#
# SECURITY: Change USER_PASSWORD before flashing. Do not commit real passwords.
# SAFETY:   Verify disk identifiers from hdiutil/diskutil before writing to SD.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# --- Configuration (override via environment) ---
# Bullseye Legacy = raspios_oldstable (NOT raspios_lite — that path is Bookworm now)
IMG_XZ_URL="${IMG_XZ_URL:-https://downloads.raspberrypi.com/raspios_oldstable_lite_armhf/images/raspios_oldstable_lite_armhf-2023-12-06/2023-12-05-raspios-bullseye-armhf-lite.img.xz}"
WORKDIR="${WORKDIR:-$HOME/radio-pi-build}"
IMG_NAME="${IMG_NAME:-radio-pi-base.img}"
# Na macOS HOSTNAME/USER są zwykle już ustawione — używaj PI_HOSTNAME / PI_USER
PI_HOSTNAME="${PI_HOSTNAME:-radiopi}"
PI_USER="${PI_USER:-pi}"
PI_PASSWORD="${PI_PASSWORD:-zmien_to_haslo}"

ADD_WIFI="${ADD_WIFI:-false}"
WIFI_SSID="${WIFI_SSID:-}"
WIFI_PASS="${WIFI_PASS:-}"

is_valid_xz() {
  local f="$1"
  [ -f "$f" ] || return 1
  local size
  size=$(stat -f%z "$f" 2>/dev/null || stat -c%s "$f")
  [ "$size" -gt 1000000 ] || return 1
  # file(1) works on macOS without locale/binary grep issues
  file -b "$f" | grep -qi 'XZ compressed'
}

mkdir -p "$WORKDIR" && cd "$WORKDIR"

echo "==> Downloading base image"
if [ ! -f "$IMG_NAME" ]; then
  if ! is_valid_xz base.img.xz; then
    [ -f base.img.xz ] && echo "WARN: base.img.xz is corrupt or incomplete — re-downloading"
    rm -f base.img.xz
    curl -fL --retry 3 -o base.img.xz "$IMG_XZ_URL"
    if ! is_valid_xz base.img.xz; then
      echo "ERROR: Download failed or file is not a valid .xz archive."
      echo "       URL: $IMG_XZ_URL"
      echo "       Check your internet connection or set IMG_XZ_URL manually."
      rm -f base.img.xz
      exit 1
    fi
  fi
fi

if [ -f base.img.xz ] && [ ! -f "$IMG_NAME" ]; then
  echo "==> Decompressing (xz -dk) — ~380 MB, may take a minute"
  xz -dk base.img.xz
  mv "$(basename base.img.xz .xz)" "$IMG_NAME" 2>/dev/null || true
  # Handle case where xz leaves the original name
  for f in *.img; do
    [ -f "$f" ] && [ "$f" != "$IMG_NAME" ] && mv "$f" "$IMG_NAME"
  done
fi

if [ ! -f "$IMG_NAME" ]; then
  echo "ERROR: Image file $IMG_NAME not found in $WORKDIR"
  exit 1
fi

echo "==> Attaching image (hdiutil attach -nomount)"
ATTACH_OUT=$(hdiutil attach -nomount "$IMG_NAME")
echo "$ATTACH_OUT"

DISK_ID=$(echo "$ATTACH_OUT" | head -n1 | awk '{print $1}' | sed -E 's/s[0-9]+$//')
BOOT_PART="${DISK_ID}s1"

cleanup() {
  diskutil unmount "$BOOT_PART" 2>/dev/null || true
  hdiutil detach "$DISK_ID" 2>/dev/null || true
}
trap cleanup EXIT

echo "==> Mounting boot partition ($BOOT_PART)"
diskutil mount "$BOOT_PART"
BOOT_MOUNT=$(diskutil info "$BOOT_PART" | awk -F': *' '/Mount Point/{print $2}' | sed 's/^ *//')
echo "Mounted: $BOOT_MOUNT"

echo "==> Enabling SSH"
touch "$BOOT_MOUNT/ssh"

echo "==> Creating user account"
HASH=$(openssl passwd -6 "$PI_PASSWORD")
echo "${PI_USER}:${HASH}" > "$BOOT_MOUNT/userconf.txt"

echo "==> Setting hostname"
echo "$PI_HOSTNAME" > "$BOOT_MOUNT/hostname"

if [ "$ADD_WIFI" = true ]; then
  echo "==> Adding optional WiFi config"
  cat > "$BOOT_MOUNT/wpa_supplicant.conf" <<EOF
country=PL
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
network={
    ssid="${WIFI_SSID}"
    psk="${WIFI_PASS}"
    key_mgmt=WPA-PSK
}
EOF
fi

echo "==> Appending Waveshare 3.2\" LCD config to config.txt"
cat >> "$BOOT_MOUNT/config.txt" <<'EOF'

# Waveshare 3.2" RPi LCD (B) — waveshare32b
dtparam=spi=on
dtoverlay=waveshare32b
hdmi_force_hotplug=1
max_usb_current=1
hdmi_group=2
hdmi_mode=87
hdmi_cvt 480 320 60 6 0 0 0
hdmi_drive=2
display_rotate=0
EOF

echo "==> Installing firstrun.sh"
cp "$REPO_DIR/build/firstrun.sh" "$BOOT_MOUNT/firstrun.sh"
chmod +x "$BOOT_MOUNT/firstrun.sh"

echo "==> Patching cmdline.txt for first-boot script"
CMDLINE=$(tr -d '\n' < "$BOOT_MOUNT/cmdline.txt")
printf '%s systemd.run=/boot/firstrun.sh systemd.run_success_action=none systemd.unit=kernel-command-line.target' \
  "$CMDLINE" > "$BOOT_MOUNT/cmdline.txt"

echo "==> Done: $WORKDIR/$IMG_NAME"
echo ""
echo "Flash with Raspberry Pi Imager: Choose OS -> Use custom -> select the .img"
echo "Or verify SD card with: diskutil list"
echo "    diskutil unmountDisk /dev/diskN"
echo "    sudo dd if=\"$WORKDIR/$IMG_NAME\" of=/dev/rdiskN bs=1m"
echo ""
echo "First boot: connect Ethernet, then: ssh ${PI_USER}@${PI_HOSTNAME}.local"
echo "CHANGE DEFAULT PASSWORD after first login: passwd"
