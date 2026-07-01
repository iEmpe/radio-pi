#!/usr/bin/env bash
# Radio Pi — health check, czyszczenie śmieci, VLC kodeki (bez restartu radia).
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Uruchom: sudo $0"
  exit 1
fi

PI_USER="${SUDO_USER:-pi}"
PI_HOME="$(getent passwd "$PI_USER" | cut -d: -f6)"
RADIO_ROOT=/opt/radio-pi
export DEBIAN_FRONTEND=noninteractive

echo "==> Health check (przed)"
bash "$RADIO_ROOT/build/health-check-pi.sh" /tmp/radio-pi-health-before.txt || true

echo "==> Aktualizacja list pakietów"
apt-get update -qq

echo "==> Czyszczenie cache apt"
apt-get autoremove -y
apt-get autoclean -y

echo "==> Czyszczenie logów systemd (max 40 MB)"
journalctl --vacuum-size=40M

echo "==> Usuwanie zepsutego pip numpy (armhf — używamy python3-numpy z apt)"
pip3 uninstall -y numpy 2>/dev/null || true

echo "==> Wyłączanie zbędnych usług (druk, PackageKit, modem)"
for svc in cups cups-browsed packagekit ModemManager triggerhappy; do
  systemctl disable --now "$svc" 2>/dev/null || true
done

echo "==> Hotspot awaryjny — wyłączony (WiFi skonfigurowany; powodował failed unit)"
systemctl disable --now radio-hotspot.service 2>/dev/null || true
systemctl reset-failed radio-hotspot.service 2>/dev/null || true

echo "==> Wymagane pakiety Radio Pi + VLC (pełne kodeki)"
apt-get install -y --no-install-recommends \
  python3-pyqt5 python3-pyqt5.qtsvg python3-pil python3-numpy pulseaudio-utils \
  mpv network-manager lightdm pulseaudio socat \
  vlc vlc-plugin-base vlc-plugin-video-output vlc-plugin-access-extra \
  vlc-plugin-svg vlc-plugin-visualization vlc-plugin-samba \
  libavcodec-extra \
  gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav \
  gstreamer1.0-alsa gstreamer1.0-pulseaudio \
  libaacs0 libbluray2 libdvdread8 libdvdnav4 libchromaprint1 \
  gvfs gvfs-fuse udisks2 exfat-fuse exfatprogs ntfs-3g libmtp-runtime

echo "==> Usuwanie zbędnych pakietów edukacyjnych / przeglądarek"
PURGE_LIST=(
  wolfram-engine scratch scratch3 sonic-pi minecraft-pi
  greenfoot bluej nodered chromium-browser chromium chromium-l10n
  dillo rp-bookshelf python3-pygame python3-tk
  realvnc-vnc-server realvnc-vnc-viewer
)
to_purge=()
for pkg in "${PURGE_LIST[@]}"; do
  dpkg-query -W -f='${Status}' "$pkg" 2>/dev/null | grep -q "install ok installed" && to_purge+=("$pkg")
done
if ((${#to_purge[@]})); then
  apt-get purge -y "${to_purge[@]}" || true
  apt-get autoremove -y
fi

echo "==> Optymalizacja pamięci (sysctl)"
cat >/etc/sysctl.d/99-radio-pi.conf <<'EOF'
vm.swappiness=10
vm.vfs_cache_pressure=50
EOF
sysctl --system >/dev/null 2>&1 || true

echo "==> Porządkowanie plików tymczasowych (bez aktywnych socketów radia)"
find /tmp -maxdepth 1 -type f -name 'radio-pi-mpv.log' -size +5M -delete 2>/dev/null || true
find /tmp -maxdepth 1 -type f -name 'core.*' -delete 2>/dev/null || true
find "$RADIO_ROOT" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
rm -rf "$PI_HOME/.cache/thumbnails" 2>/dev/null || true
rm -rf "$PI_HOME/Bookshelf" 2>/dev/null || true

echo "==> Porządkowanie starych plików z błędnych rsync (NIE usuwa app/data)"
if [[ -d "$RADIO_ROOT" ]]; then
  rm -rf \
    "$RADIO_ROOT/ui" \
    "$RADIO_ROOT/audio" \
    "$RADIO_ROOT/icons" \
    "$RADIO_ROOT/network" \
    "$RADIO_ROOT/__pycache__" 2>/dev/null || true
  find "$RADIO_ROOT" -maxdepth 1 -type f \( -name '*.svg' -o -name '*.py' \) -delete 2>/dev/null || true
fi

echo "==> Wyłączanie oszczędzania energii ekranu (kiosk)"
AUTOSTART="$PI_HOME/.config/autostart"
mkdir -p "$AUTOSTART"
for entry in print-applet geoclue-demo-agent; do
  cat >"$AUTOSTART/${entry}.desktop" <<EOF
[Desktop Entry]
Hidden=true
EOF
done
chown -R "$PI_USER:$PI_USER" "$AUTOSTART"

echo "==> Skrót VLC pendrive (jeśli brak)"
if [[ -x "$RADIO_ROOT/build/install-vlc-media.sh" ]]; then
  bash "$RADIO_ROOT/build/install-vlc-media.sh"
fi

echo "==> Health check (po)"
bash "$RADIO_ROOT/build/health-check-pi.sh" /tmp/radio-pi-health-after.txt || true

echo
echo "==> Podsumowanie"
df -h / | tail -1
free -h | head -2
systemctl is-active radio-ui.service 2>/dev/null || echo "radio-ui: inactive"
echo "Gotowe (radio NIE restartowane)."
