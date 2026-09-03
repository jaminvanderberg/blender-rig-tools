import bpy

class RIG_PT_tools_npanel(bpy.types.Panel):
	bl_label = "Rig Tools"
	bl_idname = "RIG_PT_tools_npanel"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = "Rig Tools"

	@classmethod
	def poll(cls, context):
		return True #context.object and context.object.type == 'ARMATURE'

	def draw(self, context):
		layout = self.layout
		obj = context.object
		mode = context.mode

		if mode == 'POSE':
			layout.label(text="Pose Tools:")
			layout.operator("rig.add_eye_targets", icon='CON_TRACKTO')
			
			layout.label(text="Weight Paint:")
			layout.operator("rig.switch_to_weight_paint", icon='WPAINT_HLT')
		
		if mode in {'OBJECT', 'EDIT_ARMATURE', 'POSE'}:
			layout.label(text="Rig Setup:")
			layout.operator("rig.setup_def_constraints", icon='CON_TRANSLIKE')

		if mode == 'PAINT_WEIGHT':
			layout.label(text="Weight Paint:")
			layout.operator("rig.switch_back_to_pose", icon='OUTLINER_DATA_ARMATURE')
			
		else:
			layout.label(text="Switch to Pose or Object Mode")