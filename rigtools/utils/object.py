import bpy

def remove_object(obj):
	if obj is None:
		return

	data = obj.data
	bpy.data.objects.remove(obj, do_unlink=True)

	if data is not None and data.users == 0:
		if isinstance(data, bpy.types.Mesh):
			bpy.data.meshes.remove(data)
		elif isinstance(data, bpy.types.Curve):
			bpy.data.curves.remove(data)