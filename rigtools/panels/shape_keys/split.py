"""Create/Update L/R Shape Keys: split a full-face key into its .L and .R halves."""
import bpy
import numpy as np
from bpy.props import FloatProperty, StringProperty

from rigtools.panels.shape_keys.shape_key_utils import (
	can_split, falloff_prop, group_weights, is_key_driven, is_locked, key_index, place_after, read_co,
	side_names,
)

DEFAULT_FALLOFF = 0.002

def left_weights(basis_x, falloff):
	"""Smooth ramp across X = 0: 1 on the left (+X), 0 on the right. Left + right = 1."""
	if falloff <= 0:
		return np.where(basis_x > 0, 1.0, np.where(basis_x < 0, 0.0, 0.5)).astype(np.float32)
	t = np.clip((basis_x + falloff / 2) / falloff, 0.0, 1.0)
	return (t * t * (3 - 2 * t)).astype(np.float32)

class RIG_OT_split_shape_key(bpy.types.Operator):
	bl_idname = "rig.split_shape_key"
	bl_label = "Split Shape Key"
	bl_description = ("Write the left and right halves of this key to its .L and .R keys, "
		"creating them if needed. Drivers and settings on existing sides are kept")
	bl_options = {'REGISTER', 'UNDO'}

	object_name: StringProperty(options={'HIDDEN'})
	shape_key_name: StringProperty(options={'HIDDEN'})
	falloff: FloatProperty(
		name="Falloff",
		description="Width of the blend across the center. Wider for shapes that cross the center",
		default=DEFAULT_FALLOFF, min=0.0, soft_max=0.05,
		subtype='DISTANCE', precision=4,
	)

	def invoke(self, context, event):
		obj = bpy.data.objects.get(self.object_name)
		if obj and obj.data.shape_keys:
			self.falloff = obj.data.shape_keys.get(falloff_prop(self.shape_key_name), DEFAULT_FALLOFF)
		return self.execute(context)

	def execute(self, context):
		obj = bpy.data.objects.get(self.object_name)
		key = obj.data.shape_keys if obj and obj.type == 'MESH' else None
		source = key.key_blocks.get(self.shape_key_name) if key else None
		if source is None or not can_split(key, source):
			if source is not None and is_key_driven(key, source):
				self.report({'ERROR'}, f"'{source.name}' is driven. Split it before connecting, "
					"then connect its .L and .R")
			else:
				self.report({'ERROR'}, f"'{self.shape_key_name}' can't be split")
			return {'CANCELLED'}

		# A locked side is skipped and the other still updated: the lock says which one to keep
		left_name, right_name = side_names(source.name)
		locked = [name for name in (left_name, right_name)
			if name in key.key_blocks and is_locked(key.key_blocks[name])]
		if len(locked) == 2:
			self.report({'ERROR'}, f"{left_name} and {right_name} are both locked")
			return {'CANCELLED'}

		# Edits made in edit mode only reach the key once edit mode is left
		was_editing = obj == context.object and obj.mode == 'EDIT'
		if was_editing:
			bpy.ops.object.mode_set(mode='OBJECT')

		count = len(obj.data.vertices)
		basis_x = read_co(key.reference_key, count)[:, 0]
		relative = read_co(source.relative_key, count)
		delta = read_co(source, count) - relative
		# The source's vertex group limits what it does; the sides get exactly that, so they
		# don't need a vertex group of their own and stray edits outside it don't come back
		if source.vertex_group in obj.vertex_groups:
			delta *= group_weights(obj, source.vertex_group)[:, None]
		weight_l = left_weights(basis_x, self.falloff)[:, None]

		created = []
		updated = []
		for name, weight in ((left_name, weight_l), (right_name, 1 - weight_l)):
			if name in locked:
				continue
			side = key.key_blocks.get(name)
			if side is None:
				side = obj.shape_key_add(name=name, from_mix=False)
				side.relative_key = source.relative_key
				side.slider_min = source.slider_min
				side.slider_max = source.slider_max
				created.append(name)
			else:
				updated.append(name)
			side.data.foreach_set("co", (relative + delta * weight).ravel())

		key[falloff_prop(source.name)] = self.falloff
		obj.data.update()

		# New sides are added at the bottom: move them to just under the source, .L then .R
		# (or under an existing .L). Sides that already existed stay where the user put them
		if created:
			anchor = key.key_blocks[left_name] if left_name not in created else source
			place_after(context, obj, anchor, created)
			obj.active_shape_key_index = key_index(key, source)

		if was_editing:
			bpy.ops.object.mode_set(mode='EDIT')

		parts = []
		if created:
			parts.append(f"created {', '.join(created)}")
		if updated:
			parts.append(f"updated {', '.join(updated)}")
		if locked:
			parts.append(f"skipped {locked[0]} (locked)")
		message = f"{source.name}: {'; '.join(parts)}"
		self.report({'WARNING'} if locked else {'INFO'}, message)
		return {'FINISHED'}

classes = (
	RIG_OT_split_shape_key,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
