import bpy
from rigtools.armature_settings import CURRENT_RIG_DATA_VERSION, needs_rig_upgrade
from rigtools.utils.naming import find_side


def migrate_0_to_1(armature_data, context):
	"""Persist assembly.side from org bone names."""
	for assembly in armature_data.rigtools_assemblies:
		names = [bone.name for bone in assembly.org_states]
		assembly.side = find_side(names) or ""


MIGRATIONS = {
	0: migrate_0_to_1,
}


def upgrade_rig(armature_data, context):
	settings = armature_data.rigtools
	while settings.rig_data_version < CURRENT_RIG_DATA_VERSION:
		migrate = MIGRATIONS.get(settings.rig_data_version)
		if not migrate:
			raise ValueError(
				f"No migration from rig data version {settings.rig_data_version} "
				f"to {settings.rig_data_version + 1}."
			)
		migrate(armature_data, context)
		settings.rig_data_version += 1
	return settings.rig_data_version


class RIG_OT_upgrade_rig(bpy.types.Operator):
	bl_idname = "rig.upgrade_rig"
	bl_label = "Upgrade Rig"
	bl_description = "Apply pending rigtools data migrations to this armature"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(cls, context):
		obj = context.object
		return obj and obj.type == 'ARMATURE' and needs_rig_upgrade(obj.data)

	def execute(self, context):
		armature_data = context.object.data
		from_version = armature_data.rigtools.rig_data_version
		try:
			to_version = upgrade_rig(armature_data, context)
		except Exception as e:
			self.report({'ERROR'}, str(e))
			return {'CANCELLED'}

		self.report({'INFO'}, f"Upgraded rig data v{from_version} → v{to_version}")
		return {'FINISHED'}


classes = (
	RIG_OT_upgrade_rig,
)


def register():
	for cls in classes:
		bpy.utils.register_class(cls)


def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
