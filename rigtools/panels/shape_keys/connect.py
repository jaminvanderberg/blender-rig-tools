"""Connect: drive a shape key from the active bone's current pose, through a channel.

	control bone --(channel driver)--> SK-<key> property on the property bone --(key driver)--> key

The channel driver holds the capture: one Transform Channel variable per bone, named
capture_0, capture_1, ..., and the expression `clamp(capture_0 / E0 + capture_1 / E1, 0, 1)`,
where E is the bone's location at the extreme. Inverted terms are `(1 - capture_n / E)`.
The key's driver only reads the channel, so every key with the same name, on any mesh,
can share it. Nothing else is stored: the drivers are the record.
"""
import re
import bpy
from bpy.props import BoolProperty, StringProperty

from rigtools.armature_settings import get_armature_settings
from rigtools.assemblies.assembly_data import find_assemblies
from rigtools.panels.shape_keys.shape_key_utils import has_sides
from rigtools.utils.naming import does_match_def_name

CHANNEL_PREFIX = "SK-"
CAPTURE_PREFIX = "capture_"
CHANNEL_VARIABLE = "channel"
AXES = ('LOC_X', 'LOC_Y', 'LOC_Z')
# One term of the channel expression: capture_0 / 0.02, or (1 - capture_0 / 0.02)
TERM = re.compile(r"(\(1 - )?(" + CAPTURE_PREFIX + r"\d+) / (-?[0-9.e+-]+)\)?")

def channel_name(key_block_name):
	return CHANNEL_PREFIX + key_block_name

def _quoted(name):
	return f'["{bpy.utils.escape_identifier(name)}"]'

def _driver(anim_owner, path):
	anim = anim_owner.animation_data
	return anim.drivers.find(path) if anim else None

def _new_driver(owner, path):
	"""A clean scripted driver: no mapping curve or modifiers, so it outputs its expression."""
	fcurve = owner.driver_add(path)
	fcurve.keyframe_points.clear()
	for modifier in list(fcurve.modifiers):
		fcurve.modifiers.remove(modifier)
	fcurve.driver.type = 'SCRIPTED'
	return fcurve

def read_capture(pose_bone):
	"""(axis index, extreme) from the bone's own pose, or an error message.
	matrix_basis is the pose without constraints, so limits don't shorten the reading."""
	basis = pose_bone.matrix_basis
	location = basis.to_translation()
	rotation = basis.to_euler()
	scale = basis.to_scale()
	if max(abs(a) for a in rotation) > 1e-4:
		return None, f"'{pose_bone.name}' is rotated. Connect reads location only: clear its rotation"
	if max(abs(s - 1) for s in scale) > 1e-4:
		return None, f"'{pose_bone.name}' is scaled. Connect reads location only: clear its scale"
	if location.length < 1e-5:
		return None, f"'{pose_bone.name}' isn't posed. Move it to the shape's extreme first"
	axis = max(range(3), key=lambda i: abs(location[i]))
	return (axis, location[axis]), None

def _parse_terms(driver):
	"""{variable name: (extreme, inverted)} for the terms of one of our channel drivers."""
	return {name: (float(extreme), bool(inverted))
		for inverted, name, extreme in TERM.findall(driver.expression)}

def _expression(terms):
	parts = []
	for name in sorted(terms, key=lambda n: int(n[len(CAPTURE_PREFIX):])):
		extreme, inverted = terms[name]
		term = f"{name} / {extreme:.6g}"
		parts.append(f"(1 - {term})" if inverted else term)
	return f"clamp({' + '.join(parts)}, 0, 1)"

class RIG_OT_connect_shape_key(bpy.types.Operator):
	bl_idname = "rig.connect_shape_key"
	bl_label = "Connect Shape Key"
	bl_description = ("Drive this shape key from the active bone's current pose: "
		"the bone's position now is where the key reaches 1")
	bl_options = {'REGISTER', 'UNDO'}

	object_name: StringProperty(options={'HIDDEN'})
	shape_key_name: StringProperty(options={'HIDDEN'})

	invert: BoolProperty(
		name="Invert",
		description="The key is 1 at rest and 0 at the extreme",
		default=False,
	)

	@classmethod
	def poll(cls, context):
		return (context.mode == 'POSE'
			and context.active_pose_bone is not None)

	def execute(self, context):
		rig = context.object
		pose_bone = context.active_pose_bone
		mesh = bpy.data.objects.get(self.object_name)
		key = mesh.data.shape_keys if mesh and mesh.type == 'MESH' else None
		key_block = key.key_blocks.get(self.shape_key_name) if key else None

		error = self.problem(context, rig, pose_bone, mesh, key, key_block)
		if error:
			self.report({'ERROR'}, error)
			return {'CANCELLED'}
		capture, error = read_capture(pose_bone)
		if error:
			self.report({'ERROR'}, error)
			return {'CANCELLED'}
		axis, extreme = capture

		prop_bone = rig.pose.bones[get_armature_settings(rig.data, context).property_bone_name]
		channel = channel_name(key_block.name)
		channel_path = f'pose.bones{_quoted(prop_bone.name)}{_quoted(channel)}'

		# Check both drivers before changing anything
		channel_fcurve = _driver(rig, channel_path)
		if channel_fcurve and not self.is_ours(channel_fcurve.driver, CAPTURE_PREFIX):
			self.report({'ERROR'}, f"'{channel}' has a hand-written driver. Left alone")
			return {'CANCELLED'}
		key_fcurve = _driver(key, key_block.path_from_id("value"))
		if key_fcurve and not self.is_ours(key_fcurve.driver, CHANNEL_VARIABLE):
			self.report({'ERROR'}, f"'{key_block.name}' has a hand-written driver. Left alone")
			return {'CANCELLED'}

		# The channel: a 0-1 property on the property bone
		if channel not in prop_bone:
			prop_bone[channel] = 0.0
			prop_bone.id_properties_ui(channel).update(
				min=0.0, max=1.0, soft_min=0.0, soft_max=1.0,
				description=f"Shape key channel for {key_block.name}")

		# Its driver: same bone and axis replaces that term, anything else adds one
		if channel_fcurve is None:
			channel_fcurve = _new_driver(prop_bone, _quoted(channel))
		driver = channel_fcurve.driver
		terms = _parse_terms(driver)
		variable = next((v for v in driver.variables if v.name in terms
			and v.targets[0].bone_target == pose_bone.name
			and v.targets[0].transform_type == AXES[axis]), None)
		if variable is None:
			used = {v.name for v in driver.variables}
			index = next(i for i in range(len(used) + 1) if f"{CAPTURE_PREFIX}{i}" not in used)
			variable = driver.variables.new()
			variable.name = f"{CAPTURE_PREFIX}{index}"
			variable.type = 'TRANSFORMS'
			target = variable.targets[0]
			target.id = rig
			target.bone_target = pose_bone.name
			target.transform_type = AXES[axis]
			target.transform_space = 'LOCAL_SPACE'
			replaced = False
		else:
			replaced = True
		terms[variable.name] = (extreme, self.invert)
		driver.expression = _expression(terms)

		# The key just reads the channel
		if key_fcurve is None:
			key_fcurve = _new_driver(key, key_block.path_from_id("value"))
			reader = key_fcurve.driver.variables.new()
			reader.name = CHANNEL_VARIABLE
			reader.type = 'SINGLE_PROP'
			reader.targets[0].id_type = 'OBJECT'
			reader.targets[0].id = rig
			reader.targets[0].data_path = channel_path
			key_fcurve.driver.expression = CHANNEL_VARIABLE

		axis_name = "XYZ"[axis]
		action = "Updated" if replaced else "Connected"
		self.report({'INFO'}, f"{action} {key_block.name} to {pose_bone.name} "
			f"{axis_name} {extreme:+.4g}{' (inverted)' if self.invert else ''}")
		return {'FINISHED'}

	def problem(self, context, rig, pose_bone, mesh, key, key_block):
		"""An error message, or None if this can be connected."""
		if rig is None or rig.type != 'ARMATURE':
			return "Select the rig's control bone in pose mode"
		if key_block is None:
			return f"No shape key '{self.shape_key_name}' on '{self.object_name}'"
		if key_block == key.reference_key:
			return "The Basis can't be connected"
		if has_sides(key, key_block.name):
			return (f"'{key_block.name}' is split: connect its .L or .R instead")
		if not any(m.type == 'ARMATURE' and m.object == rig for m in mesh.modifiers):
			return f"'{mesh.name}' isn't deformed by '{rig.name}'"

		prop_bone_name = get_armature_settings(rig.data, context).property_bone_name
		if prop_bone_name not in rig.pose.bones:
			return f"The rig has no property bone ('{prop_bone_name}'). Set one in Armature Settings"
		name = pose_bone.name
		if name == prop_bone_name:
			return "The property bone can't be a control"
		owners = find_assemblies(rig.data, [name], include_org_states=False)
		if owners:
			return f"'{name}' belongs to assembly '{owners[0].name}'. Use a bone of your own"
		if does_match_def_name(name):
			return f"'{name}' is named like a DEF bone. Use a bone of your own"
		return None

	@staticmethod
	def is_ours(driver, prefix):
		"""Our drivers only use our variable names: capture_n on channels, channel on keys."""
		return driver.type == 'SCRIPTED' and all(
			v.name.startswith(prefix) if prefix == CAPTURE_PREFIX else v.name == prefix
			for v in driver.variables)

def find_channel(rig, key_block_name):
	"""(data path, driver F-curve or None) of a key's channel. Read-only, so safe in draw."""
	prop_bone_name = rig.data.rigtools.property_bone_name
	path = f'pose.bones{_quoted(prop_bone_name)}{_quoted(channel_name(key_block_name))}'
	return path, _driver(rig, path)

def connections(rig, key_block_name):
	"""[(variable, bone, axis letter, extreme, inverted)] for each bone driving this key."""
	_, fcurve = find_channel(rig, key_block_name)
	if fcurve is None:
		return []
	terms = _parse_terms(fcurve.driver)
	found = []
	for variable in fcurve.driver.variables:
		if variable.name in terms:
			target = variable.targets[0]
			extreme, inverted = terms[variable.name]
			found.append((variable.name, target.bone_target, target.transform_type[-1], extreme, inverted))
	return found

class RIG_OT_disconnect_shape_key(bpy.types.Operator):
	bl_idname = "rig.disconnect_shape_key"
	bl_label = "Disconnect"
	bl_description = ("Stop this bone driving the key. Removing the last bone also removes the "
		"channel, and the key's driver on every mesh that shares it")
	bl_options = {'REGISTER', 'UNDO'}

	rig_name: StringProperty(options={'HIDDEN'})
	shape_key_name: StringProperty(options={'HIDDEN'})
	variable: StringProperty(options={'HIDDEN'})

	def execute(self, context):
		rig = bpy.data.objects.get(self.rig_name)
		path, fcurve = find_channel(rig, self.shape_key_name) if rig else (None, None)
		variable = fcurve.driver.variables.get(self.variable) if fcurve else None
		if variable is None:
			self.report({'ERROR'}, f"'{self.shape_key_name}' isn't connected to that bone")
			return {'CANCELLED'}
		bone = variable.targets[0].bone_target

		driver = fcurve.driver
		terms = _parse_terms(driver)
		terms.pop(variable.name, None)
		driver.variables.remove(variable)
		if terms:
			driver.expression = _expression(terms)
			self.report({'INFO'}, f"Disconnected {bone} from {self.shape_key_name}")
			return {'FINISHED'}

		# That was the last bone: remove the channel and everything reading it
		rig.animation_data.drivers.remove(fcurve)
		prop_bone = rig.pose.bones.get(rig.data.rigtools.property_bone_name)
		channel = channel_name(self.shape_key_name)
		if prop_bone and channel in prop_bone:
			del prop_bone[channel]
		keys = 0
		for obj in bpy.data.objects:
			key = obj.data.shape_keys if obj.type == 'MESH' else None
			if key is None or key.animation_data is None:
				continue
			for key_fcurve in list(key.animation_data.drivers):
				if any(v.targets[0].id == rig and v.targets[0].data_path == path
						for v in key_fcurve.driver.variables):
					key_block = key.path_resolve(key_fcurve.data_path.rsplit(".", 1)[0])
					key.animation_data.drivers.remove(key_fcurve)
					key_block.value = 0.0
					keys += 1
		self.report({'INFO'}, f"Disconnected {self.shape_key_name} ({keys} key{'s' if keys != 1 else ''})")
		return {'FINISHED'}

class RIG_OT_select_control(bpy.types.Operator):
	bl_idname = "rig.select_control"
	bl_label = "Select Control"
	bl_description = "Select this control bone"
	bl_options = {'REGISTER', 'UNDO'}

	rig_name: StringProperty(options={'HIDDEN'})
	bone_name: StringProperty(options={'HIDDEN'})

	def execute(self, context):
		rig = context.object
		if rig is None or rig.name != self.rig_name or rig.mode != 'POSE':
			self.report({'INFO'}, f"Enter pose mode on '{self.rig_name}' to select its bones")
			return {'CANCELLED'}
		pose_bone = rig.pose.bones.get(self.bone_name)
		if pose_bone is None:
			self.report({'ERROR'}, f"No bone '{self.bone_name}'")
			return {'CANCELLED'}
		# Selection is on the pose bone since Blender 5.0, on the bone before
		for other in rig.pose.bones:
			(other if hasattr(other, "select") else other.bone).select = False
		(pose_bone if hasattr(pose_bone, "select") else pose_bone.bone).select = True
		rig.data.bones.active = pose_bone.bone
		return {'FINISHED'}

classes = (
	RIG_OT_connect_shape_key,
	RIG_OT_disconnect_shape_key,
	RIG_OT_select_control,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
