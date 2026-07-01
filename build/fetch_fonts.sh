#!/usr/bin/env bash
# Fetch bundled UI fonts (JetBrains Mono + DSEG7 clock).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEST="$SCRIPT_DIR/../app/assets/fonts"
mkdir -p "$DEST"

echo "==> JetBrains Mono"
BASE="https://github.com/JetBrains/JetBrainsMono/raw/master/fonts/ttf"
for f in JetBrainsMono-Regular.ttf JetBrainsMono-Bold.ttf; do
  curl -fsSL -o "$DEST/$f" "$BASE/$f"
done

echo "==> DSEG7 Modern Bold"
ZIP="/tmp/fonts-DSEG.zip"
curl -fsSL -o "$ZIP" "https://github.com/keshikan/DSEG/releases/download/v0.46/fonts-DSEG_v046.zip"
unzip -j -o "$ZIP" "fonts-DSEG_v046/DSEG7-Modern/DSEG7Modern-Bold.ttf" -d "$DEST"

echo "Fonts saved to $DEST"
