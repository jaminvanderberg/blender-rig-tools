import bpy

class RIG_PT_tools_npanel(bpy.types.Panel):
	bl_label = "Rig Tools"
	bl_idname = "RIG_PT_tools_npanel"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = "Rig Tools"

	@classmethod
	def poll(cls, context):
		return context.object and context.object.type == 'ARMATURE'

	def draw(self, context):
		layout = self.layout
		obj = context.object
		mode = context.mode

		if mode in {'OBJECT', 'EDIT_ARMATURE', 'POSE'}:
			layout.label(text="Rig Setup:")
			layout.operator("rig.generate_org_bones", icon='CON_TRANSLIKE')
			if mode in {'POSE', 'EDIT_ARMATURE'}:
				layout.operator("rig.batch_rename_bones", icon='SYNTAX_OFF')

		if mode in {'POSE', 'EDIT_ARMATURE'}:
			layout.label(text="Chain Tools:")
			layout.operator("rig.create_rotation_isolation", icon='CON_ROTLIKE')
			layout.operator("rig.create_fk_tweak_chain", icon='CON_STRETCHTO')
			layout.operator("rig.create_fk_ik_switch", icon='CON_CHILDOF')

