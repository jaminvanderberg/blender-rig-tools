def generate_property_name(template, base_name, side):
    if "{side}" in template:
        return template.format(base_name=base_name, side=side)
    elif "{base_name}" in template:
        return template.format(base_name=base_name)
    else:
        return template
