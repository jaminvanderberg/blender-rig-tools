"""Connect and Disconnect: drive a shape key from a control bone's pose. Plus selecting a
control or a connected key from the panel.
The records (rig_data/shape_key_connections.py) are the source; key_drivers.py builds the
drivers from them, limits.py the bone's limits."""
import math

import bpy
from bpy.props import BoolProperty, StringProperty

from rigtools.armature_settings import get_armature_settings
from rigtools.assemblies.assembly_data import find_assemblies
from rigtools.panels.shape_keys.connection_status import (
	connection_status, record_id, tidy_rig_connections)
from rigtools.panels.shape_keys.key_drivers import build_key_drivers, has_foreign_driver
from rigtools.panels.shape_keys.limits import set_limits_enabled, update_limits
from rigtools.panels.shape_keys.shape_key_utils import (
	MAX_TURN, has_sides, set_side_props, side_label)
from rigtools.rig_data.shape_key_connections import (
	add_shape_key_connection, find_shape_key_connection, remove_shape_key_connection)
from rigtools.utils.naming import does_match_def_name
from rigtools.utils.object import get_controlled_meshes

def read_turns(rotation):
	"""(RX, RY, RZ) of a quaternion as the drivers read it (SWING_TWIST_Y): RY is the twist
	around the bone's length, RX and RZ the tilt of its tip (2 * asin of the swing)"""
	swing, twist = rotation.to_swing_twist('Y')
	def swing_angle(component):
		return 2 * math.asin(max(-1.0, min(1.0, component)))
	return swing_angle(swing.x), twist, swing_angle(swing.z)

def read_capture(pose_bone):
	"""((channel, axis, extreme), None) from the bone's pose, or (None, error). The largest axis
	wins; moved and turned is refused. matrix_basis, so limits don't shorten it"""
	location, rotation, scale = pose_bone.matrix_basis.decompose()
	if max(abs(s - 1) for s in scale) > 1e-4:
		return None, f"'{pose_bone.name}' is scaled. Connect reads location or rotation: clear its scale"
	turns = read_turns(rotation)
	moved = location.length >= 1e-5
	turned = max(abs(t) for t in turns) > 1e-4
	if moved and turned:
		return None, (f"'{pose_bone.name}' is both moved and rotated. Connect reads one: "
			"clear the other")
	if moved:
		axis = max(range(3), key=lambda i: abs(location[i]))
		return ('LOC', axis, location[axis]), None
	if turned:
		axis = max(range(3), key=lambda i: abs(turns[i]))
		if abs(turns[axis]) > MAX_TURN:
			return None, f"'{pose_bone.name}' is turned past 179°. Use a smaller turn"
		return ('ROT', axis, turns[axis]), None
	return None, f"'{pose_bone.name}' isn't posed. Move or turn it to the shape's extreme first"

def control_problem(context, armature_obj, pose_bone):
	"""Why this bone can't be a shape key control, or None"""
	prop_bone_name = get_armature_settings(armature_obj.data, context).property_bone_name
	name = pose_bone.name
	if name == prop_bone_name:
		return "The property bone can't be a control"
	owners = find_assemblies(armature_obj.data, [name], include_org_states=False)
	if owners:
		return f"'{name}' belongs to assembly '{owners[0].name}'. Use a bone of your own"
	if does_match_def_name(name):
		return f"'{name}' is named like a DEF bone. Use a bone of your own"
	return None

class RIG_OT_connect_shape_key(bpy.types.Operator):
	bl_idname = "rig.connect_shape_key"
	bl_label = "Connect Shape Key"
	bl_description = ("Drive this shape key from the active bone's current pose: "
		"the bone's position or turn now is where the key reaches 1")
	bl_options = {'REGISTER', 'UNDO'}

	object_name: StringProperty(options={'HIDDEN'})
	shape_key_name: StringProperty(options={'HIDDEN'})

	@classmethod
	def poll(cls, context):
		return (context.mode == 'POSE'
			and context.active_pose_bone is not None)

	def execute(self, context):
		armature_obj = context.object
		pose_bone = context.active_pose_bone
		mesh = bpy.data.objects.get(self.object_name)
		key = mesh.data.shape_keys if mesh and mesh.type == 'MESH' else None
		key_block = key.key_blocks.get(self.shape_key_name) if key else None

		error = self.problem(context, armature_obj, pose_bone, mesh, key, key_block)
		if error:
			self.report({'ERROR'}, error)
			return {'CANCELLED'}
		capture, error = read_capture(pose_bone)
		if error:
			self.report({'ERROR'}, error)
			return {'CANCELLED'}
		channel, axis, extreme = capture
		positive = extreme > 0

		# Before the foreign check: a renamed key's records have the old name until tidied
		tidy_rig_connections(armature_obj)
		if has_foreign_driver(armature_obj, mesh, key_block):
			self.report({'ERROR'}, f"'{key_block.name}' has a driver RigTools didn't make. Left alone")
			return {'CANCELLED'}
		# The pose sets the side's extent, new side or not
		set_side_props(pose_bone, axis, positive, abs(extreme), channel)

		axis_name = "XYZ"[axis]
		replaced = find_shape_key_connection(
			pose_bone, mesh, key_block.name, axis_name, positive, channel) is not None
		add_shape_key_connection(pose_bone, mesh, key_block.name, axis_name, positive, channel)

		# Turn the limits back on if they were off for posing
		update_limits(armature_obj, pose_bone)
		set_limits_enabled(pose_bone, True)
		# The new record isn't in the driver yet, so it's trusted
		build_key_drivers(armature_obj, mesh, key_block,
			trust={record_id(pose_bone, mesh, key_block.name, axis_name, positive, channel)})

		action = "Updated" if replaced else "Connected"
		amount = f"{math.degrees(abs(extreme)):.3g}°" if channel == 'ROT' else f"{abs(extreme):.4g}"
		self.report({'INFO'}, f"{action} {key_block.name} to {pose_bone.name} "
			f"{side_label(axis, positive, channel)} {amount}")
		return {'FINISHED'}

	def problem(self, context, armature_obj, pose_bone, mesh, key, key_block):
		"""An error message, or None if this can be connected"""
		if armature_obj is None or armature_obj.type != 'ARMATURE':
			return "Select the rig's control bone in pose mode"
		if key_block is None:
			return f"No shape key '{self.shape_key_name}' on '{self.object_name}'"
		if key_block == key.reference_key:
			return "The Basis can't be connected"
		if has_sides(key, key_block.name):
			return (f"'{key_block.name}' is split: connect its .L or .R instead")
		if not any(m.type == 'ARMATURE' and m.object == armature_obj for m in mesh.modifiers):
			return f"'{mesh.name}' isn't deformed by '{armature_obj.name}'"
		return control_problem(context, armature_obj, pose_bone)

class RIG_OT_disconnect_shape_key(bpy.types.Operator):
	bl_idname = "rig.disconnect_shape_key"
	bl_label = "Disconnect"
	bl_description = "Stop this bone driving this shape key from this side"
	bl_options = {'REGISTER', 'UNDO'}

	armature_name: StringProperty(options={'HIDDEN'})
	bone_name: StringProperty(options={'HIDDEN'})
	object_name: StringProperty(options={'HIDDEN'})
	shape_key_name: StringProperty(options={'HIDDEN'})
	axis: StringProperty(options={'HIDDEN'})
	positive: BoolProperty(options={'HIDDEN'})
	channel: StringProperty(default='LOC', options={'HIDDEN'})

	def execute(self, context):
		armature_obj = bpy.data.objects.get(self.armature_name)
		pose_bone = armature_obj.pose.bones.get(self.bone_name) if armature_obj else None
		mesh = bpy.data.objects.get(self.object_name)
		connection = find_shape_key_connection(pose_bone, mesh, self.shape_key_name, self.axis,
			self.positive, self.channel) if pose_bone else None
		if connection is None:
			self.report({'ERROR'}, f"'{self.shape_key_name}' isn't connected to that bone")
			return {'CANCELLED'}
		# The key's current name, in case it was renamed since the record was written
		_status, key_name = connection_status(armature_obj, pose_bone, connection)
		remove_shape_key_connection(pose_bone, connection)
		tidy_rig_connections(armature_obj)
		update_limits(armature_obj, pose_bone)

		# Rebuilt from the bones still driving it, or removed
		key = mesh.data.shape_keys if mesh and mesh.type == 'MESH' else None
		key_block = key.key_blocks.get(key_name) if key and key_name else None
		if key_block and not build_key_drivers(armature_obj, mesh, key_block):
			key_block.value = 0.0
		self.report({'INFO'}, f"Disconnected {self.bone_name} from {self.shape_key_name}")
		return {'FINISHED'}

class RIG_OT_select_control(bpy.types.Operator):
	bl_idname = "rig.select_control"
	bl_label = "Select Control"
	bl_description = "Select this control bone"
	bl_options = {'REGISTER', 'UNDO'}

	armature_name: StringProperty(options={'HIDDEN'})
	bone_name: StringProperty(options={'HIDDEN'})

	def execute(self, context):
		armature_obj = context.object
		if armature_obj is None or armature_obj.name != self.armature_name or armature_obj.mode != 'POSE':
			self.report({'INFO'}, f"Enter pose mode on '{self.armature_name}' to select its bones")
			return {'CANCELLED'}
		pose_bone = armature_obj.pose.bones.get(self.bone_name)
		if pose_bone is None:
			self.report({'ERROR'}, f"No bone '{self.bone_name}'")
			return {'CANCELLED'}
		# Selection is on the pose bone since Blender 5.0, on the bone before
		for other in armature_obj.pose.bones:
			(other if hasattr(other, "select") else other.bone).select = False
		(pose_bone if hasattr(pose_bone, "select") else pose_bone.bone).select = True
		armature_obj.data.bones.active = pose_bone.bone
		return {'FINISHED'}

class RIG_OT_select_connected_key(bpy.types.Operator):
	bl_idname = "rig.select_connected_key"
	bl_label = "Select Shape Key"
	bl_description = "Make this the active shape key on every mesh of the rig that has it"
	bl_options = {'REGISTER', 'UNDO'}

	armature_name: StringProperty(options={'HIDDEN'})
	shape_key_name: StringProperty(options={'HIDDEN'})

	def execute(self, context):
		armature_obj = bpy.data.objects.get(self.armature_name)
		if armature_obj is None:
			self.report({'ERROR'}, f"No armature '{self.armature_name}'")
			return {'CANCELLED'}
		found = 0
		for obj in get_controlled_meshes(armature_obj, context.view_layer):
			index = obj.data.shape_keys.key_blocks.find(self.shape_key_name)
			if index >= 0:
				obj.active_shape_key_index = index
				found += 1
		if not found:
			self.report({'ERROR'}, f"No mesh of '{armature_obj.name}' has '{self.shape_key_name}'")
			return {'CANCELLED'}
		return {'FINISHED'}

classes = (
	RIG_OT_connect_shape_key,
	RIG_OT_disconnect_shape_key,
	RIG_OT_select_control,
	RIG_OT_select_connected_key,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
