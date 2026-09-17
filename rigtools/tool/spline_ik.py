import bpy
from rigtools.utils.bone import generate_bone_name, duplicate_bone, duplicate_chain, set_bone_collection
from rigtools.armature_settings import get_armature_settings
from bpy.props import StringProperty
from rna_prop_ui import rna_idprop_ui_create
from dataclasses import dataclass
from mathutils import Vector
from rigtools.utils.widget import get_widget_collection, create_sphere_widget, create_line_widget, create_twist_widget
from rigtools.preferences import get_preferences

@dataclass
class SplineIKChain:
	mch_bone_names: list[str] = None
	control_names: list[str] = None
	spline_object: bpy.types.Object = None
	twist_names: list[str] = None

spline_twist_type = [
	('NONE', "None", "No twist controllers"),
	('START_END', "Start and End", "Twist controllers at the start and end of the spline"),
	('START', "Start", "Twist controller at the start of the spline"),
	('END', "End", "Twist controller at the end of the spline"),
	('ALL', "All", "Twist controllers at every control point of the spline"),
]

@dataclass
class SplineIKOptions:
	control_count: int = 3
	skip_first: bool = False
	ik_collection_name: str = None
	twist_type: str = 'START_END'

def create_spline_ik_edit_mode(context, mch_bone_names, options: SplineIKOptions, name_source=None) -> SplineIKChain:
	obj = context.object
	edit_bones = obj.data.edit_bones
	prefs = get_preferences()

	if obj.mode != 'EDIT':
		bpy.ops.object.mode_set(mode='EDIT')

	settings = get_armature_settings(obj.data, context)
	root_bone = edit_bones.get(settings.root_bone_name)

	bones = mch_bone_names[1 if options.skip_first else 0:]

	chain_parent = edit_bones[mch_bone_names[0]].parent

	spline_length = sum(edit_bones[name].length for name in bones) / len(bones) * 0.5

	points = [edit_bones[b].head for b in bones] + [edit_bones[bones[-1]].tail]
	
	control_names = []
	twist_names = []
	twist_positions = []
	bone_suffix = "abcdefghijklmnopqrstuvwxyz"
	bone_count = len(bones)
	for i in range(options.control_count):
		chain_pos = (i / (options.control_count - 1)) * bone_count
		joint_index = round(chain_pos)

		if chain_pos >= bone_count:
			seg_index = bone_count - 1
			seg_t = 1.0
		else:
			seg_index = int(chain_pos)
			seg_t = chain_pos - seg_index
		
		pos = points[seg_index].lerp(points[seg_index + 1], seg_t)
		direction = (points[seg_index + 1] - points[seg_index]).normalized()

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
			twist_template = prefs.ik_spline_twist_template.replace("{i}", pos_name)
		else:
			spline_template = prefs.ik_spline_template + "." + pos_name
			twist_template = prefs.ik_spline_twist_template + "." + pos_name

		ref_bone = edit_bones[bones[seg_index]]
		spline_bone_name = generate_bone_name(name_source[0] if name_source else ref_bone.name, spline_template)
		spline_bone = edit_bones.new(spline_bone_name)
		spline_bone.head = pos
		direction = (points[seg_index + 1] - points[seg_index]).normalized()
		spline_bone.tail = pos + direction * spline_length
		spline_bone.parent = chain_parent
		spline_bone.roll = ref_bone.roll
		
		# Twist controllers
		do_twist = False
		if options.twist_type == 'ALL':
			do_twist = True
		elif i == 0 and options.twist_type in ['START', 'START_END']:
			do_twist = True
		elif i == options.control_count - 1 and options.twist_type in ['END', 'START_END']:
			do_twist = True

		twist_bone = None
		if do_twist:
			twist_name = generate_bone_name(name_source[0] if name_source else ref_bone.name, twist_template)
			twist_bone = duplicate_bone(obj.data, spline_bone, twist_name, 1.2)
			twist_names.append(twist_bone.name)
			twist_bone.parent = spline_bone

			if i == 0:
				twist_positions.append(0.0)
			elif i == options.control_count - 1:
				twist_positions.append(1.0)
			else:
				twist_positions.append(chain_pos - joint_index)

		if options.ik_collection_name:
			set_bone_collection(obj.data, spline_bone, options.ik_collection_name)
			if twist_bone:
				set_bone_collection(obj.data, twist_bone, options.ik_collection_name)
		else:
			for coll in ref_bone.collections:
				coll.assign(spline_bone)
				if twist_bone:
					coll.assign(twist_bone)

		control_names.append(spline_bone.name)

	if twist_names and options.twist_type in ['START', 'START_END', 'ALL']:
		first = edit_bones[twist_names[0]]
		mch = edit_bones[bones[0]]
		mch.parent = first


	return SplineIKChain(
		mch_bone_names=mch_bone_names,
		control_names=control_names,
		spline_object=None,
		twist_names=twist_names,
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
		spline_object=curve_obj,
		twist_names=chain.twist_names,
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

	ik_names = chain.mch_bone_names[1 if options.skip_first else 0:]

	# Twist
	names = chain.twist_names or []

	if len(names) >= 2:
		bone_count = len(ik_names)
		denom = len(names) - 1

		# list of (twist_index, n_seg)
		influence = {b: [] for b in range(bone_count)}

		for k in range(len(names) - 1):
			start = int((k / denom) * bone_count)
			mid = int(((k + 1) / denom) * bone_count)
			end = int(((k + 2) / denom) * bone_count)

			twist = k + 1

			for b in range(start, mid + 1):
				if b < bone_count:
					influence[b].append((twist, mid - start + 1))
			for b in range(mid + 1, end + 1):
				if b < bone_count:
					influence[b].append((twist, -(end - mid + 1)))

		## DEBUG OUTPUT ###############################################################
		print(f"twist influences ({bone_count} bones, {len(names)} twists):")
		for b, contribs in influence.items():
			if not contribs:
				print(f"  {ik_names[b]}: (none)")
				continue
			parts = []
			for twist_index, n_seg in contribs:
				sign = '+' if n_seg > 0 else '-'
				parts.append(f"{sign}{names[twist_index]}/{abs(n_seg)}")
			print(f"  [{b}] {ik_names[b]}: {' '.join(parts)}")	
		################################################################################				

		for b in range(bone_count):
			contribs = influence[b]
			if len(contribs) == 0:
				continue

			pb = pose_bones[ik_names[b]]

			pb.rotation_mode = 'XYZ'
			fcurve = pb.driver_add('rotation_euler', 1)
			driver = fcurve.driver
			driver.type = 'SCRIPTED'

			expr = ''
			first = True

			for twist_index, n_seg in contribs:
				var = driver.variables.new()
				var.name = 't' + str(twist_index)
				var.type = 'TRANSFORMS'
				t = var.targets[0]
				t.id = obj
				t.bone_target = names[twist_index]
				t.transform_type = 'ROT_Y'
				t.transform_space = 'LOCAL_SPACE'

				if not first:
					expr += ' + '
				expr += f't{twist_index} / {n_seg}'
				first = False

			driver.expression = expr

	# Bone Colors
	for control_name in chain.control_names:
		control_bone = pose_bones[control_name]
		control_bone.color.palette = prefs.ik_bone_color

	for twist_name in chain.twist_names or []:
		twist_bone = pose_bones[twist_name]
		twist_bone.color.palette = prefs.ik_bone_color

	# Lock Transforms
	for control_name in chain.control_names:
		pb = pose_bones[control_name]
		pb.lock_rotation = (True, True, True)
		pb.lock_scale = (True, True, True)

	for twist_name in chain.twist_names or []:
		pb = pose_bones[twist_name]
		pb.color.palette = prefs.ik_bone_color
		pb.lock_location = (True, True, True)
		pb.lock_rotation = (True, False, True)
		pb.lock_scale = (True, True, True)
		pb.rotation_mode = 'XYZ'

	# Widgets
	if settings.do_create_widgets:
		coll = get_widget_collection(context, settings.widget_collection)
		for control_name in chain.control_names:
			control_widget_name = generate_bone_name(control_name, settings.widget_template)
			wgt = create_sphere_widget(control_widget_name, coll)
			control_bone = pose_bones[control_name]
			control_bone.custom_shape = wgt

		for twist_name in chain.twist_names or []:
			twist_widget_name = generate_bone_name(twist_name, settings.widget_template)
			wgt = create_twist_widget(twist_widget_name, coll)
			twist_bone = pose_bones[twist_name]
			twist_bone.custom_shape = wgt

	return chain