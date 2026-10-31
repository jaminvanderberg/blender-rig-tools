import bpy
from bpy.props import BoolProperty, EnumProperty, StringProperty
from rigtools.assemblies.assembly_data import styled_bone_refs
from rigtools.assemblies.configs.bone_styles import reset_style, style_diff
from rigtools.utils.widget import (
	STANDARD_WIDGET_TYPES, apply_widget, default_widget_class, find_standard_widget,
	is_standard_widget, is_widget_mesh_edited, restore_standard_widget,
)

# Up to this many bones are named in the Custom Shape panel; more are just counted
NAMED_BONES_MAX = 3

# Reset to Default checkbox -> (label, the bone settings it resets). Widget Mesh resets the shared widget itself
RESET_OPTIONS = {
	"widget": ("Widget", ("custom_shape",)),
	"widget_mesh": ("Widget Mesh", ()),
	"color": ("Color", ("color",)),
	"translation": ("Translation", ("custom_shape_translation",)),
	"rotation": ("Rotation", ("custom_shape_rotation_euler",)),
	"scale": ("Scale", ("custom_shape_scale_xyz",)),
	"wire_width": ("Wire Width", ("custom_shape_wire_width",)),
	"override_transform": ("Override Transform", ("custom_shape_transform",)),
	"display": ("Display", ("use_custom_shape_bone_size", "show_wire")),
}
SETTING_OPTIONS = {setting: option for option, (_label, settings) in RESET_OPTIONS.items() for setting in settings}

def _bones_using(wgt):
	return [pb.name for obj in bpy.data.objects if obj.type == 'ARMATURE' for pb in obj.pose.bones if pb.custom_shape == wgt]

def _selected_pose_bones(context):
	return context.selected_pose_bones or ([context.active_pose_bone] if context.active_pose_bone else [])

def _shared_widget(context, bone_ref):
	"""The shared widget the bone's style expects, if it exists"""
	style = bone_ref.get_style()
	return find_standard_widget(context, style.widget, style.widget_class) if style.widget else None

def _edited_options(context, pose_bones, first_only=False):
	"""The Reset to Default options with something to reset on these bones, in checkbox order"""
	bone_refs = styled_bone_refs(context.object.data)
	edited = set()
	checked_widgets = set() # each shared widget's mesh is hashed once
	for pose_bone in pose_bones:
		bone_ref = bone_refs.get(pose_bone.name)
		if bone_ref is None:
			continue
		edited.update(SETTING_OPTIONS[prop] for prop in style_diff(context, pose_bone, bone_ref).diff)
		wgt = _shared_widget(context, bone_ref)
		if wgt and "widget_mesh" not in edited and wgt.name not in checked_widgets:
			checked_widgets.add(wgt.name)
			if is_widget_mesh_edited(wgt):
				edited.add("widget_mesh")
		if first_only and edited:
			break
	return [option for option in RESET_OPTIONS if option in edited]

class RIG_OT_reset_bone_style(bpy.types.Operator):
	bl_idname = "rig.reset_bone_style"
	bl_label = "Reset Style to Default"
	bl_description = "Set the selected bones' custom shape and color back to the way their assembly built them"
	bl_options = {'REGISTER', 'UNDO'}

	widget: BoolProperty(name="Widget", description="Assign the shared widget the assembly built", default=True)
	widget_mesh: BoolProperty(name="Widget Mesh", description="Undo edits to the shared widget's mesh. Changes every bone that uses it", default=True)
	color: BoolProperty(name="Color", default=True)
	translation: BoolProperty(name="Translation", default=True)
	rotation: BoolProperty(name="Rotation", default=True)
	scale: BoolProperty(name="Scale", default=True)
	wire_width: BoolProperty(name="Wire Width", default=True)
	override_transform: BoolProperty(name="Override Transform", default=True)
	display: BoolProperty(name="Display", description="Wireframe and Scale to Bone Length", default=True)
	# Set by a field's reset button in the Bone Style panel: reset just that, with no dialog
	only: StringProperty(options={'HIDDEN', 'SKIP_SAVE'})

	@classmethod
	def poll(cls, context):
		obj = context.object
		if obj is None or obj.type != 'ARMATURE' or obj.pose is None:
			return False
		if not _edited_options(context, _selected_pose_bones(context), first_only=True):
			cls.poll_message_set("Nothing on the selected bones differs from the assembly default")
			return False
		return True

	def invoke(self, context, event):
		if self.only:
			return self.execute(context)
		# A dialog, because the Properties editor has no redo panel
		return context.window_manager.invoke_props_dialog(self)

	def draw(self, context):
		# Only what's edited; hidden checkboxes keep their values, and resetting an unedited setting changes nothing
		for option in _edited_options(context, _selected_pose_bones(context)):
			self.layout.prop(self, option)

	def execute(self, context):
		obj = context.object
		# A field's reset button leaves the remembered checkboxes alone
		options = [self.only] if self.only else [option for option in RESET_OPTIONS if getattr(self, option)]
		props = [prop for option in options for prop in RESET_OPTIONS[option][1]]

		bone_refs = styled_bone_refs(obj.data)
		reset = skipped = 0
		widgets = set() # (type, class): each shared widget is restored once
		for pose_bone in _selected_pose_bones(context):
			bone_ref = bone_refs.get(pose_bone.name)
			if bone_ref is None:
				skipped += 1
				continue
			reset_style(context, pose_bone, bone_ref, props)
			style = bone_ref.get_style()
			if style.widget not in (None, 'NONE'):
				widgets.add((style.widget, style.widget_class))
			reset += 1

		restored = []
		if "widget_mesh" in options:
			for widget_type, widget_class in widgets:
				wgt = find_standard_widget(context, widget_type, widget_class)
				if wgt and is_widget_mesh_edited(wgt):
					restored.append(restore_standard_widget(context, widget_type, widget_class).name)

		message = f"Reset {reset} bones"
		if restored:
			message += f", restored {', '.join(sorted(restored))}"
		if skipped:
			message += f" ({skipped} not built by RigTools, skipped)"
		self.report({'INFO'}, message)
		return {'FINISHED'}

class RIG_OT_change_widget(bpy.types.Operator):
	bl_idname = "rig.change_widget"
	bl_label = "Change Widget"
	bl_description = "Give the selected bones another shared widget. Kept on reconfigure; Reset to Default brings back the original"
	bl_options = {'REGISTER', 'UNDO'}

	widget_type: EnumProperty(
		name="Widget",
		items=[(t, default_widget_class(t), "") for t in STANDARD_WIDGET_TYPES] + [('NONE', "None", "No widget")],
	)

	@classmethod
	def poll(cls, context):
		obj = context.object
		return obj is not None and obj.type == 'ARMATURE' and obj.pose is not None and bool(_selected_pose_bones(context))

	def execute(self, context):
		# The type's default class: a class has one shape, so a bone's own class can't take another type
		pose_bones = _selected_pose_bones(context)
		for pose_bone in pose_bones:
			apply_widget(context, pose_bone, self.widget_type)
		self.report({'INFO'}, f"Changed the widget on {len(pose_bones)} bones")
		return {'FINISHED'}

def _label_row(layout, label, text, icon='NONE'):
	"""Two columns, lined up with the panel's own fields"""
	split = layout.split(factor=0.4)
	left = split.row()
	left.alignment = 'RIGHT'
	left.label(text=label)
	split.label(text=text, icon=icon)

def _field_row(layout, label, option, edited):
	"""A labeled row ending in the field's reset button, or a blank when it isn't edited.
	Returns the middle of the row for the field itself"""
	split = layout.split(factor=0.4)
	left = split.row()
	left.alignment = 'RIGHT'
	left.label(text=label)
	right = split.row(align=True)
	field = right.row(align=True)
	if option in edited:
		op = right.operator(RIG_OT_reset_bone_style.bl_idname, text="", icon='LOOP_BACK')
		op.only = option
	else:
		right.label(text="", icon='BLANK1')
	return field

class RIG_PT_bone_style(bpy.types.Panel):
	bl_label = "Bone Style"
	bl_idname = "RIG_PT_bone_style"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = "Rig Tools"

	@classmethod
	def poll(cls, context):
		return context.object and context.object.type == 'ARMATURE' and context.mode == 'POSE'

	def draw(self, context):
		layout = self.layout
		obj = context.object
		pose_bone = context.active_pose_bone
		bone_ref = styled_bone_refs(obj.data).get(pose_bone.name) if pose_bone else None
		if bone_ref is None:
			layout.label(text="Select a control built by an assembly", icon='INFO')
			return
		edited = set(_edited_options(context, [pose_bone]))

		wgt = pose_bone.custom_shape
		row = _field_row(layout, "Widget", "widget", edited)
		row.label(text=wgt.name if wgt else "None")
		row.operator_menu_enum(RIG_OT_change_widget.bl_idname, "widget_type", text="Change")

		shared = _shared_widget(context, bone_ref)
		if shared:
			bones = _bones_using(shared)
			used_by = ", ".join(bones) if len(bones) <= NAMED_BONES_MAX else f"{len(bones)} bones"
			_field_row(layout, "Widget Mesh", "widget_mesh", edited).label(text=used_by, icon='LINKED')

		_field_row(layout, "Translation", "translation", edited).prop(pose_bone, "custom_shape_translation", text="")
		_field_row(layout, "Rotation", "rotation", edited).prop(pose_bone, "custom_shape_rotation_euler", text="")
		_field_row(layout, "Scale", "scale", edited).prop(pose_bone, "custom_shape_scale_xyz", text="")
		_field_row(layout, "Wire Width", "wire_width", edited).prop(pose_bone, "custom_shape_wire_width", text="")
		_field_row(layout, "Override Transform", "override_transform", edited).prop_search(
			pose_bone, "custom_shape_transform", obj.pose, "bones", text="")
		row = _field_row(layout, "Display", "display", edited)
		row.prop(pose_bone.bone, "show_wire", text="Wireframe", toggle=True)
		row.prop(pose_bone, "use_custom_shape_bone_size", text="Bone Length", toggle=True)
		_field_row(layout, "Color", "color", edited).prop(pose_bone.color, "palette", text="")

		layout.separator()
		layout.operator(RIG_OT_reset_bone_style.bl_idname, text="Reset to Default", icon='LOOP_BACK')

def draw_custom_shape(self, context):
	"""Appended to Blender's Custom Shape panel: which bones share this widget, what's been edited, and Reset"""
	obj = context.object
	bone = context.bone
	pose_bone = obj.pose.bones.get(bone.name) if obj and obj.pose and bone else None
	if not pose_bone:
		return
	wgt = pose_bone.custom_shape
	bone_ref = styled_bone_refs(obj.data).get(pose_bone.name)
	if not is_standard_widget(wgt) and bone_ref is None:
		return

	layout = self.layout
	layout.separator()

	if is_standard_widget(wgt):
		bones = _bones_using(wgt)
		used_by = ", ".join(bones) if len(bones) <= NAMED_BONES_MAX else f"{len(bones)} bones"
		_label_row(layout, "Shared Widget", used_by, icon='LINKED')

	if bone_ref is not None:
		edited = _edited_options(context, [pose_bone])
		if edited:
			_label_row(layout, "Edited", ", ".join(RESET_OPTIONS[option][0] for option in edited))
		# Greyed out by poll when nothing on the selected bones is edited
		layout.operator(RIG_OT_reset_bone_style.bl_idname, text="Reset to Default", icon='LOOP_BACK')

def draw_pose_context_menu(self, context):
	"""Appended to the Pose mode right-click menu"""
	layout = self.layout
	layout.separator()
	layout.operator(RIG_OT_reset_bone_style.bl_idname, icon='LOOP_BACK')

def draw_edit_warning(self, context):
	"""Appended to the 3D View header: editing a shared widget changes every bone that uses it"""
	wgt = context.edit_object
	if not is_standard_widget(wgt):
		return
	row = self.layout.row()
	row.alert = True
	row.label(text=f"Editing shared widget: changes {len(_bones_using(wgt))} bones", icon='ERROR')

def _custom_shape_panel():
	return getattr(bpy.types, "BONE_PT_display_custom_shape", None)

classes = (
	RIG_OT_reset_bone_style,
	RIG_OT_change_widget,
	RIG_PT_bone_style,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	panel = _custom_shape_panel()
	if panel:
		panel.append(draw_custom_shape)
	bpy.types.VIEW3D_HT_header.append(draw_edit_warning)
	bpy.types.VIEW3D_MT_pose_context_menu.append(draw_pose_context_menu)

def unregister():
	bpy.types.VIEW3D_MT_pose_context_menu.remove(draw_pose_context_menu)
	bpy.types.VIEW3D_HT_header.remove(draw_edit_warning)
	panel = _custom_shape_panel()
	if panel:
		panel.remove(draw_custom_shape)
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
