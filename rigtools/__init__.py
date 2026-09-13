bl_info = {
	"name": "Rig Tools",
	"author": "Jamin VanderBerg",
	"version": (0, 79),
	"blender": (4, 0, 0),
	"location": "View3D > Sidebar > Rig Tools",
	"description": "Helper functions for rig building",
	"category": "Rigging"
}

import bpy

from rigtools import generate_org_bones
from rigtools import panel
from rigtools import fk_tweak_chain
from rigtools import selection_panel
from rigtools import batch_rename
from rigtools import create_mch_bones
from rigtools import create_rotation_isolation
from rigtools import preferences
from rigtools import preferences_io
from rigtools import armature_settings
from rigtools import create_fk_ik_switch

classes = (
	preferences.RigToolsPreferences,
	preferences_io.RIG_OT_export_preferences,
	preferences_io.RIG_OT_import_preferences,
	panel.RIG_PT_tools_npanel,
	generate_org_bones.RIG_OT_generate_org_bones,
	fk_tweak_chain.RIG_OT_create_fk_tweak_chain,
	batch_rename.RIG_OT_batch_rename_bones,
	create_mch_bones.RIG_OT_create_mch_bones,
	create_mch_bones.RIG_PT_create_mch_bones,
	create_rotation_isolation.RIG_OT_create_rotation_isolation,
)

addon_keymaps = []

def register():

	armature_settings.register()
	selection_panel.register()
	create_fk_ik_switch.register()

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
	
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)

	selection_panel.unregister()
	armature_settings.unregister()
	create_fk_ik_switch.unregister()

if __name__ == "__main__":
	register()
