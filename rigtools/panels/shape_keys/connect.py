"""Connect: drive a shape key from the active bone's current pose.

Each connection is recorded on the control bone (rig_data/shape_key_connections.py): which
mesh's shape key it drives, and from which side (axis and direction). The shape key's driver
is built from those records and never read back. Per bone driving the key, it has a
location variable (capture_n) and a variable reading that side's extent property on the bone
(extent_n), combined as `max(capture_0 / extent_0, capture_1 / extent_1, 0)`. The key's own
slider range caps the top.

Each side's extent is an `SK ±Axis` custom property on the control, e.g. `SK +Z`: how far
the bone moves on that side to reach 1. Each control also gets one Limit Location whose
connected sides are driven by those same extent properties.
"""
import bpy
from bpy.props import BoolProperty, StringProperty

from rigtools.armature_settings import get_armature_settings
from rigtools.assemblies.assembly_data import find_assemblies
from rigtools.panels.shape_keys.shape_key_utils import has_sides
from rigtools.rig_data.shape_key_connections import (
	add_shape_key_connection, find_bone_connections_for_shape_key, find_shape_key_connection,
	get_shape_key_connections, remove_shape_key_connection)
from rigtools.utils.naming import does_match_def_name
from rigtools.utils.object import get_controlled_meshes

AXES = ('LOC_X', 'LOC_Y', 'LOC_Z')
LIMIT_NAME = "Shape Key Limits"

def _quote(name):
	return f'["{bpy.utils.escape_identifier(name)}"]'

def _find_driver(anim_owner, path):
	anim = anim_owner.animation_data
	return anim.drivers.find(path) if anim else None

def _create_new_driver(owner, path):
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

def limit_constraint(pose_bone):
	return pose_bone.constraints.get(LIMIT_NAME)

def side_name(axis, positive):
	"""The control's extent property for one side, e.g. 'SK +Z'."""
	return f"SK {'+' if positive else '-'}{'XYZ'[axis]}"

def limit_field(axis, positive):
	"""The Limit Location field for one side, e.g. 'max_z' for +Z."""
	return f"{'max' if positive else 'min'}_{'xyz'[axis]}"

def _build_limit_driver(armature_obj, pose_bone, constraint, axis, positive, side_connections):
	"""Drive one side's limit field: the extent times the largest Range Max among the shape
	keys connected on that side. A Range Max of 1 stops the bone at the extent; 1.2 lets it
	travel 20% further, so the key reaches 1.2 (overshoot)."""
	field = limit_field(axis, positive)
	fcurve = _find_driver(armature_obj, constraint.path_from_id(field))
	if fcurve is None:
		fcurve = _create_new_driver(constraint, field)
	driver = fcurve.driver
	for variable in list(driver.variables):
		driver.variables.remove(variable)

	extent = driver.variables.new()
	extent.name = "extent"
	extent.type = 'SINGLE_PROP'
	extent.targets[0].id_type = 'OBJECT'
	extent.targets[0].id = armature_obj
	extent.targets[0].data_path = f'pose.bones{_quote(pose_bone.name)}{_quote(side_name(axis, positive))}'

	range_maxes = []
	for connection in side_connections:
		key = connection.mesh.data.shape_keys if connection.mesh else None
		key_block = key.key_blocks.get(connection.key_name) if key else None
		if key_block is None:
			continue
		range_max = driver.variables.new()
		range_max.name = f"range_max_{len(range_maxes)}"
		range_max.type = 'SINGLE_PROP'
		range_max.targets[0].id_type = 'KEY'
		range_max.targets[0].id = key
		range_max.targets[0].data_path = key_block.path_from_id("slider_max")
		range_maxes.append(range_max.name)

	sign = '' if positive else '-'
	driver.expression = f"{sign}extent * max({', '.join(range_maxes + ['1'])})"

def update_limits(armature_obj, pose_bone):
	"""Rebuild the bone's Limit Location from its connection records. Each connected side's
	field is driven by its extent and its shape keys' Range Max. Sides with no connection
	stay free, and lose their extent property."""
	connections = get_shape_key_connections(pose_bone)
	sides = {("XYZ".index(connection.axis), connection.positive) for connection in connections}

	constraint = limit_constraint(pose_bone)
	if sides and constraint is None:
		constraint = pose_bone.constraints.new('LIMIT_LOCATION')
		constraint.name = LIMIT_NAME
	for axis in range(3):
		for positive in (True, False):
			prop = side_name(axis, positive)
			connected = (axis, positive) in sides
			if not connected and prop in pose_bone:
				del pose_bone[prop]
			if constraint is None:
				continue
			field = limit_field(axis, positive)
			setattr(constraint, f"use_{field}", connected)
			if connected:
				side_connections = [connection for connection in connections
					if connection.axis == "XYZ"[axis] and connection.positive == positive]
				_build_limit_driver(armature_obj, pose_bone, constraint, axis, positive, side_connections)
				continue
			fcurve = _find_driver(armature_obj, constraint.path_from_id(field))
			if fcurve:
				armature_obj.animation_data.drivers.remove(fcurve)
			setattr(constraint, field, 0.0)

	if constraint is None:
		return
	if not sides:
		# Its field drivers are gone above; now the constraint itself
		pose_bone.constraints.remove(constraint)
		return
	# Local space matches what the drivers read; Affect Transform stops the bone while dragging
	constraint.owner_space = 'LOCAL'
	constraint.use_transform_limit = True

def _build_driver(armature_obj, mesh, key_block):
	"""Writes or overwrites the shape key's driver from the connection records, or removes
	it when no bone is recorded as driving the key. Returns whether a driver remains."""
	key = mesh.data.shape_keys
	path = key_block.path_from_id("value")
	fcurve = _find_driver(key, path)
	found = find_bone_connections_for_shape_key(armature_obj, mesh, key_block.name)
	if not found:
		if fcurve:
			key.animation_data.drivers.remove(fcurve)
		return False

	if fcurve is None:
		fcurve = _create_new_driver(key, path)
	driver = fcurve.driver
	for variable in list(driver.variables):
		driver.variables.remove(variable)

	terms = []
	for n, (pose_bone, sk_connection) in enumerate(found):
		axis = "XYZ".index(sk_connection.axis)
		capture = driver.variables.new()
		capture.name = f"capture_{n}"
		capture.type = 'TRANSFORMS'
		ctarget = capture.targets[0]
		ctarget.id = armature_obj
		ctarget.bone_target = pose_bone.name
		ctarget.transform_type = AXES[axis]
		ctarget.transform_space = 'LOCAL_SPACE'

		extent = driver.variables.new()
		extent.name = f"extent_{n}"
		extent.type = 'SINGLE_PROP'
		etarget = extent.targets[0]
		etarget.id_type = 'OBJECT'
		etarget.id = armature_obj
		etarget.data_path = (
			f'pose.bones{_quote(pose_bone.name)}{_quote(side_name(axis, sk_connection.positive))}'
		)

		sign = '' if sk_connection.positive else '-'
		terms.append(f"{sign}capture_{n} / extent_{n}")

	driver.expression = f"max({', '.join(terms)}, 0)"
	return True

class RIG_OT_connect_shape_key(bpy.types.Operator):
	bl_idname = "rig.connect_shape_key"
	bl_label = "Connect Shape Key"
	bl_description = ("Drive this shape key from the active bone's current pose: "
		"the bone's position now is where the key reaches 1")
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
		axis, extreme = capture

		# A driver with no connection records behind it was made by someone else: leave it alone
		key_fcurve = _find_driver(key, key_block.path_from_id("value"))
		if key_fcurve and not find_bone_connections_for_shape_key(armature_obj, mesh, key_block.name):
			self.report({'ERROR'}, f"'{key_block.name}' has a driver RigTools didn't make. Left alone")
			return {'CANCELLED'}

		# Connect captures: the pose sets the side's extent, new side or not
		side = side_name(axis, extreme > 0)
		pose_bone[side] = abs(extreme)
		# Fine steps for small distances; shown in scene units (cm/mm)
		pose_bone.id_properties_ui(side).update(
			subtype='DISTANCE', min=0.0001, soft_min=0.0, soft_max=0.1,
			step=0.01, precision=4,
			description=f"How far the bone moves {side[3:]} for its shape keys to reach 1")

		# Record the connection on this bone, then build the shape key's driver from the records
		axis_name = "XYZ"[axis]
		replaced = find_shape_key_connection(
			pose_bone, mesh, key_block.name, axis_name, extreme > 0) is not None
		add_shape_key_connection(pose_bone, mesh, key_block.name, axis_name, extreme > 0)

		# Turn the limits back on if they were off for posing
		update_limits(armature_obj, pose_bone)
		limit_constraint(pose_bone).mute = False
		_build_driver(armature_obj, mesh, key_block)

		action = "Updated" if replaced else "Connected"
		self.report({'INFO'}, f"{action} {key_block.name} to {pose_bone.name} {axis_name} {extreme:+.4g}")
		return {'FINISHED'}

	def problem(self, context, armature_obj, pose_bone, mesh, key, key_block):
		"""An error message, or None if this can be connected."""
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

	def execute(self, context):
		armature_obj = bpy.data.objects.get(self.armature_name)
		pose_bone = armature_obj.pose.bones.get(self.bone_name) if armature_obj else None
		mesh = bpy.data.objects.get(self.object_name)
		connection = find_shape_key_connection(
			pose_bone, mesh, self.shape_key_name, self.axis, self.positive) if pose_bone else None
		if connection is None:
			self.report({'ERROR'}, f"'{self.shape_key_name}' isn't connected to that bone")
			return {'CANCELLED'}
		remove_shape_key_connection(pose_bone, connection)
		update_limits(armature_obj, pose_bone)

		# The shape key's driver is rebuilt from the bones still driving it, or removed
		key = mesh.data.shape_keys if mesh and mesh.type == 'MESH' else None
		key_block = key.key_blocks.get(self.shape_key_name) if key else None
		if key_block and not _build_driver(armature_obj, mesh, key_block):
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

# The bone view's extent sliders. Each edits a side's SK property and moves the bone to
# that extent, so you see where it is. Get/set only: nothing is saved to the file.
# PROTOTYPE: the user wants this complexity scaled back later (see the plan).
def drive_slider(axis, positive):
	return f"rigtools_drive_{'pos' if positive else 'neg'}_{'xyz'[axis]}"

def _drive_property(axis, positive):
	prop = side_name(axis, positive)
	sign = 1 if positive else -1

	def get(pose_bone):
		return pose_bone.get(prop, 0.0)

	def set(pose_bone, value):
		pose_bone[prop] = value
		pose_bone.location[axis] = sign * value

	return bpy.props.FloatProperty(
		name=f"Extent {prop[3:]}",
		description=f"How far {prop[3:]} travels to reach 1. Moves the bone there",
		get=get, set=set, subtype='DISTANCE', min=0.0001, soft_min=0.0, soft_max=0.1,
		step=0.01, precision=4)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	for axis in range(3):
		for positive in (True, False):
			setattr(bpy.types.PoseBone, drive_slider(axis, positive), _drive_property(axis, positive))

def unregister():
	for axis in range(3):
		for positive in (True, False):
			delattr(bpy.types.PoseBone, drive_slider(axis, positive))
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
