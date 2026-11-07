import bpy
from bpy.props import BoolProperty, StringProperty

class RIG_OT_connect_shape_key(bpy.types.Operator):
	bl_idname = "rig.connect_shape_key"
	bl_label = "Connect Shape Key"
	bl_description = "Drive this shape key from the active bone's current pose"
	bl_options = {'REGISTER', 'UNDO'}

	object_name: StringProperty(options={'HIDDEN'})
	shape_key_name: StringProperty(options={'HIDDEN'})

	invert: BoolProperty(
		name="Invert",
		description="The key is 1 at rest and 0 at the extreme",
		default=False,
	)

	@classmethod
	def poll(cls, context):
		return (context.mode == 'POSE'
			and context.active_pose_bone is not None)

	def execute(self, context):
		obj = bpy.data.objects[self.object_name]
		key_block = obj.data.shape_keys.key_blocks[self.shape_key_name]
		pose_bone = context.active_pose_bone

		self.report({'INFO'},
			f"Connect {key_block.name} to {pose_bone.name} (not built yet)")
		return {'FINISHED'}

classes = (
	RIG_OT_connect_shape_key,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
