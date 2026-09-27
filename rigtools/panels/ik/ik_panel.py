import bpy

from rigtools.assemblies.ik_templates import IK_TEMPLATES
from rigtools.panels.ik import ik_setup


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

		op = layout.operator("rig.advanced_ik_setup", icon='SETTINGS')
		op.template_id = ""
		op.assembly_uid = ""

		layout.label(text="Templates")
		grid = layout.grid_flow(row_major=True, columns=2, even_columns=True, align=True)
		grid.operator_context = 'INVOKE_DEFAULT'
		for template_id, template in IK_TEMPLATES.items():
			operator = grid.operator(
				"rig.advanced_ik_setup",
				text=template.label,
				icon=template.icon or 'ARMATURE_DATA',
			)
			operator.template_id = template_id
			operator.assembly_uid = ""


classes = (
	RIG_PT_ik_panel,
)


def register():
	for cls in classes:
		bpy.utils.register_class(cls)

	ik_setup.register()


def unregister():
	ik_setup.unregister()

	for cls in classes:
		bpy.utils.unregister_class(cls)


if __name__ == "__main__":
	try:
		unregister()
	except Exception:
		pass
	register()
