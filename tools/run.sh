#!/bin/sh
# Run an app straight from RAM over USB serial, without touching the badge's
# files:  tools/run.sh apps/memes/__init__.py
set -e
PORT=${PORT:-$(ls /dev/cu.usbmodem* | head -1)}
TMP=$(mktemp -t badge).py
printf 'import sys\nif "/system" not in sys.path: sys.path.insert(0, "/system")\n' > "$TMP"
cat "$1" >> "$TMP"
mpremote connect "$PORT" run "$TMP"
