import bpy
import os

def get_widget_path():
	"""Returns the full path to WGTS.blend inside the add-on directory"""
	return os.path.join(os.path.dirname(__file__), "WGTS.blend")

def load_widget_shape(name):
	"""Load a widget object by name from WGTS.blend"""
	path = get_widget_path()
	with bpy.data.libraries.load(path, link=False) as (data_from, data_to):
		if name in data_from.objects and name not in bpy.data.objects:
			data_to.objects.append(name)
	return bpy.data.objects.get(name)

# Create helper bone
def create_shape_driver_bone(edit_bones, name, base_bone_name, rot, scale):
	b = edit_bones.new(name)
	base = edit_bones[base_bone_name]
	b.head = base.head.copy()
	b.tail = base.tail.copy()
	b.roll = base.roll
	b.parent = base
	b.length = 0.1
	# Apply rotation and scale via matrix
	b.transform(Matrix.Rotation(rot[0], 4, 'X') @
	            Matrix.Rotation(rot[1], 4, 'Y') @
	            Matrix.Rotation(rot[2], 4, 'Z'))
	return b.name