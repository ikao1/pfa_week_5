#!/usr/bin/env python3
"""opencode MCP server that runs scripts in a live Blender session.

Talks to the blender_bridge TCP server inside Blender (see blender_bridge.py).
"""

import json
import os
import socket
import sys
import time
import traceback
import uuid

SERVER_NAME = "blender-bridge"
SERVER_VERSION = "0.1.0"
DEFAULT_PROTOCOL = "2024-11-05"
HOST = "127.0.0.1"
PORT = int(os.environ.get("BLENDER_BRIDGE_PORT", "7788"))

MAX_FIELD = 40000
DEFAULT_TIMEOUT = 120.0
MAX_TIMEOUT = 290.0

STATUS_CODE = """import json
import bpy

info = {}
info["blender_version"] = bpy.app.version_string
platform = getattr(bpy.app, "build_platform", "")
if isinstance(platform, (bytes, bytearray)):
    platform = platform.decode("utf-8", "replace")
info["platform"] = str(platform)
info["background"] = bool(bpy.app.background)
info["filepath"] = bpy.data.filepath or "<unsaved>"
info["objects"] = len(bpy.data.objects)
try:
    info["scene"] = bpy.context.scene.name if bpy.context.scene else "<none>"
except Exception:
    info["scene"] = "<none>"
try:
    info["mode"] = bpy.context.mode
except Exception:
    info["mode"] = "<unknown>"
try:
    selected = bpy.context.selected_objects
    info["selected"] = len(selected)
    info["selection"] = [obj.name for obj in selected[:20]]
except Exception:
    info["selected"] = 0
    info["selection"] = []
print(json.dumps(info, indent=2))
"""

TOOLS = [
    {
        "name": "run",
        "description": (
            "Execute Python in the connected live Blender session and return its output. "
            "The code runs on Blender's main thread, so the UI blocks until it finishes. "
            "Python globals persist across calls (a persistent REPL session), and `bpy`, "
            "`bmesh`, and `mathutils` are pre-imported in that namespace. The value of the "
            "last expression is returned as `result`, Python-REPL style. Output sections: "
            "stdout (prints), result (last expression), error (traceback when the script "
            "raised). Fails with isError=true only when the bridge itself is unreachable or "
            "times out; script exceptions are returned in-band under `error`. Requires "
            "Blender to be running with the bridge open (it auto-starts on launch; otherwise "
            "run `import blender_bridge; blender_bridge.start()` in the Scripting workspace)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python source to execute inside Blender.",
                },
                "timeout_seconds": {
                    "type": "number",
                    "description": (
                        "Seconds to wait for the result, default 120, max 290. "
                        "Blender keeps running a script after a timeout."
                    ),
                },
            },
            "required": ["code"],
        },
    },
    {
        "name": "status",
        "description": (
            "Check that the live Blender bridge is reachable and report the Blender "
            "version, platform, current .blend file, scene, object count, mode, and "
            "selection. Use before the run tool when a connection error is suspected, or "
            "to inspect the open session without writing a script."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
]


class BridgeError(Exception):
    pass


def _truncate(text, limit=MAX_FIELD):
    if text is None or len(text) <= limit:
        return text or ""
    return text[:limit] + "\n...[truncated %d chars]" % (len(text) - limit)


def bridge_call(code, timeout):
    request = {"bridge": 1, "id": uuid.uuid4().hex, "code": code, "lang": "python"}
    try:
        sock = socket.create_connection((HOST, PORT), timeout=5)
    except OSError as exc:
        reason = getattr(exc, "strerror", None) or str(exc)
        raise BridgeError(
            "Cannot reach the Blender bridge at %s:%d (%s).\n"
            "Open Blender - the bridge auto-starts on launch. To start it manually, "
            "run in Blender's Scripting workspace:\n\n"
            "    import blender_bridge\n"
            "    blender_bridge.start()\n\n"
            "For a headless session, run:\n\n"
            "    import blender_bridge\n"
            "    blender_bridge.run()" % (HOST, PORT, reason)
        )
    fh = None
    try:
        sock.settimeout(timeout)
        sock.sendall((json.dumps(request) + "\n").encode("utf-8"))
        fh = sock.makefile("rb")
        line = fh.readline()
        if not line:
            raise BridgeError(
                "The Blender bridge closed the connection without responding "
                "(Blender may be quitting or busy)."
            )
        try:
            response = json.loads(line.decode("utf-8"))
        except ValueError:
            raise BridgeError(
                "Port %d accepted the connection but did not answer the blender-bridge "
                "handshake; another service may be using this port." % PORT
            )
        if not isinstance(response, dict) or response.get("bridge") != 1:
            raise BridgeError(
                "Port %d answered with an unrecognized payload; another service may be "
                "using this port." % PORT
            )
        return response
    except (socket.timeout, TimeoutError):
        raise BridgeError(
            "Timed out after %g seconds waiting for Blender. The script is probably still "
            "running (Blender's UI blocks while a script runs). Increase timeout_seconds if "
            "the script is legitimately slow." % timeout
        )
    finally:
        if fh is not None:
            try:
                fh.close()
            except Exception:
                pass
        sock.close()


def _tool_blender_run(args):
    code = args.get("code")
    if not isinstance(code, str) or not code.strip():
        return "'code' must be a non-empty string", True
    timeout = args.get("timeout_seconds")
    try:
        timeout = float(timeout) if timeout is not None else DEFAULT_TIMEOUT
    except (TypeError, ValueError):
        return "'timeout_seconds' must be a number", True
    timeout = max(1.0, min(timeout, MAX_TIMEOUT))

    started = time.time()
    try:
        response = bridge_call(code, timeout)
    except BridgeError as exc:
        return str(exc), True
    elapsed = time.time() - started

    if response.get("ok"):
        parts = ["status: ok (%.2fs)" % elapsed]
    else:
        parts = ["status: script error (%.2fs)" % elapsed]
    stdout = (response.get("stdout") or "").strip("\n")
    if stdout:
        parts.append("--- stdout ---\n" + stdout)
    if response.get("result") is not None:
        parts.append("--- result ---\n" + response["result"])
    if response.get("error"):
        parts.append("--- error ---\n" + response["error"].rstrip("\n"))
    text = "\n".join(parts)
    return _truncate(text, MAX_FIELD * 3), False


def _tool_blender_status(args):
    started = time.time()
    try:
        response = bridge_call(STATUS_CODE, timeout=15)
    except BridgeError as exc:
        return str(exc), True
    elapsed = (time.time() - started) * 1000
    if not response.get("ok"):
        text = (
            "Blender bridge is reachable on port %d, but the status script failed:\n\n%s"
            % (PORT, (response.get("error") or "unknown error").rstrip("\n"))
        )
        return _truncate(text), False
    stdout = (response.get("stdout") or "").strip()
    text = "Bridge OK on port %d (round trip %.0f ms)\n%s" % (PORT, elapsed, stdout)
    return _truncate(text, MAX_FIELD * 2), False


_HANDLERS = {"run": _tool_blender_run, "status": _tool_blender_status}

_INSTRUCTIONS = (
    "Tools run Python in a live Blender session through a local TCP bridge. "
    "Use blender_status to confirm Blender is reachable, then blender_run to execute "
    "Python. Scripts block Blender's UI while running and Python globals persist across "
    "blender_run calls; bpy, bmesh, and mathutils are pre-imported."
)


def _send(message):
    sys.stdout.write(json.dumps(message) + "\n")
    sys.stdout.flush()


def _result(msg_id, result):
    _send({"jsonrpc": "2.0", "id": msg_id, "result": result})


def _error(msg_id, code, message):
    _send({"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}})


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except ValueError:
            continue
        if not isinstance(message, dict):
            continue
        msg_id = message.get("id")
        if msg_id is None:
            continue
        method = message.get("method")
        if method == "initialize":
            params = message.get("params") or {}
            client_version = params.get("protocolVersion")
            _result(
                msg_id,
                {
                    "protocolVersion": (
                        client_version if isinstance(client_version, str) else DEFAULT_PROTOCOL
                    ),
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                    "instructions": _INSTRUCTIONS,
                },
            )
        elif method == "ping":
            _result(msg_id, {})
        elif method == "tools/list":
            _result(msg_id, {"tools": TOOLS})
        elif method == "tools/call":
            params = message.get("params") or {}
            handler = _HANDLERS.get(params.get("name"))
            if handler is None:
                _error(msg_id, -32602, "Unknown tool: %s" % params.get("name"))
                continue
            try:
                text, is_error = handler(params.get("arguments") or {})
            except Exception:
                text, is_error = "blender-bridge server error:\n" + traceback.format_exc(), True
            _result(
                msg_id,
                {
                    "content": [{"type": "text", "text": text}],
                    "isError": is_error,
                },
            )
        else:
            _error(msg_id, -32601, "Method not found: %s" % method)


if __name__ == "__main__":
    try:
        main()
    except (BrokenPipeError, KeyboardInterrupt):
        pass
