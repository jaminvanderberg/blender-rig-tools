import bpy

def get_mesh_items(self, context):
	armature = context.object
	if not armature or armature.type != 'ARMATURE':
		return []

	items = []
	for i, child in enumerate(armature.children):
		if child.type == 'MESH':
			items.append((child.name, child.name, "", i))
	return items

class RIG_OT_switch_to_weight_paint(bpy.types.Operator):
	bl_idname = "rig.switch_to_weight_paint"
	bl_label = "Switch to Weight Paint Mode"
	bl_options = {'REGISTER', 'UNDO'}

	target_mesh: bpy.props.EnumProperty(name="Target Mesh", items=get_mesh_items)

	def execute(self, context):
		rig = context.object
		if rig.type != 'ARMATURE':
			self.report({'ERROR'}, "Active object must be an armature")
			return {'CANCELLED'}

		mesh = bpy.data.objects.get(self.target_mesh)
		if not mesh:
			self.report({'ERROR'}, "Selected mesh not found")
			return {'CANCELLED'}

		# Solo DEF bone collection
		for coll in rig.data.collections:
			coll.is_solo = (coll.name == "DEF")

		# Switch to Object mode
		bpy.ops.object.mode_set(mode='OBJECT')

		# Select rig and mesh, make mesh active
		bpy.ops.object.select_all(action='DESELECT')
		rig.select_set(True)
		mesh.select_set(True)
		context.view_layer.objects.active = mesh

		# Switch to Weight Paint mode
		bpy.ops.object.mode_set(mode='WEIGHT_PAINT')

		# Enable wireframe overlay in Solid mode (no X-ray)
		for area in context.screen.areas:
			if area.type == 'VIEW_3D':
				for space in area.spaces:
					if space.type == 'VIEW_3D':
						space.shading.type = 'SOLID'
						space.overlay.show_wireframes = True

		return {'FINISHED'}

	def invoke(self, context, event):
		wm = context.window_manager
		return wm.invoke_props_dialog(self)
