bl_info = {
	"name": "RigTools",
	"author": "Jamin VanderBerg",
	"version": (0, 9, 1),
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
from rigtools.rig_data import shape_key_connections
from rigtools.operators import rename_chain
from rigtools.operators import parent_along_chain
from rigtools.operators import weight_paint_proxy
from rigtools.operators import root_widget
from rigtools.operators import human_skeleton
from rigtools.operators import create_twist_bones
from rigtools.operators import bone_colors
from rigtools.operators import corrective_bones
from rigtools.operators import pin_to_mesh
from rigtools.assemblies import assembly_data
from rigtools.assemblies import config_registry
from rigtools.panels import skirt_legs as skirt_legs_panel
from rigtools.panels.ik import ik_panel
from rigtools.panels.fk import fk_panel
from rigtools.panels.assembly import assembly_panel
from rigtools.panels.corrective import corrective_panel
from rigtools.panels.bone_style import bone_style_panel
from rigtools.panels import shape_keys
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

modules = (
	# Registered first so the Armature panel sits at the top of the tab
	armature_panel,
	armature_settings,
	migrate_rig,
	twist_chain,
	shape_key_connections,

	assembly_data,
	config_registry,
	skirt_legs_panel,
	ik_panel,
	fk_panel,
	assembly_panel,
	corrective_panel,
	data_viewer_panel,

	rename_chain,
	weight_paint_proxy,
	root_widget,
	human_skeleton,
	create_twist_bones,
	bone_colors,
	corrective_bones,
	pin_to_mesh,
	bone_style_panel,
	shape_keys,

	snapping_data,
	rig_ui,
	collections_panel,
	embed_ui,
)

def register():
	if rig_ui.RIG_DATA_VERSION != armature_settings.CURRENT_RIG_DATA_VERSION:
		raise RuntimeError(
			f"rig_ui.RIG_DATA_VERSION ({rig_ui.RIG_DATA_VERSION}) must match "
			f"CURRENT_RIG_DATA_VERSION ({armature_settings.CURRENT_RIG_DATA_VERSION})"
		)

	for mod in modules:
		mod.register()
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
	for mod in reversed(modules):
		mod.unregister()
