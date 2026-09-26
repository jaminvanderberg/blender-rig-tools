from rigtools.utils.bone import get_selected_bones
from rigtools.armature_settings import get_armature_settings
from rigtools.preferences import get_preferences
import bpy

class ChainBranchingError(Exception):
	"""Creates FK/Tweak chain from an existing bone chain."""
	pass

def find_chains_from_selection(context):
	selected_bones = get_selected_bones(context)
	if not selected_bones:
		return []
	
	heads = [
		bone for bone in selected_bones
		if bone.parent is None or bone.parent not in selected_bones
	]
	chains = []
	
	def walk_chain(current_bone, current_chain):
		current_chain.append(current_bone.name)
		selected_children = [c for c in current_bone.children if c in selected_bones]
		
		if len(selected_children) > 1:
			raise ChainBranchingError(
				f"Branching detected at bone '{current_bone.name}'. All bones must have only one selected child."
			)
		elif len(selected_children) == 0:
			chains.append(current_chain)
			return

		walk_chain(selected_children[0], current_chain)
		
	for head in heads:
		walk_chain(head, [])
		
	return chains


import math

def sort_chains(context, chains, mode, axis, start_angle_deg=0.0, invert=False):
	bones = (
		context.object.data.edit_bones 
		if context.object.mode == 'EDIT' 
		else context.object.data.bones
	)
	axis_idx = 'XYZ'.index(axis)

	heads = [bones[chain[0]].head.copy() for chain in chains]
	center = sum(heads, heads[0].__class__()) / len(heads)  # or use mathutils.Vector

	from mathutils import Vector
	heads = [bones[chain[0]].head.copy() for chain in chains]
	center = sum((Vector(h) for h in heads), Vector()) / len(heads)

	def sort_key(chain):
		co = bones[chain[0]].head
		if mode == 'LINEAR':
			return (co[axis_idx], chain[0])

		# ANGULAR: plane perpendicular to axis
		d = co - center
		a, b = [i for i in (0, 1, 2) if i != axis_idx]
		angle = math.atan2(d[b], d[a])
		start = math.radians(start_angle_deg)
		return ((angle - start) % math.tau, chain[0])

	chains = sorted(chains, key=sort_key)
	if invert:
		chains.reverse()
	return chains
	
name_segment_types = [
	('2DIGIT', "2 Digit", "Use a 2 digit number for the chain name."),
	('3DIGIT', "3 Digit", "Use a 3 digit number for the chain name."),
	('LOWER', "Lowercase Letter", "Use a lowercase letter for the chain name."),
	('UPPER', "Uppercase Letter", "Use a uppercase letter for the chain name."),
]

def get_name_segment(i, seg_type):
	if seg_type == '2DIGIT':
		return f'{i+1:02d}'
	elif seg_type == '3DIGIT':
		return f'{i+1:03d}'
	elif seg_type == 'LOWER':
		return f'{chr(i + 97)}'
	elif seg_type == 'UPPER':
		return f'{chr(i + 65)}'	

def rename_chain(context, chain, name_template, bone_name_type):
	obj = context.object
	edit_bones = obj.data.edit_bones

	for i, old_name in enumerate(chain):
		new_name = name_template.replace('{bone}', get_name_segment(i, bone_name_type))
		if new_name != old_name:
			edit_bones[old_name].name = new_name

def rename_chains(context, chains, name_template, chain_name_type, bone_name_type):
	obj = context.object
	edit_bones = obj.data.edit_bones

	for i, chain in enumerate(chains):
		rename_chain(context, chain, name_template.replace('{chain}', get_name_segment(i, chain_name_type)), bone_name_type)

###############################################################################################
# Hierarchy

def is_ancestor_selected(bone, selected_set):
	parent = bone.parent
	while parent:
		if parent in selected_set:
			return True
		parent = parent.parent
	return False

def find_hierarchy_chains(context, connected_only=False):
	selected_bones = get_selected_bones(context)
	if not selected_bones:
		return []
	
	heads = [
		bone for bone in selected_bones
		if not is_ancestor_selected(bone, selected_bones)
	]
	chains = []
	
	def walk_hierarchy(current_bone, current_chain):
		current_chain.append(current_bone.name)
		children = list(current_bone.children)
		if connected_only:
			children = [c for c in children if c.use_connect]
		
		if len(children) == 0:
			chains.append(current_chain)
			return
		
		walk_hierarchy(children[0], current_chain)
		
	for head in heads:
		walk_hierarchy(head, [])
		
	return chains

###############################################################################################
# Assembly
###############################################################################################

def get_assembly_chains(context, check_property_bone = True) -> tuple[list[list[str]], str]:
	""" Switches mode to edit mode
		Returns: list of chains of bones names, original mode
		Raises ValueError if the object is not an armature, or in object mode, or no edit bones are selected,
		or the property bone is not found.
	"""
	obj = context.object
	if not obj or obj.type != 'ARMATURE':
		raise ValueError("Active object must be an armature.")
	
	if obj.mode == 'OBJECT':
		raise ValueError(f"Can't use from Object mode")

	settings = get_armature_settings(obj.data, context)
	prefs = get_preferences()
	if check_property_bone and settings.property_bone_name not in obj.pose.bones:
		raise ValueError(f"Property bone '{settings.property_bone_name}' not found.")

	armature_data = obj.data
	
	# Switch to edit mode
	original_mode = obj.mode
	if obj.mode != 'EDIT':
		bpy.ops.object.mode_set(mode='EDIT')
		
	if not context.selected_editable_bones:
		bpy.ops.object.mode_set(mode=original_mode)
		raise ValueError("No edit bones selected. Select at least one bone.")
	
	# Find all of the indivual bone chains
	try:
		chains = find_chains_from_selection(context)
	except Exception as e:
		bpy.ops.object.mode_set(mode=original_mode)
		raise ValueError(str(e))

	return chains, original_mode