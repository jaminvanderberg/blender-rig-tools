import bpy
from bpy.props import StringProperty, CollectionProperty
from rigtools.armature_settings import get_armature_settings
from rigtools.rig_ui.snapping_data import RigUISnapBoneItem, RigUISnapChainItem, find_snap_chain

# returns final world matrix accounting for offset in rest pose
def get_matrix(armature, source_bone, target_bone):
	# rest post matrices
	source_bone_rest_matrix = source_bone.bone.matrix_local
	target_bone_rest_matrix = target_bone.bone.matrix_local

	# rest pose offset matrix
	offset_matrix = source_bone_rest_matrix.inverted() @ target_bone_rest_matrix

	# world_space_matrices
	source_world_matrix = source_bone.matrix

	#world space matrix
	matrix_final =  source_world_matrix @ offset_matrix
	
	return matrix_final

class RIG_OT_snap_ik_to_fk(bpy.types.Operator):
	bl_idname = "rig.snap_ik_to_fk"
	bl_label = "Snap IK > FK"
	bl_description = "Snap IK > FK"
	bl_options = {'UNDO', 'INTERNAL'}

	switch_property: StringProperty()

	@classmethod
	def poll(self, context):
		return context.active_object and context.active_object.type == 'ARMATURE'

	def execute(self, context):
		arm = context.active_object
		item = find_snap_chain(arm.data, self.switch_property)
		pose_bones = arm.pose.bones
		settings = get_armature_settings(arm.data, context)
		props = pose_bones[settings.property_bone_name]

		ik_control = pose_bones[item.ik_control]
		snap_control = pose_bones[item.snap_control]
		ik_control.matrix = get_matrix(arm, snap_control, ik_control)
		context.view_layer.update()

		if item.ik_pole and item.snap_pole:
			ik_pole = pose_bones[item.ik_pole]
			snap_pole = pose_bones[item.snap_pole]
			ik_pole.matrix = get_matrix(arm, snap_pole, ik_pole)
			context.view_layer.update()

		props[item.switch_property] = 1 #IK

		return {'FINISHED'}

class RIG_OT_snap_fk_to_ik(bpy.types.Operator):
	bl_idname = "rig.snap_fk_to_ik"
	bl_label = "Snap FK > IK"
	bl_description = "Snap FK > IK"
	bl_options = {'UNDO', 'INTERNAL'}

	switch_property: StringProperty()

	@classmethod
	def poll(self, context):
		return context.active_object and context.active_object.type == 'ARMATURE'

	def execute(self, context):
		arm = context.active_object
		item = find_snap_chain(arm.data, self.switch_property)
		pose_bones = arm.pose.bones
		settings = get_armature_settings(arm.data, context)
		props = pose_bones[settings.property_bone_name]

		select_set = [props.name]
		for i, fk_bone in enumerate(item.fk_bones):
			fk_bone = pose_bones[fk_bone.name]
			mch_bone = pose_bones[item.ik_bones[i].name]
			fk_bone.matrix = get_matrix(arm, mch_bone, fk_bone)
			context.view_layer.update()
			select_set.append(fk_bone.name)

		props[item.switch_property] = 0 #FK 

		return {'FINISHED'}

classes = (
	RigUISnapBoneItem,
	RigUISnapChainItem,
	RIG_OT_snap_ik_to_fk,
	RIG_OT_snap_fk_to_ik,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	bpy.types.Armature.rig_ui_snap_chains = CollectionProperty(type=RigUISnapChainItem)

def unregister():
	del bpy.types.Armature.rig_ui_snap_chains
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
