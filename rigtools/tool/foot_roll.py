import math
import bpy
from mathutils import Vector
from rigtools.utils.bone import duplicate_bone, generate_mch_bones
from rigtools.utils.naming import bone_template, name_bone
from rigtools.utils.widget import IK_WIRE_WIDTH
from rigtools.assemblies.tool_data.mechanism_bones import MechanismBones

class FootRoll:
	def __init__(self):		
		self.mch_ik_foot_name = None
		self.ik_foot_name = None
		self.org_toe_name = None
		self.heel_pivot_name = None

		self.foot_rool_control_name = None
		self.toe_roll_name = None
		self.heel_roll_name = None
		self.rock_a_name = None
		self.rock_b_name = None
		self.mch_toe_name = None
		self.vis_name = None

		self.mechanism_bones = MechanismBones()
		self.property_names = []
		self.object_names = []

	def edit_mode(self, context, mch_ik_foot_name, ik_foot_name, heel_pivot_name, org_toe_name):
		obj = context.object
		armature_data = obj.data

		if obj.mode != 'EDIT':
			bpy.ops.object.mode_set(mode='EDIT')
		edit_bones = armature_data.edit_bones

		self.mch_ik_foot_name = mch_ik_foot_name
		self.ik_foot_name = ik_foot_name
		self.heel_pivot_name = heel_pivot_name
		self.org_toe_name = org_toe_name

		heel_pivot_bone = edit_bones[heel_pivot_name]
		toe_bone = edit_bones[org_toe_name]
		mch_ik_foot_bone = edit_bones[mch_ik_foot_name]

		ball_pivot = toe_bone.head
		ankle = mch_ik_foot_bone.head

		heel_head = heel_pivot_bone.head
		heel_tail = heel_pivot_bone.tail
		heel_vec = heel_tail - heel_head

		t = (ankle - heel_head).dot(heel_vec) / heel_vec.length_squared
		heel_pivot = heel_head + heel_vec * t

		# World +Z = up
		forward = Vector((0, 1, 0))
		if forward.dot(ball_pivot - heel_pivot) < 0:
			forward = -forward

		up = Vector((0, 0, 1))

		def create_roll_bone(roll_type, head, tail):
			name = name_bone("mch_foot_roll", ik_foot_name, type=roll_type)
			bone = edit_bones.new(name)
			bone.head = head
			bone.tail = tail
			self.mechanism_bones.add(bone.name, 'mch')
			return bone

		def align_roll_bone(bone):
			y = (bone.tail - bone.head).normalized()
			hint = forward
			if abs(hint.dot(y)) > 0.9:
				hint = up
			hint = (hint - y * hint.dot(y)).normalized()
			bone.align_roll(hint)

			return bone

		length = mch_ik_foot_bone.length * 0.5
		toe_roll_bone = align_roll_bone(create_roll_bone("toe.roll", ball_pivot, heel_pivot))
		heel_roll_bone = align_roll_bone(create_roll_bone("heel.roll", heel_pivot, heel_pivot + Vector((0, 0, length))))
		rock_a_bone = align_roll_bone(create_roll_bone("rock.a", heel_head, heel_tail))
		rock_b_bone = align_roll_bone(create_roll_bone("rock.b", heel_tail, heel_head))

		self.toe_roll_name = toe_roll_bone.name
		self.heel_roll_name = heel_roll_bone.name
		self.rock_a_name = rock_a_bone.name
		self.rock_b_name = rock_b_bone.name

		foot_roll_control_name = name_bone("foot_roll", ik_foot_name)
		foot_roll_control_bone = duplicate_bone(context.object.data, heel_roll_bone, foot_roll_control_name, 1.5)
		self.foot_roll_control_name = foot_roll_control_bone.name
		style = self.mechanism_bones.add(foot_roll_control_bone.name, 'ik')
		style.set(widget='ROLL', wire_width=IK_WIRE_WIDTH)

		# Parenting
		mch_ik_foot_bone.parent = toe_roll_bone
		toe_roll_bone.parent = heel_roll_bone
		heel_roll_bone.parent = rock_a_bone
		rock_a_bone.parent = rock_b_bone
		rock_b_bone.parent = edit_bones[self.ik_foot_name]
		foot_roll_control_bone.parent = edit_bones[self.ik_foot_name]

		# IK VIS bone
		vis_name = name_bone("vis", ik_foot_name)
		vis_bone = edit_bones.new(vis_name)
		vis_bone.head = heel_pivot
		vis_bone.tail = toe_bone.tail
		vis_bone.tail.z = heel_pivot.z
		vis_bone.parent = edit_bones[self.ik_foot_name]
		self.vis_name = vis_bone.name
		self.mechanism_bones.add(vis_bone.name, 'mch')
		self.mechanism_bones.style(self.ik_foot_name, transform_bone=self.vis_name)

		# MCH Toe bone
		mch_toe_bone = align_roll_bone(edit_bones[generate_mch_bones(armature_data, 
			[org_toe_name],
			bone_template("mch")
		)[0]])
		self.mch_toe_name = mch_toe_bone.name
		self.mechanism_bones.add(mch_toe_bone.name, 'mch')

		return self

	def pose_mode(self, context):
		obj = context.object
		pose_bones = obj.pose.bones

		if obj.mode != 'POSE':
			bpy.ops.object.mode_set(mode='POSE')

		# Remove contraint from MCH IK foot bone
		mch_ik_foot_bone = pose_bones[self.mch_ik_foot_name]
		for c in list(mch_ik_foot_bone.constraints):
			if c.type == 'COPY_TRANSFORMS' and c.subtarget == self.ik_foot_name:
				mch_ik_foot_bone.constraints.remove(c)

		# Setup the control bone
		ctrl = pose_bones[self.foot_roll_control_name]
		ctrl.lock_location = (True, True, True)
		ctrl.lock_scale = (True, True, True)
		ctrl.rotation_mode = 'XYZ'

		# Rock bones
		for rock_name, lim in ((self.rock_a_name, 'max_z'), (self.rock_b_name, 'min_z')):
			r = pose_bones[rock_name]
			r.rotation_mode = 'XYZ'
			c = r.constraints.new('COPY_ROTATION')
			c.target = obj
			c.subtarget = self.foot_roll_control_name
			c.use_x = c.use_y = False
			c.use_z = True
			c.target_space = 'LOCAL'
			c.owner_space = 'LOCAL'

			lim_c = r.constraints.new('LIMIT_ROTATION')
			lim_c.owner_space = 'LOCAL'
			lim_c.use_limit_z = True
			if lim == 'max_z':
				lim_c.min_z = 0
				lim_c.max_z = math.pi
			else:
				lim_c.min_z = -math.pi
				lim_c.max_z = 0

		# Roll bones
		for roll_name, lim in ((self.heel_roll_name, 'min_x'), (self.toe_roll_name, 'max_x')):
			r = pose_bones[roll_name]
			r.rotation_mode = 'XYZ'
			c = r.constraints.new('COPY_ROTATION')
			c.target = obj
			c.subtarget = self.foot_roll_control_name
			c.use_y = c.use_z = False
			c.use_x = True
			c.target_space = 'LOCAL'
			c.owner_space = 'LOCAL'

			lim_c = r.constraints.new('LIMIT_ROTATION')
			lim_c.owner_space = 'LOCAL'
			lim_c.use_limit_x = True
			if lim == 'max_x':
				lim_c.min_x = 0
				lim_c.max_x = math.pi
			else:
				lim_c.min_x = -math.pi
				lim_c.max_x = 0

		# MCH Toe bone
		t = pose_bones[self.mch_toe_name]
		c = t.constraints.new('COPY_ROTATION')
		c.target = obj
		c.subtarget = self.foot_roll_control_name
		c.use_y = c.use_z = False
		c.use_x = True
		c.target_space = 'LOCAL'
		c.owner_space = 'LOCAL'

		lim_c = t.constraints.new('LIMIT_ROTATION')
		lim_c.owner_space = 'LOCAL'
		lim_c.use_limit_x = True
		lim_c.min_x = 0
		lim_c.max_x = math.pi	

		return self