import bpy
from rigtools.armature_settings import get_armature_settings
from rigtools.preferences import get_preferences
from rigtools.utils.widget import apply_widget

class RIG_OT_apply_root_widgets(bpy.types.Operator):
	bl_idname = "rig.apply_root_widgets"
	bl_label = "Apply Root Widgets"
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		obj = context.object
		armature_data = obj.data
		settings = get_armature_settings(armature_data, context)

		root = obj.pose.bones.get(settings.root_bone_name)
		if root is None:
			self.report({'ERROR'}, f"Root bone not found: {settings.root_bone_name}")
			return {'CANCELLED'}

		apply_widget(context, root, 'ROOT', replace=True)

		root.color.palette = get_preferences(context).control_bone_color
		root.custom_shape_wire_width = 1.5

		message = f"Root widget applied to {settings.root_bone_name}. "

		# Properties bone
		properties = obj.pose.bones.get(settings.property_bone_name)
		if properties is None:
			message += f"Properties bone not found: {settings.property_bone_name}"
			self.report({'WARNING'}, message)
			return {'FINISHED'}

		apply_widget(context, properties, 'GEAR', replace=True)

		properties.custom_shape_wire_width = 1.5
		properties.lock_location = (True, True, True)
		properties.lock_rotation = (True, True, True)
		properties.lock_scale = (True, True, True)

		message += f"Properties widget applied to {settings.property_bone_name}"

		self.report({'INFO'}, message)
		return {'FINISHED'}

classes = (
	RIG_OT_apply_root_widgets,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)
def unregister():
	for cls in classes:
		bpy.utils.unregister_class(cls)
if __name__ == "__main__":
	try:
		unregister()
	except Exception:
		pass
	register()
	
	bpy.ops.rig.apply_root_widgets('INVOKE_DEFAULT')		