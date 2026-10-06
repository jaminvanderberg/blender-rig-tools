from dataclasses import dataclass, field
from typing import Any

from rigtools.armature_settings import get_armature_settings
from rigtools.assemblies.ik_assembly import IKAssemblyOptions
from rigtools.assemblies.template_options import resolve_template_options
from rigtools.assemblies.template_validation import validate_assembly_templates
from rigtools.tool.ik_parent import IKParentTarget
from rigtools.tool.twist_bones import TwistSegment, FALLOFF, twist_source_types


@dataclass(frozen=True)
class IKTemplate:
	label: str
	description: str
	icon: str
	options: dict[str, Any]
	redo_fields: tuple[str, ...] = ()
	field_labels: dict[str, str] = field(default_factory=dict)
	show_dialog: bool = False


IK_TEMPLATES = {
	"arm": IKTemplate(
		label="Arm",
		description="Humanoid arm. Works best with 3 bones.",
		icon="CON_CHILDOF",
		options={
			"limb_property_base_name": "arm",
			"add_tweak_bones": True,
			"switch_property_type": "ENUM",
			"ik_bone_count": 3,
			"add_rotation_isolation": True,
			"inherit_scale_from_root": True,
			"override_collections": True,
			"ik_type": "IK",
			"enable_ik_stretch": True,
			"pole_distance": 0.25,
			"tweak_relationship": "STRETCH_TO",
			"fk_widget": "FK",
			"tip_widget": "CIRCLE",
			"fk_end_widget": "CIRCLE",
			"enable_snapping": True,
			"ik_parent": True,
			"ik_parents": ("root", "torso", "hips", "chest", "head"),
			"use_twist_bones": True,
			"twist_segments": (
				{"name": "Arm", "index": 0, "source": "SELF", "falloff": "ROOT"},
				{"name": "Forearm", "index": 1, "source": "CHILD", "falloff": "LINEAR"},
			),
			"twist_bone_count": 4,
		},
		redo_fields=(
			"add_tweak_bones",
			"tweak_relationship",
			"switch_property_type",
			"fk_widget",
			"fk_end_widget",
			"enable_ik_stretch",
			"ik_bone_count",
			"add_rotation_isolation",
			"inherit_scale_from_root",
			"use_twist_bones",
			"twist_bone_count",
			"twist_segments",
			"fk_end_widget",
		),
		field_labels={
			"fk_end_widget": "Hand FK Widget:",
		},
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
			"inherit_scale_from_root": False,
			"override_collections": True,
			"ik_type": "IK",
			"ik_bone_count": 3,
			"enable_ik_stretch": True,
			"pole_distance": 0.5,
			"tweak_relationship": "STRETCH_TO",
			"fk_widget": "FK",
			"tip_widget": "CIRCLE",
			"fk_end_widget": "CIRCLE",
			"enable_snapping": True,
			"ik_parent": True,
			"ik_parents": ("root", "torso", "self"),
			"ik_parent_self_parent_label": "Foot",
			"use_twist_bones": True,
			"twist_segments": (
				{"name": "Thigh", "index": 0, "source": "SELF", "falloff": "SHARP"},
				{"name": "Shin", "index": 1, "source": "NONE", "falloff": "LINEAR"},
			),
			"twist_bone_count": 4,
			"add_foot_roll": True,
		},
		redo_fields=(
			"add_tweak_bones",
			"tweak_relationship",
			"switch_property_type",
			"fk_widget",
			"enable_ik_stretch",
			"ik_bone_count",
			"use_twist_bones",
			"twist_bone_count",
			"twist_segments",
			"add_foot_roll",
			"tip_widget",
			"fk_end_widget",
		),
		field_labels={
			"tip_widget": "Toe Widget:",
			"fk_end_widget": "Foot FK Widget:",
		},
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
			"ik_parents",
		),
		show_dialog=False,
	),
}


IK_PARENT_SETTINGS = {
	"root": ("Root", "root_bone_name"),
	"torso": ("Torso", "torso_bone_name"),
	"hips": ("Hips", "hips_bone_name"),
	"chest": ("Chest", "chest_bone_name"),
	"head": ("Head", "head_bone_name"),
}

# Fields the template redo panel / operator may expose.
REDO_PROPERTIES = {
	"limb_property_base_name",
	"add_tweak_bones",
	"switch_property_type",
	"add_rotation_isolation",
	"inherit_scale_from_root",
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
	"ik_parents",
	"use_twist_bones",
	"twist_bone_count",
	"twist_segments",
	"add_foot_roll",
	"ik_bone_count",
	"tip_widget",
	"fk_end_widget",
}


def get_ik_template(template_id: str) -> IKTemplate | None:
	return IK_TEMPLATES.get(template_id)


_VALID_TWIST_SOURCES = {item[0] for item in twist_source_types}
_VALID_TWIST_FALLOFFS = set(FALLOFF)


def resolve_twist_segments(raw_segments) -> list[TwistSegment]:
	"""Convert template/JSON segment dicts into TwistSegment values."""
	segments = []
	for entry in raw_segments or []:
		if isinstance(entry, TwistSegment):
			segments.append(entry)
			continue
		segments.append(
			TwistSegment(
				index=int(entry["index"]),
				source=entry["source"],
				falloff=entry.get("falloff", "LINEAR"),
				name=entry.get("name", ""),
			)
		)
	return segments


def _validate_ik_template_rules(template_id: str, template: IKTemplate):
	options = resolve_template_options(IKAssemblyOptions, template.options)
	valid_parent_names = set(IK_PARENT_SETTINGS) | {"self"}
	parent_names = options["ik_parents"]
	if not isinstance(parent_names, (tuple, list)) or not all(
		isinstance(parent_name, str) for parent_name in parent_names
	):
		raise ValueError(f"IK template '{template_id}' parents must be a list of special names")

	invalid_parent_names = set(parent_names) - valid_parent_names
	if invalid_parent_names:
		raise ValueError(
			f"IK template '{template_id}' has unknown IK parents: {sorted(invalid_parent_names)}"
		)
	if options["ik_parent"] and not parent_names:
		raise ValueError(f"IK template '{template_id}' enables IK parents without defining any")
	if "self" in parent_names and options["ik_type"] != "IK":
		raise ValueError(f"IK template '{template_id}' can only use the self parent with standard IK")

	if options["use_twist_bones"]:
		if options["ik_type"] != "IK":
			raise ValueError(f"IK template '{template_id}' can only use twist bones with standard IK")
		if options["twist_bone_count"] < 2:
			raise ValueError(f"IK template '{template_id}' twist_bone_count must be >= 2")
		segments = resolve_twist_segments(options["twist_segments"])
		if not segments:
			raise ValueError(f"IK template '{template_id}' enables twist bones without segments")
		indexes = [segment.index for segment in segments]
		if len(indexes) != len(set(indexes)):
			raise ValueError(f"IK template '{template_id}' twist segment indexes must be unique")
		for segment in segments:
			if segment.source not in _VALID_TWIST_SOURCES:
				raise ValueError(
					f"IK template '{template_id}' has unknown twist source '{segment.source}'"
				)
			if segment.falloff not in _VALID_TWIST_FALLOFFS:
				raise ValueError(
					f"IK template '{template_id}' has unknown twist falloff '{segment.falloff}'"
				)


def validate_ik_templates():
	validate_assembly_templates(
		IK_TEMPLATES,
		IKAssemblyOptions,
		kind="IK",
		redo_properties=REDO_PROPERTIES,
		extra_check=_validate_ik_template_rules,
	)


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
