bl_info = {
    "name": "Rig Tools",
    "author": "Jamin VanderBerg",
    "version": (1, 2),
    "blender": (2, 93, 0),
    "location": "View3D > Sidebar > Tool > Rig Tools",
    "description": "Helper functions for rig building",
    "category": "Rigging"
}

import bpy

from . import pair_bones
from . import panel
from . import fk_tweak_chain
from . import selection_panel
from . import batch_rename

classes = (
    panel.RIG_PT_tools_npanel,
    pair_bones.RIG_PG_def_result,
    pair_bones.RIG_UL_def_results,
    pair_bones.RIG_OT_pair_bones,
    fk_tweak_chain.RIG_OT_create_fk_tweak_chain,
    selection_panel.RIG_OT_select_bones_by_name,
    selection_panel.RIG_PT_selection_panel,
    batch_rename.RIG_OT_batch_rename_bones,
)

addon_keymaps = []

def register():

    for cls in classes:
        bpy.utils.register_class(cls)

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        # Target the Armature keymap container (active in Edit and Pose modes)
        km = kc.keymaps.new(name='Armature', space_type='EMPTY')
        kmi = km.keymap_items.new(
            "rig.batch_rename_bones", 
            type='F2', 
            value='PRESS', 
            ctrl=True
        )
        addon_keymaps.append((km, kmi))

def unregister():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
