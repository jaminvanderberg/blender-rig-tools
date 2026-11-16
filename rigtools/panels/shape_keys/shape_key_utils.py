"""Shared helpers for the shape key tools: key names and data, moving keys, drivers, and a
control's sides and their properties."""
import math
import re

import bpy
import numpy as np

from rigtools.rig_ui.rig_ui import flip_side_name, get_base_name
from rigtools.utils.naming import SEPARATORS, SIDE_NAMES

def side_names(name):
	"""A key's .L and .R names"""
	return f"{name}.L", f"{name}.R"

def find_driver(anim_owner, path):
	anim = anim_owner.animation_data
	return anim.drivers.find(path) if anim else None

def _quote(name):
	return f'["{bpy.utils.escape_identifier(name)}"]'

def bone_prop_path(pose_bone, prop):
	"""Data path from the armature object to a custom property on the bone"""
	return f'pose.bones{_quote(pose_bone.name)}{_quote(prop)}'

def create_new_driver(owner, path):
	"""A scripted driver with no curve or modifiers, so it outputs its expression"""
	fcurve = owner.driver_add(path)
	fcurve.keyframe_points.clear()
	for modifier in list(fcurve.modifiers):
		fcurve.modifiers.remove(modifier)
	fcurve.driver.type = 'SCRIPTED'
	return fcurve

def add_bone_variable(driver, name, armature_obj, pose_bone, prop):
	"""A driver variable reading a custom property on the bone"""
	variable = driver.variables.new()
	variable.name = name
	variable.type = 'SINGLE_PROP'
	variable.targets[0].id_type = 'OBJECT'
	variable.targets[0].id = armature_obj
	variable.targets[0].data_path = bone_prop_path(pose_bone, prop)

# A control's side is one direction it moves or turns to drive keys: (axis 0-2, positive,
# channel). Each connected side has three custom properties on the control:
#   'SK +Z'      extent: how far the bone goes on that side to reach 1
#   'SK +Z Min'  the side's range bottom (below 0 takes its keys negative)
#   'SK +Z Max'  the side's range top (above 1 overshoots)
# Rotation sides have an R ('SK +RZ') and are angles.
CHANNELS = ('LOC', 'ROT')
# How rotation is read, by capture and by the drivers alike
SWING_TWIST = 'SWING_TWIST_Y'
# A turn's direction is ambiguous at 180 degrees
MAX_TURN = math.radians(179)

def side_label(axis, positive, channel):
	"""e.g. '+Z' or '-RY'"""
	return f"{'+' if positive else '-'}{'R' if channel == 'ROT' else ''}{'XYZ'[axis]}"

def extent_name(axis, positive, channel):
	"""The side's extent property, e.g. 'SK +Z'"""
	return f"SK {side_label(axis, positive, channel)}"

def range_name(axis, positive, end, channel):
	"""The side's 'Min' or 'Max' property, e.g. 'SK +Z Max'"""
	return f"{extent_name(axis, positive, channel)} {end}"

def side_prop_names(axis, positive, channel):
	"""All three properties of a side: extent, Min, Max"""
	return (extent_name(axis, positive, channel), range_name(axis, positive, "Min", channel),
		range_name(axis, positive, "Max", channel))

def set_side_props(pose_bone, axis, positive, extent, channel):
	"""Write the side's extent. Min and Max are made once (0 and 1), then left to the user"""
	prop = extent_name(axis, positive, channel)
	pose_bone[prop] = extent
	label = side_label(axis, positive, channel)
	if channel == 'ROT':
		pose_bone.id_properties_ui(prop).update(
			subtype='ANGLE', min=0.0001, max=MAX_TURN, soft_min=0.0, soft_max=math.pi / 2,
			precision=1, description=f"How far the bone turns {label} for its shape keys to reach 1")
	else:
		pose_bone.id_properties_ui(prop).update(
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

# Direction words flip with the side: the mirror of the left eye looking left is the
# right eye looking right. Lower case: chunks are matched ignoring case
_LEFT, _RIGHT = SIDE_NAMES["L"].lower(), SIDE_NAMES["R"].lower()
_MIRROR_WORDS = {_LEFT: _RIGHT, _RIGHT: _LEFT}

def _match_case(word, like):
	"""word in like's case: all lower, all upper, or proper case for anything mixed."""
	if like.islower():
		return word.lower()
	if like.isupper():
		return word.upper()
	return word.capitalize()

def mirror_shape_key_name(name):
	"""The name of this key's mirror, or None if it has none. Flips the side suffix
	(Mouth.Smile.L to Mouth.Smile.R, keeping any .001) and any whole Left/Right chunk
	(Eye.Left.L to Eye.Right.R, Mouth.Left to Mouth.Right)."""
	base_name, side = get_base_name(name)
	# The capture group keeps the separators, so joining gives back the exact name
	chunks = re.split(f"([{re.escape(SEPARATORS)}])", base_name)
	for i, chunk in enumerate(chunks):
		mirrored = _MIRROR_WORDS.get(chunk.lower())
		if mirrored:
			chunks[i] = _match_case(mirrored, chunk)
	mirrored_side = flip_side_name(side) if side else ""
	mirrored_name = "".join(chunks) + mirrored_side
	return mirrored_name if mirrored_name != name else None

def can_mirror(key, key_block):
	"""A key can be mirrored when it has a mirror name and that key, if it already
	exists, isn't locked. The Basis is the rest shape: there's nothing to mirror."""
	if key_block is None or key_block == key.reference_key:
		return False
	target_name = mirror_shape_key_name(key_block.name)
	if target_name is None:
		return False
	target = key.key_blocks.get(target_name)
	return target is None or not is_locked(target)

# Blender's own lock against accidental edits. It only stops edit and sculpt mode, not
# Python, so every tool that writes a key's coordinates checks it. Older Blenders lack it
HAS_KEY_LOCK = "lock_shape" in bpy.types.ShapeKey.bl_rna.properties

def is_locked(key_block):
	return HAS_KEY_LOCK and key_block.lock_shape

def is_side_key(name):
	return name.endswith((".L", ".R"))

def falloff_prop(source_name):
	"""ID property on the Key that remembers a source's falloff, so Update reuses it.
	Shape keys can't hold custom properties themselves."""
	return f"split_falloff:{source_name}"

def is_key_driven(key, key_block):
	"""True if the key block's value has a driver."""
	if key.animation_data is None:
		return False
	# path_from_id escapes quotes in the name: 'key_blocks["Name"].value'
	return key.animation_data.drivers.find(key_block.path_from_id("value")) is not None

def can_split(key, key_block):
	"""Driven keys can't be split: the sides are what get driven, never their source."""
	return (key_block is not None
		and key_block != key.reference_key
		and not is_side_key(key_block.name)
		and not is_key_driven(key, key_block))

def has_sides(key, source_name):
	"""True once either side exists: a source stays split even if one side was deleted
	(Update recreates it)."""
	return any(name in key.key_blocks for name in side_names(source_name))

def read_co(key_block, count):
	co = np.empty(count * 3, dtype=np.float32)
	key_block.data.foreach_get("co", co)
	return co.reshape(-1, 3)

def group_weights(obj, group_name):
	"""Per-vertex weight of a vertex group, 0 for vertices not in it."""
	weights = np.zeros(len(obj.data.vertices), dtype=np.float32)
	index = obj.vertex_groups[group_name].index
	for vertex in obj.data.vertices:
		for element in vertex.groups:
			if element.group == index:
				weights[vertex.index] = element.weight
				break
	return weights

def key_index(key, key_block):
	return list(key.key_blocks).index(key_block)

# Blender has no move-to-index for shape keys, only the shape_key_move operator, and
# every call re-evaluates the mesh with its modifiers (~0.1s on Kendra). Since 5.0 it
# moves every *selected* key, not just the active one: that lets a whole block move in
# one call, but leftover selections in a file get dragged along unless we set them.
# 4.x has no key selection and moves only the active key.
HAS_KEY_SELECT = "select" in bpy.types.ShapeKey.bl_rna.properties

def move_selected(context, obj, names, active_name, move_type):
	"""Select exactly these keys, run one shape_key_move, then restore the selection."""
	key = obj.data.shape_keys
	selected = {kb.name for kb in key.key_blocks if kb.select} if HAS_KEY_SELECT else set()
	try:
		if HAS_KEY_SELECT:
			for kb in key.key_blocks:
				kb.select = kb.name in names
		obj.active_shape_key_index = key.key_blocks.find(active_name)
		with context.temp_override(object=obj, active_object=obj):
			bpy.ops.object.shape_key_move(type=move_type)
	finally:
		if HAS_KEY_SELECT:
			for kb in key.key_blocks:
				kb.select = kb.name in selected

def move_key(context, obj, key_block, direction):
	"""Move one key one step UP or DOWN, leaving every other key where it is."""
	move_selected(context, obj, {key_block.name}, key_block.name, direction)

def place_after(context, obj, anchor, new_names):
	"""Put newly added keys (at the bottom, in order) right after the anchor key, by
	sending every other key below the anchor to the bottom in one call. Needs 5.0+;
	on 4.x the new keys stay at the bottom rather than walking up one slow step at a time."""
	if not HAS_KEY_SELECT:
		return
	key = obj.data.shape_keys
	names = [kb.name for kb in key.key_blocks]
	tail = [n for n in names[names.index(anchor.name) + 1:] if n not in new_names]
	if tail:
		move_selected(context, obj, set(tail), tail[0], 'BOTTOM')
