import bpy

from rigtools.assemblies.fk_templates import FK_TEMPLATES
from rigtools.panels.fk import fk_setup, palm_setup, torso_setup
from rigtools.utils.icons import icon


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

		op = layout.operator("rig.advanced_torso_setup", text="Torso", icon='MOD_CLOTH')
		op.template_id = "torso"
		op.assembly_uid = ""

		grid = layout.grid_flow(row_major=True, columns=2, even_columns=True, align=True)
		grid.operator_context = 'INVOKE_DEFAULT'
		for template_id, template in FK_TEMPLATES.items():
			if template.manual_display:
				continue
			operator = grid.operator(
				"rig.advanced_fk_setup",
				text=template.label,
				icon=icon(template.icon or 'ARMATURE_DATA'),
			)
			operator.template_id = template_id
			operator.assembly_uid = ""

		grid = layout.grid_flow(row_major=True, columns=2, even_columns=True, align=True)
		grid.operator_context = 'INVOKE_DEFAULT'

		op = grid.operator("rig.advanced_fk_setup", text="Shoulder", icon='IPO_EASE_OUT')
		op.template_id = "shoulder"
		op.assembly_uid = ""

		op = grid.operator("rig.advanced_palm_setup", text="Palm", icon='MESH_CAPSULE')
		op.template_id = "palm"
		op.assembly_uid = ""

classes = (
	RIG_PT_fk_panel,
)


def register():
	for cls in classes:
		bpy.utils.register_class(cls)

	fk_setup.register()
	torso_setup.register()
	palm_setup.register()


def unregister():
	fk_setup.unregister()
	torso_setup.unregister()
	palm_setup.unregister()

	for cls in classes:
		bpy.utils.unregister_class(cls)


if __name__ == "__main__":
	try:
		unregister()
	except Exception:
		pass
	register()
