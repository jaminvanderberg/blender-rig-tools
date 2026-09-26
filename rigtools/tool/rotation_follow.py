import bpy
from rigtools.utils.bone import generate_bone_name, duplicate_bone, set_bone_collection
from rigtools.preferences import get_preferences

class RotationFollow:
	def __init__(self, *,
		mch_collection_name: str | None = None,
		relationship: str = 'COPY_ROTATION'
	):
		self.mch_collection_name = mch_collection_name
		self.relationship = relationship

		self.master_name = None
		self.mch_bone_names = None

	def edit_mode(self, context, bone_names: list[str]):
		obj = context.object
		edit_bones = obj.data.edit_bones
		prefs = get_preferences()

		if obj.mode != 'EDIT':
			bpy.ops.object.mode_set(mode='EDIT')

		self.master_name = bone_names[0]

		self.mch_bone_names = []
		
		for bone_name in bone_names[1:]:
			bone = edit_bones[bone_name]
			mch_bone_name = generate_bone_name(bone_name, prefs.mch_template)
			mch_bone = duplicate_bone(obj.data, bone, mch_bone_name, 0.35)
			if self.mch_collection_name:
				set_bone_collection(obj.data, mch_bone, self.mch_collection_name)
			elif prefs.mch_collection_name:
				set_bone_collection(obj.data, mch_bone, prefs.mch_collection_name)
			self.mch_bone_names.append(mch_bone.name)
			bone.use_connect = False
			bone.parent = mch_bone

		return self


	def pose_mode(self, context):
		obj = context.object

		pose_bones = obj.pose.bones

		for mch_name in self.mch_bone_names:
			mch_bone = pose_bones[mch_name]
			constraint = mch_bone.constraints.new(self.relationship)
			constraint.target = obj
			constraint.subtarget = self.master_name
			constraint.target_space = 'LOCAL'
			constraint.owner_space = 'LOCAL'

		return self
