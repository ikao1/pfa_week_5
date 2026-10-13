"""Minimal client for the blender-bridge port (127.0.0.1:7788).

Sends a Python snippet to the live Blender session and returns the bridge's
response dict (ok, stdout, result, error). Used by ``demo_job.py`` and usable
on its own:

    python3 bridge_client.py run "print(bpy.app.version_string)"
    python3 bridge_client.py file some_snippet.py
"""

import json
import os
import socket
import sys

HOST = "127.0.0.1"
PORT = int(os.environ.get("BLENDER_BRIDGE_PORT", "7788"))
DEFAULT_TIMEOUT = float(os.environ.get("BLENDER_BRIDGE_TIMEOUT", "300"))


def send(code, timeout=DEFAULT_TIMEOUT, host=HOST, port=PORT):
    """Execute ``code`` in the running Blender and return the response dict."""
    payload = json.dumps({"id": 1, "code": code}).encode("utf-8") + b"\n"
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.sendall(payload)
        buf = b""
        while not buf.endswith(b"\n"):
            chunk = sock.recv(4096)
            if not chunk:
                break
            buf += chunk
    return json.loads(buf.decode("utf-8"))


def run(code, timeout=DEFAULT_TIMEOUT):
    """Like ``send`` but prints the response and returns it. Raises on error."""
    resp = send(code, timeout=timeout)
    if resp.get("stdout"):
        sys.stdout.write(resp["stdout"])
    if resp.get("result") is not None:
        print("-> %s" % resp["result"])
    if resp.get("error"):
        raise RuntimeError(resp["error"])
    return resp


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    mode = argv[1]
    if mode == "run":
        run(" ".join(argv[2:]))
    elif mode == "file":
        with open(argv[2]) as handle:
            run(handle.read())
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
