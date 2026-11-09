"""Reverse a shape key: fold it into the Basis and make the key take it back out.

For a key that's always on (value 1). The mesh looks the same at every value afterwards,
with the key running the other way:

	Basis' = Basis + delta * vertex group weight    (the look at the old value 1)
	key'   = Basis' - delta                         (its vertex group weights it again)
	value' = 1 - value, slider range flipped to match
	every other key keeps its own delta: it moves by whatever its relative key moved by

Keys that are driven or keyframed are refused rather than flipped: connect them afterwards.
"""
import bpy
from bpy.props import StringProperty

from rigtools.panels.shape_keys.shape_key_utils import (
	group_weights, has_sides, is_locked, is_side_key, read_co,
)

def reverse_problems(obj, key_block):
	"""Reasons this key can't be reversed exactly. Empty when it can."""
	key = obj.data.shape_keys
	if key_block == key.reference_key:
		return ["The Basis can't be reversed"]
	problems = []
	# Reverse rewrites the key and the Basis. Other keys' coordinates shift with the Basis,
	# but what they do is unchanged, so their locks don't matter
	if is_locked(key_block):
		problems.append("it's locked")
	if is_locked(key.reference_key):
		problems.append(f"the Basis '{key.reference_key.name}' is locked")
	if obj.library or obj.data.library:
		problems.append("the mesh is linked from another file")
	if not key.use_relative:
		problems.append("the mesh uses absolute shape keys")
	if key_block.relative_key != key.reference_key:
		problems.append(f"it's relative to '{key_block.relative_key.name}', not the Basis")
	if key_block.mute:
		problems.append("it's muted, so it isn't part of the current look")
	if key_block.vertex_group and key_block.vertex_group not in obj.vertex_groups:
		problems.append(f"its vertex group '{key_block.vertex_group}' doesn't exist")
	anim = key.animation_data
	if anim and anim.drivers.find(key_block.path_from_id("value")):
		problems.append("it's driven: remove the driver, reverse, then connect it again")
	if anim and (anim.action or anim.nla_tracks):
		problems.append("this mesh's shape keys have keyframes")
	if has_sides(key, key_block.name):
		problems.append("it has split sides: reverse it before splitting, or delete the sides")
	if is_side_key(key_block.name) and key_block.name[:-2] in key.key_blocks:
		problems.append(f"it's a split side of '{key_block.name[:-2]}', and Update would overwrite it")
	return problems

class RIG_OT_reverse_shape_key(bpy.types.Operator):
	bl_idname = "rig.reverse_shape_key"
	bl_label = "Reverse Shape Key"
	bl_description = ("Fold this key into the Basis and make it take its shape back out, so 0 is "
		"the current look. The mesh looks the same at every value")
	bl_options = {'REGISTER', 'UNDO'}

	object_name: StringProperty(options={'HIDDEN'})
	shape_key_name: StringProperty(options={'HIDDEN'})

	def execute(self, context):
		obj = bpy.data.objects.get(self.object_name)
		key = obj.data.shape_keys if obj and obj.type == 'MESH' else None
		key_block = key.key_blocks.get(self.shape_key_name) if key else None
		if key_block is None:
			self.report({'ERROR'}, f"No shape key '{self.shape_key_name}' on '{self.object_name}'")
			return {'CANCELLED'}
		problems = reverse_problems(obj, key_block)
		if problems:
			self.report({'ERROR'}, f"Can't reverse '{key_block.name}': {'; '.join(problems)}")
			return {'CANCELLED'}

		# Edits made in edit mode only reach the keys once edit mode is left
		was_editing = obj.mode == 'EDIT'
		if was_editing:
			with context.temp_override(object=obj, active_object=obj):
				bpy.ops.object.mode_set(mode='OBJECT')

		count = len(obj.data.vertices)
		basis = key.reference_key
		coords = {kb.name: read_co(kb, count) for kb in key.key_blocks}
		delta = coords[key_block.name] - coords[basis.name]
		if key_block.vertex_group:
			applied = delta * group_weights(obj, key_block.vertex_group)[:, None]
		else:
			applied = delta

		# How far each key's reference moves; every other key moves with its reference, so
		# what it does to the mesh is unchanged. The key itself becomes Basis' - delta
		shift = {basis.name: applied, key_block.name: applied - 2 * delta}
		def shift_of(kb, seen=()):
			if kb.name not in shift:
				# A relative-key loop can't be resolved: leave the loop's keys alone
				shift[kb.name] = 0 if kb.name in seen else shift_of(kb.relative_key, seen + (kb.name,))
			return shift[kb.name]

		for kb in key.key_blocks:
			kb.data.foreach_set("co", (coords[kb.name] + shift_of(kb)).ravel())
		# Outside edit mode the mesh's own positions are the Basis; keep them in step
		obj.data.vertices.foreach_set("co", (coords[basis.name] + applied).ravel())

		# Value v before looks the same as 1 - v after
		old_min, old_max = key_block.slider_min, key_block.slider_max
		key_block.slider_min, key_block.slider_max = 1 - old_max, 1 - old_min
		key_block.value = 1 - key_block.value
		obj.data.update()

		if was_editing:
			with context.temp_override(object=obj, active_object=obj):
				bpy.ops.object.mode_set(mode='EDIT')

		self.report({'INFO'}, f"Reversed '{key_block.name}'")
		return {'FINISHED'}

def draw_menu_item(self, context):
	"""Reverse in Blender's Shape Key Specials menu (the ▾ under the list). Rarely used, so
	it lives there rather than as a button. Our panel's ▾ sets context.object to its mesh."""
	obj = context.object
	if obj is None or obj.type != 'MESH' or obj.active_shape_key is None:
		return
	layout = self.layout
	layout.separator()
	# Always enabled: if it can't be reversed, clicking says why
	op = layout.operator("rig.reverse_shape_key", text="Reverse Shape Key", icon='ARROW_LEFTRIGHT')
	op.object_name = obj.name
	op.shape_key_name = obj.active_shape_key.name

classes = (
	RIG_OT_reverse_shape_key,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	bpy.types.MESH_MT_shape_key_context_menu.append(draw_menu_item)

def unregister():
	bpy.types.MESH_MT_shape_key_context_menu.remove(draw_menu_item)
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
