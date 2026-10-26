import json
from dataclasses import dataclass
from typing import List

import bpy
from rigtools.assemblies.tool_data.mechanism_bones import MechanismBones
from rna_prop_ui import rna_idprop_ui_create

from rigtools.armature_settings import get_armature_settings
from rigtools.preferences import get_preferences
from rigtools.utils.bone import duplicate_bone
from rigtools.utils.naming import name_bone

CONSTRAINT_NAME = "IK Parent"
CONFIG_KEY = "ik_parent_config"


@dataclass
class IKParentTarget:
	label: str
	bone: str


class IKParent:
	def __init__(self, *,
		property_name: str,
		parents: List[IKParentTarget],
		self_parent_label: str = 'Foot',
		add_ik_control_as_pole_parent: bool = False
	):
		self.property_name = property_name
		self.parents = parents
		self.self_parent_label = self_parent_label

		self.self_parent_name = ""
		self.parent_bone_names = None
		self.add_ik_control_as_pole_parent = add_ik_control_as_pole_parent
		self.self_parent_mch = None

		self.mechanism_bones = MechanismBones()
		self.property_names = []
		self.object_names = []

	def edit_mode(self, context, bone_names: list[str], self_parent_name: str = ""):
		obj = context.object

		if obj.mode != 'EDIT':
			bpy.ops.object.mode_set(mode='EDIT')
		edit_bones = obj.data.edit_bones

		self.self_parent_name = self_parent_name

		self.parent_bone_names = []
		for bone_name in bone_names:
			bone = edit_bones.get(bone_name)
			parent_name = name_bone("ik_parent", bone_name)
			parent_bone = duplicate_bone(obj.data, bone, parent_name, 0.5)
			bone.parent = parent_bone
			parent_bone.parent = None

			self.parent_bone_names.append(parent_bone.name)

		self.mechanism_bones.extend(self.parent_bone_names, 'mch')
		self.property_names.append((self.property_name, "IK_PARENT"))

		if len(self.parent_bone_names) > 1:
			self.self_parent_mch = self.parent_bone_names[1]
		else:
			self.self_parent_mch = None

		return self

	def pose_mode(self, context):
		if context.object.mode != 'POSE':
			bpy.ops.object.mode_set(mode='POSE')

		self._ensure_property(context, create=True)
		self._setup_constraints(context)
		return self

	def resolved_parents(self):
		parents = list(self.parents)
		default = 0
		use_self = (
			self.add_ik_control_as_pole_parent
			and self.self_parent_mch
			and self.self_parent_name
		)
		if use_self:
			parents.append(IKParentTarget(label=self.self_parent_label, bone=self.self_parent_name))
			default = len(parents) - 1
		return parents, default

	def _ensure_property(self, context, *, create: bool):
		obj = context.object
		pose_bones = obj.pose.bones
		settings = get_armature_settings(obj.data, context)
		prop_bone = pose_bones.get(settings.property_bone_name)

		parents, default = self.resolved_parents()
		if not parents:
			raise ValueError("IK parent requires at least one parent target")

		labels = [parent.label for parent in parents]
		items = [(str(i), label, label) for i, label in enumerate(labels)]

		if self.property_name not in prop_bone:
			if not create:
				raise ValueError(f"IK parent property '{self.property_name}' not found")
			prop_bone[self.property_name] = default
			rna_idprop_ui_create(
				prop_bone,
				self.property_name,
				default=default,
				min=0,
				max=len(labels) - 1,
				items=items,
			)
			prop_bone.property_overridable_library_set(f'["{self.property_name}"]', True)
			return

		current = int(prop_bone[self.property_name])
		rna_idprop_ui_create(
			prop_bone,
			self.property_name,
			default=default,
			min=0,
			max=len(labels) - 1,
			items=items,
		)
		prop_bone[self.property_name] = min(max(current, 0), len(labels) - 1)

	def _setup_constraints(self, context):
		obj = context.object
		pose_bones = obj.pose.bones
		settings = get_armature_settings(obj.data, context)
		parents, _default = self.resolved_parents()

		use_self_mch = (
			self.add_ik_control_as_pole_parent
			and self.self_parent_mch
			and self.self_parent_name
		)

		for parent_bone_name in self.parent_bone_names:
			parent_bone = pose_bones.get(parent_bone_name)
			if not parent_bone:
				raise ValueError(f"IK parent bone '{parent_bone_name}' not found")

			for constraint in list(parent_bone.constraints):
				if constraint.type == 'ARMATURE' and constraint.name == CONSTRAINT_NAME:
					parent_bone.constraints.remove(constraint)

			constraint = parent_bone.constraints.new(type='ARMATURE')
			constraint.name = CONSTRAINT_NAME

			for i, parent in enumerate(parents):
				target = constraint.targets.new()
				target.target = obj
				target.subtarget = parent.bone
				if (
					use_self_mch
					and parent_bone_name != self.self_parent_mch
					and parent.bone == self.self_parent_name
				):
					target.subtarget = settings.root_bone_name
				target.weight = 1.0

				driver = target.driver_add("weight").driver
				driver.type = 'SCRIPTED'
				driver.expression = f'val == {i}'

				var = driver.variables.new()
				var.name = "val"
				var.type = 'SINGLE_PROP'
				var.targets[0].id = obj
				var.targets[0].data_path = (
					f'pose.bones["{settings.property_bone_name}"]["{self.property_name}"]'
				)

	def save_config(self, assembly):
		payload = {
			"property_name": self.property_name,
			"parent_bone_names": list(self.parent_bone_names or []),
			"self_parent_name": self.self_parent_name or "",
			"self_parent_mch": self.self_parent_mch or "",
			"self_parent_label": self.self_parent_label,
			"add_ik_control_as_pole_parent": bool(self.add_ik_control_as_pole_parent),
		}
		options = assembly.get_options()
		options[CONFIG_KEY] = payload
		options["add_ik_control_as_pole_parent"] = bool(self.add_ik_control_as_pole_parent)
		options["ik_parent_self_parent_label"] = self.self_parent_label
		assembly.options_json = json.dumps(options)

		assembly.ik_parents.clear()
		for parent in self.parents:
			row = assembly.ik_parents.add()
			row.label = parent.label
			row.bone = parent.bone

		return assembly

	@classmethod
	def apply_from_assembly(cls, context, assembly, parents: List[IKParentTarget], *, add_self: bool, self_label: str):
		options = assembly.get_options()
		payload = options.get(CONFIG_KEY)
		if not payload:
			raise ValueError(f"Assembly '{assembly.name}' has no IK parent config data")

		property_name = payload["property_name"]
		parent_bone_names = list(payload["parent_bone_names"])
		self_parent_name = payload.get("self_parent_name") or ""
		self_parent_mch = payload.get("self_parent_mch") or ""

		if add_self:
			if not self_parent_name:
				raise ValueError("Self parent bone is not configured for this assembly")
			if not self_parent_mch:
				if len(parent_bone_names) < 2:
					raise ValueError("Self parent requires a pole/parent mechanism bone")
				self_parent_mch = parent_bone_names[1]

		tool = cls(
			property_name=property_name,
			parents=parents,
			self_parent_label=self_label,
			add_ik_control_as_pole_parent=add_self,
		)
		tool.parent_bone_names = parent_bone_names
		tool.self_parent_name = self_parent_name
		tool.self_parent_mch = self_parent_mch or None

		if context.object.mode != 'POSE':
			bpy.ops.object.mode_set(mode='POSE')

		tool._ensure_property(context, create=False)
		tool._setup_constraints(context)
		tool.save_config(assembly)
		return tool
