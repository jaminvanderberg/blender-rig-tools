import re
from rigtools.preferences import get_preferences


def generate_bone_collection_name(template, base_name, side):
	ret = template
	if "{Name}" in template:
		ret = ret.replace("{Name}", base_name.capitalize())
	if "{name}" in template:
		ret = ret.replace("{name}", base_name)
	if "{side}" in template:
		ret = ret.replace("{side}", side)
	return ret

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
