from dataclasses import dataclass
from math import degrees, radians
import bpy
from mathutils import Vector
from rigtools.preferences import get_preferences
from rigtools.utils.bone import generate_mch_bones
from rigtools.utils.naming import bone_template, generate_bone_name
from rigtools.armature_settings import get_armature_settings
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

		self.mechanism_bone_names = []
		self.property_names = []
		self.object_names = []		

	def edit_mode(self, context, fk_name):
		self.fk_name = fk_name

		obj = context.object
		armature_data = obj.data
		edit_bones = armature_data.edit_bones

		if obj.mode != 'EDIT':
			bpy.ops.object.mode_set(mode='EDIT')

		fk_bone = edit_bones.get(self.fk_name)

		self.mch_name = generate_mch_bones(armature_data, [fk_bone], bone_template('skirt_ride'), self.mch_bone_collection_name)[0]
		self.mechanism_bone_names.append(self.mch_name)

		return self

	def pose_mode(self, context):
		obj = context.object
		prefs = get_preferences()
		pose_bones = obj.pose.bones
		settings = get_armature_settings(obj.data, context)

		if obj.mode != 'POSE':
			bpy.ops.object.mode_set(mode='POSE')

		fk_bone = pose_bones[self.fk_name].bone
		terms = []

		print(f"[skirt ride] {self.fk_name}")
		print(f"  fk head_local {tuple(round(c, 4) for c in fk_bone.head_local)}")

		for i, leg in enumerate(self.legs):
			thigh = pose_bones[leg.bone_name].bone
			sign = -1 if leg.forward_axis[0] == '-' else 1
			x_axis = thigh.matrix_local.col[0].xyz
			y_axis = thigh.matrix_local.col[1].xyz
			z_axis = thigh.matrix_local.col[2].xyz
			forward = (x_axis if leg.forward_axis[1] == 'X' else z_axis) * sign

			offset = fk_bone.head_local - thigh.head_local
			flat = offset - y_axis * offset.dot(y_axis)

			angle = forward.angle(flat)
			cone = radians(45)
			if angle >= cone:
				infuence = 0.0
			else:
				t = angle / cone
				infuence = (1.0 - t) ** 2

			print(f"  leg {leg.bone_name} {leg.forward_axis}")
			print(f"    thigh head_local {tuple(round(c, 4) for c in thigh.head_local)}")
			print(f"    offset {tuple(round(c, 4) for c in offset)}")
			print(f"    y_axis {tuple(round(c, 4) for c in y_axis)}")
			print(f"    forward {tuple(round(c, 4) for c in forward)}")
			print(f"    flat {tuple(round(c, 4) for c in flat)} len {flat.length:.4f}")
			print(f"    angle {degrees(angle):.1f}  influence {infuence:.4f}")

			if infuence < 0.01:
				print("    skip")
				continue

			bend_axis = 'ROT_Z' if leg.forward_axis[1] == 'X' else 'ROT_X'
			bend_sign = -sign if leg.forward_axis[1] == 'X' else sign
			terms.append((i, leg.bone_name, forward, infuence))

		fcurve = pose_bones[self.mch_name].driver_add('scale', 1)
		driver = fcurve.driver
		driver.type = 'SCRIPTED'

		parts = []
		for index, bone_name, forward, influence in terms:
			for row, component in enumerate("xyz"):
				var = driver.variables.new()
				var.name = f'leg{index}{component}'
				var.type = 'SINGLE_PROP'
				target = var.targets[0]
				target.id = obj
				target.data_path = f'pose.bones["{bone_name}"].matrix[{row}][1]'
			parts.append(
				f'max(0.0, (leg{index}x * {forward.x:.6f} + leg{index}y * {forward.y:.6f} + leg{index}z * {forward.z:.6f}) * {influence:.4f})'
			)

		driver.expression = f'max(0, 1 - {self.shrink_factor} * max({", ".join(parts)}))'


		print(f"  terms {len(terms)}  {driver.expression}")

		return self