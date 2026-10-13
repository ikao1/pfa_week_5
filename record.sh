#!/usr/bin/env bash
# Record a <= 1 minute demo of the Blender bridge job (macOS).
#
# Requires: Blender open with the bridge running (see README), and Screen
# Recording permission for your terminal in System Settings > Privacy &
# Security > Screen Recording.
#
# Usage:
#   ./record.sh          # records 60s to recording.mov
#   ./record.sh 45       # records 45s
set -euo pipefail

SECONDS_TO_RECORD="${1:-60}"
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/recording.mov"

rm -f "$OUT"
echo "Recording ${SECONDS_TO_RECORD}s to $OUT"
echo "Now, in another terminal/window, run:  python3 demo_job.py"
echo "Keep both Blender and this terminal on screen. Click to highlight if you like."

# -v video, -V duration, -k show clicks, -D 1 main display
screencapture -v -V "$SECONDS_TO_RECORD" -k -D 1 "$OUT"

echo "Saved $OUT"
