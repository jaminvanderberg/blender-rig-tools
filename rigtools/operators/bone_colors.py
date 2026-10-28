import bpy
from rigtools.assemblies.tool_data.mechanism_bones import BoneStyle

class RIG_OT_reapply_bone_colors(bpy.types.Operator):
	bl_idname = "rig.reapply_bone_colors"
	bl_label = "Reapply Bone Colors"
	bl_description = "Recolor every rig in the file using the current color preferences"
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		count = 0
		for obj in bpy.data.objects:
			if obj.type != 'ARMATURE':
				continue
			pose_bones = obj.pose.bones
			for assembly in obj.data.rigtools_assemblies:
				for mech_bone in assembly.mechanism_bones:
					color = mech_bone.get_style().color
					pose_bone = pose_bones.get(mech_bone.name)
					if color is None or pose_bone is None:
						continue
					BoneStyle(color=color).apply(context, pose_bone, assembly.side)
					mech_bone.palette = pose_bone.color.palette
					count += 1

			settings = obj.data.rigtools
			if settings.is_initialized:
				for name in (settings.root_bone_name, settings.property_bone_name):
					pose_bone = pose_bones.get(name)
					if pose_bone and pose_bone.color.palette != 'DEFAULT':
						BoneStyle(color='root').apply(context, pose_bone, "")
						count += 1                    

		self.report({'INFO'}, f"Recolored {count} bones")
		return {'FINISHED'}


classes = (
	RIG_OT_reapply_bone_colors,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
