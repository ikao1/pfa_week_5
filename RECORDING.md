# Recording (≤ 1 minute)

The grader wants a short screen recording showing **(a) the terminal where you ask
the agent for the job** and **(b) Blender doing the work**. Target ≤ 60 seconds.

## One-time setup

Grant your terminal app Screen Recording permission:
**System Settings ▸ Privacy & Security ▸ Screen Recording** → enable it for
Terminal (or iTerm/opencode). Restart the terminal afterwards.
Without this, `screencapture -v` exits with code 1 and writes nothing.

## Record it

1. Open **Blender** and confirm the bridge line is in the System Console:
   `blender-bridge listening on 127.0.0.1:7788`.
2. Put this terminal and the Blender window so **both are visible** (e.g. terminal
   on the left, Blender on the right).
3. Start the capture (it records the main display for 60 s):

   ```sh
   ./record.sh 60
   ```

4. Switch to the terminal half and run:

   ```sh
   python3 demo_job.py
   ```

Output: `recording.mov` (≤ 60 s).

## 60-second shot list

| Time | On screen |
| --- | --- |
| 0:00–0:05 | Blender open, **Texture GUI** sidebar tab visible; terminal beside it. |
| 0:05–0:10 | Type and run `python3 demo_job.py`. |
| 0:10–0:20 | Watch Blender build the sphere, lights, camera and the material. |
| 0:20–0:30 | **Pass 1** render appears (gray). Terminal prints the self-check: `PROBLEM: render is nearly colourless (mean saturation 0.050)`. |
| 0:30–0:40 | Terminal prints the diagnosis + fix; Blender re-applies to the sphere and **pass 2** renders (colourful). |
| 0:40–0:55 | Show the two renders side by side: `work/demo_pass1.png` vs `work/demo_pass2.png`. |

## What "good" looks like

* The render visibly changes from **gray → colourful** after the fix.
* The terminal shows the agent's own numbers (mean saturation `0.050 → 0.213`),
  i.e. it checked itself rather than being told the answer.
