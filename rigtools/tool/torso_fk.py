import math
import bpy
from mathutils import Vector
from rigtools.armature_settings import get_armature_settings
from rigtools.preferences import get_preferences
from rigtools.tool.fk_tweak_chain import FKTweakChain
from rigtools.tool.twist_bones import twist_influence
from rigtools.twist_bones import get_twist_chain, set_twist_parent
from rigtools.utils.bone import duplicate_bone, duplicate_bone_subdivided, generate_mch_bones, match_orientation
from rigtools.utils.naming import generate_bone_name
from rigtools.utils.bone_collection import set_bone_collection
from rigtools.utils.bone_chain import get_length_weighted_midpoint
from rigtools.utils.widget import create_box_widget, create_chest_widget, create_fk_widget, get_widget_collection
    
class TorsoFK:
	def __init__(self, *,
		fk_widget: str = "CIRCLE",
		lower_torso_bone_count: int,
		neck_bone_count: int,
		add_tweak_bones: bool = True,
		tweak_relationship: str = "STRETCH_TO",
		neck_twist_bone_count: int,
		chest_twist_bone_count: int,
		tweak_collection_name: str = "",
		control_collection_name: str = "",
		fk_collection_name: str = "",
		mch_collection_name: str = "",
		add_neck_rotation_isolation: bool = True,
		neck_falloff_type: str = "ROOT",
	):
		self.fk_widget = fk_widget
		self.neck_bone_count = neck_bone_count
		self.neck_twist_bone_count = neck_twist_bone_count
		self.chest_twist_bone_count = chest_twist_bone_count
		self.lower_torso_bone_count = lower_torso_bone_count
		self.add_tweak_bones = add_tweak_bones
		self.tweak_relationship = tweak_relationship
		self.control_collection_name = control_collection_name
		self.tweak_collection_name = tweak_collection_name
		self.fk_collection_name = fk_collection_name
		self.mch_collection_name = mch_collection_name
		self.add_neck_rotation_isolation = add_neck_rotation_isolation
		self.neck_falloff_type = neck_falloff_type

		self.tweak_chain = None
		self.fk_bone_names = []

		self.mechanism_bone_names = []
		self.property_names = []
		self.object_names = []

		self.twist_bones = {}
		self.twist_states = []

		self.torso_bone_name = None
		self.hip_bone_name = None
		self.chest_bone_name = None

		self.twist_isolator_name = None
		self.middle_torso_mch_name = None
		self.neck_org_names = []

		self.hips_mch_names = []
		self.chest_mch_names = []

	def edit_mode(self, context, org_bone_names):
		self.org_bone_names = org_bone_names

		obj = context.object
		armature_data = obj.data
		
		prefs = get_preferences()
		bpy.ops.object.mode_set(mode='EDIT')
		settings = get_armature_settings(armature_data, context)

		edit_bones = armature_data.edit_bones

		# Torso controller
		torso_names = org_bone_names[:-self.neck_bone_count - 1]
		torso_position = get_length_weighted_midpoint(context, torso_names)
		torso_length = sum(edit_bones[name].length for name in torso_names) / len(torso_names) * 2.0
		torso_bone = edit_bones.new(settings.torso_bone_name)
		torso_bone.head = torso_position
		y = obj.matrix_world.inverted().to_3x3() @ Vector((0.0, 1.0, 0.0))
		torso_bone.tail = torso_position + y.normalized() * torso_length
		torso_bone.roll = 0.0
		torso_bone.parent = edit_bones[settings.root_bone_name]

		if self.control_collection_name:
			set_bone_collection(armature_data, torso_bone, self.control_collection_name)

		waist_position = edit_bones[org_bone_names[self.lower_torso_bone_count]].head
		
		first_neck_bone_index = len(org_bone_names) - self.neck_bone_count - 1
		chest_bone_index = len(org_bone_names) - self.neck_bone_count - 2
		lower_torso_index = self.lower_torso_bone_count - 1
		upper_torso_index = self.lower_torso_bone_count

		self.torso_bone_name = torso_bone.name
		self.mechanism_bone_names.append(torso_bone.name)

		# Hips controller
		hip_bone = duplicate_bone(armature_data, torso_bone, settings.hips_bone_name, 1.0)
		hip_bone.head = waist_position
		hip_bone.tail = waist_position + y.normalized() * torso_length * 0.6
		hip_bone.parent = torso_bone

		self.hip_bone_name = hip_bone.name
		self.mechanism_bone_names.append(hip_bone.name)

		# Chest controller
		chest_bone = duplicate_bone(armature_data, torso_bone, settings.chest_bone_name, 1.0)
		chest_bone.head = waist_position
		chest_bone.tail = waist_position + y.normalized() * torso_length * 0.7
		chest_bone.parent = torso_bone

		self.chest_bone_name = chest_bone.name
		self.mechanism_bone_names.append(chest_bone.name)

		# Neck twist bones
		if self.neck_twist_bone_count > 0:
			for i in range(first_neck_bone_index, len(org_bone_names) - 1):
				twist_names = get_twist_chain(armature_data, org_bone_names[i], use_edit_bones=True)
				org_bone = edit_bones[org_bone_names[i]]
				if not twist_names:
					twist_names = duplicate_bone_subdivided(
						context, org_bone, self.neck_twist_bone_count, prefs.twist_template
					)
					for twist_name in twist_names:
						set_twist_parent(armature_data, twist_name, org_bone_names[i])
				elif len(twist_names) != self.neck_twist_bone_count:
					raise ValueError(
						f"Twist chain for {org_bone_names[i]} must have {self.neck_twist_bone_count} bones"
					)
				self.twist_bones[i] = twist_names

				for twist_name in twist_names:
					b = edit_bones[twist_name]
					self.twist_states.append({
						"name": b.name,
						"parent": b.parent.name if b.parent else "",
						"use_connect": b.use_connect
					})

		# Chest twist bones
		if self.chest_twist_bone_count > 0:
			twist_names = get_twist_chain(armature_data, org_bone_names[chest_bone_index], use_edit_bones=True)
			org_bone = edit_bones[org_bone_names[chest_bone_index]]
			if not twist_names:
				twist_names = duplicate_bone_subdivided(
					context, org_bone, self.chest_twist_bone_count, prefs.twist_template
				)
				for twist_name in twist_names:
					set_twist_parent(armature_data, twist_name, org_bone_names[chest_bone_index])
			elif len(twist_names) != self.chest_twist_bone_count:
				raise ValueError(
					f"Twist chain for {org_bone_names[chest_bone_index]} must have {self.chest_twist_bone_count} bones"
				)

			self.twist_bones[chest_bone_index] = twist_names
			for twist_name in twist_names:
				b = edit_bones[twist_name]
				self.twist_states.append({
					"name": b.name,
					"parent": b.parent.name if b.parent else "",
					"use_connect": b.use_connect
				})

		# Create FK bones
		fk_bones = [] # store locally because we reference them alot during parenting
		for i, org_name in enumerate(org_bone_names):
			org_bone = edit_bones[org_name]

			is_neck_bone = i >= first_neck_bone_index and i < first_neck_bone_index + self.neck_bone_count
			is_head_bone = i == len(org_bone_names) - 1
			if is_neck_bone:
				fk_bone_name = generate_bone_name(org_name, prefs.control_template)
			elif is_head_bone:
				fk_bone_name = settings.head_bone_name
			else:
				fk_bone_name = generate_bone_name(org_name, prefs.fk_template)

			fk_bone = duplicate_bone(armature_data, org_bone, fk_bone_name, 1.0)
			fk_bones.append(fk_bone)

			if  i < self.lower_torso_bone_count:
				offset = fk_bone.tail - fk_bone.head
				fk_bone.head += offset
				fk_bone.tail += offset

			self.fk_bone_names.append(fk_bone.name)

			if self.fk_collection_name and not (is_head_bone or is_neck_bone):
				set_bone_collection(armature_data, fk_bone, self.fk_collection_name)
			if self.control_collection_name and (is_neck_bone or is_head_bone):
				set_bone_collection(armature_data, fk_bone, self.control_collection_name)

			self.mechanism_bone_names.append(fk_bone.name)

		# Parent the FK bones in two sections: lower torso and upper torso
		for fk_bone in fk_bones:
			# Clear the parent first to avoid any circular dependencies
			fk_bone.parent = None

		for i in range(lower_torso_index): # skip spine.1
			fk_bones[i].parent = fk_bones[i + 1]
		for i in range(upper_torso_index + 1, len(fk_bones)): # skip spine.2
			fk_bones[i].parent = fk_bones[i - 1]

		fk_bones[lower_torso_index].parent = torso_bone
		fk_bones[upper_torso_index].parent = torso_bone

		# Prepare to create tweak chain
		source_names = []
		tweak_parents = []
		for i, org_name in enumerate(org_bone_names):
			if i == 0:
				parent_index = 0
			elif i <= self.lower_torso_bone_count:
				parent_index = i - 1
			else:
				parent_index = i

			if i == first_neck_bone_index:
				first_neck_tweak_index = len(source_names)

			is_neck_bone = i >= first_neck_bone_index and i < first_neck_bone_index + self.neck_bone_count

			if i not in self.twist_bones:
				source_names.append(org_name)
				tweak_parents.append(self.fk_bone_names[parent_index])
				if is_neck_bone:
					self.neck_org_names.append(org_name)
				continue

			twist_names = self.twist_bones[i]
			source_names.extend(twist_names)
			if is_neck_bone:
				self.neck_org_names.extend(twist_names)

			tweak_parents.append(self.fk_bone_names[parent_index])
			tweak_parents.extend([org_name] * (len(twist_names) - 1))

		# Create the tweak chain
		if self.add_tweak_bones:
			self.tweak_chain = FKTweakChain(
				do_create_fk=False,
				tweak_relationship=self.tweak_relationship,
				tweak_collection_name=self.tweak_collection_name,
				tweak_scale=0.40
			).edit_mode(armature_data, source_names)

		# Parent the tweak bones to the fk bones
		if self.add_tweak_bones:
			for tweak_name, parent in zip(self.tweak_chain.tweak_bone_names, tweak_parents, strict=True):
				edit_bones[tweak_name].parent = edit_bones[parent]

			edit_bones[self.tweak_chain.terminal_tweak_name].parent = edit_bones[self.fk_bone_names[-1]]
		
		if self.tweak_chain:
			self.mechanism_bone_names.extend(self.tweak_chain.mechanism_bone_names)
			self.property_names.extend(self.tweak_chain.property_names)

		# Parent the twist ORG bones to the tweak bones
		tweak_index = 0
		for i, org_name in enumerate(org_bone_names):
			if i not in self.twist_bones:
				tweak_index += 1
				continue
			
			org_bone = edit_bones[org_name]
			org_bone.use_connect = False
			org_bone.parent = edit_bones[self.tweak_chain.tweak_bone_names[tweak_index]]
			tweak_index += len(self.twist_bones[i])

		# Create MCH bones (for master control falloff)
		# Hips MCH bones
		hips_count = self.lower_torso_bone_count
		if hips_count == 1:
			fk_bones[0].parent = hip_bone
		else:
			self.hips_mch_names = generate_mch_bones(
				armature_data,
				fk_bones[0:hips_count],
				prefs.mch_template,
				self.mch_collection_name
			)
			for mch_name in self.hips_mch_names:
				match_orientation(edit_bones[mch_name], hip_bone)
			self.mechanism_bone_names.extend(self.hips_mch_names)

		# Chest MCH bones
		chest_count = len(org_bone_names) - self.neck_bone_count - self.lower_torso_bone_count - 1
		if chest_count == 1:
			fk_bones[self.lower_torso_bone_count].parent = chest_bone
		else:
			self.chest_mch_names = generate_mch_bones(
				armature_data,
				fk_bones[self.lower_torso_bone_count:self.lower_torso_bone_count + chest_count],
				prefs.mch_template,
				self.mch_collection_name
			)
			for mch_name in self.chest_mch_names:
				match_orientation(edit_bones[mch_name], chest_bone)
			self.mechanism_bone_names.extend(self.chest_mch_names)

		# Middle Torso tweak bone
		# Should take influence from both hips and chest
		tweak_name = self.tweak_chain.tweak_bone_names[upper_torso_index] # No twist bones, so FK index = tweak index
		tweak_bone = edit_bones[tweak_name]
		mch_bone = generate_mch_bones(
			armature_data,
			[tweak_bone],
			prefs.mch_template,
			self.mch_collection_name
		)[0]
		self.mechanism_bone_names.append(mch_bone)
		self.middle_torso_mch_name = mch_bone

		# Fix required if there is more than one neck bone
		multiple_neck_bones = self.neck_bone_count > 1 or self.neck_twist_bone_count > 1

		# And rotation isolation is enabled.
		if self.add_neck_rotation_isolation and multiple_neck_bones:
			# We need a twist isolation bone to fix neck twisting
			first_neck_tweak_name = self.tweak_chain.tweak_bone_names[first_neck_tweak_index]
			second_neck_tweak_name = self.tweak_chain.tweak_bone_names[first_neck_tweak_index + 1]
			self.twist_isolator_name = generate_mch_bones(
				armature_data, 
				[edit_bones[first_neck_tweak_name]], 
				prefs.twist_isolator_template, 
				self.mch_collection_name
			)[0]
			self.mechanism_bone_names.append(self.twist_isolator_name)

			twist_isolator = edit_bones[self.twist_isolator_name]
			twist_isolator.parent = edit_bones[self.fk_bone_names[chest_bone_index]] # parent to chest FK
			edit_bones[second_neck_tweak_name].parent = twist_isolator

		return self

	def pose_mode(self, context):
		obj = context.object
		prefs = get_preferences()
		settings = get_armature_settings(obj.data, context)

		if obj.mode != 'POSE':
			bpy.ops.object.mode_set(mode='POSE')

		pose_bones = obj.pose.bones

		if self.tweak_chain:
			self.tweak_chain.pose_mode(context)
			self.object_names.extend(self.tweak_chain.object_names)

		# Master control falloff
		if self.hips_mch_names:
			influence = 1.0 / len(self.hips_mch_names)
			for mch_name in self.hips_mch_names:
				constraint = pose_bones[mch_name].constraints.new(type='COPY_TRANSFORMS')
				constraint.target = obj
				constraint.subtarget = self.hip_bone_name
				constraint.target_space = 'LOCAL'
				constraint.owner_space = 'LOCAL'
				constraint.influence = influence

		if self.chest_mch_names:
			influence = 1.0 / len(self.chest_mch_names)
			for mch_name in self.chest_mch_names:
				constraint = pose_bones[mch_name].constraints.new(type='COPY_TRANSFORMS')
				constraint.target = obj
				constraint.subtarget = self.chest_bone_name
				constraint.target_space = 'LOCAL'
				constraint.owner_space = 'LOCAL'
				constraint.influence = influence

		avg_size = sum(pose_bones[name].length for name in self.fk_bone_names) / len(self.fk_bone_names)

		# Neck twist falloff
		if self.neck_falloff_type != "NONE":
			for i, org_name in enumerate(self.neck_org_names):
				org_bone = pose_bones[org_name]
				constraint = org_bone.constraints.new(type='COPY_ROTATION')
				constraint.target = obj
				constraint.subtarget = self.fk_bone_names[-1]
				constraint.target_space = 'LOCAL'
				constraint.owner_space = 'LOCAL'

				influence = twist_influence(self.neck_falloff_type, i, len(self.neck_org_names) + 1, reverse=True)
				constraint.influence = influence

		# Middle Torso MCH bone
		if self.middle_torso_mch_name:
			mch_bone = pose_bones[self.middle_torso_mch_name]
			constraint = mch_bone.constraints.new(type='COPY_TRANSFORMS')
			constraint.target = obj
			constraint.subtarget = self.fk_bone_names[self.lower_torso_bone_count] # First upper torso bone
			constraint.influence = 0.5

		# Twist isolator
		if self.twist_isolator_name:
			first_neck_bone_index = len(self.fk_bone_names) - self.neck_bone_count - 1
			neck_fk_name = self.fk_bone_names[first_neck_bone_index]

			twist_isolator = pose_bones[self.twist_isolator_name]
			copy_loc = twist_isolator.constraints.new(type='COPY_LOCATION')
			copy_loc.target = obj
			copy_loc.subtarget = neck_fk_name

			damped_track = twist_isolator.constraints.new(type='DAMPED_TRACK')
			damped_track.target = obj
			damped_track.subtarget = neck_fk_name
			damped_track.head_tail = 1.0 # Aim at tail of neck FK

			copy_scale = twist_isolator.constraints.new(type='COPY_SCALE')
			copy_scale.target = obj
			copy_scale.subtarget = neck_fk_name
		
		# Create widgets
		# FK widgets
		coll = get_widget_collection(context, settings.widget_collection)
		if settings.do_create_widgets and self.fk_widget != "NONE":
			for i, fk_name in enumerate(self.fk_bone_names):
				fk_bone = pose_bones[fk_name]
				widget_name = generate_bone_name(fk_name, settings.widget_template)
				wgt = create_fk_widget(self.fk_widget, widget_name, coll)
				fk_bone.custom_shape = wgt

				# make all torso widgets the same size
				scale = avg_size / fk_bone.length * 1.5 # but scaled up a little
				if i >= len(self.fk_bone_names) - self.neck_bone_count - 1:
					scale = 1.5 # Keep neck size, but scale up as well
				if i == len(self.fk_bone_names) - 1:
					scale = 1.0 # Head bone is already the right size
				fk_bone.custom_shape_scale_xyz = (scale, 1.0, scale)

				if i < self.lower_torso_bone_count:
					# Move the lower torso widgets down to their original bone position
					fk_bone.custom_shape_translation = (0.0, -fk_bone.length, 0.0)
				if i == len(self.fk_bone_names) - 1:
					# Move the head widget up just past the end of the bone
					fk_bone.custom_shape_translation = (0.0, fk_bone.length * 0.6, 0.0)

				self.object_names.append(wgt.name)

		# Master Control widgets
		if settings.do_create_widgets:
			hips_widget_name = generate_bone_name(self.hip_bone_name, settings.widget_template)
			hips_wgt = create_chest_widget(hips_widget_name, coll)
			hip_bone = pose_bones[self.hip_bone_name]
			hip_bone.custom_shape = hips_wgt
			hip_bone.custom_shape_rotation_euler[1] = math.pi
			hip_bone.custom_shape_translation = (0.0, 0.0, -hip_bone.length * 0.25)  # toward head = down
			self.object_names.append(hips_wgt.name)

			chest_widget_name = generate_bone_name(self.chest_bone_name, settings.widget_template)
			chest_wgt = create_chest_widget(chest_widget_name, coll)
			chest_bone = pose_bones[self.chest_bone_name]
			chest_bone.custom_shape = chest_wgt
			chest_bone.custom_shape_translation = (0.0, 0.0, chest_bone.length)  # toward tip = up
			self.object_names.append(chest_wgt.name)

			torso_widget_name = generate_bone_name(self.torso_bone_name, settings.widget_template)
			torso_wgt = create_box_widget(torso_widget_name, coll)
			torso_bone = pose_bones[self.torso_bone_name]
			torso_bone.custom_shape = torso_wgt
			torso_bone.custom_shape_translation = (0.0, -torso_bone.length * 0.5, 0.0) # center on the head
			self.object_names.append(torso_wgt.name)

		# Bone Colors
		for i, fk_name in enumerate(self.fk_bone_names):
			fk_bone = pose_bones[fk_name]

			if i >= len(self.fk_bone_names) - self.neck_bone_count - 1:
				fk_bone.color.palette = prefs.control_bone_color
				fk_bone.custom_shape_wire_width = 1.5
			else:			
				fk_bone.color.palette = prefs.fk_bone_color

		torso_bone = pose_bones[self.torso_bone_name]
		torso_bone.color.palette = prefs.control_bone_color
		torso_bone.custom_shape_wire_width = 1.5

		hip_bone = pose_bones[self.hip_bone_name]
		hip_bone.color.palette = prefs.control_bone_color
		hip_bone.custom_shape_wire_width = 1.5

		chest_bone = pose_bones[self.chest_bone_name]
		chest_bone.color.palette = prefs.control_bone_color
		chest_bone.custom_shape_wire_width = 1.5

		return self