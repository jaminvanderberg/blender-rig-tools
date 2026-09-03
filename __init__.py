bl_info = {
    "name": "Rig Tools",
    "author": "Jamin VanderBerg",
    "version": (1, 2),
    "blender": (2, 93, 0),
    "location": "View3D > Sidebar > Rig Tools",
    "description": "Helper functions for rig building",
    "category": "Rigging"
}

import bpy

def register():
    from . import eye_targets
    from . import def_constraints
    from . import panel
    from . import weightpaint
    from . import posemode
    from . import bone_collections

    global classes
    classes = (
        panel.RIG_PT_tools_npanel,
        eye_targets.EYE_OT_add_targets,
        def_constraints.RIG_OT_setup_def_constraints,
        weightpaint.RIG_OT_switch_to_weight_paint,
        posemode.RIG_OT_switch_back_to_pose,
        bone_collections.RIG_OT_toggle_bone_collection,
        bone_collections.RIG_OT_solo_bone_collection,
        bone_collections.RIG_OT_show_all_bone_collections,
        bone_collections.RIG_PT_bone_collections_panel,
    )

    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
