import bpy
from bpy.props import IntProperty

from rigtools.twist_bones import create_def_twist_chain, get_twist_chain, get_twist_parent
from rigtools.utils.bone import get_selected_bones, select_bones


class RIG_OT_create_twist_bones(bpy.types.Operator):
	bl_idname = "rig.create_twist_bones"
	bl_label = "Create Twist Bones"
	bl_description = "Create twist bone chains on the selected DEF bones"
	bl_options = {'REGISTER', 'UNDO'}

	count: IntProperty(
		name="Twist Bone Count",
		description="Number of twist bones created per bone",
		default=2,
		min=2,
	)

	@classmethod
	def poll(cls, context):
		return (
			context.object
			and context.object.type == 'ARMATURE'
			and context.mode in {'EDIT_ARMATURE', 'POSE'}
		)

	def execute(self, context):
		obj = context.object
		armature_data = obj.data

		selected_names = [bone.name for bone in get_selected_bones(context)]

		original_mode = obj.mode
		if original_mode != 'EDIT':
			bpy.ops.object.mode_set(mode='EDIT')

		outcome = self._create(context, armature_data, selected_names)

		select_bones(obj, self._source_names, select_hidden=True, deselect=True)

		if original_mode != 'EDIT':
			bpy.ops.object.mode_set(mode=original_mode)
		return outcome

	def _create(self, context, armature_data, selected_names):
		edit_bones = armature_data.edit_bones
		self._source_names = []

		def_bones = []
		skipped = 0
		for name in selected_names:
			if not name.startswith('DEF-') or get_twist_parent(armature_data, name):
				skipped += 1
				continue
			def_bones.append(edit_bones[name])
			self._source_names.append(name)

		if not def_bones:
			self.report({'ERROR'}, "No DEF bones selected")
			return {'CANCELLED'}

		try:
			for bone in def_bones:
				chain = get_twist_chain(armature_data, bone.name, use_edit_bones=True)
				if chain and len(chain) != self.count:
					self.report(
						{'ERROR'},
						f"{bone.name} already has {len(chain)} twist bones, not {self.count}",
					)
					return {'CANCELLED'}
		except ValueError as error:
			self.report({'ERROR'}, str(error))
			return {'CANCELLED'}

		created = 0
		existing = 0
		for bone in def_bones:
			if get_twist_chain(armature_data, bone.name, use_edit_bones=True):
				existing += 1
				continue
			create_def_twist_chain(context, bone, self.count)
			created += 1

		messages = []
		if created:
			messages.append(f"Created {self.count} twist bones on {created} bone(s)")
		if existing:
			messages.append(f"{existing} bone(s) already had twist bones")
		if skipped:
			messages.append(f"skipped {skipped} non-DEF bone(s)")
		self.report({'INFO'}, "; ".join(messages))
		return {'FINISHED'}


classes = (
	RIG_OT_create_twist_bones,
)


def register():
	for cls in classes:
		bpy.utils.register_class(cls)


def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
