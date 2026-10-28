from dataclasses import asdict, dataclass, is_dataclass
import json
import uuid
import bpy
from bpy.props import StringProperty, CollectionProperty, BoolProperty, EnumProperty
from bpy.types import PropertyGroup
from rigtools.assemblies.limb_collections import LimbCollectionMap
from rigtools.assemblies.tool_data.mechanism_bones import BoneStyle
from rigtools.utils.naming import limb_group_label
from rigtools.utils.widget import widget_fingerprint

def find_assemblies(armature_data, bone_names):
	wanted = set(bone_names)
	assemblies = []
	for assembly in armature_data.rigtools_assemblies:
		names = {o.name for o in assembly.org_states}
		names.update(b.name for b in assembly.mechanism_bones)
		if names & wanted:
			assemblies.append(assembly)
	return assemblies

# Config payloads that tools write back into options_json; they hold per-chain bone names
CONFIG_OPTION_KEYS = {"ik_parent_config", "skirt_collision", "skirt_ride"}

def find_similar_assemblies(armature_data, source, mode, include_mirror):
	"""mode 'LIMB': same limb name. mode 'CONFIG': also the same options.
	include_mirror matches any side, otherwise only the source's side. Yields the source assembly too."""
	source_options = source.get_options()
	limb = source_options["limb_property_base_name"]
	source_config = {k: v for k, v in source_options.items() if k not in CONFIG_OPTION_KEYS}

	for assembly in armature_data.rigtools_assemblies:
		if not include_mirror and assembly.side != source.side:
			continue
		options = assembly.get_options()
		if options["limb_property_base_name"] != limb:
			continue
		if mode == 'CONFIG' and {k: v for k, v in options.items() if k not in CONFIG_OPTION_KEYS} != source_config:
			continue
		yield assembly

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
	style_json: StringProperty()
	widget_fingerprint: StringProperty() # hash
	palette: StringProperty() # resolved widget color

	def get_style(self) -> BoneStyle:
		return BoneStyle.from_json(self.style_json)

	def set_style(self, style: BoneStyle):
		self.style_json = style.to_json()

	def add_style(self, style: BoneStyle):
		stored = self.get_style()
		stored.append(style)
		self.set_style(stored)

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
	ui_label: StringProperty()
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

	def apply_tool(self, context, tool, limb_collections):
		obj = context.object
		armature_data = obj.data
		if obj.mode != 'POSE':
			bpy.ops.object.mode_set(mode='POSE')

		pose_bones = obj.pose.bones

		# Mechanism bones and collections
		for bone_ref in tool.mechanism_bones:
			mech_bone = self.mechanism_bones.add()
			mech_bone.name = bone_ref.name
			roles = []
			for role in bone_ref.roles:
				mech_role = mech_bone.roles.add()
				mech_role.name = role
				roles.append(role)

			limb_collections.add_bone(armature_data, bone_ref.name, roles)

			# Bone Color
			style = tool.mechanism_bones.styles[bone_ref.name]
			if style.color is None:
				color_roles = [role for role in bone_ref.roles if role != 'mch']
				if len(color_roles) == 1:
					style.color = color_roles[0]

		# Bone Styles
		mech_bones_by_name = {row.name: row for row in self.mechanism_bones}
		for bone_name, style in tool.mechanism_bones.styles.items():
			mech_bone = mech_bones_by_name.get(bone_name)
			if mech_bone is None:
				raise ValueError(f"{type(tool).__name__} styled '{bone_name}', which isn't in assembly '{self.name}'")

			pose_bone = pose_bones[bone_name]
			wgt = style.apply(context, pose_bones[bone_name], limb_collections.side)
			if wgt:
				self.objects.add().name = wgt.name
			if style.widget is not None:
				mech_bone.widget_fingerprint = widget_fingerprint(wgt)
			if style.color is not None:
				mech_bone.palette = pose_bone.color.palette

			mech_bone.add_style(style)

		# Properties
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

	limb = getattr(options, 'limb_property_base_name', "") or ""
	assembly_data.ui_label = limb_group_label(limb.strip(), side) or name

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
