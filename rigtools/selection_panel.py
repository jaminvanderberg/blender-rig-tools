import bpy
from rigtools.utils.bone import is_bone_visible

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
				if is_bone_visible(pbone) and self.target_name in pbone.name.upper():
					pbone.select = True
					count += 1

		if obj.mode == 'EDIT':
			for ebone in obj.data.edit_bones:
				if is_bone_visible(ebone) and self.target_name in ebone.name.upper():
					ebone.select = True
					count += 1

		self.report({'INFO'}, f"Selected {count} bone{'s' if count != 1 else ''}")
		return {'FINISHED'}

class RIG_PT_selection_panel(bpy.types.Panel):
	bl_label = "Quick Bone Selection"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = "Item"

	def draw(self, context):
		if context.mode not in {'EDIT_ARMATURE', 'POSE'}:
			return

		layout = self.layout
		
		layout.label(text="Select bones by name:")

		row = layout.row(align=True)

		fk = row.operator("rig.select_bones_by_name", text="FK")
		fk.target_name = "FK"

		ik = row.operator("rig.select_bones_by_name", text="IK")
		ik.target_name = "IK"

		tweak = row.operator("rig.select_bones_by_name", text="Tweak")
		tweak.target_name = "TWEAK"

		row = layout.row(align=True)

		fk = row.operator("rig.select_bones_by_name", text="DEF")
		fk.target_name = "DEF"

		ik = row.operator("rig.select_bones_by_name", text="ORG")
		ik.target_name = "ORG"

		tweak = row.operator("rig.select_bones_by_name", text="MCH")
		tweak.target_name = "MCH"