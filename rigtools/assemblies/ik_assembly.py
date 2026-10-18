from dataclasses import dataclass, field
from typing import List

from rigtools.assemblies.assembly_data import AssemblyChain, create_assembly_data, find_assembly
from rigtools.assemblies.limb_collections import ensure_limb_collections
from rigtools.heel_pivots import get_heel_pivot
from rigtools.tool.fk_chain import FKChain
from rigtools.tool.foot_roll import FootRoll
from rigtools.utils.naming import bone_template, guess_assembly_name, find_side, name_property
from rigtools.utils.bone_collection import add_bone_collection
from rigtools.tool.twist_bones import TwistBones, TwistSegment

# Tools
from rigtools.tool.fk_tweak_chain import FKTweakChain
from rigtools.tool.fk_ik_switch import FKIKSwitch
from rigtools.tool.master_controllers import MasterControllers
from rigtools.tool.rotation_isolation import RotationIsolation
from rigtools.tool.standard_ik import StandardIK
from rigtools.tool.spline_ik import SplineIK
from rigtools.tool.ik_parent import IKParent, IKParentTarget
from rigtools.tool.skirt_collision import SkirtCollision
from rigtools.tool.skirt_ride import SkirtLeg, SkirtRide

@dataclass
class IKAssemblyOptions:
	limb_property_base_name: str
	add_tweak_bones: bool
	limb_type: str = ""
	add_rotation_isolation: bool = True
	inherit_scale_from_root: bool = False
	ik_type: str = 'IK' # 'IK' or 'SPLINE'
	ik_bone_count: int = 3
	enable_ik_stretch: bool = True
	pole_distance: float = 1.0
	spline_control_count: int = 3
	spline_skip_first: bool = False
	spline_skip_last: bool = False
	twist_type: str = 'START_END' # spline_ik.spline_twist_type
	tweak_relationship: str = 'STRETCH_TO' # 'STRETCH_TO' or 'DAMPED_TRACK'
	fk_widget: str = 'FK' # 'widget.fk_widget_types
	enable_snapping: bool = True
	tip_widget: str = 'CIRCLE'
	fk_end_widget: str = 'SAME'

	add_foot_roll: bool = False

	ik_parent: bool = True
	ik_parents: List[IKParentTarget] = field(default_factory=list)
	add_ik_control_as_pole_parent: bool = False
	ik_parent_self_parent_label: str = 'Self'

	use_twist_bones: bool = False
	twist_segments: List[TwistSegment] = field(default_factory=list)
	twist_bone_count: int = 4

	add_skirt_collision: bool = False
	skirt_collision_target_bone_names: list[str] = field(default_factory=list)
	add_skirt_ride: bool = False
	skirt_ride_legs: list[SkirtLeg] = field(default_factory=list)

	create_master_controllers: bool = False
	master_controllers_interval: int = 0
	master_controllers_skip_first: bool = False
	master_controllers_type: str = 'FK' # or 'MASTER'
	master_controllers_widget: str = 'CIRCLE'


def create_ik_assembly(context, chains, template_id, template_name, options: IKAssemblyOptions, replacement_uid=None, prior_configs=None):
	"""find_side() throws an error if the side is not the same for all bones in the chain"""

	armature_data = context.object.data
	original_mirror = armature_data.use_mirror_x
	armature_data.use_mirror_x = False
	edit_bones = armature_data.edit_bones
	prior_configs = prior_configs or {}

	assemblies = []
	tip_controls = []
	try:
		##############
		# Edit mode
		##############
		for chain in chains:

			org_chain = chain
			limb = options.limb_property_base_name
			side = find_side(chain)

			limb_collections = ensure_limb_collections(armature_data, limb, side, promote=True)

			assembly_name = guess_assembly_name(context.object.data, chain, limb, side)
			assembly = create_assembly_data(context.object, chain, assembly_name, "IK", template_id, template_name, options, side=side, uid=replacement_uid)
			assembly_chain = AssemblyChain(assembly_uid=assembly.uid, tools=[], limb_collections=limb_collections)
			assemblies.append(assembly_chain)

			if options.ik_type == 'IK':
				limb_count = options.ik_bone_count
			else:
				limb_count = len(chain) - (1 if options.spline_skip_last else 0)
			limb_chain = chain[:limb_count]
			fk_tip = chain[limb_count:]

			# TWEAK CHAIN
			if options.add_tweak_bones:
				tweak_chain = FKTweakChain(
					tweak_relationship = options.tweak_relationship,

					# Hard-coded options
					fk_role = 'mch',
					fk_bone_template = bone_template("switch"),
					fk_widget = "NONE",  # this is an intermediate chain, no widget
					skip_first_tweak = False,
					do_create_fk = True,
				)
				tweak_chain.edit_mode(armature_data, limb_chain)
				switch_chain = tweak_chain.fk_bone_names
				assembly_chain.tools.append(tweak_chain)
			else:
				switch_chain = limb_chain

			# END OF CHAIN FK
			if len(fk_tip) > 0:
				tip_fk = FKChain(
					fk_bone_template = bone_template("control"),
					fk_widget = options.tip_widget,
					fk_role = ['fk', 'ik']
				)
				tip_fk.edit_mode(armature_data, fk_tip)
				assembly_chain.tools.append(tip_fk)

			# FK/IK SWITCH
			switch_property_name = name_property("fk_ik_switch", options.limb_property_base_name, side)
			fk_ik_switch = FKIKSwitch(
				switch_property_name = switch_property_name,
				fk_widget_type = options.fk_widget,
				fk_end_widget_type = options.fk_end_widget,
			)
			fk_ik_switch.edit_mode(context, switch_chain, name_source = org_chain)
			fk_bone_names, ik_bone_names = fk_ik_switch.fk_bone_names, fk_ik_switch.ik_bone_names
			assembly_chain.tools.append(fk_ik_switch)

			# ROTATION ISOLATION
			if options.add_rotation_isolation:
				rotation_isolation = RotationIsolation(
					property_name = name_property("rotation_isolation", options.limb_property_base_name, side),
					inherit_scale_from_root = options.inherit_scale_from_root,

					# Hard-coded options
					include_scale = True,
					disable_scale = False,
				)
				rotation_isolation.edit_mode(context, armature_data, [fk_bone_names[0]])
				assembly_chain.tools.append(rotation_isolation)
				twist_parent_name = rotation_isolation.created_bones[0][0] # SOCKET
			else:
				twist_parent_name = None # will inherit ORG parent

			# MASTER CONTROLLERS (limb FK only - not tip/toe chain)
			if options.create_master_controllers and len(fk_bone_names) > 0:
				master_controllers = MasterControllers(
					interval=options.master_controllers_interval,
					skip_first=options.master_controllers_skip_first,
					master_controller_type=options.master_controllers_type,
					master_controller_widget=options.master_controllers_widget,
				)
				master_controllers.edit_mode(context, fk_bone_names, name_source=org_chain[:limb_count])
				assembly_chain.tools.append(master_controllers)

			# SKIRT COLLISION (FK mode only)
			if options.add_skirt_collision and len(fk_bone_names) > 0:
				property_name = name_property("skirt_collision", options.limb_property_base_name, side)
				skirt_collision = SkirtCollision(
					property_name=property_name,
					target_bone_names=options.skirt_collision_target_bone_names,
					prior_configs=prior_configs,
				)
				skirt_collision.edit_mode(context, fk_bone_names)
				assembly_chain.tools.append(skirt_collision)

			# SKIRT RIDE (FK mode only)
			if options.add_skirt_ride and len(fk_bone_names) > 0:
				property_name = name_property("skirt_ride", options.limb_property_base_name, side)
				skirt_ride = SkirtRide(
					property_name=property_name,
					legs=options.skirt_ride_legs,
					prior_configs=prior_configs,
				)
				skirt_ride.edit_mode(context, fk_bone_names[0])
				assembly_chain.tools.append(skirt_ride)

			# IK
			if options.ik_type == 'IK':
				if options.use_twist_bones:
					twist_bones = TwistBones(
						segments = options.twist_segments,
						twist_bone_count = options.twist_bone_count,
						twist_parent_name = twist_parent_name,
						tweak_relationship = options.tweak_relationship,
						add_tweak_bones = options.add_tweak_bones,
					)
					twist_bones.edit_mode(context, limb_chain, fk_ik_switch.switch_bone_names)
					assembly_chain.tools.append(twist_bones)

				ik = StandardIK(
					enable_ik_stretch = options.enable_ik_stretch,
					pole_distance = options.pole_distance,
					enable_snapping = options.enable_snapping,
				)
				tweak_bone_names = tweak_chain.tweak_bone_names if options.add_tweak_bones else None
				ik.edit_mode(context, ik_bone_names[:limb_count], fk_bone_names[:limb_count], tweak_bone_names, name_source=org_chain[:limb_count])
				assembly_chain.tools.append(ik)
				tip_controls.append(ik.ik_control_name)

				if options.enable_snapping:
					ik.register_snap_chain(context, switch_property_name)

				if options.add_foot_roll:
					heel_pivot_name = get_heel_pivot(context.object.data, org_chain[limb_count - 1])
					foot_roll = FootRoll()
					foot_roll.edit_mode(context, 
						mch_ik_foot_name = ik_bone_names[limb_count - 1],
						ik_foot_name = ik.ik_control_name,
						heel_pivot_name = heel_pivot_name,
						org_toe_name = tip_fk.fk_bone_names[0],
					)
					assembly_chain.tools.append(foot_roll)
			# SPLINE IK
			elif options.ik_type == 'SPLINE':
				spline_ik = SplineIK(
					control_count = options.spline_control_count,
					skip_first = options.spline_skip_first,
					twist_type = options.twist_type,
				)
				spline_ik.edit_mode(context, ik_bone_names, name_source=org_chain)
				assembly_chain.tools.append(spline_ik)
				tip_controls.append(spline_ik.control_names[-1])

			# IK PARENT
			if options.ik_parent:
				ik_parent = IKParent(
					property_name = name_property("ik_parent", options.limb_property_base_name, side),
					parents = options.ik_parents,
					self_parent_label = options.ik_parent_self_parent_label,
					add_ik_control_as_pole_parent = options.add_ik_control_as_pole_parent if options.ik_type == 'IK' else False,
				)
				if options.ik_type == 'IK':
					bones_to_parent = [ik.ik_control_name, ik.pole_name]
					self_target = ik.ik_control_name
				else: #SPLINE
					bones_to_parent = spline_ik.control_names
					self_target = spline_ik.control_names[0]
				ik_parent.edit_mode(context, bones_to_parent, self_target)
				assembly_chain.tools.append(ik_parent)

		##############
		# Object mode
		##############
		for assembly_chain in assemblies:
			for tool in assembly_chain.tools:
				object_mode = getattr(tool, 'object_mode', None)
				if callable(object_mode):
					object_mode(context)

		##############
		# Pose mode
		##############
		for assembly_chain in assemblies:
			assembly = find_assembly(context.object, assembly_chain.assembly_uid)
			for tool in assembly_chain.tools:
				tool.pose_mode(context)
				assembly.apply_tool(armature_data, tool, assembly_chain.limb_collections)

				save_config = getattr(tool, 'save_config', None)
				if callable(save_config):
					save_config(assembly)

	finally:
		armature_data.use_mirror_x = original_mirror

	return tip_controls
