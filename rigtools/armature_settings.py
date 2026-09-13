import bpy
from rigtools.preferences import get_preferences

class RigToolsArmatureSettings(bpy.types.PropertyGroup):
	is_initialized: bpy.props.BoolProperty(
		name="Is Initialized",
		default=False,
		options={'HIDDEN'}
	)
	root_bone_name: bpy.props.StringProperty(
		name="Root",
		description="Root bone name",
		default=""
	)
	property_bone_name: bpy.props.StringProperty(
		name="Property",
		description="Property bone name",
		default=""
	)
	do_create_widgets: bpy.props.BoolProperty(
		name="Create Widgets",
		description="Create widgets for the bones",
		default=True
	)
	widget_collection: bpy.props.StringProperty(
		name="Wgt Coll",
		description="Widget collection name",
		default=""
	)
	widget_template: bpy.props.StringProperty(
		name="Wgt Obj",
		description="Widget object name",
		default=""
	)

def get_armature_settings(armature_data, context):
	if not armature_data.rigtools.is_initialized:
		initialize_armature_settings(armature_data, context)
	return armature_data.rigtools

def initialize_armature_settings(armature_data, context):
	settings = armature_data.rigtools

	prefs = get_preferences()
	settings.root_bone_name = prefs.root_bone_name
	settings.property_bone_name = prefs.property_bone_name
	settings.do_create_widgets = prefs.do_create_widgets
	settings.widget_collection = prefs.widget_collection
	settings.widget_template = prefs.widget_template
	settings.is_initialized = True

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
		col = layout.column(align=True)
		col.prop(settings, "root_bone_name")
		col.prop(settings, "property_bone_name")
		col.prop(settings, "do_create_widgets")
		if settings.do_create_widgets:
			col.prop(settings, "widget_collection")
			col.prop(settings, "widget_template")

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
