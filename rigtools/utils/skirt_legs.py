from mathutils import Vector

from rigtools.utils.naming import get_base_name

FORWARD_AXIS_ITEMS = (
	('+X', '+X', 'Thigh +X'),
	('-X', '-X', 'Thigh -X'),
	('+Z', '+Z', 'Thigh +Z'),
	('-Z', '-Z', 'Thigh -Z'),
)

_CHAR_FORWARD = Vector((0.0, -1.0, 0.0))
_AXIS_DOT_MIN = 0.5


def _side_char(bone_name: str) -> str:
	_, extension = get_base_name(bone_name)
	for char in extension:
		upper = char.upper()
		if upper in ('L', 'R'):
			return upper
	return ""


def _fallback_forward_axis(bone_name: str) -> str:
	side = _side_char(bone_name)
	if side == 'R':
		return '-X'
	return '+X'


def guess_thigh_forward_axis(thigh_bone, *, bone_name: str | None = None) -> str:
	"""Pick +X/-X/+Z/-Z on the thigh that best matches character forward (-Y)."""
	name = bone_name or thigh_bone.name
	flat = _CHAR_FORWARD - thigh_bone.y_axis * _CHAR_FORWARD.dot(thigh_bone.y_axis)
	if flat.length_squared < 1e-8:
		return _fallback_forward_axis(name)

	flat.normalize()
	candidates = (
		('+X', thigh_bone.x_axis),
		('-X', -thigh_bone.x_axis),
		('+Z', thigh_bone.z_axis),
		('-Z', -thigh_bone.z_axis),
	)
	axis, direction = max(candidates, key=lambda item: flat.dot(item[1]))
	if flat.dot(direction) < _AXIS_DOT_MIN:
		return _fallback_forward_axis(name)
	return axis


def scan_leg_assemblies(obj):
	"""Yield leg rows from assemblies tagged limb_type == 'leg'."""
	bones = obj.data.bones
	for assembly in obj.data.rigtools_assemblies:
		options = assembly.get_options()
		if options.get("limb_type") != "leg":
			continue

		orgs = [state.name for state in assembly.org_states]
		if not orgs:
			continue

		thigh_name = orgs[0]
		thigh = bones.get(thigh_name)
		if not thigh:
			continue

		shin_name = orgs[1] if len(orgs) > 1 else ""
		yield {
			"thigh": thigh_name,
			"shin": shin_name if shin_name in bones else "",
			"forward_axis": guess_thigh_forward_axis(thigh, bone_name=thigh_name),
		}
