import bpy

class RIG_PT_tools_npanel(bpy.types.Panel):
	bl_label = "Tools"
	bl_idname = "RIG_PT_tools_npanel"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = "Rig Tools"
	bl_options = {'DEFAULT_CLOSED'}

	@classmethod
	def poll(cls, context):
		return context.object and context.object.type == 'ARMATURE'

	def draw(self, context):
		layout = self.layout
		mode = context.mode

		if mode in {'OBJECT', 'EDIT_ARMATURE', 'POSE'}:
			layout.label(text="Rig Setup:")
			layout.operator("rig.generate_org_bones", icon='CON_TRANSLIKE')
			layout.operator("rig.create_twist_bones", icon='MOD_SCREW')
			layout.operator("rig.apply_root_widgets", icon='ORIENTATION_GLOBAL')

		if mode in {'POSE', 'EDIT_ARMATURE'}:
			layout.label(text="Chain Tools:")
			layout.operator("rig.rename_chain", icon='GROUP_BONE')
			layout.operator("rig.weight_paint_proxy", icon='WPAINT_HLT')
			layout.operator("rig.parent_along_chain", icon='CONSTRAINT_BONE')
