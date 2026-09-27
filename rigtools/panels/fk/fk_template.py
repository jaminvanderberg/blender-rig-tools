import bpy
from bpy.props import BoolProperty, EnumProperty, IntProperty, StringProperty

from rigtools.assemblies.fk_assembly import FKAssemblyOptions, create_fk_assembly
from rigtools.assemblies.fk_templates import FK_TEMPLATES, get_fk_template, validate_fk_templates
from rigtools.assemblies.template_options import resolve_template_options
from rigtools.preferences import get_preferences
from rigtools.rig_ui.property_name import guess_limb_name
from rigtools.utils.bone_chain import (
	ChainBranchingError,
	find_chains_from_selection,
	get_assembly_chains,
)
from rigtools.utils.widget import fk_widget_types


class RIG_OT_create_fk_from_template(bpy.types.Operator):
	"""Create an FK assembly from a template."""

	bl_idname = "rig.create_fk_from_template"
	bl_label = "Create FK From Template"
	bl_options = {'REGISTER', 'UNDO'}

	template_id: StringProperty(options={'HIDDEN'})

	limb_property_base_name: StringProperty(
		name="Limb Property Base Name",
		description="Base name used for the limb properties and collections",
		default="",
	)

	do_create_fk: BoolProperty(name="Create FK Bones", default=True)

	fk_bone_template: StringProperty(
		name="FK Bone Template",
		default="FK-{name}",
	)

	skip_first_tweak: BoolProperty(name="Skip First Tweak", default=False)

	fk_widget: EnumProperty(
		name="FK Widget",
		items=fk_widget_types,
		default='CIRCLE',
	)

	create_rotation_follow_setup: BoolProperty(name="Create Rotation Follow Setup", default=False)

	rotation_follow_skip: IntProperty(name="Rotation Follow Skip", default=1, min=0)

	rotation_follow_relationship: EnumProperty(
		name="Rotation Follow Relationship",
		items=[
			('COPY_ROTATION', 'Copy Rotation', 'Copy rotation from the master bone'),
			('COPY_TRANSFORMS', 'Copy Transforms', 'Copy transforms from the master bone'),
		],
		default='COPY_ROTATION',
	)

	tweak_relationship: EnumProperty(
		name="Tweak Relationship",
		items=[
			('STRETCH_TO', 'Stretch To', 'Stretch the tweak bone to the target bone'),
			('DAMPED_TRACK', 'Damped Track', 'Damped track the tweak bone to the target bone'),
		],
		default='STRETCH_TO',
	)

	add_rotation_isolation: BoolProperty(name="Add Rotation Isolation", default=True)
	override_collections: BoolProperty(name="Override Bone Collections", default=True)

	@classmethod
	def description(cls, context, properties):
		return get_fk_template(properties.template_id).description

	def invoke(self, context, event):
		try:
			template = get_fk_template(self.template_id)
		except ValueError as error:
			self.report({'ERROR'}, str(error))
			return {'CANCELLED'}

		option_values = resolve_template_options(FKAssemblyOptions, template.options)

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
			template = get_fk_template(self.template_id)
		except ValueError as error:
			self.report({'ERROR'}, str(error))
			return {'CANCELLED'}

		option_values = resolve_template_options(FKAssemblyOptions, template.options)
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

		if option_values.get("add_rotation_isolation") and not option_values.get("limb_property_base_name"):
			self.report({'ERROR'}, "Limb property base name is required for rotation isolation.")
			return {'CANCELLED'}

		obj = context.object
		if not obj or obj.type != 'ARMATURE':
			self.report({'ERROR'}, "Active object must be an armature.")
			return {'CANCELLED'}

		if "fk_bone_template" not in template.options:
			option_values["fk_bone_template"] = get_preferences().fk_template

		try:
			options = FKAssemblyOptions(**option_values)
		except (KeyError, TypeError, ValueError) as error:
			self.report({'ERROR'}, f"Invalid FK template '{self.template_id}': {error}")
			return {'CANCELLED'}

		try:
			chains, original_mode = get_assembly_chains(
				context,
				check_property_bone=options.add_rotation_isolation,
			)
		except Exception as error:
			self.report({'ERROR'}, str(error))
			return {'CANCELLED'}

		try:
			create_fk_assembly(context, chains, template.label, options)
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
		template = get_fk_template(self.template_id)
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
	RIG_OT_create_fk_from_template,
)


def register():
	validate_fk_templates()
	for cls in classes:
		bpy.utils.register_class(cls)


def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
