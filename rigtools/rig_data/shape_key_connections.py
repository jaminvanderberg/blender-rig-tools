import bpy
from bpy.props import BoolProperty, CollectionProperty, EnumProperty, IntProperty, PointerProperty, StringProperty


class RigToolsShapeKeyConnection(bpy.types.PropertyGroup):
	"""Records that this bone drives one mesh's shape key, from one side (axis and direction)."""
	mesh: PointerProperty(
		type=bpy.types.Object,
		poll=lambda self, obj: obj.type == 'MESH',
		description="The mesh that has the shape key. A real reference: survives renaming the object",
	)
	# Shape keys can't be pointed to, so this is a name. Repaired from the drivers if stale
	key_name: StringProperty()
	axis: EnumProperty(items=(('X', "X", ""), ('Y', "Y", ""), ('Z', "Z", "")))
	positive: BoolProperty(default=True, description="Which way the bone moves to reach the shape")

class RigToolsShapeKeyConnections(bpy.types.PropertyGroup):
	"""Everything this bone drives, plus the list's selection."""
	items: CollectionProperty(type=RigToolsShapeKeyConnection)
	active_index: IntProperty()


def get_shape_key_connections(pose_bone):
	"""Get all shape key connections for a bone, in list order."""
	return pose_bone.rigtools_shape_keys.items


def find_shape_key_connection(pose_bone, mesh, key_name, axis, positive):
	"""The connection item for this key on this side of the bone, or None."""
	for item in pose_bone.rigtools_shape_keys.items:
		if (item.mesh == mesh and item.key_name == key_name
				and item.axis == axis and item.positive == positive):
			return item
	return None


def add_shape_key_connection(pose_bone, mesh, key_name, axis, positive):
	"""Add a new connection, returns existing if already present."""
	item = find_shape_key_connection(pose_bone, mesh, key_name, axis, positive)
	if item is None:
		item = pose_bone.rigtools_shape_keys.items.add()
		item.mesh = mesh
		item.key_name = key_name
		item.axis = axis
		item.positive = positive
	return item


def remove_shape_key_connection(pose_bone, item):
	"""Forget a connection, keeping the list's selection in range."""
	data = pose_bone.rigtools_shape_keys
	index = next(i for i, other in enumerate(data.items) if other == item)
	data.items.remove(index)
	data.active_index = min(data.active_index, len(data.items) - 1)

def find_bone_connections_for_shape_key(armature_obj, mesh, key_name):
	"""[(pose bone, sk_connection)] for every bone on the armature that drives this shape key"""
	return [(pose_bone, sk_connection) for pose_bone in armature_obj.pose.bones
		for sk_connection in get_shape_key_connections(pose_bone)
		if sk_connection.mesh == mesh and sk_connection.key_name == key_name]

classes = (
	RigToolsShapeKeyConnection,
	RigToolsShapeKeyConnections,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	bpy.types.PoseBone.rigtools_shape_keys = PointerProperty(type=RigToolsShapeKeyConnections)

def unregister():
	del bpy.types.PoseBone.rigtools_shape_keys
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
