import bpy
from rigtools.rig_data.correctives import corrective_constraints, corrective_target
from rigtools.utils.icons import icon

class RIG_PT_corrective_panel(bpy.types.Panel):
	bl_label = "Corrective"
	bl_idname = "RIG_PT_corrective_panel"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = "Rig Tools"
	bl_parent_id = "RIG_PT_assembly_panel"

	@classmethod
	def poll(cls, context):
		return context.mode == 'POSE'

	def draw(self, context):
		layout = self.layout
		obj = context.object
		layout.operator("rig.create_corrective_bone", icon='ADD')

		found = False
		for pose_bone in context.selected_pose_bones:
			for c in corrective_constraints(pose_bone):
				found = True
				self.draw_constraint(layout, obj, pose_bone, c)

		if not found:
			layout.label(text="No correctives selected",
				icon=icon('STATUS_INFO'))

	def draw_constraint(self, layout, obj, pose_bone, c):
		box = layout.box()
		row = box.row()
		target = corrective_target(obj, c)
		row.label(text=f"{target} > {pose_bone.name}", icon='CON_TRANSFORM')
		op = row.operator("rig.delete_corrective", text="", icon='TRASH')
		op.bone_name = pose_bone.name
		op.constraint_name = c.name

		# Input: the one axis the corrective reads
		axis = c.map_to_x_from.lower()
		row = box.row(align=True)
		row.prop(c, f"from_min_{axis}_rot", text="From")
		row.prop(c, f"from_max_{axis}_rot", text="")

		# Output: min/max per axis
		suffix = "_rot" if c.map_to == 'ROTATION' else ""
		col = box.column(align=True)
		for out in "xyz":
			row = col.row(align=True)
			row.prop(c, f"to_min_{out}{suffix}", text=out.upper())
			row.prop(c, f"to_max_{out}{suffix}", text="")

classes = (
	RIG_PT_corrective_panel,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
