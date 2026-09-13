import bpy
from rigtools.utils.bone import generate_bone_name, duplicate_bone, duplicate_chain, set_bone_collection
from rigtools.armature_settings import get_armature_settings
from bpy.props import StringProperty
from rna_prop_ui import rna_idprop_ui_create
from dataclasses import dataclass
from mathutils import Vector
from rigtools.utils.widget import get_widget_collection, create_sphere_widget, create_line_widget
from rigtools.preferences import get_preferences

@dataclass
class SplineIKChain:
	mch_bone_names: list[str] = None
	control_names: list[str] = None
	spline_object: bpy.types.Object = None

@dataclass
class SplineIKOptions:
	control_count: int = 3
	skip_first: bool = False
	ik_collection_name: str = None

def create_spline_ik_edit_mode(context, mch_bone_names, options: SplineIKOptions, name_source=None) -> SplineIKChain:
	obj = context.object
	edit_bones = obj.data.edit_bones
	prefs = get_preferences()

	if obj.mode != 'EDIT':
		bpy.ops.object.mode_set(mode='EDIT')

	settings = get_armature_settings(obj.data, context)
	root_bone = edit_bones.get(settings.root_bone_name)

	bones = mch_bone_names[1 if options.skip_first else 0:]

	spline_length = sum(edit_bones[name].length for name in bones) / len(bones) * 0.5

	# For this calculation, we're including the distance between the heads of disconnected bones
	points = [edit_bones[b].head for b in bones] + [edit_bones[bones[-1]].tail]
	seg_lengths = [(points[i + 1] - points[i]).length for i in range(len(points) - 1)]
	total_seg_length = sum(seg_lengths)
	
	control_names = []
	# Create the spline controller bones
	bone_suffix = "abcdefghijklmnopqrstuvwxyz"
	for i in range(options.control_count):
		target = total_seg_length * (i / (options.control_count - 1))
		remaining = target
		for s, length in enumerate(seg_lengths):
			if remaining < length or s == len(seg_lengths) - 1:
				u = 0.0 if length == 0.0 else min(remaining, length) / length
				pos = points[s].lerp(points[s + 1], u)
				break
			remaining -= length

		if i == 0:
			pos_name = "start"
		elif i == options.control_count - 1:
			pos_name = "end"
		elif i == 1 and options.control_count == 3:
			pos_name = "mid"
		else:
			pos_name = "mid." + bone_suffix[(i - 1) % len(bone_suffix)]

		if "{i}" in prefs.ik_spline_template:
			spline_template = prefs.ik_spline_template.replace("{i}", pos_name)
		else:
			spline_template = prefs.ik_spline_template + "." + pos_name

		ref_bone = edit_bones[bones[s]]
		spline_bone_name = generate_bone_name(name_source[0] if name_source else ref_bone.name, spline_template)
		spline_bone = edit_bones.new(spline_bone_name)
		spline_bone.head = pos
		direction = (points[s + 1] - points[s]).normalized()
		spline_bone.tail = pos + direction * spline_length
		spline_bone.parent = root_bone
		spline_bone.roll = ref_bone.roll

		if options.ik_collection_name:
			set_bone_collection(obj.data, spline_bone, options.ik_collection_name)
		else:
			for coll in ref_bone.collections:
				coll.assign(spline_bone)

		control_names.append(spline_bone.name)

	return SplineIKChain(
		mch_bone_names=mch_bone_names,
		control_names=control_names,
		spline_object=None
	)

def create_spline_ik_object_mode(context, chain: SplineIKChain, options: SplineIKOptions):
	obj = context.object
	prefs = get_preferences()
	
	if obj.mode != 'OBJECT':
		bpy.ops.object.mode_set(mode='OBJECT')

	armature_data = obj.data
	prev_pose_position = armature_data.pose_position
	armature_data.pose_position = 'REST'	

	# Create the spline object
	spline_name = generate_bone_name(chain.control_names[0], prefs.spline_object_template)
	curve_data = bpy.data.curves.new(spline_name, 'CURVE')
	curve_data.dimensions = '3D'
	curve_obj = bpy.data.objects.new(spline_name, curve_data)

	for coll in obj.users_collection:
		coll.objects.link(curve_obj)

	curve_obj.parent = obj
	curve_obj.matrix_parent_inverse.identity()
	curve_obj.location = (0.0, 0.0, 0.0)
	curve_obj.rotation_euler = (0.0, 0.0, 0.0)
	curve_obj.scale = (1.0, 1.0, 1.0)

	spline = curve_data.splines.new('BEZIER')
	spline.bezier_points.add(len(chain.control_names) - 1)

	handle_size = 0.01

	for i, control_name in enumerate(chain.control_names):
		bp = spline.bezier_points[i]
		co = obj.data.bones[control_name].head_local.copy()
		bp.co = co

		if i == 0:
			next = obj.data.bones[chain.control_names[i + 1]].head_local.copy()
			direction = (next - co).normalized()
			bp.handle_left_type = bp.handle_right_type = 'ALIGNED'
			bp.handle_right = co + direction * handle_size
			bp.handle_left = co - direction * handle_size
		elif i == len(chain.control_names) - 1:
			prev = obj.data.bones[chain.control_names[i - 1]].head_local.copy()
			direction = (co - prev).normalized()
			bp.handle_left_type = bp.handle_right_type = 'ALIGNED'
			bp.handle_left = co - direction * handle_size
			bp.handle_right = co + direction * handle_size
		else:
			bp.handle_left = bp.handle_right = co.copy()
			bp.handle_left_type = bp.handle_right_type = 'AUTO'

		mod = curve_obj.modifiers.new(name=f"Hook {control_name}", type='HOOK')
		mod.object = obj
		mod.subtarget = control_name
		mod.center = co
		mod.vertex_indices_set([i * 3, i * 3 + 1, i * 3 + 2])

	armature_data.pose_position = prev_pose_position

	return SplineIKChain(
		mch_bone_names=chain.mch_bone_names,
		control_names=chain.control_names,
		spline_object=curve_obj
	)

def create_spline_ik_pose_mode(context, chain: SplineIKChain, options: SplineIKOptions):
	obj = context.object
	settings = get_armature_settings(obj.data, context)
	prefs = get_preferences()

	if obj.mode != 'POSE':
		bpy.ops.object.mode_set(mode='POSE')

	pose_bones = obj.pose.bones

	# Spline IK
	last_mch_bone_name = chain.mch_bone_names[-1]
	last_mch_bone = pose_bones[last_mch_bone_name]
	spline_constraint = last_mch_bone.constraints.new('SPLINE_IK')
	spline_constraint.target = chain.spline_object
	spline_constraint.chain_count = len(chain.mch_bone_names) - 1 if options.skip_first else len(chain.mch_bone_names)

	# Bone Colors
	for control_name in chain.control_names:
		control_bone = pose_bones[control_name]
		control_bone.color.palette = prefs.ik_bone_color

	# Widgets
	if settings.do_create_widgets:
		coll = get_widget_collection(context, settings.widget_collection)
		for control_name in chain.control_names:
			control_widget_name = generate_bone_name(control_name, settings.widget_template)
			wgt = create_sphere_widget(control_widget_name, coll)
			control_bone = pose_bones[control_name]
			control_bone.custom_shape = wgt

	return chain