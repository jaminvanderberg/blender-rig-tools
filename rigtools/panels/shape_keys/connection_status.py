"""Which connection records are real, and repairing the rest.

A record is checked against its key's value driver: does the driver read this bone's extent
for this side? Blender's Duplicate and edit mode Symmetrize copy records but not drivers, so
copies are DEAD. Records hold the key by name, so a renamed key's records are RENAMED until
tidied. Run tidy_rig_connections before looking records up by key name."""
from rigtools.panels.shape_keys.limits import update_limits
from rigtools.panels.shape_keys.shape_key_utils import bone_prop_path, extent_name, find_driver
from rigtools.rig_data.shape_key_connections import (
	find_bone_connections_for_shape_key, find_shape_key_connection, get_shape_key_connections,
	remove_shape_key_connection, rename_shape_key_connection)

def _reads_side(armature_obj, key, key_block, pose_bone, connection):
	"""True if the key's value driver reads this bone's extent for the record's side"""
	fcurve = find_driver(key, key_block.path_from_id("value"))
	if fcurve is None:
		return False
	prop = extent_name("XYZ".index(connection.axis), connection.positive, connection.channel)
	path = bone_prop_path(pose_bone, prop)
	return any(variable.type == 'SINGLE_PROP' and variable.targets[0].id == armature_obj
		and variable.targets[0].data_path == path for variable in fcurve.driver.variables)

def connection_status(armature_obj, pose_bone, connection):
	"""(status, key name) for one record:
		LIVE       the key exists and its driver reads this side
		RENAMED    the key is gone, and exactly one other key's driver reads this side
		           (not one this bone already has a record for): its new name
		AMBIGUOUS  several keys could be the renamed one
		DEAD       nothing reads it: a copied bone's record, or a driver removed by hand"""
	mesh = connection.mesh
	key = mesh.data.shape_keys if mesh and mesh.type == 'MESH' else None
	if key is None:
		return 'DEAD', None
	key_block = key.key_blocks.get(connection.key_name)
	if key_block is not None:
		live = _reads_side(armature_obj, key, key_block, pose_bone, connection)
		return ('LIVE', key_block.name) if live else ('DEAD', None)
	candidates = [kb.name for kb in key.key_blocks
		if _reads_side(armature_obj, key, kb, pose_bone, connection)
		and find_shape_key_connection(pose_bone, mesh, kb.name, connection.axis,
			connection.positive, connection.channel) is None]
	if len(candidates) == 1:
		return 'RENAMED', candidates[0]
	return ('AMBIGUOUS', None) if candidates else ('DEAD', None)

def has_connections(armature_obj, pose_bone):
	"""True if the bone has any record that isn't dead"""
	return any(connection_status(armature_obj, pose_bone, connection)[0] != 'DEAD'
		for connection in get_shape_key_connections(pose_bone))

def record_id(pose_bone, mesh, key_name, axis_name, positive, channel):
	"""A record by value, for trust: items move in memory as the list grows"""
	return (pose_bone.name, mesh.name, key_name, axis_name, positive, channel)

def get_live_connections_for_key(armature_obj, mesh, key_block, trust=()):
	"""[(pose bone, record)] that really drive this key, plus trusted ones (record_ids of
	records just written, which the driver doesn't read yet)"""
	key = mesh.data.shape_keys
	return [(pose_bone, connection)
		for pose_bone, connection in find_bone_connections_for_shape_key(armature_obj, mesh, key_block.name)
		if record_id(pose_bone, mesh, key_block.name, connection.axis, connection.positive,
			connection.channel) in trust
		or _reads_side(armature_obj, key, key_block, pose_bone, connection)]

def tidy_connections(armature_obj, pose_bone):
	"""One bone's records: renamed ones get the new key name, dead ones are removed,
	ambiguous ones are kept for the Data Viewer"""
	items = get_shape_key_connections(pose_bone)
	statuses = [connection_status(armature_obj, pose_bone, connection) for connection in items]
	for index in reversed(range(len(items))):
		status, key_name = statuses[index]
		if status == 'DEAD':
			remove_shape_key_connection(pose_bone, items[index])
		elif status == 'RENAMED':
			rename_shape_key_connection(items[index], key_name)

def tidy_rig_connections(armature_obj):
	"""tidy_connections on every bone, rebuilding the limits of bones that lost a record.
	Every bone, not just the one operated on: another bone driving a renamed key would
	otherwise be left out of its rebuilt driver"""
	for pose_bone in armature_obj.pose.bones:
		items = get_shape_key_connections(pose_bone)
		if not items:
			continue
		count = len(items)
		tidy_connections(armature_obj, pose_bone)
		if len(items) != count:
			update_limits(armature_obj, pose_bone)
