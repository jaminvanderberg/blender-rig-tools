from dataclasses import asdict, dataclass, is_dataclass
import json
from typing import NamedTuple
import uuid
import bpy
from bpy.props import StringProperty, CollectionProperty, BoolProperty, EnumProperty
from bpy.types import PropertyGroup
from rigtools.assemblies.limb_collections import LimbCollectionMap

def find_assemblies(arm, bone_names):
	wanted = set(bone_names)
	assemblies = []
	for assembly in arm.rigtools_assemblies:
		names = {o.name for o in assembly.org_states}
		names.update(b.name for b in assembly.mechanism_bones)
		if names & wanted:
			assemblies.append(assembly)
	return assemblies

def check_assembly_use(armature_data, bone_names):
	to_check = set(bone_names)
	assemblies = []
	for assembly in armature_data.rigtools_assemblies:
		if to_check & {o.name for o in assembly.org_states}:
			assemblies.append(assembly)
	return assemblies

class RoleRef(PropertyGroup):
	name: StringProperty()

class BoneRef(PropertyGroup):
	name: StringProperty()
	roles: CollectionProperty(type=RoleRef)

class OrgState(PropertyGroup):
	name: StringProperty() # ORG bone name
	parent: StringProperty()
	use_connect: BoolProperty()

class AssemblyProperty(PropertyGroup):
	name: StringProperty()
	role: StringProperty()
	qualifier: StringProperty()

class AssemblyObject(PropertyGroup):
	name: StringProperty()

class AssemblyParent(PropertyGroup):
	label: StringProperty()
	bone: StringProperty()

class ReparentRule(PropertyGroup):
	from_bone: StringProperty()
	to_bone: StringProperty()

class AssemblyData(PropertyGroup):
	uid: StringProperty()
	name: StringProperty()
	side: StringProperty()
	assembly_type: EnumProperty(items=[
		('FK', "FK", ""),
		('IK', "IK", ""),
		('TORSO', "TORSO", ""),
		('PALM', "PALM", ""),
	])
	template_id: StringProperty()
	template_name: StringProperty()

	org_states: CollectionProperty(type=OrgState)
	twist_states: CollectionProperty(type=OrgState)
	# Cleared by migrate_4_to_5; kept so that migration can run. Tip handoff uses reparent_rules.
	org_children: CollectionProperty(type=OrgState)

	mechanism_bones: CollectionProperty(type=BoneRef)
	properties: CollectionProperty(type=AssemblyProperty)
	objects: CollectionProperty(type=AssemblyObject)
	reparent_rules: CollectionProperty(type=ReparentRule)
	
	ik_parents: CollectionProperty(type=AssemblyParent)

	options_json: StringProperty()
	config_defaults_json: StringProperty()

	def apply_tool(self, armature_data, tool, limb_collections):
		for bone_ref in tool.mechanism_bones:
			row = self.mechanism_bones.add()
			row.name = bone_ref.name
			roles = []
			for role in bone_ref.roles:
				role_row = row.roles.add()
				role_row.name = role
				roles.append(role)

			limb_collections.add_bone(armature_data, bone_ref.name, roles)

		for prop in tool.property_names:
			if not prop:
				continue
			if isinstance(prop, str):
				name, role, qualifier = prop, "", ""
			elif len(prop) == 2:
				name, role = prop
				qualifier = ""
			else:
				name, role, qualifier = prop
			row = self.properties.add()
			row.name = name
			row.role = role
			row.qualifier = qualifier

		for obj in tool.object_names:
			if not obj:
				continue
			row = self.objects.add()
			row.name = obj

		if hasattr(tool, 'twist_states'):
			for state in tool.twist_states:
				row = self.twist_states.add()
				row.name = state['name']
				row.parent = state['parent']
				row.use_connect = state['use_connect']

		if hasattr(tool, 'reparent_rules'):
			for from_bone, to_bone in tool.reparent_rules:
				row = self.reparent_rules.add()
				row.from_bone = from_bone
				row.to_bone = to_bone

		return self

	def get_bones_by_role(self, role):
		names = []
		for bone_ref in self.mechanism_bones:
			for role_ref in bone_ref.roles:
				if role_ref.name == role:
					names.append(bone_ref.name)
		return names

	def get_options(self):
		return json.loads(self.options_json or "{}")

	def get_config_defaults(self):
		return json.loads(self.get("config_defaults_json") or "{}")

	def get_chain(self):
		return [bone.name for bone in self.org_states]

def create_assembly_data(obj, org_bones, name, assembly_type, template_id, template_name, options, side="", uid=None):
	assemblies = check_assembly_use(obj.data, org_bones)
	if assemblies:
		raise ValueError(f"Selected bones are being used by other assemblies: {', '.join(a.name for a in assemblies)}")

	assembly_data = obj.data.rigtools_assemblies.add()
	assembly_data.uid = uid or str(uuid.uuid4())
	assembly_data.name = name
	assembly_data.side = side
	assembly_data.assembly_type = assembly_type
	assembly_data.options_json = _options_to_json(options)
	assembly_data.template_id = template_id
	assembly_data.template_name = template_name

	bones = obj.data.edit_bones if obj.mode == 'EDIT' else obj.data.bones

	for bone_name in org_bones:
		bone = bones[bone_name]
		row = assembly_data.org_states.add()
		row.name = bone_name
		row.parent = bone.parent.name if bone.parent else ""
		row.use_connect = bone.use_connect

	parents = getattr(options, 'ik_parents', None) or []
	for parent in parents:
		row = assembly_data.ik_parents.add()
		row.label = parent.label
		row.bone = parent.bone

	return assembly_data

def find_assembly(obj, uid):
	for assembly in obj.data.rigtools_assemblies:
		if assembly.uid == uid:
			return assembly
	return None

def _options_to_json(options):
	data = asdict(options) if is_dataclass(options) else dict(options)
	data.pop('ik_parents', None) # store separately
	return json.dumps(data)

@dataclass
class AssemblyChain:
	assembly_uid: str
	tools: list
	limb_collections: LimbCollectionMap
	
classes = (
	RoleRef,
	BoneRef,
	OrgState,
	AssemblyProperty,
	AssemblyObject,
	AssemblyParent,
	ReparentRule,
	AssemblyData,
	LimbCollectionMap,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	bpy.types.Armature.rigtools_assemblies = CollectionProperty(type=AssemblyData)
	bpy.types.Armature.rigtools_limb_collections = CollectionProperty(type=LimbCollectionMap)

def unregister():
	del bpy.types.Armature.rigtools_assemblies
	del bpy.types.Armature.rigtools_limb_collections
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
