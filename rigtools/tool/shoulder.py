import math

import bpy
from mathutils import Vector

from rigtools.assemblies.tool_data.mechanism_bones import MechanismBones
from rigtools.preferences import get_preferences
from rigtools.utils.naming import name_bone

RAISE_FRACTION = 0.15
BACK_FRACTION = 0.0
DIP_DEGREES = 10.0
VIS_LENGTH_SCALE = 1.4

class Shoulder:
	def __init__(self):
		self.fk_bone_name = None
		self.control_bone_name = None
		self.vis_bone_name = None

		self.mechanism_bones = MechanismBones()
		self.property_names = []
		self.object_names = []

	def edit_mode(self, context, fk_bone_name):
		self.fk_bone_name = fk_bone_name

		obj = context.object
		armature_data = obj.data

		bpy.ops.object.mode_set(mode='EDIT')
		edit_bones = armature_data.edit_bones

		shoulder = edit_bones[fk_bone_name]
		head = shoulder.head.copy()
		tail = shoulder.tail.copy()
		length = shoulder.length
		neck_base = shoulder.parent.tail.copy() if shoulder.parent else head

		side = 1.0 if tail.x >= head.x else -1.0
		direction = Vector((side, 0.0, -math.tan(math.radians(DIP_DEGREES)))).normalized()

		center = (head + tail) * 0.5
		center.y = neck_base.y + BACK_FRACTION * length
		center.z += RAISE_FRACTION * length

		vis_length = length * VIS_LENGTH_SCALE
		vis_name = name_bone('vis', fk_bone_name)
		vis_bone = edit_bones.new(vis_name)
		vis_bone.head = center - direction * (vis_length * 0.5)
		vis_bone.tail = center + direction * (vis_length * 0.5)
		vis_bone.align_roll(Vector((0.0, 0.0, 1.0)))
		vis_bone.use_deform = False
		vis_bone.parent = shoulder
		self.vis_bone_name = vis_bone.name
		self.mechanism_bones.add(self.vis_bone_name, 'mch')

		return self

	def pose_mode(self, context):
		obj = context.object
		pose_bones = obj.pose.bones
		prefs = get_preferences(context)

		if obj.mode != 'POSE':
			bpy.ops.object.mode_set(mode='POSE')

		shoulder = pose_bones[self.fk_bone_name]
		vis = pose_bones[self.vis_bone_name]

		shoulder.custom_shape_transform = vis
		
		# Bone Colors
		shoulder.color.palette = prefs.control_bone_color
		shoulder.custom_shape_wire_width = 1.2

		return self
