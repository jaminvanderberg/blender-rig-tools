from dataclasses import dataclass

from rigtools.assemblies.assembly_data import AssemblyChain, create_assembly_data, find_assembly
from rigtools.preferences import get_preferences
from rigtools.rig_ui.property_name import guess_assembly_name
from rigtools.tool.torso_fk import TorsoFK
from rigtools.utils.bone import find_side
from rigtools.utils.bone_collection import generate_bone_collection_name

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
	add_chest_rotation_isolation: bool = True
	use_twist_bones: bool = True
	tweak_relationship: str = "STRETCH_TO"
	override_collections: bool = True

def create_torso_assembly(context, chains: list[list[str]], template_name, options: TorsoAssemblyOptions):
	prefs = get_preferences()
	
	assemblies = []

	##############
	# Edit mode
	##############
	for chain in chains:
		side = find_side(chain)
		
		assembly_name = guess_assembly_name(context.object.data, chain, options.limb_property_base_name,side)
		assembly = create_assembly_data(context.object, chain, assembly_name, "TORSO", template_name, options)
		assembly_chain = AssemblyChain(assembly_uid=assembly.uid, tools=[])
		assemblies.append(assembly_chain)

		tweak_collection_name = generate_bone_collection_name(prefs.tweak_collection_template, options.limb_property_base_name, side)
		fk_collection_name = generate_bone_collection_name(prefs.fk_collection_template, options.limb_property_base_name, side)
		mch_collection_name = generate_bone_collection_name(prefs.mch_collection_template, options.limb_property_base_name, side)		
		control_collection_name = generate_bone_collection_name(prefs.control_collection_template, options.limb_property_base_name, side)

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
		)
		torso_fk_chain.edit_mode(context, chain)
		assembly_chain.tools.append(torso_fk_chain)

	##############
	# Pose mode
	##############
	for assembly_chain in assemblies:
		assembly = find_assembly(context.object, assembly_chain.assembly_uid)
		for tool in assembly_chain.tools:
			tool.pose_mode(context)
			assembly.apply_tool(tool)