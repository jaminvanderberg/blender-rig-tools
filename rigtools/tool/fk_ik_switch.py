import bpy
from rigtools.assemblies.tool_data.mechanism_bones import MechanismBones
from rigtools.utils.bone import duplicate_chain
from rigtools.utils.naming import generate_bone_name, bone_template
from rigtools.armature_settings import get_armature_settings
from rna_prop_ui import rna_idprop_ui_create
from rigtools.preferences import get_preferences
from rigtools.utils.widget import apply_widget

class FKIKSwitch:
	def __init__(self, *,
		switch_property_name: str,
		fk_widget_type: str = "CIRCLE",
		fk_end_widget_type: str = "SAME",
	):
		self.switch_property_name = switch_property_name
		self.fk_widget_type = fk_widget_type
		self.fk_end_widget_type = fk_end_widget_type

		self.switch_bone_names = None
		self.fk_bone_names = None
		self.ik_bone_names = None

		self.mechanism_bones = MechanismBones()
		self.property_names = []
		self.object_names = []

	def edit_mode(self, context, switch_bone_names, name_source=None):
		self.switch_bone_names = switch_bone_names

		obj = context.object
		prefs = get_preferences()

		if obj.mode != 'EDIT':
			bpy.ops.object.mode_set(mode='EDIT')

		self.fk_bone_names = duplicate_chain(obj.data, switch_bone_names, prefs.fk_template, 1.0, name_source)
		self.ik_bone_names = duplicate_chain(obj.data, switch_bone_names, bone_template("ik_mch"), 1.0, name_source)

		self.mechanism_bones.extend(self.ik_bone_names, 'mch')
		self.mechanism_bones.extend(self.fk_bone_names, 'fk')
		self.property_names.append((self.switch_property_name, "FK_IK_SWITCH"))

		return self

	def pose_mode(self, context):
		obj = context.object
		settings = get_armature_settings(obj.data, context)
		prefs = get_preferences()

		if obj.mode != 'POSE':
			bpy.ops.object.mode_set(mode='POSE')

		pose_bones = obj.pose.bones

		prop_bone_name = settings.property_bone_name
		prop_bone = pose_bones.get(prop_bone_name)
		prop_name = self.switch_property_name

		if prop_name not in prop_bone:
			prop_bone[prop_name] = 1.0
			rna_idprop_ui_create(
				prop_bone,
				prop_name,
				default=1.0,
				min=0.0,
				max=1.0
			)
			prop_bone.property_overridable_library_set(f'["{prop_name}"]', True)

		for i, (switch_bone_name, fk_bone_name, ik_bone_name) in enumerate(zip(self.switch_bone_names, self.fk_bone_names, self.ik_bone_names)):
			fk_bone = pose_bones[fk_bone_name]
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

			widget_type = (
				self.fk_end_widget_type
				if i == len(self.fk_bone_names) - 1 and self.fk_end_widget_type != "SAME"
				else self.fk_widget_type
			)

			if widget_type != "NONE":
				wgt = apply_widget(context, fk_bone, widget_type)
				self.object_names.append(wgt.name)

		return self
