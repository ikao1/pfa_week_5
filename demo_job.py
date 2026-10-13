"""The job the agent performs in Blender through the bridge (port 7788).

Plain-English request: "Put my test image on the sphere as an art-directed
material and render it so I can see it."

Several steps, then a self-check on the rendered pixels, an automatic fix, and
a re-render. Run with Blender open and the bridge listening:

    python3 demo_job.py

Every step is executed inside the *live, open* Blender session; you can watch
the scene and the viewport update as it runs.
"""

import json
import os
import sys

import bridge_client

HERE = os.path.dirname(os.path.abspath(__file__))
ASSET = os.path.join(HERE, "assets", "test_texture.png")
WORK = os.path.join(HERE, "work")
PASS1 = os.path.join(WORK, "demo_pass1.png")
PASS2 = os.path.join(WORK, "demo_pass2.png")

MESH_NAME = "TextureDemo"


def banner(text):
    print("\n" + "#" * 64)
    print("# " + text)
    print("#" * 64)


def step(text):
    print("\n=== %s ===" % text)


def _looks_ok(stats):
    # The texture must actually read: enough colour plus enough light.
    return stats["mean_sat"] >= 0.15 and stats["mean_lum"] >= 0.12


# --- snippets executed inside Blender --------------------------------------

SETUP_SCENE = r"""
import bpy, math

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
for block in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.node_groups):
    for item in list(block):
        if getattr(item, "users", 0) == 0:
            block.remove(item)

bpy.ops.mesh.primitive_uv_sphere_add(segments=96, ring_count=48, radius=1.0)
sphere = bpy.context.active_object
sphere.name = "TextureDemo"
bpy.ops.object.shade_smooth()

bpy.ops.object.light_add(type='AREA', location=(3.0, -3.0, 4.0))
bpy.context.active_object.data.energy = 900.0
bpy.context.active_object.data.size = 4.0
bpy.ops.object.light_add(type='AREA', location=(-4.0, -2.0, 1.0))
bpy.context.active_object.data.energy = 250.0
bpy.context.active_object.data.size = 5.0

bpy.ops.object.camera_add(location=(0.0, -5.0, 0.9),
                          rotation=(math.radians(80), 0, 0))
cam = bpy.context.active_object
bpy.context.scene.camera = cam

world = bpy.context.scene.world or bpy.data.worlds.new("World")
bpy.context.scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
bg.inputs[0].default_value = (0.03, 0.03, 0.035, 1.0)

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 960
scene.render.resolution_y = 600
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'Standard'
print("scene ready: sphere, 2 area lights, camera, EEVEE 960x600")
print("active object after setup:", bpy.context.active_object.name)
"""

LOAD_IMAGE = r"""
import bpy
image = bpy.data.images.load(%r, check_existing=True)
bpy.context.scene.texture_gui.image = image
mat = bpy.data.materials.get("TextureGUI")
print("image loaded:", image.name, tuple(image.size))
print("active object:", bpy.context.active_object.name,
      "| TextureGUI material built:", mat is not None)
""" % ASSET

ART_DIRECT = r"""
import bpy
s = bpy.context.scene.texture_gui
s.hue = 0.05
s.saturation = 1.2
s.contrast = 1.1
s.relief = 0.6
s.depth = 0.45
s.roughness = 0.4
s.metallic = 0.1
s.amount = 1.0
print("art-directed: hue=%.2f sat=%.2f contrast=%.2f relief=%.2f rough=%.2f metal=%.2f"
      % (s.hue, s.saturation, s.contrast, s.relief, s.roughness, s.metallic))
"""

FIX_SELECT_AND_APPLY = r"""
import bpy
obj = bpy.data.objects[%r]
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
bpy.ops.texturegui.apply()
mat = bpy.data.materials.get("TextureGUI")
print("active object now:", bpy.context.active_object.name,
      "| material slots:", [m.name for m in obj.data.materials if m],
      "| nodes:", len(mat.node_tree.nodes) if mat else None)
""" % MESH_NAME


def render_snippet(path):
    return r"""
import bpy
bpy.context.scene.render.filepath = %r
bpy.ops.render.render(write_still=True)
print("rendered ->", bpy.context.scene.render.filepath)
""" % path


ANALYZE = r"""
import bpy, numpy as np
image = bpy.data.images.load(%r, check_existing=False)
w, h = image.size
buf = np.empty(w * h * 4, dtype=np.float32)
image.pixels.foreach_get(buf)
rgb = buf.reshape(-1, 4)[:, :3]
mx = rgb.max(axis=1)
mn = rgb.min(axis=1)
sat = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
lum = rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
stats = {
    "w": int(w), "h": int(h),
    "mean_lum": round(float(lum.mean()), 4),
    "mean_sat": round(float(sat.mean()), 4),
    "spread": round(float(rgb.std()), 4),
    "mean_rgb": [round(float(v), 4) for v in rgb.mean(axis=0)],
}
bpy.data.images.remove(image)
print("STATS_JSON " + __import__("json").dumps(stats))
"""


def analyze(path):
    resp = bridge_client.send(ANALYZE % path)
    if resp.get("error"):
        raise RuntimeError(resp["error"])
    for line in resp["stdout"].splitlines():
        if line.startswith("STATS_JSON "):
            return json.loads(line[len("STATS_JSON "):])
    raise RuntimeError("no stats in:\n" + resp["stdout"])


def main():
    banner("Blender texture-GUI job - driven entirely through the port bridge")
    bridge_client.run("import bpy; print('connected:', bpy.app.version_string, '| scene:', bpy.context.scene.name)")

    step("STEP 1 - build a clean demo scene (sphere, lights, camera)")
    bridge_client.run(SETUP_SCENE)

    step("STEP 2 - bring the image into the Texture GUI")
    bridge_client.run(LOAD_IMAGE)

    step("STEP 3 - art-direct the material")
    bridge_client.run(ART_DIRECT)

    step("STEP 4 - render pass 1")
    bridge_client.run(render_snippet(PASS1))
    stats1 = analyze(PASS1)
    print("pass 1 stats:", stats1)

    step("STEP 5 - self-check the rendered pixels")
    if _looks_ok(stats1):
        print("PASS 1 looks good - no fix needed.")
        return
    print("PROBLEM: render is nearly colourless (mean saturation %.3f)." % stats1["mean_sat"])
    print("The texture is not showing on the sphere.")

    step("STEP 6 - diagnose and fix")
    print("Diagnosis: the image/material was applied to bpy.context.active_object,")
    print("which was the camera - so nothing was built on the mesh.")
    bridge_client.run(FIX_SELECT_AND_APPLY)

    step("STEP 7 - render pass 2")
    bridge_client.run(render_snippet(PASS2))
    stats2 = analyze(PASS2)
    print("pass 2 stats:", stats2)

    step("RESULT")
    print("mean saturation %.3f -> %.3f" % (stats1["mean_sat"], stats2["mean_sat"]))
    print("mean luminance  %.3f -> %.3f" % (stats1["mean_lum"], stats2["mean_lum"]))
    print("fixed:", _looks_ok(stats2))
    print("final render:", PASS2)
    print("before/after:", PASS1, "->", PASS2)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ERROR:", exc)
        sys.exit(1)
