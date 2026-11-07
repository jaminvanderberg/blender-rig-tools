import bpy

def get_controlled_meshes(armature_obj, context):
	"""Meshes with shape keys and an armature modifier using this rig."""
	meshes = []
	for obj in context.scene.objects:
		if obj.type != 'MESH' or not obj.data.shape_keys:
			continue
		for modifier in obj.modifiers:
			if modifier.type == 'ARMATURE' and modifier.object == armature_obj:
				meshes.append(obj)
				break
	return meshes

class RIG_UL_shape_keys(bpy.types.UIList):
	def draw_item(self, context, layout, shape_keys, shape_key, icon_value, active_data,
			active_propname, index):
		# data is the mesh's Key, item is one of its key_blocks
		row = layout.row(align=True)
		split = row.split(factor=0.65, align=False)
		split.prop(shape_key, "name", text="", emboss=False, icon='SHAPEKEY_DATA')
		split.prop(shape_key, "value", text="", emboss=False)
		# active_data is the mesh object passed to template_list
		op = row.operator("rig.connect_shape_key", text="The", emboss=False, icon='DRIVER')
		op.object_name = active_data.name
		op.shape_key_name = shape_key.name

class RIG_PT_shape_keys(bpy.types.Panel):
	bl_label = "Shape Keys"
	bl_idname = "RIG_PT_shape_keys"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = "Rig Tools"

	@classmethod
	def poll(cls, context):
		return (
			context.object
			and context.object.type == 'ARMATURE'
			and context.mode == 'POSE'
		)

	def draw(self, context):
		layout = self.layout
		meshes = get_controlled_meshes(context.object, context)
		if not meshes:
			layout.label(text="No meshes with shape keys use this rig")
			return

		for obj in meshes:
			header, body = layout.panel(
				f"RIG_shape_keys_{obj.name}", default_closed=False
			)
			header.label(text=obj.name, icon='MESH_DATA')
			if body is None:
				continue
			# The list id has to be unique per object, or every list
			# shares one scroll position and filter
			body.template_list(
				"RIG_UL_shape_keys", obj.name,
				obj.data.shape_keys, "key_blocks",
				obj, "active_shape_key_index",
				rows=6,
			)

classes = (
	RIG_UL_shape_keys,
	RIG_PT_shape_keys,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
