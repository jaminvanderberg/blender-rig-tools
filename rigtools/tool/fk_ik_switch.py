import bpy
from rigtools.utils.bone import generate_bone_name, duplicate_bone, duplicate_chain
from rigtools.armature_settings import get_armature_settings
from bpy.props import StringProperty
from rna_prop_ui import rna_idprop_ui_create
from rigtools.preferences import get_preferences
from rigtools.utils.widget import get_widget_collection, create_fk_widget

def create_fk_ik_switch_edit_mode(context, switch_bone_names, name_source=None):
	obj = context.object
	edit_bones = obj.data.edit_bones
	prefs = get_preferences()

	if obj.mode != 'EDIT':
		bpy.ops.object.mode_set(mode='EDIT')

	fk_bone_names = duplicate_chain(obj.data, switch_bone_names, prefs.fk_template, 1.0, name_source)
	ik_bone_names = duplicate_chain(obj.data, switch_bone_names, prefs.ik_mch_template, 1.0, name_source)

	return fk_bone_names, ik_bone_names

def create_fk_ik_switch_pose_mode(context, switch_bone_names, fk_bone_names, ik_bone_names, switch_property_name, fk_widget_type):
	obj = context.object
	settings = get_armature_settings(obj.data, context)
	prefs = get_preferences()

	if obj.mode != 'POSE':
		bpy.ops.object.mode_set(mode='POSE')

	pose_bones = obj.pose.bones

	prop_bone_name = settings.property_bone_name
	prop_bone = pose_bones.get(prop_bone_name)
	prop_name = switch_property_name

	if prop_name not in prop_bone:
		prop_bone[prop_name] = 1
		
		rna_idprop_ui_create(
			prop_bone,
			prop_name,
			default=1,
			min=0,
			max=1
		)
		prop_bone.property_overridable_library_set(f'["{prop_name}"]', True)

	for switch_bone_name, fk_bone_name, ik_bone_name in zip(switch_bone_names, fk_bone_names, ik_bone_names):
		fk_bone = pose_bones[fk_bone_name]
		ik_bone = pose_bones[ik_bone_name]
		switch_bone = pose_bones[switch_bone_name]

		fk_constraint = switch_bone.constraints.new('COPY_TRANSFORMS')
		fk_constraint.name = "Copy Transforms - FK"
		fk_constraint.target = obj
		fk_constraint.subtarget = fk_bone_name

		ik_constraint = switch_bone.constraints.new('COPY_TRANSFORMS')
		ik_constraint.name = "Copy Transforms - IK"
		ik_constraint.target = obj
		ik_constraint.subtarget = ik_bone_name

		driver = ik_constraint.driver_add("influence").driver
		driver.type = 'AVERAGE'

		var = driver.variables.new()
		var.name = "ik_switch"
		var.type = 'SINGLE_PROP'
		var.targets[0].id = obj
		var.targets[0].data_path = f'pose.bones["{prop_bone.name}"]["{prop_name}"]'

		fk_bone.color.palette = prefs.fk_bone_color

		if fk_widget_type != "None":
			coll = get_widget_collection(context, settings.widget_collection)
			widget_name = generate_bone_name(fk_bone_name, settings.widget_template)	
			wgt = create_fk_widget(fk_widget_type, widget_name, coll)
			fk_bone.custom_shape = wgt		

	return fk_bone_names, ik_bone_names
