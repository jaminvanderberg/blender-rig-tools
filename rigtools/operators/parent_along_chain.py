import bpy


class RIG_OT_parent_along_chain(bpy.types.Operator):
	"""Parent each selected bone to the selected bone whose tail sits on its head."""
	bl_idname = "rig.parent_along_chain"
	bl_label = "Parent Along Chain"
	bl_options = {'REGISTER', 'UNDO'}

	distance: bpy.props.FloatProperty(
		name="Scan Distance",
		description="Parent a bone when another selected bone's tail is within this distance of its head",
		default=0.0001,
		min=0.0,
		soft_max=1.0,
		precision=4,
		subtype='DISTANCE',
		unit='LENGTH',
	)

	connected: bpy.props.BoolProperty(
		name="Parent Connected",
		description="Lock each parented bone's head to its new parent's tail",
		default=False,
	)

	@classmethod
	def poll(cls, context):
		obj = context.object
		return (
			obj
			and obj.type == 'ARMATURE'
			and context.mode == 'EDIT_ARMATURE'
			and context.selected_editable_bones
		)

	def execute(self, context):
		selected = list(context.selected_editable_bones)
		parented, skipped = parent_bones_along_chain(selected, self.distance, self.connected)

		if skipped:
			names = ", ".join(bone.name for bone in skipped)
			self.report(
				{'WARNING'},
				f"Parented {parented} bone(s). Skipped {len(skipped)} with no single match: {names}",
			)
		else:
			self.report({'INFO'}, f"Parented {parented} bone(s)")

		return {'FINISHED'}


def parent_bones_along_chain(selected, distance, connected):
	"""Parent each bone to the selected bone whose tail is nearest its head.

	When connected is set, the bone's head locks to that tail. A bone is skipped
	when more than one tail is inside the distance, or when parenting it would
	make a cycle. Returns (parented_count, skipped_bones).
	"""
	parented = 0
	skipped = []

	for bone in selected:
		parent = find_chain_parent(bone, selected, distance)
		if parent is None:
			continue
		if parent is False:
			skipped.append(bone)
			continue
		if creates_parent_cycle(bone, parent):
			skipped.append(bone)
			continue
		if bone.parent == parent and bone.use_connect == connected:
			continue

		bone.use_connect = False
		bone.parent = parent
		bone.use_connect = connected
		parented += 1

	return parented, skipped


def find_chain_parent(bone, selected, distance):
	"""Return the parent bone, None if nothing is in range, or False if the match is ambiguous."""
	matches = []
	for other in selected:
		if other == bone:
			continue
		if (other.tail - bone.head).length <= distance:
			matches.append(other)

	if not matches:
		return None
	if len(matches) > 1:
		return False
	return matches[0]


def creates_parent_cycle(bone, parent):
	ancestor = parent
	while ancestor:
		if ancestor == bone:
			return True
		ancestor = ancestor.parent
	return False
