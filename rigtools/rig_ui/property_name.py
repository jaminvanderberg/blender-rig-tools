import re
from rigtools.preferences import get_preferences
from rigtools.utils.bone import get_base_name, strip_bone_tags

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

def split_side(property_name):
	match = re.search(r'[._]([LR])$', property_name, re.IGNORECASE)
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

def guess_snapping_label(property_name, context=None):
	base, side = guess_group(property_name, context)
	side_name = SIDE_NAMES.get(side)
	if side_name:
		return f"{side_name} {base}", base
	return base, base

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