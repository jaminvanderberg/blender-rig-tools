from dataclasses import MISSING, fields
from typing import Any, Mapping


def dataclass_option_defaults(options_class: type) -> dict[str, Any]:
	defaults = {}
	for field in fields(options_class):
		if field.default is not MISSING:
			defaults[field.name] = field.default
		elif field.default_factory is not MISSING:
			defaults[field.name] = field.default_factory()
	return defaults


def resolve_template_options(options_class: type, overrides: Mapping[str, Any]) -> dict[str, Any]:
	"""Merge options-dataclass defaults with template overrides.

	Template values win. Fields with no default must appear in ``overrides``
	(or be filled by the caller before constructing the options object).
	"""
	return {**dataclass_option_defaults(options_class), **dict(overrides)}
