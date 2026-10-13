#!/usr/bin/env bash
# Install the Blender-side bridge into the user's Blender scripts directory.
set -euo pipefail

VERSION="${1:-5.2}"
BASE="$HOME/Library/Application Support/Blender/$VERSION/scripts"
HERE="$(cd "$(dirname "$0")" && pwd)"

if [ ! -d "$BASE" ]; then
  echo "Blender user scripts dir not found: $BASE" >&2
  echo "Pass the Blender version (major.minor) as the first argument, e.g. ./install.sh 5.2" >&2
  exit 1
fi

mkdir -p "$BASE/modules" "$BASE/startup"
cp "$HERE/blender_bridge.py" "$BASE/modules/blender_bridge.py"
cp "$HERE/startup.py" "$BASE/startup/opencode_blender_bridge.py"

echo "Installed blender_bridge.py  -> $BASE/modules/blender_bridge.py"
echo "Installed startup hook       -> $BASE/startup/opencode_blender_bridge.py"
echo
echo "Restart Blender; the bridge starts on launch and listens on 127.0.0.1:7788."
