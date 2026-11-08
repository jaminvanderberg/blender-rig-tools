import bpy
from rigtools.rig_ui.rig_ui import get_related_meshes
from rigtools.utils.bone import select_bones
from rigtools.utils.bone_chain import find_connected_chains
from rigtools.utils.object import get_rig, sort_by_order

###############################################################################
# MODE SWITCHING

def _make_active(context, obj, also_select=()):
	"""Leave the current mode, then make obj the only selected, active object.
	Returns an error message, or None."""
	view_layer = context.view_layer
	for other in (obj, *also_select):
		if view_layer.objects.get(other.name) is None:
			return f"'{other.name}' is not in the active view layer"
		# Unhide the eye toggle; other kinds of hiding are the user's call
		if other.hide_get(view_layer=view_layer):
			other.hide_set(False, view_layer=view_layer)
		if not other.visible_get(view_layer=view_layer):
			return f"'{other.name}' is hidden (viewport or collection)"

	if context.object and context.object.mode != 'OBJECT':
		bpy.ops.object.mode_set(mode='OBJECT')
	for selected in context.selected_objects:
		selected.select_set(False)
	for other in (obj, *also_select):
		other.select_set(True)
	view_layer.objects.active = obj
	return None

_SWITCH_TARGETS = [
	('RIG_OBJECT', "Rig Object", "Object mode on the rig"),
	('RIG_EDIT', "Rig Edit", "Edit mode on the rig"),
	('RIG_POSE', "Rig Pose", "Pose mode on the rig"),
	('MESH_OBJECT', "Select Mesh", "Make the mesh active, in object mode"),
	('MESH_EDIT', "Mesh Edit", "Edit mode on the mesh"),
	('MESH_WEIGHT', "Weight Paint", "Weight paint the mesh, with the rig's bones selectable"),
	('KEY_EDIT', "Edit Shape Key", "Edit the mesh's active shape key in edit mode"),
	('KEY_SCULPT', "Sculpt Shape Key", "Sculpt the mesh's active shape key"),
]

_MESH_MODES = {
	'MESH_OBJECT': 'OBJECT', 'MESH_EDIT': 'EDIT', 'MESH_WEIGHT': 'WEIGHT_PAINT',
	'KEY_EDIT': 'EDIT', 'KEY_SCULPT': 'SCULPT',
}

class RIG_OT_switch_mode(bpy.types.Operator):
	bl_idname = "rig.switch_mode"
	bl_label = "Switch Mode"
	bl_description = "Switch to this mode, on the rig or the active mesh"
	bl_options = {'REGISTER', 'UNDO'}

	target: bpy.props.EnumProperty(items=_SWITCH_TARGETS, options={'HIDDEN'})
	mesh_name: bpy.props.StringProperty(options={'HIDDEN'})

	@staticmethod
	def _is_toggle_off(context, target, mesh_name):
		"""Clicking a mesh mode button you're already in goes back to the rig's pose mode."""
		obj = context.object
		mode = _MESH_MODES.get(target)
		return (mode not in (None, 'OBJECT')
			and obj is not None and obj.name == mesh_name and obj.mode == mode)

	@classmethod
	def description(cls, context, properties):
		if cls._is_toggle_off(context, properties.target, properties.mesh_name):
			return "Back to pose mode on the rig"
		for identifier, _, desc in _SWITCH_TARGETS:
			if identifier == properties.target:
				return desc
		return cls.bl_description

	@classmethod
	def poll(cls, context):
		return get_rig(context) is not None

	def execute(self, context):
		rig = get_rig(context)

		if self._is_toggle_off(context, self.target, self.mesh_name):
			self.target = 'RIG_POSE'

		if self.target in _MESH_MODES:
			mesh = bpy.data.objects.get(self.mesh_name)
			if mesh is None:
				self.report({'ERROR'}, f"Mesh '{self.mesh_name}' not found")
				return {'CANCELLED'}
			# Weight paint selects the rig too: Blender then puts it in pose mode,
			# so clicking a bone picks its vertex group
			also_select = (rig,) if self.target == 'MESH_WEIGHT' else ()
			error = _make_active(context, mesh, also_select=also_select)
			if error:
				self.report({'ERROR'}, error)
				return {'CANCELLED'}
			if _MESH_MODES[self.target] != 'OBJECT':
				bpy.ops.object.mode_set(mode=_MESH_MODES[self.target])
			return {'FINISHED'}

		error = _make_active(context, rig)
		if error:
			self.report({'ERROR'}, error)
			return {'CANCELLED'}
		mode = {'RIG_OBJECT': 'OBJECT', 'RIG_EDIT': 'EDIT', 'RIG_POSE': 'POSE'}[self.target]
		if mode != 'OBJECT':
			bpy.ops.object.mode_set(mode=mode)
		return {'FINISHED'}

class RIG_OT_toggle_hide(bpy.types.Operator): 
	bl_idname = "rig.toggle_hide"
	bl_label = "Toggle Visibility"
	bl_description = "Hide or show this object in the viewport"
	bl_options = {'REGISTER', 'UNDO'}

	obj_name: bpy.props.StringProperty(options={'HIDDEN'})

	def execute(self, context):
		view_layer = context.view_layer
		obj = view_layer.objects.get(self.obj_name)
		if obj is None:
			self.report({'ERROR'}, f"'{self.obj_name}' is not in the active view layer")
			return {'CANCELLED'}
		if obj == context.object and obj.mode != 'OBJECT':
			self.report({'ERROR'}, f"Can't hide '{obj.name}' while it's in {obj.mode.title()} mode")
			return {'CANCELLED'}
		obj.hide_set(not obj.hide_get(view_layer=view_layer), view_layer=view_layer)
		return {'FINISHED'}

###############################################################################
# MESH ORDER

def _ordered_meshes(rig, view_layer):
	return sort_by_order(get_related_meshes(rig, view_layer))

class RIG_OT_move_mesh(bpy.types.Operator):
	bl_idname = "rig.move_mesh"
	bl_label = "Move Mesh"
	bl_description = "Move this mesh up or down in the rig's mesh lists"
	bl_options = {'REGISTER', 'UNDO'}

	mesh_name: bpy.props.StringProperty(options={'HIDDEN'})
	direction: bpy.props.EnumProperty(
		items=[('UP', "Up", ""), ('DOWN', "Down", "")],
		options={'HIDDEN'},
	)

	@classmethod
	def poll(cls, context):
		return get_rig(context) is not None

	def execute(self, context):
		meshes = _ordered_meshes(get_rig(context), context.view_layer)
		names = [mesh.name for mesh in meshes]
		if self.mesh_name not in names:
			return {'CANCELLED'}
		i = names.index(self.mesh_name)
		j = i - 1 if self.direction == 'UP' else i + 1
		if not 0 <= j < len(meshes):
			return {'CANCELLED'}
		meshes[i], meshes[j] = meshes[j], meshes[i]
		# Renumber the whole list, so meshes that were never ordered (all 0) get a place
		for order, mesh in enumerate(meshes):
			mesh.rigtools_order = order
		return {'FINISHED'}

###############################################################################
# SELECTION

class RIG_OT_select_chains(bpy.types.Operator):
	bl_idname = "rig.select_chains"
	bl_label = "Select Connected"
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		names = find_connected_chains(context)
		select_bones(context.object, names, select_hidden=False)

		return {'FINISHED'}

class RIG_OT_select_mirror(bpy.types.Operator):
	bl_idname = "rig.select_mirror"
	bl_label = "Select Mirror"
	bl_description = "Extend the selection to include each bone's opposite-side counterpart"
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		obj = context.object
		if not obj or obj.type != 'ARMATURE':
			self.report({'ERROR'}, "Active object must be an armature.")
			return {'CANCELLED'}

		if obj.mode == 'POSE':
			bpy.ops.pose.select_mirror(extend=True)
		elif obj.mode == 'EDIT':
			bpy.ops.armature.select_mirror(extend=True)
		else:
			self.report({'ERROR'}, "Use from Pose or Edit mode.")
			return {'CANCELLED'}

		return {'FINISHED'}

###############################################################################
# PANEL

def _mode_button(layout, target, icon, active, mesh_name=""):
	op = layout.operator("rig.switch_mode", text="", icon=icon, depress=active)
	op.target = target
	op.mesh_name = mesh_name

def _hide_button(layout, obj, view_layer):
	hidden = obj.hide_get(view_layer=view_layer)
	op = layout.operator(
		"rig.toggle_hide", text="",
		icon='HIDE_ON' if hidden else 'HIDE_OFF', emboss=False,
	)
	op.obj_name = obj.name

class RIG_PT_armature(bpy.types.Panel):
	bl_label = "Armature"
	bl_idname = "RIG_PT_armature"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = "Rig Tools"

	@classmethod
	def poll(cls, context):
		return get_rig(context) is not None

	def draw(self, context):
		layout = self.layout
		rig = get_rig(context)
		obj = context.object
		rig_active = obj == rig

		if not rig_active:
			layout.label(text=rig.name)

		row = layout.row(align=True)
		row.prop(rig.data, "pose_position", expand=True)

		row.separator()
		modes = row.row(align=True)
		if rig_active:
			_mode_button(modes, 'RIG_OBJECT', 'OBJECT_DATAMODE', rig.mode == 'OBJECT')
			_mode_button(modes, 'RIG_EDIT', 'EDITMODE_HLT', rig.mode == 'EDIT')
			_mode_button(modes, 'RIG_POSE', 'POSE_HLT', rig.mode == 'POSE')
		else:
			_mode_button(modes, 'RIG_EDIT', 'EDITMODE_HLT', False)
			_mode_button(modes, 'RIG_POSE', 'POSE_HLT', False)
			_hide_button(row, rig, context.view_layer)

		if rig_active:
			header, body = layout.panel(
				f"RIG_connected_meshes_{obj.name}", default_closed=False
			)
			header.label(text="Meshes")
			reorder = context.window_manager.rigtools_reorder_meshes
			if body is not None:
				# Reorder button
				header.prop(
					context.window_manager, "rigtools_reorder_meshes",
					text="", icon='SORTSIZE', emboss=True,
				)

				col = body.column(align=True)
				for mesh_obj in _ordered_meshes(rig, context.view_layer):
					row = col.row(align=True)
					# Two sub-rows so the name sits left and the buttons right
					name_row = row.row(align=True)
					name_row.alignment = 'LEFT'
					buttons = row.row(align=True)
					buttons.alignment = 'RIGHT'

					# The name is a button: click it to select the mesh
					op = name_row.operator(
						"rig.switch_mode", text=mesh_obj.name,
						icon='OUTLINER_OB_MESH', emboss=False, translate=False,
					)
					op.target = 'MESH_OBJECT'
					op.mesh_name = mesh_obj.name

					if reorder:
						for direction, icon in (('UP', 'TRIA_UP'), ('DOWN', 'TRIA_DOWN')):
							op = buttons.operator("rig.move_mesh", text="", icon=icon)
							op.mesh_name = mesh_obj.name
							op.direction = direction
					else:
						_mode_button(buttons, 'MESH_EDIT', 'EDITMODE_HLT', False, mesh_obj.name)
						_mode_button(buttons, 'MESH_WEIGHT', 'WPAINT_HLT', False, mesh_obj.name)
					_hide_button(buttons, mesh_obj, context.view_layer)

		if rig_active and context.mode in {'EDIT_ARMATURE', 'POSE'}:
			layout.label(text="Selection:")
			row = layout.row(align=True)
			row.operator("rig.select_chains", text="Select Connected", icon='PARTICLES')
			row.operator("rig.select_mirror", text="Select Mirror", icon='MOD_MIRROR')

		# TODO: a Back button that returns to the object and mode a jump came from

classes = (
	RIG_OT_switch_mode,
	RIG_OT_toggle_hide,
	RIG_OT_move_mesh,
	RIG_OT_select_chains,
	RIG_OT_select_mirror,
	RIG_PT_armature,
)

def register():
	# Saved with the object, so the order survives renames and file reloads
	bpy.types.Object.rigtools_order = bpy.props.IntProperty(
		name="Order",
		description="Position in RigTools' mesh lists; equal values sort by name",
		default=0,
	)
	bpy.types.WindowManager.rigtools_reorder_meshes = bpy.props.BoolProperty(
		name="Reorder Meshes",
		description="Show arrows to change the order of the meshes",
		default=False,
	)
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
	del bpy.types.WindowManager.rigtools_reorder_meshes
	del bpy.types.Object.rigtools_order
