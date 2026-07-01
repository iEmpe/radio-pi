#!/usr/bin/env bash
# First-boot setup script for Radio Pi (runs on Raspberry Pi via Ethernet).
# WARNING: Change the default password after first SSH login (passwd).
set -euo pipefail

LOG="/var/log/radio-pi-firstrun.log"
exec > >(tee -a "$LOG") 2>&1

echo "==> Radio Pi first-run setup started at $(date)"

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get upgrade -y

echo "==> Installing packages"
apt-get install -y \
  network-manager \
  mpv \
  git \
  python3-pip \
  python3-pyqt5 \
  xserver-xorg \
  xinit \
  openbox \
  unclutter \
  socat

echo "==> Disabling dhcpcd, enabling NetworkManager"
systemctl disable dhcpcd || true
systemctl enable NetworkManager
systemctl start NetworkManager

echo "==> WiFi country + 2.4 GHz default"
raspi-config nonint do_wifi_country PL || true

# Default band preference for new WiFi profiles
mkdir -p /etc/NetworkManager/conf.d
cat > /etc/NetworkManager/conf.d/99-radio-pi-wifi.conf <<'EOF'
[device]
wifi.scan-rand-mac-address=no
EOF

echo "==> Cloning radio-pi repository"
REPO_DIR="/opt/radio-pi"
mkdir -p "$REPO_DIR"
if [ ! -f "$REPO_DIR/app/main.py" ]; then
  echo "WARN: Brak /opt/radio-pi — uruchom z Maca: PI_HOST=… ./build/deploy-to-pi.sh"
fi

if [ -f "$REPO_DIR/requirements.txt" ]; then
  pip3 install --break-system-packages -r "$REPO_DIR/requirements.txt" 2>/dev/null \
    || pip3 install -r "$REPO_DIR/requirements.txt"
fi

echo "==> Installing Waveshare LCD driver"
if [ ! -d /root/LCD-show ]; then
  git clone https://github.com/waveshare/LCD-show.git /root/LCD-show
fi
cd /root/LCD-show
chmod +x LCD32-show
./LCD32-show lite || echo "WARN: LCD32-show may need reboot"

echo "==> Installing systemd units"
cp "$REPO_DIR/systemd/radio-ui.service" /etc/systemd/system/
cp "$REPO_DIR/systemd/radio-hotspot.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable radio-ui.service
systemctl enable radio-hotspot.service

echo "==> First-run complete — rebooting"
# Remove self from cmdline on next boot is handled by one-shot nature
rm -f /boot/firstrun.sh
reboot
