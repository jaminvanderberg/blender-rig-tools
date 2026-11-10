"""Connect: drive a shape key from the active bone's current pose.

Each connection is recorded on the control bone (rig_data/shape_key_connections.py): which
mesh's shape key it drives, and from which side (channel, axis and direction). The channel
is location or rotation. The shape key's driver is built from those records. Per bone
driving the key, it has a transform variable (capture_n) and a variable reading that side's
extent property on the bone (extent_n), combined as `max(capture_0 / extent_0, ...)`. No
clamp in the expression: Blender clamps the value to the key's slider range.

Each connected side has three custom properties on the control, e.g. for +Z:
	SK +Z       extent: how far the bone moves on that side to reach 1
	SK +Z Min   the range's bottom, 0 by default; below 0 lets its keys go negative
	SK +Z Max   the range's top, 1 by default; 1.2 lets the bone and its keys overshoot
Rotation sides are named with an R: SK +RZ is an angle (radians, shown in degrees).
The key's slider range is driven from them (the widest range of the bones driving it), and
each control gets a Limit Location and a Limit Rotation, as needed, whose connected sides
are driven by them too.

Rotation is read as swing and twist around the bone's Y: twist is the turn around the
bone's own length (RY), swing the tilt of its tip, split into RX and RZ. Each reads cleanly
even with the others nudged, unlike Euler angles.

Nothing on the bone may read the Key. Blender evaluates a shape key's settings together with
its value driver, which reads the bone, so a limit reading the key's slider_max is a
dependency cycle. Custom properties on the bone are safe to read from anywhere.
"""
import math

import bpy
from bpy.props import BoolProperty, StringProperty
from mathutils import Quaternion

from rigtools.armature_settings import get_armature_settings
from rigtools.assemblies.assembly_data import find_assemblies
from rigtools.panels.shape_keys.shape_key_utils import has_sides
from rigtools.rig_data.shape_key_connections import (
	add_shape_key_connection, find_bone_connections_for_shape_key, find_shape_key_connection,
	get_shape_key_connections, remove_shape_key_connection)
from rigtools.utils.naming import does_match_def_name
from rigtools.utils.object import get_controlled_meshes

CHANNELS = ('LOC', 'ROT')
# One constraint per channel, made when the bone has a connected side on it
LIMITS = {
	'LOC': ("Shape Key Limits", 'LIMIT_LOCATION'),
	'ROT': ("Shape Key Rotation Limits", 'LIMIT_ROTATION'),
}
# The rotation driver variables' reading; capture reads the pose the same way
SWING_TWIST = 'SWING_TWIST_Y'
# A turn's direction is ambiguous at 180 degrees
MAX_TURN = math.radians(179)

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

def read_turns(rotation):
	"""(RX, RY, RZ) of a quaternion as the drivers read it (SWING_TWIST_Y): RY is the twist
	angle, RX and RZ are 2*asin of the swing's components. Tested against Blender's own."""
	swing, twist = rotation.to_swing_twist('Y')
	def swing_angle(component):
		return 2 * math.asin(max(-1.0, min(1.0, component)))
	return swing_angle(swing.x), twist, swing_angle(swing.z)

def read_capture(pose_bone):
	"""((channel, axis index, extreme), None) from the bone's own pose, or (None, an error
	message). The largest axis wins. A bone both moved and turned is refused rather than
	guessed. matrix_basis is the pose without constraints, so limits don't shorten it."""
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

def shape_key_limits(pose_bone):
	"""The bone's limit constraints made by Connect: none, one or both channels."""
	return [c for c in (pose_bone.constraints.get(name) for name, _type in LIMITS.values()) if c]

def set_limits_enabled(pose_bone, enabled):
	for constraint in shape_key_limits(pose_bone):
		constraint.mute = not enabled

def side_label(axis, positive, channel):
	"""How a side is shown, e.g. '+Z' or '-RY'."""
	return f"{'+' if positive else '-'}{'R' if channel == 'ROT' else ''}{'XYZ'[axis]}"

def side_name(axis, positive, channel):
	"""The control's extent property for one side, e.g. 'SK +Z' or 'SK -RY'."""
	return f"SK {side_label(axis, positive, channel)}"

def range_name(axis, positive, end, channel):
	"""A side's range property on the control, e.g. 'SK +Z Max' or 'SK +RY Min'."""
	return f"{side_name(axis, positive, channel)} {end}"

def side_props(axis, positive, channel):
	"""Every custom property a connected side owns: extent, Min and Max."""
	return (side_name(axis, positive, channel), range_name(axis, positive, "Min", channel),
		range_name(axis, positive, "Max", channel))

def limit_field(axis, positive):
	"""The limit constraint's field for one side, e.g. 'max_z' for +Z (both channels)."""
	return f"{'max' if positive else 'min'}_{'xyz'[axis]}"

def _sides(connections, channel):
	return {("XYZ".index(c.axis), c.positive) for c in connections if c.channel == channel}

def _add_bone_variable(driver, name, armature_obj, pose_bone, prop):
	"""A driver variable reading one of the control's custom properties."""
	variable = driver.variables.new()
	variable.name = name
	variable.type = 'SINGLE_PROP'
	variable.targets[0].id_type = 'OBJECT'
	variable.targets[0].id = armature_obj
	variable.targets[0].data_path = f'pose.bones{_quote(pose_bone.name)}{_quote(prop)}'

def _build_limit_driver(armature_obj, pose_bone, constraint, axis, positive, channel, opposite_connected):
	"""Drive one side's limit field from the bone's own properties: how far its keys need the
	bone to go. That's the side's extent times its Max (1 stops at the extent, 1.2 overshoots),
	or, if the opposite side is connected, that side's extent times minus its Min (how far
	back its keys go negative), whichever is further. Rotation stops short of a half turn."""
	field = limit_field(axis, positive)
	fcurve = _find_driver(armature_obj, constraint.path_from_id(field))
	if fcurve is None:
		fcurve = _create_new_driver(constraint, field)
	driver = fcurve.driver
	for variable in list(driver.variables):
		driver.variables.remove(variable)

	_add_bone_variable(driver, "extent", armature_obj, pose_bone, side_name(axis, positive, channel))
	_add_bone_variable(driver, "range_max", armature_obj, pose_bone,
		range_name(axis, positive, "Max", channel))
	reaches = ["extent * range_max"]
	if opposite_connected:
		_add_bone_variable(driver, "opposite_extent", armature_obj, pose_bone,
			side_name(axis, not positive, channel))
		_add_bone_variable(driver, "opposite_min", armature_obj, pose_bone,
			range_name(axis, not positive, "Min", channel))
		reaches.append("opposite_extent * -opposite_min")

	reach = f"max({', '.join(reaches)}, 0)"
	if channel == 'ROT':
		reach = f"min({reach}, {MAX_TURN:.4f})"
	driver.expression = reach if positive else f"-{reach}"

def _update_channel_limits(armature_obj, pose_bone, channel, sides):
	"""One channel's limit constraint: connected sides driven, others free, and the
	constraint removed when no side is connected."""
	name, constraint_type = LIMITS[channel]
	constraint = pose_bone.constraints.get(name)
	if sides and constraint is None:
		constraint = pose_bone.constraints.new(constraint_type)
		constraint.name = name
	if constraint is None:
		return
	for axis in range(3):
		if channel == 'ROT':
			# Limit Rotation has one switch per axis, so a free side gets a half turn
			setattr(constraint, f"use_limit_{'xyz'[axis]}",
				(axis, True) in sides or (axis, False) in sides)
		for positive in (True, False):
			field = limit_field(axis, positive)
			connected = (axis, positive) in sides
			if channel == 'LOC':
				setattr(constraint, f"use_{field}", connected)
			if connected:
				_build_limit_driver(armature_obj, pose_bone, constraint, axis, positive, channel,
					(axis, not positive) in sides)
				continue
			fcurve = _find_driver(armature_obj, constraint.path_from_id(field))
			if fcurve:
				armature_obj.animation_data.drivers.remove(fcurve)
			free = math.pi if channel == 'ROT' else 0.0
			setattr(constraint, field, free if positive else -free)

	if not sides:
		# Its field drivers are gone above; now the constraint itself
		pose_bone.constraints.remove(constraint)
		return
	# Local space matches what the drivers read; Affect Transform stops the bone while dragging
	constraint.owner_space = 'LOCAL'
	constraint.use_transform_limit = True
	if channel == 'ROT':
		constraint.use_legacy_behavior = False

def update_limits(armature_obj, pose_bone):
	"""Rebuild the bone's limit constraints from its connection records. Each connected side's
	field is driven by the bone's extent and range properties. Sides with no connection stay
	free, and lose their properties."""
	connections = get_shape_key_connections(pose_bone)
	for channel in CHANNELS:
		sides = _sides(connections, channel)
		for axis in range(3):
			for positive in (True, False):
				if (axis, positive) not in sides:
					for prop in side_props(axis, positive, channel):
						if prop in pose_bone:
							del pose_bone[prop]
		_update_channel_limits(armature_obj, pose_bone, channel, sides)

def _combine(function, terms):
	"""max(a, b, ...) or min(...), or the bare term when there's only one: Python's max and
	min need at least two arguments."""
	return terms[0] if len(terms) == 1 else f"{function}({', '.join(terms)})"

def _key_driver(key, key_block, prop, found):
	"""The key's driver on one of its properties, emptied for rebuilding; or removed (and
	None returned) when no bone drives the key. A removed range driver leaves its last value."""
	path = key_block.path_from_id(prop)
	fcurve = _find_driver(key, path)
	if not found:
		if fcurve:
			key.animation_data.drivers.remove(fcurve)
		return None
	if fcurve is None:
		fcurve = _create_new_driver(key, path)
	driver = fcurve.driver
	for variable in list(driver.variables):
		driver.variables.remove(variable)
	return driver

def _build_value_driver(armature_obj, key, key_block, found):
	"""Per bone and side: location or rotation over extent, combined with max. Blender clamps
	the value to the slider range, which _build_range_drivers sets, so no clamp here."""
	driver = _key_driver(key, key_block, "value", found)
	if driver is None:
		return
	terms = []
	for n, (pose_bone, sk_connection) in enumerate(found):
		axis = "XYZ".index(sk_connection.axis)
		capture = driver.variables.new()
		capture.name = f"capture_{n}"
		capture.type = 'TRANSFORMS'
		ctarget = capture.targets[0]
		ctarget.id = armature_obj
		ctarget.bone_target = pose_bone.name
		ctarget.transform_type = f"{sk_connection.channel}_{sk_connection.axis}"
		ctarget.transform_space = 'LOCAL_SPACE'
		if sk_connection.channel == 'ROT':
			ctarget.rotation_mode = SWING_TWIST

		_add_bone_variable(driver, f"extent_{n}", armature_obj, pose_bone,
			side_name(axis, sk_connection.positive, sk_connection.channel))

		sign = '' if sk_connection.positive else '-'
		terms.append(f"{sign}capture_{n} / extent_{n}")
	driver.expression = _combine("max", terms)

def _build_range_drivers(armature_obj, key, key_block, found):
	"""The key's slider range from the bones driving it: the widest of their sides' ranges,
	so slider_max is the largest Max and slider_min the smallest Min. Reads only bone
	properties, so nothing here waits on the key's own value."""
	for prop, end, function in (("slider_max", "Max", "max"), ("slider_min", "Min", "min")):
		driver = _key_driver(key, key_block, prop, found)
		if driver is None:
			continue
		terms = []
		for n, (pose_bone, sk_connection) in enumerate(found):
			axis = "XYZ".index(sk_connection.axis)
			name = f"{end.lower()}_{n}"
			_add_bone_variable(driver, name, armature_obj, pose_bone,
				range_name(axis, sk_connection.positive, end, sk_connection.channel))
			terms.append(name)
		driver.expression = _combine(function, terms)

def build_key_drivers(armature_obj, mesh, key_block, trust=()):
	"""Writes or overwrites the shape key's value and range drivers from its live connection
	records, or removes them when none are left. trust holds record_ids of records just
	written, which aren't in the driver yet. Returns whether the key is still driven."""
	key = mesh.data.shape_keys
	found = live_connections_for_key(armature_obj, mesh, key_block, trust)
	_build_range_drivers(armature_obj, key, key_block, found)
	_build_value_driver(armature_obj, key, key_block, found)
	return bool(found)

# Which records are real. Blender's Duplicate and edit mode Symmetrize copy a bone's records,
# properties and constraints, but not the drivers, so a copied record names a key that
# doesn't read its bone. And keys are stored by name, so a renamed key leaves a record
# pointing at nothing while its driver (renamed with it) still works. Both are told apart
# by asking the driver: does it read this bone's extent for this side? That one variable
# names the bone (Blender updates it when the bone is renamed), the channel, axis and side.

def _reads_side(armature_obj, key, key_block, pose_bone, connection):
	"""True if the key's value driver reads this bone's extent property for this record's side."""
	fcurve = _find_driver(key, key_block.path_from_id("value"))
	if fcurve is None:
		return False
	prop = side_name("XYZ".index(connection.axis), connection.positive, connection.channel)
	path = f'pose.bones{_quote(pose_bone.name)}{_quote(prop)}'
	return any(variable.type == 'SINGLE_PROP' and variable.targets[0].id == armature_obj
		and variable.targets[0].data_path == path for variable in fcurve.driver.variables)

def connection_status(armature_obj, pose_bone, connection):
	"""(status, key name) for one record:
		LIVE       the key exists and its driver reads this side
		RENAMED    the key is gone, and exactly one other key's driver reads this side
		           (not one this bone already has a record for): its new name
		AMBIGUOUS  several keys could be the renamed one
		DEAD       nothing reads it: a copied bone's record, or a driver removed by hand"""
	mesh = connection.mesh
	key = mesh.data.shape_keys if mesh and mesh.type == 'MESH' else None
	if key is None:
		return 'DEAD', None
	key_block = key.key_blocks.get(connection.key_name)
	if key_block is not None:
		live = _reads_side(armature_obj, key, key_block, pose_bone, connection)
		return ('LIVE', key_block.name) if live else ('DEAD', None)
	candidates = [kb.name for kb in key.key_blocks
		if _reads_side(armature_obj, key, kb, pose_bone, connection)
		and find_shape_key_connection(pose_bone, mesh, kb.name, connection.axis,
			connection.positive, connection.channel) is None]
	if len(candidates) == 1:
		return 'RENAMED', candidates[0]
	return ('AMBIGUOUS', None) if candidates else ('DEAD', None)

def has_connections(armature_obj, pose_bone):
	"""True if the bone has any record that isn't dead."""
	return any(connection_status(armature_obj, pose_bone, connection)[0] != 'DEAD'
		for connection in get_shape_key_connections(pose_bone))

def record_id(pose_bone, mesh, key_name, axis_name, positive, channel):
	"""Identifies a record by value, for trust: items can move in memory as the list grows."""
	return (pose_bone.name, mesh.name, key_name, axis_name, positive, channel)

def live_connections_for_key(armature_obj, mesh, key_block, trust=()):
	"""[(pose bone, record)] for the records that really drive this key, plus trusted ones."""
	key = mesh.data.shape_keys
	return [(pose_bone, connection)
		for pose_bone, connection in find_bone_connections_for_shape_key(armature_obj, mesh, key_block.name)
		if record_id(pose_bone, mesh, key_block.name, connection.axis, connection.positive,
			connection.channel) in trust
		or _reads_side(armature_obj, key, key_block, pose_bone, connection)]

def tidy_connections(armature_obj, pose_bone):
	"""Run by every operator that changes a bone's connections, before it does: renamed keys
	get their new name, dead records are forgotten. Ambiguous ones are kept for the Data
	Viewer. The caller's update_limits then clears the dead sides' properties."""
	items = get_shape_key_connections(pose_bone)
	statuses = [connection_status(armature_obj, pose_bone, connection) for connection in items]
	for index in reversed(range(len(items))):
		status, key_name = statuses[index]
		if status == 'DEAD':
			remove_shape_key_connection(pose_bone, items[index])
		elif status == 'RENAMED':
			items[index].key_name = key_name

def set_side_props(pose_bone, axis, positive, extent, channel):
	"""Write a side's extent, and create its Min and Max if they're missing: the range is
	created once, then it's the user's, so reconnecting keeps it."""
	side = side_name(axis, positive, channel)
	pose_bone[side] = extent
	label = side_label(axis, positive, channel)
	if channel == 'ROT':
		# Radians, shown in degrees
		pose_bone.id_properties_ui(side).update(
			subtype='ANGLE', min=0.0001, max=MAX_TURN, soft_min=0.0, soft_max=math.pi / 2,
			precision=1, description=f"How far the bone turns {label} for its shape keys to reach 1")
	else:
		# Fine steps for small distances; shown in scene units (cm/mm)
		pose_bone.id_properties_ui(side).update(
			subtype='DISTANCE', min=0.0001, soft_min=0.0, soft_max=0.1,
			step=0.01, precision=4,
			description=f"How far the bone moves {label} for its shape keys to reach 1")
	for end, default, description in (
			("Min", 0.0, "The lowest its shape keys go. Below 0, moving the bone the other way "
				"takes them negative"),
			("Max", 1.0, "The highest its shape keys go. Above 1 lets the bone travel past "
				"the extent (overshoot)")):
		prop = range_name(axis, positive, end, channel)
		if prop not in pose_bone:
			pose_bone[prop] = default
			pose_bone.id_properties_ui(prop).update(
				min=-10.0 if end == "Min" else 0.0, max=0.0 if end == "Min" else 10.0,
				soft_min=-1.0 if end == "Min" else 0.0, soft_max=0.0 if end == "Min" else 2.0,
				step=1, precision=2, description=description)

def has_foreign_driver(armature_obj, mesh, key_block):
	"""A value driver with no live connection records behind it was made by someone else:
	leave it alone."""
	key = mesh.data.shape_keys
	return (_find_driver(key, key_block.path_from_id("value")) is not None
		and not live_connections_for_key(armature_obj, mesh, key_block))

def control_problem(context, armature_obj, pose_bone):
	"""Why this bone can't be a shape key control, or None."""
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

		if has_foreign_driver(armature_obj, mesh, key_block):
			self.report({'ERROR'}, f"'{key_block.name}' has a driver RigTools didn't make. Left alone")
			return {'CANCELLED'}

		# Copied records go first, so connecting a duplicated bone starts it clean
		tidy_connections(armature_obj, pose_bone)
		# Connect captures: the pose sets the side's extent, new side or not
		set_side_props(pose_bone, axis, positive, abs(extreme), channel)

		# Record the connection on this bone, then build the shape key's driver from the records
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
		tidy_connections(armature_obj, pose_bone)
		update_limits(armature_obj, pose_bone)

		# The shape key's driver is rebuilt from the bones still driving it, or removed
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

# The bone view's extent sliders. Each edits a side's SK property and moves or turns the bone
# to that extent, so you see where it is. Get/set only: nothing is saved to the file.
# PROTOTYPE: the user wants this complexity scaled back later (see the plan).
def drive_slider(axis, positive, channel):
	return (f"rigtools_drive_{'pos' if positive else 'neg'}_"
		f"{'r' if channel == 'ROT' else ''}{'xyz'[axis]}")

def _set_turn(pose_bone, axis, angle):
	"""Turn the bone by angle around one local axis, in whatever rotation mode it uses."""
	vector = [0.0, 0.0, 0.0]
	vector[axis] = 1.0
	rotation = Quaternion(vector, angle)
	if pose_bone.rotation_mode == 'QUATERNION':
		pose_bone.rotation_quaternion = rotation
	elif pose_bone.rotation_mode == 'AXIS_ANGLE':
		turn_axis, turn_angle = rotation.to_axis_angle()
		pose_bone.rotation_axis_angle = (turn_angle, *turn_axis)
	else:
		pose_bone.rotation_euler = rotation.to_euler(pose_bone.rotation_mode)

def _drive_property(axis, positive, channel):
	prop = side_name(axis, positive, channel)
	label = side_label(axis, positive, channel)
	sign = 1 if positive else -1

	def get(pose_bone):
		return pose_bone.get(prop, 0.0)

	def set(pose_bone, value):
		pose_bone[prop] = value
		if channel == 'ROT':
			_set_turn(pose_bone, axis, sign * value)
		else:
			pose_bone.location[axis] = sign * value

	if channel == 'ROT':
		return bpy.props.FloatProperty(
			name=f"Extent {label}",
			description=f"How far {label} turns to reach 1. Turns the bone there",
			get=get, set=set, subtype='ANGLE', min=0.0001, max=MAX_TURN, soft_min=0.0,
			soft_max=math.pi / 2, precision=1)
	return bpy.props.FloatProperty(
		name=f"Extent {label}",
		description=f"How far {label} travels to reach 1. Moves the bone there",
		get=get, set=set, subtype='DISTANCE', min=0.0001, soft_min=0.0, soft_max=0.1,
		step=0.01, precision=4)

# The Limited/Unlocked toggle: both limit constraints at once. Get/set, nothing saved
def _get_limits_enabled(pose_bone):
	return any(not constraint.mute for constraint in shape_key_limits(pose_bone))

def _set_limits_enabled(pose_bone, value):
	set_limits_enabled(pose_bone, value)

def _all_sides():
	return [(axis, positive, channel) for channel in CHANNELS for axis in range(3)
		for positive in (True, False)]

def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	for axis, positive, channel in _all_sides():
		setattr(bpy.types.PoseBone, drive_slider(axis, positive, channel),
			_drive_property(axis, positive, channel))
	bpy.types.PoseBone.rigtools_limits_enabled = BoolProperty(
		name="Limited",
		description="The shape key limits. Turn off to pose past them for a new connection; "
			"Connect turns them back on",
		get=_get_limits_enabled, set=_set_limits_enabled)

def unregister():
	del bpy.types.PoseBone.rigtools_limits_enabled
	for axis, positive, channel in _all_sides():
		delattr(bpy.types.PoseBone, drive_slider(axis, positive, channel))
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
