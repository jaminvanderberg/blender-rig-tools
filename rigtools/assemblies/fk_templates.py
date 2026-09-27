from dataclasses import dataclass
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


# Fields the template redo panel / operator may expose.
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
	validate_assembly_templates(
		FK_TEMPLATES,
		FKAssemblyOptions,
		kind="FK",
		redo_properties=REDO_PROPERTIES,
	)
