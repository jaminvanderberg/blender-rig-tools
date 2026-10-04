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

def get_separator_string(context=None):
	pref = get_preferences(context)
	return pref.strip_separators.strip()

def get_strip_tags(context=None):
	pref = get_preferences(context)
	return [tag.strip() for tag in pref.strip_tags.split(",") if tag.strip()]

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
	show_selection_on_item_panel: BoolProperty(
		name="Show on Item Panel",
		description="Also show Select Bones by Name on the Item sidebar tab",
		default=True
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

	# User-facing naming boundaries
	def_template: StringProperty(
		name="DEF Bone",
		description="Template for DEF (deform) bones on the copy tool.",
		default="DEF-{name}"
	)
	org_template: StringProperty(
		name="Target/ORG Bone",
		description="Template for target/ORG bones on the copy tool.",
		default="ORG-{name}"
	)
	fk_template: StringProperty(
		name="FK Bone",
		description="Default template for FK bones created by the FK/tweak tool.",
		default="FK-{name}"
	)

	# Rig Structure Defaults
	root_bone_name: StringProperty(
		name="Root Bone",
		description="Name of root bone for rotation isolation",
		default="root"
	)
	torso_bone_name: StringProperty(
		name="Torso Bone",
		description="Name of torso bone for IK parent switching",
		default="torso"
	)
	hips_bone_name: StringProperty(
		name="Hips Bone",
		description="Name of hips bone for IK parent switching",
		default="hips"
	)
	chest_bone_name: StringProperty(
		name="Chest Bone",
		description="Name of chest bone for IK parent switching",
		default="chest"
	)
	head_bone_name: StringProperty(
		name="Head Bone",
		description="Name of head bone for IK parent switching",
		default="head"
	)
	property_bone_name: StringProperty(
		name="Property Bone",
		description="Name of bone holding custom properties",
		default="properties"
	)
	mch_collection_name: StringProperty(
		name="Non-Limb MCH Collection",
		description="Name of bone collection where non-limb MCH bones are created",
		default="MCH-TMP"
	)
	mch_parent_collection: StringProperty(
		name="MCH Parent Collection",
		description="Name of the parent collection for MCH collections",
		default="MCH"
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
	control_bone_color: EnumProperty(
		name="Master Control Color",
		description="Default theme color set for master control bones",
		items=BONE_COLOR_ITEMS,
		default='THEME02'
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
		box.prop(self, "show_selection_on_item_panel")

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
		box.label(text="Naming", icon='OUTLINER_DATA_ARMATURE')
		box.prop(self, "def_template")
		box.prop(self, "org_template")
		box.prop(self, "fk_template")

		box = layout.box()
		box.label(text="Rig Structure Defaults", icon='CON_ARMATURE')
		box.prop(self, "root_bone_name")
		box.prop(self, "torso_bone_name")
		box.prop(self, "hips_bone_name")
		box.prop(self, "chest_bone_name")
		box.prop(self, "head_bone_name")
		box.prop(self, "property_bone_name")
		box.prop(self, "mch_collection_name")
		box.prop(self, "mch_parent_collection")
		box.prop(self, "do_create_widgets")
		if self.do_create_widgets:
			box.prop(self, "widget_collection")
			box.prop(self, "widget_template")

		# Control Colors
		box = layout.box()
		box.label(text="Control Colors", icon='COLOR')
		box.prop(self, "fk_bone_color")
		box.prop(self, "ik_bone_color")
		box.prop(self, "control_bone_color")
		box.prop(self, "tweak_bone_color")
