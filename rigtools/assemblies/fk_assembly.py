from dataclasses import dataclass, field

from rigtools.assemblies.assembly_data import AssemblyChain, create_assembly_data, find_assembly
from rigtools.tool.fk_chain import FKChain
from rigtools.tool.master_controllers import MasterControllers
from rigtools.tool.skirt_collision import SkirtCollision
from rigtools.tool.skirt_ride import SkirtLeg, SkirtRide
from rigtools.utils.naming import guess_assembly_name, find_side, name_collection, name_property
from rigtools.utils.bone_collection import ensure_bone_collection
from rigtools.preferences import get_preferences
from rigtools.tool.fk_tweak_chain import FKTweakChain
from rigtools.tool.rotation_isolation import RotationIsolation


@dataclass
class FKAssemblyOptions:
	limb_property_base_name: str
	control_mode: str = 'FK/TWEAK' # 'FK/TWEAK', 'FK', 'TWEAK'
	fk_bone_template: str = "FK-{name}"
	skip_first_tweak: bool = False
	fk_widget: str = 'CIRCLE'
	fk_collection_name: str = '' # This will override the default
	tweak_collection_name: str = '' # This will override the default
	tweak_relationship: str = 'STRETCH_TO'
	add_rotation_isolation: bool = True
	override_collections: bool = True
	add_skirt_collision: bool = False
	skirt_collision_target_bone_names: list[str] = field(default_factory=list)
	add_skirt_ride: bool = False
	skirt_ride_legs: list[SkirtLeg] = field(default_factory=list)

	create_master_controllers: bool = False
	master_controllers_interval: int = 0
	master_controllers_skip_first: bool = False
	master_controllers_type: str = 'FK' # or 'MASTER'
	master_controllers_widget: str = 'CIRCLE'

def create_fk_assembly(context, chains: list[list[str]], template_id, template_name, options: FKAssemblyOptions, replacement_uid=None, prior_configs=None):
	armature_data = context.object.data
	original_mirror = armature_data.use_mirror_x
	armature_data.use_mirror_x = False
	prior_configs = prior_configs or {}

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
			master_controllers_collection_name = name_collection("fk_master", options.limb_property_base_name, side)

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

			# MASTER CONTROLLERS
			if options.create_master_controllers and len(fk_names) > 0:
				master_controllers = MasterControllers(
					interval=options.master_controllers_interval,
					skip_first=options.master_controllers_skip_first,
					master_controller_type=options.master_controllers_type,
					mch_collection_name=mch_collection_name,
					master_controller_collection_name=master_controllers_collection_name,
					master_controller_widget=options.master_controllers_widget,
				)
				master_controllers.edit_mode(context, fk_names, name_source=chain)
				assembly_chain.tools.append(master_controllers)

			# SKIRT COLLISION
			if options.add_skirt_collision and len(fk_names) > 0:
				property_name = name_property("skirt_collision", options.limb_property_base_name, side)
				skirt_collision = SkirtCollision(
					property_name=property_name,
					target_bone_names=options.skirt_collision_target_bone_names,
					mch_bone_collection_name=mch_collection_name,
					prior_configs=prior_configs,
				)
				skirt_collision.edit_mode(context, fk_names)
				assembly_chain.tools.append(skirt_collision)

			# SKIRT RIDE
			if options.add_skirt_ride and len(fk_names) > 0:
				property_name = name_property("skirt_ride", options.limb_property_base_name, side)
				skirt_ride = SkirtRide(
					property_name=property_name,
					legs=options.skirt_ride_legs,
					mch_bone_collection_name=mch_collection_name,
					prior_configs=prior_configs
				)
				skirt_ride.edit_mode(context, fk_names[0])
				assembly_chain.tools.append(skirt_ride)

		##############
		# Pose mode
		##############
		for assembly_chain in assemblies:
			assembly = find_assembly(context.object, assembly_chain.assembly_uid)
			for tool in assembly_chain.tools:
				tool.pose_mode(context)
				assembly.apply_tool(tool)

				save_config = getattr(tool, 'save_config', None)
				if callable(save_config):
					save_config(assembly)
				
	finally:
		armature_data.use_mirror_x = original_mirror

		select_bones = []
		if fk_names:
			select_bones.append(fk_names[0])
		else:
			name = next((n for n in tweak.tweak_bone_names if n), None) or tweak.terminal_tweak_name
			select_bones.append(name)

		return select_bones
