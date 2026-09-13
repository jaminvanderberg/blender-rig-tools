import bpy
import re
from rigtools.utils.bone_chain import find_chains_from_selection, rename_chain, rename_chains, name_segment_types
from rigtools.utils.bone_chain import sort_chains, get_name_segment
import gpu
import blf
from bpy_extras.view3d_utils import location_3d_to_region_2d

# module-level so the draw callback can see it
_preview = None  # {"op": operator, "handler": handle}

def _draw_order_overlay():
	print("overlay draw", bpy.context.mode, len(find_chains_from_selection(bpy.context) or []))	
	state = _preview
	if not state:
		return
	op = state["op"]
	context = bpy.context
	obj = context.active_object
	if not obj or obj.type != 'ARMATURE' or obj.mode != 'EDIT':
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
	edit_bones = obj.data.edit_bones
	mw = obj.matrix_world

	# world-space heads + center (same math as sort_chains)
	heads_w = [mw @ edit_bones[c[0]].head for c in chains]
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
		label = get_name_segment(i, op.chain_name_type)  # "a" / "01" / ...
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

class RIG_OT_rename_chain(bpy.types.Operator):
		"""Rename one or more chains using advancing numbers or letters for each bone in the chain."""
		bl_idname = "rig.rename_chain"
		bl_label = "Rename Chain(s)"
		bl_options = {'REGISTER', 'UNDO'}
		bl_property = "name_template"
		
		name_template: bpy.props.StringProperty(
			name="Name Template",
			description="Template to use for the new name. {chain} is the chain name, {bone} is the bone name.",
			default="bone.{chain}.{bone}"
		)

		chain_name_type: bpy.props.EnumProperty(
			name="Chain Name Type",
			description="Type of chain name to use.",
			items=name_segment_types,
			default='LOWER'
		)

		bone_name_type: bpy.props.EnumProperty(
			name="Bone Name Type",
			description="Type of bone name to use.",
			items=name_segment_types,
			default='2DIGIT'
		)

		order_mode: bpy.props.EnumProperty(
			name="Order Mode",
			description="Mode to use for the order of the bones.",
			items=[
				('ANGULAR', "Angular", "Order by rotating around a central axis."),
				('LINEAR', "Linear", "Use linear order for the bones."),
			],
			default='ANGULAR'
		)

		order_axis: bpy.props.EnumProperty(
			name="Order Axis",
			description="Axis to use for the order of the bones.",
			items=[
				('X', "X", "X axis"),
				('Y', "Y", "Y axis"),
				('Z', "Z", "Z axis"),
			],
			default='Z'
		)

		order_start_angle: bpy.props.FloatProperty(
			name="Order Start Angle",
			description="Start angle to use for the order of the bones.",
			min=-360.0,
			max=360.0,
			default=0.0
		)

		order_invert: bpy.props.BoolProperty(
			name="Order Invert",
			description="Invert the order of the bones.",
			default=False
		)

		def execute(self, context):
			_remove_preview(context)
			obj = context.active_object
			if not obj or obj.type != 'ARMATURE':
					self.report({'ERROR'}, "Active object must be an armature.")
					return {'CANCELLED'}

			chains = find_chains_from_selection(context)

			if len(chains) == 0:
				self.report({'ERROR'}, "No chains found.")
				return {'CANCELLED'}
			elif len(chains) == 1:
				rename_chain(context, chains[0], self.name_template, self.bone_name_type)
			else:
				chains = sort_chains(context, chains, self.order_mode, self.order_axis, self.order_start_angle, self.order_invert)
				rename_chains(context, chains, self.name_template, self.chain_name_type, self.bone_name_type)

			self.report({'INFO'}, f"Renamed {len(chains)} chains.")
			return {'FINISHED'}
		
		def invoke(self, context, event):
			global _preview
			handler = bpy.types.SpaceView3D.draw_handler_add(
				_draw_order_overlay, (), 'WINDOW', 'POST_PIXEL'
			)
			_preview = {"op": self, "handler": handler}
			context.area.tag_redraw()
			return context.window_manager.invoke_props_dialog(self, width=300)			
		
		def draw(self, context):
			layout = self.layout
			
			obj = context.active_object
			if not obj or obj.type != 'ARMATURE':
				layout.label(text="Active object must be an armature.", icon='ERROR')
				return
			if obj.mode not in {'EDIT', 'POSE'}:
				layout.label(text="Must be in Edit or Pose mode.", icon='ERROR')
				return

			chains = find_chains_from_selection(context)
			if len(chains) == 0:
				self.report({'ERROR'}, "No chains selected.")

			layout.label(text=f"Found {len(chains)} chains.")
			# Settings section
			#box = layout.box()
			#box.label(text="Settings:", icon='SETTINGS')
			
			col = layout.column()
			col.prop(self, "name_template")
			if len(chains) > 1:
				col.prop(self, "chain_name_type")
			col.prop(self, "bone_name_type")

			if len(chains) < 2:
				return
			col.separator()
			box = col.box()
			box.label(text="Chain Order Settings:", icon='SORTALPHA')
			box.prop(self, "order_mode")
			row = box.row(align=True)
			row.prop(self, "order_axis", expand=True)
			if self.order_mode == 'ANGULAR':
				box.prop(self, "order_start_angle")
			box.prop(self, "order_invert")

			for area in context.screen.areas:
				if area.type == 'VIEW_3D':
					area.tag_redraw()

		def cancel(self, context):
			_remove_preview(context)			

classes = (
		RIG_OT_rename_chain,
)


import bpy

addon_keymaps = []

def register():
	for cls in classes:
			bpy.utils.register_class(cls)

def unregister():
	_remove_preview(bpy.context)
	for cls in classes:
			bpy.utils.unregister_class(cls)

if __name__ == "__main__":
		try:
				unregister()
		except Exception:
				pass
		register()
