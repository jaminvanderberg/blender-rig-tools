from rigtools.utils.naming import bone_template, get_affixes_from_template

def corrective_prefix():
	prefix, _ = get_affixes_from_template(bone_template("corrective"))
	return prefix

def corrective_constraints(pose_bone, prefix=None):
	"""Transformation constraints on pose_bone that read a corrective MCH"""
	prefix = prefix or corrective_prefix()
	return [c for c in pose_bone.constraints
		if c.type == 'TRANSFORM' and c.subtarget.startswith(prefix)]

def find_correctives(obj):
	"""(pose bone, constraint) for every corrective on the rig"""
	prefix = corrective_prefix()
	return [(pb, c) for pb in obj.pose.bones
		for c in corrective_constraints(pb, prefix)]

def corrective_target(obj, constraint):
	"""The target bone name, read from the MCH's Copy Transforms"""
	mch = obj.pose.bones[constraint.subtarget]
	return mch.constraints[0].subtarget
