import bpy
from rigtools.utils.object import get_controlled_meshes, get_rig, sort_by_order
from rigtools.panels.shape_keys.shape_key_utils import can_split, falloff_prop, has_sides, is_key_driven
from rigtools.panels.shape_keys.connect import connections

class RIG_UL_shape_keys(bpy.types.UIList):
	
	def draw_item(self, context, layout, shape_keys, shape_key, icon_value, active_data,
			active_propname, index):
		# data is the mesh's Key, item is one of its key_blocks
		row = layout.row(align=True)
		split = row.split(factor=0.70, align=False)
		split.prop(shape_key, "name", text="", emboss=False, icon='SHAPEKEY_DATA')
		# Basis is the rest shape: its value does nothing and it can't be connected
		if shape_key == shape_keys.reference_key:
			split.label(text="")
			row.label(text="", icon='LOCKED')
			return
		# Only the slider is disabled; Connect still works on driven keys
		value_row = split.row()
		value_row.enabled = not is_key_driven(shape_keys, shape_key)
		value_row.prop(shape_key, "value", text="", emboss=False)
		# A split source is a sculpting template that stays at 0: its sides get connected.
		# A blank keeps the rows lined up
		if has_sides(shape_keys, shape_key.name):
			row.label(text="", icon='BLANK1')
			return
		# active_data is the mesh object passed to template_list
		op = row.operator("rig.connect_shape_key", text="", icon='DRIVER')
		op.object_name = active_data.name
		op.shape_key_name = shape_key.name


def draw_key_buttons(layout, obj):
	"""Pin, Edit Key and Sculpt Key for the mesh's active shape key."""
	row = layout.row(align=True)
	row.alignment = 'RIGHT'
	# Blender's own pin: show the active key alone (ignored in edit mode)
	row.prop(obj, "show_only_shape_key", text="")

	sub = row.row(align=True)
	sub.enabled = obj.active_shape_key is not None
	for target, icon, mode in (('KEY_EDIT', 'EDITMODE_HLT', 'EDIT'), ('KEY_SCULPT', 'SCULPTMODE_HLT', 'SCULPT')):
		op = sub.operator("rig.switch_mode", text="", icon=icon, depress=obj.mode == mode)
		op.target = target
		op.mesh_name = obj.name

def draw_key_actions(layout, obj):
	"""Add/remove/menu/move buttons for this mesh's keys, in a row under its list.
	Blender's operators act on context.object, so override it for these buttons: they
	then work from pose mode with the rig active, without selecting the mesh."""
	row = layout.row()
	row.context_pointer_set("object", obj)
	active = obj.active_shape_key
	# Removing or moving Basis promotes another key to Basis and wrecks every shape
	not_basis = active is not None and active != obj.data.shape_keys.reference_key

	edit = row.row(align=True)
	edit.operator("object.shape_key_add", icon='ADD', text="").from_mix = False
	remove = edit.row(align=True)
	remove.enabled = not_basis
	# Our own operator: the mesh and key are passed explicitly, never inferred from context
	op = remove.operator("rig.remove_shape_key", icon='REMOVE', text="")
	op.object_name = obj.name
	op.shape_key_name = active.name if active else ""
	edit.menu("MESH_MT_shape_key_context_menu", icon='DOWNARROW_HLT', text="")

	move = row.row(align=True)
	move.alignment = 'RIGHT'
	move.enabled = not_basis
	# Moving up from just below Basis would make this key the new Basis
	up = move.row(align=True)
	up.enabled = obj.active_shape_key_index > 1
	# Our own operator: Blender's moves every *selected* key (5.0+), not just this one
	for layout_, direction, icon in ((up, 'UP', 'TRIA_UP'), (move, 'DOWN', 'TRIA_DOWN')):
		op = layout_.operator("rig.move_shape_key", icon=icon, text="")
		op.object_name = obj.name
		op.shape_key_name = active.name if active else ""
		op.direction = direction

def draw_active_key(layout, obj):
	"""Settings and actions for the mesh's active key, below its list.
	Blender's property layout: labels on the left, fields and buttons lined up on the right."""
	key = obj.data.shape_keys
	key_block = obj.active_shape_key
	if key_block is None or key_block == key.reference_key:
		return

	layout.separator()
	col = layout.column()
	col.use_property_split = True
	col.use_property_decorate = False
	# Limits the key to part of the mesh, so stray edits elsewhere do nothing.
	# Split and Reverse (in the ▾ menu) both respect it
	row = col.row(align=True)
	row.prop_search(key_block, "vertex_group", obj, "vertex_groups", text="Vertex Group")
	# Bake it in and clear it: for cleaning up stray edits for good
	apply = row.row(align=True)
	apply.enabled = key_block.vertex_group in obj.vertex_groups
	op = apply.operator("rig.apply_shape_key_vertex_group", text="", icon='CHECKMARK')
	op.object_name = obj.name
	op.shape_key_name = key_block.name

	if can_split(key, key_block):
		col.separator()
		split_exists = has_sides(key, key_block.name)
		op = col.operator(
			"rig.split_shape_key",
			text="Update L/R Shape Keys" if split_exists else "Create L/R Shape Keys",
			icon='FILE_REFRESH' if split_exists else 'MOD_MIRROR',
		)
		op.object_name = obj.name
		op.shape_key_name = key_block.name
		# Stored by the first split; editing it takes effect on the next Update
		prop = falloff_prop(key_block.name)
		if prop in key:
			col.prop(key, f'["{bpy.utils.escape_identifier(prop)}"]', text="Falloff")

	# The bones driving this key, each with a button to disconnect it
	rig = obj.find_armature()
	found = connections(rig, key_block.name) if rig else []
	if not found:
		return
	layout.separator()
	layout.label(text="Connections")
	col = layout.column(align=True)
	for variable, bone, axis, extreme, inverted in found:
		row = col.row()
		op = row.operator("rig.select_control", text=bone, icon='BONE_DATA', emboss=False, translate=False)
		op.rig_name = rig.name
		op.bone_name = bone
		right = row.row()
		right.alignment = 'RIGHT'
		# The direction the bone moves to reach the shape, e.g. -Z
		right.label(text=f"{'+' if extreme > 0 else '-'}{axis}", icon='ARROW_LEFTRIGHT' if inverted else 'NONE')
		op = right.operator("rig.disconnect_shape_key", text="", icon='X', emboss=False)
		op.rig_name = rig.name
		op.shape_key_name = key_block.name
		op.variable = variable

class RIG_PT_shape_keys(bpy.types.Panel):
	bl_label = "Shape Keys"
	bl_idname = "RIG_PT_shape_keys" 
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = "Rig Tools"

	@classmethod
	def poll(cls, context):
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
			row = layout.row()
			row.label(text=context.object.name, icon='MESH_DATA')
			draw_key_buttons(row, context.object)
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
			draw_key_buttons(header, obj)
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
		draw_key_actions(layout, obj)
		draw_active_key(layout, obj)

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
