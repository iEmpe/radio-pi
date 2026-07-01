#!/bin/bash
# X session launcher for Radio Pi kiosk
export DISPLAY=:0
xset s off
xset -dpms
xset s noblank
unclutter -idle 0 &
openbox-session &
sleep 1
cd /opt/radio-pi
exec python3 -m app.main
