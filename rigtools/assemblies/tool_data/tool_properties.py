from dataclasses import dataclass
from rna_prop_ui import rna_idprop_ui_create

@dataclass(frozen=True)
class ToolProperty:
	name: str
	role: str
	qualifier: str = "" # Used when same role is used more than once per assembly (i.e. neck, head)

	def apply(self, prop_bone, *, default=1.0, min=0.0, max=1.0, items=None):
		current = prop_bone.get(self.name)
		rna_idprop_ui_create(prop_bone, self.name, default=default, min=min, max=max, items=items, overridable=True)
		if current is not None and (not items or current < len(items)):
			prop_bone[self.name] = current

class ToolProperties:
	def __init__(self):
		self._items: list[ToolProperty] = []

	def __iter__(self):
		return iter(self._items)

	def add(self, name: str, role: str, qualifier: str = ""):
		"""Add a tool property. Qualifier is used when same role is used more than once per assembly (i.e. neck, head)"""
		prop = ToolProperty(name, role, qualifier)
		self._items.append(prop)
		return prop

	def append(self, tool_properties: "ToolProperties"):
		self._items.extend(tool_properties._items)
