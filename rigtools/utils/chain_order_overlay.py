import bpy
from rigtools.utils.bone_chain import find_chains_from_selection, sort_chains, get_name_segment
import blf
from bpy_extras.view3d_utils import location_3d_to_region_2d

# module-level so the draw callback can see it
_preview = None  # {"op": operator, "handler": handle}

def _draw_order_overlay():
	state = _preview
	if not state:
		return
	op = state["op"]
	context = bpy.context
	obj = context.active_object
	if not obj or obj.type != 'ARMATURE' or obj.mode not in ('EDIT', 'POSE'):
		return

	chains = state.get("chains")
	if chains is None and callable(state.get("get_chains")):
		chains = state["get_chains"](context)
	if chains is None:
		chains = find_chains_from_selection(context)
	if not chains:
		return

	# Flat list of chains (rename/weight-paint) vs list of groups (palm)
	if chains[0] and isinstance(chains[0][0], str):
		groups = [chains]
	else:
		groups = chains

	region = context.region
	rv3d = context.region_data
	bones = obj.data.edit_bones if obj.mode == 'EDIT' else obj.data.bones
	mw = obj.matrix_world

	font_id = 0
	blf.color(font_id, 1.0, 0.9, 0.2, 1.0)
	blf.size(font_id, 64)

	for group in groups:
		if len(group) < 2:
			continue
		ordered = sort_chains(
			context, group,
			getattr(op, "order_mode", "LINEAR"),
			op.order_axis,
			getattr(op, "order_start_angle", 0.0),
			op.order_invert,
		)
		heads_w = [mw @ bones[c[0]].head for c in ordered]
		for i, p in enumerate(heads_w):
			co2d = location_3d_to_region_2d(region, rv3d, p)
			if not co2d:
				continue
			seg = getattr(op, "chain_name_type", None)
			label = get_name_segment(i, seg) if seg else str(i)
			blf.position(font_id, co2d.x + 8, co2d.y + 8, 0)
			blf.draw(font_id, label)

def _remove_preview(context):
	global _preview
	if _preview and _preview["handler"]:
		bpy.types.SpaceView3D.draw_handler_remove(_preview["handler"], 'WINDOW')
	_preview = None
	if context.area:
		context.area.tag_redraw()
