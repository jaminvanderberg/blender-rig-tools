from dataclasses import asdict, dataclass, is_dataclass
import json
import uuid
import bpy
from bpy.props import StringProperty, CollectionProperty, BoolProperty, EnumProperty
from bpy.types import PropertyGroup

def find_assemblies(arm, bone_names):
	wanted = set(bone_names)
	assemblies = []
	for assembly in arm.rigtools_assemblies:
		names = {o.name for o in assembly.org_states}
		names.update(b.name for b in assembly.mechanism_bones)
		if names & wanted:
			assemblies.append(assembly)
	return assemblies

class BoneRef(PropertyGroup):
	name: StringProperty()

class OrgState(PropertyGroup):
	name: StringProperty() # ORG bone name
	parent: StringProperty()
	use_connect: BoolProperty()

class AssemblyProperty(PropertyGroup):
	name: StringProperty()

class AssemblyObject(PropertyGroup):
	name: StringProperty()

class AssemblyParent(PropertyGroup):
	label: StringProperty()
	bone: StringProperty()

class AssemblyData(PropertyGroup):
	uid: StringProperty()
	name: StringProperty()
	assembly_type: EnumProperty(items=[
		('FK', "FK", ""),
		('IK', "IK", ""),
		('TORSO', "TORSO", ""),
	])
	template_name: StringProperty()

	org_states: CollectionProperty(type=OrgState)
	twist_states: CollectionProperty(type=OrgState)
	org_children: CollectionProperty(type=OrgState)

	mechanism_bones: CollectionProperty(type=BoneRef)
	properties: CollectionProperty(type=AssemblyProperty)
	objects: CollectionProperty(type=AssemblyObject)
	
	ik_parents: CollectionProperty(type=AssemblyParent)

	options_json: StringProperty()

	def apply_tool(self, tool):
		for bone_ref in tool.mechanism_bone_names:
			if not bone_ref:
				continue
			row = self.mechanism_bones.add()
			row.name = bone_ref

		for prop in tool.property_names:
			if not prop:
				continue
			row = self.properties.add()
			row.name = prop

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

		return self

	def get_options(self):
		return json.loads(self.options_json)

	def get_chains(self):
		return [[bone.name for bone in self.org_states]]

def create_assembly_data(obj, org_bones, name, assembly_type, template_name, options):
	assembly_data = obj.data.rigtools_assemblies.add()
	assembly_data.uid = str(uuid.uuid4())
	assembly_data.name = name
	assembly_data.assembly_type = assembly_type
	assembly_data.options_json = _options_to_json(options)
	assembly_data.template_name = template_name

	bones = obj.data.edit_bones if obj.mode == 'EDIT' else obj.data.bones

	for bone_name in org_bones:
		bone = bones[bone_name]
		row = assembly_data.org_states.add()
		row.name = bone_name
		row.parent = bone.parent.name if bone.parent else ""
		row.use_connect = bone.use_connect

	last_org_bone = bones[org_bones[-1]]
	for child in last_org_bone.children:
		row = assembly_data.org_children.add()
		row.name = child.name
		row.parent = last_org_bone.name
		row.use_connect = child.use_connect

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
	
classes = (
	BoneRef,
	OrgState,
	AssemblyProperty,
	AssemblyObject,
	AssemblyParent,
	AssemblyData,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	bpy.types.Armature.rigtools_assemblies = CollectionProperty(type=AssemblyData)

def unregister():
	del bpy.types.Armature.rigtools_assemblies
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
