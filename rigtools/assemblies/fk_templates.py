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
	manual_display: bool = False


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
		},
		redo_fields=(
			"limb_property_base_name",
			"fk_widget",
			"normalize_fk_widget_scale",
			"taper_fk_widgets",
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
			"normalize_fk_widget_scale",
			"taper_fk_widgets",
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
			"master_controllers_type": "FK",
			"master_controllers_widget": "RECTANGLE",
			"tweak_relationship": "STRETCH_TO",
			"add_rotation_isolation": True,
			"add_skirt_collision": True,
			"add_skirt_ride": False,
			"normalize_fk_widget_scale": True,
		},
		redo_fields=(
			"fk_widget",
			"normalize_fk_widget_scale",
			"taper_fk_widgets",
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
			"normalize_fk_widget_scale": True,
			"taper_fk_widgets": True,
		},
		redo_fields=(
			"limb_property_base_name",
			"fk_widget",
			"normalize_fk_widget_scale",
			"taper_fk_widgets",
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
	"finger_curl": FKTemplate(
		label="Finger (Curl)",
		description="FK finger chain with curl controllers (Rigify style).",
		icon="VIEW_PAN",
		options={
			"limb_property_base_name": "hand",
			"control_mode": "FK/TWEAK",
			"skip_first_tweak": True,
			"fk_widget": "CIRCLE",
			"add_finger_curl": True,
			"finger_curl_axis": "AUTO",
			"tweak_relationship": "STRETCH_TO",
			"add_rotation_isolation": False,
			"normalize_fk_widget_scale": True,
			"taper_fk_widgets": True,
		},
		redo_fields=(
			"fk_widget",
			"skip_first_tweak",
			"tweak_relationship",
			"add_tweak_bones",
			"finger_curl_axis",
		),
	),
	"finger": FKTemplate(
		label="Finger (FK)",
		description="FK finger chain with master controller on second knuckle.",
		icon="VIEW_PAN",
		options={
			"limb_property_base_name": "hand",
			"control_mode": "FK/TWEAK",
			"skip_first_tweak": True,
			"fk_widget": "CIRCLE",
			"create_master_controllers": True,
			"master_controllers_interval": 0,
			"master_controllers_skip_first": True,
			"master_controllers_type": "FK",
			"tweak_relationship": "STRETCH_TO",
			"add_rotation_isolation": False,
			"normalize_fk_widget_scale": True,
			"taper_fk_widgets": True,
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
	"shoulder": FKTemplate(
		label="Shoulder",
		description="Humanoid shoulder. Single FK control..",
		icon="CON_GEOMETRYATTRIBUTE",
		options={
			"limb_property_base_name": "arm",
			"assembly_name_base": "shoulder",
			"create_shoulder_vis": True,
			"control_mode": "FK",
			"fk_widget": "SHOULDER",
			"share_fk_ik_role": True,
			"add_rotation_isolation": False,
		},
		redo_fields=(
			"fk_widget",
		),
		manual_display=True,
	),
}


REDO_PROPERTIES = {
	"limb_property_base_name",
	"skip_first_tweak",
	"fk_widget",
	"normalize_fk_widget_scale",
	"taper_fk_widgets",
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
	"add_finger_curl",
	"finger_curl_axis",
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
