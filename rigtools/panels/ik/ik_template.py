import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, StringProperty

from rigtools.assemblies.ik_assembly import IKAssemblyOptions, create_ik_assembly
from rigtools.assemblies.ik_templates import (
	IK_TEMPLATES,
	get_ik_template,
	resolve_ik_parents,
	validate_ik_templates,
)
from rigtools.assemblies.template_options import resolve_template_options
from rigtools.rig_ui.property_name import guess_limb_name
from rigtools.tool.spline_ik import spline_twist_type
from rigtools.utils.bone_chain import (
	ChainBranchingError,
	find_chains_from_selection,
	get_assembly_chains,
)
from rigtools.utils.widget import fk_widget_types


class RIG_OT_create_ik_from_template(bpy.types.Operator):
	"""Create an IK assembly from a template."""

	bl_idname = "rig.create_ik_from_template"
	bl_label = "Create IK From Template"
	bl_options = {'REGISTER', 'UNDO'}

	template_id: StringProperty(options={'HIDDEN'})

	limb_property_base_name: StringProperty(
		name="Limb Property Base Name",
		description="Base name used for the limb properties and collections",
		default="",
	)

	add_tweak_bones: BoolProperty(name="Add Tweak Bones", default=True)

	switch_property_type: EnumProperty(
		name="Switch Property Type",
		items=[
			('ENUM', "Enum", "Dropdown with FK and IK options"),
			('FLOAT', "Float", "Float slider between 0.0 and 1.0"),
		],
		default='ENUM',
	)

	add_rotation_isolation: BoolProperty(name="Add Rotation Isolation", default=True)
	override_collections: BoolProperty(name="Override Bone Collections", default=True)

	ik_type: EnumProperty(
		name="IK Type",
		items=[
			('IK', "IK", "Standard IK setup"),
			('SPLINE', "Spline IK", "Spline IK setup"),
		],
		default='IK',
	)

	enable_ik_stretch: BoolProperty(name="Enable IK Stretch", default=True)
	pole_distance: FloatProperty(name="Pole Distance", default=1.0, min=0.0)
	spline_control_count: IntProperty(name="Control Count", default=3, min=2, max=10)
	spline_skip_first: BoolProperty(name="Skip First Bone", default=False)

	twist_type: EnumProperty(
		name="Twist Controllers",
		items=spline_twist_type,
		default='START_END',
	)

	tweak_relationship: EnumProperty(
		name="Tweak Relationship",
		items=[
			('STRETCH_TO', 'Stretch To', 'Stretch the tweak bone to the target bone'),
			('DAMPED_TRACK', 'Damped Track', 'Damped track the tweak bone to the target bone'),
		],
		default='STRETCH_TO',
	)

	fk_widget: EnumProperty(
		name="FK Widget",
		items=fk_widget_types,
		default='FK',
	)

	enable_snapping: BoolProperty(name="Enable FK<->IK Snapping", default=True)

	ik_parent: BoolProperty(name="Setup IK Parent Switching", default=False)

	@classmethod
	def description(cls, context, properties):
		return get_ik_template(properties.template_id).description

	def invoke(self, context, event):
		try:
			template = get_ik_template(self.template_id)
		except (ChainBranchingError, ValueError) as error:
			self.report({'ERROR'}, str(error))
			return {'CANCELLED'}

		option_values = resolve_template_options(IKAssemblyOptions, template.options)

		if option_values.get("limb_property_base_name"):
			self.limb_property_base_name = option_values["limb_property_base_name"]
		else:
			try:
				chains = find_chains_from_selection(context)
			except ChainBranchingError as error:
				self.report({'ERROR'}, str(error))
				return {'CANCELLED'}

			if not chains:
				self.report({'ERROR'}, "No chains selected.")
				return {'CANCELLED'}

			self.limb_property_base_name = guess_limb_name(chains[0][0], context)

		for property_name in template.redo_fields:
			if property_name != "limb_property_base_name":
				setattr(self, property_name, option_values[property_name])

		return self.execute(context)

	def execute(self, context):
		try:
			template = get_ik_template(self.template_id)
		except ValueError as error:
			self.report({'ERROR'}, str(error))
			return {'CANCELLED'}

		option_values = resolve_template_options(IKAssemblyOptions, template.options)
		if not option_values.get("limb_property_base_name"):
			if self.properties.is_property_set("limb_property_base_name"):
				option_values["limb_property_base_name"] = self.limb_property_base_name
			else:
				try:
					chains = find_chains_from_selection(context)
				except ChainBranchingError as error:
					self.report({'ERROR'}, str(error))
					return {'CANCELLED'}

				if not chains:
					self.report({'ERROR'}, "No chains selected.")
					return {'CANCELLED'}

				option_values["limb_property_base_name"] = guess_limb_name(chains[0][0], context)

		for property_name in template.redo_fields:
			if self.properties.is_property_set(property_name):
				option_values[property_name] = getattr(self, property_name)

		if not option_values["limb_property_base_name"]:
			self.report({'ERROR'}, "Limb property base name is required.")
			return {'CANCELLED'}

		obj = context.object
		if not obj or obj.type != 'ARMATURE':
			self.report({'ERROR'}, "Active object must be an armature.")
			return {'CANCELLED'}

		try:
			parent_names = option_values.pop("ik_parents", ())
			parents, include_self = resolve_ik_parents(context, parent_names)
			option_values["ik_parents"] = parents
			option_values["add_ik_control_as_pole_parent"] = include_self
			options = IKAssemblyOptions(**option_values)
		except (KeyError, TypeError, ValueError) as error:
			self.report({'ERROR'}, f"Invalid IK template '{self.template_id}': {error}")
			return {'CANCELLED'}

		try:
			chains, original_mode = get_assembly_chains(context)
		except Exception as error:
			self.report({'ERROR'}, str(error))
			return {'CANCELLED'}

		for chain in chains:
			if len(chain) == 1:
				self.report({'ERROR'}, "All chains must have at least 2 bones.")
				bpy.ops.object.mode_set(mode=original_mode)
				return {'CANCELLED'}

		try:
			create_ik_assembly(context, chains, template.label, options)
		except Exception as error:
			self.report({'ERROR'}, str(error))
			bpy.ops.object.mode_set(mode=original_mode)
			return {'CANCELLED'}

		chain_count = len(chains)
		self.report(
			{'INFO'},
			f"Created {template.label} for {chain_count} chain{'s' if chain_count != 1 else ''}.",
		)
		return {'FINISHED'}

	def draw(self, context):
		template = get_ik_template(self.template_id)
		split_size = 0.5
		for property_name in template.redo_fields:
			prop = self.properties.bl_rna.properties[property_name]

			if prop.type == 'BOOLEAN':
				self.layout.prop(self, property_name)
				continue

			split = self.layout.split(factor=split_size, align=True)
			split.label(text=f"{prop.name}:")
			split.prop(self, property_name, text="")


classes = (
	RIG_OT_create_ik_from_template,
)


def register():
	validate_ik_templates()
	for cls in classes:
		bpy.utils.register_class(cls)


def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
