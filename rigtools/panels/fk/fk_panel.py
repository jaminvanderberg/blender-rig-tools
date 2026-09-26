import bpy

class RIG_PT_fk_panel(bpy.types.Panel):
	bl_label = "Forward Kinematics"
	bl_idname = "RIG_PT_fk_panel"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = "Rig Tools"

	@classmethod
	def poll(cls, context):
		return context.object and context.object.type == 'ARMATURE' and context.mode in {'EDIT_ARMATURE', 'POSE'}

	def draw(self, context):
		layout = self.layout

		layout.operator("rig.advanced_fk_setup", icon='CON_STRETCHTO')

from rigtools.panels.fk import fk_setup

classes = (
	RIG_PT_fk_panel,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)

	fk_setup.register()

def unregister():
	fk_setup.unregister()

	for cls in classes:
		bpy.utils.unregister_class(cls)
	
if __name__ == "__main__":
	try:
		unregister()
	except Exception:
		pass
	register()
