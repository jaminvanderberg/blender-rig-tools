from dataclasses import dataclass

from rigtools.assemblies.assembly_data import AssemblyChain, create_assembly_data, find_assembly
from rigtools.tool.fk_chain import FKChain
from rigtools.utils.naming import guess_assembly_name, find_side, name_collection, name_property
from rigtools.utils.bone_collection import ensure_bone_collection
from rigtools.preferences import get_preferences
from rigtools.tool.fk_tweak_chain import FKTweakChain
from rigtools.tool.rotation_follow import RotationFollow
from rigtools.tool.rotation_isolation import RotationIsolation


@dataclass
class FKAssemblyOptions:
	limb_property_base_name: str
	control_mode: str = 'FK/TWEAK' # 'FK/TWEAK', 'FK', 'TWEAK'
	fk_bone_template: str = "FK-{name}"
	skip_first_tweak: bool = False
	fk_widget: str = 'CIRCLE'
	create_rotation_follow_setup: bool = False
	rotation_follow_skip: int = 1
	rotation_follow_relationship: str = 'COPY_ROTATION'
	fk_collection_name: str = '' # This will override the default
	tweak_collection_name: str = '' # This will override the default
	tweak_relationship: str = 'STRETCH_TO'
	add_rotation_isolation: bool = True
	override_collections: bool = True

def create_fk_assembly(context, chains: list[list[str]], template_id, template_name, options: FKAssemblyOptions, replacement_uid=None):
	armature_data = context.object.data
	original_mirror = armature_data.use_mirror_x
	armature_data.use_mirror_x = False

	assemblies = []

	try:
		##############
		# Edit mode
		##############
		for chain in chains:
			side = find_side(chain)
			
			assembly_name = guess_assembly_name(context.object.data, chain, options.limb_property_base_name,side)
			assembly = create_assembly_data(context.object, chain, assembly_name, "FK", template_id, template_name, options, replacement_uid)
			assembly_chain = AssemblyChain(assembly_uid=assembly.uid, tools=[])
			assemblies.append(assembly_chain)

			default_tweak_collection_name = name_collection("tweak", options.limb_property_base_name, side)
			default_fk_collection_name = name_collection("fk", options.limb_property_base_name, side)
			mch_collection_name = name_collection("mch", options.limb_property_base_name, side)

			fk_collection_name = options.fk_collection_name or default_fk_collection_name
			tweak_collection_name = options.tweak_collection_name or default_tweak_collection_name
			if not options.override_collections:
				fk_collection_name = None
				tweak_collection_name = None

			ensure_bone_collection(
				armature_data,
				mch_collection_name,
				get_preferences().mch_parent_collection,
			)

			if options.control_mode in ['FK/TWEAK', 'TWEAK']:
				# TWEAK CHAIN
				tweak = FKTweakChain(
					fk_bone_template=options.fk_bone_template,
					skip_first_tweak=options.skip_first_tweak,
					do_create_fk=(options.control_mode == 'FK/TWEAK'),
					fk_widget=options.fk_widget,
					fk_collection_name=fk_collection_name,
					tweak_collection_name=tweak_collection_name,
					tweak_relationship=options.tweak_relationship,
				)
				tweak.edit_mode(armature_data, chain)
				assembly_chain.tools.append(tweak)
				fk_names = tweak.fk_bone_names
			else:
				# FK CHAIN
				fk = FKChain(
					fk_bone_template=options.fk_bone_template,
					fk_widget=options.fk_widget,
					fk_collection_name=fk_collection_name,
				)
				fk.edit_mode(armature_data, chain)
				assembly_chain.tools.append(fk)
				fk_names = fk.fk_bone_names

			# ROTATION ISOLATION
			if options.add_rotation_isolation and len(fk_names) > 0:
				property_name = name_property("rotation_isolation", options.limb_property_base_name, side)
				rotation_isolation = RotationIsolation(property_name=property_name, mch_collection_name=mch_collection_name)
				rotation_isolation.edit_mode(context, armature_data, [fk_names[0]])
				assembly_chain.tools.append(rotation_isolation)

			# ROTATION FOLLOW
			if options.create_rotation_follow_setup and len(fk_names) > 0:
				follow_bones = fk_names[options.rotation_follow_skip:]
				if follow_bones:
					follow = RotationFollow(relationship=options.rotation_follow_relationship, mch_collection_name=mch_collection_name)
					follow.edit_mode(context, follow_bones)
					assembly_chain.tools.append(follow)

		##############
		# Pose mode
		##############
		for assembly_chain in assemblies:
			assembly = find_assembly(context.object, assembly_chain.assembly_uid)
			for tool in assembly_chain.tools:
				tool.pose_mode(context)
				assembly.apply_tool(tool)
	finally:
		armature_data.use_mirror_x = original_mirror
