import bpy
from bpy.props import StringProperty

from rigtools.assemblies.assembly_data import find_assembly
from rigtools.assemblies.configs.skirt_ride import SkirtRideConfig, SkirtRideLegSlot, classes as skirt_ride_classes


CONFIGS = {
	SkirtRideConfig.id: SkirtRideConfig,
}


def iterate_configs(assembly):
	for config in CONFIGS.values():
		if config.present(assembly):
			yield config


class RIG_OT_assembly_config(bpy.types.Operator):
	bl_idname = "rig.assembly_config"
	bl_label = "Assembly Config"
	bl_options = {'REGISTER', 'UNDO'}

	assembly_uid: StringProperty()
	config_id: StringProperty()

	def _config(self):
		return CONFIGS.get(self.config_id)

	def _assembly(self, context):
		return find_assembly(context.object, self.assembly_uid)

	def invoke(self, context, event):
		config = self._config()
		assembly = self._assembly(context)
		if not config or not assembly:
			self.report({'ERROR'}, "Config or assembly not found")
			return {'CANCELLED'}

		wm = context.window_manager
		wm.rigtools_assembly_config_uid = self.assembly_uid
		wm.rigtools_assembly_config_id = self.config_id
		config.sync_to_wm(wm, config.load(assembly))
		return context.window_manager.invoke_props_dialog(self, width=350)

	def draw(self, context):
		config = CONFIGS.get(context.window_manager.rigtools_assembly_config_id)
		assembly = find_assembly(context.object, context.window_manager.rigtools_assembly_config_uid)
		if not config or not assembly:
			return
		self.layout.label(text=config.name)
		if config.description:
			self.layout.label(text=config.description, icon='INFO')
		config.draw(self.layout, assembly, context)

	def execute(self, context):
		wm = context.window_manager
		config = CONFIGS.get(wm.rigtools_assembly_config_id)
		assembly = find_assembly(context.object, wm.rigtools_assembly_config_uid)
		if not config or not assembly:
			self.report({'ERROR'}, "Config or assembly not found")
			return {'CANCELLED'}

		old = config.load(assembly)
		new = config.payload_from_wm(wm)
		config.apply(context, assembly, old, new)
		return {'FINISHED'}


classes = (
	RIG_OT_assembly_config,
	*skirt_ride_classes,
)


def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	wm = bpy.types.WindowManager
	wm.rigtools_assembly_config_uid = StringProperty()
	wm.rigtools_assembly_config_id = StringProperty()
	wm.rigtools_skirt_ride_mch_name = StringProperty()
	wm.rigtools_skirt_ride_legs = bpy.props.CollectionProperty(type=SkirtRideLegSlot)


def unregister():
	del bpy.types.WindowManager.rigtools_skirt_ride_legs
	del bpy.types.WindowManager.rigtools_skirt_ride_mch_name
	del bpy.types.WindowManager.rigtools_assembly_config_id
	del bpy.types.WindowManager.rigtools_assembly_config_uid
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
