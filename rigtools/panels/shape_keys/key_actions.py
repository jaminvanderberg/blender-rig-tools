"""Small per-key actions: Remove and Move (the buttons under the list), and Apply Vertex Group.
Remove and Move are our own versions, because Blender's act on every *selected* key (5.0+),
Basis included."""
import bpy
from bpy.props import EnumProperty, StringProperty

from rigtools.panels.shape_keys.shape_key_utils import group_weights, key_index, move_key, read_co

class RIG_OT_remove_shape_key(bpy.types.Operator):
	bl_idname = "rig.remove_shape_key"
	bl_label = "Remove Shape Key"
	bl_description = "Remove this shape key. Basis can't be removed here"
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
		if key_block == key.reference_key:
			self.report({'ERROR'}, f"'{key_block.name}' is the Basis; not removed")
			return {'CANCELLED'}
		if obj.mode == 'EDIT':
			self.report({'ERROR'}, "Leave edit mode first")
			return {'CANCELLED'}

		index = key_index(key, key_block)
		obj.shape_key_remove(key_block)
		obj.active_shape_key_index = max(1, index - 1)
		self.report({'INFO'}, f"Removed '{self.shape_key_name}' from '{obj.name}'")
		return {'FINISHED'}

class RIG_OT_move_shape_key(bpy.types.Operator):
	bl_idname = "rig.move_shape_key"
	bl_label = "Move Shape Key"
	bl_description = "Move this shape key up or down. Basis stays first"
	bl_options = {'REGISTER', 'UNDO'}

	object_name: StringProperty(options={'HIDDEN'})
	shape_key_name: StringProperty(options={'HIDDEN'})
	direction: EnumProperty(
		items=[('UP', "Up", ""), ('DOWN', "Down", "")],
		options={'HIDDEN'},
	)

	def execute(self, context):
		obj = bpy.data.objects.get(self.object_name)
		key = obj.data.shape_keys if obj and obj.type == 'MESH' else None
		key_block = key.key_blocks.get(self.shape_key_name) if key else None
		if key_block is None or key_block == key.reference_key:
			return {'CANCELLED'}
		if obj.mode == 'EDIT':
			self.report({'ERROR'}, "Leave edit mode first")
			return {'CANCELLED'}
		index = key_index(key, key_block)
		# Index 1 moving up would become the new Basis
		if (self.direction == 'UP' and index <= 1) or (
				self.direction == 'DOWN' and index >= len(key.key_blocks) - 1):
			return {'CANCELLED'}
		move_key(context, obj, key_block, self.direction)
		return {'FINISHED'}

class RIG_OT_apply_shape_key_vertex_group(bpy.types.Operator):
	bl_idname = "rig.apply_shape_key_vertex_group"
	bl_label = "Apply Vertex Group"
	bl_description = ("Bake the vertex group into this key and clear it: anything the group "
		"hides is removed for good. The mesh looks the same")
	bl_options = {'REGISTER', 'UNDO'}

	object_name: StringProperty(options={'HIDDEN'})
	shape_key_name: StringProperty(options={'HIDDEN'})

	def execute(self, context):
		obj = bpy.data.objects.get(self.object_name)
		key = obj.data.shape_keys if obj and obj.type == 'MESH' else None
		key_block = key.key_blocks.get(self.shape_key_name) if key else None
		if key_block is None or key_block == key.reference_key:
			return {'CANCELLED'}
		if key_block.vertex_group not in obj.vertex_groups:
			self.report({'ERROR'}, f"'{key_block.name}' has no vertex group to apply")
			return {'CANCELLED'}

		# Edits made in edit mode only reach the keys once edit mode is left
		was_editing = obj.mode == 'EDIT'
		if was_editing:
			with context.temp_override(object=obj, active_object=obj):
				bpy.ops.object.mode_set(mode='OBJECT')

		count = len(obj.data.vertices)
		current = read_co(key_block, count)
		relative = read_co(key_block.relative_key, count)
		weights = group_weights(obj, key_block.vertex_group)[:, None]
		applied = relative + (current - relative) * weights
		change = applied - current
		key_block.data.foreach_set("co", applied.ravel())
		# Keys built on this one (relative to it, directly or down a chain) move with it,
		# so what they do is unchanged
		for kb in key.key_blocks:
			seen, ref = set(), kb.relative_key
			while kb != key_block and ref != key.reference_key and ref.name not in seen:
				if ref == key_block:
					kb.data.foreach_set("co", (read_co(kb, count) + change).ravel())
					break
				seen.add(ref.name)
				ref = ref.relative_key
		group = key_block.vertex_group
		key_block.vertex_group = ""
		obj.data.update()

		if was_editing:
			with context.temp_override(object=obj, active_object=obj):
				bpy.ops.object.mode_set(mode='EDIT')
		self.report({'INFO'}, f"Applied '{group}' to '{key_block.name}'")
		return {'FINISHED'}

classes = (
	RIG_OT_remove_shape_key,
	RIG_OT_move_shape_key,
	RIG_OT_apply_shape_key_vertex_group,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
