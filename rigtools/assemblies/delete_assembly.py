import bpy
from rigtools.armature_settings import get_armature_settings
from rigtools.rig_ui.snapping_panel import delete_snap_chain
from rigtools.utils.bone import select_bones

def delete_assembly(context, assembly_uid):
	obj = context.object
	assembly = None
	for a in obj.data.rigtools_assemblies:
		if a.uid == assembly_uid:
			assembly = a
			break
	else:
		raise ValueError(f"Assembly not found: {assembly_uid}")
	assembly_name = assembly.name

	settings = get_armature_settings(obj.data, context)
	property_bone_name = settings.property_bone_name
	prop_bone = obj.pose.bones[property_bone_name]

	owned_names = {b.name for b in assembly.mechanism_bones}

	# We don't want to delete properties that are used by other assemblies
	property_names = set()
	for other_assembly in obj.data.rigtools_assemblies:
		if other_assembly.uid == assembly_uid:
			continue
		protected_names = {b.name for b in other_assembly.org_states}
		protected_names.update(b.name for b in other_assembly.twist_states)
		protected_names.update(b.parent for b in other_assembly.org_states)
		protected_names.update(b.parent for b in other_assembly.twist_states)
		protected_names.update(b.name for b in other_assembly.mechanism_bones)
		protected_names.update(b.name for b in other_assembly.org_children)
		protected_names.update(b.parent for b in other_assembly.org_children)

		hits = owned_names & protected_names
		if hits:
			bone = next(iter(hits))
			raise ValueError(f"Assembly {other_assembly.name} references bone {bone}. Delete assembly first.")

		property_names.update(p.name for p in other_assembly.properties)

	solo_property_names = {p.name for p in assembly.properties if p.name not in property_names}

	for property_name in solo_property_names:
		if property_name and prop_bone:
			if property_name in prop_bone:
				del prop_bone[property_name]
		delete_snap_chain(obj.data, property_name)

	for ref in assembly.objects:
		ob = bpy.data.objects.get(ref.name)
		if not ob:
			continue
		data = ob.data
		bpy.data.objects.remove(ob, do_unlink=True)
		if data is not None and data.users == 0:
			if isinstance(data, bpy.types.Mesh):
				bpy.data.meshes.remove(data)
			elif isinstance(data, bpy.types.Curve):
				bpy.data.curves.remove(data)

	original_mode = obj.mode
	try:
		# Remove things in reverse order, constrains first
		bpy.ops.object.mode_set(mode='POSE')
		for org_state in assembly.org_states:
			bone = obj.pose.bones.get(org_state.name)
			if not bone:
				continue
			for c in list(bone.constraints):
				sub = getattr(c, 'subtarget', "") or ""
				if sub in owned_names:
					bone.constraints.remove(c)

		# Remove all constraints from twist bones
		for twist_state in assembly.twist_states:
			bone = obj.pose.bones.get(twist_state.name)
			if not bone: continue
			for c in list(bone.constraints):
				bone.constraints.remove(c)

		if obj.mode != 'EDIT':
			bpy.ops.object.mode_set(mode='EDIT')
	
		# Reparent the original bones
		for org_child in (assembly.org_children):
			bone = obj.data.edit_bones.get(org_child.name)
			if not bone:
				continue
			parent = obj.data.edit_bones.get(org_child.parent) if org_child.parent else None
			if not parent and org_child.parent:
				continue # don't clear parent if bone can't be found
			bone.parent = parent
			bone.use_connect = org_child.use_connect

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
		collection_names = set()
		edit_bones = obj.data.edit_bones
		for name in owned_names:
			bone = edit_bones.get(name)
			if bone:
				collection_names.update(c.name for c in bone.collections)
				edit_bones.remove(bone)

		bpy.ops.object.mode_set(mode='OBJECT') # flush any bone changes from the big delete

		# check to see if any collections are empty
		for collection_name in collection_names:
			collection = obj.data.collections.get(collection_name)
			if collection and len(collection.bones) == 0:
				obj.data.collections.remove(collection)

		bpy.ops.object.mode_set(mode=original_mode)

		select_bones(obj, [b.name for b in assembly.org_states])

		for i, a in enumerate(obj.data.rigtools_assemblies):
			if a.uid == assembly_uid:
				obj.data.rigtools_assemblies.remove(i)
				break
	finally:
		bpy.ops.object.mode_set(mode=original_mode)

	return assembly_name
