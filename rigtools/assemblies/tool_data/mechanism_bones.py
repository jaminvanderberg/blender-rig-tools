from dataclasses import asdict, dataclass
import json

from rigtools.preferences import get_preferences
from rigtools.utils.bone_colors import get_bone_color
from rigtools.utils.widget import apply_widget

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
	translate: tuple | None = None
	rotate: tuple | None = None
	transform_bone: str | None = None

	def set(self, **settings) -> "BoneStyle":
		for key, value in settings.items():
			if not hasattr(self, key):
				raise AttributeError(f"BoneStyle has no property '{key}'")
			setattr(self, key, value)
		return self

	def apply(self, context, pose_bone, side, *, replace_widget=False):
		wgt = None
		if self.widget is not None:
			wgt = apply_widget(context, pose_bone, self.widget, replace=replace_widget) # 'NONE' -> no shape
		if self.scale is not None:
			pose_bone.custom_shape_scale_xyz = self.scale
		if self.translate is not None:
			pose_bone.custom_shape_translation = self.translate
		if self.rotate is not None:
			pose_bone.custom_shape_rotation_euler = self.rotate
		if self.transform_bone is not None:
			pose_bone.custom_shape_transform = pose_bone.id_data.pose.bones[self.transform_bone]
		if self.wire_width is not None:
			pose_bone.custom_shape_wire_width = self.wire_width

		if self.color is not None:
			prefs = get_preferences(context)
			pose_bone.color.palette = get_bone_color(prefs, self.color, side)

		return wgt

	def append(self, style: "BoneStyle"):
		self.set(**{k: v for k, v in asdict(style).items() if v is not None})

	def to_json(self):
		return json.dumps({k: v for k, v in asdict(self).items() if v is not None})	

	@classmethod
	def from_json(cls, text: str) -> "BoneStyle":
		return cls(**json.loads(text or "{}"))

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
