bl_info = {
    "name": "Texture GUI",
    "author": "Irene Kao",
    "version": (1, 4, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Texture GUI",
    "description": "Assign and art-direct a texture on the selected object: drop an image, tune colour, UV, surface and shading controls.",
    "category": "Material",
}

import colorsys
import math

import bpy

MATERIAL_NAME = "TextureGUI"
HUE_GROUP_NAME = "TextureGUI_Hue"
GRAPH_VERSION = 3
IMAGE_EXTENSIONS = ".png;.jpg;.jpeg;.jpe;.bmp;.tga;.tif;.tiff;.exr;.hdr;.webp;.gif"


# ---------------------------------------------------------------------------
# Defaults / reset bookkeeping
# ---------------------------------------------------------------------------

DEFAULTS = {
    # colour
    "invert": False, "grayscale": 0.0, "hue": 0.0, "saturation": 1.0,
    "brightness": 1.0, "contrast": 1.0, "gamma": 1.0, "temperature": 0.0,
    "tint": 0.0, "posterize": 0, "amount": 1.0,
    # transform
    "scale": 1.0, "tiling_x": 1.0, "tiling_y": 1.0, "rotation": 0.0,
    "offset_x": 0.0, "offset_y": 0.0, "flip_x": False, "flip_y": False,
    # surface
    "relief": 0.5, "depth": 0.5, "relief_invert": False, "detail": 0.0,
    "detail_scale": 8.0, "roughness": 0.5, "metallic": 0.0, "specular": 0.5,
    "ior": 1.5, "coat": 0.0, "coat_roughness": 0.03, "sheen": 0.0,
    "sheen_roughness": 0.5, "anisotropic": 0.0, "subsurface": 0.0,
    "transmission": 0.0, "alpha": 1.0, "normal_strength": 1.0,
    # emission
    "emission": 0.0, "glow_color": (1.0, 1.0, 1.0, 1.0),
}

RESET_SECTIONS = {
    "COLOR": (
        "invert", "grayscale", "hue", "saturation", "brightness", "contrast",
        "gamma", "temperature", "tint", "posterize", "amount",
    ),
    "TRANSFORM": ("scale", "tiling_x", "tiling_y", "rotation", "offset_x",
                  "offset_y", "flip_x", "flip_y"),
    "SURFACE": (
        "relief", "depth", "relief_invert", "detail", "detail_scale", "roughness",
        "metallic", "specular", "ior", "coat", "coat_roughness", "sheen",
        "sheen_roughness", "anisotropic", "subsurface", "transmission", "alpha",
        "normal_strength", "emission", "glow_color",
    ),
}


# ---------------------------------------------------------------------------
# Surface presets
# ---------------------------------------------------------------------------

SURFACE_PRESETS = {
    "MATTE": {
        "label": "Matte", "roughness": 0.9, "metallic": 0.0, "specular": 0.25,
        "ior": 1.45, "coat": 0.0, "coat_roughness": 0.1, "sheen": 0.0,
        "sheen_roughness": 0.5, "anisotropic": 0.0, "subsurface": 0.0,
        "transmission": 0.0, "alpha": 1.0, "emission": 0.0,
    },
    "GLOSSY": {
        "label": "Glossy", "roughness": 0.15, "metallic": 0.0, "specular": 0.8,
        "ior": 1.5, "coat": 0.4, "coat_roughness": 0.05, "sheen": 0.0,
        "sheen_roughness": 0.5, "anisotropic": 0.0, "subsurface": 0.0,
        "transmission": 0.0, "alpha": 1.0, "emission": 0.0,
    },
    "PLASTIC": {
        "label": "Plastic", "roughness": 0.3, "metallic": 0.0, "specular": 0.6,
        "ior": 1.45, "coat": 0.0, "coat_roughness": 0.03, "sheen": 0.0,
        "sheen_roughness": 0.5, "anisotropic": 0.0, "subsurface": 0.0,
        "transmission": 0.0, "alpha": 1.0, "emission": 0.0,
    },
    "CERAMIC": {
        "label": "Ceramic", "roughness": 0.12, "metallic": 0.0, "specular": 0.7,
        "ior": 1.5, "coat": 0.6, "coat_roughness": 0.03, "sheen": 0.0,
        "sheen_roughness": 0.5, "anisotropic": 0.0, "subsurface": 0.0,
        "transmission": 0.0, "alpha": 1.0, "emission": 0.0,
    },
    "METAL": {
        "label": "Metal", "roughness": 0.25, "metallic": 1.0, "specular": 0.5,
        "ior": 1.5, "coat": 0.0, "coat_roughness": 0.03, "sheen": 0.0,
        "sheen_roughness": 0.5, "anisotropic": 0.0, "subsurface": 0.0,
        "transmission": 0.0, "alpha": 1.0, "emission": 0.0,
    },
    "BRUSHED": {
        "label": "Brushed", "roughness": 0.35, "metallic": 1.0, "specular": 0.5,
        "ior": 1.5, "coat": 0.0, "coat_roughness": 0.03, "sheen": 0.0,
        "sheen_roughness": 0.5, "anisotropic": 0.8, "subsurface": 0.0,
        "transmission": 0.0, "alpha": 1.0, "emission": 0.0,
    },
    "VELVET": {
        "label": "Velvet", "roughness": 0.85, "metallic": 0.0, "specular": 0.2,
        "ior": 1.45, "coat": 0.0, "coat_roughness": 0.03, "sheen": 1.0,
        "sheen_roughness": 0.3, "anisotropic": 0.0, "subsurface": 0.1,
        "transmission": 0.0, "alpha": 1.0, "emission": 0.0,
    },
    "GLASS": {
        "label": "Glass", "roughness": 0.05, "metallic": 0.0, "specular": 0.5,
        "ior": 1.45, "coat": 0.0, "coat_roughness": 0.03, "sheen": 0.0,
        "sheen_roughness": 0.5, "anisotropic": 0.0, "subsurface": 0.0,
        "transmission": 1.0, "alpha": 1.0, "emission": 0.0,
    },
    "GLOWING": {
        "label": "Glowing", "roughness": 0.6, "metallic": 0.0, "specular": 0.4,
        "ior": 1.45, "coat": 0.0, "coat_roughness": 0.03, "sheen": 0.0,
        "sheen_roughness": 0.5, "anisotropic": 0.0, "subsurface": 0.0,
        "transmission": 0.0, "alpha": 1.0, "emission": 1.5,
    },
}

PRESET_ITEMS = [(key, SURFACE_PRESETS[key]["label"], "") for key in SURFACE_PRESETS]


# ---------------------------------------------------------------------------
# Material helpers
# ---------------------------------------------------------------------------

def _get_material(obj):
    mat = bpy.data.materials.get(MATERIAL_NAME)
    if mat is None:
        mat = bpy.data.materials.new(MATERIAL_NAME)
    mat.use_nodes = True
    slots = obj.data.materials
    if mat.name not in [m.name for m in slots if m]:
        slots.append(mat)
    index = [m.name for m in slots].index(mat.name)
    obj.active_material_index = index
    if len(slots) > 1:
        obj.data.polygons.foreach_set("material_index", [index] * len(obj.data.polygons))
        obj.data.update()
    return mat


def _vmath(nt, name, op, a, b=None):
    n = nt.nodes.new("ShaderNodeVectorMath")
    n.name = name
    n.operation = op
    if isinstance(a, tuple):
        n.inputs[0].default_value = a
    else:
        nt.links.new(a, n.inputs[0])
    if b is not None:
        if isinstance(b, tuple):
            n.inputs[1].default_value = b
        else:
            nt.links.new(b, n.inputs[1])
    return n


def _mix(nt, name, blend="MIX"):
    n = nt.nodes.new("ShaderNodeMixRGB")
    n.name = name
    n.blend_type = blend
    return n


def _link_single(nt, to_socket, from_socket):
    """Point an input at exactly one source (removing any existing link)."""
    for link in list(to_socket.links):
        nt.links.remove(link)
    if from_socket is not None:
        nt.links.new(from_socket, to_socket)


def _posterize(nt, in_socket):
    """Vector-based colour posterize chain. Levels applied in _set_values."""
    mul = _vmath(nt, "TG_Post_mul", "MULTIPLY", in_socket, (8.0,) * 3)
    flr = _vmath(nt, "TG_Post_flr", "FLOOR", mul.outputs["Vector"])
    div = _vmath(nt, "TG_Post_div", "MULTIPLY", flr.outputs["Vector"], (1.0 / 8.0,) * 3)
    return mul, div


# ---------------------------------------------------------------------------
# Node graph
# ---------------------------------------------------------------------------

def _build(mat, s):
    nt = mat.node_tree
    nt.nodes.clear()
    L = nt.links.new

    coord = nt.nodes.new("ShaderNodeTexCoord")
    coord.name = "TG_Coord"
    coord.location = (-1700, 0)

    mapn = nt.nodes.new("ShaderNodeMapping")
    mapn.name = "TG_Map"
    mapn.location = (-1500, 0)

    image = nt.nodes.new("ShaderNodeTexImage")
    image.name = "TG_Image"
    image.location = (-1300, 0)

    invert = nt.nodes.new("ShaderNodeInvert")
    invert.name = "TG_Invert"
    invert.location = (-1080, 200)

    mono_bw = nt.nodes.new("ShaderNodeRGBToBW")
    mono_bw.name = "TG_Mono_BW"
    mono_bw.location = (-1080, -60)

    mono_mix = _mix(nt, "TG_Mono_Mix")
    mono_mix.location = (-880, 100)

    hsv = nt.nodes.new("ShaderNodeHueSaturation")
    hsv.name = "TG_HueSat"
    hsv.location = (-660, 100)

    gamma = nt.nodes.new("ShaderNodeGamma")
    gamma.name = "TG_Gamma"
    gamma.location = (-440, 100)

    bc = nt.nodes.new("ShaderNodeBrightContrast")
    bc.name = "TG_BC"
    bc.location = (-240, 100)

    tint = _mix(nt, "TG_Tint", blend="MULTIPLY")
    tint.location = (-40, 100)

    post_mul, post_div = _posterize(nt, tint.outputs["Color"])
    post_mul.location = (160, -160)
    post_div.location = (420, -160)

    post_mix = _mix(nt, "TG_Post_Mix")
    post_mix.location = (620, 60)

    amount = _mix(nt, "TG_Amount")
    amount.location = (820, 60)

    glow = _mix(nt, "TG_Glow", blend="MULTIPLY")
    glow.location = (1020, 260)

    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.name = "TG_Noise"
    noise.location = (820, -420)
    noise.inputs["Detail"].default_value = 6.0

    detail_mix = _mix(nt, "TG_Detail_Mix")
    detail_mix.location = (1020, -420)

    bump_bw = nt.nodes.new("ShaderNodeRGBToBW")
    bump_bw.name = "TG_Bump_BW"
    bump_bw.location = (1020, -220)

    bump = nt.nodes.new("ShaderNodeBump")
    bump.name = "TG_Bump"
    bump.location = (1240, -340)

    normal_img = nt.nodes.new("ShaderNodeTexImage")
    normal_img.name = "TG_Normal_Img"
    normal_img.location = (1240, -620)

    normal_flat = nt.nodes.new("ShaderNodeRGB")
    normal_flat.name = "TG_NormalFlat"
    normal_flat.location = (1240, -820)
    normal_flat.outputs["Color"].default_value = (0.5, 0.5, 1.0, 1.0)

    normal_map = nt.nodes.new("ShaderNodeNormalMap")
    normal_map.name = "TG_NormalMap"
    normal_map.location = (1450, -420)

    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.name = "TG_BSDF"
    bsdf.location = (1260, 40)

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.name = "TG_Out"
    out.location = (1560, 40)

    # vector path
    L(coord.outputs["UV"], mapn.inputs["Vector"])
    L(mapn.outputs["Vector"], image.inputs["Vector"])

    # colour path
    L(image.outputs["Color"], invert.inputs["Color"])
    L(invert.outputs["Color"], mono_bw.inputs["Color"])
    L(invert.outputs["Color"], mono_mix.inputs["Color1"])
    L(mono_bw.outputs["Val"], mono_mix.inputs["Color2"])
    L(mono_mix.outputs["Color"], hsv.inputs["Color"])
    L(hsv.outputs["Color"], gamma.inputs["Color"])
    L(gamma.outputs["Color"], bc.inputs["Color"])
    L(bc.outputs["Color"], tint.inputs["Color1"])
    L(tint.outputs["Color"], post_mul.inputs[0])
    L(post_div.outputs["Vector"], post_mix.inputs["Color2"])
    L(tint.outputs["Color"], post_mix.inputs["Color1"])
    L(image.outputs["Color"], amount.inputs["Color1"])
    L(post_mix.outputs["Color"], amount.inputs["Color2"])
    L(amount.outputs["Color"], bsdf.inputs["Base Color"])

    # glow tint
    L(amount.outputs["Color"], glow.inputs["Color1"])
    try:
        L(glow.outputs["Color"], bsdf.inputs["Emission Color"])
    except Exception:
        pass

    # surface / bump (texture luminance broken up by procedural detail)
    L(coord.outputs["Object"], noise.inputs["Vector"])
    L(image.outputs["Color"], bump_bw.inputs["Color"])
    L(bump_bw.outputs["Val"], detail_mix.inputs["Color1"])
    L(noise.outputs["Factor"], detail_mix.inputs["Color2"])
    L(detail_mix.outputs["Color"], bump.inputs["Height"])
    L(mapn.outputs["Vector"], normal_img.inputs["Vector"])
    L(normal_flat.outputs["Color"], normal_map.inputs["Color"])
    L(normal_map.outputs["Normal"], bump.inputs["Normal"])
    L(bump.outputs["Normal"], bsdf.inputs["Normal"])

    L(bsdf.outputs["BSDF"], out.inputs["Surface"])

    try:
        nt["tg_version"] = GRAPH_VERSION
    except Exception:
        pass
    _set_values(nt, s)


def _set_input(node, name, value):
    try:
        node.inputs[name].default_value = value
    except Exception:
        pass


def _set_values(nt, s):
    mapn = nt.nodes["TG_Map"]
    image = nt.nodes["TG_Image"]
    invert = nt.nodes["TG_Invert"]
    mono_mix = nt.nodes["TG_Mono_Mix"]
    hsv = nt.nodes["TG_HueSat"]
    gamma = nt.nodes["TG_Gamma"]
    bc = nt.nodes["TG_BC"]
    tint = nt.nodes["TG_Tint"]
    post_mul = nt.nodes["TG_Post_mul"]
    post_div = nt.nodes["TG_Post_div"]
    post_mix = nt.nodes["TG_Post_Mix"]
    amount = nt.nodes["TG_Amount"]
    glow = nt.nodes["TG_Glow"]
    noise = nt.nodes["TG_Noise"]
    detail_mix = nt.nodes["TG_Detail_Mix"]
    bump = nt.nodes["TG_Bump"]
    normal_img = nt.nodes["TG_Normal_Img"]
    normal_flat = nt.nodes["TG_NormalFlat"]
    normal_map = nt.nodes["TG_NormalMap"]
    bsdf = nt.nodes["TG_BSDF"]

    if s.image is not None:
        image.image = s.image

    # UV / mapping
    fx = -1.0 if s.flip_x else 1.0
    fy = -1.0 if s.flip_y else 1.0
    mapn.inputs["Location"].default_value = (s.offset_x, s.offset_y, 0.0)
    mapn.inputs["Rotation"].default_value = (0.0, 0.0, math.radians(s.rotation))
    scale = max(s.scale, 0.001)
    mapn.inputs["Scale"].default_value = (max(s.tiling_x, 0.001) * scale * fx,
                                          max(s.tiling_y, 0.001) * scale * fy, 1.0)

    # colour
    invert.inputs["Factor"].default_value = 1.0 if s.invert else 0.0
    mono_mix.inputs["Factor"].default_value = s.grayscale
    hsv.inputs["Hue"].default_value = 0.5 + s.hue * 0.5
    hsv.inputs["Saturation"].default_value = s.saturation
    hsv.inputs["Value"].default_value = s.brightness
    gamma.inputs["Gamma"].default_value = max(s.gamma, 0.01)
    bc.inputs["Brightness"].default_value = 0.0
    bc.inputs["Contrast"].default_value = s.contrast - 1.0

    tc = _tint_color(s.temperature, s.tint)
    tint.inputs["Factor"].default_value = 1.0
    tint.inputs["Color2"].default_value = tc

    levels = s.posterize
    on = levels >= 2
    lv = float(levels if on else 8)
    post_mul.inputs[1].default_value = (lv, lv, lv)
    post_div.inputs[1].default_value = (1.0 / lv,) * 3
    post_mix.inputs["Factor"].default_value = 1.0 if on else 0.0

    amount.inputs["Factor"].default_value = s.amount

    # emission / glow
    glow.inputs["Factor"].default_value = 1.0
    glow.inputs["Color2"].default_value = s.glow_color
    _set_input(bsdf, "Emission Strength", s.emission)

    # surface relief
    bump.invert = s.relief_invert
    bump.inputs["Strength"].default_value = s.relief
    bump.inputs["Distance"].default_value = 0.02 + 0.5 * s.depth
    detail_mix.inputs["Factor"].default_value = s.detail
    noise.inputs["Scale"].default_value = max(s.detail_scale, 0.1)

    # normal map (optional image combined with the bump relief)
    if s.normal_image is not None:
        normal_img.image = s.normal_image
        _link_single(nt, normal_map.inputs["Color"], normal_img.outputs["Color"])
    else:
        _link_single(nt, normal_map.inputs["Color"], normal_flat.outputs["Color"])
    normal_map.inputs["Strength"].default_value = s.normal_strength

    # shading
    _set_input(bsdf, "Roughness", s.roughness)
    _set_input(bsdf, "Metallic", s.metallic)
    _set_input(bsdf, "Specular IOR Level", s.specular)
    _set_input(bsdf, "IOR", s.ior)
    _set_input(bsdf, "Coat Weight", s.coat)
    _set_input(bsdf, "Coat Roughness", s.coat_roughness)
    _set_input(bsdf, "Sheen Weight", s.sheen)
    _set_input(bsdf, "Sheen Roughness", s.sheen_roughness)
    _set_input(bsdf, "Anisotropic", s.anisotropic)
    _set_input(bsdf, "Subsurface Weight", s.subsurface)
    _set_input(bsdf, "Transmission Weight", s.transmission)
    _set_input(bsdf, "Alpha", s.alpha)

    # blend method for transparency (EEVEE Next naming, guarded)
    mat = nt.id_data
    try:
        blended = s.alpha < 0.999 or s.transmission > 0.0
        mat.surface_render_method = "BLENDED" if blended else "DITHERED"
    except Exception:
        pass


def _tint_color(temperature, tint):
    r = 1.0 + 0.28 * temperature + 0.12 * tint
    g = 1.0 - 0.18 * tint
    b = 1.0 - 0.28 * temperature + 0.12 * tint
    clamp = lambda v: max(0.05, min(2.0, v))
    return (clamp(r), clamp(g), clamp(b), 1.0)


# ---------------------------------------------------------------------------
# Hue colour bar (display ramp)
# ---------------------------------------------------------------------------

def _hue_rgb(t):
    return colorsys.hsv_to_rgb(t % 1.0, 1.0, 1.0) + (1.0,)


def _fill_hue_ramp(cr):
    cr.interpolation = "LINEAR"
    stops = [0.0, 1 / 6.0, 2 / 6.0, 3 / 6.0, 4 / 6.0, 5 / 6.0, 1.0]
    while len(cr.elements) > 1:
        cr.elements.remove(cr.elements[-1])
    cr.elements[0].position = 0.0
    cr.elements[0].color = _hue_rgb(0.0)
    for p in stops[1:]:
        cr.elements.new(p).color = _hue_rgb(p)


def _hue_group():
    """Create/reuse a node group holding a single hue-spectrum ColourRamp.

    Must only be called outside panel draw (Blender forbids data edits during
    draw), e.g. from a timer or a property callback. Self-heals if the group
    was polluted with extra nodes.
    """
    try:
        ng = bpy.data.node_groups.get(HUE_GROUP_NAME)
        if ng is None:
            ng = bpy.data.node_groups.new(HUE_GROUP_NAME, "ShaderNodeTree")
        node = ng.nodes.get("Hue")
        if node is None or len(ng.nodes) != 1:
            for n in list(ng.nodes):
                ng.nodes.remove(n)
            node = ng.nodes.new("ShaderNodeValToRGB")
            node.name = "Hue"
            _fill_hue_ramp(node.color_ramp)
        return ng
    except Exception:
        return None


def _get_hue_group_readonly():
    try:
        ng = bpy.data.node_groups.get(HUE_GROUP_NAME)
        if ng is not None and ng.nodes.get("Hue"):
            return ng
    except Exception:
        pass
    return None


def _schedule_hue_group():
    """Create the ramp shortly after registration, on the main loop."""
    def _make():
        _hue_group()
        return None
    try:
        bpy.app.timers.register(_make, first_interval=0.3)
    except Exception:
        pass


def _remove_hue_group():
    try:
        ng = bpy.data.node_groups.get(HUE_GROUP_NAME)
        if ng is not None:
            bpy.data.node_groups.remove(ng)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------

def _show_material_preview():
    wm = getattr(bpy.context, "window_manager", None)
    if wm is None:
        return
    for win in wm.windows:
        screen = getattr(win, "screen", None)
        if screen is None:
            continue
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            for space in area.spaces:
                if getattr(space, "type", None) != "VIEW_3D":
                    continue
                shading = getattr(space, "shading", None)
                if shading is not None and shading.type == "SOLID":
                    shading.type = "MATERIAL"


def _apply(context, rebuild):
    obj = context.active_object
    if obj is None or obj.type != "MESH":
        return
    s = context.scene.texture_gui
    mat = _get_material(obj)
    nt = mat.node_tree
    stale = nt.nodes.get("TG_BSDF") is None or nt.get("tg_version") != GRAPH_VERSION
    if rebuild or stale:
        _build(mat, s)
    else:
        _set_values(nt, s)
    _hue_group()
    _show_material_preview()


# ---------------------------------------------------------------------------
# Property callbacks
# ---------------------------------------------------------------------------

def _on_update(self, context):
    try:
        _apply(context, rebuild=False)
    except Exception as exc:
        print("TextureGUI: %s" % exc)


def _on_image(self, context):
    try:
        _apply(context, rebuild=True)
    except Exception as exc:
        print("TextureGUI: %s" % exc)


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

class TextureGUISettings(bpy.types.PropertyGroup):
    image: bpy.props.PointerProperty(
        name="Image", type=bpy.types.Image, update=_on_image,
        description="Drop or pick an image to texture the selected object",
    )

    invert: bpy.props.BoolProperty(
        name="Invert", default=False, update=_on_update,
        description="Invert the image colours",
    )
    grayscale: bpy.props.FloatProperty(
        name="Desaturate", min=0.0, max=1.0, default=0.0, subtype="FACTOR", update=_on_update,
        description="Mix toward a black-and-white version of the image",
    )
    hue: bpy.props.FloatProperty(
        name="Hue", min=0.0, max=1.0, default=0.0, subtype="FACTOR", update=_on_update,
        description="Rotate colours around the hue wheel",
    )
    saturation: bpy.props.FloatProperty(
        name="Saturation", min=0.0, max=2.0, default=1.0, subtype="FACTOR", update=_on_update,
    )
    brightness: bpy.props.FloatProperty(
        name="Brightness", min=0.0, max=2.0, default=1.0, subtype="FACTOR", update=_on_update,
    )
    contrast: bpy.props.FloatProperty(
        name="Contrast", min=0.0, max=2.0, default=1.0, subtype="FACTOR", update=_on_update,
    )
    gamma: bpy.props.FloatProperty(
        name="Gamma / Midtones", min=0.2, max=4.0, default=1.0, update=_on_update,
        description="Brighten or darken the midtones",
    )
    temperature: bpy.props.FloatProperty(
        name="Temperature", min=-1.0, max=1.0, default=0.0, subtype="FACTOR", update=_on_update,
        description="Warm (+) / cool (-) tint",
    )
    tint: bpy.props.FloatProperty(
        name="Tint", min=-1.0, max=1.0, default=0.0, subtype="FACTOR", update=_on_update,
        description="Magenta (+) / green (-) tint",
    )
    posterize: bpy.props.IntProperty(
        name="Posterize", min=0, max=16, default=0, update=_on_update,
        description="Number of colour bands (0 = off)",
    )
    amount: bpy.props.FloatProperty(
        name="Amount", min=0.0, max=1.0, default=1.0, subtype="FACTOR", update=_on_update,
        description="Blend between the original image and the edited result",
    )

    scale: bpy.props.FloatProperty(
        name="Scale", min=0.05, max=16.0, default=1.0, update=_on_update,
        description="Overall image scale",
    )
    tiling_x: bpy.props.FloatProperty(
        name="Tiling X", min=0.01, max=32.0, default=1.0, update=_on_update,
        description="Repeat the image horizontally",
    )
    tiling_y: bpy.props.FloatProperty(
        name="Tiling Y", min=0.01, max=32.0, default=1.0, update=_on_update,
        description="Repeat the image vertically",
    )
    rotation: bpy.props.FloatProperty(
        name="Rotation", min=-180.0, max=180.0, default=0.0, update=_on_update,
    )
    offset_x: bpy.props.FloatProperty(
        name="Offset X", min=-1.0, max=1.0, default=0.0, subtype="FACTOR", update=_on_update,
    )
    offset_y: bpy.props.FloatProperty(
        name="Offset Y", min=-1.0, max=1.0, default=0.0, subtype="FACTOR", update=_on_update,
    )
    flip_x: bpy.props.BoolProperty(name="Flip X", default=False, update=_on_update)
    flip_y: bpy.props.BoolProperty(name="Flip Y", default=False, update=_on_update)

    relief: bpy.props.FloatProperty(
        name="Relief", min=0.0, max=1.0, default=0.5, subtype="FACTOR", update=_on_update,
        description="Bump strength: how raised the texture feels",
    )
    depth: bpy.props.FloatProperty(
        name="Depth", min=0.0, max=2.0, default=0.5, subtype="FACTOR", update=_on_update,
        description="Bump distance / height of the relief",
    )
    relief_invert: bpy.props.BoolProperty(
        name="Invert Relief", default=False, update=_on_update,
        description="Treat dark areas as raised instead of bright",
    )
    detail: bpy.props.FloatProperty(
        name="Detail", min=0.0, max=1.0, default=0.0, subtype="FACTOR", update=_on_update,
        description="Blend procedural noise into the relief for organic texture",
    )
    detail_scale: bpy.props.FloatProperty(
        name="Detail Scale", min=0.5, max=40.0, default=8.0, update=_on_update,
        description="Size of the procedural detail",
    )
    roughness: bpy.props.FloatProperty(
        name="Roughness", min=0.0, max=1.0, default=0.5, subtype="FACTOR", update=_on_update,
    )
    metallic: bpy.props.FloatProperty(
        name="Metallic", min=0.0, max=1.0, default=0.0, subtype="FACTOR", update=_on_update,
    )
    specular: bpy.props.FloatProperty(
        name="Specular", min=0.0, max=1.0, default=0.5, subtype="FACTOR", update=_on_update,
        description="Strength of the specular reflection",
    )
    ior: bpy.props.FloatProperty(
        name="IOR", min=1.0, max=3.0, default=1.5, update=_on_update,
        description="Index of refraction",
    )
    coat: bpy.props.FloatProperty(
        name="Coat", min=0.0, max=1.0, default=0.0, subtype="FACTOR", update=_on_update,
        description="Clear-coat layer weight",
    )
    coat_roughness: bpy.props.FloatProperty(
        name="Coat Roughness", min=0.0, max=1.0, default=0.03, subtype="FACTOR", update=_on_update,
    )
    sheen: bpy.props.FloatProperty(
        name="Sheen", min=0.0, max=1.0, default=0.0, subtype="FACTOR", update=_on_update,
        description="Fabric / velvet sheen weight",
    )
    sheen_roughness: bpy.props.FloatProperty(
        name="Sheen Roughness", min=0.0, max=1.0, default=0.5, subtype="FACTOR", update=_on_update,
    )
    anisotropic: bpy.props.FloatProperty(
        name="Anisotropic", min=-1.0, max=1.0, default=0.0, subtype="FACTOR", update=_on_update,
        description="Stretch highlights for brushed / spun surfaces",
    )
    subsurface: bpy.props.FloatProperty(
        name="Subsurface", min=0.0, max=1.0, default=0.0, subtype="FACTOR", update=_on_update,
        description="Light scattering beneath the surface (skin, wax, marble)",
    )
    transmission: bpy.props.FloatProperty(
        name="Transmission", min=0.0, max=1.0, default=0.0, subtype="FACTOR", update=_on_update,
        description="Glass / translucent transmission weight",
    )
    alpha: bpy.props.FloatProperty(
        name="Alpha", min=0.0, max=1.0, default=1.0, subtype="FACTOR", update=_on_update,
        description="Overall opacity",
    )
    normal_image: bpy.props.PointerProperty(
        name="Normal Map", type=bpy.types.Image, update=_on_update,
        description="Optional tangent-space normal map combined with the relief",
    )
    normal_strength: bpy.props.FloatProperty(
        name="Normal Strength", min=0.0, max=2.0, default=1.0, subtype="FACTOR", update=_on_update,
        description="Strength of the normal map",
    )
    emission: bpy.props.FloatProperty(
        name="Glow", min=0.0, max=5.0, default=0.0, update=_on_update,
        description="Emission strength",
    )
    glow_color: bpy.props.FloatVectorProperty(
        name="Glow Tint", subtype="COLOR", size=4, min=0.0, max=1.0,
        default=(1.0, 1.0, 1.0, 1.0), update=_on_update,
        description="Colour applied to the emission",
    )


# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------

class TEXTUREGUI_OT_apply(bpy.types.Operator):
    bl_idname = "texturegui.apply"
    bl_label = "Apply to Selected"
    bl_description = "Build/refresh the texture material on the active object"

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != "MESH":
            self.report({"WARNING"}, "Select a mesh object first")
            return {"CANCELLED"}
        _apply(context, rebuild=True)
        return {"FINISHED"}


class TEXTUREGUI_OT_reset_section(bpy.types.Operator):
    bl_idname = "texturegui.reset_section"
    bl_label = "Reset Section"
    bl_description = "Reset a group of controls to their defaults"

    section: bpy.props.EnumProperty(
        items=(
            ("COLOR", "Colour", ""),
            ("TRANSFORM", "Transform", ""),
            ("SURFACE", "Surface", ""),
            ("ALL", "Everything", ""),
        ),
        default="ALL",
    )

    def execute(self, context):
        s = context.scene.texture_gui
        if self.section == "ALL":
            keys = DEFAULTS.keys()
        else:
            keys = RESET_SECTIONS.get(self.section, ())
        for key in keys:
            setattr(s, key, DEFAULTS[key])
        return {"FINISHED"}


class TEXTUREGUI_OT_rotate(bpy.types.Operator):
    bl_idname = "texturegui.rotate"
    bl_label = "Rotate Image"
    bl_description = "Nudge the image rotation by a fixed step"

    angle: bpy.props.FloatProperty(default=90.0)

    def execute(self, context):
        s = context.scene.texture_gui
        s.rotation = ((s.rotation + self.angle + 180.0) % 360.0) - 180.0
        return {"FINISHED"}


class TEXTUREGUI_OT_surface_preset(bpy.types.Operator):
    bl_idname = "texturegui.surface_preset"
    bl_label = "Surface Preset"
    bl_description = "Apply a ready-made surface look"

    preset: bpy.props.EnumProperty(items=PRESET_ITEMS)

    def execute(self, context):
        s = context.scene.texture_gui
        values = SURFACE_PRESETS.get(self.preset)
        if not values:
            return {"CANCELLED"}
        for key, value in values.items():
            if key == "label":
                continue
            setattr(s, key, value)
        return {"FINISHED"}


class TEXTUREGUI_MT_reset(bpy.types.Menu):
    bl_idname = "TEXTUREGUI_MT_reset"
    bl_label = "Reset"

    def draw(self, context):
        for key, label in (("COLOR", "Colour"), ("TRANSFORM", "Transform"),
                           ("SURFACE", "Surface"), ("ALL", "Everything")):
            op = self.layout.operator("texturegui.reset_section", text=label)
            op.section = key


class TEXTUREGUI_OT_drop_image(bpy.types.Operator):
    bl_idname = "texturegui.drop_image"
    bl_label = "Texture GUI: Drop Image"
    bl_description = "Load a dragged-and-dropped image file as the texture"
    bl_options = {"REGISTER", "UNDO"}

    filepath: bpy.props.StringProperty(
        name="File Path", subtype="FILE_PATH", options={"SKIP_SAVE"},
    )

    def execute(self, context):
        path = self.filepath
        if not path:
            return {"CANCELLED"}
        try:
            img = bpy.data.images.load(path, check_existing=True)
        except Exception as exc:
            self.report({"ERROR"}, "Could not load image: %s" % exc)
            return {"CANCELLED"}
        context.scene.texture_gui.image = img
        self.report({"INFO"}, "Loaded %s" % img.name)
        return {"FINISHED"}


class TEXTUREGUI_FH_image_drop(bpy.types.FileHandler):
    bl_idname = "TEXTUREGUI_FH_image_drop"
    bl_label = "Texture GUI Image"
    bl_import_operator = "texturegui.drop_image"
    bl_file_extensions = IMAGE_EXTENSIONS

    @classmethod
    def poll_drop(cls, context):
        area = getattr(context, "area", None)
        return area is not None and area.type in {"VIEW_3D", "IMAGE_EDITOR"}


class TEXTUREGUI_OT_open(bpy.types.Operator):
    bl_idname = "texturegui.open"
    bl_label = "Texture GUI"
    bl_description = "Open the Texture GUI in a floating window"

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=420)

    def draw(self, context):
        _draw_settings(self.layout, context)

    def execute(self, context):
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# UI sections
# ---------------------------------------------------------------------------

def _ui_image(layout, s):
    layout.template_ID(s, "image", open="image.open")
    if s.image is not None:
        try:
            w, h = s.image.size
            layout.label(text="%d x %d px" % (w, h), icon="INFO")
        except Exception:
            pass
    layout.label(text="Drag & drop an image into the viewport", icon="FILE_IMAGE")


def _ui_color(layout, s):
    col = layout.column()
    row = col.row(align=True)
    row.prop(s, "invert", toggle=True)
    row.prop(s, "grayscale")
    col.prop(s, "amount")
    col.separator()
    ng = _get_hue_group_readonly()
    if ng is not None:
        col.template_color_ramp(ng.nodes["Hue"], "color_ramp", expand=True)
    col.prop(s, "hue", slider=True)
    col.prop(s, "saturation")
    col.prop(s, "brightness")
    col.prop(s, "contrast")
    col.prop(s, "gamma")
    row = col.row(align=True)
    row.prop(s, "temperature")
    row.prop(s, "tint")
    col.prop(s, "posterize")


def _ui_transform(layout, s):
    col = layout.column()
    col.prop(s, "scale")
    row = col.row(align=True)
    row.prop(s, "tiling_x")
    row.prop(s, "tiling_y")
    col.separator()
    col.prop(s, "rotation")
    row = col.row(align=True)
    back = row.operator("texturegui.rotate", text="", icon="LOOP_BACK")
    back.angle = -90.0
    fwd = row.operator("texturegui.rotate", text="", icon="LOOP_FORWARDS")
    fwd.angle = 90.0
    row = col.row(align=True)
    row.prop(s, "offset_x")
    row.prop(s, "offset_y")
    row = col.row(align=True)
    row.prop(s, "flip_x", toggle=True)
    row.prop(s, "flip_y", toggle=True)


def _ui_surface(layout, s):
    col = layout.column()
    col.prop(s, "relief", slider=True)
    col.prop(s, "depth", slider=True)
    row = col.row(align=True)
    row.prop(s, "relief_invert", toggle=True)
    row.prop(s, "detail", slider=True)
    col.prop(s, "detail_scale")
    col.separator()
    col.prop(s, "roughness", slider=True)
    col.prop(s, "metallic", slider=True)
    row = col.row(align=True)
    row.prop(s, "specular", slider=True)
    row.prop(s, "ior", slider=True)
    col.separator()
    col.prop(s, "normal_image", text="Normal")
    col.prop(s, "normal_strength", slider=True)


def _ui_surface_advanced(layout, s):
    col = layout.column()
    col.prop(s, "coat", slider=True)
    col.prop(s, "coat_roughness", slider=True)
    col.prop(s, "sheen", slider=True)
    col.prop(s, "sheen_roughness", slider=True)
    col.separator()
    col.prop(s, "anisotropic", slider=True)
    col.prop(s, "subsurface", slider=True)
    col.prop(s, "transmission", slider=True)
    col.prop(s, "alpha", slider=True)


def _ui_emission(layout, s):
    col = layout.column()
    col.prop(s, "emission", slider=True)
    row = col.row(align=True)
    row.prop(s, "glow_color", text="")


def _ui_presets(layout, _s):
    grid = layout.grid_flow(columns=3, even_columns=True, align=True)
    for key in SURFACE_PRESETS:
        op = grid.operator("texturegui.surface_preset", text=SURFACE_PRESETS[key]["label"])
        op.preset = key


def _ui_actions(layout, _s):
    row = layout.row(align=True)
    row.operator("texturegui.apply", icon="PLAY")
    row.menu("TEXTUREGUI_MT_reset", icon="LOOP_BACK")
    row.operator("texturegui.open", text="", icon="WINDOW")


def _draw_settings(layout, context):
    s = context.scene.texture_gui
    layout.use_property_split = True
    layout.use_property_decorate = False

    box = layout.box()
    box.label(text="Image", icon="IMAGE_DATA")
    _ui_image(box, s)

    box = layout.box()
    box.label(text="Colour", icon="COLOR")
    _ui_color(box, s)

    box = layout.box()
    box.label(text="Transform", icon="UV")
    _ui_transform(box, s)

    box = layout.box()
    box.label(text="Surface", icon="MATERIAL")
    _ui_surface(box, s)

    box = layout.box()
    box.label(text="Surface — Advanced", icon="SHADERFX")
    _ui_surface_advanced(box, s)

    box = layout.box()
    box.label(text="Emission", icon="LIGHT")
    _ui_emission(box, s)

    box = layout.box()
    box.label(text="Presets", icon="PRESET")
    _ui_presets(box, s)

    layout.separator()
    _ui_actions(layout, s)


# ---------------------------------------------------------------------------
# Panels (sidebar, collapsible sections)
# ---------------------------------------------------------------------------

class TEXTUREGUI_PT_panel(bpy.types.Panel):
    bl_label = "Texture GUI"
    bl_idname = "TEXTUREGUI_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Texture GUI"

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        s = context.scene.texture_gui
        if obj is None or obj.type != "MESH":
            layout.label(text="Select a mesh object", icon="INFO")
        else:
            layout.label(text="Object: %s" % obj.name, icon="OBJECT_DATAMODE")
        if s.image is not None:
            try:
                w, h = s.image.size
                layout.label(text="%s  (%d x %d)" % (s.image.name, w, h), icon="IMAGE_DATA")
            except Exception:
                layout.label(text=s.image.name, icon="IMAGE_DATA")
        _ui_actions(layout, s)


def _make_section(name, label, icon, order, draw_fn):
    def draw(self, context):
        draw_fn(self.layout, context.scene.texture_gui)

    return type("TEXTUREGUI_PT_%s" % name, (bpy.types.Panel,), {
        "bl_label": label,
        "bl_idname": "TEXTUREGUI_PT_%s" % name,
        "bl_parent_id": "TEXTUREGUI_PT_panel",
        "bl_space_type": "VIEW_3D",
        "bl_region_type": "UI",
        "bl_options": {"DEFAULT_CLOSED"},
        "bl_order": order,
        "draw": draw,
    })


TEXTUREGUI_PT_image = _make_section("image", "Image", "IMAGE_DATA", 0, _ui_image)
TEXTUREGUI_PT_colour = _make_section("colour", "Colour", "COLOR", 1, _ui_color)
TEXTUREGUI_PT_transform = _make_section("transform", "Transform", "UV", 2, _ui_transform)
TEXTUREGUI_PT_surface = _make_section("surface", "Surface", "MATERIAL", 3, _ui_surface)
TEXTUREGUI_PT_advanced = _make_section("advanced", "Surface — Advanced", "SHADERFX", 4, _ui_surface_advanced)
TEXTUREGUI_PT_emission = _make_section("emission", "Emission", "LIGHT", 5, _ui_emission)
TEXTUREGUI_PT_presets = _make_section("presets", "Presets", "PRESET", 6, _ui_presets)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

_classes = (
    TextureGUISettings,
    TEXTUREGUI_OT_apply,
    TEXTUREGUI_OT_reset_section,
    TEXTUREGUI_OT_rotate,
    TEXTUREGUI_OT_surface_preset,
    TEXTUREGUI_OT_drop_image,
    TEXTUREGUI_OT_open,
    TEXTUREGUI_MT_reset,
    TEXTUREGUI_PT_panel,
    TEXTUREGUI_PT_image,
    TEXTUREGUI_PT_colour,
    TEXTUREGUI_PT_transform,
    TEXTUREGUI_PT_surface,
    TEXTUREGUI_PT_advanced,
    TEXTUREGUI_PT_emission,
    TEXTUREGUI_PT_presets,
    TEXTUREGUI_FH_image_drop,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.texture_gui = bpy.props.PointerProperty(type=TextureGUISettings)
    _schedule_hue_group()


def unregister():
    _remove_hue_group()
    del bpy.types.Scene.texture_gui
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
