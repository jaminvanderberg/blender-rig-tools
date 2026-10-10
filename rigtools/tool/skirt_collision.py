import json
import bpy
from mathutils import Vector
from rigtools.preferences import get_preferences
from rigtools.utils.bone import generate_mch_bones
from rigtools.utils.naming import bone_template, generate_bone_name
from rigtools.armature_settings import get_armature_settings
from rigtools.utils.bone_collection import set_bone_collection
from rna_prop_ui import rna_idprop_ui_create

class SkirtCollision:
	def __init__(self, *,
		property_name: str,
		target_bone_names: list[str],
		mch_bone_collection_name: str,
	):
		self.property_name = property_name
		self.target_bone_names = target_bone_names
		self.mch_bone_collection_name = mch_bone_collection_name

		self.fk_bone_names = []
		self.collision_bone_names = []
		self.mch_bone_names = []
		self.pin_bone_names = []

		self.mechanism_bone_names = []
		self.property_names = []
		self.object_names = []		

	def edit_mode(self, context, fk_names):
		self.fk_bone_names = fk_names
		obj = context.object
		armature_data = obj.data

		if obj.mode != 'EDIT':
			bpy.ops.object.mode_set(mode='EDIT')

		edit_bones = armature_data.edit_bones
		fk_bones = [edit_bones[name] for name in fk_names]

		total_length = sum(fk_bone.length for fk_bone in fk_bones)
		target_spacing = total_length * 1.5 / len(fk_bones)
		covered = 0.0

		for index, fk_bone in enumerate(fk_bones):
			collision_name = generate_bone_name(
				fk_bone.name,
				bone_template("collision_target"),
			)
			collision_bone = edit_bones.new(collision_name)
			collision_bone.parent = fk_bones[0].parent

			direction = fk_bone.tail - fk_bone.head
			tangent = direction / direction.length
			along = target_spacing * (index + 1) - covered
			point = fk_bone.head + tangent * along
			collision_bone.head = point
			collision_bone.tail = point + tangent * target_spacing * 0.25

			covered += direction.length

			if self.mch_bone_collection_name:
				set_bone_collection(armature_data, collision_bone, self.mch_bone_collection_name)
			else:
				for coll in fk_bone.collections:
					coll.assign(collision_bone)

			self.mechanism_bone_names.append(collision_bone.name)
			self.collision_bone_names.append(collision_bone.name)

			target = edit_bones[self.target_bone_names[0]]
			target_direction = (target.tail - target.head).normalized()

			point = collision_bone.head
			distance_along_target = (point - target.head).dot(target_direction)
			axis_point = target.head + target_direction * distance_along_target

			pin_name = generate_bone_name(fk_bone.name, bone_template("collision_source"))
			pin = edit_bones.new(pin_name)
			pin.head = axis_point
			pin.tail = point
			pin.parent = target
			pin.length = pin.length * 0.35
			
			self.mechanism_bone_names.append(pin.name)
			self.pin_bone_names.append(pin.name)

		mch_names = generate_mch_bones(armature_data, fk_bones, bone_template("mch"), self.mch_bone_collection_name)

		self.mechanism_bone_names.extend(mch_names)
		self.mch_bone_names.extend(mch_names)

		self.property_names.append(self.property_name)

		return self

	def pose_mode(self, context):
		obj = context.object
		pose_bones = obj.pose.bones

		settings = get_armature_settings(obj.data, context)
		prop_bone = obj.pose.bones[settings.property_bone_name]
		property_name = self.property_name

		if obj.mode != 'POSE':
			bpy.ops.object.mode_set(mode='POSE')

		# Create the skirt collision property
		if property_name not in prop_bone:
			prop_bone[property_name] = 1.0
			
			rna_idprop_ui_create(
				prop_bone,
				property_name,
				default=1.0,
				min=0.0,
				max=1.0
			)
			prop_bone.property_overridable_library_set(f'["{property_name}"]', True)			

		for fk_name, mch_name, collision_name, pin_name in zip(self.fk_bone_names, self.mch_bone_names, self.collision_bone_names, self.pin_bone_names):
			target_bone = pose_bones[pin_name]

			collision_bone = pose_bones[collision_name]
			local = target_bone.bone.matrix_local.inverted() @ collision_bone.bone.head_local
			rest_offset = local.y

			floor = collision_bone.constraints.new('FLOOR')
			floor.target = obj
			floor.subtarget = pin_name
			floor.floor_location = 'FLOOR_Y'
			floor.offset = rest_offset
			floor.use_rotation = True
			floor.owner_space = 'POSE'
			floor.target_space = 'POSE'

			rna_idprop_ui_create(
				collision_bone,
				"influence",
				default=1.0,
				min=0.0,
				max=2.0,
				soft_max=1.0
			)
			collision_bone["influence"] = 1.0

			fcurve = floor.driver_add("offset")
			driver = fcurve.driver
			driver.type = 'SCRIPTED'

			# joint influence
			var = driver.variables.new()
			var.name = "inf"
			var.type = "SINGLE_PROP"
			var.targets[0].id = obj
			var.targets[0].data_path = f'pose.bones["{collision_name}"]["influence"]'

			# master influence
			var = driver.variables.new()
			var.name = "master"
			var.type = "SINGLE_PROP"
			var.targets[0].id = obj
			var.targets[0].data_path = f'pose.bones["{prop_bone.name}"]["{property_name}"]'

			driver.expression = f"{rest_offset:.6f} * inf * master"

			# Damped track
			track = pose_bones[mch_name].constraints.new('DAMPED_TRACK')
			track.target = obj
			track.subtarget = collision_name

		return self

	def save_config(self, assembly):
		payload = {
			"property_name": self.property_name,
			"joints": [
				{
					"fk_name": fk_name,
					"collision_name": collision_name,
					"influence": 1.0,
				}
				for fk_name, collision_name in zip(self.fk_bone_names, self.collision_bone_names)
			]
		}
		options = assembly.get_options()
		options["skirt_collision"] = payload
		assembly.options_json = json.dumps(options)

		defaults = assembly.get_config_defaults()
		defaults["skirt_collision"] = payload
		assembly.config_defaults_json = json.dumps(defaults)
		return assembly		