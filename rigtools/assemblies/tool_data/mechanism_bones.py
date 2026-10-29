from dataclasses import dataclass

from rigtools.assemblies.tool_data.bone_style import BoneStyle

@dataclass(frozen=True)
class MechanismBone:
	name: str
	roles: frozenset[str]

class MechanismBones:
	def __init__(self):
		self._items: list[MechanismBone] = []
		self.styles: dict[str, BoneStyle] = {}

	def __iter__(self):
		return iter(self._items)

	def add(self, name: str, role: str | list[str]):
		roles = frozenset(role) if isinstance(role, list) else frozenset([role])
		self._items.append(MechanismBone(name, roles))
		return self.style(name)

	def style(self, name: str, **settings) -> BoneStyle:
		return self.styles.setdefault(name, BoneStyle()).set(**settings)

	def extend(self, bone_names: list[str], role: str | list[str]):
		for name in bone_names:
			if name:
				self.add(name, role)

	def append(self, mechanism_bones: "MechanismBones"):
		self._items.extend(mechanism_bones._items)
		for name, style in mechanism_bones.styles.items():\
			self.style(name).append(style)
