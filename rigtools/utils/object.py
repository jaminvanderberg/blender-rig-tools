import bpy

def remove_object(obj):
	remove_objects([obj])

def remove_objects(objects):
	# batch_remove scans the file once, instead of once per object like objects.remove()
	objects = [obj for obj in objects if obj is not None]
	data = {obj.data for obj in objects if isinstance(obj.data, (bpy.types.Mesh, bpy.types.Curve))}

	bpy.data.batch_remove(objects)
	bpy.data.batch_remove([d for d in data if d.users == 0])

def get_rig(context):
	"""The active armature, or the armature deforming the active mesh."""
	obj = context.object
	if obj is None:
		return None
	if obj.type == 'ARMATURE':
		return obj
	return obj.find_armature()	

def get_controlled_meshes(rig, view_layer):
	"""Meshes with shape keys and an armature modifier using this rig."""
	meshes = []
	for obj in view_layer.objects:
		if obj.type != 'MESH' or not obj.data.shape_keys or "rigtools_helper" in obj:
			continue
		if any(m.type == 'ARMATURE' and m.object == rig for m in obj.modifiers):
			meshes.append(obj)
	return meshes

def sort_by_order(objects):
	"""Objects in the user's order from the Meshes list (Object.rigtools_order), then by name."""
	return sorted(objects, key=lambda obj: (obj.rigtools_order, obj.name.lower()))
