bl_info = {
	"name": "RigTools UI",
	"author": "Jamin VanderBerg",
	"version": (0, 1),
	"blender": (4, 0, 0),
	"location": "View3D > Sidebar > Item",
	"description": "Animator panels for rigs built with Rig Tools",
	"category": "Rigging"
}

import bpy
import re
from bpy.props import StringProperty, CollectionProperty

# Data
def stored(id_data):
	"""Rigtools data stored on an ID, whether or not rigtools is registered."""
	if hasattr(id_data, "bl_system_properties_get"): # Blender 5.0+
		return id_data.bl_system_properties_get() or {}
	return id_data # 4.x: add-on properties live with regular ID properties

def property_bone(obj):
	"""The rig's properties pose bone, of None not applicable."""
	settings = stored(obj.data).get("rigtools")
	if not settings or not settings.get("is_initialized"):
		return None
	return obj.pose.bones.get(settings.get("property_bone_name", ""))

def find_assemblies(armature_data, bone_names):
	wanted = set(bone_names)
	assemblies = []
	for assembly in stored(armature_data).get("rigtools_assemblies", ()):
		names = {o.get("name") for o in assembly.get("org_states", ())}
		names.update(b.get("name") for b in assembly.get("mechanism_bones", ()))
		if names & wanted:
			assemblies.append(assembly)
	return assemblies

def find_snap_chain(armature_data, switch_property):
	for item in stored(armature_data).get("rig_ui_snap_chains", ()):
		if item.get("switch_property") == switch_property:
			return item
	return None

# Selection

def get_selected_bones(context):
	if context.mode == 'EDIT_ARMATURE':
		return list(context.selected_editable_bones)
	elif context.mode == 'POSE':
		return list(context.selected_pose_bones)
	return []

def mirror_pose_selection(context, selected):
	"""If X-Mirror is on in Pose mode, append each bone's L/R counterpart (no ID writes)."""
	obj = context.object
	if not obj or obj.type != 'ARMATURE' or context.mode != 'POSE':
		return selected
	if not obj.pose.use_mirror_x:
		return selected

	pose_bones = obj.pose.bones
	seen = {b.name for b in selected}
	expanded = list(selected)
	for bone in selected:
		flipped = flip_side_name(bone.name)
		if not flipped or flipped in seen:
			continue
		mirror = pose_bones.get(flipped)
		if mirror is None:
			continue
		expanded.append(mirror)
		seen.add(flipped)
	return expanded

# Naming
def get_base_name(bone_name) -> tuple[str, str]:
	symmetry_pattern = r'(\.[LR]|\_[LR])(\.\d+)?$'
	match = re.search(symmetry_pattern, bone_name, re.IGNORECASE)

	if match:
		base_name = bone_name[:match.start()]
		extension = match.group(0)
	else:
		base_name = bone_name
		extension = ""

	return base_name, extension

def flip_side_name(bone_name):
	"""Return the L/R flipped bone name, or None if there is no side suffix."""
	base_name, extension = get_base_name(bone_name)
	if not extension:
		return None
	flipped = extension.replace('L', '\0').replace('R', 'L').replace('\0', 'R')
	flipped = flipped.replace('l', '\0').replace('r', 'l').replace('\0', 'r')
	if flipped == extension:
		return None
	return base_name + flipped

###############################################################################
# SNAPPING OPERATORS

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
		obj = context.active_object
		item = find_snap_chain(obj.data, self.switch_property)
		pose_bones = obj.pose.bones
		prop_bone = property_bone(obj)
		if item is None or prop_bone is None:
			self.report({'ERROR'}, "Snap data not found for this rig.")
			return {'CANCELLED'}

		ik_control = pose_bones[item["ik_control"]]
		snap_control = pose_bones[item["snap_control"]]
		ik_control.matrix = get_matrix(obj, snap_control, ik_control)
		context.view_layer.update()

		if item["ik_pole"] and item["snap_pole"]:
			ik_pole = pose_bones[item["ik_pole"]]
			snap_pole = pose_bones[item["snap_pole"]]
			ik_pole.matrix = get_matrix(obj, snap_pole, ik_pole)
			context.view_layer.update()

		prop_bone[item["switch_property"]] = 1 #IK

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
		prop_bone = property_bone(arm)
		if item is None or prop_bone is None:
			self.report({'ERROR'}, "Snap data not found for this rig.")
			return {'CANCELLED'}

		for i, fk_bone in enumerate(item["fk_bones"]):
			fk_bone = pose_bones[fk_bone["name"]]
			mch_bone = pose_bones[item["ik_bones"][i]["name"]]
			fk_bone.matrix = get_matrix(arm, mch_bone, fk_bone)
			context.view_layer.update()

		prop_bone[item["switch_property"]] = 0 #FK 

		return {'FINISHED'}

classes = (
	RIG_OT_snap_ik_to_fk,
	RIG_OT_snap_fk_to_ik,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)

if __name__ == "__main__":
	register()
