from bpy.types import PropertyGroup
from bpy.props import StringProperty, BoolProperty
from rigtools.preferences import get_preferences
from rigtools.rig_ui.collections_panel import rename_layout_collection
from rigtools.utils.bone_collection import ensure_bone_collection
from rigtools.utils.naming import name_collection, LIMB_COLLECTION_ROLES

def find_bones_by_limb_role(armature_data, limb, side, role):
	names = []
	for assembly in armature_data.rigtools_assemblies:
		options = assembly.get_options()
		if "limb_property_base_name" not in options:
			continue
		if options["limb_property_base_name"] == limb and assembly.side == side:
			names.extend(assembly.get_bones_by_role(role))
	return names

class LimbCollectionMap(PropertyGroup):
	limb: StringProperty()
	side: StringProperty()

	fk: StringProperty()
	ik: StringProperty()
	tweak: StringProperty()
	control: StringProperty()

	split: BoolProperty(
		name="FK/IK Split",
		description="True once this limb has both FK and IK/Torso collections",
		default=False,
	)

	def rename(self, role, new_name):
		old_name = getattr(self, role)
		if not new_name or new_name == old_name:
			return

		armature_data = self.id_data
		new_coll = ensure_bone_collection(armature_data, new_name)
		
		all_collections = getattr(armature_data, "collections_all", armature_data.collections)
		old_coll = all_collections.get(old_name)
		bones = armature_data.edit_bones if armature_data.is_editmode else armature_data.bones

		for name in find_bones_by_limb_role(armature_data, self.limb, self.side, role):
			bone = bones[name]
			if old_coll and old_coll.name in bone.collections:
				old_coll.unassign(bone)
			new_coll.assign(bone)

		setattr(self, role, new_name)

		if old_coll and old_coll != new_coll and not old_coll.bones:
			rename_layout_collection(armature_data, old_name, new_name)
			armature_data.collections.remove(old_coll)		

	def promote_fk(self):
		if self.split:
			return
		if self.fk == name_collection("fk", self.limb, self.side):
			self.rename("fk", name_collection("fk_split", self.limb, self.side))
		self.split = True

	def add_bone(self, armature_data, bone_name, roles: list[str]):
		bone = armature_data.bones[bone_name]

		for coll in list(bone.collections):
			coll.unassign(bone)

		for role in roles:
			if role == "mch":
				coll = ensure_bone_collection(armature_data, get_preferences().mch_collection_name, hidden=True)
			else:
				if not getattr(self, role):
					raise ValueError(f"Role {role} not found in {self.name}")
				coll = ensure_bone_collection(armature_data, getattr(self, role))
			coll.assign(bone)

def find_limb_collections(armature_data, limb, side):
	for row in armature_data.rigtools_limb_collections:
		if row.limb == limb and row.side == side:
			return row
	return None

def ensure_limb_collections(armature_data, limb, side, promote = False):
	row = find_limb_collections(armature_data, limb, side)
	if not row:
		row = armature_data.rigtools_limb_collections.add()
		row.limb = limb
		row.side = side

	if promote:
		if row.fk and not row.split:
			row.promote_fk()
		elif not row.fk:
			row.fk = name_collection("fk_split", limb, side)
			row.split = True
	elif not row.fk:
		row.fk = name_collection("fk", limb, side)

	if not row.ik:
		row.ik = name_collection("ik", limb, side)
	if not row.tweak:
		row.tweak = name_collection("tweak", limb, side)
	if not row.control:
		row.control = name_collection("control", limb, side)

	return row
