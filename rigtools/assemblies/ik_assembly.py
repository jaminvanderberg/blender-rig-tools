from dataclasses import dataclass, field
from typing import List

from rigtools.utils.bone import find_side
from rigtools.utils.bone_collection import generate_bone_collection_name
from rigtools.utils.property import generate_property_name
from rigtools.preferences import get_preferences

# Tools
from rigtools.tool.fk_tweak_chain import FKTweakChain
from rigtools.tool.fk_ik_switch import FKIKSwitch
from rigtools.tool.rotation_isolation import RotationIsolation
from rigtools.tool.standard_ik import StandardIK
from rigtools.tool.spline_ik import SplineIK
from rigtools.tool.ik_parent import IKParent, IKParentTarget

@dataclass
class IKAssemblyOptions:
	limb_property_base_name: str
	add_tweak_bones: bool
	switch_property_type: str
	add_rotation_isolation: bool = True
	override_collections: bool = True
	ik_type: str = 'IK' # 'IK' or 'SPLINE'
	enable_ik_stretch: bool = True
	pole_distance: float = 1.0
	spline_control_count: int = 3
	spline_skip_first: bool = False
	twist_type: str = 'START_END' # spline_ik.spline_twist_type
	tweak_relationship: str = 'STRETCH_TO' # 'STRETCH_TO' or 'DAMPED_TRACK'
	fk_widget: str = 'FK' # 'widget.fk_widget_types
	enable_snapping: bool = True
	ik_parent: bool = True
	ik_parents: List[IKParentTarget] = field(default_factory=list)
	add_ik_control_as_pole_parent: bool = False
	ik_parent_self_parent_label: str = 'Foot'

def create_ik_assembly(context, chains, options: IKAssemblyOptions):
	"""find_side() throws an error if the side is not the same for all bones in the chain"""

	prefs = get_preferences()
	
	armature_data = context.object.data

	switch_chains = []
	tweak_chains = []
	ik_chains = []
	ik_parents = []
	rotation_isolation_chains = []
	##############
	# Edit mode
	##############
	for chain in chains:
		org_chain = chain
		side = find_side(chain)

		ik_collection_name = generate_bone_collection_name(prefs.ik_collection_template, options.limb_property_base_name, side)
		tweak_collection_name = generate_bone_collection_name(prefs.tweak_collection_template, options.limb_property_base_name, side)
		fk_collection_name = generate_bone_collection_name(prefs.fk_collection_template, options.limb_property_base_name, side)
		mch_collection_name = generate_bone_collection_name(prefs.mch_collection_template, options.limb_property_base_name, side)

		# TWEAK CHAIN
		if options.add_tweak_bones:
			tweak_chain = FKTweakChain(
				tweak_relationship = options.tweak_relationship,
				tweak_collection_name = tweak_collection_name if options.override_collections else None,
				fk_collection_name = mch_collection_name if options.override_collections else None,

				# Hard-coded options
				fk_bone_template = prefs.switch_template,
				fk_widget = "NONE",  # this is an intermediate chain, no widget
				skip_first_tweak = False,
				do_create_fk = True,
			)
			tweak_chain.edit_mode(armature_data, chain)
			chain = tweak_chain.fk_bone_names
			tweak_chains.append(tweak_chain)

		# FK/IK SWITCH
		switch_property_name = generate_property_name(prefs.fk_ik_switch_property_template, options.limb_property_base_name, side)
		fk_ik_switch = FKIKSwitch(
			switch_property_name = switch_property_name,
			switch_property_type = options.switch_property_type,
			fk_widget_type = options.fk_widget,
			fk_collection_name = fk_collection_name if options.override_collections else None,
			mch_collection_name = mch_collection_name if options.override_collections else None,
		)
		fk_ik_switch.edit_mode(context, chain, name_source = org_chain)
		fk_bone_names, ik_bone_names = fk_ik_switch.fk_bone_names, fk_ik_switch.ik_bone_names
		switch_chains.append(fk_ik_switch)

		# ROTATION ISOLATION
		if options.add_rotation_isolation:
			rotation_isolation = RotationIsolation(
				property_name = generate_property_name(prefs.rotation_isolation_property_template, options.limb_property_base_name, side),
				mch_collection_name = mch_collection_name if options.override_collections else None,

				# Hard-coded options
				include_scale = True,
				disable_scale = False,
			)
			rotation_isolation.edit_mode(context, armature_data, [fk_bone_names[0]])
			rotation_isolation_chains.append(rotation_isolation)

		# IK
		if options.ik_type == 'IK':
			ik = StandardIK(
				enable_ik_stretch = options.enable_ik_stretch,
				pole_distance = options.pole_distance,
				ik_collection_name = ik_collection_name if options.override_collections else None,
				enable_snapping = options.enable_snapping,
				mch_collection_name = mch_collection_name if options.override_collections else None,
			)
			ik.edit_mode(context, ik_bone_names, fk_bone_names, name_source=org_chain)
			ik_chains.append(ik)

			if options.enable_snapping:
				ik.register_snap_chain(context, switch_property_name)
		# SPLINE IK
		elif options.ik_type == 'SPLINE':
			spline_ik = SplineIK(
				control_count = options.spline_control_count,
				skip_first = options.spline_skip_first,
				ik_collection_name = ik_collection_name if options.override_collections else None,
				twist_type = options.twist_type,
			)
			spline_ik.edit_mode(context, ik_bone_names, name_source=org_chain)
			ik_chains.append(spline_ik)

		# IK PARENT
		if options.ik_parent:
			ik_parent = IKParent(
				property_name = generate_property_name(prefs.ik_parent_property_template, options.limb_property_base_name, side),
				parents = options.ik_parents,
				self_parent_label = options.ik_parent_self_parent_label,
				mch_collection_name = mch_collection_name if options.override_collections else None
			)
			if options.ik_type == 'IK':
				bones_to_parent = [ik.ik_control_name, ik.pole_name]
				self_target = ik.ik_control_name
			else: #SPLINE
				bones_to_parent = spline_ik.control_names
				self_target = spline_ik.control_names[0]
			ik_parent.edit_mode(context, bones_to_parent, self_target)
			ik_parents.append(ik_parent)

	##############
	# Object mode
	##############
	if options.ik_type == 'SPLINE':
		for ik_chain in ik_chains:
			ik_chain.object_mode(context)

	##############
	# Pose mode
	##############
	for tweak_chain in tweak_chains:
		tweak_chain.pose_mode(context)

	for fk_ik_switch in switch_chains:
		fk_ik_switch.pose_mode(context)

	for rotation_isolation_chain in rotation_isolation_chains:
		rotation_isolation_chain.pose_mode(context)

	for ik_chain in ik_chains:
		ik_chain.pose_mode(context)

	for ik_parent in ik_parents:
		self_parent_mch = (
			ik_parent.parent_bone_names[1] # pole parent
			if options.ik_type == 'IK' and options.add_ik_control_as_pole_parent 
			else None
		)
		ik_parent.pose_mode(context, self_parent_mch)