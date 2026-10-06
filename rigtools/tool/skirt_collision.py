import bpy
from mathutils import Vector
from rigtools.preferences import get_preferences
from rigtools.utils.bone import generate_mch_bones
from rigtools.utils.naming import bone_template, generate_bone_name
from rigtools.armature_settings import get_armature_settings
from rigtools.utils.bone_collection import set_bone_collection

class SkirtCollision:
	def __init__(self, *,
		target_bone_names: list[str],
		mch_bone_collection_name: str,
	):
		self.target_bone_names = target_bone_names
		self.mch_bone_collection_name = mch_bone_collection_name

		self.fk_bone_names = []
		self.collision_bone_names = []
		self.mch_bone_names = []

		self.mechanism_bone_names = []
		self.property_names = []
		self.object_names = []

	def edit_mode(self, context, fk_names):
		self.fk_bone_names = fk_names
		obj = context.object
		armature_data = obj.data

		if obj.mode != 'EDIT':
			bpy.ops.object.mode_set(mode='EDIT')

		edit_bones = armature_data.edit_bones
		fk_bones = [edit_bones[name] for name in fk_names]

		for fk_bone in fk_bones:
			collision_name = generate_bone_name(fk_bone.name, bone_template("collision_target"))
			collision_bone = edit_bones.new(collision_name)
			collision_bone.parent = fk_bones[0].parent # All collision targets parented to the parent of the chain
			collision_bone.head = fk_bone.tail
			collision_bone.tail = fk_bone.tail + Vector((0, fk_bone.length * 0.25, 0))

			if self.mch_bone_collection_name:
				set_bone_collection(armature_data, collision_bone, self.mch_bone_collection_name)
			else:
				for coll in fk_bone.collections:
					coll.assign(collision_bone)

			self.mechanism_bone_names.append(collision_bone.name)
			self.collision_bone_names.append(collision_bone.name)

		mch_names = generate_mch_bones(armature_data, fk_bones, bone_template("mch"), self.mch_bone_collection_name)

		self.mechanism_bone_names.extend(mch_names)
		self.mch_bone_names.extend(mch_names)

		return self

	def pose_mode(self, context):
		obj = context.object
		prefs = get_preferences()
		pose_bones = obj.pose.bones
		settings = get_armature_settings(obj.data, context)

		if obj.mode != 'POSE':
			bpy.ops.object.mode_set(mode='POSE')

		for fk_name, mch_name, collision_name in zip(self.fk_bone_names, self.mch_bone_names, self.collision_bone_names):
			target_name = self.target_bone_names[0]
			target_bone = pose_bones[target_name]

			collision_bone = pose_bones[collision_name]
			local = target_bone.bone.matrix_local.inverted() @ collision_bone.bone.head_local

			floor = collision_bone.constraints.new('FLOOR')
			floor.target = obj
			floor.subtarget = target_name
			floor.floor_location = 'FLOOR_X'
			floor.offset = local.x
			floor.use_rotation = False

			track = pose_bones[mch_name].constraints.new('DAMPED_TRACK')
			track.target = obj
			track.subtarget = collision_name

		return self