bl_info = {
    "name": "Rig Tools",
    "author": "Jamin VanderBerg",
    "version": (0, 61),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Tool > Rig Tools",
    "description": "Helper functions for rig building",
    "category": "Rigging"
}

import bpy

from rigtools import pair_bones
from rigtools import panel
from rigtools import fk_tweak_chain
from rigtools import selection_panel
from rigtools import batch_rename
from rigtools import create_mch_bones
from rigtools import create_rotation_isolation

classes = (
    panel.RIG_PT_tools_npanel,
    pair_bones.RIG_PG_def_result,
    pair_bones.RIG_UL_def_results,
    pair_bones.RIG_OT_pair_bones,
    fk_tweak_chain.RIG_OT_create_fk_tweak_chain,
    selection_panel.RIG_OT_select_bones_by_name,
    selection_panel.RIG_PT_selection_panel,
    batch_rename.RIG_OT_batch_rename_bones,
    create_mch_bones.RIG_OT_create_mch_bones,
    create_mch_bones.RIG_PT_create_mch_bones,
    create_rotation_isolation.RIG_OT_create_rotation_isolation,
)

addon_keymaps = []

def register():

    for cls in classes:
        bpy.utils.register_class(cls)

    # Scene properties
    bpy.types.Scene.mch_bone_name = bpy.props.StringProperty(
        name="Bone Name", 
        description="Template using {name} as a placeholder (e.g., 'MCH-{name}' or '{name}_MCH'). L/R suffixes will be preserved.",
        default="MCH-{name}"
    )

    # Keymaps
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        # Armature Edit keymap
        km = kc.keymaps.new(name='Armature', space_type='EMPTY')
        kmi = km.keymap_items.new(
            "rig.batch_rename_bones", 
            type='F2', 
            value='PRESS', 
            ctrl=True
        )
        addon_keymaps.append((km, kmi))

        # Pose mode keymap
        km_pose = kc.keymaps.new(name='Pose', space_type='EMPTY')
        kmi_pose = km_pose.keymap_items.new(
            "rig.batch_rename_bones", 
            type='F2', 
            value='PRESS', 
            ctrl=True
        )
        addon_keymaps.append((km_pose, kmi_pose))        

def unregister():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    del bpy.types.Scene.mch_bone_name
    del bpy.types.Scene.mch_scale_factor
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
