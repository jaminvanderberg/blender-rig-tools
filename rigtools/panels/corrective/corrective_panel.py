"""Corrective Bones panel: the Create button, plus the active bone's correctives when it has any."""
import bpy

from rigtools.rig_data.correctives import correction_end, corrective_constraints, corrective_target, from_value_name

class RIG_PT_corrective_bones(bpy.types.Panel):
	bl_label = "Corrective Bones"
	bl_idname = "RIG_PT_corrective_bones"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = "Rig Tools"
	bl_options = {'DEFAULT_CLOSED'}

	@classmethod
	def poll(cls, context):
		return context.object and context.object.type == 'ARMATURE' and context.mode == 'POSE'

	def draw(self, context):
		layout = self.layout
		# Greyed out by the operator's poll unless exactly two bones are selected
		layout.operator("rig.create_corrective_bone", icon='CON_TRANSFORM')
		draw_correctives(layout, context)

def draw_correctives(layout, context):
	"""Correctives on the active bone. Draws nothing if the active bone isn't a selected corrective."""
	pose_bone = context.active_pose_bone
	if not pose_bone or pose_bone not in context.selected_pose_bones:
		return

	constraints = corrective_constraints(pose_bone)
	if not constraints:
		return

	obj = context.object
	for c in constraints:
		draw_constraint(layout, obj, pose_bone, c)

def draw_constraint(layout, obj, pose_bone, c):
	box = layout.box()
	col = box.column(align=True)

	row = col.row(align=True)
	target = corrective_target(obj, c)
	row.label(text=f"{target}")
	op = row.operator("rig.mirror_corrective", text="", icon='MOD_MIRROR')
	op.bone_name = pose_bone.name
	op.constraint_name = c.name
	op = row.operator("rig.delete_corrective", text="", icon='TRASH')
	op.bone_name = pose_bone.name
	op.constraint_name = c.name

	end = correction_end(c)

	col.separator(factor=0.5)
	col.prop(c, from_value_name(c), text="From")

	suffix = "_rot" if c.map_to == 'ROTATION' else ""
	row = col.row(align=True)
	row.label(text="Rotate" if c.map_to == 'ROTATION' else "Move")
	for out in "xyz":
		row.prop(c, f"to_{end}_{out}{suffix}", text=out.upper())

classes = (
	RIG_PT_corrective_bones,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
