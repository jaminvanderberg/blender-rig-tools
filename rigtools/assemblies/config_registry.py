import bpy
from bpy.props import StringProperty

from rigtools.assemblies.assembly_data import find_assembly
from rigtools.assemblies.configs.ik_parent import (
	IkParentConfig,
	classes as ik_parent_classes,
	register as register_ik_parent_wm,
	unregister as unregister_ik_parent_wm,
)
from rigtools.assemblies.configs.skirt_ride import SkirtRideConfig, classes as skirt_ride_classes
from rigtools.assemblies.configs.skirt_collision import SkirtCollisionConfig, classes as skirt_collision_classes

CONFIGS = {
	IkParentConfig.id: IkParentConfig,
	SkirtRideConfig.id: SkirtRideConfig,
	SkirtCollisionConfig.id: SkirtCollisionConfig,
}


def iterate_configs(assembly):
	for config in CONFIGS.values():
		if config.present(assembly):
			yield config

def snapshot_configs(context, assembly) -> dict:
	stash = {}
	for config in iterate_configs(assembly):
		fn = getattr(config, "snapshot", None)
		if not callable(fn):
			continue
		data = fn(context, assembly)
		if data:
			stash[config.id] = data
	return stash

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
		draw_dialog = getattr(config, "draw_dialog", None)
		if callable(draw_dialog):
			draw_dialog(self.layout, assembly, context)
		else:
			config.draw(self.layout, assembly, context)

	def execute(self, context):
		wm = context.window_manager
		config = CONFIGS.get(wm.rigtools_assembly_config_id)
		assembly = find_assembly(context.object, wm.rigtools_assembly_config_uid)
		if not config or not assembly:
			self.report({'ERROR'}, "Config or assembly not found")
			return {'CANCELLED'}

		try:
			old = config.load(assembly)
			new = config.payload_from_wm(wm)
			config.apply(context, assembly, old, new)
		except Exception as e:
			self.report({'ERROR'}, str(e))
			return {'CANCELLED'}
		return {'FINISHED'}


classes = (
	RIG_OT_assembly_config,
	*ik_parent_classes,
	*skirt_ride_classes,
	*skirt_collision_classes,
)


def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	wm = bpy.types.WindowManager
	wm.rigtools_assembly_config_uid = StringProperty()
	wm.rigtools_assembly_config_id = StringProperty()
	register_ik_parent_wm()


def unregister():
	unregister_ik_parent_wm()
	del bpy.types.WindowManager.rigtools_assembly_config_id
	del bpy.types.WindowManager.rigtools_assembly_config_uid
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
