import bpy
from rigtools.utils.bone_chain import sort_chains, get_name_segment, find_chains_from_selection
import gpu
import blf
from bpy_extras.view3d_utils import location_3d_to_region_2d
from rigtools.utils.chain_order_overlay import _draw_order_overlay, _remove_preview
from rigtools.utils import chain_order_overlay
from collections import defaultdict

def stitch_cols(a, b, faces, align_end = False):

	if align_end:
		i = len(a) - 1
		j = len(b) - 1
		while i > 0 and j > 0:
			i -= 1
			j -= 1
			faces.append((a[i], a[i+1], b[j+1], b[j]))
		while i > 0:
			i -= 1
			faces.append((a[i], a[i+1], b[0]))
		while j > 0:
			j -= 1
			faces.append((a[0], b[j+1], b[j]))
		return

	i = j = 0
	while i < len(a) - 1 and j < len(b) - 1:
		faces.append((a[i], a[i+1], b[j+1], b[j]))
		i += 1
		j += 1
	# Triangle fan any remaining vertices on either side
	while i < len(a) - 1:
		faces.append((a[i], a[i+1], b[-1]))
		i += 1
	while j < len(b) - 1:
		faces.append((a[-1], b[j+1], b[j]))
		j += 1

def seed_weight_map(chains, grid):
	weights = defaultdict(dict)
	for col_idx, chain in enumerate(chains):
		col = grid[col_idx]
		for row, bone_name in enumerate(chain):
			weights[col[row]][bone_name] = 1.0
		weights[col[-1]][chain[-1]] = 1.0
	return weights

def normalize_vert(wmap):
	total = sum(wmap.values())
	if total <= 0:
		return
	for b in wmap:
		wmap[b] /= total

def spread_weights(weights, grid, chians, *,
	carry_v = 0.25, carry_h = 0.15,
	protect_rows = 1,
	iterations = 1,
	close_loop = True,
	align_end = False
):
	ncols = len(grid)

	def neighbors(c, r):
		col = grid[c]
		if r > 0:
			yield grid[c][r-1], 'up'
		if r < len(col) - 1:
			yield grid[c][r+1], 'down'
		if ncols > 1:
			left = (c - 1) % ncols if close_loop else c - 1
			right = (c + 1) % ncols if close_loop else c + 1
			for nc in (left, right):
				if nc < 0 or nc >= ncols:
					continue
				nr = r + len(grid[nc]) - len(col) if align_end else r
				base = r + len(grid[nc]) - len(col) if align_end else r
				if base < 0:
					side_r = 0
				elif base >= len(grid[nc]):
					side_r = len(grid[nc]) - 1
				else:
					side_r = base
				if (r > protect_rows) == (side_r < protect_rows):
					yield grid[nc][side_r], 'side'
				for dr, kind in ((-1, 'diag_up'), (1, 'diag_down')):
					nr = base + dr
					if nr < 0 or nr >= len(grid[nc]) or nr <= protect_rows:
						continue
					yield grid[nc][nr], kind

	for _ in range(iterations):
		acc = defaultdict(lambda: defaultdict(float))

		for c, col in enumerate(grid):
			for r, v in enumerate(col):
				is_top = (r == 0)
				for bone, w in weights[v].items():
					if w <= 0:
						continue
					
					pushes = []
					for nv, kind in neighbors(c, r):
						if kind in ('up', 'down', 'diag_up', 'diag_down'):
							if is_top and kind in ('up', 'diag_up'):
								continue
							if kind in ('up', 'diag_up') and r <= protect_rows + 1:
								continue
							if kind in ('down', 'diag_down') and r <= protect_rows:
								continue
							factor = carry_v * carry_h if kind.startswith('diag') else carry_v
							pushes.append((nv, factor))
						else:
							pushes.append((nv, carry_h))

					given = sum(f for _, f in pushes)
					keep = max(0,0, 1.0 - given)
					acc[v][bone] += w * keep
					for nv, f in pushes:
						acc[nv][bone] += w * f

		weights = {v: dict(bones) for v, bones in acc.items()}
		for v in weights:
			normalize_vert(weights[v])
			
	return weights

def write_vertex_groups(obj, weights):
	for v, bones in weights.items():
		for bone, w in bones.items():
			vg = obj.vertex_groups.get(bone) or obj.vertex_groups.new(name=bone)
			vg.add([v], w, 'REPLACE')

class RIG_OT_weight_paint_proxy(bpy.types.Operator):
		"""Create a weight paint proxy for the selected chains."""
		bl_idname = "rig.weight_paint_proxy"
		bl_label = "Weight Paint Proxy"
		bl_options = {'REGISTER', 'UNDO'}
		bl_property = "object_name"
		
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

		stitch_chain: bpy.props.BoolProperty(
			name="Stitch Chain",
			description="Stitch chains into a single mesh.",
			default=True
		)

		close_loop: bpy.props.BoolProperty(
			name="Close Loop",
			description="Close the loop of the chain.",
			default=True
		)

		seed_weights: bpy.props.BoolProperty(
			name="Seed Weights",
			description="Add vertex groups to the mesh.",
			default=True
		)

		armature_modifier: bpy.props.BoolProperty(
			name="Armature Modifier",
			description="Add an armature modifier to the mesh.",
			default=True
		)

		object_name: bpy.props.StringProperty(
			name="Object Name",
			description="The name of the object to create.",
			default="WProxy-{armature}"
		)

		spread_weights: bpy.props.BoolProperty(
			name="Spread Weights",
			description="Spread the weights of the bones.",
			default=True
		)

		carry_v: bpy.props.FloatProperty(
			name="Spread Along Chain",
			description="The amount of weight to carry vertically.",
			min=0.0,
			max=1.0,
			default=0.10
		)
		
		carry_h: bpy.props.FloatProperty(
			name="Spread Across Chain",
			description="The amount of weight to carry horizontally.",
			min=0.0,
			max=1.0,
			default=0.10
		)
		
		protect_rows: bpy.props.IntProperty(
			name="Lock Root Rows",
			description="Don't spread weight along chain for the first n rows.",
			min=0,
			default=1
		)
		
		iterations: bpy.props.IntProperty(
			name="Iterations",
			description="The number of iterations to run.",
			min=1,
			default=1
		)

		chain_align: bpy.props.EnumProperty(
			name="Chain Align",
			description="Which end lines up when chains have different lengths.",
			items=[
				('START', "Start", "Line up the roots. Extra length fans onto the tip."),
				('END', "End", "Line up the tips. Extra length fans onto the root."),
			],
			default='START'
		)

		def execute(self, context):
			_remove_preview(context)

			arm = context.object

			chains = find_chains_from_selection(context)
			if self.stitch_chain and len(chains) > 1:
				chains = sort_chains(context, chains, self.order_mode, self.order_axis, self.order_start_angle, self.order_invert)

			bpy.ops.object.mode_set(mode='EDIT')

			bones = context.object.data.edit_bones
			align_end = self.chain_align == 'END'

			vertices = []
			edges = []
			faces = []
			vert_index = 0
			grid = [] # grid[col][row] = vert_index
			for chain in chains:
				col = []
				for i, bone_name in enumerate(chain):
					bone = bones.get(bone_name)
					vertices.append(bone.head)
					col.append(vert_index)
					if i > 0:
						edges.append((vert_index - 1, vert_index))
					vert_index += 1

					if i == len(chain) - 1:
						vertices.append(bone.tail)
						edges.append((vert_index - 1, vert_index))
						col.append(vert_index)
						vert_index += 1
				grid.append(col)

			if self.stitch_chain and len(grid) > 1:
				for c in range(len(grid) - 1):
					stitch_cols(grid[c], grid[c+1], faces, align_end)
				if self.close_loop:
					stitch_cols(grid[-1], grid[0], faces, align_end)

			mesh_name = self.object_name
			if '{armature}' in mesh_name:
				mesh_name = mesh_name.format(armature=context.object.name)

			mesh = bpy.data.meshes.new(mesh_name)
			if self.stitch_chain:
				mesh.from_pydata(vertices, [], faces)
			else:
				mesh.from_pydata(vertices, edges, [])
			mesh.validate(verbose=True)
			mesh.update()

			obj = bpy.data.objects.new(mesh_name, mesh)
			context.collection.objects.link(obj)

			if self.armature_modifier:
				modifier = obj.modifiers.new(type='ARMATURE', name='Armature')
				modifier.object = context.object

			if self.seed_weights:
				weights = seed_weight_map(chains, grid)
				if self.spread_weights:
					weights = spread_weights(weights, grid, chains, 
						carry_v = self.carry_v,
						carry_h = self.carry_h,
						protect_rows = self.protect_rows,
						iterations = self.iterations,
						close_loop = self.close_loop,
						align_end = align_end)
				write_vertex_groups(obj, weights)

			bpy.ops.object.mode_set(mode='OBJECT')
			for o in context.selected_objects:
				o.select_set(False)
			arm.select_set(True)
			obj.select_set(True)
			context.view_layer.objects.active = obj
			bpy.ops.object.mode_set(mode='WEIGHT_PAINT')

			return {'FINISHED'}

		def invoke(self, context, event):
			global _preview
			handler = bpy.types.SpaceView3D.draw_handler_add(
				_draw_order_overlay, (), 'WINDOW', 'POST_PIXEL'
			)
			chain_order_overlay._preview = {"op": self, "handler": handler}
			context.area.tag_redraw()
			return context.window_manager.invoke_props_dialog(self, width=300)			
		
		def draw(self, context):
			layout = self.layout
			
			obj = context.active_object

			chains = find_chains_from_selection(context)
			if len(chains) == 0:
				self.report({'ERROR'}, "No chains selected.")

			layout.label(text=f"Found {len(chains)} chains.")

			min_length = min(len(chain) for chain in chains)
			max_length = max(len(chain) for chain in chains)

			if len(chains) > 1:
				layout.separator()
				col = layout.column()
				col.prop(self, "stitch_chain")

				if self.stitch_chain and min_length != max_length:
					col.prop(self, "chain_align")

				if self.stitch_chain:
					col.prop(self, "close_loop")

					box = layout.box()
					box.label(text="Chain Order Settings:", icon='SORTALPHA')
					box.prop(self, "order_mode")
					row = box.row(align=True)
					row.prop(self, "order_axis", expand=True)
					if self.order_mode == 'ANGULAR':
						box.prop(self, "order_start_angle")
					box.prop(self, "order_invert")

			layout.separator()
			col = layout.column()
			col.prop(self, "object_name")
			col.prop(self, "seed_weights")
			if self.seed_weights:
				col.prop(self, "spread_weights")
			if self.seed_weights and self.spread_weights:
				col.prop(self, "carry_v")
				if self.sitch_chain:
					col.prop(self, "carry_h")
				col.prop(self, "iterations")
				col.separator()
				col.prop(self, "protect_rows")

			for area in context.screen.areas:
				if area.type == 'VIEW_3D':
					area.tag_redraw()

		def cancel(self, context):
			_remove_preview(context)			

classes = (
		RIG_OT_weight_paint_proxy,
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
