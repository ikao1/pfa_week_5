"""Bridge server for opencode <-> Blender.

Listens on 127.0.0.1:<BLENDER_BRIDGE_PORT or 7788> for newline-delimited JSON
requests and executes Python on Blender's main thread, returning stdout, the
value of the last expression, and any traceback.

In the GUI the bridge auto-starts via
``<user scripts>/startup/opencode_blender_bridge.py`` and executes requests
through ``bpy.app.timers``, which runs callbacks on Blender's main thread while
the UI is idle. To start it manually, run this in the Scripting workspace:

    import blender_bridge
    blender_bridge.start()

``blender --background`` has no UI event loop for the timer to piggyback on, so
drive the pump explicitly and keep the process alive:

    import blender_bridge
    blender_bridge.run()
"""

import ast
import io
import json
import os
import queue
import socket
import socketserver
import sys
import threading
import traceback

DEFAULT_PORT = int(os.environ.get("BLENDER_BRIDGE_PORT", "7788"))
HOST = "127.0.0.1"

MAX_STDOUT = 400000
MAX_RESULT = 100000
MAX_ERROR = 100000

# How often the GUI timer polls for queued work, in seconds.
POLL_INTERVAL = 0.02

_jobs = queue.Queue()
_server = None
_py_namespace = None
_stop = threading.Event()
_timer_active = False


def _truncate(text, limit):
    if text is None or len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated %d chars]" % (len(text) - limit)


def _safe_repr(value):
    try:
        text = repr(value)
    except Exception as exc:
        text = "<repr failed: %s>" % exc
    return _truncate(text, MAX_RESULT)


def _namespace():
    global _py_namespace
    if _py_namespace is None:
        _py_namespace = {"__name__": "__blender_bridge__"}
        for name in ("bpy", "bmesh", "mathutils"):
            try:
                _py_namespace[name] = __import__(name)
            except ImportError:
                pass
    return _py_namespace


def _exec_python(code):
    stdout = io.StringIO()
    result = None
    error = None
    ns = _namespace()
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout = stdout
    sys.stderr = stdout
    try:
        tree = ast.parse(code, filename="<blender-bridge>", mode="exec")
        if tree.body and isinstance(tree.body[-1], ast.Expr):
            head = ast.Module(body=tree.body[:-1], type_ignores=[])
            exec(compile(head, "<blender-bridge>", "exec"), ns)
            tail = ast.Expression(tree.body[-1].value)
            result = _safe_repr(eval(compile(tail, "<blender-bridge>", "eval"), ns))
        else:
            exec(compile(tree, "<blender-bridge>", "exec"), ns)
    except BaseException:
        error = traceback.format_exc()
    finally:
        sys.stdout = old_out
        sys.stderr = old_err
    return {
        "ok": error is None,
        "stdout": _truncate(stdout.getvalue(), MAX_STDOUT),
        "result": result,
        "error": _truncate(error, MAX_ERROR) if error else None,
    }


def _execute(code, lang):
    # Blender has no MEL; anything that is not an explicit unsupported language
    # is treated as Python.
    if lang not in (None, "python"):
        return {
            "ok": False,
            "stdout": "",
            "result": None,
            "error": "unsupported lang %r (only 'python' is available)" % (lang,),
        }
    return _exec_python(code)


def _pump():
    """Run every queued job on the calling (main) thread. Returns how many ran."""
    handled = 0
    while True:
        try:
            job = _jobs.get_nowait()
        except queue.Empty:
            break
        job["result"].put(_execute(job["code"], job.get("lang")))
        handled += 1
    return handled


def _timer_tick():
    # Runs on Blender's main thread. Return the delay until the next poll; a
    # persistent timer stays registered even if this returns None.
    try:
        _pump()
    except BaseException:
        print("blender-bridge pump error:\n" + traceback.format_exc())
    return POLL_INTERVAL


class _Handler(socketserver.StreamRequestHandler):
    def handle(self):
        try:
            self.connection.settimeout(600)
        except OSError:
            pass
        while True:
            try:
                line = self.rfile.readline()
            except Exception:
                break
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            response = self._dispatch(line)
            try:
                self.wfile.write((json.dumps(response) + "\n").encode("utf-8"))
                self.wfile.flush()
            except Exception:
                break

    def _dispatch(self, line):
        try:
            request = json.loads(line.decode("utf-8"))
            if not isinstance(request, dict):
                raise ValueError("request must be a JSON object")
        except Exception:
            return {"bridge": 1, "ok": False, "error": "invalid JSON request"}
        response = {"bridge": 1, "id": request.get("id")}
        code = request.get("code")
        if not isinstance(code, str):
            response.update(
                {"ok": False, "stdout": "", "result": None, "error": "missing 'code' string"}
            )
            return response
        job = {"code": code, "lang": request.get("lang"), "result": queue.Queue(1)}
        _jobs.put(job)
        try:
            result = job["result"].get(timeout=600)
        except queue.Empty:
            result = {
                "ok": False,
                "stdout": "",
                "result": None,
                "error": "timed out waiting for Blender's main thread",
            }
        response.update(result)
        return response


class _Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def _probe(port):
    try:
        sock = socket.create_connection((HOST, port), timeout=1)
    except OSError:
        return False
    try:
        sock.settimeout(2)
        sock.sendall(b'{"id": 0, "code": "pass"}\n')
        return bool(sock.makefile("rb").readline())
    except OSError:
        return False
    finally:
        sock.close()


def _register_timer():
    global _timer_active
    if _timer_active:
        return False
    try:
        import bpy
    except ImportError:
        return False
    if getattr(bpy.app, "background", False):
        # No UI event loop to host the timer; caller must use run().
        return False
    try:
        bpy.app.timers.register(_timer_tick, persistent=True)
    except ValueError:
        # Already registered from a previous start() in this session.
        pass
    _timer_active = True
    return True


def _start_server(port):
    global _server
    if port is None:
        port = DEFAULT_PORT
    if _server is not None:
        return {"status": "already_running", "port": _server.server_address[1]}
    try:
        _server = _Server((HOST, port), _Handler)
    except OSError:
        if _probe(port):
            return {"status": "already_running", "port": port}
        raise
    thread = threading.Thread(target=_server.serve_forever, daemon=True, name="blender-bridge")
    thread.start()
    return {"status": "started", "port": port}


def start(port=None):
    """Start the bridge without blocking. In the GUI a timer drives execution;
    in ``--background`` mode use run() instead."""
    _stop.clear()
    info = _start_server(port)
    if info.get("status") == "started":
        info["timer"] = _register_timer()
        print("blender-bridge listening on %s:%d" % (HOST, info["port"]))
    return info


def run(port=None):
    """Start the bridge and pump jobs on the main thread until stop(). For
    headless (``--background``) sessions."""
    _stop.clear()
    info = _start_server(port)
    print("blender-bridge: pumping on the main thread (headless)")
    try:
        while not _stop.is_set():
            try:
                job = _jobs.get(timeout=0.5)
            except queue.Empty:
                continue
            job["result"].put(_execute(job["code"], job.get("lang")))
    except KeyboardInterrupt:
        pass
    finally:
        stop()
    return info


def stop():
    global _server, _timer_active
    _stop.set()
    if _timer_active:
        try:
            import bpy

            bpy.app.timers.unregister(_timer_tick)
        except Exception:
            pass
        _timer_active = False
    if _server is None:
        return {"status": "not_running"}
    _server.shutdown()
    _server.server_close()
    _server = None
    return {"status": "stopped"}


if __name__ == "__main__":
    info = run()
