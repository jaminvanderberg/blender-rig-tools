import string
import bpy
import re
from rigtools.preferences import get_separators, get_strip_tags

def get_selected_bones(context):
	if context.mode == 'EDIT_ARMATURE':
		return list(context.selected_editable_bones)
	elif context.mode == 'POSE':
		return list(context.selected_pose_bones)
	return []

def get_base_name(bone_name) -> tuple[str, str]:
	symmetry_pattern = r'(\.[LR]|\_[LR])(\.\d+)?$'
	match = re.search(symmetry_pattern, bone_name, re.IGNORECASE)
	
	if match:
		base_name = bone_name[:match.start()]
		extension = match.group(0)
	else:
		base_name = bone_name
		extension = ""

	return base_name, extension


def flip_side_name(bone_name):
	"""Return the L/R flipped bone name, or None if there is no side suffix."""
	base_name, extension = get_base_name(bone_name)
	if not extension:
		return None
	flipped = extension.replace('L', '\0').replace('R', 'L').replace('\0', 'R')
	flipped = flipped.replace('l', '\0').replace('r', 'l').replace('\0', 'r')
	if flipped == extension:
		return None
	return base_name + flipped


def same_side_names(name_a, name_b):
	"""True if both lack a side, or both are L, or both are R."""
	_, side_a = get_base_name(name_a)
	_, side_b = get_base_name(name_b)
	if not side_a or not side_b:
		return True
	return ('L' in side_a.upper()) == ('L' in side_b.upper())

def bone_name_matches(bone_name, prefix, suffix):
	base_name, extension = get_base_name(bone_name)
	if len(base_name) <= len(prefix) + len(suffix):
		return False
	return base_name.startswith(prefix) and base_name.endswith(suffix)

def strip_bone_numbers(base_name):
	separators = get_separators()
	if not separators:
		return base_name
	
	sep_class = re.escape("".join(separators))
	parts = re.split(f"([{sep_class}])", base_name)

	kept = []
	for i, part in enumerate(parts):
		if part.isdigit():
			if kept and kept[-1] in separators:
				kept.pop()
			continue
		kept.append(part)

	if kept and kept[-1] in separators:
		kept.pop()

	return "".join(kept)

def strip_bone_tags(base_name, context=None):
	tags = get_strip_tags(context)
	separators = get_separators(context)
	if not tags or not separators:
		return base_name

	for tag in tags:
		tag_lower = tag.lower()
		for sep in separators:
			prefix = tag_lower + sep
			if base_name.lower().startswith(prefix):
				base_name = base_name[len(prefix):]
				break
		for sep in separators:
			suffix = sep + tag_lower
			if base_name.lower().endswith(suffix):
				base_name = base_name[:-len(suffix)]
				break
	return base_name

def generate_bone_name(org_name, template, strip_name=True, strip_numbers=False, index=None):
	name = org_name
	base_name, extension = get_base_name(name)

	if strip_name:
		base_name = strip_bone_tags(base_name)
		
	if strip_numbers:
		base_name = strip_bone_numbers(base_name)

	if "{name}" not in template:
		# Gentle fallback behavior for when {name} is missing.
		# If it starts with a separator, assume the used just mean a suffix
		separators = tuple(get_separators())
		if template.startswith(separators):
			template = f"{{name}}{template}"
		else:
			# Otherwise, we just assume it's a prefix.
			# empty string template will just return the same bone name,
			# which is probably fine
			template = f"{template}{{name}}"

	kwargs = {"name": base_name}
	if index:
		kwargs["i"] = index
		kwargs["a"] = string.ascii_lowercase[index - 1]
		kwargs["A"] = string.ascii_uppercase[index - 1]
			
	formatted_base = template.format(**kwargs)
	
	return f"{formatted_base}{extension}"

def duplicate_bone(armature_data, bone, name, scale):
	new_bone = armature_data.edit_bones.new(name)

	direction = (bone.tail - bone.head).normalized()
	
	new_bone.head = bone.head
	new_bone.tail = bone.head + (direction * bone.length * scale)

	new_bone.parent = bone.parent
	# intentionally not copying connected status

	connected = bone.use_connect
	# we need to disconnect the bone so that the roll calculates properly
	bone.use_connect = False
	
	new_bone.roll = bone.roll

	bone.use_connect = connected

	for coll in bone.collections:
		coll.assign(new_bone)

	return new_bone


def duplicate_bone_subdivided(context, org_bone, count, name_template):
	"""Duplicate a bone and subdivide it into count bones.
	New bones are created in the same bone collection as the original bone.

	Returns a list of the new bone names in chain order.
	"""
	obj = context.object

	direction = (org_bone.tail - org_bone.head).normalized()
	twist_length = org_bone.length / count

	twist_bones = []
	parent = org_bone
	for i in range(count):
		name = generate_bone_name(org_bone.name, name_template, index=i+1)
		bone = obj.data.edit_bones.new(name)
		bone.head = org_bone.head + direction * i * twist_length
		bone.tail = bone.head + direction * twist_length
		bone.length = twist_length
		bone.parent = parent
		bone.roll = parent.roll

		for coll in parent.collections:
			coll.assign(bone)

		parent = bone

		twist_bones.append(bone.name)

	return twist_bones	

def set_bone_collection(armature_data, bone, collection_name):
	if not collection_name:
		return None

	for coll in list(bone.collections):
		coll.unassign(bone)

	colls = armature_data.collections
	collection = colls.get(collection_name) or colls.new(collection_name)

	collection.assign(bone)
	return collection

def duplicate_chain(armature_data, bone_names, name_template, scale, name_source=None):
	new_bones = []
	prev_bone = None
	for i, bone_name in enumerate(bone_names):
		source_name = name_source[i] if name_source else bone_name
		bone = armature_data.edit_bones[bone_name]
		name = generate_bone_name(source_name, name_template)
		new_bone = duplicate_bone(armature_data, bone, name, scale)
		if prev_bone:
			new_bone.parent = prev_bone
		prev_bone = new_bone
		new_bones.append(new_bone.name)
	return new_bones
			
def is_bone_visible(bone):
	if bone.hide:
		return False
	
	data_bone = getattr(bone, "bone", bone)
	
	if hasattr(data_bone, "collections"):
		if not data_bone.collections:
			return True
		return any(coll.is_visible for coll in data_bone.collections)
	
	armature = data_bone.id_data if hasattr(data_bone, "id_data") else None
	if armature and hasattr(armature, "layers"):
		return any(b_layer and a_layer for b_layer, a_layer in zip(data_bone.layers, armature.layers))
	
	return True

def select_bones(obj, bone_names, select_hidden=False) -> [int, int]: # Total selected, total hidden
	count = 0
	hidden = 0
	for bone_name in bone_names:
		if obj.mode == 'POSE':
			bone = obj.pose.bones.get(bone_name)
			if bone is None:
				continue
			visible = is_bone_visible(bone)
			if not visible:
				hidden += 1
			if select_hidden or visible:
				if hasattr(bone, "select"):
					bone.select = True
				else:
					obj.data.bones[bone_name].select = True
				count += 1

		elif obj.mode == 'EDIT':
			bone = obj.data.edit_bones.get(bone_name)
			if bone is None:
				continue
			visible = is_bone_visible(bone)
			if not visible:
				hidden += 1
			if select_hidden or visible:
				bone.select = True
				bone.select_head = True
				bone.select_tail = True
				count += 1

	return count, hidden


def is_collection_visible(collection, armature_data):
	if collection:
		return collection.is_visible_effectively
	return not armature_data.collections.is_solo_active


def find_side(bone_names):
	ret = None
	first_bone_name = ""
	for name in bone_names:
		base_name, side = get_base_name(name)
		if not first_bone_name:
			first_bone_name = name
			ret = side
		elif ret != side:
			raise ValueError(f"Side mismatch: Bone {name} does not have the same side as {first_bone_name}")
	return ret