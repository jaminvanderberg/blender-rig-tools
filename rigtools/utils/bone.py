from rigtools.preferences import get_preferences
from rigtools.utils.naming import generate_bone_name
from rigtools.utils.bone_collection import set_bone_collection


def get_selected_bones(context):
	if context.mode == 'EDIT_ARMATURE':
		return list(context.selected_editable_bones)
	elif context.mode == 'POSE':
		return list(context.selected_pose_bones)
	return []


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


def generate_mch_bones(armature_data, bones, name_template, collection_name, scale=0.35):
	prefs = get_preferences()
	mch_bone_names = []
	for bone in bones:
		bone_name = generate_bone_name(bone.name, name_template)
		mch_bone = duplicate_bone(armature_data, bone, bone_name, scale)

		if collection_name:
			set_bone_collection(armature_data, mch_bone, collection_name, prefs.mch_parent_collection)

		mch_bone.parent = bone.parent
		bone.use_connect = False
		bone.parent = mch_bone

		mch_bone.color.palette = 'DEFAULT'

		mch_bone_names.append(mch_bone.name)
	return mch_bone_names


def match_orientation(bone, reference):
	length = bone.length
	direction = (reference.tail - reference.head).normalized()
	bone.tail = bone.head + direction * length
	bone.roll = reference.roll


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
