import bpy
from rigtools.assemblies.tool_data.mechanism_bones import MechanismBones
from rigtools.assemblies.tool_data.reparent_rules import ReparentRules, apply_reparent_rule
from rigtools.utils.bone import duplicate_bone
from rigtools.utils.naming import generate_bone_name, name_bone
from rigtools.utils.widget import apply_widget
from rigtools.armature_settings import get_armature_settings
from rigtools.preferences import get_preferences

class FKTweakChain:
	def __init__(self, *,
		fk_bone_template: str = "FK-{name}",
		skip_first_tweak: bool = False,
		do_create_fk: bool = True,
		fk_widget: str = "CIRCLE",
		tweak_relationship: str = "STRETCH_TO",
		tweak_scale: float = 0.25,
		normalize_fk_widget_scale: bool = False,
		fk_widget_taper: float = 0.0,
		fk_role: str | list[str] = 'fk',
		inherit_xz_scale_from_previous: bool = False, # ik scaling fix
	):
		self.fk_bone_template = fk_bone_template
		self.skip_first_tweak = skip_first_tweak
		self.do_create_fk = do_create_fk
		self.fk_widget = fk_widget
		self.tweak_relationship = tweak_relationship
		self.tweak_scale = tweak_scale
		self.normalize_fk_widget_scale = normalize_fk_widget_scale
		self.fk_widget_taper = fk_widget_taper
		self.fk_role = fk_role
		self.inherit_xz_scale_from_previous = inherit_xz_scale_from_previous

		self.org_bone_names = None
		self.fk_bone_names = None
		self.tweak_bone_names = None
		self.terminal_tweak_name = ""
		self.bone_lengths = {}

		self.mechanism_bones = MechanismBones()
		self.property_names = []
		self.object_names = []
		self.reparent_rules = ReparentRules()

	def edit_mode(self, armature_data, org_bone_names):
		self.org_bone_names = org_bone_names

		bpy.ops.object.mode_set(mode='EDIT')

		edit_bones = armature_data.edit_bones
		
		total_length = sum(edit_bones[name].length for name in self.org_bone_names)
		avg_length = total_length / len(self.org_bone_names)
		tweak_length = avg_length * self.tweak_scale
		
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

			if self.skip_first_tweak and bone_name == self.org_bone_names[0]:
				self.tweak_bone_names.append("")
				continue
			
			tweak_name = name_bone("tweak", bone_name)
			tweak_bone = duplicate_bone(armature_data, org_bone, tweak_name, 1)
			tweak_bone.length = tweak_length
			
			if self.do_create_fk:
				tweak_bone.parent = fk_bone
			else:
				tweak_bone.parent = last_parent
				last_parent = tweak_bone
			
			self.tweak_bone_names.append(tweak_bone.name)

		# Create terminal (tip) tweak bone            
		last_org_bone = edit_bones[self.org_bone_names[-1]]
		term_name = name_bone("term", self.org_bone_names[-1])
		term_bone = edit_bones.new(term_name)
		if self.do_create_fk:
			term_bone.parent = last_parent

		for coll in last_org_bone.collections:
			coll.assign(term_bone)
		
		term_bone.head = last_org_bone.tail
		direction = (last_org_bone.tail - last_org_bone.head).normalized()	
		term_bone.tail = last_org_bone.tail + (direction * tweak_length)
		term_bone.roll = last_org_bone.roll

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
		# Since it controls parenting outside of the assembly,
		# This is done through a reparent rule to ensure rebuildable assembly data
		self.reparent_rules.add(term_bone.name, last_org_bone.name)
		apply_reparent_rule(armature_data, term_bone.name, last_org_bone.name, forward=True)
			
		self.mechanism_bones.extend(self.fk_bone_names, self.fk_role)
		self.mechanism_bones.extend(self.tweak_bone_names, 'tweak')
		self.mechanism_bones.add(self.terminal_tweak_name, 'tweak')

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

		# This is a scaling fix for IK chains
		if self.inherit_xz_scale_from_previous:
			for org_name, tweak_name, prev_org_name, prev_tweak_name in zip(
				self.org_bone_names[1:],
				self.tweak_bone_names[1:],
				self.org_bone_names[:-1],
				self.tweak_bone_names[:-1],
			):
				for bone_name, target_name in ((tweak_name, prev_tweak_name), (org_name, prev_org_name)):
					if not bone_name: continue
					scale = pose_bones[bone_name].constraints.new('COPY_SCALE')
					scale.name = "IK XZ Scale Fix"
					scale.target = obj
					scale.subtarget = target_name
					scale.use_x = True
					scale.use_y = False
					scale.use_z = True

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
		n = len(self.fk_bone_names)
		avg = sum(pose_bones[name].length for name in self.fk_bone_names) / n if n else 0.0

		for i, fk_name in enumerate(self.fk_bone_names):
			fk_bone = pose_bones[fk_name]
			wgt = apply_widget(context, fk_bone, self.fk_widget)
			if wgt is None: continue

			if self.normalize_fk_widget_scale:
				s = avg / fk_bone.length
				if n > 1 and self.fk_widget_taper:
					t = i / (n - 1)
					s *= 1.0 - self.fk_widget_taper * t
				fk_bone.custom_shape_scale_xyz = (s, 1.0, s)

			self.object_names.append(wgt.name)

		for tweak_name in tweakers:
			tweak_bone = pose_bones[tweak_name]
			wgt = apply_widget(context, tweak_bone, 'SPHERE')
			self.object_names.append(wgt.name)
