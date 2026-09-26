def generate_property_name(template, base_name, side):
	ret = template
	if "{name}" in template:
		ret = ret.replace("{name}", base_name)
	if "{side}" in template:
		ret = ret.replace("{side}", side)
	return ret