import bpy
import re

class RIG_OT_batch_rename_bones(bpy.types.Operator):
		"""Batch rename bones via find and replace, add prefix/suffix, and strip numbers"""
		bl_idname = "rig.batch_rename_bones"
		bl_label = "Batch Rename Bones"
		bl_options = {'REGISTER', 'UNDO'}
		bl_property = "find"
		
		find: bpy.props.StringProperty(name="Find")
		replace: bpy.props.StringProperty(name="Replace")

		prefix: bpy.props.StringProperty(name="Add Prefix")
		suffix: bpy.props.StringProperty(name="Add Suffix")
		
		strip_suffix: bpy.props.BoolProperty(
				name="Strip .001 Suffixes",
				description="Remove trailing numeric suffixes before applying rename rules",
				default=True
		)

		def execute(self, context):
				obj = context.active_object
				if not obj or obj.type != 'ARMATURE':
						self.report({'ERROR'}, "Active object must be an armature.")
						return {'CANCELLED'}

				count = 0

				# Mode-safe bone collection selection
				if obj.mode == 'EDIT':
						bones = context.selected_editable_bones
				elif obj.mode == 'POSE':
						bones = [pbone.bone for pbone in context.selected_pose_bones]
				else:
						self.report({'ERROR'}, "Must be in Edit or Pose mode.")
						return {'CANCELLED'}

				for bone in bones:
						original_name = bone.name
						working_name = original_name

						# Find & Replace
						if self.find:
								working_name = working_name.replace(self.find, self.replace)

						# Strip numeric suffixes like .001, .042 if requested
						# We do this after find/replace, in case the user uses the number in the find string
						if self.strip_suffix:
								working_name = re.sub(r'\.\d{3}$', '', working_name)

						# Prefix & Suffix
						if self.prefix:
								working_name = self.prefix + working_name
						if self.suffix:
								working_name = working_name + self.suffix

						# Only update and count if the name actually changed
						if working_name != original_name:
								bone.name = working_name
								count += 1

				self.report({'INFO'}, f"Renamed {count} bone{'s' if count != 1 else ''}.")
				return {'FINISHED'}
		
		def invoke(self, context, event):
				return context.window_manager.invoke_props_dialog(self, width=300)
		
		def draw(self, context):
				layout = self.layout
				
				# Settings section
				#box = layout.box()
				#box.label(text="Settings:", icon='SETTINGS')
				
				col = layout.column()
				col.prop(self, "find")
				col.prop(self, "replace")

				row = layout.row(align=True)
				sub = row.split(factor=0.45)
				sub.label(text="Add Prefix")
				sub.prop(self, "prefix", text="")
				sub = row.split(factor=0.45)
				sub.label(text="  Add Suffix")
				sub.prop(self, "suffix", text="")
				col = layout.row()
				col.prop(self, "strip_suffix")
		
classes = (
		RIG_OT_batch_rename_bones,
)


import bpy

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
		
		for cls in classes:
				bpy.utils.unregister_class(cls)

if __name__ == "__main__":
		try:
				unregister()
		except Exception:
				pass
		register()
