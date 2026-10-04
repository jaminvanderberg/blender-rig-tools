import re
from rigtools.preferences import get_preferences


def set_bone_collection(armature_data, bone, collection_name, parent_collection_name=None):
	if not collection_name:
		return None

	for coll in list(bone.collections):
		coll.unassign(bone)

	colls = armature_data.collections
	all_colls = getattr(armature_data, "collections_all", armature_data.collections)

	collection = all_colls.get(collection_name)
	if not collection:
		parent = None
		if parent_collection_name:
			parent = all_colls.get(parent_collection_name)
			if not parent:
				parent = colls.new(parent_collection_name)

		collection = colls.new(collection_name, parent=parent)

	collection.assign(bone)
	return collection


def is_collection_visible(collection, armature_data):
	if collection:
		return collection.is_visible_effectively
	return not armature_data.collections.is_solo_active


def replace_name_token(name, find, replace):
	if not find or find == replace:
		return name
	separators = get_preferences().strip_separators.strip()

	parts = re.split(f'([{re.escape(separators)}])', name)
	out = []
	for part in parts:
		if part in separators:
			out.append(part)
		elif part == find:
			out.append(replace)
		else:
			out.append(part)
	return ''.join(out)


def collection_ancestors(coll):
	chain = []
	while coll:
		chain.append(coll)
		coll = coll.parent
	chain.reverse()
	return chain


def copy_collection_structure(armature_data, source_coll, find, replace):
	parent = None
	target = None
	all_colls = getattr(armature_data, "collections_all", armature_data.collections)
	for coll in collection_ancestors(source_coll):
		name = replace_name_token(coll.name, find, replace)
		target = all_colls.get(name)
		if not target:
			target = armature_data.collections.new(name)
		if parent and target.parent != parent:
			target.parent = parent
		parent = target
	return target
