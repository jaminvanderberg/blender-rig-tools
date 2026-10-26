import bpy

def remove_object(obj):
	remove_objects([obj])

def remove_objects(objects):
	# batch_remove scans the file once, instead of once per object like objects.remove()
	objects = [obj for obj in objects if obj is not None]
	data = {obj.data for obj in objects if isinstance(obj.data, (bpy.types.Mesh, bpy.types.Curve))}

	bpy.data.batch_remove(objects)
	bpy.data.batch_remove([d for d in data if d.users == 0])
