from rigtools.rig_data.correctives import correction_end, corrective_constraints, corrective_target

def draw_correctives(layout, context):
	"""Correctives on the active bone, drawn at the top of the assembly panel.
	Draws nothing if the active bone isn't a corrective."""
	pose_bone = context.active_pose_bone
	if context.mode != 'POSE' or not pose_bone:
		return
	if pose_bone not in context.selected_pose_bones:
		return

	constraints = corrective_constraints(pose_bone)
	if not constraints:
		return

	obj = context.object
	for c in constraints:
		draw_constraint(layout, obj, pose_bone, c)
	layout.separator()

def draw_constraint(layout, obj, pose_bone, c):
	box = layout.box()
	header = box.column()
	header.label(text="Corrective Bone", icon='CON_TRANSFORM')
	
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

	axis = c.map_to_x_from.lower()
	end = correction_end(c)

	col.separator(factor=0.5)
	col.prop(c, f"from_{end}_{axis}_rot", text="From")

	suffix = "_rot" if c.map_to == 'ROTATION' else ""
	row = col.row(align=True)
	row.label(text="Rotate" if c.map_to == 'ROTATION' else "Move")
	for out in "xyz":
		row.prop(c, f"to_{end}_{out}{suffix}", text=out.upper())
