#!/bin/sh
# Copy the apps and config onto the badge. Put the badge in Disk mode first
# (double-press RESET) so it mounts as /Volumes/TUFTY.
set -e
cd "$(dirname "$0")/.."
T=${1:-/Volumes/TUFTY}
[ -d "$T/apps" ] || { echo "badge drive not found at $T"; exit 1; }
for app in apps/*/; do
  mkdir -p "$T/$app" && cp -R "$app" "$T/$app"
done
cp config/profile.py config/profile.png "$T/"
[ -f config/secrets.py ] && cp config/secrets.py "$T/"
# macOS resource forks would show up in the launcher as broken apps
find "$T" -name '._*' -delete
sync
echo "installed; eject TUFTY and press RESET"
