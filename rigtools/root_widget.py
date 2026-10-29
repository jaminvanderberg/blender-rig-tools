import bpy
from rigtools.armature_settings import get_armature_settings
from rigtools.assemblies.tool_data.bone_style import BoneStyle
from rigtools.preferences import get_preferences
from rigtools.utils.widget import ROOT_WIRE_WIDTH, apply_widget

def apply_root_widgets(context, obj):
	"""Styles the root and properties bones. Returns the names of any that weren't found."""
	settings = get_armature_settings(obj.data, context)
	pose_bones = obj.pose.bones
	missing = []

	root = pose_bones.get(settings.root_bone_name)
	if root:
		BoneStyle(widget='ROOT', color='root', wire_width=ROOT_WIRE_WIDTH).apply(context, root, side="", replace_widget=True)
	else:
		missing.append(settings.root_bone_name)

	properties = pose_bones.get(settings.property_bone_name)
	if properties:
		BoneStyle(widget='GEAR', color='root', wire_width=ROOT_WIRE_WIDTH).apply(context, properties, side="", replace_widget=True)
		properties.lock_location = (True, True, True)
		properties.lock_rotation = (True, True, True)
		properties.lock_scale = (True, True, True)
	else:
		missing.append(settings.property_bone_name)

	return missing		

class RIG_OT_apply_root_widgets(bpy.types.Operator):
	bl_idname = "rig.apply_root_widgets"
	bl_label = "Apply Root Widgets"
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		missing = apply_root_widgets(context, context.object)
		if missing:
			self.report({'WARNING'}, f"Bones not found: {', '.join(missing)}")
		else:
			self.report({'INFO'}, "Root and properties widgets applied")
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