from dataclasses import MISSING, dataclass, fields
from typing import Any

import bpy
from bpy.props import BoolProperty, EnumProperty, IntProperty, StringProperty

from rigtools.assemblies.fk_assembly import FKAssemblyOptions, create_fk_assembly
from rigtools.preferences import get_preferences
from rigtools.rig_ui.property_name import guess_limb_name
from rigtools.utils.bone_chain import (
	ChainBranchingError,
	find_chains_from_selection,
	get_assembly_chains,
)
from rigtools.utils.widget import fk_widget_types


@dataclass(frozen=True)
class FKTemplate:
	label: str
	description: str
	icon: str
	options: dict[str, Any]
	redo_fields: tuple[str, ...] = ()


FK_TEMPLATES = {
	"simple": FKTemplate(
		label="Simple FK",
		description="Simple FK with rotation follow along the chain.",
		icon="BONE_DATA",
		options={
			"limb_property_base_name": "",
			"do_create_fk": True,
			"skip_first_tweak": False,
			"fk_widget": "CIRCLE",
			"create_rotation_follow_setup": True,
			"rotation_follow_skip": 1,
			"rotation_follow_relationship": "COPY_ROTATION",
			"tweak_relationship": "STRETCH_TO",
			"add_rotation_isolation": False,
			"override_collections": True,
		},
		redo_fields=(
			"limb_property_base_name",
			"fk_widget",
			"skip_first_tweak",
			"tweak_relationship",
			"add_rotation_isolation",
			"create_rotation_follow_setup",
			"rotation_follow_skip",
		),
	),
	"skirt": FKTemplate(
		label="Skirt FK",
		description="FK skirt with rotation follow along the chain.",
		icon="CON_GEOMETRYATTRIBUTE",
		options={
			"limb_property_base_name": "",
			"do_create_fk": True,
			"skip_first_tweak": False,
			"fk_widget": "RECTANGLE",
			"create_rotation_follow_setup": True,
			"rotation_follow_skip": 1,
			"rotation_follow_relationship": "COPY_ROTATION",
			"tweak_relationship": "STRETCH_TO",
			"add_rotation_isolation": True,
			"override_collections": True,
		},
		redo_fields=(
			"fk_widget",
			"skip_first_tweak",
			"tweak_relationship",
			"add_rotation_isolation",
			"create_rotation_follow_setup",
			"rotation_follow_skip",
		),
	),	
	"tail": FKTemplate(
		label="Tail",
		description="FK tail with rotation follow along the chain.",
		icon="CURVE_PATH",
		options={
			"limb_property_base_name": "tail",
			"do_create_fk": True,
			"skip_first_tweak": False,
			"fk_widget": "CIRCLE",
			"create_rotation_follow_setup": True,
			"rotation_follow_skip": 1,
			"rotation_follow_relationship": "COPY_ROTATION",
			"tweak_relationship": "STRETCH_TO",
			"add_rotation_isolation": True,
			"override_collections": True,
		},
		redo_fields=(
			"fk_widget",
			"skip_first_tweak",
			"tweak_relationship",
			"add_rotation_isolation",
			"create_rotation_follow_setup",
			"rotation_follow_skip",
		),
	),
	"finger": FKTemplate(
		label="Finger",
		description="Compact FK finger chain. Skips the first tweak.",
		icon="VIEW_PAN",
		options={
			"limb_property_base_name": "finger",
			"do_create_fk": True,
			"skip_first_tweak": True,
			"fk_widget": "CIRCLE",
			"create_rotation_follow_setup": True,
			"rotation_follow_skip": 1,
			"rotation_follow_relationship": "COPY_ROTATION",
			"tweak_relationship": "STRETCH_TO",
			"add_rotation_isolation": False,
			"override_collections": True,
		},
		redo_fields=(
			"fk_widget",
			"skip_first_tweak",
			"tweak_relationship",
			"add_rotation_isolation",
		),
	),
	"tweak": FKTemplate(
		label="Tweak Only",
		description="Tweak bones parented in a chain, without FK controls.",
		icon="PARTICLE_POINT",
		options={
			"limb_property_base_name": "",
			"do_create_fk": False,
			"skip_first_tweak": False,
			"fk_widget": "None",
			"create_rotation_follow_setup": False,
			"rotation_follow_skip": 1,
			"rotation_follow_relationship": "COPY_ROTATION",
			"tweak_relationship": "STRETCH_TO",
			"add_rotation_isolation": False,
			"override_collections": False,
		},
		redo_fields=(
			"limb_property_base_name",
			"tweak_relationship",
			"override_collections",
		),
	),
}


REDO_PROPERTIES = {
	"limb_property_base_name",
	"do_create_fk",
	"fk_bone_template",
	"skip_first_tweak",
	"fk_widget",
	"create_rotation_follow_setup",
	"rotation_follow_skip",
	"rotation_follow_relationship",
	"tweak_relationship",
	"add_rotation_isolation",
	"override_collections",
}


def get_fk_template(template_id: str) -> FKTemplate:
	try:
		return FK_TEMPLATES[template_id]
	except KeyError:
		raise ValueError(f"Unknown FK template: '{template_id}'") from None


def validate_fk_templates():
	option_fields = {field.name for field in fields(FKAssemblyOptions)}
	required_fields = {
		field.name
		for field in fields(FKAssemblyOptions)
		if field.default is MISSING and field.default_factory is MISSING
	} - {"limb_property_base_name"}
	managed_fields = {
		"fk_collection_name",
		"tweak_collection_name",
		"fk_bone_template",
	}

	for template_id, template in FK_TEMPLATES.items():
		option_names = set(template.options)
		missing = required_fields - option_names
		unknown = option_names - option_fields
		managed = option_names & managed_fields
		invalid_redo_fields = set(template.redo_fields) - REDO_PROPERTIES
		missing_redo_fields = set(template.redo_fields) - option_names - {"limb_property_base_name"}

		if missing:
			raise ValueError(f"FK template '{template_id}' is missing options: {sorted(missing)}")
		if unknown:
			raise ValueError(f"FK template '{template_id}' has unknown options: {sorted(unknown)}")
		if managed:
			raise ValueError(
				f"FK template '{template_id}' cannot directly set: {sorted(managed)}"
			)
		if invalid_redo_fields:
			raise ValueError(
				f"FK template '{template_id}' has unsupported redo fields: {sorted(invalid_redo_fields)}"
			)
		if missing_redo_fields:
			raise ValueError(
				f"FK template '{template_id}' has redo fields without template values: "
				f"{sorted(missing_redo_fields)}"
			)
		if template.options.get("create_rotation_follow_setup") and not template.options.get("do_create_fk"):
			raise ValueError(
				f"FK template '{template_id}' enables rotation follow without FK bones"
			)
		if template.options.get("add_rotation_isolation") and not template.options.get("do_create_fk"):
			raise ValueError(
				f"FK template '{template_id}' enables rotation isolation without FK bones"
			)


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

		if template.options.get("limb_property_base_name"):
			self.limb_property_base_name = template.options["limb_property_base_name"]
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
				setattr(self, property_name, template.options[property_name])

		return self.execute(context)

	def execute(self, context):
		try:
			template = get_fk_template(self.template_id)
		except ValueError as error:
			self.report({'ERROR'}, str(error))
			return {'CANCELLED'}

		option_values = dict(template.options)
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

		option_values.setdefault("fk_bone_template", get_preferences().fk_template)
		option_values.setdefault("fk_collection_name", "")
		option_values.setdefault("tweak_collection_name", "")

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
