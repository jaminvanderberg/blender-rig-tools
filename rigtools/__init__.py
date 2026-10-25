bl_info = {
	"name": "RigTools",
	"author": "Jamin VanderBerg",
	"version": (0, 97),
	"blender": (4, 0, 0),
	"location": "View3D > Sidebar > Rig Tools",
	"description": "Helper functions for rig building",
	"category": "Rigging"
}

import bpy

from rigtools import generate_org_bones
from rigtools import panel
from rigtools import selection_panel
from rigtools import preferences
from rigtools import preferences_io
from rigtools import armature_settings
from rigtools import migrate_rig
from rigtools import twist_bones
from rigtools import rename_chain
from rigtools import parent_along_chain
from rigtools import weight_paint_proxy
from rigtools import root_widget
from rigtools.operators import human_skeleton
from rigtools.operators import create_twist_bones
from rigtools.assemblies import assembly_data
from rigtools.assemblies import config_registry
from rigtools.panels import skirt_legs as skirt_legs_panel
from rigtools.panels.ik import ik_panel
from rigtools.panels.fk import fk_panel
from rigtools.panels.assembly import assembly_panel
from rigtools.rig_ui import collections_panel
from rigtools.rig_ui import snapping_data
from rigtools.rig_ui import rig_ui
from rigtools.rig_ui import embed_ui

classes = (
	preferences.RigToolsPreferences,
	preferences_io.RIG_OT_export_preferences,
	preferences_io.RIG_OT_import_preferences,
	panel.RIG_PT_tools_npanel,
	generate_org_bones.RIG_OT_generate_org_bones,
	parent_along_chain.RIG_OT_parent_along_chain,
)

def register():
	if rig_ui.RIG_DATA_VERSION != armature_settings.CURRENT_RIG_DATA_VERSION:
		raise RuntimeError(
			f"rig_ui.RIG_DATA_VERSION ({rig_ui.RIG_DATA_VERSION}) must match "
			f"CURRENT_RIG_DATA_VERSION ({armature_settings.CURRENT_RIG_DATA_VERSION})"
		)

	armature_settings.register()
	migrate_rig.register()
	twist_bones.register()
	selection_panel.register()

	assembly_data.register()
	config_registry.register()
	skirt_legs_panel.register()
	ik_panel.register()
	fk_panel.register()
	assembly_panel.register()

	rename_chain.register()
	weight_paint_proxy.register()
	root_widget.register()
	human_skeleton.register()
	create_twist_bones.register()

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

	create_twist_bones.unregister()
	human_skeleton.unregister()
	root_widget.unregister()
	weight_paint_proxy.unregister()
	rename_chain.unregister()
	selection_panel.unregister()
	twist_bones.unregister()

	assembly_panel.unregister()
	ik_panel.unregister()
	fk_panel.unregister()
	skirt_legs_panel.unregister()
	config_registry.unregister()
	assembly_data.unregister()
	migrate_rig.unregister()
	armature_settings.unregister()

if __name__ == "__main__":
	register()
