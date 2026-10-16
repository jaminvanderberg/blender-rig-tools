import json

import bpy

from rigtools.armature_settings import CURRENT_RIG_DATA_VERSION, needs_rig_upgrade
from rigtools.assemblies.limb_collections import ensure_limb_collections
from rigtools.tool.ik_parent import CONFIG_KEY, CONSTRAINT_NAME
from rigtools.utils.naming import find_side, name_collection


def migrate_0_to_1(armature_data, context):
	"""Persist assembly.side from org bone names."""
	for assembly in armature_data.rigtools_assemblies:
		names = [bone.name for bone in assembly.org_states]
		assembly.side = find_side(names) or ""


def migrate_1_to_2(armature_data, context):
	"""Persist IK parent config payloads for surgical parent updates."""
	obj = context.object
	if not obj or obj.type != 'ARMATURE' or obj.data != armature_data:
		raise ValueError("Active armature is required to migrate IK parent config")

	pose_bones = obj.pose.bones
	bones = armature_data.bones

	for assembly in armature_data.rigtools_assemblies:
		options = json.loads(assembly.options_json or "{}")
		if not options.get("ik_parent"):
			continue
		if options.get(CONFIG_KEY):
			continue
		if assembly.assembly_type != 'IK':
			continue

		property_name = ""
		for prop in assembly.properties:
			if prop.role == "IK_PARENT":
				property_name = prop.name
				break
		if not property_name:
			raise ValueError(
				f"Assembly '{assembly.name}' has IK parent enabled but no IK_PARENT property"
			)

		parent_bone_names = []
		for ref in assembly.mechanism_bones:
			pb = pose_bones.get(ref.name)
			if not pb:
				continue
			if any(
				constraint.type == 'ARMATURE' and constraint.name == CONSTRAINT_NAME
				for constraint in pb.constraints
			):
				parent_bone_names.append(ref.name)

		if not parent_bone_names:
			raise ValueError(
				f"Assembly '{assembly.name}' has IK parent enabled but no '{CONSTRAINT_NAME}' constraints"
			)

		mch0 = bones.get(parent_bone_names[0])
		if not mch0 or not mch0.children:
			raise ValueError(
				f"Assembly '{assembly.name}' IK parent bone '{parent_bone_names[0]}' has no child control"
			)
		self_parent_name = mch0.children[0].name
		self_parent_mch = parent_bone_names[1] if len(parent_bone_names) > 1 else ""
		add_self = bool(options.get("add_ik_control_as_pole_parent", False))
		self_label = options.get("ik_parent_self_parent_label") or "Self"

		options[CONFIG_KEY] = {
			"property_name": property_name,
			"parent_bone_names": parent_bone_names,
			"self_parent_name": self_parent_name,
			"self_parent_mch": self_parent_mch,
			"self_parent_label": self_label,
			"add_ik_control_as_pole_parent": add_self,
		}
		assembly.options_json = json.dumps(options)


def migrate_2_to_3(armature_data, context):
	"""Build rigtools_limb_collections from existing assemblies/collections."""
	all_colls = getattr(armature_data, "collections_all", armature_data.collections)

	# 1) Group assemblies by (limb, side)
	by_key = {}
	for assembly in armature_data.rigtools_assemblies:
		options = json.loads(assembly.options_json or "{}")
		limb = (options.get("limb_property_base_name") or "").strip()
		if not limb:
			continue
		side = assembly.side or ""
		by_key.setdefault((limb, side), []).append((assembly, options))

	for (limb, side), items in by_key.items():
		row = ensure_limb_collections(armature_data, limb, side)  # fills new defaults + mch parent
		# then OVERRIDE names from what already exists

		types = {a.assembly_type for a, _ in items}
		has_ik = "IK" in types
		has_torso = "TORSO" in types

		# Prefer options overrides if anyone stored explicit names
		for _, options in items:
			for role, key in (
				("fk", "fk_collection_name"),
				("tweak", "tweak_collection_name"),
			):
				name = (options.get(key) or "").strip()
				if name:
					setattr(row, role, name)

		# Prefer live Blender collections over brand-new template guesses
		candidates = {
			"fk": [
				name_collection("fk_split", limb, side),  # Hand.FK.L (old default)
				name_collection("fk", limb, side),        # Hand.L
			],
			"ik": [name_collection("ik", limb, side)],
			"tweak": [name_collection("tweak", limb, side)],
			"mch": [name_collection("mch", limb, side)],
			"master": [
				name_collection("fk_master", limb, side),           # Hand.Master.L (new)
				f"{limb.capitalize()}.FK.Master{side}",             # Hand.FK.Master.L (old)
			],
			"control": [name_collection("control", limb, side)],
		}
		for role, names in candidates.items():
			for name in names:
				if all_colls.get(name):
					setattr(row, role, name)
					break

		# split: IK limbs, torso (neck FK vs control), or fk name already has .FK.
		if has_ik or has_torso or ".FK" in (row.fk or ""):
			row.split = True
			# If somehow still on unqualified fk but IK/torso says split, point at .FK name if it exists
			split_name = name_collection("fk_split", limb, side)
			if all_colls.get(split_name):
				row.fk = split_name

	print(armature_data.rigtools_limb_collections)


MIGRATIONS = {
	0: migrate_0_to_1,
	1: migrate_1_to_2,
	2: migrate_2_to_3,
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
