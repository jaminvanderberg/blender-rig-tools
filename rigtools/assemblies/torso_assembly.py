from dataclasses import dataclass

from rigtools.assemblies.assembly_data import AssemblyChain, create_assembly_data, find_assembly
from rigtools.preferences import get_preferences
from rigtools.rig_ui.property_name import guess_assembly_name
from rigtools.utils.bone import find_side

@dataclass
class TorsoAssemblyOptions:
	bone_count_below_waist: int
	neck_bone_count: int
	neck_twist_bone_count: int = 2
	chest_twist_bone_count: int = 2
	fk_widget : str = "CIRCLE"
	tweak_relationship: str = "STRETCH_TO"

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


	##############
	# Pose mode
	##############
	for assembly_chain in assemblies:
		assembly = find_assembly(context.object, assembly_chain.assembly_uid)
		for tool in assembly_chain.tools:
			tool.pose_mode(context)
			assembly.apply_tool(tool)