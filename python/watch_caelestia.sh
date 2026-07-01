#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WALLPAPER_FILE="$HOME/.local/state/caelestia/wallpaper/path.txt"

echo "Watching $WALLPAPER_FILE ..."
while inotifywait -e modify "$WALLPAPER_FILE"; do
    python3 "$SCRIPT_DIR/send_palette_from_image.py" --current-wallpaper --send "$@"
done
