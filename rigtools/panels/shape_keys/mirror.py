"""Mirror Shape Key: copy a key's shape, mirrored across X, onto its mirror key
(Mouth.Smile.L to Mouth.Smile.R, Eye.Left.L to Eye.Right.R, Mouth.Left to Mouth.Right)."""
import bpy
import numpy as np
from bpy.props import StringProperty
from mathutils.kdtree import KDTree

from rigtools.panels.shape_keys.shape_key_utils import (
	group_weights, is_locked, key_index, mirror_shape_key_name, place_after, read_co,
)

# Object-space distance. Kendra matches to 5 decimals; 0.1 mm leaves room for meshes
# that were mirrored with a little float drift
MIRROR_TOLERANCE = 1e-4

def mirror_vertex_map(basis_co, tolerance=MIRROR_TOLERANCE):
	"""For each vertex, the index of its mirror vertex across X = 0, or -1 if no vertex
	is within tolerance. Center vertices map to themselves."""
	count = len(basis_co)
	coords = basis_co.tolist()
	tree = KDTree(count)
	for index, co in enumerate(coords):
		tree.insert(co, index)
	tree.balance()

	mirror = np.full(count, -1, dtype=np.int64)
	for index, (x, y, z) in enumerate(coords):
		_co, found, distance = tree.find((-x, y, z))
		if found is not None and distance <= tolerance:
			mirror[index] = found
	return mirror

class RIG_OT_mirror_shape_key(bpy.types.Operator):
	bl_idname = "rig.mirror_shape_key"
	bl_label = "Mirror Shape Key"
	bl_description = ("Copy this key's shape, mirrored across X, onto its mirror key "
		"(.L to .R, Left to Right), creating it if needed. Drivers and settings on an "
		"existing key are kept")
	bl_options = {'REGISTER', 'UNDO'}

	object_name: StringProperty(options={'HIDDEN'})
	shape_key_name: StringProperty(options={'HIDDEN'})

	def execute(self, context):
		obj = bpy.data.objects.get(self.object_name)
		key = obj.data.shape_keys if obj and obj.type == 'MESH' else None
		source = key.key_blocks.get(self.shape_key_name) if key else None

		if source is None:
			self.report({'ERROR'}, f"Shape key '{self.shape_key_name}' not found")
			return {'CANCELLED'}

		if source == key.reference_key:
			self.report({'ERROR'}, "The Basis is the rest shape: there's nothing to mirror")
			return {'CANCELLED'}

		target_name = mirror_shape_key_name(source.name)
		if target_name is None:
			self.report({'ERROR'}, f"'{source.name}' has no mirror name")
			return {'CANCELLED'}

		target = key.key_blocks.get(target_name)
		if target is not None and is_locked(target):
			self.report({'ERROR'}, f"'{target_name}' is locked")
			return {'CANCELLED'}

		# Edits made in edit mode only reach the key once edit mode is left
		was_editing = obj == context.object and obj.mode == 'EDIT'
		if was_editing:
			bpy.ops.object.mode_set(mode='OBJECT')

		created = target is None
		if created:
			target = obj.shape_key_add(name=target_name, from_mix=False)
			target.relative_key = source.relative_key
			target.slider_min = source.slider_min
			target.slider_max = source.slider_max

		count = len(obj.data.vertices)
		mirror_indexes = mirror_vertex_map(read_co(key.reference_key, count))
		has_mirror = mirror_indexes >= 0

		# The source's vertex group counts as applied
		delta = read_co(source, count) - read_co(source.relative_key, count)
		if source.vertex_group in obj.vertex_groups:
			delta *= group_weights(obj, source.vertex_group)[:, None]

		# Each vertex takes its mirror vertex's motion, with X flipped
		mirrored = delta[mirror_indexes[has_mirror]]
		mirrored[:, 0] *= -1

		# Vertices with no mirror keep whatever the target already had
		target_co = read_co(target, count)
		target_co[has_mirror] = read_co(target.relative_key, count)[has_mirror] + mirrored
		target.data.foreach_set("co", target_co.ravel())
		obj.data.update()

		# A new key is added at the bottom: move it to just under the source
		if created:
			place_after(context, obj, source, [target_name])
			obj.active_shape_key_index = key_index(key, source)

		if was_editing:
			bpy.ops.object.mode_set(mode='EDIT')

		message = f"{'Created' if created else 'Updated'} {target_name} from {source.name}"
		unmatched = int((~has_mirror).sum())
		if unmatched:
			self.report({'WARNING'}, f"{message}. {unmatched} vertices have no mirror and were left as they were")
		else:
			self.report({'INFO'}, message)
		return {'FINISHED'}

classes = (
	RIG_OT_mirror_shape_key,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
