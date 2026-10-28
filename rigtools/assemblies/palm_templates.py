from dataclasses import dataclass, field
from typing import Any

from rigtools.assemblies.palm_assembly import PalmAssemblyOptions
from rigtools.assemblies.template_validation import validate_assembly_templates

@dataclass(frozen=True)
class PalmTemplate:
	label: str
	description: str
	icon: str
	options: dict[str, Any]
	redo_fields: tuple[str, ...] = ()
	show_dialog: bool = False
	field_labels: dict[str, str] = field(default_factory=dict)


PALM_TEMPLATES = {
	"palm": PalmTemplate(
		label="Palm",
		description="Palm template - defaults designed for humanoids",
		icon="MESH_CAPSULE",
		options={
			"limb_property_base_name": "hand",
			"fk_widget": "PILL",
			"index_falloff_type": "SHARP",
			"pinky_falloff_type": "LINEAR",
		},
		redo_fields=(
			"fk_widget",
			"index_falloff_type",
			"pinky_falloff_type",
		),
		show_dialog=True,
	),
}


REDO_PROPERTIES = {
	"limb_property_base_name",
	"fk_widget",
	"index_falloff_type",
	"pinky_falloff_type",
}


def get_palm_template(template_id: str) -> PalmTemplate | None:
	return PALM_TEMPLATES.get(template_id)


def validate_palm_templates():
	validate_assembly_templates(
		PALM_TEMPLATES,
		PalmAssemblyOptions,
		kind="PALM",
		redo_properties=REDO_PROPERTIES,
	)
