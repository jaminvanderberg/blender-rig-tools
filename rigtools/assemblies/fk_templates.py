from dataclasses import dataclass, field
from typing import Any

from rigtools.assemblies.fk_assembly import FKAssemblyOptions
from rigtools.assemblies.template_validation import validate_assembly_templates


@dataclass(frozen=True)
class FKTemplate:
	label: str
	description: str
	icon: str
	options: dict[str, Any]
	redo_fields: tuple[str, ...] = ()
	show_dialog: bool = False
	field_labels: dict[str, str] = field(default_factory=dict)


FK_TEMPLATES = {
	"simple": FKTemplate(
		label="Simple FK",
		description="Simple FK with rotation follow along the chain.",
		icon="BONE_DATA",
		options={
			"limb_property_base_name": "",
			"control_mode": "FK/TWEAK",
			"skip_first_tweak": False,
			"fk_widget": "CIRCLE",
			"create_master_controllers": True,
			"master_controllers_skip_first": True,
			"master_controllers_type": "FK",
			"tweak_relationship": "STRETCH_TO",
			"add_rotation_isolation": False,
			"override_collections": True,
		},
		redo_fields=(
			"limb_property_base_name",
			"fk_widget",
			"skip_first_tweak",
			"add_rotation_isolation",
			"create_master_controllers",
			"master_controllers_skip_first",
			"add_tweak_bones",
		),
	),
	"fk_only": FKTemplate(
		label="FK Only",
		description="FK only chain. No tweaks.",
		icon="RESTRICT_SELECT_OFF",
		options={
			"limb_property_base_name": "",
			"control_mode": "FK",
			"fk_widget": "CIRCLE",
			"create_master_controllers": True,
			"master_controllers_interval": 0,
			"master_controllers_skip_first": True,
			"master_controllers_type": "FK",
			"add_rotation_isolation": False,
		},
		redo_fields=(
			"limb_property_base_name",
			"fk_widget",
			"create_master_controllers",
			"master_controllers_skip_first",
		),
	),
	"skirt": FKTemplate(
		label="Skirt FK",
		description="FK skirt with rotation follow along the chain.",
		icon="CON_GEOMETRYATTRIBUTE",
		options={
			"limb_property_base_name": "",
			"control_mode": "FK/TWEAK",
			"skip_first_tweak": False,
			"fk_widget": "RECTANGLE",
			"create_master_controllers": True,
			"master_controllers_interval": 0,
			"master_controllers_skip_first": True,
			"master_controllers_type": "MASTER",
			"master_controllers_widget": "RECTANGLE",
			"tweak_relationship": "STRETCH_TO",
			"add_rotation_isolation": True,
			"add_skirt_collision": True,
			"add_skirt_ride": False,
		},
		redo_fields=(
			"fk_widget",
			"skip_first_tweak",
			"tweak_relationship",
			"add_rotation_isolation",
			"create_master_controllers",
			"master_controllers_interval",
			"master_controllers_skip_first",
			"master_controllers_type",
			"master_controllers_widget",
			"add_tweak_bones",
			"add_skirt_collision",
			"add_skirt_ride",
			"skirt_legs",
		),
	),
	"tail": FKTemplate(
		label="Tail",
		description="FK tail with rotation follow along the chain.",
		icon="CURVE_PATH",
		options={
			"limb_property_base_name": "tail",
			"control_mode": "FK/TWEAK",
			"skip_first_tweak": False,
			"fk_widget": "CIRCLE",
			"create_master_controllers": True,
			"master_controllers_interval": 3,
			"master_controllers_skip_first": True,
			"master_controllers_type": "MASTER",
			"master_controllers_widget": "CIRCLE",
			"tweak_relationship": "STRETCH_TO",
			"add_rotation_isolation": True,
		},
		redo_fields=(
			"fk_widget",
			"skip_first_tweak",
			"tweak_relationship",
			"add_rotation_isolation",
			"create_master_controllers",
			"master_controllers_interval",
			"master_controllers_skip_first",
			"master_controllers_type",
			"master_controllers_widget",
			"add_tweak_bones",
		),
	),
	"finger": FKTemplate(
		label="Finger",
		description="Compact FK finger chain. Skips the first tweak.",
		icon="VIEW_PAN",
		options={
			"limb_property_base_name": "finger",
			"control_mode": "FK/TWEAK",
			"skip_first_tweak": True,
			"fk_widget": "CIRCLE",
			"create_master_controllers": True,
			"master_controllers_interval": 0,
			"master_controllers_skip_first": True,
			"master_controllers_type": "FK",
			"tweak_relationship": "STRETCH_TO",
			"add_rotation_isolation": False,
		},
		redo_fields=(
			"fk_widget",
			"skip_first_tweak",
			"tweak_relationship",
			"add_tweak_bones",
			"create_master_controllers",
			"master_controllers_type",
			"master_controllers_skip_first",
		),
	),
	"tweak": FKTemplate(
		label="Tweak Only",
		description="Tweak bones parented in a chain, without FK controls.",
		icon="PARTICLE_POINT",
		options={
			"limb_property_base_name": "",
			"control_mode": "TWEAK",
			"skip_first_tweak": False,
			"fk_widget": "NONE",
			"create_master_controllers": False,
			"tweak_relationship": "STRETCH_TO",
			"add_rotation_isolation": False,
		},
		redo_fields=(
			"limb_property_base_name",
			"tweak_relationship",
		),
	),
}


REDO_PROPERTIES = {
	"limb_property_base_name",
	"skip_first_tweak",
	"fk_widget",
	"create_master_controllers",
	"master_controllers_interval",
	"master_controllers_skip_first",
	"master_controllers_type",
	"master_controllers_widget",
	"tweak_relationship",
	"add_rotation_isolation",
	"control_mode",
	"add_tweak_bones",
	"add_skirt_collision",
	"add_skirt_ride",
	"skirt_legs",
}


def get_fk_template(template_id: str) -> FKTemplate | None:
	return FK_TEMPLATES.get(template_id)


def validate_fk_templates():
	validate_assembly_templates(
		FK_TEMPLATES,
		FKAssemblyOptions,
		kind="FK",
		redo_properties=REDO_PROPERTIES,
	)
