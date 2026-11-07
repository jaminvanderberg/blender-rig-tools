import bpy
from rigtools.utils.object import get_controlled_meshes, get_rig, sort_by_order

def is_key_driven(key, key_block):
	"""True if the key block's value has a driver."""
	if key.animation_data is None:
		return False
	# path_from_id escapes quotes in the name: 'key_blocks["Name"].value'
	return key.animation_data.drivers.find(key_block.path_from_id("value")) is not None

class RIG_UL_shape_keys(bpy.types.UIList):
	
	def draw_item(self, context, layout, shape_keys, shape_key, icon_value, active_data,
			active_propname, index):
		# data is the mesh's Key, item is one of its key_blocks
		row = layout.row(align=True)
		split = row.split(factor=0.70, align=False)
		split.prop(shape_key, "name", text="", emboss=False, icon='SHAPEKEY_DATA')
		# Only the slider is disabled; Connect still works on driven keys
		value_row = split.row()
		value_row.enabled = not is_key_driven(shape_keys, shape_key)
		value_row.prop(shape_key, "value", text="", emboss=False)
		# active_data is the mesh object passed to template_list
		op = row.operator("rig.connect_shape_key", text="", icon='DRIVER')
		op.object_name = active_data.name
		op.shape_key_name = shape_key.name

	def filter_items(self, context, data, propname):
		key_blocks = getattr(data, propname)
		helper = bpy.types.UI_UL_list
		if self.filter_name:
			flags = helper.filter_items_by_name(
				self.filter_name, self.bitflag_filter_item, key_blocks, "name",
				reverse=self.use_filter_invert)
		else:
			flags = [self.bitflag_filter_item] * len(key_blocks)

		for i, kb in enumerate(key_blocks):
			if kb == data.reference_key: # Basis
				flags[i] &= ~self.bitflag_filter_item

		order = helper.sort_items_by_name(key_blocks, "name") if self.use_filter_sort_alpha else []
		return flags, order


class RIG_PT_shape_keys(bpy.types.Panel):
	bl_label = "Shape Keys"
	bl_idname = "RIG_PT_shape_keys" 
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = "Rig Tools"

	@classmethod
	def poll(cls, context):
		return False  # Temp for version 0.9.0
		rig = get_rig(context)
		if rig is None:
			return False
		meshes = get_controlled_meshes(rig, context.view_layer)
		if context.object.type == 'MESH':
			return context.object in meshes
		return bool(meshes)

	def draw(self, context):
		layout = self.layout
		meshes = sort_by_order(get_controlled_meshes(get_rig(context), context.view_layer))

		# A mesh is active: show only its keys, no sub-panel
		if context.object.type == 'MESH':
			if context.object not in meshes:
				layout.label(text="This mesh has no shape keys")
				return
			self.draw_list(layout, context.object)
			return

		# The rig is active: one collapsible sub-panel per mesh
		if not meshes:
			layout.label(text="No meshes with shape keys use this rig") 
			return
		for obj in meshes:
			header, body = layout.panel(
				f"RIG_shape_keys_{obj.name}", default_closed=False
			)
			header.label(text=obj.name, icon='MESH_DATA')
			if body is not None:
				self.draw_list(body, obj)

	def draw_list(self, layout, obj):
		# The list id has to be unique per object, or every list
		# shares one scroll position and filter
		layout.template_list(
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
