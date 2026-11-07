bl_info = {
	"name": "RigTools",
	"author": "Jamin VanderBerg",
	"version": (0, 9, 0),
	"blender": (4, 1, 0),
	"location": "View3D > Sidebar > Rig Tools",
	"description": "Helper functions for rig building",
	"category": "Rigging"
}

import bpy

from rigtools.operators import generate_org_bones
from rigtools.panels.main import main_panel
from rigtools.panels.armature import armature_panel
from rigtools import preferences
from rigtools import preferences_io
from rigtools import armature_settings
from rigtools.operators import migrate_rig
from rigtools.rig_data import twist_chain
from rigtools.operators import rename_chain
from rigtools.operators import parent_along_chain
from rigtools.operators import weight_paint_proxy
from rigtools.operators import root_widget
from rigtools.operators import human_skeleton
from rigtools.operators import create_twist_bones
from rigtools.operators import bone_colors
from rigtools.operators import corrective_bones
from rigtools.operators import connect_shape_key
from rigtools.assemblies import assembly_data
from rigtools.assemblies import config_registry
from rigtools.panels import skirt_legs as skirt_legs_panel
from rigtools.panels.ik import ik_panel
from rigtools.panels.fk import fk_panel
from rigtools.panels.assembly import assembly_panel
from rigtools.panels.bone_style import bone_style_panel
from rigtools.panels.shape_keys import shape_keys_panel
from rigtools.data_viewer import panel as data_viewer_panel
from rigtools.rig_ui import collections_panel
from rigtools.rig_ui import snapping_data
from rigtools.rig_ui import rig_ui
from rigtools.rig_ui import embed_ui

classes = (
	preferences.RigToolsPreferences,
	preferences_io.RIG_OT_export_preferences,
	preferences_io.RIG_OT_import_preferences,
	main_panel.RIG_PT_tools_npanel,
	generate_org_bones.RIG_OT_generate_org_bones,
	parent_along_chain.RIG_OT_parent_along_chain,
)

def register():
	if rig_ui.RIG_DATA_VERSION != armature_settings.CURRENT_RIG_DATA_VERSION:
		raise RuntimeError(
			f"rig_ui.RIG_DATA_VERSION ({rig_ui.RIG_DATA_VERSION}) must match "
			f"CURRENT_RIG_DATA_VERSION ({armature_settings.CURRENT_RIG_DATA_VERSION})"
		)

	# Registered first so the Armature panel sits at the top of the tab
	armature_panel.register()
	armature_settings.register()
	migrate_rig.register()
	twist_chain.register()

	assembly_data.register()
	config_registry.register()
	skirt_legs_panel.register()
	ik_panel.register()
	fk_panel.register()
	assembly_panel.register()
	data_viewer_panel.register()

	rename_chain.register()
	weight_paint_proxy.register()
	root_widget.register()
	human_skeleton.register()
	create_twist_bones.register()
	bone_colors.register()
	corrective_bones.register()
	connect_shape_key.register()
	bone_style_panel.register()
	shape_keys_panel.register()

	snapping_data.register()
	rig_ui.register()
	collections_panel.register()
	embed_ui.register()

	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)

	embed_ui.unregister()
	collections_panel.unregister()
	rig_ui.unregister()
	snapping_data.unregister()

	shape_keys_panel.unregister()
	bone_style_panel.unregister()
	connect_shape_key.unregister()
	corrective_bones.unregister()
	bone_colors.unregister()
	create_twist_bones.unregister()
	human_skeleton.unregister()
	root_widget.unregister()
	weight_paint_proxy.unregister()
	rename_chain.unregister()
	twist_chain.unregister()

	data_viewer_panel.unregister()
	assembly_panel.unregister()
	ik_panel.unregister()
	fk_panel.unregister()
	skirt_legs_panel.unregister()
	config_registry.unregister()
	assembly_data.unregister()
	migrate_rig.unregister()
	armature_settings.unregister()
	armature_panel.unregister()

if __name__ == "__main__":
	register()
