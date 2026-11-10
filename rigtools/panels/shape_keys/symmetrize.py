"""Symmetrize Connections: make each selected bone's mirror an exact copy of its shape key
connections, flipped.

Bones mirror by bone rules (flip_side_name: Eye.L to Eye.R; a bone with no side has no
mirror). Keys mirror by key rules (mirror_shape_key_name: Eye.Left.L to Eye.Right.R), and
sides flip by Blender's flip-pose rules, assuming symmetric rest rolls like the corrective
Mirror: location X, rotation Y and Z. So +X Eye.Left.L on Eye.L becomes -X Eye.Right.R on
Eye.R: the X flip mirrors the motion, the name flip relabels the key for it.

It replaces, like symmetry: the target's records, extents and ranges become the source's,
and its other connections go. Then the same update_limits and build_key_drivers as Connect
rebuild everything from the records.

Only live records count (see connection_status): a bone copied with Blender's Duplicate or
Symmetrize carries records that drive nothing, and they're neither mirrored nor kept.
"""
import bpy
from bpy.props import EnumProperty

from rigtools.panels.shape_keys.connect import (
	build_key_drivers, connection_status, control_problem, has_connections, has_foreign_driver,
	range_name, record_id, set_limits_enabled, set_side_props, side_name, tidy_connections,
	update_limits)
from rigtools.panels.shape_keys.shape_key_utils import has_sides, mirror_shape_key_name
from rigtools.rig_data.shape_key_connections import add_shape_key_connection, get_shape_key_connections
from rigtools.rig_ui.rig_ui import flip_side_name, get_base_name

def mirror_bone(armature_obj, pose_bone):
	"""The bone on the other side, or None for a center bone or a missing partner."""
	name = flip_side_name(pose_bone.name)
	return armature_obj.pose.bones.get(name) if name else None

def _is_left(name):
	_, side = get_base_name(name)
	return side[1:2].upper() == "L"

def mirrored_side(axis, positive, channel):
	"""Which way the mirror bone goes: location X flips, rotation Y and Z flip, the rest keep
	their sign (Blender's own flip-pose rule). axis is 0, 1, 2."""
	flips = axis == 0 if channel == 'LOC' else axis in (1, 2)
	return not positive if flips else positive

def can_symmetrize(armature_obj, pose_bones):
	"""True if any of these bones has connections and a mirror bone. Shared by the panel
	(shows the button) and poll."""
	return any(has_connections(armature_obj, pose_bone) and mirror_bone(armature_obj, pose_bone)
		for pose_bone in pose_bones)

def symmetrize_pairs(armature_obj, pose_bones, left_to_right):
	"""(source, target) for each selected bone with connections and a mirror. When both
	bones of a pair are selected, the direction picks the source."""
	selected = {pose_bone.name for pose_bone in pose_bones}
	pairs = []
	for pose_bone in pose_bones:
		target = mirror_bone(armature_obj, pose_bone)
		if target is None or not has_connections(armature_obj, pose_bone):
			continue
		if target.name in selected and _is_left(pose_bone.name) != left_to_right:
			continue
		pairs.append((pose_bone, target))
	return pairs

def pair_problems(context, armature_obj, source, target):
	"""Everything stopping source from being mirrored onto target, as messages."""
	problems = []
	error = control_problem(context, armature_obj, target)
	if error:
		problems.append(error)
	sides = set()
	for connection in get_shape_key_connections(source):
		# Dead records are dropped; a renamed key is mirrored under its new name
		status, key_name = connection_status(armature_obj, source, connection)
		if status == 'DEAD':
			continue
		if status == 'AMBIGUOUS':
			problems.append(f"{source.name}: '{connection.key_name}' was renamed, and several keys "
				"could be it")
			continue
		sides.add(("XYZ".index(connection.axis), connection.positive, connection.channel))
		mesh = connection.mesh
		key = mesh.data.shape_keys
		target_name = mirror_shape_key_name(key_name)
		if target_name is None:
			problems.append(f"'{key_name}' ({source.name}) has no mirror key name")
			continue
		target_block = key.key_blocks.get(target_name)
		if target_block is None:
			problems.append(f"'{target_name}' isn't on '{mesh.name}'. Mirror '{key_name}' first")
		elif has_sides(key, target_name):
			problems.append(f"'{target_name}' is split: its .L and .R are what get connected")
		elif has_foreign_driver(armature_obj, mesh, target_block):
			problems.append(f"'{target_name}' has a driver RigTools didn't make")
	for axis, positive, channel in sorted(sides):
		prop = side_name(axis, positive, channel)
		if prop not in source:
			problems.append(f"{source.name} has no {prop} extent. Connect it again")
	return problems

def mirror_connections(armature_obj, source, target):
	"""Replace target's connections with source's, mirrored, and copy each side's extent and
	range. Returns (keys, trust): the (mesh, key name) of every key whose drivers need
	rebuilding (the target's old keys and its new ones), and the record_ids just written.
	Drivers aren't rebuilt here, so several bones can be written before any key is."""
	# The target's old keys under their current names; its dead records drove nothing
	keys = set()
	for connection in get_shape_key_connections(target):
		status, key_name = connection_status(armature_obj, target, connection)
		if status in {'LIVE', 'RENAMED'}:
			keys.add((connection.mesh, key_name))
	target.rigtools_shape_keys.items.clear()
	tidy_connections(armature_obj, source)
	trust = set()

	sides = set()
	for connection in get_shape_key_connections(source):
		axis, channel = "XYZ".index(connection.axis), connection.channel
		key_name = mirror_shape_key_name(connection.key_name)
		positive = mirrored_side(axis, connection.positive, channel)
		add_shape_key_connection(target, connection.mesh, key_name, connection.axis, positive, channel)
		trust.add(record_id(target, connection.mesh, key_name, connection.axis, positive, channel))
		sides.add((axis, connection.positive, channel))
		keys.add((connection.mesh, key_name))
	target.rigtools_shape_keys.active_index = source.rigtools_shape_keys.active_index

	for axis, positive, channel in sides:
		flipped = mirrored_side(axis, positive, channel)
		set_side_props(target, axis, flipped, source[side_name(axis, positive, channel)], channel)
		for end, default in (("Min", 0.0), ("Max", 1.0)):
			target[range_name(axis, flipped, end, channel)] = source.get(
				range_name(axis, positive, end, channel), default)

	# Sides the source doesn't use lose their properties; the limits are on, as after Connect.
	# (Setting the lock runs its own rebuild too; harmless)
	target.rigtools_lock_unused = source.rigtools_lock_unused
	update_limits(armature_obj, target)
	set_limits_enabled(target, True)
	return keys, trust

class RIG_OT_symmetrize_connections(bpy.types.Operator):
	bl_idname = "rig.symmetrize_connections"
	bl_label = "Symmetrize Connections"
	bl_description = ("Make each selected bone's mirror drive the mirrored shape keys, the same "
		"way. Replaces the mirror bone's connections")
	bl_options = {'REGISTER', 'UNDO'}

	direction: EnumProperty(
		name="Direction",
		description="Which bone is copied when both sides of a pair are selected",
		items=[
			('LEFT_TO_RIGHT', "Left to Right", "Copy the left bone onto the right"),
			('RIGHT_TO_LEFT', "Right to Left", "Copy the right bone onto the left"),
		],
	)

	@classmethod
	def poll(cls, context):
		return (context.mode == 'POSE'
			and can_symmetrize(context.object, context.selected_pose_bones or []))

	def execute(self, context):
		armature_obj = context.object
		pairs = symmetrize_pairs(armature_obj, context.selected_pose_bones or [],
			self.direction == 'LEFT_TO_RIGHT')
		if not pairs:
			self.report({'ERROR'}, "No selected bone on that side has connections to mirror")
			return {'CANCELLED'}

		# All or nothing: a half-mirrored face is worse than none
		problems = [problem for source, target in pairs
			for problem in pair_problems(context, armature_obj, source, target)]
		if problems:
			self.report({'ERROR'}, "Nothing symmetrized. " + "; ".join(problems))
			return {'CANCELLED'}

		keys, trust = set(), set()
		for source, target in pairs:
			pair_keys, pair_trust = mirror_connections(armature_obj, source, target)
			keys |= pair_keys
			trust |= pair_trust

		# Once every bone is written, since two of them can drive one key
		for mesh, key_name in keys:
			key = mesh.data.shape_keys
			key_block = key.key_blocks.get(key_name) if key else None
			if key_block and not build_key_drivers(armature_obj, mesh, key_block, trust):
				key_block.value = 0.0
		# Bone properties set from Python don't tag the drivers that read them
		armature_obj.update_tag()

		names = ", ".join(f"{source.name} → {target.name}" for source, target in pairs)
		self.report({'INFO'}, f"Symmetrized {names}")
		return {'FINISHED'}

classes = (
	RIG_OT_symmetrize_connections,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
