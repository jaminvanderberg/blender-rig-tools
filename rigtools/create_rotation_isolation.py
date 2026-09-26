import bpy
from bpy.props import StringProperty, BoolProperty
from rigtools.armature_settings import get_armature_settings
from rigtools.tool.rotation_isolation import RotationIsolation

class RIG_OT_create_rotation_isolation(bpy.types.Operator):
	"""Create a isolate rotation mechanism for the selected bone and drive it by a custom property."""
	bl_idname = "rig.create_rotation_isolation"
	bl_label = "Create Rotation Isolation Mechanism"
	bl_options = {'REGISTER', 'UNDO'}
	bl_property = "property_name"

	property_name: StringProperty(
		name = "Property Name",
		default = "",
		description = "Name of the custom property driving the rotation isolation mechanism."
	)
	include_scale: BoolProperty(
		name = "Copy Scale",
		default = True,
		description = "Create a copy scale constraint."
	)
	disable_scale: BoolProperty(
		name = "Disable Scale",
		default = False,
		description = "Leave the copy scale constraint disabled."
	)    
	

	##################################################################################################
	# execute
	
	def execute(self, context):
	
		obj = context.object
		if not obj or obj.type != 'ARMATURE':
			self.report({'ERROR'}, "Active object must be an armature.")
			return {'CANCELLED'}
		
		if obj.mode == 'OBJECT':
			self.report({'ERROR'}, f"Can't use from Object mode")
			return {'CANCELLED'}
		
		settings = get_armature_settings(obj.data, context)

		# Switch to edit mode
		original_mode = obj.mode
		if obj.mode != 'EDIT':
			bpy.ops.object.mode_set(mode='EDIT')
			
		bone_data = obj.data

		if not bone_data.edit_bones.get(settings.root_bone_name):
			self.report({'ERROR'}, "Root bone not found")
			bpy.ops.object.mode_set(mode=original_mode)
			return {'CANCELLED'}

		if not bone_data.edit_bones.get(settings.property_bone_name):
			self.report({'ERROR'}, "Property bone not found")
			bpy.ops.object.mode_set(mode=original_mode)
			return {'CANCELLED'}

		if not context.selected_editable_bones:
			self.report({'ERROR'}, "No edit bones selected. Select at least one bone.")
			bpy.ops.object.mode_set(mode=original_mode)
			return {'CANCELLED'}
		
		isolation = RotationIsolation(
			property_name=self.property_name,
			include_scale=self.include_scale,
			disable_scale=self.disable_scale,
		)
		isolation.edit_mode(context, bone_data, [bone.name for bone in context.selected_editable_bones])

		bpy.ops.object.mode_set(mode='POSE')
		isolation.pose_mode(context)

		bpy.ops.object.mode_set(mode=original_mode)

		count = len(isolation.created_bones)
		self.report({'INFO'}, f"Successfully generated {count} rotation isolation mechanism{'s' if count != 1 else ''}.")              
			
		return {'FINISHED'}

	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self, width=350)

	def draw(self, context):
		layout = self.layout
			  
		# Primary clean focus
		layout.prop(self, "property_name")
		row = layout.row()
		row.prop(self, "include_scale")
		row.prop(self, "disable_scale")

classes = (
	RIG_OT_create_rotation_isolation,
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
	
	bpy.ops.rig.create_rotation_isolation('INVOKE_DEFAULT')