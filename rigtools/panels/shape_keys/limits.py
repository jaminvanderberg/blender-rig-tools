"""Shape key limits: a Limit Location and a Limit Rotation per control, as needed, holding
each connected side to its extent x Max. Also the Limited toggle and Lock Unused.
Nothing here may read the Key: its settings evaluate with its value driver, which reads the
bone, so that's a dependency cycle. The bone's own properties are safe."""
import math

import bpy
from bpy.props import BoolProperty, StringProperty

from rigtools.panels.shape_keys.shape_key_utils import (
	CHANNELS, MAX_TURN, add_bone_variable, create_new_driver, extent_name, find_driver,
	range_name, side_prop_names)
from rigtools.rig_data.shape_key_connections import get_shape_key_connections

LIMITS = {
	'LOC': ("Shape Key Limits", 'LIMIT_LOCATION'),
	'ROT': ("Shape Key Rotation Limits", 'LIMIT_ROTATION'),
}

def shape_key_limits(pose_bone):
	"""The bone's limit constraints made by Connect"""
	return [c for c in (pose_bone.constraints.get(name) for name, _type in LIMITS.values()) if c]

def set_limits_enabled(pose_bone, enabled):
	for constraint in shape_key_limits(pose_bone):
		constraint.mute = not enabled

def limit_field(axis, positive):
	"""The limit field for a side, e.g. 'max_z' for +Z"""
	return f"{'max' if positive else 'min'}_{'xyz'[axis]}"

def _sides(connections, channel):
	return {("XYZ".index(c.axis), c.positive) for c in connections if c.channel == channel}

def _build_limit_driver(armature_obj, pose_bone, constraint, axis, positive, channel, connected,
		opposite_connected):
	"""Drive one side's limit: extent x Max, or the opposite side's extent x -Min if that's
	further"""
	field = limit_field(axis, positive)
	fcurve = find_driver(armature_obj, constraint.path_from_id(field))
	if fcurve is None:
		fcurve = create_new_driver(constraint, field)
	driver = fcurve.driver
	for variable in list(driver.variables):
		driver.variables.remove(variable)

	reaches = []
	if connected:
		add_bone_variable(driver, "extent", armature_obj, pose_bone, extent_name(axis, positive, channel))
		add_bone_variable(driver, "range_max", armature_obj, pose_bone,
			range_name(axis, positive, "Max", channel))
		reaches.append("extent * range_max")
	if opposite_connected:
		add_bone_variable(driver, "opposite_extent", armature_obj, pose_bone,
			extent_name(axis, not positive, channel))
		add_bone_variable(driver, "opposite_min", armature_obj, pose_bone,
			range_name(axis, not positive, "Min", channel))
		reaches.append("opposite_extent * -opposite_min")

	reach = f"max({', '.join(reaches)}, 0)"
	if channel == 'ROT':
		reach = f"min({reach}, {MAX_TURN:.4f})"
	driver.expression = reach if positive else f"-{reach}"

def _update_channel_limits(armature_obj, pose_bone, channel, sides, lock):
	"""One channel's constraint: connected sides driven, the rest free, or at rest when
	locked. Removed when nothing on the channel is connected or locked"""
	name, constraint_type = LIMITS[channel]
	needed = bool(sides) or lock
	constraint = pose_bone.constraints.get(name)
	if needed and constraint is None:
		constraint = pose_bone.constraints.new(constraint_type)
		constraint.name = name
	if constraint is None:
		return
	for axis in range(3):
		if channel == 'ROT':
			# Limit Rotation has one switch per axis, so a free side gets a half turn
			setattr(constraint, f"use_limit_{'xyz'[axis]}",
				lock or (axis, True) in sides or (axis, False) in sides)
		for positive in (True, False):
			field = limit_field(axis, positive)
			connected = (axis, positive) in sides
			opposite_connected = (axis, not positive) in sides
			if channel == 'LOC':
				setattr(constraint, f"use_{field}", connected or lock)
			# A locked side still lets the opposite side's keys go negative (its Min)
			if connected or (lock and opposite_connected):
				_build_limit_driver(armature_obj, pose_bone, constraint, axis, positive, channel,
					connected, opposite_connected)
				continue
			fcurve = find_driver(armature_obj, constraint.path_from_id(field))
			if fcurve:
				armature_obj.animation_data.drivers.remove(fcurve)
			free = 0.0 if lock or channel == 'LOC' else math.pi
			setattr(constraint, field, free if positive else -free)

	if not needed:
		pose_bone.constraints.remove(constraint)
		return
	# Local space matches what the drivers read; Affect Transform stops the bone while dragging
	constraint.owner_space = 'LOCAL'
	constraint.use_transform_limit = True
	if channel == 'ROT':
		constraint.use_legacy_behavior = False

def update_limits(armature_obj, pose_bone):
	"""Rebuild the bone's limits from its records. Unconnected sides lose their properties.
	A bone with no connections isn't locked"""
	connections = get_shape_key_connections(pose_bone)
	lock = pose_bone.rigtools_lock_unused and len(connections) > 0
	for channel in CHANNELS:
		sides = _sides(connections, channel)
		for axis in range(3):
			for positive in (True, False):
				if (axis, positive) not in sides:
					for prop in side_prop_names(axis, positive, channel):
						if prop in pose_bone:
							del pose_bone[prop]
		_update_channel_limits(armature_obj, pose_bone, channel, sides, lock)

class RIG_OT_lock_unused_sides(bpy.types.Operator):
	"""Sets the bone's saved Lock Unused. The Limited toggle is for posing past the limits for
	a moment; this is part of the control's setup"""
	bl_idname = "rig.lock_unused_sides"
	bl_label = "Lock Unused Sides"
	bl_description = ("Hold every side with no shape key at rest, location and rotation, so the "
		"control only moves the ways it drives something")
	bl_options = {'REGISTER', 'UNDO'}

	armature_name: StringProperty(options={'HIDDEN'})
	bone_name: StringProperty(options={'HIDDEN'})
	lock: BoolProperty(default=True, options={'HIDDEN'})

	@classmethod
	def description(cls, context, properties):
		if properties.lock:
			return cls.bl_description
		return "Let the sides with no shape key move freely again"

	def execute(self, context):
		armature_obj = bpy.data.objects.get(self.armature_name)
		pose_bone = armature_obj.pose.bones.get(self.bone_name) if armature_obj else None
		if pose_bone is None:
			self.report({'ERROR'}, f"No bone '{self.bone_name}'")
			return {'CANCELLED'}
		# Its update rebuilds the limits (and turns them on when locking)
		pose_bone.rigtools_lock_unused = self.lock
		return {'FINISHED'}

# The Limited toggle: both constraints at once. Get/set, nothing saved
def _get_limits_enabled(pose_bone):
	return any(not constraint.mute for constraint in shape_key_limits(pose_bone))

def _set_limits_enabled(pose_bone, value):
	set_limits_enabled(pose_bone, value)

# Lock Unused is saved on the bone. Turning it on also turns the limits on, so it shows
def _update_lock_unused(pose_bone, context):
	armature_obj = pose_bone.id_data
	update_limits(armature_obj, pose_bone)
	if pose_bone.rigtools_lock_unused:
		set_limits_enabled(pose_bone, True)
	armature_obj.update_tag()

classes = (
	RIG_OT_lock_unused_sides,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	bpy.types.PoseBone.rigtools_limits_enabled = BoolProperty(
		name="Limited",
		description="The shape key limits. Turn off to pose past them for a new connection; "
			"Connect turns them back on",
		get=_get_limits_enabled, set=_set_limits_enabled)
	bpy.types.PoseBone.rigtools_lock_unused = BoolProperty(
		name="Lock Unused",
		description="Hold every side with no shape key at rest, location and rotation. "
			"Turn Limited off to pose past it",
		default=False, update=_update_lock_unused)

def unregister():
	del bpy.types.PoseBone.rigtools_lock_unused
	del bpy.types.PoseBone.rigtools_limits_enabled
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
