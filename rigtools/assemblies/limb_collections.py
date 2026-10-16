from bpy.types import PropertyGroup
from bpy.props import StringProperty, BoolProperty
from rigtools.preferences import get_preferences
from rigtools.rig_ui.collections_panel import rename_layout_collection
from rigtools.utils.bone_collection import ensure_bone_collection
from rigtools.utils.naming import name_collection

class LimbCollectionMap(PropertyGroup):
    limb: StringProperty()
    side: StringProperty()

    fk: StringProperty()
    ik: StringProperty()
    tweak: StringProperty()
    mch: StringProperty()
    master: StringProperty()
    control: StringProperty()

    split: BoolProperty(
        name="FK/IK Split",
        description="True once this limb has both FK and IK/Torso collections",
        default=False,
    )

    def rename(self, role, new_name):
        old_name = getattr(self, role)
        actual = rename_collection(self.id_data, old_name, new_name)
        setattr(self, role, actual)
        return actual

    def promote_fk(self):
        if self.split:
            return
        self.rename("fk", name_collection("fk_split", self.limb, self.side))
        self.split = True

def find_limb_collections(arm, limb, side):
    for row in arm.rigtools_limb_collections:
        if row.limb == limb and row.side == side:
            return row
    return None

def ensure_limb_collections(arm, limb, side, promote = False):
    row = find_limb_collections(arm, limb, side)
    if not row:
        row = arm.rigtools_limb_collections.add()
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
    if not row.mch:
        row.mch = name_collection("mch", limb, side)
    if not row.master:
        row.master = name_collection("fk_master", limb, side)
    if not row.control:
        row.control = name_collection("control", limb, side)

    # This makes sure the MCH is properly parented
    ensure_bone_collection(arm, row.mch, get_preferences().mch_parent_collection)

    return row


def rename_collection(armature_data, old_name, new_name):
    if not old_name or old_name == new_name:
        return new_name
    
    all_collections = getattr(armature_data, "collections_all", armature_data.collections)
    coll = all_collections.get(old_name)
    if not coll:
        return new_name
    
    new_coll = all_collections.get(new_name)
    if new_coll:
        if armature_data.is_editmode:
            bones = [b for b in armature_data.edit_bones if coll in b.collections]
        else:
            bones = list(coll.bones)

        for bone in bones:
            new_coll.assign(bone)
            coll.unassign(bone)
        actual = new_name
    else:
        coll.name = new_name
        actual = coll.name
        rename_layout_collection(armature_data, old_name, coll.name)

    return actual