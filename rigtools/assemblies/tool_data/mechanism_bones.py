from dataclasses import dataclass

@dataclass(frozen=True)
class MechanismBone:
	name: str
	roles: frozenset[str]

@dataclass
class BoneStyle:
	"""None = 'no change'"""
	widget: str | None = None
	color: str | None = None
	wire_width: float | None = None
	scale: tuple | None = None
	translation: tuple | None = None
	rotation: tuple | None = None
	transform_bone: str | None = None

	def set(self, **settings) -> "BoneStyle":
		for key, value in settings.items():
			if not hasattr(self, key):
				raise AttributeError(f"BoneStyle has no property '{key}'")
			setattr(self, key, value)
		return self

class MechanismBones:
	def __init__(self):
		self._items: list[MechanismBone] = []
		self.styles: dict[str, BoneStyle] = {}

	def __iter__(self):
		return iter(self._items)

	def add(self, name: str, role: str | list[str], *,
	    widget="", weight=1.0, scale=1.0
	):
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
		for name, style in mechanism_bones.styles.items():
			self.style(name, **{k:v for k,v in vars(style).items() if v is not None})
