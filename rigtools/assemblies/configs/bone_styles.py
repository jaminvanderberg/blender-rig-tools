from dataclasses import dataclass
import math

import bpy

from rigtools.utils.widget import STANDARD_WIDGET_KEY, get_standard_widget, is_standard_widget, standard_widget_name

CUSTOM_SHAPE_PROPS = {
	"custom_shape_scale_xyz": (1.0, 1.0, 1.0),
	"custom_shape_translation": (0.0, 0.0, 0.0),
	"custom_shape_rotation_euler": (0.0, 0.0, 0.0),
	"custom_shape_wire_width": 1.0,
	"use_custom_shape_bone_size": True,
	"show_wire": False,
}

BONE_PROPS = { "show_wire" }

STYLE_FIELDS = {
	"custom_shape_scale_xyz": "scale",
	"custom_shape_translation": "translate",
	"custom_shape_rotation_euler": "rotate",
	"custom_shape_wire_width": "wire_width",
}

def _get_prop(pose_bone, prop):
	bone = pose_bone.bone if prop in BONE_PROPS else pose_bone
	return getattr(bone, prop)

def _same(a, b):
	if isinstance(a, tuple):
		return all(math.isclose(x, y, abs_tol=1e-4) for x, y in zip(a, b))
	if isinstance(a, float):
		return math.isclose(a, b, abs_tol=1e-4)
	return a == b

@dataclass
class BoneStyleDiff:
	"""Difference between live bone and stored style"""
	bone_name: str
	diff: dict

	def add(self, prop, value):
		self.diff[prop] = value

	def get(self, prop, default=None):
		return self.diff.get(prop, default)

	def __bool__(self):
		return bool(self.diff)
	
	def apply(self, pose_bone):
		for prop, value in self.diff.items():
			if prop == "color":
				color = pose_bone.color
				color.palette = value.get("palette", color.palette)
				if color.palette == 'CUSTOM':
					color.custom.normal = value.get("normal", color.custom.normal)
					color.custom.select = value.get("select", color.custom.select)
					color.custom.active = value.get("active", color.custom.active)
			elif prop == "custom_shape":
				shape = bpy.data.objects.get(value) if value else None
				if shape or not value:
					pose_bone.custom_shape = shape
			elif prop == "custom_shape_transform":
				transform_name = value
				transform_bone = pose_bone.id_data.pose.bones.get(transform_name) if transform_name else None
				pose_bone.custom_shape_transform = transform_bone
			else:
				bone = pose_bone.bone if prop in BONE_PROPS else pose_bone
				setattr(bone, prop, value)

def style_defaults(context, bone_ref) -> dict:
	"""Each kept setting as the assembly built it: {property: default}.
	custom_shape is the shared widget's name, since looking the widget up could create it,
	and this runs while drawing. color is left out when the stored palette is unknown."""
	style = bone_ref.get_style()
	defaults = {}

	for prop, default in CUSTOM_SHAPE_PROPS.items():
		field = STYLE_FIELDS.get(prop)
		value = getattr(style, field) if field else None
		defaults[prop] = default if value is None else value

	defaults["custom_shape_transform"] = style.transform_bone

	if style.widget in (None, 'NONE'):
		defaults["custom_shape"] = None
	else:
		defaults["custom_shape"] = standard_widget_name(context, style.widget, style.widget_class)

	if style.color is None or bone_ref.palette:
		defaults["color"] = bone_ref.palette or 'DEFAULT'

	return defaults

def style_diff(context, pose_bone, bone_ref) -> dict:
	"""Returns difference from live bone vs stored style, as BoneStyleDiff"""
	defaults = style_defaults(context, bone_ref)
	diff = BoneStyleDiff(bone_name=pose_bone.name, diff={})

	for prop in CUSTOM_SHAPE_PROPS:
		live, expected = _get_prop(pose_bone, prop), defaults[prop]
		if isinstance(expected, (tuple, list)):
			live, expected = tuple(live), tuple(expected)
		if not _same(live, expected):
			diff.add(prop, live)

	transform = pose_bone.custom_shape_transform
	transform_name = transform.name if transform else None
	if transform_name != defaults["custom_shape_transform"]:
		diff.add("custom_shape_transform", transform_name)

	shape = pose_bone.custom_shape
	widget_name = defaults["custom_shape"]
	if widget_name is None:
		shape_modified = shape is not None
	else:
		# Anything but the shared widget for this style is a hand edit
		shape_modified = not is_standard_widget(shape) or shape[STANDARD_WIDGET_KEY] != widget_name

	if shape_modified:
		diff.add("custom_shape", shape.name if shape else None)

	color = pose_bone.color
	if "color" in defaults:
		if color.palette != defaults["color"]:
			value = {"palette": color.palette}
			if color.palette == 'CUSTOM':
				value.update({
					"normal": tuple(color.custom.normal),
					"select": tuple(color.custom.select),
					"active": tuple(color.custom.active)
				})
			diff.add("color", value)

	return diff

def reset_style(context, pose_bone, bone_ref, props):
	"""Set each of these properties back to the way the assembly built it"""
	defaults = style_defaults(context, bone_ref)
	for prop in props:
		if prop not in defaults:
			continue
		value = defaults[prop]
		if prop == "custom_shape":
			style = bone_ref.get_style()
			pose_bone.custom_shape = get_standard_widget(context, style.widget, style.widget_class) if value else None
		elif prop == "custom_shape_transform":
			pose_bone.custom_shape_transform = pose_bone.id_data.pose.bones.get(value) if value else None
		elif prop == "color":
			pose_bone.color.palette = value
		else:
			bone = pose_bone.bone if prop in BONE_PROPS else pose_bone
			setattr(bone, prop, value)


class BoneStyleConfig:
	id = "bone_styles"
	name = "Bone Styles"
	description = "Keeps hand-edited bone styles across reconfigure."

	@staticmethod
	def present(assembly) -> bool:
		return any(ref.style_json for ref in assembly.mechanism_bones)

	@staticmethod
	def snapshot(context, assembly) -> dict:
		pose_bones = context.object.pose.bones
		snap = {}
		for bone_ref in assembly.mechanism_bones:
			pose_bone = pose_bones.get(bone_ref.name)
			if not pose_bone:
				continue
			diff = style_diff(context, pose_bone, bone_ref)
			if diff:
				snap[bone_ref.name] = diff
		return snap

	@staticmethod
	def draw(layout, assembly, context):
		pass
