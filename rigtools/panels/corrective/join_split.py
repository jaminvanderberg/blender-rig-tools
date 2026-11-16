"""Join and Split: whether a corrective's constraints share one Begin/Full (one box) or each
keep their own."""
import bpy
from bpy.props import EnumProperty, StringProperty

from rigtools.rig_data.correctives import (correction_end, find_box, find_join_candidates,
	get_box_base_name, join_constraints, make_box_names, read_box_range,
	remove_box_properties_if_unused, split_box)

def format_reading(constraint, value):
	"""A Begin/Full value as the panel shows it: degrees, or scene units"""
	units = bpy.context.scene.unit_settings
	category = 'ROTATION' if constraint.map_from == 'ROTATION' else 'LENGTH'
	scale = 1.0 if category == 'ROTATION' else units.scale_length
	return bpy.utils.units.to_string(units.system, category, value * scale, precision=3)

def describe_box(pose_bone, box):
	"""e.g. 'Move, Rotate (Full 60°)', for picking a box in the redo panel"""
	kinds = ", ".join("Rotate" if c.map_to == 'ROTATION' else "Move" for c in box.constraints)
	_, full = read_box_range(pose_bone, box)
	return f"{kinds} (Full {format_reading(box.constraints[0], full)})"

# Blender keeps only pointers into these strings: if the list is freed, the labels turn to garbage
_join_items_cache = []

def join_items(self, context):
	global _join_items_cache
	items = []
	armature_obj = context.object
	pose_bone = armature_obj.pose.bones.get(self.bone_name) if armature_obj and armature_obj.pose else None
	box = find_box(pose_bone, self.constraint_name) if pose_bone else None
	if box is not None:
		# Identified by their first constraint's name
		items = [(other.constraints[0].name, describe_box(pose_bone, other), "")
			for other in find_join_candidates(pose_bone, box)]
	# An enum can't be empty
	_join_items_cache = items or [('NONE', "Nothing to join", "")]
	return _join_items_cache

def scale_corrections(pose_bone, box, begin, full):
	"""Scale the box's corrections so that at the reading full, the box moves as far as it
	did before at that reading. Exact over the whole range only with the same Begin and
	full no further than the box's own Full"""
	box_begin, box_full = read_box_range(pose_bone, box)
	if abs(box_full - box_begin) < 1e-9:
		return
	factor = min(max((full - box_begin) / (box_full - box_begin), 0.0), 1.0)
	for constraint in box.constraints:
		end = correction_end(pose_bone, constraint)
		suffix = "_rot" if constraint.map_to == 'ROTATION' else ""
		for out in "xyz":
			name = f"to_{end}_{out}{suffix}"
			setattr(constraint, name, getattr(constraint, name) * factor)

class RIG_OT_join_corrective(bpy.types.Operator):
	bl_idname = "rig.join_corrective"
	bl_label = "Join Corrective"
	bl_description = ("Join another corrective on the same input into this one, so they share "
		"this one's Begin and Full")
	bl_options = {'REGISTER', 'UNDO'}

	bone_name: StringProperty(options={'HIDDEN'})
	constraint_name: StringProperty(options={'HIDDEN'}) # any constraint in the box joined into

	other: EnumProperty(
		name="Join",
		description="The corrective to join into this one",
		items=join_items,
		options={'SKIP_SAVE'},
	)
	amounts: EnumProperty(
		name="Amounts",
		items=[
			('KEEP', "Keep", "Keep the joined corrective's Move and Rotate amounts. "
				"It reaches them at this one's Full"),
			('SCALE', "Scale", "Scale the joined corrective's amounts so that at this one's "
				"Full it's where it was before at that reading"),
		],
		default='KEEP',
	)

	@classmethod
	def poll(cls, context):
		return context.mode == 'POSE'

	def execute(self, context):
		pose_bone = context.object.pose.bones.get(self.bone_name)
		box = find_box(pose_bone, self.constraint_name) if pose_bone else None
		other = find_box(pose_bone, self.other) if box and self.other != 'NONE' else None
		if box is None or other is None or other not in find_join_candidates(pose_bone, box):
			self.report({'ERROR'}, "Nothing to join: no other corrective on this bone reads the same input.")
			return {'CANCELLED'}

		begin, full = read_box_range(pose_bone, box)
		if self.amounts == 'SCALE':
			scale_corrections(pose_bone, other, begin, full)

		name = box.name
		if name is None:
			first = box.constraints[0]
			axis = "xyz".index(first.map_to_x_from.lower())
			base = get_box_base_name(first.subtarget, first.map_from, axis, full)
			name = make_box_names([(pose_bone, base)])[0]
		join_constraints(pose_bone, box.constraints + other.constraints, name, begin, full)
		if other.name is not None and other.name != name:
			remove_box_properties_if_unused(pose_bone, other.name)

		self.report({'INFO'}, f"Joined into one corrective on '{pose_bone.name}'.")
		return {'FINISHED'}

class RIG_OT_split_corrective(bpy.types.Operator):
	bl_idname = "rig.split_corrective"
	bl_label = "Split Corrective"
	bl_description = "Split this corrective so each of its constraints has its own Begin and Full"
	bl_options = {'REGISTER', 'UNDO'}

	bone_name: StringProperty(options={'HIDDEN'})
	constraint_name: StringProperty(options={'HIDDEN'}) # any constraint in the box

	@classmethod
	def poll(cls, context):
		return context.mode == 'POSE'

	def execute(self, context):
		pose_bone = context.object.pose.bones.get(self.bone_name)
		box = find_box(pose_bone, self.constraint_name) if pose_bone else None
		if box is None or box.name is None:
			self.report({'ERROR'}, "This corrective isn't joined.")
			return {'CANCELLED'}
		split_box(pose_bone, box)
		self.report({'INFO'}, f"Split into {len(box.constraints)} correctives on '{pose_bone.name}'.")
		return {'FINISHED'}

classes = (
	RIG_OT_join_corrective,
	RIG_OT_split_corrective,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
