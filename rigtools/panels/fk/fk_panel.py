import bpy

from rigtools.assemblies.fk_templates import FK_TEMPLATES
from rigtools.panels.fk import fk_setup, torso_setup


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

		op = layout.operator("rig.advanced_fk_setup", icon='CON_STRETCHTO')
		op.template_id = ""
		op.assembly_uid = ""

		op = layout.operator("rig.advanced_torso_setup", icon='MOD_CLOTH')
		op.template_id = ""
		op.assembly_uid = ""

		layout.label(text="Templates")
		grid = layout.grid_flow(row_major=True, columns=2, even_columns=True, align=True)
		grid.operator_context = 'INVOKE_DEFAULT'
		for template_id, template in FK_TEMPLATES.items():
			operator = grid.operator(
				"rig.advanced_fk_setup",
				text=template.label,
				icon=template.icon or 'ARMATURE_DATA',
			)
			operator.template_id = template_id
			operator.assembly_uid = ""


classes = (
	RIG_PT_fk_panel,
)


def register():
	for cls in classes:
		bpy.utils.register_class(cls)

	fk_setup.register()
	torso_setup.register()


def unregister():
	fk_setup.unregister()
	torso_setup.unregister()

	for cls in classes:
		bpy.utils.unregister_class(cls)


if __name__ == "__main__":
	try:
		unregister()
	except Exception:
		pass
	register()
