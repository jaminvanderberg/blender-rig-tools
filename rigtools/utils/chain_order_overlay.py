import bpy
from rigtools.utils.bone_chain import find_chains_from_selection, sort_chains, get_name_segment
import gpu
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

	chains = find_chains_from_selection(context)
	if len(chains) < 2:
		return

	chains = sort_chains(
		context, chains,
		op.order_mode, op.order_axis,
		op.order_start_angle, op.order_invert,
	)

	region = context.region
	rv3d = context.region_data
	bones = obj.data.edit_bones if obj.mode == 'EDIT' else obj.data.bones
	mw = obj.matrix_world

	# world-space heads + center (same math as sort_chains)
	heads_w = [mw @ bones[c[0]].head for c in chains]
	center = sum(heads_w, heads_w[0].__class__()) / len(heads_w)

	# lines: center → each head (angular), or polyline through heads (linear)
	shader = gpu.shader.from_builtin('UNIFORM_COLOR')
	gpu.state.blend_set('ALPHA')
	# ... batch_for_shader LINE_STRIP / LINES with heads_w / center ...

	# labels in screen space
	font_id = 0
	blf.color(font_id, 1.0, 0.9, 0.2, 1.0)
	blf.size(font_id, 64)
	for i, p in enumerate(heads_w):
		co2d = location_3d_to_region_2d(region, rv3d, p)
		if not co2d:
			continue
		seg = getattr(op, "chain_name_type", None)
		label = get_name_segment(i, seg) if seg else str(i)  # "a" / "01" / ...
		blf.position(font_id, co2d.x + 8, co2d.y + 8, 0)
		blf.draw(font_id, label)

	gpu.state.blend_set('NONE')

def _remove_preview(context):
	global _preview
	if _preview and _preview["handler"]:
		bpy.types.SpaceView3D.draw_handler_remove(_preview["handler"], 'WINDOW')
	_preview = None
	if context.area:
		context.area.tag_redraw()