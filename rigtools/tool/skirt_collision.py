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
		self.pin_bone_names = []

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

		total_length = sum(fk_bone.length for fk_bone in fk_bones)
		target_spacing = total_length * 1.5 / len(fk_bones)
		covered = 0.0

		for index, fk_bone in enumerate(fk_bones):
			collision_name = generate_bone_name(
				fk_bone.name,
				bone_template("collision_target"),
			)
			collision_bone = edit_bones.new(collision_name)
			collision_bone.parent = fk_bones[0].parent

			direction = fk_bone.tail - fk_bone.head
			tangent = direction / direction.length
			along = target_spacing * (index + 1) - covered
			point = fk_bone.head + tangent * along
			collision_bone.head = point
			collision_bone.tail = point + tangent * target_spacing * 0.25

			covered += direction.length

			if self.mch_bone_collection_name:
				set_bone_collection(armature_data, collision_bone, self.mch_bone_collection_name)
			else:
				for coll in fk_bone.collections:
					coll.assign(collision_bone)

			self.mechanism_bone_names.append(collision_bone.name)
			self.collision_bone_names.append(collision_bone.name)

			target = edit_bones[self.target_bone_names[0]]
			target_direction = (target.tail - target.head).normalized()

			point = collision_bone.head
			distance_along_target = (point - target.head).dot(target_direction)
			axis_point = target.head + target_direction * distance_along_target

			pin_name = generate_bone_name(fk_bone.name, bone_template("collision_source"))
			pin = edit_bones.new(pin_name)
			pin.head = axis_point
			pin.tail = point
			pin.parent = target
			pin.length = pin.length * 0.35
			
			self.mechanism_bone_names.append(pin.name)
			self.pin_bone_names.append(pin.name)

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

		for fk_name, mch_name, collision_name, pin_name in zip(self.fk_bone_names, self.mch_bone_names, self.collision_bone_names, self.pin_bone_names):
			target_bone = pose_bones[pin_name]

			collision_bone = pose_bones[collision_name]
			local = target_bone.bone.matrix_local.inverted() @ collision_bone.bone.head_local

			floor = collision_bone.constraints.new('FLOOR')
			floor.target = obj
			floor.subtarget = pin_name
			floor.floor_location = 'FLOOR_Y'
			floor.offset = local.y
			floor.use_rotation = True
			floor.owner_space = 'POSE'
			floor.target_space = 'POSE'

			track = pose_bones[mch_name].constraints.new('DAMPED_TRACK')
			track.target = obj
			track.subtarget = collision_name

		return self