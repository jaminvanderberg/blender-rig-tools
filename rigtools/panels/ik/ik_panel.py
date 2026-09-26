import bpy

class RIG_PT_ik_panel(bpy.types.Panel):
	bl_label = "Inverse Kinematics"
	bl_idname = "RIG_PT_ik_panel"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = "Rig Tools"

	@classmethod
	def poll(cls, context):
		return context.object and context.object.type == 'ARMATURE' and context.mode in {'EDIT_ARMATURE', 'POSE'}

	def draw(self, context):
		layout = self.layout

		layout.operator("rig.advanced_ik_setup", icon='CON_CHILDOF')

		templates = layout.column()
		templates.label(text="Templates")
		templates.operator_context = 'INVOKE_DEFAULT'
		for template_id, template in ik_template.IK_TEMPLATES.items():
			operator = templates.operator(
				"rig.create_ik_from_template",
				text=template.label,
				icon=template.icon or 'ARMATURE_DATA',
			)
			operator.template_id = template_id

from rigtools.panels.ik import ik_setup, ik_template

classes = (
	RIG_PT_ik_panel,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)

	ik_setup.register()
	ik_template.register()

def unregister():
	ik_template.unregister()
	ik_setup.unregister()

	for cls in classes:
		bpy.utils.unregister_class(cls)
	
if __name__ == "__main__":
	try:
		unregister()
	except Exception:
		pass
	register()
	
	bpy.ops.rig.advanced_ik_setup()