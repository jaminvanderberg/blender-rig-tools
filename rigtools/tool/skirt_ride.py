from dataclasses import dataclass
import json
from math import radians
import bpy
from rigtools.preferences import get_preferences
from rigtools.utils.bone import duplicate_bone, generate_mch_bones
from rigtools.utils.naming import bone_template, generate_bone_name, get_base_name
from rigtools.utils.bone_collection import set_bone_collection

@dataclass
class SkirtLeg:
	bone_name: str
	forward_axis: str # '+X', '-X', '+Z', '-Z'

class SkirtRide:
	def __init__(self, *,
		mch_bone_collection_name: str,
		legs: list[SkirtLeg],
		shrink_factor: float,
	):
		self.legs = legs
		self.shrink_factor = shrink_factor
		self.mch_bone_collection_name = mch_bone_collection_name

		self.fk_name = None
		self.mch_name = None
		self.terms = []

		self.mechanism_bone_names = []
		self.property_names = []
		self.object_names = []

	@staticmethod
	def get_helper_name(self, fk_name, thigh_name):
		thigh_base_name, thigh_side = get_base_name(thigh_name)
		template = bone_template('skirt_ride_target').replace('{org}', thigh_base_name)
		return generate_bone_name(fk_name, template)

	@staticmethod
	def bend_for_axis(forward_axis: str):
		sign = -1 if forward_axis[0] == '-' else 1
		bend_axis = 'ROT_Z' if forward_axis[1] == 'X' else 'ROT_X'
		bend_sign = -sign if forward_axis[1] == 'X' else sign
		return bend_axis, bend_sign

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
		cone = radians(45)

		pending = []
		for i, leg in enumerate(self.legs):
			thigh = edit_bones[leg.bone_name]
			sign = -1 if forward_axis[0] == '-' else 1
			forward = (thigh.x_axis if leg.forward_axis[1] == 'X' else thigh.z_axis) * sign

			offset = fk_bone.head - thigh.head
			flat = offset - thigh.y_axis * offset.dot(thigh.y_axis)
			if flat.length_squared < 1e-12:
				continue

			angle = forward.angle(flat)
			if angle >= cone:
				continue

			influence = ((1.0 - angle / cone) ** 2) * self.shrink_factor
			if influence < 0.01:
				continue

			bend_axis, bend_sign = SkirtRide.bend_for_axis(leg.forward_axis)
			pending.append((i, leg.bone_name, bend_axis, bend_sign, influence))

		self.mch_name = generate_mch_bones(
			armature_data,
			[fk_bone],
			bone_template('skirt_ride'),
			self.mch_bone_collection_name,
		)[0]
		self.mechanism_bone_names.append(self.mch_name)

		self.terms = []
		for i, thigh_name, bend_axis, bend_sign, influence in pending:
			thigh = edit_bones[thigh_name]
			helper_name = self.get_helper_name(self.fk_name, thigh_name)
			helper = duplicate_bone(armature_data, thigh, helper_name, 0.35)
			helper.parent = skirt_parent
			helper.use_connect = False

			if self.mch_bone_collection_name:
				set_bone_collection(
					armature_data,
					helper,
					self.mch_bone_collection_name,
					prefs.mch_parent_collection,
				)

			self.mechanism_bone_names.append(helper.name)
			self.terms.append((helper.name, thigh_name, bend_axis, bend_sign, influence))

		return self

	def pose_mode(self, context):
		obj = context.object
		pose_bones = obj.pose.bones

		if obj.mode != 'POSE':
			bpy.ops.object.mode_set(mode='POSE')

		if not self.terms:
			return self

		for helper_name, thigh_name, bend_axis, bend_sign, influence in self.terms:
			helper = pose_bones[helper_name]
			track = helper.constraints.new('DAMPED_TRACK')
			track.target = obj
			track.subtarget = thigh_name
			track.head_tail = 1.0

		SkirtRide.build_driver(obj, self.mch_name, [
			(helper_name, thigh_name, bend_axis, bend_sign, influence)
			for helper_name, thigh_name, bend_axis, bend_sign, influence in self.terms
		]

		return self

	@staticmethod
	def build_driver(obj, mch_name: str, terms: list):
		"""terms (helper_name, bend_axis, bend_sign, influence)"""
		pose_bones = obj.pose.bones
		pb = pose_bones[mch_name]

		if obj.animation_data:
			data_path = f'pose.bones["{mch_name}"].scale'
			for fcurve in list(obj.animation_data.drivers):
				if fcurve.data_path == data_path and fcurve.array_index == 1:
					obj.animation_data.drivers.remove(fcurve)

		if not terms:
			return

		fcurve = pb.driver_add('scale', 1)
		driver = fcurve.driver
		driver.type = 'SCRIPTED'

		parts = []
		for index, (helper_name, bend_axis, bend_sign, influence) in enumerate(terms):
			var = driver.variables.new()
			var.name = f'leg{index}'
			var.type = 'TRANSFORMS'
			target = var.targets[0]
			target.id = obj
			target.bone_target = helper_name
			target.transform_type = bend_axis
			target.transform_space = 'LOCAL_SPACE'
			target.rotation_mode = 'SWING_TWIST_Y'
			parts.append(f'max(0.0, {bend_sign} * leg{index} * {influence:.4f})')

		driver.expression = f'max(0, 1 - max({", ".join(parts)}))'

	def save_config(self, assembly):
		payload = {
			"mch_name": self.mch_name,
			"legs": [
				{
					"thigh_name": thigh_name,
					"helper_name": helper_name,
					"forward_axis": forward_axis,
					"influence": influence,
				}
			],
		}
		options = assembly.get_options()
		options["skirt_ride"] = payload
		assembly.options_json = json.dumps(options)

		defaults = assembly.get_config_defaults()
		defaults["skirt_ride"] = payload
		assembly.config_defaults_json = json.dumps(defaults)
		return assembly

	@staticmethod
	def apply_config(context, assembly, old: dict, new: dict):
		options = assembly.get_options()
		influences = new.get("influences", {})
		legs = options.get("legs", [])


		for thigh_name, influence in influences.items():
			helper_name = self.get_helper_name(self.fk_name, thigh_name)
			helper = context.object.data.edit_bones[helper_name]
			helper.scale_y = influence

