#!/usr/bin/env bash
# VLC + pełne kodeki + skrót pulpitu + domyślny odtwarzacz plików z pendrive.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Uruchom: sudo $0"
  exit 1
fi

PI_USER="${SUDO_USER:-pi}"
PI_HOME="$(getent passwd "$PI_USER" | cut -d: -f6)"
DESKTOP="$PI_HOME/Desktop/vlc-pendrive.desktop"

echo "==> Instalacja VLC + kodeki"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends \
  vlc vlc-plugin-base vlc-plugin-video-output vlc-plugin-access-extra \
  vlc-plugin-svg vlc-plugin-visualization vlc-plugin-samba \
  libavcodec-extra \
  gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav \
  gstreamer1.0-alsa gstreamer1.0-pulseaudio \
  libaacs0 libbluray2 libdvdread8 libdvdnav4 libchromaprint1 \
  gvfs gvfs-fuse udisks2 pcmanfm \
  libmtp-runtime exfat-fuse exfatprogs ntfs-3g

chmod +x "$REPO_DIR/build/open-usb-media.sh"

echo "==> Skrót na pulpicie"
install -m 755 "$REPO_DIR/build/vlc-media.desktop" "$DESKTOP"
chown "$PI_USER:$PI_USER" "$DESKTOP"
if command -v gio >/dev/null 2>&1 && [[ -n "${SUDO_USER:-}" ]]; then
  sudo -u "$PI_USER" gio set "$DESKTOP" metadata::trusted true 2>/dev/null || true
fi
install -m 644 "$REPO_DIR/build/vlc-media.desktop" /usr/share/applications/vlc-pendrive.desktop

echo "==> Domyślny odtwarzacz (VLC) dla plików audio/wideo"
if id "$PI_USER" >/dev/null 2>&1; then
  for mime in \
    video/mp4 video/x-matroska video/webm video/quicktime video/x-msvideo \
    video/mpeg audio/mpeg audio/mp3 audio/x-flac audio/x-wav audio/ogg \
    application/ogg; do
    sudo -u "$PI_USER" xdg-mime default vlc.desktop "$mime" 2>/dev/null || true
  done
fi

echo "==> Montowanie USB (udisks2)"
systemctl enable udisks2 2>/dev/null || true
systemctl start udisks2 2>/dev/null || true

echo "Gotowe."
echo "  Pendrive montuje się w: /media/pi/<nazwa>"
echo "  Kliknij na pulpicie: VLC — pendrive"
