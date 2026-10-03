import math
import bpy
from mathutils import Vector
from rigtools.armature_settings import get_armature_settings
from rigtools.preferences import get_preferences
from rigtools.tool.fk_tweak_chain import FKTweakChain
from rigtools.twist_bones import get_twist_chain, set_twist_parent
from rigtools.utils.bone import duplicate_bone, duplicate_bone_subdivided, generate_bone_name, generate_mch_bones, match_orientation, set_bone_collection
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
			first_neck_bone_index = len(org_bone_names) - self.neck_bone_count - 1
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
			chest_bone_index = len(org_bone_names) - self.neck_bone_count - 2
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
			fk_bone_name = generate_bone_name(org_name, prefs.fk_template)
			fk_bone = duplicate_bone(armature_data, org_bone, fk_bone_name, 1.0)
			fk_bones.append(fk_bone)

			if  i < self.lower_torso_bone_count:
				offset = fk_bone.tail - fk_bone.head
				fk_bone.head += offset
				fk_bone.tail += offset

			self.fk_bone_names.append(fk_bone.name)

			if self.fk_collection_name:
				set_bone_collection(armature_data, fk_bone, self.fk_collection_name)

			self.mechanism_bone_names.append(fk_bone.name)

		# Parent the FK bones in two sections: lower torso and upper torso
		lower_torso_index = self.lower_torso_bone_count - 1
		upper_torso_index = self.lower_torso_bone_count

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

			if i not in self.twist_bones:
				source_names.append(org_name)
				tweak_parents.append(self.fk_bone_names[parent_index])
				continue

			twist_names = self.twist_bones[i]
			source_names.extend(twist_names)

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
		for fk_name in self.fk_bone_names:
			fk_bone = pose_bones[fk_name]
			fk_bone.color.palette = prefs.fk_bone_color

		pose_bones[self.torso_bone_name].color.palette = prefs.control_bone_color
		pose_bones[self.hip_bone_name].color.palette = prefs.control_bone_color
		pose_bones[self.chest_bone_name].color.palette = prefs.control_bone_color

		return self