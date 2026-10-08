import re
import string
from rigtools.preferences import get_preferences, get_separator_string, get_separators, get_strip_tags

GROUP_REMAP = {
	"hand": "Arm",
	"foot": "Leg",
	"neck": "Head",
	"spine": "Torso",
	"thigh": "Leg",
	"shin": "Leg",
	"calf": "Leg",
	"forearm": "Arm",
}

KEEP_UPPER = {"fk", "ik"}

SIDE_NAMES = {
	"L": "Left",
	"R": "Right"
}

QUALIFIER_NAMES = ("upper", "lower", "left", "right", "front", "back", "top", "bottom", "inner", "outer")

# Tool-owned naming contract. User-facing boundaries (DEF/ORG/FK) stay in preferences.
BONE = {
	"ik": "{name}",
	"fk": "FK-{name}",
	"ik_pole": "{name}.pole",
	"ik_pole_vis": "VIS-{name}.pole",
	"ik_mch": "MCH-IK-{name}",
	"control": "{name}",
	"foot_roll": "{name}.roll",
	"vis": "VIS-{name}",
	"mch": "MCH-{name}",
	"twist": "ORG-{name}.{i}",
	"twist_isolator": "MCH-TWIST-{name}",
	"fk_ik_snap": "MCH-FK-IK-{name}.master",
	"ik_parent": "MCH-IK-{name}.parent",
	"switch": "MCH-SWITCH-{name}",
	"tweak": "{name}.tweak",
	"term": "{name}.tip.tweak",
	"socket": "MCH-SOCKET-{name}",
	"int": "MCH-INT-{name}",
	"ik_spline": "{name}.spline.{i}",
	"ik_spline_twist": "{name}.twist.{i}",
	"mch_foot_roll": "MCH-{name}.{type}",
	"spline_object": "SPLINE-{name}",
	"collision_target": "MCH-COLLIDE-TGT-{name}",
	"collision_source": "MCH-COLLIDE-{name}",
	"skirt_ride": "MCH-SKIRT-RIDE-{name}",
	"skirt_ride_target": "MCH-{name}-TGT-{org}",
}

COLLECTION = {
	"ik": "{Name}.IK{side}",
	"fk": "{Name}.FK{side}",
	"control": "{Name}{side}",
	"tweak": "{Name}.Tweak{side}",
	"mch": "MCH-{Name}",
}

PROPERTY = {
	"rotation_isolation": "{name}.FK.rot.follow{side}",
	"fk_ik_switch": "{name}.FK.IK{side}",
	"ik_parent": "{name}.ik.parent{side}",
}

def bone_template(role):
	return BONE[role]


def name_bone(role, source_name, *, strip_name=True, strip_numbers=False, index=None, **tokens):
	template = BONE[role]
	for key, value in tokens.items():
		template = template.replace("{" + key + "}", str(value))
	return generate_bone_name(
		source_name,
		template,
		strip_name=strip_name,
		strip_numbers=strip_numbers,
		index=index,
	)


def name_collection(role, base_name, side):
	return generate_bone_collection_name(COLLECTION[role], base_name, side)


def name_property(role, base_name, side):
	return generate_property_name(PROPERTY[role], base_name, side)

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


def generate_property_name(template, base_name, side):
	ret = template
	if "{name}" in template:
		ret = ret.replace("{name}", base_name)
	if "{side}" in template:
		ret = ret.replace("{side}", side)
	return ret


def generate_bone_collection_name(template, base_name, side):
	ret = template
	if "{Name}" in template:
		ret = ret.replace("{Name}", base_name.capitalize())
	if "{name}" in template:
		ret = ret.replace("{name}", base_name)
	if "{side}" in template:
		ret = ret.replace("{side}", side)
	return ret


def split_side(property_name):
	separators = get_separator_string()
	match = re.search(rf'[{re.escape(separators)}]([LR])$', property_name, re.IGNORECASE)
	if match:
		return property_name[:match.start()], match.group(1).upper()
	return property_name, ""


def _format_token(token):
	if token.lower() in KEEP_UPPER:
		return token.upper()
	if token.isdigit():
		return token
	return token.capitalize()


def _tokens(name, context=None):
	separators = re.escape(get_preferences(context).strip_separators.strip())
	if not separators:
		return [name] if name else []

	return [t for t in re.split(rf"[{separators}]", name) if t]


def guess_property_label(property_name, context=None):
	base, side = split_side(property_name)
	label = " ".join(_format_token(t) for t in _tokens(base, context))
	side_name = SIDE_NAMES.get(side)
	if side_name:
		label = f"{side_name} {label}"
	return label


def guess_group(property_name, context=None):
	base, side = split_side(property_name)
	tokens = _tokens(base, context)
	if not tokens:
		return ""
	key = tokens[0]
	if key.lower() in GROUP_REMAP:
		return GROUP_REMAP[key.lower()], side
	return _format_token(key), side


def guess_limb_name(bone_name, context=None):
	base, _extension = get_base_name(bone_name)
	base = strip_bone_tags(base, context)
	tokens = _tokens(base, context)
	tokens = [t for t in tokens if t.lower() not in QUALIFIER_NAMES and not t.isdigit()]
	if not tokens:
		return ""
	key = tokens[0].lower()
	if key in GROUP_REMAP:
		return GROUP_REMAP[key].capitalize()
	return key.capitalize()


def guess_assembly_instance(bone_name, context=None):
	base, _ = get_base_name(bone_name)
	base = strip_bone_tags(base, context)
	tokens = _tokens(base, context)
	if len(tokens) < 2:
		return ""

	# last token is along-chain index — skip it
	for token in tokens[:-1]:
		if len(token) == 1 and token.isalpha():
			return "." + token.upper()
		if token.isdigit():
			return "." + token
	return ""


def unique_assembly_name(armature_data, name):
	existing = {a.name for a in armature_data.rigtools_assemblies}
	if name not in existing:
		return name
	i = 2
	while f"{name}.{i}" in existing:
		i += 1
	return f"{name}.{i}"


def guess_assembly_name(armature_data, chain, property_base, side="", context=None):
	separators = get_separator_string()
	short_side = re.match(rf'[{re.escape(separators)}]([LR])$', side, re.IGNORECASE)
	letter = short_side.group(1) if short_side else ""
	side_name = SIDE_NAMES.get(letter)

	instance = guess_assembly_instance(chain[0], context)
	
	if side_name:
		name = f"{side_name} {property_base.capitalize()}{instance}"
	else:
		name = f"{property_base.capitalize()}{instance}"
	return unique_assembly_name(armature_data, name)
