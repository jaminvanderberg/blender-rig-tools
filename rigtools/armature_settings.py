import bpy
from rigtools.preferences import get_preferences

# Schema version for armature-stored rigtools data. Independent of addon bl_info version.
CURRENT_RIG_DATA_VERSION = 7

class RigToolsArmatureSettings(bpy.types.PropertyGroup):
	is_initialized: bpy.props.BoolProperty(
		name="Is Initialized",
		default=False,
		options={'HIDDEN'}
	)
	rig_data_version: bpy.props.IntProperty(
		name="Rig Data Version",
		description="Schema version of rigtools data stored on this armature",
		default=0,
		options={'HIDDEN'}
	)
	root_bone_name: bpy.props.StringProperty(
		name="Root",
		description="Root bone name",
		default=""
	)
	torso_bone_name: bpy.props.StringProperty(
		name="Torso",
		description="Torso bone name",
		default=""
	)
	hips_bone_name: bpy.props.StringProperty(
		name="Hips",
		description="Hips bone name",
		default=""
	)
	chest_bone_name: bpy.props.StringProperty(
		name="Chest",
		description="Chest bone name",
		default=""
	)
	head_bone_name: bpy.props.StringProperty(
		name="Head",
		description="Head bone name",
		default=""
	)
	property_bone_name: bpy.props.StringProperty(
		name="Property",
		description="Property bone name",
		default=""
	)

	ui_script: bpy.props.PointerProperty(type=bpy.types.Text)

def get_armature_settings(armature_data, context):
	if not armature_data.rigtools.is_initialized:
		initialize_armature_settings(armature_data, context)
	return armature_data.rigtools

def initialize_armature_settings(armature_data, context):
	settings = armature_data.rigtools
	was_initialized = settings.is_initialized

	prefs = get_preferences()
	settings.root_bone_name = prefs.root_bone_name
	settings.torso_bone_name = prefs.torso_bone_name
	settings.hips_bone_name = prefs.hips_bone_name
	settings.chest_bone_name = prefs.chest_bone_name
	settings.head_bone_name = prefs.head_bone_name
	settings.property_bone_name = prefs.property_bone_name
	if not was_initialized and not armature_data.rigtools_assemblies:
		settings.rig_data_version = CURRENT_RIG_DATA_VERSION
	settings.is_initialized = True


def needs_rig_upgrade(armature_data):
	version = armature_data.rigtools.rig_data_version
	if version >= CURRENT_RIG_DATA_VERSION:
		return False
	if version == 0 and not armature_data.rigtools_assemblies:
		return False
	return True

class RIG_OT_initialize_armature_settings(bpy.types.Operator):
	bl_idname = "rig.initialize_armature_settings"
	bl_label = "Initialize Armature Settings"
	bl_options = {'INTERNAL'}

	def execute(self, context):
		initialize_armature_settings(context.object.data, context)
		return {'FINISHED'}


class RIG_PT_armature_settings(bpy.types.Panel):
	bl_label = "Armature Settings"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = "Rig Tools"
	bl_options = {'DEFAULT_CLOSED'}

	@classmethod
	def poll(cls, context):
		return context.object and context.object.type == 'ARMATURE'

	def draw(self, context):
		settings = context.object.data.rigtools
		if not settings.is_initialized:
			self.layout.operator("rig.initialize_armature_settings", icon='FILE_CACHE')
			return

		layout = self.layout
		if needs_rig_upgrade(context.object.data):
			row = layout.row()
			row.alert = True
			row.operator(
				"rig.upgrade_rig",
				text=f"Upgrade Rig (v{settings.rig_data_version} -> v{CURRENT_RIG_DATA_VERSION})",
				icon='FILE_REFRESH',
			)
			layout.separator()

		col = layout.column(align=True)
		col.prop(settings, "root_bone_name")
		col.prop(settings, "torso_bone_name")
		col.prop(settings, "hips_bone_name")
		col.prop(settings, "chest_bone_name")
		col.prop(settings, "head_bone_name")
		col.prop(settings, "property_bone_name")

		layout.separator()
		layout.operator("rig.initialize_armature_settings", text="Reinitialize from Preferences", icon='FILE_REFRESH')

classes = (
	RIG_OT_initialize_armature_settings,
	RIG_PT_armature_settings,
	RigToolsArmatureSettings
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	bpy.types.Armature.rigtools = bpy.props.PointerProperty(type=RigToolsArmatureSettings)

def unregister():
	for cls in classes:
		bpy.utils.unregister_class(cls)
	del bpy.types.Armature.rigtools
