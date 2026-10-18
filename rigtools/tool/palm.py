import bpy
from rigtools.assemblies.tool_data.mechanism_bones import MechanismBones
from rigtools.preferences import get_preferences
from rigtools.tool.fk_chain import FKChain
from rigtools.tool.twist_bones import twist_influence
from rigtools.utils.bone import generate_mch_bones
from rigtools.utils.naming import bone_template


class Palm:
	def __init__(self, *,
		fk_widget: str = "PILL",
		pinky_falloff_type: str = "LINEAR",
		index_falloff_type: str = "SHARP",
	):
		self.fk_widget = fk_widget
		self.pinky_falloff_type = pinky_falloff_type
		self.index_falloff_type = index_falloff_type

		self.fk_chain = None
		self.org_bone_names = []
		self.mch_bone_names = []

		self.mechanism_bones = MechanismBones()
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
			fk_widget=self.fk_widget
		)

		self.fk_chain.edit_mode(armature_data, self.org_bone_names)

		fk_bones = [edit_bones[name] for name in self.fk_chain.fk_bone_names]
		for fk_bone, org_name in zip(fk_bones, self.org_bone_names):
			org_bone = edit_bones[org_name]
			fk_bone.use_connect = False
			fk_bone.parent = org_bone.parent


		middle_bones = self.fk_chain.fk_bone_names[1:-1]
		self.mch_bone_names = generate_mch_bones(armature_data, middle_bones, bone_template('mch'))
		self.mechanism_bones.extend(self.mch_bone_names, 'mch')

		self.mechanism_bones.append(self.fk_chain.mechanism_bones)
		self.property_names.extend(self.fk_chain.property_names)

		return self

	def pose_mode(self, context):
		obj = context.object
		pose_bones = obj.pose.bones
		prefs = get_preferences()

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
				c.influence = twist_influence(self.pinky_falloff_type, (n - 1) - i, n - 1, reverse=False)

			if self.index_falloff_type != "NONE":
				c = mch.constraints.new('COPY_ROTATION')
				c.target = obj
				c.subtarget = index
				c.target_space = c.owner_space = 'LOCAL'
				c.influence = twist_influence(self.index_falloff_type, i, n - 1, reverse=False)

		# Bone Colors
		if self.index_falloff_type != "NONE":
			pb = pose_bones[index]
			pb.color.palette = prefs.control_bone_color
			pb.custom_shape_wire_width = 1.5

		if self.pinky_falloff_type != "NONE":
			pb = pose_bones[pinky]
			pb.color.palette = prefs.control_bone_color		
			pb.custom_shape_wire_width = 1.5

		return self