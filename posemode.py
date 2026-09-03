import bpy

class RIG_OT_switch_back_to_pose(bpy.types.Operator):
	bl_idname = "rig.switch_back_to_pose"
	bl_label = "Switch Back to Pose Mode"
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		# Find the armature among selected objects
		rig = None
		for obj in context.selected_objects:
			if obj.type == 'ARMATURE':
				rig = obj
				break

		if not rig:
			self.report({'ERROR'}, "Could not find armature among selected objects")
			return {'CANCELLED'}

		# Deselect all, select and activate the rig
		bpy.ops.object.mode_set(mode='OBJECT')
		bpy.ops.object.select_all(action='DESELECT')
		rig.select_set(True)
		context.view_layer.objects.active = rig

		# Optional: unsolo DEF (or reset soloing)
		for coll in rig.data.collections:
			coll.is_solo = False  # Remove soloing from all

		# Switch to Pose Mode
		bpy.ops.object.mode_set(mode='POSE')

		# Restore viewport shading to solid (no wireframe overlay)
		for area in context.screen.areas:
			if area.type == 'VIEW_3D':
				for space in area.spaces:
					if space.type == 'VIEW_3D':
						space.shading.type = 'SOLID'
						space.overlay.show_wireframes = False

		return {'FINISHED'}
