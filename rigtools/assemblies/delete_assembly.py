import bpy
from rigtools.armature_settings import get_armature_settings
from rigtools.assemblies.tool_data.reparent_rules import apply_reparent_rule
from rigtools.rig_ui.snapping_data import delete_snap_chain
from rigtools.utils.bone import select_bones
from rigtools.utils.object import remove_objects

def delete_assembly(context, assembly_uid):
	return delete_assemblies(context, [assembly_uid])[0]

# Optimized to minimize mode switches
def delete_assemblies(context, assembly_uids):
	obj = context.object
	armature_data = obj.data

	deleting = set(assembly_uids)
	assemblies = [a for a in armature_data.rigtools_assemblies if a.uid in deleting]
	missing = deleting - {a.uid for a in assemblies}
	if missing:
		raise ValueError(f"Assembly not found: {', '.join(missing)}")
	assembly_names = [a.name for a in assemblies]
	org_names = [s.name for a in assemblies for s in a.org_states]

	settings = get_armature_settings(obj.data, context)
	property_bone_name = settings.property_bone_name
	prop_bone = obj.pose.bones[property_bone_name]

	owned_names = {b.name for a in assemblies for b in a.mechanism_bones}
	reparent_from = {r.from_bone for a in assemblies for r in a.reparent_rules}

	###################
	# DEPENDENCY CHECK
	# We don't want to delete properties that are used by other assemblies
	property_names = set()
	for other_assembly in obj.data.rigtools_assemblies:
		if other_assembly.uid in deleting:
			continue
		protected_names = {b.name for b in other_assembly.org_states}
		protected_names.update(b.name for b in other_assembly.twist_states)
		protected_names.update(b.parent for b in other_assembly.org_states)
		protected_names.update(b.parent for b in other_assembly.twist_states)
		protected_names.update(b.name for b in other_assembly.mechanism_bones)

		hits = (owned_names & protected_names) - reparent_from
		if hits:
			bone = next(iter(hits))
			raise ValueError(f"Assembly {other_assembly.name} references bone {bone}. Delete assembly first.")

		property_names.update(p.name for p in other_assembly.properties)

	solo_property_names = {p.name for a in assemblies for p in a.properties if p.name not in property_names}

	for property_name in solo_property_names:
		if property_name and prop_bone:
			if property_name in prop_bone:
				del prop_bone[property_name]
		delete_snap_chain(obj.data, property_name)

	remove_objects(bpy.data.objects.get(ref.name) for assembly in assemblies for ref in assembly.objects)

	###################
	# POSE MODE
	# Remove things in reverse order
	original_mode = obj.mode
	if obj.mode != 'POSE':
		bpy.ops.object.mode_set(mode='POSE')

	try:
		for assembly in assemblies:
			# constraints first
			assembly_owned_names = {b.name for b in assembly.mechanism_bones}
			for org_state in assembly.org_states:
				bone = obj.pose.bones.get(org_state.name)
				if not bone:
					continue
				for c in list(bone.constraints):
					sub = getattr(c, 'subtarget', "") or ""
					if sub in assembly_owned_names:
						bone.constraints.remove(c)

			# Remove all constraints from twist bones
			for twist_state in assembly.twist_states:
				bone = obj.pose.bones.get(twist_state.name)
				if not bone: continue
				for c in list(bone.constraints):
					bone.constraints.remove(c)

		#################
		# EDIT MODE

		if obj.mode != 'EDIT':
			bpy.ops.object.mode_set(mode='EDIT')

		for assembly in assemblies:
			assembly_owned_names = {b.name for b in assembly.mechanism_bones}

			# Un-apply reparent rules
			for rule in assembly.reparent_rules:
				apply_reparent_rule(obj.data, rule.from_bone, rule.to_bone, forward=False)
		
			for twist_state in assembly.twist_states:
				bone = obj.data.edit_bones.get(twist_state.name)
				if not bone: continue
				parent = obj.data.edit_bones.get(twist_state.parent) if twist_state.parent else None
				if not parent and twist_state.parent:
					continue # don't clear parent if bone can't be found
				bone.parent = parent
				bone.use_connect = twist_state.use_connect
			
			for org_state in reversed(assembly.org_states):
				bone = obj.data.edit_bones.get(org_state.name)
				if not bone:
					continue
				parent = obj.data.edit_bones.get(org_state.parent) if org_state.parent else None
				if not parent and org_state.parent:
					continue # don't clear parent if bone can't be found
				bone.parent = parent
				bone.use_connect = org_state.use_connect

			# finally, delete all the bones that were created by this assembly
			edit_bones = obj.data.edit_bones
			for name in assembly_owned_names:
				bone = edit_bones.get(name)
				if bone:
					edit_bones.remove(bone)

		if original_mode == 'EDIT':
			bpy.ops.object.mode_set(mode='OBJECT') # flush any bone changes from the big delete
		bpy.ops.object.mode_set(mode=original_mode)

		select_bones(obj, org_names)

		# in reverse order so we don't mess with indexes
		for i in reversed(range(len(obj.data.rigtools_assemblies))):
			if obj.data.rigtools_assemblies[i].uid in deleting:
				obj.data.rigtools_assemblies.remove(i)
	finally:
		if obj.mode != original_mode:
			bpy.ops.object.mode_set(mode=original_mode)

	return assembly_names
