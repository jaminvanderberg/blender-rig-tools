import bpy
from bpy.types import AddonPreferences
from bpy.props import StringProperty, IntProperty, EnumProperty, BoolProperty
from rigtools.utils.bone_colors import BONE_COLOR_ITEMS

addon_name = __package__.split('.')[0] if __package__ else "rigtools"

def get_preferences(context=None):
	if context is None:
		context = bpy.context
	return context.preferences.addons[addon_name].preferences

def get_separators(context=None):
	pref = get_preferences(context)
	return list(pref.strip_separators.strip())

class RigToolsPreferences(AddonPreferences):
	bl_idname = addon_name

	# Quick Bone Selection
	selection_buttons: StringProperty(
		name="Selection Buttons",
		description="Comma-separated list of button labels and search terms",
		default="FK, IK-, Tweak, DEF, ORG, MCH"
	)
	selection_columns: IntProperty(
		name="Columns",
		description="Number of columns for selection buttons in the panel",
		default=3,
		min=1,
		max=10
	)

	# Name Stripping
	strip_tags: StringProperty(
		name="Tags to Strip",
		description="Comma-separated list of prefixes/suffixes to strip from bone names",
		default="ORG, DEF, MCH, CTRL"
	)
	strip_separators: StringProperty(
		name="Separators",
		description="Separator characters used between tags and base names",
		default="-._"
	)

	# Naming Templates
	def_template: StringProperty(
		name="DEF Bone",
		description="Template for DEF (deform) bones.",
		default="DEF-{name}"
	)
	org_template: StringProperty(
		name="Target/ORG Bone",
		description="Template for target/ORG bones.",
		default="ORG-{name}"
	)
	fk_template: StringProperty(
		name="FK Bone",
		description="Template for FK bones.",
		default="FK-{name}"
	)
	ik_template: StringProperty(
		name="IK Controller Bone",
		description="Template for the IK controller bone. {name} is taken from the last bone in the chain.",
		default="{name}"
	)
	ik_pole_template: StringProperty(
		name="IK Pole Bone",
		description="Template for the IK pole bone. {name} is taken from the first bone in the chain.",
		default="{name}.pole"
	)
	ik_pole_vis_template: StringProperty(
		name="IK Pole Vis Target Bone",
		description="Template for the IK pole vis target bone. {name} is taken from the first bone in the chain.",
		default="VIS-{name}.pole"
	)
	ik_spline_template: StringProperty(
		name="IK Spline Bone",
		description="Template for the IK spline bone names. {i} is the position number (start, mid, end).",
		default="{name}.spline.{i}"
	)
	mch_template: StringProperty(
		name="MCH Bone",
		description="Template for standard MCH bones.",
		default="MCH-{name}"
	)
	ik_mch_template: StringProperty(
		name="MCH-IK Bone",
		description="Template for the IK MCH bones.",
		default="MCH-IK-{name}"
	)
	switch_template: StringProperty(
		name="Switch Bone",
		description="Template FK/IK switch control bones.",
		default="MCH-SWITCH-{name}"
	)
	tweak_template: StringProperty(
		name="Tweak Bone",
		description="Template for tweak bones.",
		default="{name}.tweak"
	)
	term_template: StringProperty(
		name="Terminal Tweak",
		description="Template using {name} as placeholder",
		default="{name}.tip.tweak"
	)
	socket_template: StringProperty(
		name="Socket Bone",
		description="Template using {name} as placeholder",
		default="MCH-SOCKET-{name}"
	)
	int_template: StringProperty(
		name="Intermediate Bone",
		description="Template using {name} as placeholder",
		default="MCH-INT-{name}"
	)

	# Rig Structure Defaults
	root_bone_name: StringProperty(
		name="Root Bone",
		description="Name of root bone for rotation isolation",
		default="root"
	)
	property_bone_name: StringProperty(
		name="Property Bone",
		description="Name of bone holding custom properties",
		default="properties"
	)
	do_create_widgets: BoolProperty(
		name="Create Widgets",
		description="Create widgets for the bones",
		default=True
	)
	widget_collection: StringProperty(
		name="Widget Collection",
		description="Name of collection where widgets are created",
		default="WGT"
	)
	widget_template: StringProperty(
		name="Widget Object",
		description="Template using {name} as placeholder",
		default="WGT-{name}"
	)
	spline_object_template: StringProperty(
		name="Spline Object",
		description="Template using {name} as placeholder",
		default="SPLINE-{name}"
	)

	# Theme Colors
	fk_bone_color: EnumProperty(
		name="FK Color",
		description="Default theme color set for FK controls",
		items=BONE_COLOR_ITEMS,
		default='THEME04'
	)
	ik_bone_color: EnumProperty(
		name="IK Color",
		description="Default theme color set for IK controls",
		items=BONE_COLOR_ITEMS,
		default='THEME01'
	)
	tweak_bone_color: EnumProperty(
		name="Tweak Color",
		description="Default theme color set for tweak controls",
		items=BONE_COLOR_ITEMS,
		default='THEME09'
	)

	def draw(self, context):
		layout = self.layout
		layout.use_property_split = True
		layout.use_property_decorate = False

		row = layout.row(align=True)
		row.operator("rig.export_preferences", text="Export Settings...", icon='EXPORT')
		row.operator("rig.import_preferences", text="Import Settings...", icon='IMPORT')

		# Quick Bone Selection
		box = layout.box()
		box.label(text="Quick Bone Selection", icon='RESTRICT_SELECT_OFF')
		box.prop(self, "selection_buttons")
		box.prop(self, "selection_columns")

		# Preview of selection buttons
		preview_box = box.box()
		preview_box.use_property_split = False
		preview_box.label(text="Button Layout Preview:")
		tags = [t.strip() for t in self.selection_buttons.split(",") if t.strip()]
		if tags:
			grid = preview_box.grid_flow(row_major = True, columns=self.selection_columns, even_columns=True, align=True)
			for tag in tags:
				grid.label(text=tag)

		# Name Stripping
		box = layout.box()
		box.label(text="Name Stripping", icon='SYNTAX_OFF')
		box.prop(self, "strip_tags")
		box.prop(self, "strip_separators")

		# Naming Templates
		box = layout.box()
		box.label(text="Naming Templates", icon='OUTLINER_DATA_ARMATURE')
		box.prop(self, "def_template")
		box.prop(self, "org_template")
		box.prop(self, "fk_template")
		box.prop(self, "ik_template")
		box.prop(self, "ik_pole_template")
		box.prop(self, "ik_pole_vis_template")
		box.prop(self, "mch_template")
		box.prop(self, "ik_mch_template")
		box.prop(self, "ik_spline_template")
		box.prop(self, "switch_template")
		box.prop(self, "tweak_template")
		box.prop(self, "term_template")
		box.prop(self, "socket_template")
		box.prop(self, "int_template")

		# Rig Structure Defaults
		box = layout.box()
		box.label(text="Rig Structure Defaults", icon='CON_ARMATURE')
		box.prop(self, "root_bone_name")
		box.prop(self, "property_bone_name")
		box.prop(self, "do_create_widgets")
		if self.do_create_widgets:
			box.prop(self, "widget_collection")
			box.prop(self, "widget_template")
		box.prop(self, "spline_object_template")

		# Control Colors
		box = layout.box()
		box.label(text="Control Colors", icon='COLOR')
		box.prop(self, "fk_bone_color")
		box.prop(self, "ik_bone_color")
		box.prop(self, "tweak_bone_color")
