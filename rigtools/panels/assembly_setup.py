from dataclasses import dataclass
import bpy
from rigtools.armature_settings import get_armature_settings


def validate_setup_context(context, *, check_property_bone=True):
	obj = context.object
	if not obj or obj.type != 'ARMATURE':
		return "Active object must be an armature."

	if obj.mode == 'OBJECT':
		return "Can't use from Object mode"

	settings = get_armature_settings(obj.data, context)
	if check_property_bone and settings.property_bone_name not in obj.pose.bones:
		return f"Property bone '{settings.property_bone_name}' not found."

	return None

class SetupEditState:
	def __init__(self, mode: str, mirror: bool):
		self.mode = mode
		self.mirror = mirror

	def restore(self, context):
		if context.object.mode != self.mode:
			bpy.ops.object.mode_set(mode=self.mode)
		context.object.data.use_mirror_x = self.mirror
	
	def restore_mirror(self, context):
		context.object.data.use_mirror_x = self.mirror

def begin_setup_edit(context) -> SetupEditState:
	obj = context.object
	# Switch to edit mode
	original_mode = obj.mode
	if obj.mode != 'EDIT':
		bpy.ops.object.mode_set(mode='EDIT')

	original_mirror = obj.data.use_mirror_x
	obj.data.use_mirror_x = False

	return SetupEditState(original_mode, original_mirror)
