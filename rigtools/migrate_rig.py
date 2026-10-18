import bpy

from rigtools.armature_settings import CURRENT_RIG_DATA_VERSION, needs_rig_upgrade
from rigtools.utils.naming import name_bone

# Note to AI: ALWAYS provide thorough debug output when migrating data.

def migrate_3_to_4(armature_data, context):
	"""Backfill tip-tweak reparent rules and sync dependent stored parents."""
	bones = armature_data.bones
	print(f"migrate_3_to_4: {len(armature_data.rigtools_assemblies)} assemblies")

	rules_added = 0
	parents_synced = 0
	skipped_no_org = 0
	skipped_no_tip = 0
	skipped_existing = 0

	for assembly in armature_data.rigtools_assemblies:
		print(f"assembly: {assembly.name} ({assembly.assembly_type})")

		if not assembly.org_states:
			skipped_no_org += 1
			print("  skip: no org_states")
			continue

		owned = {ref.name for ref in assembly.mechanism_bones}
		existing_from = {rule.from_bone for rule in assembly.reparent_rules}
		found_tip = False

		for org_state in assembly.org_states:
			org_name = org_state.name
			tip = name_bone("term", org_name)
			tip_owned = tip in owned
			print(f"  org={org_name} tip={tip} tip_owned={tip_owned}")

			if not tip_owned:
				continue

			found_tip = True
			if tip in existing_from:
				skipped_existing += 1
				print(f"  skip: rule already exists for {tip}")
				continue

			row = assembly.reparent_rules.add()
			row.from_bone = tip
			row.to_bone = org_name
			existing_from.add(tip)
			rules_added += 1
			print(f"  rule: {tip} -> {org_name}")

			for other in armature_data.rigtools_assemblies:
				if other.uid == assembly.uid:
					continue
				for state in list(other.org_states) + list(other.twist_states):
					if state.parent != org_name:
						continue
					bone = bones.get(state.name)
					live_parent = bone.parent.name if bone and bone.parent else None
					print(
						f"  check {other.name}.{state.name}: "
						f"stored={state.parent} live={live_parent}"
					)
					if bone and bone.parent and bone.parent.name == tip:
						state.parent = tip
						parents_synced += 1
						print(f"  sync: {other.name}.{state.name} parent {org_name} -> {tip}")

		if not found_tip:
			skipped_no_tip += 1
			print("  skip: no owned tip tweak for any org")

	print(
		f"migrate_3_to_4 done: rules_added={rules_added} "
		f"parents_synced={parents_synced} "
		f"skipped_existing={skipped_existing} "
		f"skipped_no_org={skipped_no_org} "
		f"skipped_no_tip={skipped_no_tip}"
	)


MIGRATIONS = {
	3: migrate_3_to_4,
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

		self.report({'INFO'}, f"Upgraded rig data v{from_version} -> v{to_version}")
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
