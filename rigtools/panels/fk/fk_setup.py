import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty, IntProperty, FloatProperty

from rigtools.assemblies.assembly_transaction import AssemblyTransactionError, run_assembly_transaction
from rigtools.assemblies.delete_assembly import delete_assembly
from rigtools.assemblies.assembly_data import find_assembly, get_assembly_chains
from rigtools.assemblies.fk_assembly import FKAssemblyOptions, create_fk_assembly
from rigtools.assemblies.fk_templates import get_fk_template, validate_fk_templates
from rigtools.assemblies.template_options import resolve_template_options
from rigtools.panels.template_draw import TemplateDraw
from rigtools.preferences import get_preferences
from rigtools.tool.skirt_ride import SkirtLeg
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

	create_rotation_follow_setup: BoolProperty(
		name="Create Rotation Follow Setup",
		description="Create a rotation follow setup along the FK chain.",
		default=True
	)

	rotation_follow_skip: IntProperty(
		name="Rotation Follow Skip",
		description="Number of bones to skip before creating a rotation follow setup.",
		default=1,
		min=0,
	)

	rotation_follow_relationship: EnumProperty(
		name="Rotation Follow Relationship",
		description="Type of relationship for the rotation follow setup.",
		items=[
			('COPY_ROTATION', 'Copy Rotation', 'Copy rotation from the master bone'),
			('COPY_TRANSFORMS', 'Copy Transforms', 'Copy transforms from the master bone'),
		],
		default='COPY_ROTATION'
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
		prefs = get_preferences()

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
			return True

		draw = TemplateDraw(self, template, split_size=split_size, visible_func=field_visible)

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
		draw.draw_section(layout, ["add_rotation_isolation", "create_rotation_follow_setup", "rotation_follow_skip", "rotation_follow_relationship"], lambda: (
			draw.full_field(layout, "Add Rotation Isolation", "add_rotation_isolation"),
			draw.full_field(layout, "Create Rotation Follow Setup", "create_rotation_follow_setup"),
			draw.box_section(layout, ["rotation_follow_skip", "rotation_follow_relationship"], "Rotation Follow Setup:", 'CONSTRAINT', lambda col: (
				draw.full_field(col, "Rotation Follow Skip:", "rotation_follow_skip"),
				draw.split_field(col, "Rotation Follow Relationship:", "rotation_follow_relationship"),
			))
		))
		draw.draw_section(layout, ["add_skirt_collision", "add_skirt_ride"], lambda: (
			draw.full_field(layout, "Add Skirt Collision", "add_skirt_collision"),
			draw.full_field(layout, "Add Skirt Ride", "add_skirt_ride"),
		))
		
	##################################################################################################
	# execute

	def execute(self, context):
		if self.add_rotation_isolation and not self.limb_property_base_name:
			self.report({'ERROR'}, "Limb property base name is required for rotation isolation.")
			return {'CANCELLED'}

		try:
			chains, original_mode, original_mirror = get_assembly_chains(
				context,
				self.assembly_uid,
				check_property_bone=self.add_rotation_isolation or self.add_skirt_collision,
			)
		except Exception as e:
			self.report({'ERROR'}, str(e))
			return {'CANCELLED'}

		if self.control_mode != 'TWEAK':
			self.control_mode = 'FK/TWEAK' if self.add_tweak_bones else 'FK'

		options = FKAssemblyOptions(
			limb_property_base_name=self.limb_property_base_name,
			control_mode=self.control_mode,
			fk_bone_template=bone_template('fk'),
			skip_first_tweak=self.skip_first_tweak,
			fk_widget=self.fk_widget,
			create_rotation_follow_setup=self.create_rotation_follow_setup,
			rotation_follow_skip=self.rotation_follow_skip,
			rotation_follow_relationship=self.rotation_follow_relationship,
			fk_collection_name=self.fk_collection_name,
			tweak_collection_name=self.tweak_collection_name,
			tweak_relationship=self.tweak_relationship,
			add_rotation_isolation=self.add_rotation_isolation,
			add_skirt_collision=self.add_skirt_collision,
			skirt_collision_target_bone_names=['ORG-thigh.L'],
			add_skirt_ride=self.add_skirt_ride,
			skirt_ride_legs=[SkirtLeg(bone_name='ORG-thigh.L', forward_axis='+X'), SkirtLeg(bone_name='ORG-thigh.R', forward_axis='-X')],
		)

		assembly_uid = self.assembly_uid

		def rebuild():
			if assembly_uid:
				delete_assembly(context, assembly_uid)

			return create_fk_assembly(
				context,
				chains,
				self.template_id,
				self.template_name,
				options,
				replacement_uid=assembly_uid,
			)

		try:
			run_assembly_transaction(rebuild)
		except AssemblyTransactionError as e:
			self.report({'ERROR'}, str(e))
			bpy.ops.object.mode_set(mode=original_mode)
			context.object.data.use_mirror_x = original_mirror
			return {'CANCELLED'}

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
	for cls in classes:
		bpy.utils.unregister_class(cls)


if __name__ == "__main__":
	try:
		unregister()
	except Exception:
		pass
	register()

	bpy.ops.rig.advanced_fk_setup('INVOKE_DEFAULT')
