import bpy
from bpy.props import EnumProperty, StringProperty
from rigtools.panels.shape_keys.connection_status import get_live_connections_for_key, tidy_rig_connections
from rigtools.panels.shape_keys.key_drivers import build_key_drivers
from rigtools.panels.shape_keys.shape_key_utils import find_driver
from rigtools.rig_data.shape_key_connections import SHAPE_KEY_COMBINE_ITEMS, set_key_combine

class RIG_OT_set_key_combine(bpy.types.Operator):
	bl_idname = "rig.set_key_combine"
	bl_label = "Set Key Combine"
	bl_description = "Define how multiple bones' influence on a shape key are combined"
	bl_options = {'REGISTER', 'UNDO'}

	object_name: StringProperty(options={'HIDDEN'})
	armature_name: StringProperty(options={'HIDDEN'})
	shape_key_name: StringProperty(options={'HIDDEN'})
	combine: EnumProperty(items=SHAPE_KEY_COMBINE_ITEMS, default="MAX")

	def execute(self, context):
		mesh = bpy.data.objects.get(self.object_name)
		if not mesh:
			self.report({'ERROR'}, f"Object not found: '{self.object_name}'")
			return {'CANCELLED'}
		if mesh.type != 'MESH':
			self.report({'ERROR'}, f"Object '{self.object_name}' is not a mesh object")
			return {'CANCELLED'}

		key = mesh.data.shape_keys
		key_block = key.key_blocks.get(self.shape_key_name) if key else None
		if not key_block:
			self.report({'ERROR'}, f"Shape key not found: '{self.shape_key_name}'")
			return {'CANCELLED'}

		fcurve = find_driver(key, key_block.path_from_id("value"))
		if not fcurve:
			self.report({'ERROR'}, f"Shape key '{self.shape_key_name}' isn't driven")
			return {'CANCELLED'}

		armature_obj = bpy.data.objects.get(self.armature_name)
		if not armature_obj or armature_obj.type != 'ARMATURE':
			self.report({'ERROR'}, f"Armature not found: '{self.armature_name}'")
			return {'CANCELLED'}

		tidy_rig_connections(armature_obj)
		found = get_live_connections_for_key(armature_obj, mesh, key_block)
		set_key_combine(found, self.combine)
		build_key_drivers(armature_obj, mesh, key_block)

		self.report({'INFO'}, f"'{self.shape_key_name}' combines with {self.combine.upper()}")
		return {'FINISHED'}

classes = (
	RIG_OT_set_key_combine,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
