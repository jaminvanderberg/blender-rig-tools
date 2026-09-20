import bpy
from rigtools.utils.bone_chain import sort_chains, get_name_segment, find_chains_from_selection
import gpu
import blf
from bpy_extras.view3d_utils import location_3d_to_region_2d
from rigtools.utils.chain_order_overlay import _draw_order_overlay, _remove_preview
from rigtools.utils import chain_order_overlay

def stitch_cols(a, b, faces):
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

		def execute(self, context):
			_remove_preview(context)

			arm = context.object

			chains = find_chains_from_selection(context)
			if self.stitch_chain and len(chains) > 1:
				chains = sort_chains(context, chains, self.order_mode, self.order_axis, self.order_start_angle, self.order_invert)
			
			bones = context.object.data.edit_bones if context.mode == 'EDIT_ARMATURE' else context.object.data.bones

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
					stitch_cols(grid[c], grid[c+1], faces)
				if self.close_loop:
					stitch_cols(grid[-1], grid[0], faces)

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
				for col_idx, chain in enumerate(chains):
					col = grid[col_idx]
					for row, bone_name in enumerate(chain):
						bg = obj.vertex_groups.get(bone_name) or obj.vertex_groups.new(name=bone_name)
						bg.add([col[row]], 1.0, 'REPLACE')
					vg = obj.vertex_groups.get(chain[-1]) or obj.vertex_groups.new(name=chain[-1])
					vg.add([col[-1]], 1.0, 'REPLACE')

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

			layout.separator()
			col = layout.column()
			col.prop(self, "stitch_chain")
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
