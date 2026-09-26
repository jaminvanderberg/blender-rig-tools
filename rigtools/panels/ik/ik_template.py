from dataclasses import MISSING, dataclass, fields
from typing import Any

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, StringProperty

from rigtools.armature_settings import get_armature_settings
from rigtools.assemblies.ik_assembly import IKAssemblyOptions, create_ik_assembly
from rigtools.rig_ui.property_name import guess_limb_name
from rigtools.tool.ik_parent import IKParentTarget
from rigtools.tool.spline_ik import spline_twist_type
from rigtools.utils.bone_chain import (
	ChainBranchingError,
	find_chains_from_selection,
	get_assembly_chains,
)
from rigtools.utils.widget import fk_widget_types


@dataclass(frozen=True)
class IKTemplate:
	label: str
	description: str
	icon: str
	options: dict[str, Any]
	redo_fields: tuple[str, ...] = ()


IK_TEMPLATES = {
	"arm": IKTemplate(
		label="Arm",
		description="Humanoid arm. Works best with 3 bones.",
		icon="CON_CHILDOF",
		options={
			"limb_property_base_name": "arm",
			"add_tweak_bones": True,
			"switch_property_type": "ENUM",
			"add_rotation_isolation": True,
			"override_collections": True,
			"ik_type": "IK",
			"enable_ik_stretch": True,
			"pole_distance": 0.5,
			"tweak_relationship": "STRETCH_TO",
			"fk_widget": "FK",
			"enable_snapping": True,
			"ik_parent": True,
			"ik_parents": ("root", "torso", "hips", "chest", "head"),
		},
		redo_fields=(
			"add_tweak_bones",
			"tweak_relationship",
			"switch_property_type",
			"fk_widget",
			"enable_ik_stretch",
		),
	),
	"leg": IKTemplate(
		label="Leg",
		description="Humanoid leg. Works best with 3 bones.",
		icon="CON_KINEMATIC",
		options={
			"limb_property_base_name": "leg",
			"add_tweak_bones": True,
			"switch_property_type": "ENUM",
			"add_rotation_isolation": True,
			"override_collections": True,
			"ik_type": "IK",
			"enable_ik_stretch": True,
			"pole_distance": 0.5,
			"tweak_relationship": "STRETCH_TO",
			"fk_widget": "FK",
			"enable_snapping": True,
			"ik_parent": True,
			"ik_parents": ("root", "torso", "self"),
			"ik_parent_self_parent_label": "Foot",
		},
		redo_fields=(
			"add_tweak_bones",
			"tweak_relationship",
			"switch_property_type",
			"fk_widget",
			"enable_ik_stretch",
		),
	),
	"skirt.spline": IKTemplate(
		label="Skirt - Spline",
		description="Long skirt with a spline IK setup.",
		icon="CURVE_DATA",
		options={
			"limb_property_base_name": "",
			"add_tweak_bones": True,
			"switch_property_type": "ENUM",
			"add_rotation_isolation": True,
			"override_collections": True,
			"ik_parent": True,
			"ik_parents": ("root", "torso"),
			"ik_type": "SPLINE",
			"spline_control_count": 3,
			"spline_skip_first": True,
			"twist_type": "START_END",
			"tweak_relationship": "STRETCH_TO",
			"fk_widget": "RECTANGLE",
			"enable_snapping": False,
		},
		redo_fields=(
			"limb_property_base_name",
			"switch_property_type",
			"fk_widget",
			"add_rotation_isolation",
			"spline_control_count",
			"spline_skip_first",
			"twist_type",
			"ik_parent",
			"enable_snapping"
		),
	)
}



IK_PARENT_SETTINGS = {
	"root": ("Root", "root_bone_name"),
	"torso": ("Torso", "torso_bone_name"),
	"hips": ("Hips", "hips_bone_name"),
	"chest": ("Chest", "chest_bone_name"),
	"head": ("Head", "head_bone_name"),
}

REDO_PROPERTIES = {
	"limb_property_base_name",
	"add_tweak_bones",
	"switch_property_type",
	"add_rotation_isolation",
	"override_collections",
	"ik_type",
	"enable_ik_stretch",
	"pole_distance",
	"spline_control_count",
	"spline_skip_first",
	"twist_type",
	"tweak_relationship",
	"fk_widget",
	"enable_snapping",
	"ik_parent",
}


def get_ik_template(template_id: str) -> IKTemplate:
	try:
		return IK_TEMPLATES[template_id]
	except KeyError:
		raise ValueError(f"Unknown IK template: '{template_id}'") from None


def validate_ik_templates():
	option_fields = {field.name for field in fields(IKAssemblyOptions)}
	required_fields = {
		field.name
		for field in fields(IKAssemblyOptions)
		if field.default is MISSING and field.default_factory is MISSING
	} - {"limb_property_base_name"}
	managed_fields = {
		"add_ik_control_as_pole_parent",
	}
	valid_parent_names = set(IK_PARENT_SETTINGS) | {"self"}

	for template_id, template in IK_TEMPLATES.items():
		option_names = set(template.options)
		missing = required_fields - option_names
		unknown = option_names - option_fields
		managed = option_names & managed_fields
		invalid_redo_fields = set(template.redo_fields) - REDO_PROPERTIES
		missing_redo_fields = set(template.redo_fields) - option_names - {"limb_property_base_name"}
		parent_names = template.options.get("ik_parents", ())
		if not isinstance(parent_names, (tuple, list)) or not all(
			isinstance(parent_name, str) for parent_name in parent_names
		):
			raise ValueError(f"IK template '{template_id}' parents must be a list of special names")
		invalid_parent_names = set(parent_names) - valid_parent_names

		if missing:
			raise ValueError(f"IK template '{template_id}' is missing options: {sorted(missing)}")
		if unknown:
			raise ValueError(f"IK template '{template_id}' has unknown options: {sorted(unknown)}")
		if managed:
			raise ValueError(
				f"IK template '{template_id}' cannot directly set parent options: {sorted(managed)}"
			)
		if invalid_redo_fields:
			raise ValueError(
				f"IK template '{template_id}' has unsupported redo fields: {sorted(invalid_redo_fields)}"
			)
		if missing_redo_fields:
			raise ValueError(
				f"IK template '{template_id}' has redo fields without template values: "
				f"{sorted(missing_redo_fields)}"
			)
		if invalid_parent_names:
			raise ValueError(
				f"IK template '{template_id}' has unknown IK parents: {sorted(invalid_parent_names)}"
			)
		if template.options.get("ik_parent", True) and not parent_names:
			raise ValueError(f"IK template '{template_id}' enables IK parents without defining any")
		if not template.options.get("ik_parent", True) and parent_names:
			raise ValueError(f"IK template '{template_id}' defines IK parents while they are disabled")
		if "self" in parent_names and template.options.get("ik_type", "IK") != "IK":
			raise ValueError(f"IK template '{template_id}' can only use the self parent with standard IK")


def resolve_ik_parents(context, parent_names):
	if len(parent_names) != len(set(parent_names)):
		raise ValueError("IK template parent names must be unique.")

	settings = get_armature_settings(context.object.data, context)
	parents = []

	for parent_name in parent_names:
		if parent_name == "self":
			continue

		label, setting_name = IK_PARENT_SETTINGS[parent_name]
		bone_name = getattr(settings, setting_name)
		if not bone_name:
			raise ValueError(f"{label} bone is not configured in the armature settings.")
		if bone_name not in context.object.data.bones:
			raise ValueError(f"{label} bone '{bone_name}' was not found.")

		parents.append(IKParentTarget(label=label, bone=bone_name))

	return parents, "self" in parent_names


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

		if "limb_property_base_name" in template.options and template.options["limb_property_base_name"]:
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
			template = get_ik_template(self.template_id)
		except ValueError as error:
			self.report({'ERROR'}, str(error))
			return {'CANCELLED'}

		option_values = dict(template.options)
		if "limb_property_base_name" not in option_values:
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
			option_values["ik_parent_self_parent_label"] = "Self"
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
			create_ik_assembly(context, chains, options)
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
