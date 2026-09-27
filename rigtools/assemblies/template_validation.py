from dataclasses import MISSING, fields
from typing import Any, Callable, Mapping


def validate_assembly_templates(
	templates: Mapping[str, Any],
	options_class: type,
	*,
	kind: str,
	redo_properties: set[str],
	required_exclusions: set[str] | None = None,
	extra_check: Callable[[str, Any], None] | None = None,
):
	"""Shared structural checks for assembly template tables.

	Templates are expected to expose ``options`` (dict) and ``redo_fields`` (iterable).
	``options`` may be overrides only; missing keys use options-dataclass defaults at resolve time.
	``extra_check(template_id, template)`` can enforce family-specific rules.
	"""
	if required_exclusions is None:
		required_exclusions = {"limb_property_base_name"}

	option_fields = {field.name for field in fields(options_class)}
	required_fields = {
		field.name
		for field in fields(options_class)
		if field.default is MISSING and field.default_factory is MISSING
	} - required_exclusions

	for template_id, template in templates.items():
		option_names = set(template.options)
		missing = required_fields - option_names
		unknown = option_names - option_fields
		invalid_redo_fields = set(template.redo_fields) - redo_properties

		if missing:
			raise ValueError(f"{kind} template '{template_id}' is missing options: {sorted(missing)}")
		if unknown:
			raise ValueError(f"{kind} template '{template_id}' has unknown options: {sorted(unknown)}")
		if invalid_redo_fields:
			raise ValueError(
				f"{kind} template '{template_id}' has unsupported redo fields: {sorted(invalid_redo_fields)}"
			)

		if extra_check is not None:
			extra_check(template_id, template)
