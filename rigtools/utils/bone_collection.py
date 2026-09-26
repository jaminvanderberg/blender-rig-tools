def generate_bone_collection_name(template, base_name, side):
	ret = template
	if "{Name}" in template:
		ret = ret.replace("{Name}", base_name.capitalize())
	if "{name}" in template:
		ret = ret.replace("{name}", base_name)
	if "{side}" in template:
		ret = ret.replace("{side}", side)
	return ret


