import bpy
from rigtools.utils.widget import STANDARD_WIDGET_KEY, is_standard_widget, make_widget_unique

class RIG_OT_make_widget_unique(bpy.types.Operator):
	bl_idname = "rig.make_widget_unique"
	bl_label = "Make Widget Unique"
	bl_description = "Give each selected bone its own copy of its widget, so editing it changes only that bone"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(cls, context):
		return context.mode == 'POSE' and context.selected_pose_bones

	def execute(self, context):
		count = 0
		for pose_bone in context.selected_pose_bones:
			if is_standard_widget(pose_bone.custom_shape):
				make_widget_unique(context, pose_bone)
				count += 1
		self.report({'INFO'}, f"Made {count} widget{'s' if count != 1 else ''} unique")
		return {'FINISHED'}

def _shared_by(wgt):
	return wgt.users - 1 # minus the widget collection

def draw_custom_shape(self, context):
	"""Appended to Blender's Custom Shape panel"""
	obj = context.object
	bone = context.bone
	pose_bone = obj.pose.bones.get(bone.name) if obj and obj.pose and bone else None
	if not pose_bone or not is_standard_widget(pose_bone.custom_shape):
		return
	layout = self.layout
	layout.label(text=f"Shared widget, used by {_shared_by(pose_bone.custom_shape)} bones", icon='LINKED')
	layout.operator(RIG_OT_make_widget_unique.bl_idname, icon='DUPLICATE')

def draw_edit_warning(self, context):
	"""Appended to the 3D View header: editing a shared widget changes every bone that uses it"""
	wgt = context.edit_object
	if not is_standard_widget(wgt):
		return
	row = self.layout.row()
	row.alert = True
	row.label(text=f"Editing shared {wgt[STANDARD_WIDGET_KEY].title()} widget: changes {_shared_by(wgt)} bones", icon='ERROR')

classes = (
	RIG_OT_make_widget_unique,
)

def _custom_shape_panel():
	return getattr(bpy.types, "BONE_PT_display_custom_shape", None)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	panel = _custom_shape_panel()
	if panel:
		panel.append(draw_custom_shape)
	bpy.types.VIEW3D_HT_header.append(draw_edit_warning)

def unregister():
	bpy.types.VIEW3D_HT_header.remove(draw_edit_warning)
	panel = _custom_shape_panel()
	if panel:
		panel.remove(draw_custom_shape)
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
