import bpy
from rigtools.utils.bone import is_bone_visible
from rigtools.preferences import get_preferences

class RIG_OT_select_bones_by_name(bpy.types.Operator):
	bl_idname = "rig.select_bones_by_name"
	bl_label = "Select bones by name"
	bl_options = {'REGISTER', 'UNDO'}

	target_name: bpy.props.StringProperty()

	def execute(self, context):
		obj = context.active_object
		if not obj or obj.type != 'ARMATURE':
			self.report({'ERROR'}, "Active object must be an armature.")
			return {'CANCELLED'}
		
		count = 0
		
		if obj.mode == 'POSE':
			for pbone in obj.pose.bones:
				if is_bone_visible(pbone) and self.target_name.upper() in pbone.name.upper():
					pbone.select = True
					count += 1

		if obj.mode == 'EDIT':
			for ebone in obj.data.edit_bones:
				if is_bone_visible(ebone) and self.target_name.upper() in ebone.name.upper():
					ebone.select = True
					count += 1

		self.report({'INFO'}, f"Selected {count} bone{'s' if count != 1 else ''}")
		return {'FINISHED'}

class RIG_PT_selection_panel(bpy.types.Panel):
	bl_label = "Select Bones by Name"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = "Item"

	def draw(self, context):
		if context.mode not in {'EDIT_ARMATURE', 'POSE'}:
			return

		prefs = get_preferences(context)

		layout = self.layout

		tags = [t.strip() for t in prefs.selection_buttons.split(",") if t.strip()]
		if tags:
			grid = layout.grid_flow(row_major = True, columns=prefs.selection_columns, even_columns=True, align=True)
			for tag in tags:
				control = grid.operator("rig.select_bones_by_name", text=tag)		
				control.target_name = tag
		row = layout.row(align=True)
		row.prop(context.window_manager, "bone_search", text="", icon='VIEWZOOM')
		op = row.operator("rig.select_bones_by_name", text="", icon='RESTRICT_SELECT_OFF')
		op.target_name = context.window_manager.bone_search

classes = (
	RIG_OT_select_bones_by_name,
	RIG_PT_selection_panel,
)

def register():
	bpy.types.WindowManager.bone_search = bpy.props.StringProperty(
		name="Search",
		description="select visible bones whos names contain this text",
		default=""
	)
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
	del bpy.types.WindowManager.bone_search