#!/usr/bin/env bash
# Naprawa Waveshare 3.2" RPi LCD (B) na Raspberry Pi OS Bullseye (desktop).
# Uruchom NA Pi po SSH: sudo bash fix_lcd_waveshare32b.sh
set -euo pipefail

echo "==> Radio Pi: instalacja sterownika Waveshare 3.2\" LCD (B)"
echo "    OS: $(grep PRETTY_NAME /etc/os-release | cut -d= -f2 | tr -d '\"')"

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y git unzip cmake build-essential

if [ ! -d /root/LCD-show ]; then
  git clone https://github.com/waveshare/LCD-show.git /root/LCD-show
fi
cd /root/LCD-show
chmod +x LCD32-show LCD-hdmi

# Desktop Bullseye — bez "lite"
echo "==> Uruchamiam LCD32-show (wymaga internetu dla dotyku)…"
./LCD32-show || {
  echo "WARN: LCD32-show zwrócił błąd — sprawdzam config.txt ręcznie"
}

CONFIG=/boot/config.txt
if [ -f /boot/firmware/config.txt ]; then
  CONFIG=/boot/firmware/config.txt
fi

echo "==> Weryfikacja $CONFIG"
grep -E 'waveshare32b|dtparam=spi|ads7846' "$CONFIG" || true

# Konflikt ads7846 + waveshare32b (znany problem po dist-upgrade)
if grep -q 'dtoverlay=ads7846' "$CONFIG" && grep -q 'dtoverlay=waveshare32b' "$CONFIG"; then
  echo "==> Usuwam zduplikowany dtoverlay=ads7846"
  sed -i '/dtoverlay=ads7846/d' "$CONFIG"
fi

if ! grep -q 'dtoverlay=waveshare32b' "$CONFIG"; then
  echo "==> Dodaję konfigurację Waveshare"
  cat >> "$CONFIG" <<'EOF'

# Waveshare 3.2" RPi LCD (B)
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
fi

echo ""
echo "==> Gotowe. Reboot za 5 s…"
sleep 5
reboot
