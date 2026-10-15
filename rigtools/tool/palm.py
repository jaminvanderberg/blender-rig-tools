import bpy
from rigtools.tool.fk_chain import FKChain
from rigtools.tool.twist_bones import twist_influence
from rigtools.utils.bone import generate_mch_bones
from rigtools.utils.naming import bone_template


class Palm:
	def __init__(self, *,
		fk_widget: str = "PILL",
		fk_collection_name: str = "",
		mch_collection_name: str = "",
		pinky_falloff_type: str = "LINEAR",
		index_falloff_type: str = "SHARP",
	):
		self.fk_widget = fk_widget
		self.fk_collection_name = fk_collection_name
		self.mch_collection_name = mch_collection_name
		self.pinky_falloff_type = pinky_falloff_type
		self.index_falloff_type = index_falloff_type

		self.fk_chain = None
		self.org_bone_names = []
		self.mch_bone_names = []

		self.mechanism_bone_names = []
		self.property_names = []
		self.object_names = []

	def edit_mode(self, context, org_bone_names):
		self.org_bone_names = org_bone_names

		obj = context.object
		armature_data = obj.data
		
		bpy.ops.object.mode_set(mode='EDIT')
		edit_bones = armature_data.edit_bones

		self.fk_chain = FKChain(
			fk_bone_template=bone_template('fk'),
			fk_collection_name=self.fk_collection_name,
			fk_widget=self.fk_widget
		)

		self.fk_chain.edit_mode(armature_data, self.org_bone_names)

		fk_bones = [edit_bones[name] for name in self.fk_chain.fk_bone_names]
		for fk_bone, org_name in zip(fk_bones, self.org_bone_names):
			org_bone = edit_bones[org_name]
			fk_bone.use_connect = False
			fk_bone.parent = org_bone.parent


		middle_bones = fk_bones[1:-1]
		self.mch_bone_names = generate_mch_bones(armature_data, middle_bones, bone_template('mch'), self.mch_collection_name)
		self.mechanism_bone_names.extend(self.mch_bone_names)

		self.mechanism_bone_names.extend(self.fk_chain.fk_bone_names)
		self.property_names.extend(self.fk_chain.property_names)

		return self

	def pose_mode(self, context):
		obj = context.object
		pose_bones = obj.pose.bones

		self.fk_chain.pose_mode(context)
		self.object_names.extend(self.fk_chain.object_names)

		fk_names = self.fk_chain.fk_bone_names
		n = len(fk_names)
		index = fk_names[0]
		pinky = fk_names[-1]

		middle_indexes = range(1, n - 1)

		for mch_name, i in zip(self.mch_bone_names, middle_indexes):
			mch = pose_bones[mch_name]

			if self.pinky_falloff_type != "NONE":
				c = mch.constraints.new('COPY_ROTATION')
				c.target = obj
				c.subtarget = pinky
				c.target_space = c.owner_space = 'LOCAL'
				c.influence = twist_influence(self.pinky_falloff_type, (n - 1) - i, n - 1)

			if self.index_falloff_type != "NONE":
				c = mch.constraints.new('COPY_ROTATION')
				c.target = obj
				c.subtarget = index
				c.target_space = c.owner_space = 'LOCAL'
				c.influence = twist_influence(self.index_falloff_type, i, n - 1)

		return self