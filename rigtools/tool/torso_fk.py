import bpy
from rigtools.preferences import get_preferences
from rigtools.tool.fk_tweak_chain import FKTweakChain
from rigtools.twist_bones import get_twist_chain, set_twist_parent
from rigtools.utils.bone import duplicate_bone, duplicate_bone_subdivided, generate_bone_name
    
class TorsoFK:
	def __init__(self, *,
		fk_widget: str = "CIRCLE",
		neck_bone_count: int,
		lower_torso_bone_count: int,
		neck_twist_bone_count: int,
		chest_twist_bone_count: int,
		add_tweak_bones: bool = True,
		tweak_relationship: str = "STRETCH_TO",
		tweak_collection_name: str = "",
	):
		self.fk_widget = fk_widget
		self.neck_bone_count = neck_bone_count
		self.neck_twist_bone_count = neck_twist_bone_count
		self.chest_twist_bone_count = chest_twist_bone_count
		self.lower_torso_bone_count = lower_torso_bone_count
		self.add_tweak_bones = add_tweak_bones
		self.tweak_relationship = tweak_relationship
		self.tweak_collection_name = tweak_collection_name

		self.tweak_chain = None
		self.fk_bone_names = []

		self.mechanism_bone_names = []
		self.property_names = []
		self.object_names = []

		self.twist_bones = {}
		self.twist_states = []

	def edit_mode(self, context, org_bone_names):
		self.org_bone_names = org_bone_names

		obj = context.object
		armature_data = obj.data
		
		prefs = get_preferences()
		bpy.ops.object.mode_set(mode='EDIT')

		edit_bones = armature_data.edit_bones

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
		for i, org_name in enumerate(org_bone_names):
			org_bone = edit_bones[org_name]
			fk_bone_name = generate_bone_name(org_name, prefs.fk_bone_template)
			fk_bone = duplicate_bone(armature_data, org_bone, fk_bone_name, 1.0)

			if  i < self.lower_torso_bone_count:
				offset = fk_bone.tail - fk_bone.head
				fk_bone.head += offset
				fk_bone.tail += offset

			self.fk_bone_names.append(fk_bone.name)

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

		if self.add_tweak_bones:
			self.tweak_chain = FKTweakChain(
				do_create_fk=False,
				tweak_relationship=self.tweak_relationship,
				tweak_collection_name=self.tweak_collection_name
			).edit_mode(armature_data, source_names)

		# Parent the tweak bones to the fk bones
		if self.add_tweak_bones:
			for tweak_name, parent in zip(self.tweak_chain.tweak_bone_names, tweak_parents, strict=True):
				edit_bones[tweak_name].parent = edit_bones[parent]

			edit_bones[self.tweak_chain.terminal_tweak_name].parent = edit_bones[self.fk_bone_names[-1]]
		

		return self