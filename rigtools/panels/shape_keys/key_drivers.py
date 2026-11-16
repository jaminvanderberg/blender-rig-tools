"""A shape key's drivers, built from its live connection records and never read back:
value (each bone's capture / extent, combined with max or min) and slider range."""
from rigtools.panels.shape_keys.connection_status import (
	get_live_connections_for_key, tidy_rig_connections)
from rigtools.panels.shape_keys.limits import update_limits
from rigtools.panels.shape_keys.shape_key_utils import (
	SWING_TWIST, add_bone_variable, create_new_driver, extent_name, find_driver, range_name)
from rigtools.rig_data.shape_key_connections import (
	get_key_combine, remove_shape_key_connection, set_key_combine)

def _combine(function, terms):
	"""max(a, b, ...) or min(...); a lone term bare, since max and min need two"""
	return terms[0] if len(terms) == 1 else f"{function}({', '.join(terms)})"

def _key_driver(key, key_block, prop, found):
	"""The key's driver on prop, emptied for rebuilding. Removed (None returned) when nothing
	drives the key; a removed range driver leaves its last value"""
	path = key_block.path_from_id(prop)
	fcurve = find_driver(key, path)
	if not found:
		if fcurve:
			key.animation_data.drivers.remove(fcurve)
		return None
	if fcurve is None:
		fcurve = create_new_driver(key, path)
	driver = fcurve.driver
	for variable in list(driver.variables):
		driver.variables.remove(variable)
	return driver

def _build_value_driver(armature_obj, key, key_block, found, combine):
	"""Each bone's capture / extent, combined with max (any bone) or min (every bone). No
	clamp: Blender clamps to the slider range"""
	driver = _key_driver(key, key_block, "value", found)
	if driver is None:
		return
	terms = []
	for n, (pose_bone, sk_connection) in enumerate(found):
		axis = "XYZ".index(sk_connection.axis)
		capture = driver.variables.new()
		capture.name = f"capture_{n}"
		capture.type = 'TRANSFORMS'
		ctarget = capture.targets[0]
		ctarget.id = armature_obj
		ctarget.bone_target = pose_bone.name
		ctarget.transform_type = f"{sk_connection.channel}_{sk_connection.axis}"
		ctarget.transform_space = 'LOCAL_SPACE'
		if sk_connection.channel == 'ROT':
			ctarget.rotation_mode = SWING_TWIST

		add_bone_variable(driver, f"extent_{n}", armature_obj, pose_bone,
			extent_name(axis, sk_connection.positive, sk_connection.channel))

		sign = '' if sk_connection.positive else '-'
		terms.append(f"{sign}capture_{n} / extent_{n}")
	driver.expression = _combine(combine.lower(), terms)

def _build_range_drivers(armature_obj, key, key_block, found):
	"""slider_max is the largest Max of the sides driving the key, slider_min the smallest Min"""
	for prop, end, function in (("slider_max", "Max", "max"), ("slider_min", "Min", "min")):
		driver = _key_driver(key, key_block, prop, found)
		if driver is None:
			continue
		terms = []
		for n, (pose_bone, sk_connection) in enumerate(found):
			axis = "XYZ".index(sk_connection.axis)
			name = f"{end.lower()}_{n}"
			add_bone_variable(driver, name, armature_obj, pose_bone,
				range_name(axis, sk_connection.positive, end, sk_connection.channel))
			terms.append(name)
		driver.expression = _combine(function, terms)

def build_key_drivers(armature_obj, mesh, key_block, trust=()):
	"""Write the key's value and range drivers from its live records, or remove them when none
	are left. trust: record_ids just written. Returns whether the key is still driven"""
	key = mesh.data.shape_keys
	found = get_live_connections_for_key(armature_obj, mesh, key_block, trust)
	combine = get_key_combine(found)
	set_key_combine(found, combine)
	_build_range_drivers(armature_obj, key, key_block, found)
	_build_value_driver(armature_obj, key, key_block, found, combine)
	return bool(found)

def has_foreign_driver(armature_obj, mesh, key_block):
	"""True if the key has a value driver with no live records: someone else's, left alone"""
	key = mesh.data.shape_keys
	return (find_driver(key, key_block.path_from_id("value")) is not None
		and not get_live_connections_for_key(armature_obj, mesh, key_block))

def disconnect_key_for_removal(mesh, key_block):
	"""Before a key is removed: drop its records, rebuild those bones' limits, and remove its
	drivers here (Python's shape_key_remove leaves the depsgraph evaluating deleted drivers,
	which crashes Blender). Returns the names of the bones disconnected"""
	key = mesh.data.shape_keys
	armature_objs = {modifier.object for modifier in mesh.modifiers
		if modifier.type == 'ARMATURE' and modifier.object}
	disconnected = []
	for armature_obj in armature_objs:
		tidy_rig_connections(armature_obj)
		# Read before the drivers go: a record is live when the key's driver reads it
		found = get_live_connections_for_key(armature_obj, mesh, key_block)
		for pose_bone, connection in found:
			remove_shape_key_connection(pose_bone, connection)
		# Each bone once, in list order
		for pose_bone in dict.fromkeys(pose_bone for pose_bone, _connection in found):
			update_limits(armature_obj, pose_bone)
			disconnected.append(pose_bone.name)

	if key.animation_data:
		key_path = key_block.path_from_id()
		for fcurve in [fcurve for fcurve in key.animation_data.drivers
				if fcurve.data_path.startswith(key_path + ".")]:
			key.animation_data.drivers.remove(fcurve)
	return disconnected
