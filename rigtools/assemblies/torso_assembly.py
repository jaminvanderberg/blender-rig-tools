from dataclasses import dataclass

from rigtools.assemblies.assembly_data import AssemblyChain, create_assembly_data, find_assembly
from rigtools.utils.naming import guess_assembly_name, find_side, name_collection, name_property
from rigtools.utils.bone_collection import ensure_bone_collection
from rigtools.preferences import get_preferences
from rigtools.tool.rotation_isolation import RotationIsolation
from rigtools.tool.torso_fk import TorsoFK

@dataclass
class TorsoAssemblyOptions:
	limb_property_base_name: str
	lower_torso_bone_count: int
	neck_bone_count: int
	neck_twist_bone_count: int = 2
	chest_twist_bone_count: int = 2
	add_tweak_bones: bool = True
	fk_widget : str = "CIRCLE"
	add_neck_rotation_isolation: bool = True
	neck_base_property_name: str = "neck"
	neck_inherit_scale_from_root: bool = True
	add_head_rotation_isolation: bool = True
	head_base_property_name: str = "head"
	head_inherit_scale_from_root: bool = True
	use_twist_bones: bool = True
	tweak_relationship: str = "STRETCH_TO"
	override_collections: bool = True
	neck_falloff_type: str = "ROOT"

def create_torso_assembly(context, chains: list[list[str]], template_id, template_name, options: TorsoAssemblyOptions):
	assemblies = []

	##############
	# Edit mode
	##############
	for chain in chains:
		side = find_side(chain)
		
		assembly_name = guess_assembly_name(context.object.data, chain, options.limb_property_base_name,side)
		assembly = create_assembly_data(context.object, chain, assembly_name, "TORSO", template_id, template_name, options)
		assembly_chain = AssemblyChain(assembly_uid=assembly.uid, tools=[])
		assemblies.append(assembly_chain)

		tweak_collection_name = name_collection("tweak", options.limb_property_base_name, side)
		fk_collection_name = name_collection("fk", options.limb_property_base_name, side)
		mch_collection_name = name_collection("mch", options.limb_property_base_name, side)
		control_collection_name = name_collection("control", options.limb_property_base_name, side)

		if options.override_collections:
			ensure_bone_collection(
				context.object.data,
				mch_collection_name,
				get_preferences().mch_parent_collection,
			)

		# TWEAK CHAIN
		torso_fk_chain = TorsoFK(
			lower_torso_bone_count = options.lower_torso_bone_count,
			neck_bone_count = options.neck_bone_count,
			neck_twist_bone_count = options.neck_twist_bone_count if options.use_twist_bones else 0,
			chest_twist_bone_count = options.chest_twist_bone_count if options.use_twist_bones else 0,
			add_tweak_bones = options.add_tweak_bones,
			tweak_relationship = options.tweak_relationship,
			fk_widget = options.fk_widget,
			tweak_collection_name = tweak_collection_name if options.override_collections else None,
			fk_collection_name = fk_collection_name if options.override_collections else None,
			mch_collection_name = mch_collection_name if options.override_collections else None,
			control_collection_name = control_collection_name if options.override_collections else None,
			add_neck_rotation_isolation = options.add_neck_rotation_isolation,
			neck_falloff_type = options.neck_falloff_type,
		)
		torso_fk_chain.edit_mode(context, chain)
		assembly_chain.tools.append(torso_fk_chain)

		# NECK ROTATION ISOLATION
		if options.add_neck_rotation_isolation:
			neck_property_name = name_property(
				"rotation_isolation",
				options.neck_base_property_name,
				side,
			)
			neck_rotation_isolation = RotationIsolation(
				property_name = neck_property_name,
				inherit_scale_from_root = options.neck_inherit_scale_from_root,
				mch_collection_name = mch_collection_name if options.override_collections else None,
			)
			neck_name = torso_fk_chain.fk_bone_names[-options.neck_bone_count - 1]
			neck_rotation_isolation.edit_mode(context, context.object.data, [neck_name])
			assembly_chain.tools.append(neck_rotation_isolation)

		# HEAD ROTATION ISOLATION
		if options.add_head_rotation_isolation:
			head_property_name = name_property(
				"rotation_isolation",
				options.head_base_property_name,
				side,
			)

			head_rotation_isolation = RotationIsolation(
				property_name = head_property_name,
				inherit_scale_from_root = options.head_inherit_scale_from_root,
				mch_collection_name = mch_collection_name if options.override_collections else None,
			)
			head_name = torso_fk_chain.fk_bone_names[-1]
			head_rotation_isolation.edit_mode(context, context.object.data, [head_name])
			assembly_chain.tools.append(head_rotation_isolation)

	##############
	# Pose mode
	##############
	for assembly_chain in assemblies:
		assembly = find_assembly(context.object, assembly_chain.assembly_uid)
		for tool in assembly_chain.tools:
			tool.pose_mode(context)
			assembly.apply_tool(tool)