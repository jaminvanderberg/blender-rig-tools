from collections import defaultdict
import json
import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty, IntProperty
from rigtools.assemblies.assembly_data import find_assembly
from rigtools.assemblies.palm_assembly import PalmAssemblyOptions
from rigtools.assemblies.palm_templates import get_palm_template
from rigtools.assemblies.template_options import resolve_template_options
from rigtools.panels.template_draw import TemplateDraw
from rigtools.tool.twist_bones import falloff_presets
from rigtools.utils import chain_order_overlay, _draw_order_overlay
from rigtools.utils.bone import get_selected_bones
from rigtools.utils.naming import get_base_name
from rigtools.utils.widget import fk_widget_types

def find_palm_chains_from_selection(context):
	selected_bones = get_selected_bones(context)
	if not selected_bones:
		return []

	by_side = defaultdict(list)
	for bone in selected_bones:
		_base, side = get_base_name(bone.name)
		by_side[side].append(bone.name)
		
	return [by_side[key] for key in by_side.keys()]

class RIG_OT_advanced_palm_setup(bpy.types.Operator):
	"""Setup Palm Assembly with advanced options"""
	bl_idname = "rig.advanced_palm_setup"
	bl_label = "Generate Palm Assembly"
	bl_options = {'REGISTER', 'UNDO'}

	limb_property_base_name: StringProperty(
		name="Limb Property Base Name",
		description="Base name of the property to store the limb. Example: 'arm', 'leg', 'tail', etc.",
		default="hand"
	)

	fk_widget: EnumProperty(
		name="FK Widget",
		description="Type of widget to use for the FK bones",
		items=fk_widget_types,
		default='PILL'
	)

	index_falloff_type: EnumProperty(
		name="Index Falloff Type",
		description="Type of falloff for the index",
		items=falloff_presets,
		default='SHARP'
	)

	pinky_falloff_type: EnumProperty(
		name="Pinky Falloff Type",
		description="Type of falloff for the pinky",
		items=falloff_presets,
		default='LINEAR'
	)

	assembly_uid: StringProperty(
		name="Assembly UID",
		description="UID of the assembly to use for the palm assembly",
		default="",
		options={'HIDDEN'}
	)

	template_id: StringProperty(
		name="Template ID",
		description="Palm template to apply on invoke",
		default="",
		options={'HIDDEN'}
	)

	template_name: StringProperty(
		name="Template Name",
		description="Name of the template to use for the palm assembly",
		default="",
		options={'HIDDEN'}
	)

	order_axis: bpy.props.EnumProperty(
		name="Order Axis",
		description="Axis to use for the order of the bones.",
		items=[
			('X', "X", "X axis"),
			('Y', "Y", "Y axis"),
			('Z', "Z", "Z axis"),
		],
		default='Y'
	)

	order_invert: bpy.props.BoolProperty(
		name="Order Invert",
		description="Invert the order of the bones.",
		default=False
	)	
		
	@classmethod
	def description(cls, context, properties):
		if properties.template_id:
			template = get_palm_template(properties.template_id)
			if template:
				return template.description
		return "Setup torso assembly with advanced options"

	##################################################################################################
	# invoke

	def _invoke_from_selection(self, context):
		chains = find_palm_chains_from_selection(context)

		if not chains:
			self.report({'ERROR'}, "No chains selected.")
			return {'CANCELLED'}

		self.template_name = "Advanced"

	def _invoke_from_template(self, context):
		template = get_palm_template(self.template_id)
		if not template:
			self.report({'ERROR'}, f"Unknown palm template: '{self.template_id}'")
			return {'CANCELLED'}

		option_values = resolve_template_options(PalmAssemblyOptions, template.options)
		for key, value in option_values.items():
			setattr(self, key, value)

		chains = find_palm_chains_from_selection(context)
		if not chains:
			self.report({'ERROR'}, "No chains selected.")
			return {'CANCELLED'}

		self.template_name = template.label

	def _invoke_from_assembly(self, context):
		assembly = find_assembly(context.object, self.assembly_uid)
		if not assembly:
			self.report({'ERROR'}, "Assembly not found.")
			return {'CANCELLED'}

		options = assembly.get_options()
		for key, value in options.items():
			setattr(self, key, value)

		self.template_name = assembly.template_name
		self.template_id = assembly.template_id

	def invoke(self, context, event):
		show_dialog = True

		if self.assembly_uid:
			result = self._invoke_from_assembly(context)
		elif self.template_id:
			result = self._invoke_from_template(context)
			template = get_palm_template(self.template_id)
			if template:
				show_dialog = template.show_dialog
		else:
			result = self._invoke_from_selection(context)

		if result == {'CANCELLED'}:
			return result

		global _preview
		handler = bpy.types.SpaceView3D.draw_handler_add(
			_draw_order_overlay, (), 'WINDOW', 'POST_PIXEL'
		)
		chain_order_overlay._preview = {
			"op": self, 
			"handler": handler, 
			"get_chains": lambda ctx: [
				[[n] for n in names]
				for names in find_palm_chains_from_selection(ctx)
			]
		}
		context.area.tag_redraw()

		if show_dialog:
			return context.window_manager.invoke_props_dialog(self, width=350)
		return self.execute(context)

	##################################################################################################
	# draw

	def draw(self, context):
		layout = self.layout
		template = get_palm_template(self.template_id) if self.template_id else None
		split_size = 0.6

		def field_visible(field_name):
			return True

		draw = TemplateDraw(self, template, split_size=split_size)

		draw.box_section(layout, ["limb_property_base_name", "fk_widget", "index_falloff_type", "pinky_falloff_type"], 
			"Palm Settings:", "SETTINGS", lambda col: (

			draw.draw_section(col, ["limb_property_base_name"], lambda: (
				draw.split_field(col, "Limb Property Base Name:", "limb_property_base_name"),
			)),
			draw.draw_section(col, ["fk_widget", "index_falloff_type", "pinky_falloff_type"], lambda: (
				draw.split_field(col, "Index Falloff Type:", "index_falloff_type"),
				draw.split_field(col, "Pinky Falloff Type:", "pinky_falloff_type"),
				draw.split_field(col, "FK Widget:", "fk_widget"),
			)),
		))
		draw.box_section(layout, ["order_axis", "order_invert"], "Order:", "EMPTY_AXIS", lambda col: (
			draw.split_field(col, "Order Axis:", "order_axis"),
			draw.split_field(col, "Order Invert:", "order_invert"),
		))


	##################################################################################################
	# execute

	def execute(self, context):
		if not self.limb_property_base_name:
			self.report({'ERROR'}, "Limb property base name is required.")
			return {'CANCELLED'}

		try:
			chains, original_mode, original_mirror = get_assembly_chains(
				context,
				self.assembly_uid,
				check_property_bone=self.add_neck_rotation_isolation or self.add_head_rotation_isolation,
			)
		except Exception as e:
			self.report({'ERROR'}, str(e))
			return {'CANCELLED'}

		options = TorsoAssemblyOptions(
			limb_property_base_name=self.limb_property_base_name,
			lower_torso_bone_count=self.lower_torso_bone_count,
			neck_bone_count=self.neck_bone_count,
			use_twist_bones=self.use_twist_bones,
			neck_twist_bone_count=self.neck_twist_bone_count,
			chest_twist_bone_count=self.chest_twist_bone_count,
			tweak_relationship=self.tweak_relationship,
			add_neck_rotation_isolation=self.add_neck_rotation_isolation,
			neck_base_property_name=self.neck_base_property_name,
			neck_inherit_scale_from_root=self.neck_inherit_scale_from_root,
			add_head_rotation_isolation=self.add_head_rotation_isolation,
			head_base_property_name=self.head_base_property_name,
			head_inherit_scale_from_root=self.head_inherit_scale_from_root,
			fk_widget=self.fk_widget,
			neck_falloff_type=self.neck_falloff_type,
		)

		assembly_uid = self.assembly_uid

		def rebuild():
			return reconfigure_assembly(
				context, 
				assembly_uid, 
				lambda prior_configs: create_torso_assembly(
					context,
					chains,
					self.template_id,
					self.template_name,
					options,
					replacement_uid=assembly_uid,
					prior_configs=prior_configs,
				),
			)

		try:
			torso_controls = run_assembly_transaction(rebuild)
		except AssemblyTransactionError as e:
			self.report({'ERROR'}, str(e))
			bpy.ops.object.mode_set(mode=original_mode)
			context.object.data.use_mirror_x = original_mirror
			return {'CANCELLED'}

		if torso_controls:
			bpy.ops.pose.select_all(action='DESELECT')
			select_bones(context.object, torso_controls)

		chain_count = len(chains)
		self.report({'INFO'}, f"Successfully generated {chain_count} torso assembl{'ies' if chain_count != 1 else 'y'}.")
		context.object.data.use_mirror_x = original_mirror
		return {'FINISHED'}


classes = (
	RIG_OT_advanced_torso_setup,
)


def register():
	validate_torso_templates()
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

	bpy.ops.rig.advanced_torso_setup('INVOKE_DEFAULT')
