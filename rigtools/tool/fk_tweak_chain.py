import bpy
from dataclasses import dataclass, field
from rigtools.utils.bone import generate_bone_name, duplicate_bone, set_bone_collection
from rigtools.utils.widget import get_widget_collection, create_sphere_widget, create_fk_widget, fk_widget_types
from rigtools.armature_settings import get_armature_settings
from rigtools.preferences import get_preferences

class FKTweakChain:
	def __init__(self, *,
		fk_bone_template: str = "FK-{name}",
		skip_first_tweak: bool = False,
		do_create_fk: bool = True,
		fk_widget: str = "CIRCLE",
		tweak_collection_name: str = "",
		fk_collection_name: str = "",
		tweak_relationship: str = "STRETCH_TO"
	):
		self.fk_bone_template = fk_bone_template
		self.skip_first_tweak = skip_first_tweak
		self.do_create_fk = do_create_fk
		self.fk_widget = fk_widget
		self.tweak_collection_name = tweak_collection_name
		self.fk_collection_name = fk_collection_name
		self.tweak_relationship = tweak_relationship

		self.org_bone_names = None
		self.fk_bone_names = None
		self.tweak_bone_names = None
		self.terminal_tweak_name = ""
		self.bone_lengths = {}

	def edit_mode(self, armature_data, org_bone_names):
		self.org_bone_names = org_bone_names

		prefs = get_preferences()
		bpy.ops.object.mode_set(mode='EDIT')

		edit_bones = armature_data.edit_bones
		
		total_length = sum(edit_bones[name].length for name in self.org_bone_names)
		avg_length = total_length / len(self.org_bone_names)
		tweak_length = avg_length * 0.25
		
		last_parent = edit_bones[self.org_bone_names[0]].parent

		self.fk_bone_names = []
		self.tweak_bone_names = []
		
		for bone_name in self.org_bone_names:
			org_bone = edit_bones[bone_name]
			self.bone_lengths[bone_name] = org_bone.length

			if self.do_create_fk:
				fk_name = generate_bone_name(bone_name, self.fk_bone_template)
				fk_bone = duplicate_bone(armature_data, org_bone, fk_name, 1.0)
				fk_bone.parent = last_parent

				self.fk_bone_names.append(fk_bone.name)
			
				last_parent = fk_bone

				if self.fk_collection_name:
					set_bone_collection(armature_data, fk_bone, self.fk_collection_name)

			if self.skip_first_tweak and bone_name == self.org_bone_names[0]:
				self.tweak_bone_names.append("")
				continue
			
			tweak_name = generate_bone_name(bone_name, prefs.tweak_template)
			tweak_bone = duplicate_bone(armature_data, org_bone, tweak_name, 1)
			tweak_bone.length = tweak_length
			
			if self.do_create_fk:
				tweak_bone.parent = fk_bone
			else:
				tweak_bone.parent = last_parent
				last_parent = tweak_bone
			
			self.tweak_bone_names.append(tweak_bone.name)

			if self.tweak_collection_name:
				set_bone_collection(armature_data, tweak_bone, self.tweak_collection_name)

		# Create terminal (tip) tweak bone            
		last_org_bone = edit_bones[self.org_bone_names[-1]]
		term_name = generate_bone_name(self.org_bone_names[-1], prefs.term_template)
		term_bone = edit_bones.new(term_name)
		if self.do_create_fk:
			term_bone.parent = last_parent

		for coll in last_org_bone.collections:
			coll.assign(term_bone)
		
		term_bone.head = last_org_bone.tail
		direction = (last_org_bone.tail - last_org_bone.head).normalized()
		term_bone.tail = last_org_bone.tail + (direction * tweak_length)
		term_bone.roll = last_org_bone.roll

		if self.tweak_collection_name:
			set_bone_collection(armature_data, term_bone, self.tweak_collection_name)
		
		self.terminal_tweak_name = term_bone.name
		
		# Parent ORG bones to Tweak
		for i in range(len(self.org_bone_names)):
			org_name = self.org_bone_names[i]
			org_bone = edit_bones[org_name]
			org_bone.use_connect = False
			if not self.tweak_bone_names[i]: # Skip first tweak
				if not self.do_create_fk:
					continue # Leave the bone parented to the last parent
				fk_bone = edit_bones[self.fk_bone_names[i]]
				org_bone.parent = fk_bone
			else:
				tweak_bone = edit_bones[self.tweak_bone_names[i]]
				org_bone.parent = tweak_bone
			
		# Children of the last bone need to be children of the terminal tweak bone instead
		last_children = [c for c in last_org_bone.children if c.name not in self.org_bone_names]
		for child in last_children:
			child.use_connect = False
			child.parent = term_bone
			
		return self

	def pose_mode(self, context):
		obj = context.object
		prefs = get_preferences()
		pose_bones = obj.pose.bones
		settings = get_armature_settings(obj.data, context)

		if obj.mode != 'POSE':
			bpy.ops.object.mode_set(mode='POSE')

		# Targets for original bones: [T1, T2, T3, ..., T_END]
		targets = self.tweak_bone_names[1:] + [self.terminal_tweak_name]

		for orig_name, target_tweak in zip(self.org_bone_names, targets):
			pbone = pose_bones[orig_name]

			constraint = pbone.constraints.new(type=self.tweak_relationship)
			constraint.target = obj
			constraint.subtarget = target_tweak
			if self.tweak_relationship == "STRETCH_TO":
				constraint.rest_length = self.bone_lengths[orig_name]

		tweakers = [t for t in self.tweak_bone_names if t] + [self.terminal_tweak_name]

		# Lock Transforms
		for tweak_name in tweakers:
			if not tweak_name:
				continue
			pb = pose_bones[tweak_name]
			pb.lock_rotation = (True, True, True)
			pb.lock_rotation_w = True

		# Bone Colors
		for fk_name in self.fk_bone_names:
			fk_bone = pose_bones[fk_name]
			fk_bone.color.palette = prefs.fk_bone_color
			
		for tweak_name in tweakers:
			tweak_bone = pose_bones[tweak_name]
			tweak_bone.color.palette = prefs.tweak_bone_color
			

		# Widgets
		coll = get_widget_collection(context, settings.widget_collection)
		if settings.do_create_widgets and self.fk_widget != "NONE":
			for fk_name in self.fk_bone_names:
				fk_bone = pose_bones[fk_name]
				widget_name = generate_bone_name(fk_name, settings.widget_template)
				wgt = create_fk_widget(self.fk_widget, widget_name, coll)
				fk_bone.custom_shape = wgt
			
		if settings.do_create_widgets:
			for tweak_name in tweakers:
				tweak_bone = pose_bones[tweak_name]
				widget_name = generate_bone_name(tweak_name, settings.widget_template)
				wgt = create_sphere_widget(widget_name, coll)
				tweak_bone.custom_shape = wgt

		return self