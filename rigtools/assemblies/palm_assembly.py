from dataclasses import dataclass

from rigtools.assemblies.assembly_data import AssemblyChain, create_assembly_data, find_assembly
from rigtools.assemblies.limb_collections import ensure_limb_collections
from rigtools.tool.palm import Palm
from rigtools.utils.naming import guess_assembly_name, find_side

@dataclass
class PalmAssemblyOptions:
	limb_property_base_name: str
	fk_widget : str = "PILL"
	index_falloff_type: str = "SHARP"
	pinky_falloff_type: str = "LINEAR"

def create_palm_assembly(context, chains: list[list[str]], template_id, template_name, options: PalmAssemblyOptions, replacement_uid=None, prior_configs=None):
	prior_configs = prior_configs or {}
	assemblies = []

	##############
	# Edit mode
	##############
	for chain in chains:
		limb = options.limb_property_base_name
		side = find_side(chain)
		
		assembly_name = guess_assembly_name(context.object.data, chain, limb, side)
		assembly = create_assembly_data(context.object, chain, assembly_name, "PALM", template_id, template_name, options, side=side, uid=replacement_uid)
		assembly_chain = AssemblyChain(assembly_uid=assembly.uid, tools=[])
		assemblies.append(assembly_chain)
		
		limb_collections = ensure_limb_collections(context.object.data, limb, side)

		palm = Palm(
			fk_widget = options.fk_widget,
			mch_collection_name = limb_collections.mch,
			fk_collection_name = limb_collections.fk,
			index_falloff_type = options.index_falloff_type,
			pinky_falloff_type = options.pinky_falloff_type,
		)
		palm.edit_mode(context, chain)
		assembly_chain.tools.append(palm)

	##############
	# Pose mode
	##############
	for assembly_chain in assemblies:
		assembly = find_assembly(context.object, assembly_chain.assembly_uid)
		for tool in assembly_chain.tools:
			tool.pose_mode(context)
			assembly.apply_tool(tool)

	return [palm.fk_chain.fk_bone_names[0]]