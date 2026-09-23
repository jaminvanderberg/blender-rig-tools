import bpy
from rigtools.preferences import get_preferences
from rigtools.utils.bone import generate_bone_name, duplicate_bone, set_bone_collection
from dataclasses import dataclass
from typing import List
from rigtools.armature_settings import get_armature_settings
from rna_prop_ui import rna_idprop_ui_create

@dataclass
class IKParentTarget:
	label: str
	bone: str

@dataclass
class IKParentOptions:
	property_name: str
	parents: List[IKParentTarget]
	self_parent_mch: str | None = None
	self_parent_name: str | None = None
	self_parent_label: str = 'Foot'


def create_ik_parent_edit_mode(context, bone_names: list[str]):
	obj = context.object
	edit_bones = obj.data.edit_bones

	prefs = get_preferences(context)

	parent_bone_names = []
	for bone_name in bone_names:
		bone = edit_bones.get(bone_name)
		parent_name = generate_bone_name(bone_name, prefs.ik_parent_template)
		parent_bone = duplicate_bone(obj.data, bone, parent_name, 0.5)
		bone.parent = parent_bone
		parent_bone.parent = None

		if prefs.mch_collection_name:
			set_bone_collection(obj.data, parent_bone, prefs.mch_collection_name)

		parent_bone_names.append(parent_bone.name)
	
	return parent_bone_names

def create_ik_parent_pose_mode(context, parent_bone_names: list[str], options: IKParentOptions):
	obj = context.object
	pose_bones = obj.pose.bones

	settings = get_armature_settings(obj.data, context)
	prop_bone = pose_bones.get(settings.property_bone_name)

	parents = list(options.parents)
	if options.self_parent_mch and options.self_parent_name:
		parents.append(IKParentTarget(label=options.self_parent_label, bone=options.self_parent_name))

	labels = [parent.label for parent in parents]
	if options.property_name not in prop_bone:
		prop_bone[options.property_name] = 0
		rna_idprop_ui_create(
			prop_bone,
			options.property_name,
			default=0,
			min=0,
			max=len(labels) - 1,
			items=[(str(i), label, label) for i, label in enumerate(labels)]
		)
		prop_bone.property_overridable_library_set(f'["{options.property_name}"]', True)

	for parent_bone_name in parent_bone_names:
		parent_bone = pose_bones.get(parent_bone_name)
		constraint = parent_bone.constraints.new(type='ARMATURE')
		constraint.name = 'IK Parent'

		for i, parent in enumerate(parents):
			target = constraint.targets.new()
			target.target = obj
			target.subtarget = parent.bone 
			if parent_bone_name != options.self_parent_mch and parent.bone == options.self_parent_name:
				target.subtarget = settings.root_bone_name
			target.weight = 1.0

			driver = target.driver_add("weight").driver
			driver.type = 'SCRIPTED'
			driver.expression = f'val == {i}'

			var = driver.variables.new()
			var.name = "val"
			var.type = 'SINGLE_PROP'
			var.targets[0].id = obj
			var.targets[0].data_path = f'pose.bones["{settings.property_bone_name}"]["{options.property_name}"]'