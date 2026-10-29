import bpy
import json

from rigtools.armature_settings import CURRENT_RIG_DATA_VERSION, needs_rig_upgrade
from rigtools.assemblies.limb_collections import ensure_limb_collections
from rigtools.assemblies.tool_data.bone_style import BoneStyle
from rigtools.utils.naming import limb_group_label, name_bone

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


def migrate_4_to_5(armature_data, context):
	"""Clear org_children; tip handoff is owned by reparent_rules."""
	print(f"migrate_4_to_5: {len(armature_data.rigtools_assemblies)} assemblies")
	cleared_rows = 0
	cleared_assemblies = 0

	for assembly in armature_data.rigtools_assemblies:
		n = len(assembly.org_children)
		if not n:
			print(f"  {assembly.name}: org_children empty")
			continue
		names = [child.name for child in assembly.org_children]
		print(f"  {assembly.name}: clearing {n} org_children: {names}")
		assembly.org_children.clear()
		cleared_rows += n
		cleared_assemblies += 1

	print(
		f"migrate_4_to_5 done: cleared_assemblies={cleared_assemblies} "
		f"cleared_rows={cleared_rows}"
	)


def migrate_5_to_6(armature_data, context):
	"""Backfill ui_label (Rig UI property group label) from limb name and side."""
	print(f"migrate_5_to_6: {len(armature_data.rigtools_assemblies)} assemblies")
	labeled = 0
	fallback = 0

	for assembly in armature_data.rigtools_assemblies:
		limb = (assembly.get_options().get("limb_property_base_name") or "").strip()
		label = limb_group_label(limb, assembly.side)
		if not label:
			label = assembly.name
			fallback += 1
			print(f"  {assembly.name}: no limb name (side={assembly.side!r}), using assembly name")
		else:
			labeled += 1
			print(f"  {assembly.name}: limb={limb!r} side={assembly.side!r} -> {label!r}")
		if assembly.ui_label and assembly.ui_label != label:
			print(f"    overwriting existing ui_label {assembly.ui_label!r}")
		assembly.ui_label = label

	print(
		f"migrate_5_to_6 done: labeled={labeled} "
		f"fallback_to_name={fallback}"
	)


def migrate_6_to_7(armature_data, context):
	"""Convert the fk_widget_taper float option to the taper_fk_widgets bool."""
	print(f"migrate_6_to_7: {len(armature_data.rigtools_assemblies)} assemblies")
	converted = 0
	skipped = 0

	for assembly in armature_data.rigtools_assemblies:
		options = assembly.get_options()
		if "fk_widget_taper" not in options:
			skipped += 1
			print(f"  {assembly.name} ({assembly.assembly_type}): no fk_widget_taper")
			continue
		old_value = options.pop("fk_widget_taper")
		options["taper_fk_widgets"] = old_value > 0
		assembly.options_json = json.dumps(options)
		converted += 1
		print(f"  {assembly.name} ({assembly.assembly_type}): fk_widget_taper={old_value!r} -> taper_fk_widgets={options['taper_fk_widgets']}")

	print(
		f"migrate_6_to_7 done: converted={converted} "
		f"skipped={skipped}"
	)


def migrate_7_to_8(armature_data, context):
	"""Convert the removed 'master' role to 'control' and remove the .Master collections."""
	if armature_data.is_editmode:
		raise ValueError("Upgrade from Object or Pose Mode (collections read as empty in Edit Mode)")
	print(f"migrate_7_to_8: {len(armature_data.rigtools_assemblies)} assemblies")
	converted = 0
	skipped = 0

	for assembly in armature_data.rigtools_assemblies:
		master_refs = [
			ref for ref in assembly.mechanism_bones
			if any(role.name == "master" for role in ref.roles)
		]
		if not master_refs:
			print(f"  {assembly.name} ({assembly.assembly_type}): no master bones")
			continue
		limb = (assembly.get_options().get("limb_property_base_name") or "").strip()
		if not limb:
			skipped += len(master_refs)
			print(f"  {assembly.name}: {len(master_refs)} master bones but no limb name, skipping")
			continue

		row = ensure_limb_collections(armature_data, limb, assembly.side, promote=True)
		print(f"  {assembly.name}: limb={limb!r} side={assembly.side!r} fk={row.fk!r} control={row.control!r}")
		for ref in master_refs:
			for role in ref.roles:
				if role.name == "master":
					role.name = "control"
			ref.add_style(BoneStyle(color="control"))
			if ref.name not in armature_data.bones:
				print(f"    {ref.name}: role converted, bone missing from armature")
				continue
			row.add_bone(armature_data, ref.name, [role.name for role in ref.roles])
			converted += 1
			print(f"    {ref.name}: master -> control ({row.control!r})")

	removed = 0
	kept = 0
	all_collections = getattr(armature_data, "collections_all", armature_data.collections)
	layout = armature_data.rig_ui_layout
	for row in armature_data.rigtools_limb_collections:
		master_name = row.get("master")
		if master_name is None:
			continue
		del row["master"]
		coll = all_collections.get(master_name)
		if coll is None:
			print(f"  {row.limb!r} {row.side!r}: cleared master={master_name!r}, collection already gone")
			continue
		if coll.bones:
			kept += 1
			print(f"  {row.limb!r} {row.side!r}: kept {master_name!r}, still has {len(coll.bones)} bones")
			continue
		armature_data.collections.remove(coll)
		for i in range(len(layout) - 1, -1, -1):
			if not layout[i].is_gap and layout[i].collection_name == master_name:
				layout.remove(i)
		removed += 1
		print(f"  {row.limb!r} {row.side!r}: removed empty {master_name!r} and its layout entry")

	print(
		f"migrate_7_to_8 done: converted={converted} skipped={skipped} "
		f"removed_collections={removed} kept_collections={kept}"
	)


MIGRATIONS = {
	3: migrate_3_to_4,
	4: migrate_4_to_5,
	5: migrate_5_to_6,
	6: migrate_6_to_7,
	7: migrate_7_to_8,
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
