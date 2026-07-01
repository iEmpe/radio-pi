#!/usr/bin/env bash
# Włącza autostart Radio Pi po bootcie (systemd + koperta LXDE).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Uruchom: sudo $0"
  exit 1
fi

PI_USER="${SUDO_USER:-pi}"
PI_HOME="$(getent passwd "$PI_USER" | cut -d: -f6)"

echo "==> Usługa systemd radio-ui"
install -m 644 "$REPO_DIR/systemd/radio-ui.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable lightdm.service 2>/dev/null || true
systemctl enable radio-ui.service
systemctl reset-failed radio-ui.service 2>/dev/null || true

echo "==> Autostart LXDE (zapasowy, po 12 s)"
AUTOSTART="$PI_HOME/.config/autostart"
mkdir -p "$AUTOSTART"
cat >"$AUTOSTART/radio-pi.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Radio Pi
Comment=Internet radio kiosk
Exec=/bin/bash -c 'sleep 12; exec /opt/radio-pi/build/start-ui-desktop.sh'
Terminal=false
Categories=Audio;
X-GNOME-Autostart-enabled=true
EOF
chown -R "$PI_USER:$PI_USER" "$AUTOSTART"

echo "==> Hotspot awaryjny — wyłączony (sieć skonfigurowana)"
systemctl disable radio-hotspot.service 2>/dev/null || true
systemctl stop radio-hotspot.service 2>/dev/null || true

echo "==> Polkit: skan WiFi dla użytkownika pi"
PKLA_DIR="/etc/polkit-1/localauthority/50-local.d"
RULES_DIR="/etc/polkit-1/rules.d"
mkdir -p "$PKLA_DIR"
install -m 644 "$REPO_DIR/build/polkit/50-radio-pi-wifi.pkla" \
  "$PKLA_DIR/50-radio-pi-wifi.pkla"
if [ -d "$RULES_DIR" ]; then
  install -m 644 "$REPO_DIR/build/polkit/50-radio-pi-wifi.rules" \
    "$RULES_DIR/50-radio-pi-wifi.rules"
fi

echo "==> Zależności Python (systemowe na Pi)"
apt-get install -y \
  python3-pil python3-numpy python3-pyqt5 python3-pyqt5.qtsvg \
  mpv network-manager 2>/dev/null || true
pip3 install --break-system-packages -r "$REPO_DIR/requirements.txt" 2>/dev/null \
  || pip3 install -r "$REPO_DIR/requirements.txt" 2>/dev/null || true

echo "Gotowe. Po reboot: systemctl status radio-ui"
