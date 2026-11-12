import bpy
from bpy.props import EnumProperty, StringProperty
from rigtools.panels.shape_keys.shape_key_utils import find_driver

CURVE_PRESETS = {
	'EASE_IN': ('QUAD', 'EASE_IN'),
	'EASE_OUT': ('QUAD', 'EASE_OUT'),
	'EASE_IN_OUT': ('SINE', 'EASE_IN_OUT'),
}

CURVE_PRESET_ITEMS = (
	('LINEAR', "Linear", "Simple linear interpolation"),
	('EASE_IN', "Ease In", "Starts slow, and picks up speed"),
	('EASE_OUT', "Ease Out", "Starts fast, then slows down"),
	('EASE_IN_OUT', "Ease In-Out", "Slower at both extremes, faster in the middle"),
)

def _is_at(keyframe, x, y, tolerance=1e-4):
	return abs(keyframe.co.x - x) < tolerance and abs(keyframe.co.y - y) < tolerance

def match_curve_preset(fcurve):
	"""Evaluate an fcurve to see if it matches one of the presets, returns 'CUSTOM' if not."""
	keyframes = fcurve.keyframe_points
	if len(keyframes) == 0:
		return 'LINEAR'
	if (len(keyframes) == 2 and fcurve.extrapolation == 'LINEAR'
			and _is_at(keyframes[0], 0.0, 0.0) and _is_at(keyframes[1], 1.0, 1.0)):

		first = (keyframes[0].interpolation, keyframes[0].easing)
		for name, settings in CURVE_PRESETS.items():
			if first == settings:
				return name            
	return 'CUSTOM'

def apply_curve_preset(fcurve, preset):
	if preset == 'CUSTOM':
		return

	fcurve.keyframe_points.clear()
	fcurve.update()
	if preset == 'LINEAR':
		return

	fcurve.keyframe_points.insert(0.0, 0.0)
	fcurve.keyframe_points.insert(1.0, 1.0)
	for keyframe in fcurve.keyframe_points:
		keyframe.interpolation, keyframe.easing = CURVE_PRESETS[preset]
	fcurve.extrapolation = 'LINEAR'
	fcurve.update()

class RIG_OT_set_key_curve(bpy.types.Operator):
	bl_idname = "rig.set_key_curve"
	bl_label = "Set Key Curve"
	bl_description = "Reshape how this shape key follows its bones between 0 and 1"
	bl_options = {'REGISTER', 'UNDO'}

	object_name: StringProperty(options={'HIDDEN'})
	shape_key_name: StringProperty(options={'HIDDEN'})
	preset: EnumProperty(items=CURVE_PRESET_ITEMS)

	@classmethod
	def description(cls, context, properties):
		# Each menu entry's tooltip is its preset's description
		return next(item[2] for item in CURVE_PRESET_ITEMS if item[0] == properties.preset)

	def execute(self, context):
		mesh = bpy.data.objects.get(self.object_name)
		if not mesh:
			self.report({'ERROR'}, f"Object not found: '{self.object_name}'")
			return {'CANCELLED'}
		if mesh.type != 'MESH':
			self.report({'ERROR'}, f"Object '{self.object_name}' is not a mesh object")
			return {'CANCELLED'}

		key = mesh.data.shape_keys
		key_block = key.key_blocks.get(self.shape_key_name) if key else None
		if not key_block:
			self.report({'ERROR'}, f"Shape key not found: '{self.shape_key_name}'")
			return {'CANCELLED'}
		
		fcurve = find_driver(key, key_block.path_from_id("value"))
		if not fcurve:
			self.report({'ERROR'}, f"Shape key '{self.shape_key_name}' isn't driven")
			return {'CANCELLED'}
		
		apply_curve_preset(fcurve, self.preset)

		self.report({'INFO'}, f"Curve preset '{self.preset}' to shape key '{self.shape_key_name}'")
		return {'FINISHED'}
