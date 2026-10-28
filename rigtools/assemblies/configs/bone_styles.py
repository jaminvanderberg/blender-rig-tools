import math

import bpy

from rigtools.utils.widget import widget_fingerprint

CUSTOM_SHAPE_PROPS = (
    "custom_shape_scale_xyz",
    "custom_shape_translation",
    "custom_shape_rotation_euler",
    "custom_shape_wire_width",
    "use_custom_shape_bone_size",
    "show_wire",
)

STYLE_FIELDS = {
    "custom_shape_scale_xyz": "scale",
    "custom_shape_translation": "translate",
    "custom_shape_rotation_euler": "rotate",
    "custom_shape_wire_width": "wire_width",
}

def _blender_default(prop):
    rna = bpy.types.PoseBone.bl_rna.properties[prop]
    return tuple(rna.default_array) if rna.is_array else rna.default

def _same(a, b):
    if isinstance(a, tuple):
        return all(math.isclose(x, y, abs_tol=1e-4) for x, y in zip(a, b))
    if isinstance(a, float):
        return math.isclose(a, b, abs_tol=1e-4)
    return a == b

def style_diff(pose_bone, bone_ref) -> dict:
    """Returns difference from live bone vs stored style, as dict: {property: value}"""
    style = bone_ref.get_style()
    diff = {}

    for prop in CUSTOM_SHAPE_PROPS:
        field = STYLE_FIELDS.get(prop)
        expected = getattr(style, field) if field else None
        if expected is None:
            expected = _blender_default(prop)
        live = getattr(pose_bone, prop)
        if isinstance(expected, (tuple, list)):
            live, expected = tuple(live), tuple(expected)
        if not _same(live, expected):
            diff[prop] = live

    transform = pose_bone.custom_shape_transform
    transform_name = transform.name if transform else None
    if transform_name != style.transform_bone:
        diff["custom_shape_transform"] = transform_name

    shape = pose_bone.custom_shape
    if style.widget in (None, 'NONE'):
        shape_modified = shape is not None
    else:
        shape_modified = bool(bone_ref.widget_fingerprint) and widget_fingerprint(shape) != bone_ref.widget_fingerprint

    if shape_modified:
        diff["custom_shape"] = shape.name if shape else None

    color = pose_bone.color
    if style.color is None or bone_ref.palette:
        if color.palette != (bone_ref.palette or 'DEFAULT'):
            diff["color"] = {"palette": color.palette}
            if color.palette == 'CUSTOM':
                diff["color"].update({
                    "normal": tuple(color.custom.normal),
                    "select": tuple(color.custom.select),
                    "active": tuple(color.custom.active)
                })

    return diff
