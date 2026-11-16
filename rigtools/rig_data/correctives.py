"""Reading corrective constraints, and the joined boxes that share Begin/Full properties.

A corrective is a Transformation constraint on the corrective bone that reads a reader MCH.
Its input range is two From fields: Begin (where the correction starts, 0 unless a dead zone
was set) and Full (the reading where it's fully applied).

Constraints made together (a capture that both moved and turned the corrective) are joined:
their Begin and Full fields are driven by two custom properties on the corrective bone,
'<box name> Begin' and '<box name> Full', so they're edited once. A constraint whose fields
aren't driven is split: a box of its own. The drivers, not the property names, say which box
a constraint is in."""
from dataclasses import dataclass

import bpy

from rigtools.utils.naming import bone_template, get_affixes_from_template

BOX_PREFIX = "CORR"
BEGIN = " Begin"
FULL = " Full"

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

def get_from_field(constraint, end):
	"""The From field at one end ('min' or 'max') of the input axis, e.g. 'from_max_x_rot'"""
	return f"from_{end}_{constraint.map_to_x_from.lower()}{from_suffix(constraint)}"

def get_other_end(end):
	return "max" if end == "min" else "min"

def get_property_path(pose_bone, prop_name):
	return pose_bone.path_from_id(f'["{bpy.utils.escape_identifier(prop_name)}"]')

def find_driven_property(pose_bone, constraint, field):
	"""The custom property on pose_bone that a driver on this constraint field reads, or None"""
	anim = pose_bone.id_data.animation_data
	if anim is None:
		return None
	fcurve = anim.drivers.find(constraint.path_from_id(field))
	if fcurve is None or len(fcurve.driver.variables) != 1:
		return None
	target = fcurve.driver.variables[0].targets[0]
	if target.id != pose_bone.id_data:
		return None
	for prop_name in pose_bone.keys():
		if target.data_path == get_property_path(pose_bone, prop_name):
			return prop_name
	return None

def find_full_driver(pose_bone, constraint):
	"""(box name, end) when a From field of the constraint is driven by a box's Full property:
	the name its properties start with, and the end ('min'/'max') that Full drives. Else None"""
	for end in ("min", "max"):
		prop_name = find_driven_property(pose_bone, constraint, get_from_field(constraint, end))
		if prop_name and prop_name.endswith(FULL):
			return prop_name[:-len(FULL)], end
	return None

def correction_end(pose_bone, constraint):
	"""'min' or 'max': the end of the ranges that holds the correction (Full's end)"""
	joined = find_full_driver(pose_bone, constraint)
	if joined:
		return joined[1]
	# A split constraint: Begin lies between 0 and Full, so Full is the end further from 0.
	# A negative reading puts the correction at min (see CorrectiveSetup.add_transform)
	from_min = getattr(constraint, get_from_field(constraint, "min"))
	from_max = getattr(constraint, get_from_field(constraint, "max"))
	return "min" if abs(from_min) > abs(from_max) else "max"

def from_full_name(pose_bone, constraint):
	"""Name of the From field holding Full, the reading where the correction is fully applied"""
	return get_from_field(constraint, correction_end(pose_bone, constraint))

def from_begin_name(pose_bone, constraint):
	"""Name of the From field holding Begin, where the correction starts. 0 unless a dead zone was set"""
	return get_from_field(constraint, get_other_end(correction_end(pose_bone, constraint)))

def read_input(pose_bone, constraint):
	"""What the constraint reads: (MCH, channel, axis, negative). Only boxes reading the same
	input can be joined"""
	full = getattr(constraint, from_full_name(pose_bone, constraint))
	return (constraint.subtarget, constraint.map_from, constraint.map_to_x_from, full < 0)

@dataclass
class CorrectiveBox:
	"""Constraints shown and edited as one. name is what the shared Begin/Full properties
	start with; None for a split constraint, which is a box of its own"""
	name: str | None
	constraints: list

def find_corrective_boxes(pose_bone):
	"""The bone's correctives as boxes, in constraint order"""
	boxes = []
	by_name = {}
	for constraint in corrective_constraints(pose_bone):
		joined = find_full_driver(pose_bone, constraint)
		name = joined[0] if joined else None
		if name is None:
			boxes.append(CorrectiveBox(None, [constraint]))
		elif name in by_name:
			by_name[name].constraints.append(constraint)
		else:
			by_name[name] = CorrectiveBox(name, [constraint])
			boxes.append(by_name[name])
	return boxes

def find_box(pose_bone, constraint_name):
	"""The box holding the named constraint, or None"""
	for box in find_corrective_boxes(pose_bone):
		if any(c.name == constraint_name for c in box.constraints):
			return box
	return None

def find_join_candidates(pose_bone, box):
	"""Other boxes on the bone reading the same input, so they can be joined into this one"""
	box_input = read_input(pose_bone, box.constraints[0])
	return [other for other in find_corrective_boxes(pose_bone)
		if other != box and read_input(pose_bone, other.constraints[0]) == box_input]

def read_box_range(pose_bone, box):
	"""(Begin, Full) of the box: its properties when joined, its constraint's fields when split"""
	if box.name is not None:
		return pose_bone[box.name + BEGIN], pose_bone[box.name + FULL]
	constraint = box.constraints[0]
	return (getattr(constraint, from_begin_name(pose_bone, constraint)),
		getattr(constraint, from_full_name(pose_bone, constraint)))

def get_box_base_name(mch_name, from_channel, axis, full):
	"""Box name for an input, without the clash suffix, e.g. 'CORR MCH-CORR-arm.L +RX'.
	axis is 0-2. Location inputs have no R: 'CORR MCH-CORR-jaw -Z'"""
	sign = "-" if full < 0 else "+"
	channel = "R" if from_channel == 'ROTATION' else ""
	return f"{BOX_PREFIX} {mch_name} {sign}{channel}{'XYZ'[axis]}"

def is_box_name_free(pose_bone, name):
	return name + BEGIN not in pose_bone and name + FULL not in pose_bone

def make_box_names(bones_and_bases):
	"""One unused box name per (pose bone, base name), sharing one suffix so mirrored boxes
	keep matching names: '' if free on every bone, else '.001', '.002' ..."""
	number = 0
	while True:
		suffix = f".{number:03d}" if number else ""
		names = [base + suffix for _, base in bones_and_bases]
		if all(is_box_name_free(pose_bone, name)
				for (pose_bone, _), name in zip(bones_and_bases, names)):
			return names
		number += 1

def set_box_range(pose_bone, name, from_channel, begin, full):
	"""Create or update the box's Begin and Full properties, shown like the From fields
	(degrees for rotation, scene units for location)"""
	subtype = 'ANGLE' if from_channel == 'ROTATION' else 'DISTANCE'
	for prop_name, value in ((name + BEGIN, begin), (name + FULL, full)):
		pose_bone[prop_name] = float(value)
		pose_bone.id_properties_ui(prop_name).update(subtype=subtype, precision=3)

def drive_field(pose_bone, constraint, field, prop_name):
	"""Drive a constraint field with a custom property on the same bone: a simple 'var'
	expression. Reading the bone's own property is cycle-free (reading another constraint's
	field isn't). Replaces any driver already there"""
	fcurve = constraint.driver_add(field)
	driver = fcurve.driver
	driver.type = 'SCRIPTED'
	while driver.variables:
		driver.variables.remove(driver.variables[0])
	variable = driver.variables.new()
	variable.name = "var"
	variable.type = 'SINGLE_PROP'
	variable.targets[0].id_type = 'OBJECT'
	variable.targets[0].id = pose_bone.id_data
	variable.targets[0].data_path = get_property_path(pose_bone, prop_name)
	driver.expression = "var"

def join_constraints(pose_bone, constraints, name, begin, full):
	"""Make the constraints one box: set its Begin/Full properties and drive every constraint's
	From fields from them. Full sits at max, or at min for a negative reading.
	The constraints' correction (to_) values must already be at that end"""
	set_box_range(pose_bone, name, constraints[0].map_from, begin, full)
	full_end = "min" if full < 0 else "max"
	for constraint in constraints:
		drive_field(pose_bone, constraint, get_from_field(constraint, full_end), name + FULL)
		drive_field(pose_bone, constraint, get_from_field(constraint, get_other_end(full_end)), name + BEGIN)

def split_box(pose_bone, box):
	"""Make each constraint its own box. The From fields keep their current values"""
	for constraint in box.constraints:
		for end in ("min", "max"):
			constraint.driver_remove(get_from_field(constraint, end))
	if box.name is not None:
		remove_box_properties_if_unused(pose_bone, box.name)

def remove_box_properties_if_unused(pose_bone, name):
	"""Delete a box's Begin/Full properties once no constraint is joined through them"""
	if any(box.name == name for box in find_corrective_boxes(pose_bone)):
		return
	for prop_name in (name + BEGIN, name + FULL):
		if prop_name in pose_bone:
			del pose_bone[prop_name]
