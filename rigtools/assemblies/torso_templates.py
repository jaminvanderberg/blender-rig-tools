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
	"add_chest_rotation_isolation",
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
