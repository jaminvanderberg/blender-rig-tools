from dataclasses import dataclass
import json
from math import cos, pi, radians
import bpy
from rigtools.assemblies.tool_data.mechanism_bones import MechanismBones
from rna_prop_ui import rna_idprop_ui_create
from rigtools.armature_settings import get_armature_settings
from rigtools.preferences import get_preferences
from rigtools.utils.bone import duplicate_bone, generate_mch_bones
from rigtools.utils.naming import bone_template, generate_bone_name

@dataclass
class SkirtLeg:
	bone_name: str
	forward_axis: str # '+X', '-X', '+Z', '-Z'

class SkirtRide:
	def __init__(self, *,
		property_name: str,
		legs: list[SkirtLeg],
		prior_configs: dict,
	):
		self.property_name = property_name
		self.legs = legs
		self.prior_config = prior_configs.get("skirt_ride", {})

		self.shrink_factor = 0.5 # hard-coded default, user configures after creation

		self.fk_name = None
		self.mch_name = None
		self.terms = []

		self.mechanism_bones = MechanismBones()
		self.property_names = []
		self.object_names = []

	def edit_mode(self, context, fk_name):
		self.fk_name = fk_name

		obj = context.object
		armature_data = obj.data
		edit_bones = armature_data.edit_bones
		prefs = get_preferences()

		if obj.mode != 'EDIT':
			bpy.ops.object.mode_set(mode='EDIT')

		fk_bone = edit_bones[self.fk_name]
		skirt_parent = fk_bone.parent
		cone = radians(210)

		pending = []
		for i, leg in enumerate(self.legs):
			thigh = edit_bones[leg.bone_name]
			sign = -1 if leg.forward_axis[0] == '-' else 1
			forward = (thigh.x_axis if leg.forward_axis[1] == 'X' else thigh.z_axis) * sign

			offset = fk_bone.head - thigh.head
			flat = offset - thigh.y_axis * offset.dot(thigh.y_axis)
			if flat.length_squared < 1e-12:
				continue

			angle = forward.angle(flat)
			if angle >= cone:
				continue

			t = angle / cone
			influence = 0.5 * (1.0 + cos(pi * t)) * self.shrink_factor
			if influence < 0.01:
				continue

			bend_axis = 'ROT_Z' if leg.forward_axis[1] == 'X' else 'ROT_X'
			bend_sign = -sign if leg.forward_axis[1] == 'X' else sign
			pending.append((i, leg.bone_name, bend_axis, bend_sign, influence, flat.length))

		if len(pending) > 1:
			d_min = min(d for *_, d in pending)
			k = 3.0 # k = sharpness
			weighted = []
			for i, thigh_name, bend_axis, bend_sign, influence, d in pending:
				influence *= (d_min / d) ** k
				if influence < 0.01:
					continue
				weighted.append((i, thigh_name, bend_axis, bend_sign, influence))
			pending = weighted
		else:
			pending = [entry[:-1] for entry in pending] # drop distance

		# Apply prior config
		if self.prior_config:
			pending = [
				(i, thigh_name, bend_axis, bend_sign, self.prior_config.get(thigh_name, influence))
				for i, thigh_name, bend_axis, bend_sign, influence in pending
			]

		self.mch_name = generate_mch_bones(armature_data, [self.fk_name], bone_template('skirt_ride'))[0]
		self.mechanism_bones.add(self.mch_name, 'mch')

		self.terms = []
		for i, thigh_name, bend_axis, bend_sign, influence in pending:
			thigh = edit_bones[thigh_name]
			template = bone_template('skirt_ride_target').replace('{org}', thigh_name)
			helper_name = generate_bone_name(self.fk_name, template)
			helper = duplicate_bone(armature_data, thigh, helper_name, 0.15)
			helper.parent = skirt_parent
			helper.use_connect = False

			self.mechanism_bones.add(helper.name, 'mch')
			self.terms.append((helper.name, thigh_name, bend_axis, bend_sign, influence))

		return self

	def pose_mode(self, context):
		obj = context.object
		pose_bones = obj.pose.bones
		settings = get_armature_settings(obj.data, context)
		prop_bone = pose_bones[settings.property_bone_name]
		property_name = self.property_name

		if obj.mode != 'POSE':
			bpy.ops.object.mode_set(mode='POSE')

		if property_name not in prop_bone:
			prop_bone[property_name] = 1.0
			rna_idprop_ui_create(
				prop_bone,
				property_name,
				default=1.0,
				min=0.0,
				max=1.0,
			)
			prop_bone.property_overridable_library_set(f'["{property_name}"]', True)

		self.property_names.append((property_name, "SKIRT_RIDE"))

		if not self.terms:
			return self

		for helper_name, thigh_name, bend_axis, bend_sign, influence in self.terms:
			helper = pose_bones[helper_name]
			track = helper.constraints.new('DAMPED_TRACK')
			track.target = obj
			track.subtarget = thigh_name
			track.head_tail = 1.0

		# Add influence properties to the MCH bone
		pb = pose_bones[self.mch_name]
		for helper_name, thigh_name, bend_axis, bend_sign, influence in self.terms:
			rna_idprop_ui_create(
				pb,
				thigh_name,
				default=influence,
				min=0.0,
				soft_max=2.0,
			)
			pb[thigh_name] = influence

		# Add driver to the MCH bone
		fcurve = pb.driver_add('scale', 1)
		driver = fcurve.driver
		driver.type = 'SCRIPTED'

		var = driver.variables.new()
		var.name = "master"
		var.type = 'SINGLE_PROP'
		var.targets[0].id = obj
		var.targets[0].data_path = f'pose.bones["{prop_bone.name}"]["{property_name}"]'

		parts = []
		for index, (helper_name, thigh_name, bend_axis, bend_sign, influence) in enumerate(self.terms):
			var = driver.variables.new()
			var.name = f'leg{index}'
			var.type = 'TRANSFORMS'
			target = var.targets[0]
			target.id = obj
			target.bone_target = helper_name
			target.transform_type = bend_axis
			target.transform_space = 'LOCAL_SPACE'
			target.rotation_mode = 'SWING_TWIST_Y'

			var = driver.variables.new()
			var.name = f'inf{index}'
			var.type = 'SINGLE_PROP'
			var.targets[0].id = obj
			var.targets[0].data_path = f'pose.bones["{self.mch_name}"]["{thigh_name}"]'

			parts.append(f'max(0.0, {bend_sign} * leg{index} * inf{index})')

		driver.expression = f'max(0.1, 1 - master * max({", ".join(parts)}))'

		return self

	def save_config(self, assembly):
		payload = {
			"property_name": self.property_name,
			"mch_name": self.mch_name,
			"legs": [
				{
					"thigh_name": thigh_name,
					"influence": influence,
				}
				for helper_name, thigh_name, bend_axis, bend_sign, influence in self.terms
			],
		}
		options = assembly.get_options()
		options["skirt_ride"] = payload
		assembly.options_json = json.dumps(options)

		defaults = assembly.get_config_defaults()
		defaults["skirt_ride"] = payload
		assembly.config_defaults_json = json.dumps(defaults)
		return assembly
