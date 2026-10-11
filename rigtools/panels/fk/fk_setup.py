import bpy
from bpy.props import (
	StringProperty,
	BoolProperty,
	EnumProperty,
	IntProperty,
)

from rigtools.assemblies.reconfigure_assembly import reconfigure_assembly
from rigtools.assemblies.assembly_transaction import AssemblyTransactionError, run_assembly_transaction
from rigtools.assemblies.assembly_data import find_assembly, get_assembly_chains
from rigtools.assemblies.fk_assembly import FKAssemblyOptions, create_fk_assembly
from rigtools.assemblies.fk_templates import get_fk_template, validate_fk_templates
from rigtools.assemblies.template_options import resolve_template_options
from rigtools.panels.skirt_legs import draw_skirt_legs, fill_skirt_legs, iter_skirt_leg_slots
from rigtools.panels.template_draw import TemplateDraw
from rigtools.utils.skirt_legs import FORWARD_AXIS_ITEMS, scan_leg_assemblies
from rigtools.tool.skirt_ride import SkirtLeg
from rigtools.utils.bone import select_bones
from rigtools.utils.naming import bone_template, guess_limb_name
from rigtools.utils.bone_chain import ChainBranchingError, find_chains_from_selection
from rigtools.utils.widget import fk_widget_types

class RIG_OT_advanced_fk_tweak_setup(bpy.types.Operator):
	"""Setup FK/Tweak setup with advanced options"""
	bl_idname = "rig.advanced_fk_setup"
	bl_label = "Generate FK Assembly"
	bl_options = {'REGISTER', 'UNDO'}

	limb_property_base_name: StringProperty(
		name="Limb Property Base Name",
		description="Base name of the property to store the limb. Example: 'arm', 'leg', 'tail', etc.",
		default=""
	)

	control_mode: EnumProperty(
		name="Control Mode",
		description="Control mode for the FK/Tweak chain",
		items=[
			('FK/TWEAK', 'FK/TWEAK', 'Create an FK/Tweak chain'),
			('FK', 'FK only', 'Create an simple FK chain without tweak bones'),
			('TWEAK', 'TWEAK only', 'Create a tweak only chain. Tweak bones should be re-parented later.'),
		],
		default='FK/TWEAK'
	)

	add_tweak_bones: BoolProperty(
		name="Add Tweak Bones",
		description="Add tweak bones to the chain",
		default=True
	)

	skip_first_tweak: BoolProperty(
		name="Skip First Tweak",
		description="Skip the first tweak bone",
		default=False
	)

	fk_widget: EnumProperty(
		name="FK Widget",
		description="Create widgets for the FK bones",
		items=fk_widget_types,
		default='CIRCLE'
	)

	override_collections: BoolProperty(
		name="Override Bone Collections",
		description="Specify the bone collections for various bone types",
		default=True
	)

	add_rotation_isolation: BoolProperty(
		name="Add Rotation Isolation",
		description="Add rotation isolation to the FK bones.",
		default=False
	)

	create_master_controllers: BoolProperty(
		name="Create FK Master Controllers / FK Follow",
		description="Create master controllers along the FK chain.",
		default=True
	)

	master_controllers_spacing: EnumProperty(
		name="Master Controllers Spacing",
		description="Spacing of the master controllers.",
		items=[
			('SINGLE', 'Single Controller', 'Use a single master controller'),
			('INTERVAL', 'Interval', 'Use an interval between master controllers'),
		],
		default='SINGLE'
	)

	master_controllers_interval: IntProperty(
		name="Interval",
		description="Number of bones to skip before creating a master controller.",
		options={'HIDDEN'}
	)

	master_controllers_interval_UI: IntProperty(
		name="Interval",
		description="Number of bones to skip before creating a master controller.",
		default=3,
		min=2,
	)

	master_controllers_skip_first: BoolProperty(
		name="Skip First",
		description="Skip the first bone when creating master controllers.",
		default=False
	)

	master_controllers_type: EnumProperty(
		name="Type",
		description="Type of master controller to create.",
		items=[
			('FK', 'Use FK Bones', 'Use the existing FK bones as master controllers (FK follow)'),
			('MASTER', 'Add Dedicated Masters', 'Create dedicated master controllers'),
		],
		default='FK'
	)

	master_controllers_widget: EnumProperty(
		name="Master Controller Widget",
		description="Type of widget to create for the master controllers.",
		items=fk_widget_types,
		default='CIRCLE'
	)

	fk_collection_name: StringProperty(
		name="FK Collection Name",
		description="Name of the collection to store the FK bones, or blank to copy collection from selected bones",
		default=""
	)

	tweak_collection_name: StringProperty(
		name="Tweak Collection Name",
		description="Name of the collection to store the tweak bones, or blank to copy collection from selected bones",
		default=""
	)

	tweak_relationship: EnumProperty(
		name="Tweak Relationship",
		description="Type of relationship for the tweak bones",
		items=[
			('STRETCH_TO', 'Stretch To', 'Stretch the tweak bone to the target bone'),
			('DAMPED_TRACK', 'Damped Track', 'Damped track the tweak bone to the target bone'),
		],
		default='STRETCH_TO'
	)

	assembly_uid: StringProperty(
		name="Assembly UID",
		description="UID of the assembly to use for the FK/Tweak chain",
		default="",
		options={'HIDDEN'}
	)

	template_id: StringProperty(
		name="Template ID",
		description="FK template to apply on invoke",
		default="",
		options={'HIDDEN'}
	)

	template_name: StringProperty(
		name="Template Name",
		description="Name of the template to use for the FK/Tweak chain",
		default="",
		options={'HIDDEN'}
	)

	add_skirt_collision: BoolProperty(
		name="Add Skirt Collision",
		description="Add skirt collision to the FK bones.",
		default=False
	)

	add_skirt_ride: BoolProperty(
		name="Add Skirt Ride",
		description="Short skirts typically ride up when the leg is lifted.",
		default=False
	)

	@classmethod
	def description(cls, context, properties):
		if properties.template_id:
			template = get_fk_template(properties.template_id)
			if template:
				return template.description
		return "Setup FK/Tweak setup with advanced options"

	##################################################################################################
	# invoke

	def _invoke_from_selection(self, context):
		try:
			chains = find_chains_from_selection(context)
		except ChainBranchingError as e:
			self.report({'ERROR'}, str(e))
			return {'CANCELLED'}

		if not chains:
			self.report({'ERROR'}, "No chains selected.")
			return {'CANCELLED'}

		self.limb_property_base_name = guess_limb_name(chains[0][0], context)
		self.template_name = "Advanced"
		self.template_id = ""

	def _invoke_from_template(self, context):
		template = get_fk_template(self.template_id)
		if not template:
			self.report({'ERROR'}, f"Unknown FK template: '{self.template_id}'")
			return {'CANCELLED'}

		option_values = resolve_template_options(FKAssemblyOptions, template.options)
		for key, value in option_values.items():
			setattr(self, key, value)

		if not self.limb_property_base_name:
			try:
				chains = find_chains_from_selection(context)
			except ChainBranchingError as error:
				self.report({'ERROR'}, str(error))
				return {'CANCELLED'}

			if not chains:
				self.report({'ERROR'}, "No chains selected.")
				return {'CANCELLED'}

			self.limb_property_base_name = guess_limb_name(chains[0][0], context)

		self.template_name = template.label

	def _invoke_from_assembly(self, context):
		assembly = find_assembly(context.object, self.assembly_uid)
		if not assembly:
			self.report({'ERROR'}, "Assembly not found.")
			return {'CANCELLED'}
		
		options = assembly.get_options()
		for key, value in options.items():
			if not hasattr(self, key):
				continue
			setattr(self, key, value)

		self.template_name = assembly.template_name
		self.template_id = assembly.template_id

	def invoke(self, context, event):
		show_dialog = True

		if self.assembly_uid:
			result = self._invoke_from_assembly(context)
		elif self.template_id:
			result = self._invoke_from_template(context)
			template = get_fk_template(self.template_id)
			if template:
				show_dialog = template.show_dialog
		else:
			result = self._invoke_from_selection(context)

		if result == {'CANCELLED'}:
			return result

		self.add_tweak_bones = (self.control_mode != 'FK')
		self.master_controllers_spacing = 'SINGLE' if self.master_controllers_interval <= 1 else 'INTERVAL'
		self.master_controllers_interval_UI = self.master_controllers_interval if self.master_controllers_interval >= 2 else 3
		fill_skirt_legs(context)

		if show_dialog:
			return context.window_manager.invoke_props_dialog(self, width=350)
		return self.execute(context)

	##################################################################################################
	# draw

	def draw(self, context):
		layout = self.layout
		template = get_fk_template(self.template_id) if self.template_id else None
		split_size = 0.6

		def field_visible(field_name):
			if field_name in ["tweak_relationship", "skip_first_tweak"]:
				return self.control_mode != 'FK' and (self.add_tweak_bones or self.control_mode == 'TWEAK')
			if field_name in ["fk_widget"]:
				return self.control_mode != 'TWEAK'
			if field_name in ["add_tweak_bones"]:
				control_mode_visible = template is None or "control_mode" in template.redo_fields
				return self.control_mode != 'TWEAK' and not control_mode_visible
			if field_name in ["add_rotation_isolation", "create_rotation_follow_setup"]:
				return self.control_mode != 'TWEAK'
			if field_name in ["rotation_follow_skip", "rotation_follow_relationship"]:
				return self.create_rotation_follow_setup
			if field_name in ["skirt_legs"]:
				return self.add_skirt_collision or self.add_skirt_ride
			if field_name in ["create_master_controllers"]:
				return self.control_mode != 'TWEAK'
			if field_name in ["master_controllers_spacing", "master_controllers_skip_first", "master_controllers_type"]:
				return self.control_mode != 'TWEAK' and self.create_master_controllers
			if field_name in ["master_controllers_interval_UI"]:
				return self.control_mode != 'TWEAK' and self.create_master_controllers and self.master_controllers_spacing == 'INTERVAL'
			if field_name in ["master_controllers_widget"]:
				return self.control_mode != 'TWEAK' and self.create_master_controllers and self.master_controllers_type == 'MASTER'
			return True

		draw = TemplateDraw(self, template, split_size=split_size, visible_func=field_visible, 
			related_fields={
				"master_controllers_spacing": "master_controllers_interval",
				"master_controllers_interval_UI": "master_controllers_interval",
			}
		)

		draw.box_section(layout, ["limb_property_base_name", "control_mode", "fk_widget", "add_tweak_bones", "tweak_relationship", "skip_first_tweak"], 
			"FK Chain Settings:", "SETTINGS", lambda col: (

			draw.draw_section(col, ["limb_property_base_name", "control_mode", "fk_widget"], lambda: (
				draw.split_field(col, "Limb Property Base Name:", "limb_property_base_name"),
				draw.split_field(col, "Control Mode:", "control_mode"),
				draw.split_field(col, "FK Widget:", "fk_widget"),
			)),
			draw.draw_section(col, ["add_tweak_bones", "tweak_relationship", "skip_first_tweak"], lambda: (
				draw.full_field(col, "Add Tweak Bones", "add_tweak_bones"),
				draw.split_field(col, "Tweak Relationship:", "tweak_relationship"),
				draw.full_field(col, "Skip First Tweak", "skip_first_tweak"),
			)),
		))
		draw.draw_section(layout, ["create_master_controllers"], lambda: (
			draw.full_field(layout, "Create FK Master Controllers / FK Follow", "create_master_controllers"),
			draw.box_section(layout, ["master_controllers_spacing", "master_controllers_interval_UI", "master_controllers_skip_first", "master_controllers_type"], 
				"", "NONE", lambda col: (
		
				draw.draw_section(col, ["master_controllers_type", "master_controllers_spacing", "master_controllers_interval_UI", "master_controllers_skip_first"], lambda: (
					draw.expand_field(col, "master_controllers_type"),
					draw.expand_field(col, "master_controllers_spacing"),
					draw.full_field(col, "Interval", "master_controllers_interval_UI"),
					draw.full_field(col, "Skip First", "master_controllers_skip_first"),
				)),
				draw.draw_section(col, ["master_controllers_widget"], lambda: (
					draw.split_field(col, "Master Controller Widget:", "master_controllers_widget"),
				)),
			))
		))

		draw.draw_section(layout, ["add_skirt_collision", "add_skirt_ride", "skirt_legs"], lambda: (
			draw.full_field(layout, "Add Skirt Collision", "add_skirt_collision"),
			draw.full_field(layout, "Add Skirt Ride", "add_skirt_ride"),
			draw.box_section(layout, ["skirt_legs"], "", "NONE", lambda col: (
				draw_skirt_legs(context, col, show_axis=self.add_skirt_ride),
			)),
		))
		
	##################################################################################################
	# execute

	def execute(self, context):
		if self.add_rotation_isolation and not self.limb_property_base_name:
			self.report({'ERROR'}, "Limb property base name is required for rotation isolation.")
			return {'CANCELLED'}

		if self.add_skirt_collision and not self.limb_property_base_name:
			self.report({'ERROR'}, "Limb property base name is required for skirt collision.")
			return {'CANCELLED'}

		if self.add_skirt_ride and not self.limb_property_base_name:
			self.report({'ERROR'}, "Limb property base name is required for skirt ride.")
			return {'CANCELLED'}

		skirt_slots = list(iter_skirt_leg_slots(context))
		if (self.add_skirt_collision or self.add_skirt_ride) and not skirt_slots:
			self.report({'ERROR'}, "No skirt legs specified. Add leg assemblies or pick thigh bones.")
			return {'CANCELLED'}

		try:
			chains, original_mode, original_mirror = get_assembly_chains(
				context,
				self.assembly_uid,
				check_property_bone=self.add_rotation_isolation or self.add_skirt_collision or self.add_skirt_ride,
			)
		except Exception as e:
			self.report({'ERROR'}, str(e))
			return {'CANCELLED'}

		if self.control_mode != 'TWEAK':
			self.control_mode = 'FK/TWEAK' if self.add_tweak_bones else 'FK'

		interval = 0 if self.master_controllers_spacing == 'SINGLE' else self.master_controllers_interval_UI
		options = FKAssemblyOptions(
			limb_property_base_name=self.limb_property_base_name,
			control_mode=self.control_mode,
			fk_bone_template=bone_template('fk'),
			skip_first_tweak=self.skip_first_tweak,
			fk_widget=self.fk_widget,
			create_master_controllers=self.create_master_controllers,
			master_controllers_interval=interval,
			master_controllers_skip_first=self.master_controllers_skip_first,
			master_controllers_type=self.master_controllers_type,
			master_controllers_widget=self.master_controllers_widget,
			fk_collection_name=self.fk_collection_name,
			tweak_collection_name=self.tweak_collection_name,
			tweak_relationship=self.tweak_relationship,
			add_rotation_isolation=self.add_rotation_isolation,
			add_skirt_collision=self.add_skirt_collision,
			skirt_collision_target_bone_names=[slot.thigh for slot in skirt_slots],
			add_skirt_ride=self.add_skirt_ride,
			skirt_ride_legs=[
				SkirtLeg(bone_name=slot.thigh, forward_axis=slot.forward_axis)
				for slot in skirt_slots
			],
		)

		assembly_uid = self.assembly_uid

		def rebuild():
			return reconfigure_assembly(
				context, 
				assembly_uid, 
				lambda prior_configs: create_fk_assembly(
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
			fk_controls = run_assembly_transaction(rebuild)
		except AssemblyTransactionError as e:
			self.report({'ERROR'}, str(e))
			bpy.ops.object.mode_set(mode=original_mode)
			context.object.data.use_mirror_x = original_mirror
			return {'CANCELLED'}

		if fk_controls:
			bpy.ops.pose.select_all(action='DESELECT')
			select_bones(context.object, fk_controls)

		chain_count = len(chains)
		self.report({'INFO'}, f"Successfully generated {chain_count} FK/Tweak chain{'s' if chain_count != 1 else ''}.")
		context.object.data.use_mirror_x = original_mirror
		return {'FINISHED'}


classes = (
	RIG_OT_advanced_fk_tweak_setup,
)

def register():
	validate_fk_templates()
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)

if __name__ == "__main__":
	try:
		unregister()
	except Exception:
		pass
	register()

	bpy.ops.rig.advanced_fk_setup('INVOKE_DEFAULT')
