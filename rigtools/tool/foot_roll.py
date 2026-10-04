import math
from re import I
import bpy
from mathutils import Vector
from rigtools.utils.bone import duplicate_bone, generate_mch_bones
from rigtools.utils.naming import generate_bone_name
from rigtools.utils.bone_collection import set_bone_collection
from rigtools.utils.widget import create_roll_widget, get_widget_collection
from rigtools.armature_settings import get_armature_settings
from rigtools.preferences import get_preferences

class FootRoll:
	def __init__(self, *,
		mch_collection_name: str,
	):
		self.mch_collection_name = mch_collection_name

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

		self.mechanism_bone_names = []
		self.property_names = []
		self.object_names = []

	def edit_mode(self, context, mch_ik_foot_name, ik_foot_name, heel_pivot_name, org_toe_name):
		prefs = get_preferences(context)
		bpy.ops.object.mode_set(mode='EDIT')

		armature_data = context.object.data
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

		toe_roll_template = prefs.mch_foot_roll_template.replace("{type}", "toe.roll")
		heel_roll_template = prefs.mch_foot_roll_template.replace("{type}", "heel.roll")
		rock_a_template = prefs.mch_foot_roll_template.replace("{type}", "rock.a")
		rock_b_template = prefs.mch_foot_roll_template.replace("{type}", "rock.b")

		def create_roll_bone(name_template, head, tail):
			name = generate_bone_name(ik_foot_name, name_template)
			bone = edit_bones.new(name)
			bone.head = head
			bone.tail = tail
			self.mechanism_bone_names.append(bone.name)
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
		toe_roll_bone = align_roll_bone(create_roll_bone(toe_roll_template, ball_pivot, heel_pivot))
		heel_roll_bone = align_roll_bone(create_roll_bone(heel_roll_template, heel_pivot, heel_pivot + Vector((0, 0, length))))
		rock_a_bone = align_roll_bone(create_roll_bone(rock_a_template, heel_head, heel_tail))
		rock_b_bone = align_roll_bone(create_roll_bone(rock_b_template, heel_tail, heel_head))

		self.toe_roll_name = toe_roll_bone.name
		self.heel_roll_name = heel_roll_bone.name
		self.rock_a_name = rock_a_bone.name
		self.rock_b_name = rock_b_bone.name

		foot_roll_control_name = generate_bone_name(ik_foot_name, prefs.foot_roll_template)
		foot_roll_control_bone = duplicate_bone(context.object.data, heel_roll_bone, foot_roll_control_name, 1.5)
		self.foot_roll_control_name = foot_roll_control_bone.name
		self.mechanism_bone_names.append(foot_roll_control_bone.name)

		if self.mch_collection_name:
			set_bone_collection(context.object.data, toe_roll_bone, self.mch_collection_name, prefs.mch_parent_collection)
			set_bone_collection(context.object.data, heel_roll_bone, self.mch_collection_name, prefs.mch_parent_collection)
			set_bone_collection(context.object.data, rock_a_bone, self.mch_collection_name, prefs.mch_parent_collection)
			set_bone_collection(context.object.data, rock_b_bone, self.mch_collection_name, prefs.mch_parent_collection)
		else:
			for coll in mch_ik_foot_bone.collections:
				coll.bones.append(toe_roll_bone)
				coll.bones.append(heel_roll_bone)
				coll.bones.append(rock_a_bone)
				coll.bones.append(rock_b_bone)

		# Parenting
		mch_ik_foot_bone.parent = toe_roll_bone
		toe_roll_bone.parent = heel_roll_bone
		heel_roll_bone.parent = rock_a_bone
		rock_a_bone.parent = rock_b_bone
		rock_b_bone.parent = edit_bones[self.ik_foot_name]
		foot_roll_control_bone.parent = edit_bones[self.ik_foot_name]

		# IK VIS bone
		vis_name = generate_bone_name(ik_foot_name, prefs.vis_template)
		vis_bone = edit_bones.new(vis_name)
		vis_bone.head = heel_pivot
		vis_bone.tail = toe_bone.tail
		vis_bone.tail.z = heel_pivot.z
		vis_bone.parent = edit_bones[self.ik_foot_name]
		self.vis_name = vis_bone.name
		self.mechanism_bone_names.append(vis_bone.name)

		if self.mch_collection_name:
			set_bone_collection(context.object.data, vis_bone, self.mch_collection_name, prefs.mch_parent_collection)
		else:
			for coll in mch_ik_foot_bone.collections:
				coll.bones.append(vis_bone)

		# MCH Toe bone
		mch_toe_bone = align_roll_bone(edit_bones[generate_mch_bones(armature_data, 
			[edit_bones[org_toe_name]],
			prefs.mch_template,
			self.mch_collection_name
		)[0]])
		self.mch_toe_name = mch_toe_bone.name
		self.mechanism_bone_names.append(mch_toe_bone.name)		

		return self

	def pose_mode(self, context):
		obj = context.object
		prefs = get_preferences()
		pose_bones = obj.pose.bones
		settings = get_armature_settings(obj.data, context)

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

		# Widgets
		coll = get_widget_collection(context, settings.widget_collection)
		if settings.do_create_widgets:
			foot_roll_control_widget_name = generate_bone_name(self.foot_roll_control_name, settings.widget_template)
			foot_roll_control_wgt = create_roll_widget(foot_roll_control_widget_name, coll)
			foot_roll_control_bone = pose_bones[self.foot_roll_control_name]
			foot_roll_control_bone.custom_shape = foot_roll_control_wgt
			self.object_names.append(foot_roll_control_wgt.name)

			ik = pose_bones[self.ik_foot_name]
			ik.custom_shape_transform = pose_bones[self.vis_name]

		return self