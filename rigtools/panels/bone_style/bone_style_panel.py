import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, StringProperty
from rigtools.assemblies.assembly_data import styled_bone_refs
from rigtools.assemblies.configs.bone_styles import reset_style, style_diff
from rigtools.utils.widget import (
	STANDARD_WIDGET_TYPES, UNIFORM_SCALE_WIDGETS, Z_SLIDE_WIDGET_CLASSES, apply_widget,
	default_widget_class, find_standard_widget, is_standard_widget, is_widget_mesh_edited,
	restore_standard_widget, restore_widget_mesh, standard_widget_type,
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

def _edited_widget(pose_bone):
	"""The bone's shared widget, if its mesh has been edited and RigTools knows how to rebuild it"""
	wgt = pose_bone.custom_shape if pose_bone else None
	return wgt if standard_widget_type(wgt) and is_widget_mesh_edited(wgt) else None

KEEP_COPY_NAME = "Keep a copy of the edited mesh"
KEEP_COPY_DESCRIPTION = "Move the edited mesh to a new WGT-EDITED- object instead of deleting it"

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
	keep_copy: BoolProperty(name=KEEP_COPY_NAME, description=KEEP_COPY_DESCRIPTION, default=True)
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
		edited = _edited_options(context, _selected_pose_bones(context))
		for option in edited:
			self.layout.prop(self, option)
		if "widget_mesh" in edited:
			self.layout.separator()
			self.layout.prop(self, "keep_copy")

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
		copies = []
		if "widget_mesh" in options:
			for widget_type, widget_class in widgets:
				wgt = find_standard_widget(context, widget_type, widget_class)
				if wgt and is_widget_mesh_edited(wgt):
					copy = restore_standard_widget(context, widget_type, widget_class, self.keep_copy)
					restored.append(wgt.name)
					if copy:
						copies.append(copy.name)

		message = f"Reset {reset} bones"
		if restored:
			message += f", restored {', '.join(sorted(restored))}"
		if copies:
			message += f", kept {', '.join(sorted(copies))}"
		if skipped:
			message += f" ({skipped} not built by RigTools, skipped)"
		self.report({'INFO'}, message)
		return {'FINISHED'}

class RIG_OT_reset_widget_mesh(bpy.types.Operator):
	bl_idname = "rig.reset_widget_mesh"
	bl_label = "Reset Widget Mesh"
	bl_description = "Undo edits to the active bone's widget. It's shared, so this changes every bone that uses it"
	bl_options = {'REGISTER', 'UNDO'}

	keep_copy: BoolProperty(name=KEEP_COPY_NAME, description=KEEP_COPY_DESCRIPTION, default=True)

	@classmethod
	def poll(cls, context):
		return _edited_widget(context.active_pose_bone) is not None

	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self, confirm_text="Reset")

	def draw(self, context):
		wgt = _edited_widget(context.active_pose_bone)
		count = len(_bones_using(wgt))
		self.layout.label(text=f"Restores {wgt.name} on {count} bone{'s' if count != 1 else ''}")
		self.layout.prop(self, "keep_copy")

	def execute(self, context):
		wgt = _edited_widget(context.active_pose_bone)
		copy = restore_widget_mesh(wgt, self.keep_copy)
		message = f"Restored {wgt.name}"
		if copy:
			message += f", kept {copy.name}"
		self.report({'INFO'}, message)
		return {'FINISHED'}

class RIG_OT_change_widget(bpy.types.Operator):
	bl_idname = "rig.change_widget"
	bl_label = "Change Widget"
	bl_description = ("Give the selected bones another shared widget. "
		"On assembly bones it's kept on reconfigure, and Reset to Default brings back the original")
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
		# Only the selected bones change, so Reset to Default undoes exactly what this did
		pose_bones = _selected_pose_bones(context)
		for pose_bone in pose_bones:
			style = _bone_style(pose_bone)
			widget_class = None # the type's default class, shared with every other bone of that shape
			if style and style.widget_class:
				# The class's own widget for this shape. Its original widget is left alone,
				# so hand edits to it come back with it
				widget_class = style.widget_class
				if self.widget_type != style.widget:
					widget_class = f"{widget_class}-{default_widget_class(self.widget_type)}"
			apply_widget(context, pose_bone, self.widget_type, widget_class)
		self.report({'INFO'}, f"Changed the widget on {len(pose_bones)} bones")
		return {'FINISHED'}

def _bone_style(pose_bone):
	bone_ref = styled_bone_refs(pose_bone.id_data.data).get(pose_bone.name)
	return bone_ref.get_style() if bone_ref else None

def _widget_label(wgt):
	"""The Change menu's text: the current widget's type, as the menu lists it"""
	if wgt is None:
		return "None"
	widget_type = standard_widget_type(wgt)
	return default_widget_class(widget_type) if widget_type else wgt.name

def _scaled_axes(pose_bone):
	"""The axes Scale changes. Most widgets keep Y, the bone's length; round and flat widgets,
	and a user's own widgets, scale on all three"""
	widget_type = standard_widget_type(pose_bone.custom_shape)
	if widget_type is None and is_standard_widget(pose_bone.custom_shape):
		style = _bone_style(pose_bone) # made before the type was stored
		widget_type = style.widget if style else None
	if widget_type is None or widget_type in UNIFORM_SCALE_WIDGETS:
		return (0, 1, 2)
	return (0, 2)

def _default_scale(pose_bone):
	style = _bone_style(pose_bone)
	return (style.scale if style else None) or (1.0, 1.0, 1.0)

def _get_scale(pose_bone):
	"""Size relative to how the assembly built it. X is one of the scaled axes for every widget"""
	default_x = _default_scale(pose_bone)[0]
	return pose_bone.custom_shape_scale_xyz[0] / default_x if default_x else 1.0

def _set_scale(pose_bone, value):
	default = _default_scale(pose_bone)
	scale = list(pose_bone.custom_shape_scale_xyz)
	for axis in _scaled_axes(pose_bone):
		scale[axis] = default[axis] * value
	pose_bone.custom_shape_scale_xyz = scale

def _slide_axis(pose_bone):
	# The assembly's class, not the live widget's: Change Widget doesn't turn the bone
	style = _bone_style(pose_bone)
	return 2 if style and style.widget_class in Z_SLIDE_WIDGET_CLASSES else 1

def _get_slide(pose_bone):
	return pose_bone.custom_shape_translation[_slide_axis(pose_bone)]

def _set_slide(pose_bone, value):
	translation = list(pose_bone.custom_shape_translation)
	translation[_slide_axis(pose_bone)] = value
	pose_bone.custom_shape_translation = translation

def _label_row(layout, label, text, icon='NONE'):
	"""Two columns, lined up with the panel's own fields"""
	split = layout.split(factor=0.4)
	left = split.row()
	left.alignment = 'RIGHT'
	left.label(text=label)
	split.label(text=text, icon=icon)

def _field_row(layout, label, option, edited, stacked=False, expand=None):
	"""A labeled row ending in the field's reset button, or a blank when it isn't edited.
	expand: a window manager toggle; the label becomes a button that flips it.
	Returns the middle of the row for the field itself"""
	split = layout.split(factor=0.4)
	left = split.row()
	left.alignment = 'RIGHT'
	if expand:
		wm = bpy.context.window_manager
		icon = 'DISCLOSURE_TRI_DOWN' if getattr(wm, expand) else 'DISCLOSURE_TRI_RIGHT'
		left.prop(wm, expand, text=label, icon=icon, emboss=False)
	else:
		left.label(text=label)
	right = split.row(align=True)
	field = right.column(align=True) if stacked else right.row(align=True)
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
	bl_options = {'DEFAULT_CLOSED'} # a finishing tool, used after the rig is built

	@classmethod
	def poll(cls, context):
		return context.object and context.object.type == 'ARMATURE' and context.mode == 'POSE'

	def draw(self, context):
		layout = self.layout
		pose_bone = context.active_pose_bone
		if pose_bone is None:
			layout.label(text="Select a bone", icon='INFO')
			return
		# Empty for bones no assembly built: there's no default to reset to
		edited = set(_edited_options(context, [pose_bone]))

		wm = context.window_manager

		row = _field_row(layout, "Widget", "widget", edited)
		row.operator_menu_enum(RIG_OT_change_widget.bl_idname, "widget_type", text=_widget_label(pose_bone.custom_shape))
		if _edited_widget(pose_bone):
			# Only takes a row when there's an edit to undo
			row = layout.row()
			row.alignment = 'CENTER'
			row.operator(RIG_OT_reset_widget_mesh.bl_idname, icon='LOOP_BACK')

		if wm.rigtools_bone_style_translation:
			_field_row(layout, "Translation", "translation", edited, stacked=True, expand="rigtools_bone_style_translation").prop(
				pose_bone, "custom_shape_translation", text="")
		else:
			_field_row(layout, "Slide", "translation", edited, expand="rigtools_bone_style_translation").prop(
				pose_bone, "rigtools_style_slide", text="")
		_field_row(layout, "Rotation", "rotation", edited, stacked=True).prop(pose_bone, "custom_shape_rotation_euler", text="")
		if wm.rigtools_bone_style_scale:
			_field_row(layout, "Scale", "scale", edited, stacked=True, expand="rigtools_bone_style_scale").prop(
				pose_bone, "custom_shape_scale_xyz", text="")
		else:
			_field_row(layout, "Scale", "scale", edited, expand="rigtools_bone_style_scale").prop(
				pose_bone, "rigtools_style_scale", text="")
		_field_row(layout, "Wire Width", "wire_width", edited).prop(pose_bone, "custom_shape_wire_width", text="")
		_field_row(layout, "Color", "color", edited).prop(pose_bone.color, "palette", text="")

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
	RIG_OT_reset_widget_mesh,
	RIG_OT_change_widget,
	RIG_PT_bone_style,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	# Single-number views of the custom shape vectors; they store nothing themselves
	bpy.types.PoseBone.rigtools_style_scale = FloatProperty(
		name="Scale", description="Widget size relative to how the assembly built it",
		get=_get_scale, set=_set_scale, min=0.0, soft_max=10.0, step=10, precision=3,
	)
	bpy.types.PoseBone.rigtools_style_slide = FloatProperty(
		name="Slide", description="Move the widget along the bone, or up the body for torso controls",
		get=_get_slide, set=_set_slide, subtype='DISTANCE', step=1, precision=3,
	)
	# Which Bone Style fields show X/Y/Z. Kept per session, not saved in the file
	bpy.types.WindowManager.rigtools_bone_style_translation = BoolProperty(name="Show X/Y/Z")
	bpy.types.WindowManager.rigtools_bone_style_scale = BoolProperty(name="Show X/Y/Z")
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
	del bpy.types.WindowManager.rigtools_bone_style_scale
	del bpy.types.WindowManager.rigtools_bone_style_translation
	del bpy.types.PoseBone.rigtools_style_slide
	del bpy.types.PoseBone.rigtools_style_scale
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
