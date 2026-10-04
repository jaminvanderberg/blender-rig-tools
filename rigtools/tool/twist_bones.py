from typing import List
import math
from dataclasses import dataclass

import bpy

from rigtools.preferences import get_preferences
from rigtools.tool.fk_tweak_chain import FKTweakChain
from rigtools.twist_bones import get_twist_chain, set_twist_parent, prune_twist_map
from rigtools.utils.bone import duplicate_bone, duplicate_bone_subdivided
from rigtools.utils.naming import generate_bone_name

def _linear(t):  return 1.0 - t
def _smooth(t): return 1.0 - (3.0 * t*t - 2.0 * t*t*t)
def _round(t):  return math.sqrt(max(0.0, 1.0 - t*t))
def _root(t):   return 1.0 - math.sqrt(t)
def _sharp(t):  return (1.0 - t) ** 2

FALLOFF = {
	"LINEAR": _linear,
	"SMOOTH": _smooth,
	"ROUND": _round,
	"ROOT": _root,
	"SHARP": _sharp,
}

falloff_presets = [
	('LINEAR', "Linear", "Linear falloff", 'IPO_LINEAR', 0),
	('SMOOTH', "Smooth", "Smooth falloff", 'SMOOTHCURVE', 1),
	('ROUND', "Round", "Round falloff", 'SPHERECURVE', 2),
	('ROOT', "Root", "Root falloff", 'ROOTCURVE', 3),
	('SHARP', "Sharp", "Sharp falloff", 'SHARPCURVE', 4),
]

twist_source_types = [
	('SELF', "Self", "Inherit twist from own control bone (like upper arm/thigh)"),
	('CHILD', "Child", "Inherit twist from child bone (like hand > forearm)"),
	('NONE', "None", "Twist deform bones only; no copy-rotation falloff"),
]

def twist_influence(preset: str, index: int, count: int, reverse: bool = True) -> float:
	i = index if not reverse else count - index - 1
	if count < 2:
		raise ValueError("twist_bone_count must be >= 2")
	fn = FALLOFF[preset]
	return fn(i / count)

@dataclass
class TwistSegment:
	index: int
	source: str
	falloff: str = 'LINEAR'
	name: str = ''

def consecutive_index_groups(indexes):
	indexes = sorted(indexes)
	groups = []
	for idx in indexes:
		if groups and idx == groups[-1][-1] + 1:
			groups[-1].append(idx)
		else:
			groups.append([idx])
	return groups

class TwistBones:
	def __init__(self, *,
		segments: List[TwistSegment],
		twist_bone_count: int,
		twist_parent_name: str = "",
		tweak_collection_name: str = "",
		tweak_relationship: str = 'STRETCH_TO'
	):
		if twist_bone_count < 2:
			raise ValueError("twist_bone_count must be >= 2")

		self.segments = segments
		self.twist_bone_count = twist_bone_count
		self.tweak_collection_name = tweak_collection_name
		self.tweak_relationship = tweak_relationship
		self.twist_parent_name = twist_parent_name

		self.driver_bone_names = None

		self.mechanism_bone_names = []
		self.property_names = []
		self.object_names = []

		self.twist_bones = {}
		self.tweak_chains = []
		self.isolator_names = {}
		self.twist_states = []

	def edit_mode(self, context, org_bone_names, driver_bone_names):
		obj = context.object
		edit_bones = obj.data.edit_bones
		prefs = get_preferences()

		self.driver_bone_names = driver_bone_names

		if obj.mode != 'EDIT':
			bpy.ops.object.mode_set(mode='EDIT')

		prune_twist_map(obj.data, use_edit_bones=True)

		self.twist_bones = {}
		for segment in self.segments:
			org_bone = edit_bones[org_bone_names[segment.index]]

			print(f"Checking twist chain for {org_bone.name}")
			twist_names = get_twist_chain(obj.data, org_bone.name, use_edit_bones=True)
			print(f"Twist names: {twist_names}")
			if not twist_names:
				twist_names = duplicate_bone_subdivided(
					context, org_bone, self.twist_bone_count, prefs.twist_template
				)
				for twist_name in twist_names:
					set_twist_parent(obj.data, twist_name, org_bone.name)
			elif len(twist_names) != self.twist_bone_count:
				raise ValueError(
					f"Twist chain for {org_bone.name} must have {self.twist_bone_count} bones"
				)

			self.twist_bones[segment.index] = twist_names

			for twist_name in twist_names:
				b = edit_bones[twist_name]
				self.twist_states.append({
					"name": b.name,
					"parent": b.parent.name if b.parent else "",
					"use_connect": b.use_connect
				})

			# Isolate twist for self-parented segments
			if segment.source != 'SELF': continue
			switch_bone = edit_bones[driver_bone_names[segment.index]]

			isolator_name = generate_bone_name(org_bone.name, prefs.twist_isolator_template)
			isolator = duplicate_bone(obj.data, switch_bone, isolator_name, scale=0.31)
			isolator.parent = (
				edit_bones[self.twist_parent_name] if segment.index == 0 and self.twist_parent_name
				else switch_bone.parent
			)

			# Parent the first BIG tweak bone (org parent) to the isolator
			first_tweak = org_bone.parent
			first_tweak.parent = isolator

			self.isolator_names[segment.index] = isolator.name
			self.mechanism_bone_names.append(isolator.name)

		n = self.twist_bone_count
		for group in consecutive_index_groups(self.twist_bones.keys()):
			flat = [name for idx in group for name in self.twist_bones[idx]]
			# group = [0, 1], flat = all twist names in group
			
			# Parent the start of each group to the end of the previous group
			for i in range(n, n * len(group), n):
				edit_bones[flat[i]].parent = edit_bones[flat[i-1]]

			tweak = FKTweakChain(
				do_create_fk=False,
				tweak_collection_name=self.tweak_collection_name,
				tweak_relationship=self.tweak_relationship,
			)
			tweak.edit_mode(obj.data, flat)
			self.tweak_chains.append(tweak)

			for i in range(len(group)):
				parent_bone = edit_bones[org_bone_names[group[i]]]
				for j in range(n):
					tweak_bone_name = tweak.tweak_bone_names[i * self.twist_bone_count + j]
					tweak_bone = edit_bones[tweak_bone_name]
					tweak_bone.parent = parent_bone

			# Set the proper parent for the terminal tweak bone
			last_idx = group[-1]
			next_idx = last_idx + 1
			if next_idx < len(org_bone_names):
				next_org = edit_bones[org_bone_names[next_idx]] # hand/foot, etc.
				big_tweak = next_org.parent
				tiny_tip = edit_bones[tweak.terminal_tweak_name]
				tiny_tip.parent = big_tweak
				next_org.parent = tiny_tip
			else:
				# parent to the last org bone
				edit_bones[tweak.terminal_tweak_name].parent = edit_bones[org_bone_names[group[-1]]]

			self.mechanism_bone_names.extend(tweak.mechanism_bone_names)
			self.property_names.extend(tweak.property_names)

		return self

	def pose_mode(self, context):
		for tweak in self.tweak_chains:
			tweak.pose_mode(context)
			self.object_names.extend(tweak.object_names)

		pose_bones = context.object.pose.bones

		# Twist isolators
		for index, isolator_name in self.isolator_names.items():
			isolator = pose_bones[isolator_name]
			switch_name = self.driver_bone_names[index]

			loc = isolator.constraints.new('COPY_LOCATION')
			loc.target = context.object
			loc.subtarget = switch_name

			track = isolator.constraints.new('DAMPED_TRACK')
			track.target = context.object
			track.subtarget = switch_name
			track.head_tail = 1.0 # Aim at tail of switch bone

		# Rotation falloff
		for segment in self.segments:
			for i in range(self.twist_bone_count):
				twist_bone_name = self.twist_bones[segment.index][i]
				twist_bone = pose_bones[twist_bone_name]

				if segment.source == 'NONE':
					continue
				elif segment.source == 'SELF':
					driver_bone_name = self.driver_bone_names[segment.index]
				elif segment.source == 'CHILD':
					driver_bone_name = self.driver_bone_names[segment.index + 1]
				else:
					raise ValueError(f"Unknown twist source '{segment.source}'")

				copyrot_constraint = twist_bone.constraints.new('COPY_ROTATION')
				copyrot_constraint.target = context.object
				copyrot_constraint.subtarget = driver_bone_name
				copyrot_constraint.target_space = 'WORLD'
				copyrot_constraint.owner_space = 'WORLD'					
				copyrot_constraint.influence = twist_influence(segment.falloff, i, self.twist_bone_count, reverse=True)				

				# Move to the first position
				twist_bone.constraints.move(len(twist_bone.constraints) - 1, 0)
		
		return self
