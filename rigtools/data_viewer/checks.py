import json
from collections import Counter
from dataclasses import dataclass, field
import bpy
from rigtools.armature_settings import CURRENT_RIG_DATA_VERSION
from rigtools.preferences import get_preferences
from rigtools.rig_ui.snapping_data import delete_snap_chain
from rigtools.utils.naming import LIMB_COLLECTION_ROLES, limb_group_label

SETTINGS_BONES = ("root", "torso", "hips", "chest", "head", "property")

@dataclass
class Issue:
	severity: str # 'ERROR', 'WARNING', 'INFO'
	message: str
	assembly_uid: str = ""
	bone: str = ""
	fix_id: str = ""
	fix_args: dict = field(default_factory=dict)

def bone_names(armature_data):
	bones = armature_data.edit_bones if armature_data.is_editmode else armature_data.bones
	return {b.name for b in bones}

def collection_names(armature_data):
	return {c.name for c in getattr(armature_data, "collections_all", armature_data.collections)}

def get_property_bone(obj):
	name = obj.data.rigtools.property_bone_name
	return obj.pose.bones.get(name) if name else None

def run_checks(obj) -> list[Issue]:
	armature_data = obj.data
	bones = bone_names(armature_data)
	issues = []
	issues += _check_assemblies(obj, bones)
	issues += _check_limb_collections(armature_data)
	issues += _check_snap_chains(armature_data, bones)
	issues += _check_layout(armature_data)
	issues += _check_settings(armature_data, bones)
	issues += _check_orphan_mch(armature_data)
	return issues

def _check_assemblies(obj, bones):
	armature_data = obj.data
	assemblies = armature_data.rigtools_assemblies
	issues = []

	for uid, count in Counter(a.uid for a in assemblies).items():
		if count > 1:
			issues.append(Issue('ERROR', f"{count} assemblies share the ID {uid}", assembly_uid=uid))

	org_owners = {}
	for assembly in assemblies:
		for state in assembly.org_states:
			org_owners.setdefault(state.name, []).append(assembly.name)
	for bone, owners in org_owners.items():
		if len(owners) > 1:
			issues.append(Issue('ERROR', f"{bone} is used by {', '.join(owners)}", bone=bone))

	prop_bone = get_property_bone(obj)

	for assembly in assemblies:
		uid = assembly.uid
		label = assembly.name

		try:
			options = json.loads(assembly.options_json or "{}")
		except ValueError:
			options = None
		if options is None:
			issues.append(Issue('ERROR', f"{label}: options can't be read", assembly_uid=uid))
		elif "limb_property_base_name" not in options:
			issues.append(Issue('ERROR', f"{label}: options have no limb name", assembly_uid=uid))

		for state in assembly.org_states:
			if state.name not in bones:
				issues.append(Issue('ERROR', f"{label}: ORG bone {state.name} is missing", uid, state.name))
			elif state.parent and state.parent not in bones:
				issues.append(Issue('INFO', f"{label}: original parent {state.parent} of {state.name} is missing", uid, state.name))

		for state in assembly.twist_states:
			if state.name not in bones:
				issues.append(Issue('WARNING', f"{label}: twist bone {state.name} is missing", uid, state.name,
					'remove_twist_state', {'assembly_uid': uid, 'name': state.name}))
			elif state.parent and state.parent not in bones:
				issues.append(Issue('INFO', f"{label}: original parent {state.parent} of {state.name} is missing", uid, state.name))

		for ref in assembly.mechanism_bones:
			if ref.name not in bones:
				issues.append(Issue('WARNING', f"{label}: mechanism bone {ref.name} is missing", uid, ref.name,
					'remove_mechanism_bone', {'assembly_uid': uid, 'name': ref.name}))

		for ref in assembly.objects:
			if ref.name not in bpy.data.objects:
				issues.append(Issue('WARNING', f"{label}: object {ref.name} is missing", uid, "",
					'remove_object_ref', {'assembly_uid': uid, 'name': ref.name}))

		for rule in assembly.reparent_rules:
			missing = [b for b in (rule.from_bone, rule.to_bone) if b not in bones]
			if missing:
				issues.append(Issue('WARNING', f"{label}: reparent rule {rule.from_bone} -> {rule.to_bone} has missing bone {missing[0]}", uid, "",
					'remove_reparent_rule', {'assembly_uid': uid, 'from_bone': rule.from_bone, 'to_bone': rule.to_bone}))

		if prop_bone:
			for prop in assembly.properties:
				if prop.name and prop.name not in prop_bone:
					issues.append(Issue('WARNING', f"{label}: property {prop.name} is missing from {prop_bone.name}", uid, prop_bone.name))

		if len(assembly.org_children) and armature_data.rigtools.rig_data_version >= CURRENT_RIG_DATA_VERSION:
			issues.append(Issue('INFO', f"{label}: has leftover pre-v5 tip data", uid, "",
				'clear_org_children', {'assembly_uid': uid}))

	return issues

def _check_limb_collections(armature_data):
	limbs = {}
	for assembly in armature_data.rigtools_assemblies:
		try:
			limb = json.loads(assembly.options_json or "{}").get("limb_property_base_name")
		except ValueError:
			continue
		limbs.setdefault((limb, assembly.side), []).append(assembly)

	collections = collection_names(armature_data)
	issues = []
	for row in armature_data.rigtools_limb_collections:
		label = limb_group_label(row.limb, row.side) or "(unnamed)"
		assemblies = limbs.get((row.limb, row.side))
		if not assemblies:
			issues.append(Issue('WARNING', f"Limb collections for {label} aren't used by any assembly",
				fix_id='remove_limb_collections', fix_args={'limb': row.limb, 'side': row.side}))
			continue
		# Collection names are reserved for every role up front; the collection only exists once a bone uses it
		for role in LIMB_COLLECTION_ROLES:
			name = getattr(row, role)
			if name and name not in collections and any(a.get_bones_by_role(role) for a in assemblies):
				issues.append(Issue('WARNING', f"{label}: {role.upper()} bones exist but their collection {name} is missing"))
	return issues

def _check_snap_chains(armature_data, bones):
	properties = {p.name for a in armature_data.rigtools_assemblies for p in a.properties}
	issues = []
	for chain in armature_data.rig_ui_snap_chains:
		if chain.switch_property not in properties:
			issues.append(Issue('WARNING', f"FK/IK snapping for {chain.switch_property} isn't used by any assembly",
				fix_id='remove_snap_chain', fix_args={'switch_property': chain.switch_property}))
			continue
		names = [b.name for b in chain.fk_bones] + [b.name for b in chain.ik_bones]
		names += [chain.ik_control, chain.ik_pole, chain.snap_control, chain.snap_pole]
		for name in names:
			if name and name not in bones:
				issues.append(Issue('WARNING', f"FK/IK snapping for {chain.switch_property}: bone {name} is missing"))
	return issues

def _check_layout(armature_data):
	collections = collection_names(armature_data)
	issues = []
	for item in armature_data.rig_ui_layout:
		if not item.is_gap and item.collection_name not in collections:
			issues.append(Issue('WARNING', f"Rig UI layout lists missing collection {item.collection_name}",
				fix_id='remove_layout_item', fix_args={'collection_name': item.collection_name}))
	return issues

def _check_settings(armature_data, bones):
	settings = armature_data.rigtools
	if not settings.is_initialized:
		return []
	issues = []
	for key in SETTINGS_BONES:
		name = getattr(settings, f"{key}_bone_name")
		if name and name not in bones:
			issues.append(Issue('WARNING', f"Armature settings: {key.title()} bone {name} is missing"))
	return issues

def _check_orphan_mch(armature_data):
	all_collections = getattr(armature_data, "collections_all", armature_data.collections)
	mch = all_collections.get(get_preferences().mch_collection_name)
	if not mch:
		return []
	owned = set()
	for assembly in armature_data.rigtools_assemblies:
		owned.update(b.name for b in assembly.mechanism_bones)
		owned.update(s.name for s in assembly.org_states)
		owned.update(s.name for s in assembly.twist_states)
	return [
		Issue('INFO', f"{bone.name} is in {mch.name} but no assembly owns it", bone=bone.name)
		for bone in mch.bones if bone.name not in owned
	]

#########
# FIXES
# Only remove references that point at nothing. Rows are found by name at fix time.

def _remove_by(collection, match):
	for i in reversed(range(len(collection))):
		if match(collection[i]):
			collection.remove(i)

def _assembly(obj, uid):
	for assembly in obj.data.rigtools_assemblies:
		if assembly.uid == uid:
			return assembly
	return None

def fix_remove_mechanism_bone(obj, assembly_uid, name):
	assembly = _assembly(obj, assembly_uid)
	if assembly:
		_remove_by(assembly.mechanism_bones, lambda r: r.name == name)

def fix_remove_twist_state(obj, assembly_uid, name):
	assembly = _assembly(obj, assembly_uid)
	if assembly:
		_remove_by(assembly.twist_states, lambda r: r.name == name)

def fix_remove_object_ref(obj, assembly_uid, name):
	assembly = _assembly(obj, assembly_uid)
	if assembly:
		_remove_by(assembly.objects, lambda r: r.name == name)

def fix_remove_reparent_rule(obj, assembly_uid, from_bone, to_bone):
	assembly = _assembly(obj, assembly_uid)
	if assembly:
		_remove_by(assembly.reparent_rules, lambda r: r.from_bone == from_bone and r.to_bone == to_bone)

def fix_clear_org_children(obj, assembly_uid):
	assembly = _assembly(obj, assembly_uid)
	if assembly:
		assembly.org_children.clear()

def fix_remove_limb_collections(obj, limb, side):
	_remove_by(obj.data.rigtools_limb_collections, lambda r: r.limb == limb and r.side == side)

def fix_remove_snap_chain(obj, switch_property):
	delete_snap_chain(obj.data, switch_property)

def fix_remove_layout_item(obj, collection_name):
	layout = obj.data.rig_ui_layout
	for i in reversed(range(len(layout))):
		item = layout[i]
		if item.is_gap or item.collection_name != collection_name:
			continue
		# Removing the first item of a row: the next item starts the row instead
		if not item.same_row and i + 1 < len(layout) and layout[i + 1].same_row:
			layout[i + 1].same_row = False
		layout.remove(i)

FIXES = {
	'remove_mechanism_bone': fix_remove_mechanism_bone,
	'remove_twist_state': fix_remove_twist_state,
	'remove_object_ref': fix_remove_object_ref,
	'remove_reparent_rule': fix_remove_reparent_rule,
	'clear_org_children': fix_clear_org_children,
	'remove_limb_collections': fix_remove_limb_collections,
	'remove_snap_chain': fix_remove_snap_chain,
	'remove_layout_item': fix_remove_layout_item,
}

def apply_fix(obj, fix_id, fix_args):
	FIXES[fix_id](obj, **fix_args)
