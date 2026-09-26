from dataclasses import dataclass

from rigtools.preferences import get_preferences
from rigtools.tool.fk_tweak_chain import FKTweakChain
from rigtools.tool.rotation_follow import RotationFollow
from rigtools.tool.rotation_isolation import RotationIsolation
from rigtools.utils.bone import find_side
from rigtools.utils.bone_collection import generate_bone_collection_name
from rigtools.utils.property import generate_property_name

@dataclass
class FKAssemblyOptions:
	limb_property_base_name: str
	do_create_fk: bool = True
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

def create_fk_assembly(context, chains: list[list[str]], options: FKAssemblyOptions):
	prefs = get_preferences()
	
	armature_data = context.object.data

	processed_chains: list[FKTweakChain] = []
	rotation_isolation_chains = []
	rotation_follow_chains = []
	for chain in chains:
		side = find_side(chain)

		prefs_tweak_collection_name = generate_bone_collection_name(prefs.tweak_collection_template, options.limb_property_base_name, side)
		prefs_fk_collection_name = generate_bone_collection_name(prefs.fk_collection_template, options.limb_property_base_name, side)
		mch_collection_name = generate_bone_collection_name(prefs.mch_collection_template, options.limb_property_base_name, side)

		fk_collection_name = options.fk_collection_name or prefs_fk_collection_name
		tweak_collection_name = options.tweak_collection_name or prefs_tweak_collection_name
		if not options.override_collections:
			fk_collection_name = None
			tweak_collection_name = None

		# TWEAK CHAIN
		tweak = FKTweakChain(
			fk_bone_template=options.fk_bone_template,
			skip_first_tweak=options.skip_first_tweak,
			do_create_fk=options.do_create_fk,
			fk_widget=options.fk_widget,
			fk_collection_name=fk_collection_name,
			tweak_collection_name=tweak_collection_name,
			tweak_relationship=options.tweak_relationship,
		)
		tweak.edit_mode(armature_data, chain)
		processed_chains.append(tweak)

		# ROTATION ISOLATION
		if options.add_rotation_isolation and options.do_create_fk:
			property_name = generate_property_name(prefs.rotation_isolation_property_template, options.limb_property_base_name, side)
			rotation_isolation = RotationIsolation(property_name=property_name, mch_collection_name=mch_collection_name)
			rotation_isolation.edit_mode(context, armature_data, [tweak.fk_bone_names[0]])
			rotation_isolation_chains.append(rotation_isolation)

		# ROTATION FOLLOW
		if options.create_rotation_follow_setup and tweak.fk_bone_names:
			follow_bones = tweak.fk_bone_names[options.rotation_follow_skip:]
			if follow_bones:
				follow = RotationFollow(relationship=options.rotation_follow_relationship, mch_collection_name=mch_collection_name)
				follow.edit_mode(context, follow_bones)
				rotation_follow_chains.append(follow)

	##############
	# Pose mode
	##############
	for chain in processed_chains:
		chain.pose_mode(context)

	for rotation_isolation in rotation_isolation_chains:
		rotation_isolation.pose_mode(context)

	for follow in rotation_follow_chains:
		follow.pose_mode(context)