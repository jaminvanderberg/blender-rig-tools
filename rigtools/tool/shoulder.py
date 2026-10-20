import math

import bpy
from mathutils import Vector

from rigtools.armature_settings import get_armature_settings
from rigtools.assemblies.tool_data.mechanism_bones import MechanismBones
from rigtools.preferences import get_preferences
from rigtools.utils.bone import duplicate_bone
from rigtools.utils.naming import generate_bone_name, name_bone
from rigtools.utils.widget import get_widget_collection


def create_shoulder_widget(widget_name, collection):
	# Elongated Pringles: long along the bone (Y), narrow across (X),
	# wave high at the X extremes and low at the Y extremes.
	verts = []
	edges = []
	segments = 32
	for i in range(segments):
		theta = 2.0 * math.pi * i / segments
		along = math.cos(theta)
		taper = 1.0 - 0.30 * max(0.0, along)
		verts.append((
			math.sin(theta) * 0.30 * taper,
			along * 0.5,
			0.095 - 0.16 * math.cos(2.0 * theta),
		))
		edges.append((i, (i + 1) % segments))

	mesh = bpy.data.meshes.new(widget_name)
	mesh.from_pydata(verts, edges, [])
	mesh.update()
	wgt = bpy.data.objects.new(widget_name, mesh)
	collection.objects.link(wgt)
	return wgt


class Shoulder:
	def __init__(self, *,
		create_vis: bool = True,
		raise_fraction: float = 0.15,
		dip_degrees: float = 10.0,
		vis_length_scale: float = 1.4,
	):
		self.create_vis = create_vis
		self.raise_fraction = raise_fraction
		self.dip_degrees = dip_degrees
		self.vis_length_scale = vis_length_scale

		self.org_bone_name = None
		self.control_bone_name = None
		self.vis_bone_name = None

		self.mechanism_bones = MechanismBones()
		self.property_names = []
		self.object_names = []

	def edit_mode(self, context, org_bone_name):
		self.org_bone_name = org_bone_name

		obj = context.object
		armature_data = obj.data

		bpy.ops.object.mode_set(mode='EDIT')
		edit_bones = armature_data.edit_bones

		shoulder = edit_bones[org_bone_name]
		head = shoulder.head.copy()
		tail = shoulder.tail.copy()
		length = shoulder.length
		roll = shoulder.roll
		neck_base = shoulder.parent.tail.copy() if shoulder.parent else head

		control_name = name_bone('control', org_bone_name)
		control_bone = duplicate_bone(armature_data, shoulder, control_name, 1.0)
		self.control_bone_name = control_bone.name
		self.mechanism_bones.add(self.control_bone_name, 'control')

		if self.create_vis:
			side = 1.0 if tail.x >= head.x else -1.0
			direction = Vector((side, 0.0, -math.tan(math.radians(self.dip_degrees)))).normalized()

			center = (head + tail) * 0.5
			center.y = neck_base.y
			center.z += self.raise_fraction * length

			vis_length = length * self.vis_length_scale
			vis_name = name_bone('vis', org_bone_name)
			vis_bone = edit_bones.new(vis_name)
			vis_bone.head = center - direction * (vis_length * 0.5)
			vis_bone.tail = center + direction * (vis_length * 0.5)
			vis_bone.roll = roll
			vis_bone.use_deform = False
			vis_bone.parent = control_bone
			self.vis_bone_name = vis_bone.name
			self.mechanism_bones.add(self.vis_bone_name, 'mch')

		return self

	def pose_mode(self, context):
		obj = context.object
		pose_bones = obj.pose.bones
		prefs = get_preferences(context)
		settings = get_armature_settings(obj.data, context)

		if obj.mode != 'POSE':
			bpy.ops.object.mode_set(mode='POSE')

		org = pose_bones[self.org_bone_name]
		control = pose_bones[self.control_bone_name]

		constraint = org.constraints.new('COPY_TRANSFORMS')
		constraint.target = obj
		constraint.subtarget = self.control_bone_name

		# Widgets
		coll = get_widget_collection(context, settings.widget_collection)
		if settings.do_create_widgets:
			control_widget_name = generate_bone_name(self.control_bone_name, settings.widget_template)
			control_wgt = create_shoulder_widget(control_widget_name, coll)
			control.custom_shape = control_wgt
			if self.vis_bone_name:
				control.custom_shape_transform = pose_bones[self.vis_bone_name]
			self.object_names.append(control_wgt.name)

		# Bone Colors
		control.color.palette = prefs.control_bone_color
		control.custom_shape_wire_width = 1.5

		return self
