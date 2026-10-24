import bpy

# Icons added in Blender 5.0, mapped to the closest 4.x icon.
# Code always uses the 5.0 name; icon() swaps it only when running on 4.x.
FALLBACKS = {
	'STATUS_INFO': 'INFO',
	'STATUS_INFO_FILLED': 'ADD',
	'STATUS_ERROR_FILLED': 'CANCEL',
	'STATUS_WARNING_FILLED': 'ERROR',
	'CON_GEOMETRYATTRIBUTE': 'MOD_CLOTH',
	'HUMANOID': 'OUTLINER_DATA_ARMATURE',
}

_available = None

def icon(name):
	global _available
	if _available is None:
		_available = set(bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items.keys())
	if name in _available:
		return name
	return FALLBACKS.get(name, 'NONE')
