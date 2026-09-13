import bpy
from rigtools.utils.bone import generate_bone_name, duplicate_bone

def create_rotation_follow_setup(context, bone_names, mch_bone_template, relationship = 'COPY_ROTATION'):
	obj = context.object
	edit_bones = obj.data.edit_bones

	if obj.mode != 'EDIT':
		bpy.ops.object.mode_set(mode='EDIT')

	master_name = bone_names[0]

	mch_bones = []
	
	for bone_name in bone_names[1:]:
		bone = edit_bones[bone_name]
		mch_bone_name = generate_bone_name(bone_name, mch_bone_template)
		mch_bone = duplicate_bone(obj.data,bone, mch_bone_name, 0.35)
		mch_bones.append(mch_bone.name)
		bone.use_connect = False
		bone.parent = mch_bone

	bpy.ops.object.mode_set(mode='POSE')

	pose_bones = obj.pose.bones

	for mch_name in mch_bones:
		mch_bone = pose_bones[mch_name]
		constraint = mch_bone.constraints.new(relationship)
		constraint.target = obj
		constraint.subtarget = master_name
		constraint.target_space = 'LOCAL'
		constraint.owner_space = 'LOCAL'



