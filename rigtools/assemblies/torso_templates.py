from dataclasses import dataclass
from typing import Any

from rigtools.assemblies.template_validation import validate_assembly_templates
from rigtools.assemblies.torso_assembly import TorsoAssemblyOptions

@dataclass(frozen=True)
class TorsoTemplate:
	label: str
	description: str
	icon: str
	options: dict[str, Any]
	redo_fields: tuple[str, ...] = ()
	show_dialog: bool = False


TORSO_TEMPLATES = {
	"torso": TorsoTemplate(
		label="Torso",
		description="Torso template - defaults designed for humanoids",
		icon="HUMANOID",
		options={
			"limb_property_base_name": "torso",
			"lower_torso_bone_count": 2,
			"neck_bone_count": 1,
			"add_neck_rotation_isolation": True,
			"add_head_rotation_isolation": True,
			"neck_base_property_name": "neck",
			"neck_inherit_scale_from_root": True,
			"head_base_property_name": "head",
			"head_inherit_scale_from_root": True,
			"fk_widget": "CIRCLE",
			"override_collections": True,
			"use_twist_bones": True,
			"tweak_relationship": "STRETCH_TO",
			"add_tweak_bones": True,
		},
		redo_fields=(
			"lower_torso_bone_count",
			"neck_bone_count",
			"use_twist_bones",
			"neck_twist_bone_count",
			"chest_twist_bone_count",
		),
	),
}


REDO_PROPERTIES = {
	"limb_property_base_name",
	"lower_torso_bone_count",
	"neck_bone_count",
	"use_twist_bones",
	"neck_twist_bone_count",
	"chest_twist_bone_count",
	"add_tweak_bones",
	"tweak_relationship",
	"add_neck_rotation_isolation",
	"add_head_rotation_isolation",
	"neck_base_property_name",
	"neck_inherit_scale_from_root",
	"head_base_property_name",
	"head_inherit_scale_from_root",
	"fk_widget",
	"override_collections",
}


def get_torso_template(template_id: str) -> TorsoTemplate | None:
	return TORSO_TEMPLATES.get(template_id)


def validate_torso_templates():
	validate_assembly_templates(
		TORSO_TEMPLATES,
		TorsoAssemblyOptions,
		kind="TORSO",
		redo_properties=REDO_PROPERTIES,
	)
