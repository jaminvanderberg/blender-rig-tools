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

class IKParent:
	def __init__(self, *,
		property_name: str,
		parents: List[IKParentTarget],
		self_parent_label: str = 'Foot',
		mch_collection_name: str | None = None
	):
		self.property_name = property_name
		self.parents = parents
		self.self_parent_label = self_parent_label
		self.mch_collection_name = mch_collection_name

		self.self_parent_name = ""
		self.parent_bone_names = None

	def edit_mode(self, context, bone_names: list[str], self_parent_name: str = ""):
		obj = context.object
		edit_bones = obj.data.edit_bones
		prefs = get_preferences(context)

		self.self_parent_name = self_parent_name

		self.parent_bone_names = []
		for bone_name in bone_names:
			bone = edit_bones.get(bone_name)
			parent_name = generate_bone_name(bone_name, prefs.ik_parent_template)
			parent_bone = duplicate_bone(obj.data, bone, parent_name, 0.5)
			bone.parent = parent_bone
			parent_bone.parent = None

			if self.mch_collection_name:
				set_bone_collection(obj.data, parent_bone, self.mch_collection_name)
			elif prefs.mch_collection_name:
				set_bone_collection(obj.data, parent_bone, prefs.mch_collection_name)

			self.parent_bone_names.append(parent_bone.name)
		
		return self

	def pose_mode(self, context, self_parent_mch = None):
		obj = context.object
		pose_bones = obj.pose.bones

		settings = get_armature_settings(obj.data, context)
		prop_bone = pose_bones.get(settings.property_bone_name)

		parents = list(self.parents)
		if self_parent_mch and self.self_parent_name:
			parents.append(IKParentTarget(label=self.self_parent_label, bone=self.self_parent_name))

		labels = [parent.label for parent in parents]
		if self.property_name not in prop_bone:
			prop_bone[self.property_name] = 0
			rna_idprop_ui_create(
				prop_bone,
				self.property_name,
				default=0,
				min=0,
				max=len(labels) - 1,
				items=[(str(i), label, label) for i, label in enumerate(labels)]
			)
			prop_bone.property_overridable_library_set(f'["{self.property_name}"]', True)

		for parent_bone_name in self.parent_bone_names:
			parent_bone = pose_bones.get(parent_bone_name)
			constraint = parent_bone.constraints.new(type='ARMATURE')
			constraint.name = 'IK Parent'

			for i, parent in enumerate(parents):
				target = constraint.targets.new()
				target.target = obj
				target.subtarget = parent.bone 
				if parent_bone_name != self_parent_mch and parent.bone == self.self_parent_name:
					target.subtarget = settings.root_bone_name
				target.weight = 1.0

				driver = target.driver_add("weight").driver
				driver.type = 'SCRIPTED'
				driver.expression = f'val == {i}'

				var = driver.variables.new()
				var.name = "val"
				var.type = 'SINGLE_PROP'
				var.targets[0].id = obj
				var.targets[0].data_path = f'pose.bones["{settings.property_bone_name}"]["{self.property_name}"]'

		return self