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

def from_suffix(constraint):
	"""'_rot' when the corrective reads rotation, '' when it reads location"""
	return "_rot" if constraint.map_from == 'ROTATION' else ""

def correction_end(constraint):
	"""'min' or 'max': the end of the ranges that holds the correction"""
	# Only one end of each range holds the correction; the other end is 0.
	# A negative reading puts the correction at min (see add_transform)
	axis = constraint.map_to_x_from.lower()
	suffix = from_suffix(constraint)
	from_min = getattr(constraint, f"from_min_{axis}{suffix}")
	from_max = getattr(constraint, f"from_max_{axis}{suffix}")
	return "min" if abs(from_min) > abs(from_max) else "max"

def from_value_name(constraint):
	"""Name of the From field holding the driving bone's reading, e.g. 'from_max_x_rot'"""
	axis = constraint.map_to_x_from.lower()
	return f"from_{correction_end(constraint)}_{axis}{from_suffix(constraint)}"
