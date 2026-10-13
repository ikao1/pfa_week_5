"""Auto-start the opencode Blender bridge when Blender launches.

Installed as ``<user scripts>/startup/opencode_blender_bridge.py``. At startup
time Blender has not yet added ``<user scripts>/modules`` to ``sys.path``, so we
add it here before importing ``blender_bridge``. Blender 5.x also expects
registerable startup scripts to define ``register()`` / ``unregister()``.
"""

import sys


def _module_dir():
    try:
        import bpy

        return bpy.utils.user_resource("SCRIPTS", path="modules", create=False)
    except Exception:
        return None


_MODULES = _module_dir()
if _MODULES and _MODULES not in sys.path:
    sys.path.insert(0, _MODULES)


def register():
    try:
        import bpy

        if bpy.app.background:
            # No UI event loop for the main-thread timer; use blender_bridge.run().
            return
    except Exception:
        pass
    try:
        import blender_bridge

        blender_bridge.start()
    except Exception as exc:  # never break Blender startup
        print("blender-bridge failed to start: %s" % exc)


def unregister():
    try:
        import blender_bridge

        blender_bridge.stop()
    except Exception:
        pass


# Blender runs this file at launch; call register() directly so the bridge starts
# even on versions that do not auto-invoke register() for startup scripts.
register()
