#!/usr/bin/env bash
# One-command demo recorder: capture the main display, then run the job.
#
# Requires Screen Recording permission for Terminal.app
# (System Settings > Privacy & Security > Screen Recording), and a Blender
# session with the bridge running (see README).
#
# Usage:
#   ./record_and_run.sh         # 45s capture, runs the job after 4s
#   ./record_and_run.sh 60
set -euo pipefail

SEC="${1:-45}"
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/recording.mov"

rm -f "$OUT"
echo "Recording ${SEC}s -> $OUT"
echo "Make sure Blender (with the Texture GUI tab) is visible next to this terminal."

screencapture -v -V "$SEC" -k -D 1 "$OUT" &
REC=$!

sleep 4
echo "Running the job now..."
python3 "$HERE/demo_job.py"

wait "$REC" || true
echo "Saved $OUT"
