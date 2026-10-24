bl_info = {
	"name": "Rig UI",
	"author": "Jamin VanderBerg",
	"version": (0, 1),
	"blender": (4, 0, 0),
	"location": "View3D > Sidebar > Item",
	"description": "Animator panels for rigs built with Rig Tools",
	"category": "Rigging"
}

import bpy

def stored(id_data):
	"""Rigtools data stored on an ID, whether or not rigtools is registered."""
	if hasattr(id_data, "bl_system_properties_get"): # Blender 5.0+
		return id_data.bl_system_properties_get() or {}
	return id_data # 4.x: add-on properties live with regular ID properties

class RIGUI_PT_spike(bpy.types.Panel):
	bl_label = "Rig UI Spike"
	bl_idname = "RIGUI_PT_spike"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = "Item"

	@classmethod
	def poll(cls, context):
		return context.object and context.object.type == 'ARMATURE'

	def draw(self, context):
		col = self.layout.column()
		for assembly in stored(context.object.data).get("rigtools_assemblies", ()):
			col.label(text=assembly.get("name", "?"), translate=False)

classes = (
	RIGUI_PT_spike,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)

if __name__ == "__main__":
	register()
