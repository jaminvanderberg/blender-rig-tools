import bpy
from rigtools.utils.object import get_controlled_meshes, get_rig, sort_by_order
from rigtools.panels.shape_keys.shape_key_utils import (
	HAS_KEY_LOCK, can_mirror, can_split, falloff_prop, has_sides, is_key_driven, mirror_shape_key_name,
)
from rigtools.panels.shape_keys.connect import drive_slider, limit_constraint, side_name
from rigtools.rig_data.shape_key_connections import find_bone_connections_for_shape_key

class RIG_UL_active_bone_connections(bpy.types.UIList):
	"""The active bone's connection records: one row per shape key it drives, and from which side."""

	def draw_item(self, context, layout, connections, connection, icon, active_data,
			active_propname, index):
		armature_obj = connection.id_data
		pose_bone = context.active_pose_bone
		row = layout.row(align=True)
		row.label(text=connection.key_name, icon='SHAPEKEY_DATA', translate=False)
		right = row.row(align=True)
		right.alignment = 'RIGHT'
		# Which mesh, since the same key name can be on several
		right.label(text=connection.mesh.name if connection.mesh else "(no mesh)", translate=False)
		right.label(text=f"{'+' if connection.positive else '-'}{connection.axis}")
		right.separator()
		op = right.operator("rig.disconnect_shape_key", text="", icon='X', emboss=True)
		op.armature_name = armature_obj.name
		op.bone_name = pose_bone.name
		op.object_name = connection.mesh.name if connection.mesh else ""
		op.shape_key_name = connection.key_name
		op.axis = connection.axis
		op.positive = connection.positive

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
			self.draw_lock(row, shape_key)
			row.label(text="", icon='BLANK1')
			return
		# Only the slider is disabled; Connect still works on driven keys
		value_row = split.row()
		value_row.enabled = not is_key_driven(shape_keys, shape_key)
		value_row.prop(shape_key, "value", text="", emboss=False)
		self.draw_lock(row, shape_key)
		# A split source is a sculpting template that stays at 0: its sides get connected.
		# A blank keeps the rows lined up
		if has_sides(shape_keys, shape_key.name):
			row.label(text="", icon='BLANK1')
			return
		# active_data is the mesh object passed to template_list
		op = row.operator("rig.connect_shape_key", text="", icon='DRIVER')
		op.object_name = active_data.name
		op.shape_key_name = shape_key.name

	@staticmethod
	def draw_lock(row, shape_key):
		"""Blender's own lock: protects the key from editing, sculpting and our tools.
		Its property defines the locked/unlocked icons, as in Blender's own list"""
		if HAS_KEY_LOCK:
			row.prop(shape_key, "lock_shape", text="", emboss=False)

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

	# Shown whenever the key has a mirror; greyed out while that key is locked
	mirror_name = mirror_shape_key_name(key_block.name)
	if mirror_name:
		col.separator()
		row = col.row()
		row.enabled = can_mirror(key, key_block)
		op = row.operator("rig.mirror_shape_key", text=f"Mirror to {mirror_name}",
			icon='MOD_MIRROR', translate=False)
		op.object_name = obj.name
		op.shape_key_name = key_block.name

	# The bones recorded as driving this key, each with a button to disconnect it
	armature_obj = obj.find_armature()
	found = find_bone_connections_for_shape_key(armature_obj, obj, key_block.name) if armature_obj else []
	if not found:
		return
	layout.separator()
	layout.label(text="Connections")
	col = layout.column(align=True)
	for pose_bone, connection in found:
		row = col.row()
		op = row.operator("rig.select_control", text=pose_bone.name, icon='BONE_DATA',
			emboss=False, translate=False)
		op.armature_name = armature_obj.name
		op.bone_name = pose_bone.name
		right = row.row()
		right.alignment = 'RIGHT'
		# The direction the bone moves to reach the shape, e.g. -Z
		right.label(text=f"{'+' if connection.positive else '-'}{connection.axis}")
		op = right.operator("rig.disconnect_shape_key", text="", icon='X', emboss=False)
		op.armature_name = armature_obj.name
		op.bone_name = pose_bone.name
		op.object_name = obj.name
		op.shape_key_name = key_block.name
		op.axis = connection.axis
		op.positive = connection.positive

def draw_active_bone(layout, armature_obj, pose_bone):
	"""What the active control drives, as a list of its connection records, with the selected
	connection's settings underneath."""
	sk_connections = pose_bone.rigtools_shape_keys
	if not sk_connections.items:
		return
	row = layout.row()
	row.label(text=pose_bone.name, icon='BONE_DATA', translate=False)
	# Limits are per bone: unlock to pose past them, Connect locks them again
	constraint = limit_constraint(pose_bone)
	if constraint:
		right = row.row()
		right.alignment = 'RIGHT'
		# A toggle shows the icon after the given one when on: UNLOCKED, then LOCKED
		right.prop(constraint, "enabled", text="Limited" if constraint.enabled else "Unlocked",
			icon='UNLOCKED', emboss=False)

	layout.template_list(
		"RIG_UL_active_bone_connections", "",
		sk_connections, "items",
		sk_connections, "active_index",
		rows=3,
	)

	# The selected connection's settings. The extent belongs to the side, shared by every
	# key connected on it
	index = sk_connections.active_index
	if not 0 <= index < len(sk_connections.items):
		return
	connection = sk_connections.items[index]
	axis = "XYZ".index(connection.axis)
	col = layout.column()
	col.use_property_split = True
	col.use_property_decorate = False
	prop = side_name(axis, connection.positive)
	if prop in pose_bone:
		col.prop(pose_bone, drive_slider(axis, connection.positive), text="Extent")

	# The shape key's own Range. Its max sets how far the bone travels: extent x max, so 1.2
	# lets the key reach 1.2. It belongs to the key, so every bone driving it follows it
	key = connection.mesh.data.shape_keys if connection.mesh else None
	key_block = key.key_blocks.get(connection.key_name) if key else None
	if key_block:
		row = col.row(align=True)
		row.prop(key_block, "slider_min", text="Range")
		row.prop(key_block, "slider_max", text="")
	layout.separator()

class RIG_PT_shape_keys(bpy.types.Panel):
	bl_label = "Shape Keys"
	bl_idname = "RIG_PT_shape_keys" 
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = "Rig Tools"

	@classmethod
	def poll(cls, context):
		armature_obj = get_rig(context)
		if armature_obj is None:
			return False
		meshes = get_controlled_meshes(armature_obj, context.view_layer)
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

		# Posing: what the active control drives, above the meshes
		armature_obj = context.object
		if armature_obj.mode == 'POSE' and context.active_pose_bone is not None:
			draw_active_bone(layout, armature_obj, context.active_pose_bone)

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
	RIG_UL_active_bone_connections,
	RIG_UL_shape_keys,
	RIG_PT_shape_keys,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
