#!/usr/bin/env bash
# Deploy radio-pi to a running Raspberry Pi over SSH.
# Usage: PI_HOST=192.168.0.42 PI_PASSWORD='haslo' ./build/deploy-to-pi.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

PI_HOST="${PI_HOST:-}"
PI_USER="${PI_USER:-pi}"
PI_PASSWORD="${PI_PASSWORD:-}"
REMOTE_DIR="/opt/radio-pi"

if [ -z "$PI_HOST" ]; then
  echo "Użycie: PI_HOST=192.168.0.x PI_PASSWORD='haslo' $0" >&2
  echo "   lub: PI_HOST=radiopi.local PI_PASSWORD='haslo' $0" >&2
  exit 1
fi

SSH_OPTS=(-o StrictHostKeyChecking=accept-new -o ConnectTimeout=10)

run_ssh() {
  if [ -n "$PI_PASSWORD" ] && command -v sshpass >/dev/null 2>&1; then
    sshpass -p "$PI_PASSWORD" ssh "${SSH_OPTS[@]}" "${PI_USER}@${PI_HOST}" "$@"
  else
    ssh "${SSH_OPTS[@]}" "${PI_USER}@${PI_HOST}" "$@"
  fi
}

run_rsync() {
  local opts=(-az --delete --exclude .venv --exclude __pycache__ --exclude .git)
  if [ -n "$PI_PASSWORD" ] && command -v sshpass >/dev/null 2>&1; then
    RSYNC_RSH="sshpass -p ${PI_PASSWORD} ssh ${SSH_OPTS[*]}" rsync "${opts[@]}" -e "$RSYNC_RSH" "$@"
  else
    rsync "${opts[@]}" -e "ssh ${SSH_OPTS[*]}" "$@"
  fi
}

echo "==> Test SSH ${PI_USER}@${PI_HOST}"
run_ssh "echo OK: \$(hostname)"

echo "==> Kopiuję projekt do ${REMOTE_DIR}"
run_ssh "sudo mkdir -p ${REMOTE_DIR} && sudo chown ${PI_USER}:${PI_USER} ${REMOTE_DIR}"
run_rsync "$REPO_DIR/" "${PI_USER}@${PI_HOST}:${REMOTE_DIR}/"

echo "==> Instalacja pakietów i usług na Pi"
run_ssh "sudo bash -s" <<'REMOTE'
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y \
  network-manager mpv git python3-pip python3-pyqt5 python3-numpy \
  pulseaudio-utils \
  xserver-xorg xinit openbox unclutter socat curl unzip cmake

systemctl disable dhcpcd 2>/dev/null || true
systemctl enable NetworkManager
systemctl start NetworkManager
raspi-config nonint do_wifi_country PL 2>/dev/null || true

mkdir -p /etc/NetworkManager/conf.d
cat > /etc/NetworkManager/conf.d/99-radio-pi-wifi.conf <<'EOF'
[device]
wifi.scan-rand-mac-address=no
EOF

cd /opt/radio-pi
# pip numpy 2.x na armhf wymaga libopenblas — używamy python3-numpy z apt
pip3 uninstall -y numpy 2>/dev/null || true
pip3 install --break-system-packages -r requirements.txt 2>/dev/null \
  || pip3 install -r requirements.txt

python3 build/fetch_stations.py || true
python3 build/fetch_station_logos.py || true

# LCD już skonfigurowany — nie uruchamiaj LCD32-show ponownie

cp systemd/radio-ui.service /etc/systemd/system/
cp systemd/radio-hotspot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable radio-ui.service
# Hotspot tylko gdy brak WiFi — domyślnie wyłączony (powodował failed unit)
systemctl disable radio-hotspot.service 2>/dev/null || true
systemctl reset-failed radio-hotspot.service 2>/dev/null || true

# Usuń firstrun z cmdline jeśli jeszcze jest
if grep -q firstrun /boot/cmdline.txt 2>/dev/null; then
  sed -i 's| systemd.run=/boot/firstrun.sh systemd.run_success_action=none systemd.unit=kernel-command-line.target||g' /boot/cmdline.txt
  rm -f /boot/firstrun.sh
fi

echo "Deploy zakończony."
REMOTE

echo "==> Ikona na pulpicie"
run_ssh "sudo bash /opt/radio-pi/build/install-desktop-icon.sh"

echo ""
echo "==> Gotowe. Uruchom UI:"
echo "    ssh ${PI_USER}@${PI_HOST} 'sudo systemctl start radio-ui.service'"
echo "    lub: sudo reboot"
