import bpy
import re
from rigtools.utils.bone_chain import find_chains_from_selection, rename_chain, rename_chains, name_segment_types
from rigtools.utils.bone_chain import sort_chains

class RIG_OT_rename_chain(bpy.types.Operator):
		"""Batch rename bones via find and replace, add prefix/suffix, and strip numbers"""
		bl_idname = "rig.rename_chain"
		bl_label = "Rename Chain"
		bl_options = {'REGISTER', 'UNDO'}
		bl_property = "find"
		
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
			min=0.0,
			max=360.0,
			default=0.0
		)

		order_invert: bpy.props.BoolProperty(
			name="Order Invert",
			description="Invert the order of the bones.",
			default=False
		)
	

		def execute(self, context):
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
				box = col.box()
				box.prop(self, "order_mode")
				row = box.row(align=True)
				row.prop(self, "order_axis", expand=True)
				if self.order_mode == 'ANGULAR':
					box.prop(self, "order_start_angle")
				box.prop(self, "order_invert")

classes = (
		RIG_OT_rename_chain,
)


import bpy

addon_keymaps = []

def register():
		for cls in classes:
				bpy.utils.register_class(cls)

def unregister():
		
		for cls in classes:
				bpy.utils.unregister_class(cls)

if __name__ == "__main__":
		try:
				unregister()
		except Exception:
				pass
		register()
