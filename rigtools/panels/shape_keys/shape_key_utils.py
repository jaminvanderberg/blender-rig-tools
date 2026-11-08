"""Shared helpers for the shape key tools: side naming, key data, and moving keys."""
import bpy
import numpy as np

def side_names(name):
	return f"{name}.L", f"{name}.R"

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
