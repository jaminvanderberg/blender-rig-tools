"""The bone view's Extent sliders: each edits a side's extent and moves or turns the bone
there, so you see where it is. Get/set only: nothing is saved."""
import math

import bpy
from mathutils import Quaternion

from rigtools.panels.shape_keys.shape_key_utils import CHANNELS, MAX_TURN, extent_name, side_label

def drive_slider(axis, positive, channel):
	"""The PoseBone property name of a side's slider, e.g. 'rigtools_drive_pos_rz'"""
	return (f"rigtools_drive_{'pos' if positive else 'neg'}_"
		f"{'r' if channel == 'ROT' else ''}{'xyz'[axis]}")

def _set_turn(pose_bone, axis, angle):
	"""Turn the bone by angle around one local axis, in whatever rotation mode it uses"""
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

def _make_slider_property(axis, positive, channel):
	prop = extent_name(axis, positive, channel)
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

def _get_all_sides():
	return [(axis, positive, channel) for channel in CHANNELS for axis in range(3)
		for positive in (True, False)]

def register():
	for axis, positive, channel in _get_all_sides():
		setattr(bpy.types.PoseBone, drive_slider(axis, positive, channel),
			_make_slider_property(axis, positive, channel))

def unregister():
	for axis, positive, channel in _get_all_sides():
		delattr(bpy.types.PoseBone, drive_slider(axis, positive, channel))
