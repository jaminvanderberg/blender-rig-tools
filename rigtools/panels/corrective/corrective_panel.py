"""Corrective Bones panel: the Create button, plus the active bone's correctives when it has any."""
import bpy

from rigtools.rig_data.correctives import (BEGIN, FULL, correction_end, corrective_target,
	find_corrective_boxes, find_join_candidates, from_begin_name, from_full_name)

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
	"""Correctives on the active bone, one box each. Draws nothing if the active bone isn't a
	selected corrective."""
	pose_bone = context.active_pose_bone
	if not pose_bone or pose_bone not in context.selected_pose_bones:
		return

	obj = context.object
	for box in find_corrective_boxes(pose_bone):
		draw_box(layout, obj, pose_bone, box)

def set_box_operator(op, pose_bone, box):
	op.bone_name = pose_bone.name
	op.constraint_name = box.constraints[0].name

def draw_box(layout, obj, pose_bone, box):
	col = layout.box().column(align=True)
	first = box.constraints[0]

	row = col.row(align=True)
	row.label(text=corrective_target(obj, first))
	if box.name is not None:
		set_box_operator(row.operator("rig.split_corrective", text="", icon='UNLINKED'),
			pose_bone, box)
	join = row.row(align=True)
	join.enabled = bool(find_join_candidates(pose_bone, box))
	set_box_operator(join.operator("rig.join_corrective", text="", icon='LINKED'), pose_bone, box)
	set_box_operator(row.operator("rig.mirror_corrective", text="", icon='MOD_MIRROR'),
		pose_bone, box)
	set_box_operator(row.operator("rig.delete_corrective", text="", icon='TRASH'),
		pose_bone, box)

	col.separator(factor=0.5)
	if box.name is not None:
		# Joined: one Begin and Full for every constraint in the box
		for suffix, label in ((BEGIN, "Begin"), (FULL, "Full")):
			prop_name = bpy.utils.escape_identifier(box.name + suffix)
			col.prop(pose_bone, f'["{prop_name}"]', text=label)
	else:
		col.prop(first, from_begin_name(pose_bone, first), text="Begin")
		col.prop(first, from_full_name(pose_bone, first), text="Full")

	# One toggle for the whole box: shown on when every constraint extrapolates,
	# and a click sets them all
	extrapolating = all(c.use_motion_extrapolate for c in box.constraints)
	op = col.operator("rig.set_corrective_extrapolate", text="Extrapolate",
		icon='CHECKBOX_HLT' if extrapolating else 'CHECKBOX_DEHLT', emboss=False)
	set_box_operator(op, pose_bone, box)
	op.extrapolate = not extrapolating

	for constraint in box.constraints:
		end = correction_end(pose_bone, constraint)
		suffix = "_rot" if constraint.map_to == 'ROTATION' else ""
		row = col.row(align=True)
		row.label(text="Rotate" if constraint.map_to == 'ROTATION' else "Move")
		for out in "xyz":
			row.prop(constraint, f"to_{end}_{out}{suffix}", text=out.upper())

classes = (
	RIG_PT_corrective_bones,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
