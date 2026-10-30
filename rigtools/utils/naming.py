import math
import re
import string
from rigtools.armature_settings import get_armature_settings
from rigtools.preferences import get_preferences, get_separator_string, get_separators, get_strip_tags
from rigtools.rig_ui.rig_ui import get_base_name, flip_side_name

SIDE_NAMES = {
	"L": "Left",
	"R": "Right"
}

# Tool-owned naming contract. User-facing boundaries (DEF/ORG/FK) stay in preferences.
BONE = {
	"ik": "{name}",
	"fk": "FK-{name}",
	"ik_pole": "{name}.pole",
	"ik_pole_vis": "VIS-{name}.pole",
	"ik_mch": "MCH-IK-{name}",
	"control": "{name}",
	"fk_master": "{name}.master.{i}",
	"foot_roll": "{name}.roll",
	"vis": "VIS-{name}",
	"mch": "MCH-{name}",
	"twist_def": "DEF-{name}.{i}",
	"twist_org": "ORG-{name}.{i}",
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
	"fk_follow": "MCH-FOLLOW-{name}",
}

WIDGET_TEMPLATE = "WGT-{prefix}-{name}"

COLLECTION = {
	"ik": "{Name}.IK{side}",
	"fk": "{Name}{side}",
	"fk_split": "{Name}.FK{side}",
	"fk_master": "{Name}.Master{side}",
	"control": "{Name}{side}",
	"tweak": "{Name}.Tweak{side}",
}

LIMB_COLLECTION_ROLES = ("fk", "ik", "tweak", "control")

PROPERTY = {
	"rotation_isolation": "{name}.FK.rot.follow{side}",
	"fk_ik_switch": "{name}.FK.IK{side}",
	"ik_parent": "{name}.ik.parent{side}",
	"skirt_collision": "{name}.collision{side}",
	"skirt_ride": "{name}.ride{side}",
	"ik_stretch": "{name}.stretch{side}",
}

def bone_template(role):
	return BONE[role]

def name_bone(role, source_name, *, strip_name=True, strip_numbers=False, index=None, **tokens):
	"""Name a bone from a fixed tool role in BONE.
	Looks up bone_template(role), substitutes any **tokens into the template (e.g. type=, i=),
	then runs generate_bone_name. Use this for mch/tweak/spline/etc.
	index: 1-based value for {i}/{a}/{A} in the template (see generate_bone_name).
	"""	
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

def get_side_letter(bone_name):
	_base, side = get_base_name(bone_name)
	s = side.upper()
	if "R" in s:
		return "R"
	elif "L" in s:
		return "L"
	return "C"

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
	"""Apply a naming template to a source bone name.
	Strips side (.L/.R) first, optionally strips tags (ORG/DEF/…) and trailing
	numbers, formats template with {name} and optional {i}/{a}/{A}, then
	re-appends the side suffix.
	Use when the template is caller-supplied. For fixed roles, prefer name_bone.
	"""	
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

def generate_widget_name(name, context):
	prefix = get_armature_settings(context.object.data, context).widget_prefix
	return generate_bone_name(name, WIDGET_TEMPLATE.replace("{prefix}", prefix))

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
		ret = ret.replace("{Name}", capitalize_limb_name(base_name))
	if "{name}" in template:
		ret = ret.replace("{name}", base_name)
	if "{side}" in template:
		ret = ret.replace("{side}", side)
	return ret

def _tokens(name, context=None):
	separators = re.escape(get_preferences(context).strip_separators.strip())
	if not separators:
		return [name] if name else []

	return [t for t in re.split(rf"[{separators}]", name) if t]

def guess_limb_name(bone_name, context=None):
	base, _extension = get_base_name(bone_name)
	base = strip_bone_tags(base, context)
	separators = re.escape(get_preferences(context).strip_separators.strip())
	if not separators:
		return base.lower()

	# Even indices are tokens, odd indices are the separators between them
	parts = re.split(rf"([{separators}])", base)
	kept = []
	for i in range(0, len(parts), 2):
		token = parts[i]
		if not token or token.isdigit() or len(token) == 1:
			continue
		if kept:
			kept.append(parts[i - 1])
		kept.append(token)
	return "".join(kept).lower()


def capitalize_limb_name(name):
	return re.sub(r"[A-Za-z0-9]+", lambda m: m.group(0).capitalize(), name)


def guess_assembly_instance(bone_name, context=None):
	base, _ = get_base_name(bone_name)
	base = strip_bone_tags(base, context)
	tokens = _tokens(base, context)
	if len(tokens) < 2:
		return ""

	# last token is along-chain index - skip it
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


def side_display_name(side):
	separators = get_separator_string()
	short_side = re.match(
		rf'[{re.escape(separators)}]([LR])(?:\.\d+)?$',
		side or "",
		re.IGNORECASE,
	)
	if not short_side:
		return ""
	return SIDE_NAMES.get(short_side.group(1).upper(), "")


def limb_group_label(property_base, side=""):
	base = (property_base or "").strip()
	if not base:
		return ""
	side_name = side_display_name(side)
	label = capitalize_limb_name(base)
	if side_name:
		return f"{side_name} {label}"
	return label


def guess_assembly_name(armature_data, chain, property_base, side="", context=None):
	side_name = side_display_name(side)

	instance = guess_assembly_instance(chain[0], context)
	base = capitalize_limb_name(property_base)
	
	if side_name:
		name = f"{side_name} {base}{instance}"
	else:
		name = f"{base}{instance}"
	return unique_assembly_name(armature_data, name)


def get_chain_order_key(bone_name, context=None):
	base, _ = get_base_name(bone_name)
	base = strip_bone_tags(base, context)
	tokens = _tokens(base, context)

	letter = None
	number = None
	for token in tokens:
		if letter is None and len(token) == 1 and token.isalpha():
			letter = token.lower()
		elif number is None and token.isdigit():
			number = int(token)

	if letter is not None:
		return ord(letter) - ord('a')
	if number is not None:
		return number
	return math.inf