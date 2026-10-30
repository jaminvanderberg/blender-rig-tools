import bpy
from rigtools.utils.widget import STANDARD_WIDGET_KEY, is_standard_widget

# Up to this many bones are named in the Custom Shape panel; more are just counted
NAMED_BONES_MAX = 3

def _bones_using(wgt):
	return [pb.name for obj in bpy.data.objects if obj.type == 'ARMATURE' for pb in obj.pose.bones if pb.custom_shape == wgt]

def draw_custom_shape(self, context):
	"""Appended to Blender's Custom Shape panel: shows which bones share this widget"""
	obj = context.object
	bone = context.bone
	pose_bone = obj.pose.bones.get(bone.name) if obj and obj.pose and bone else None
	if not pose_bone or not is_standard_widget(pose_bone.custom_shape):
		return
	wgt = pose_bone.custom_shape
	bones = _bones_using(wgt)
	used_by = ", ".join(bones) if len(bones) <= NAMED_BONES_MAX else f"{len(bones)} bones"

	# Two columns, lined up with the panel's own fields
	layout = self.layout
	layout.separator()
	split = layout.split(factor=0.4)
	left = split.row()
	left.alignment = 'RIGHT'
	left.label(text=f"Shared {wgt[STANDARD_WIDGET_KEY].title()}")
	split.label(text=used_by, icon='LINKED')

def draw_edit_warning(self, context):
	"""Appended to the 3D View header: editing a shared widget changes every bone that uses it"""
	wgt = context.edit_object
	if not is_standard_widget(wgt):
		return
	row = self.layout.row()
	row.alert = True
	row.label(text=f"Editing shared {wgt[STANDARD_WIDGET_KEY].title()} widget: changes {len(_bones_using(wgt))} bones", icon='ERROR')

def _custom_shape_panel():
	return getattr(bpy.types, "BONE_PT_display_custom_shape", None)

def register():
	panel = _custom_shape_panel()
	if panel:
		panel.append(draw_custom_shape)
	bpy.types.VIEW3D_HT_header.append(draw_edit_warning)

def unregister():
	bpy.types.VIEW3D_HT_header.remove(draw_edit_warning)
	panel = _custom_shape_panel()
	if panel:
		panel.remove(draw_custom_shape)
