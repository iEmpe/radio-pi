#!/bin/bash
# Otwórz multimedia z pendrive w VLC (montowanie: /media/pi/<nazwa>).
export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-/home/pi/.Xauthority}"

MEDIA_ROOT="/media/pi"
pick_mount() {
  local newest="" ts=0 cur
  for cur in "$MEDIA_ROOT"/*; do
    [ -d "$cur" ] || continue
    local mtime
    mtime=$(stat -c %Y "$cur" 2>/dev/null || echo 0)
    if [ "$mtime" -ge "$ts" ]; then
      ts=$mtime
      newest=$cur
    fi
  done
  printf '%s' "$newest"
}

MOUNT=$(pick_mount)

if [ -z "$MOUNT" ]; then
  notify-send "Radio Pi" "Podłącz pendrive (USB)" 2>/dev/null || true
  exec vlc --started-from-file
fi

exec vlc --started-from-file "$MOUNT"
