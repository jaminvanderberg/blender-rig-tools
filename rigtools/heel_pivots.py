import bpy
from bpy.types import Operator

HEEL_MAP_KEY = "rigtools_heel_pivots"

def _heel_map(armature):
	"""Return a plain dict copy of the armature heel map."""
	raw = armature.get(HEEL_MAP_KEY)
	if not raw:
		return {}
	return {str(k): str(v) for k, v in raw.items()}

def _write_heel_map(armature, mapping):
	"""Replace the armature heel map. Assigning a new dict keeps it as an ID property."""
	armature[HEEL_MAP_KEY] = mapping

def prune_heel_map(armature, use_edit_bones=False):
	bones = armature.edit_bones if use_edit_bones else armature.bones
	mapping = _heel_map(armature)
	cleaned = {
		foot: pivot
		for foot, pivot in mapping.items()
		if foot in bones and pivot in bones
	}
	if cleaned != mapping:
		_write_heel_map(armature, cleaned)
	return cleaned

def get_heel_pivot(armature, foot_name) -> str:
	return _heel_map(armature).get(foot_name, "")

def set_heel_pivot(armature, foot_name, pivot_name: str):
	use_edit = len(armature.edit_bones) > 0
	mapping = prune_heel_map(armature, use_edit_bones=use_edit)
	if pivot_name:
		mapping[foot_name] = pivot_name
	else:
		mapping.pop(foot_name, None)
	_write_heel_map(armature, mapping)

def get_heel_pivot_feet(armature, pivot_name) -> list[str]:
	return [foot for foot, pivot in _heel_map(armature).items() if pivot == pivot_name]

class RIG_OT_set_heel_pivot(Operator):
	bl_idname = "rig.set_heel_pivot"
	bl_label = "Set Heel Pivot"
	bl_description = "Set the heel pivot for the selected foot bone"
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		foot_bone = context.active_bone
		others = [b for b in context.selected_bones if b != foot_bone]
		if len(others) != 1:
			self.report({'ERROR'}, "Please select exactly one heel pivot bone (active = foot)")
			return {'CANCELLED'}
		set_heel_pivot(foot_bone, others[0].name)

		self.report({'INFO'}, f"Heel pivot set to {others[0].name}")
		return {'FINISHED'}