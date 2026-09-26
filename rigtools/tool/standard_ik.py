import bpy
from rigtools.utils.bone import generate_bone_name, duplicate_bone, set_bone_collection
from rigtools.armature_settings import get_armature_settings
from mathutils import Vector
from rigtools.utils.widget import get_widget_collection, create_sphere_widget, create_line_widget
from rigtools.preferences import get_preferences
from rigtools.rig_ui.snapping_panel import register_snap_chain as register_snap_chain_ui

class StandardIK:
	def __init__(self, *,
		enable_ik_stretch: bool = True,
		pole_distance: float = 1.0,
		ik_collection_name: str = None,
		enable_snapping: bool = True,
		mch_collection_name: str = None
	):
		self.enable_ik_stretch = enable_ik_stretch
		self.pole_distance = pole_distance
		self.ik_collection_name = ik_collection_name
		self.enable_snapping = enable_snapping
		self.mch_collection_name = mch_collection_name

		self.mch_bone_names = None
		self.fk_bone_names = None
		self.ik_control_name = None
		self.pole_name = None
		self.pole_vis_name = None
		self.snap_control_name = None
		self.snap_pole_name = None

	def edit_mode(self, context, mch_bone_names, fk_bone_names, name_source=None):
		obj = context.object
		edit_bones = obj.data.edit_bones
		prefs = get_preferences()

		if obj.mode != 'EDIT':
			bpy.ops.object.mode_set(mode='EDIT')

		settings = get_armature_settings(obj.data, context)
		root_bone = edit_bones.get(settings.root_bone_name)

		self.mch_bone_names = mch_bone_names
		self.fk_bone_names = fk_bone_names

		last_mch_bone_name = self.mch_bone_names[-1]
		last_mch_bone = edit_bones[last_mch_bone_name]
		ik_bone_name = generate_bone_name(name_source[-1] if name_source else last_mch_bone_name, prefs.ik_template)
		ik_control_bone = duplicate_bone(obj.data, last_mch_bone, ik_bone_name, 1.2)
		ik_control_bone.parent = root_bone

		first_mch_bone_name = self.mch_bone_names[0]
		first_mch_bone = edit_bones[first_mch_bone_name]
		pole_bone_name = generate_bone_name(name_source[0] if name_source else first_mch_bone_name, prefs.ik_pole_template)

		head = first_mch_bone.tail.copy()
		head += first_mch_bone.x_axis.normalized() * self.pole_distance
		pole_bone = edit_bones.new(pole_bone_name)
		pole_bone.head = head
		pole_bone.tail = head + Vector((0, first_mch_bone.length * 0.25, 0))
		pole_bone.parent = root_bone
		pole_bone.align_roll(Vector((1, 0, 0)))

		self.ik_control_name = ik_control_bone.name
		self.pole_name = pole_bone.name

		if self.enable_snapping:
			snap_control_name = generate_bone_name(ik_control_bone.name, prefs.fk_ik_snap_template)
			snap_control_bone = duplicate_bone(obj.data, ik_control_bone, snap_control_name, 0.8)
			snap_control_bone.parent = edit_bones[fk_bone_names[-1]]
			self.snap_control_name = snap_control_bone.name

			snap_pole_name = generate_bone_name(pole_bone.name, prefs.fk_ik_snap_template)
			snap_pole_bone = duplicate_bone(obj.data, pole_bone, snap_pole_name, 0.8)
			snap_pole_bone.parent = edit_bones[fk_bone_names[0]]
			self.snap_pole_name = snap_pole_bone.name

			if self.mch_collection_name:
				set_bone_collection(obj.data, snap_control_bone, self.mch_collection_name)
				set_bone_collection(obj.data, snap_pole_bone, self.mch_collection_name)
			elif prefs.mch_collection_name:
				set_bone_collection(obj.data, snap_control_bone, prefs.mch_collection_name)
				set_bone_collection(obj.data, snap_pole_bone, prefs.mch_collection_name)

		pole_vis_bone = None
		if settings.do_create_widgets:
			pole_vis_bone_name = generate_bone_name(name_source[0] if name_source else first_mch_bone_name, prefs.ik_pole_vis_template)
			pole_vis_bone = edit_bones.new(pole_vis_bone_name)
			pole_vis_bone.head = pole_bone.head
			pole_vis_bone.tail = first_mch_bone.tail
			pole_vis_bone.parent = pole_bone
			pole_vis_bone.align_roll(Vector((1, 0, 0)))
			self.pole_vis_name = pole_vis_bone.name

		if self.ik_collection_name:
			set_bone_collection(obj.data, ik_control_bone, self.ik_collection_name)
			set_bone_collection(obj.data, pole_bone, self.ik_collection_name)
			if pole_vis_bone:
				set_bone_collection(obj.data, pole_vis_bone, self.ik_collection_name)
		else:
			for coll in first_mch_bone.collections:
				# This is already done for the IK control bone
				coll.assign(pole_bone)
				if pole_vis_bone:
					coll.assign(pole_vis_bone)

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

		# Copy Transforms on the IK control bone to the last MCH bone
		last_mch_bone_name = self.mch_bone_names[-1]
		last_mch_bone = pose_bones[last_mch_bone_name]
		copy_constraint = last_mch_bone.constraints.new('COPY_TRANSFORMS')
		copy_constraint.target = obj
		copy_constraint.subtarget = self.ik_control_name

		# Create the IK constraint
		penultimate_mch_bone_name = self.mch_bone_names[-2]
		penultimate_mch_bone = pose_bones[penultimate_mch_bone_name]
		ik_constraint = penultimate_mch_bone.constraints.new('IK')
		ik_constraint.target = obj
		ik_constraint.subtarget = self.ik_control_name
		ik_constraint.chain_count = len(self.mch_bone_names) - 1
		ik_constraint.pole_target = obj
		ik_constraint.pole_subtarget = self.pole_name

		if self.enable_ik_stretch:
			ik_constraint.use_stretch = True
			for mch_bone_name in self.mch_bone_names[:-1]:
				mch_bone = pose_bones[mch_bone_name]
				mch_bone.ik_stretch = 0.05

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

		# Widgets
		if settings.do_create_widgets:
			coll = get_widget_collection(context, settings.widget_collection)
			pole_widget_name = generate_bone_name(self.pole_name, settings.widget_template)
			wgt = create_sphere_widget(pole_widget_name, coll)
			pole_bone.custom_shape = wgt

			if pole_vis_bone:
				pole_vis_widget_name = generate_bone_name(self.pole_vis_name, settings.widget_template)
				wgt = create_line_widget(pole_vis_widget_name, coll)
				pole_vis_bone.custom_shape = wgt

		return self