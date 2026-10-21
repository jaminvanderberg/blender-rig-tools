import math
import bpy
from rna_prop_ui import rna_idprop_ui_create
from rigtools.utils.bone import duplicate_bone
from rigtools.utils.naming import name_bone
from rigtools.armature_settings import get_armature_settings
from mathutils import Vector
from rigtools.utils.widget import apply_widget
from rigtools.preferences import get_preferences
from rigtools.rig_ui.snapping_data import register_snap_chain as register_snap_chain_ui
from rigtools.assemblies.tool_data.mechanism_bones import MechanismBones

def signed_angle(u, v, normal):
	normal = normal.normalized()
	u = u.normalized()
	v = v.normalized()
	angle = u.angle(v)
	if u.cross(v).angle(normal) < 1:  # < ~57° means same hemisphere as normal → flip sign
		angle = -angle
	return angle

def get_pole_angle(base_bone, ik_bone, pole_location):
	# Plane of the IK chain + pole
	pole_normal = (ik_bone.tail - base_bone.head).cross(pole_location - base_bone.head)
	# Pole direction flattened into base bone's "spin" plane (⊥ to bone length)
	projected_pole_axis = pole_normal.cross(base_bone.tail - base_bone.head)
	return signed_angle(
		base_bone.x_axis,
		projected_pole_axis,
		base_bone.tail - base_bone.head,  # length axis = sign reference
	)

class StandardIK:
	def __init__(self, *,
		pole_distance: float = 1.0,
		enable_snapping: bool = True,
		ik_stretch_property_name: str,
	):
		self.ik_stretch_property_name = ik_stretch_property_name
		self.pole_distance = pole_distance
		self.enable_snapping = enable_snapping

		self.mch_bone_names = None
		self.fk_bone_names = None
		self.ik_control_name = None
		self.pole_name = None
		self.pole_vis_name = None
		self.snap_control_name = None
		self.snap_pole_name = None
		self.ik_chain_length = 0.0

		self.mechanism_bones = MechanismBones()
		self.property_names = []
		self.object_names = []
		self.mch_tweak_name = None

	def edit_mode(self, context, mch_bone_names, fk_bone_names, tweak_bone_names=None, name_source=None):
		obj = context.object
		edit_bones = obj.data.edit_bones
		prefs = get_preferences()

		if obj.mode != 'EDIT':
			bpy.ops.object.mode_set(mode='EDIT')

		settings = get_armature_settings(obj.data, context)
		root_bone = edit_bones.get(settings.root_bone_name)

		self.mch_bone_names = mch_bone_names
		self.fk_bone_names = fk_bone_names

		self.ik_chain_length = sum(edit_bones[name].length for name in self.mch_bone_names[:-1])

		last_mch_bone_name = self.mch_bone_names[-1]
		last_mch_bone = edit_bones[last_mch_bone_name]
		ik_bone_name = name_bone("ik", name_source[-1] if name_source else last_mch_bone_name)
		ik_control_bone = duplicate_bone(obj.data, last_mch_bone, ik_bone_name, 1.2)
		ik_control_bone.parent = root_bone

		bone1_name = self.mch_bone_names[0]
		bone1 = edit_bones[bone1_name]
		bone2_name = self.mch_bone_names[1]
		bone2 = edit_bones[bone2_name]
		pole_bone_name = name_bone("ik_pole", name_source[0] if name_source else bone1_name)

		shoulder = bone1.head.copy()
		elbow = bone2.head.copy()
		wrist = bone2.tail.copy()

		chord = wrist - shoulder
		proj = shoulder + chord * ((elbow - shoulder).dot(chord)) / chord.length_squared
		bend = elbow - proj
		x = bone1.x_axis.normalized()
		if bend.length_squared < 1e-6:
			dir = x
		else:
			dir = x if bend.dot(x) >= 0 else -x

		offset = bone1.length * 1.5

		pole_bone = edit_bones.new(pole_bone_name)
		pole_bone.head = elbow + dir * offset
		pole_bone.tail = pole_bone.head + Vector((0, bone1.length * 0.25, 0))
		pole_bone.parent = root_bone
		pole_bone.align_roll(Vector((1, 0, 0)))

		self.ik_control_name = ik_control_bone.name
		self.pole_name = pole_bone.name

		if tweak_bone_names:
			tweak = edit_bones[tweak_bone_names[len(self.mch_bone_names) - 2]]
			mch_name = name_bone("mch", tweak.name)
			mch = duplicate_bone(obj.data, tweak, mch_name, 0.5)
			mch.parent = tweak.parent
			tweak.parent = mch

			self.mch_tweak_name = mch.name
			self.mechanism_bones.add(self.mch_tweak_name, 'mch')

		if self.enable_snapping:
			snap_control_name = name_bone("fk_ik_snap", ik_control_bone.name)
			snap_control_bone = duplicate_bone(obj.data, ik_control_bone, snap_control_name, 0.8)
			snap_control_bone.parent = edit_bones[fk_bone_names[-1]]
			self.snap_control_name = snap_control_bone.name

			snap_pole_name = name_bone("fk_ik_snap", pole_bone.name)
			snap_pole_bone = duplicate_bone(obj.data, pole_bone, snap_pole_name, 0.8)
			snap_pole_bone.parent = edit_bones[fk_bone_names[0]]
			self.snap_pole_name = snap_pole_bone.name

		pole_vis_bone_name = name_bone("ik_pole_vis", name_source[0] if name_source else bone1_name)
		pole_vis_bone = edit_bones.new(pole_vis_bone_name)
		pole_vis_bone.head = pole_bone.head
		pole_vis_bone.tail = bone1.tail
		pole_vis_bone.parent = pole_bone
		pole_vis_bone.align_roll(Vector((1, 0, 0)))
		self.pole_vis_name = pole_vis_bone.name

		self.mechanism_bones.add(self.ik_control_name, 'ik')
		self.mechanism_bones.add(self.pole_name, 'ik')
		if pole_vis_bone:
			self.mechanism_bones.add(self.pole_vis_name, 'ik')
		if self.snap_control_name:
			self.mechanism_bones.add(self.snap_control_name, 'mch')
		if self.snap_pole_name:
			self.mechanism_bones.add(self.snap_pole_name, 'mch')

		return self

	def register_snap_chain(self, context, switch_property):
		register_snap_chain_ui(
			context.object.data,
			switch_property=switch_property,
			fk_bones=self.fk_bone_names,
			ik_mch_bones=self.mch_bone_names,
			ik_control=self.ik_control_name,
			ik_pole=self.pole_name,
			snap_control=self.snap_control_name,
			snap_pole=self.snap_pole_name,
			context=context,
		)
		return self

	def pose_mode(self, context):
		obj = context.object
		prefs = get_preferences()
		settings = get_armature_settings(obj.data, context)

		if obj.mode != 'POSE':
			bpy.ops.object.mode_set(mode='POSE')

		pose_bones = obj.pose.bones

		prop_bone_name = settings.property_bone_name
		prop_bone = pose_bones[prop_bone_name]
		if self.ik_stretch_property_name not in prop_bone:
			prop_bone[self.ik_stretch_property_name] = 1.0
			rna_idprop_ui_create(
				prop_bone,
				self.ik_stretch_property_name,
				default=1.0,
				min=0.0,
				max=1.0,
			)
			prop_bone.property_overridable_library_set(f'["{self.ik_stretch_property_name}"]', True)

		self.property_names.append((self.ik_stretch_property_name, "IK_STRETCH"))

		# Copy Transforms on the IK control bone to the last MCH bone
		last_mch_bone_name = self.mch_bone_names[-1]
		last_mch_bone = pose_bones[last_mch_bone_name]
		copy_constraint = last_mch_bone.constraints.new('COPY_TRANSFORMS')
		copy_constraint.target = obj
		copy_constraint.subtarget = self.ik_control_name

		# Limit Distance controlled by the IK stretch property
		limit = last_mch_bone.constraints.new('LIMIT_DISTANCE')
		limit.name = "IK Stretch"
		limit.target = obj
		limit.subtarget = self.mch_bone_names[0]
		limit.distance = self.ik_chain_length
		limit.limit_mode = 'LIMITDIST_INSIDE'
		limit.target_space = 'CUSTOM'
		limit.owner_space = 'CUSTOM'
		limit.head_tail = 0.0
		limit.space_object = obj
		limit.space_subtarget = self.mch_bone_names[0]

		driver = limit.driver_add('influence').driver
		driver.type = 'SCRIPTED'
		driver.expression = "1 - amt"
		var = driver.variables.new()
		var.name = "amt"
		var.type = 'SINGLE_PROP'
		var.targets[0].id = obj
		var.targets[0].data_path = f'pose.bones["{prop_bone_name}"]["{self.ik_stretch_property_name}"]'

		# Create the IK constraint
		penultimate_mch_bone_name = self.mch_bone_names[-2]
		penultimate_mch_bone = pose_bones[penultimate_mch_bone_name]
		ik_constraint = penultimate_mch_bone.constraints.new('IK')
		ik_constraint.target = obj
		ik_constraint.subtarget = self.ik_control_name
		ik_constraint.chain_count = len(self.mch_bone_names) - 1
		ik_constraint.pole_target = obj
		ik_constraint.pole_subtarget = self.pole_name

		pole_bone = pose_bones[self.pole_name]
		axis = penultimate_mch_bone.y_axis.normalized()
		pole_vec = pole_bone.head - penultimate_mch_bone.head
		pole_in_plane = pole_vec - axis * pole_vec.dot(axis)
		ref = penultimate_mch_bone.x_axis.normalized()
		ref_in_plane = ref - axis * ref.dot(axis)
		angle = math.atan2(
			axis.dot(ref_in_plane.cross(pole_in_plane)), # sin component
			ref_in_plane.dot(pole_in_plane), # cos component
		)
		ik_constraint.pole_angle = angle

		base_bone = pose_bones[self.mch_bone_names[0]]   # chain root
		ik_bone = penultimate_mch_bone                   # bone with the IK constraint
		pole_location = pose_bones[self.pole_name].matrix.translation
		ik_constraint.pole_angle = get_pole_angle(base_bone, ik_bone, pole_location)

		ik_constraint.use_stretch = True
		for mch_bone_name in self.mch_bone_names[:-1]:
			mch_bone = pose_bones[mch_bone_name]
			mch_bone.ik_stretch = 0.05

			stretch_driver = mch_bone.driver_add('ik_stretch').driver
			stretch_driver.type = 'SCRIPTED'
			stretch_driver.expression = "0.05 * amt"
			var = stretch_driver.variables.new()
			var.name = "amt"
			var.type = 'SINGLE_PROP'
			var.targets[0].id = obj
			var.targets[0].data_path = f'pose.bones["{prop_bone_name}"]["{self.ik_stretch_property_name}"]'

		if self.mch_tweak_name:
			mch = pose_bones[self.mch_tweak_name]
			scale = mch.constraints.new('COPY_SCALE')
			scale.target = obj
			scale.subtarget = settings.root_bone_name

		pole_vis_bone = None
		# stretch to on the VIS bone
		if self.pole_vis_name:
			pole_vis_bone = pose_bones[self.pole_vis_name]
			vis_constraint = pole_vis_bone.constraints.new('STRETCH_TO')
			vis_constraint.target = obj
			vis_constraint.subtarget = self.mch_bone_names[0]
			vis_constraint.rest_length = 0.0
			vis_constraint.head_tail = 1.0

		# Bone Colors
		if pole_vis_bone:
			pole_vis_bone.color.palette = prefs.ik_bone_color
		pole_bone = pose_bones[self.pole_name]
		pole_bone.color.palette = prefs.ik_bone_color
		ik_control_bone = pose_bones[self.ik_control_name]
		ik_control_bone.color.palette = prefs.ik_bone_color
		ik_control_bone.custom_shape_wire_width = 2.0

		# Widgets
		wgt = apply_widget(context, ik_control_bone, 'IK')
		self.object_names.append(wgt.name)

		wgt = apply_widget(context, pole_bone, 'SPHERE')
		self.object_names.append(wgt.name)

		if pole_vis_bone:
			wgt = apply_widget(context, pole_vis_bone, 'LINE')
			self.object_names.append(wgt.name)

		return self