import bpy
from rigtools.assemblies.tool_data.mechanism_bones import MechanismBones
from rigtools.assemblies.tool_data.tool_properties import ToolProperties
from rigtools.utils.bone import duplicate_chain
from rigtools.utils.naming import bone_template
from rigtools.armature_settings import get_armature_settings
from rigtools.utils.widget import LIMB_FK_WIRE_WIDTH, chain_widget_scales, widget_scale_xyz

class FKIKSwitch:
	def __init__(self, *,
		switch_property_name: str,
		ik_switch_default: str = 'IK',
		fk_widget_type: str = "CIRCLE",
		fk_end_widget_type: str = "SAME",
		fk_end_widget_class: str | None = None,
		normalize_fk_widget_scale: bool = False,
		taper_fk_widgets: bool = False,
	):
		self.switch_property_name = switch_property_name
		self.ik_switch_default = ik_switch_default
		self.fk_widget_type = fk_widget_type
		self.fk_end_widget_type = fk_end_widget_type
		self.fk_end_widget_class = fk_end_widget_class
		self.normalize_fk_widget_scale = normalize_fk_widget_scale
		self.taper_fk_widgets = taper_fk_widgets

		self.switch_bone_names = None
		self.fk_bone_names = None
		self.ik_bone_names = None

		self.mechanism_bones = MechanismBones()
		self.tool_properties = ToolProperties()

	def edit_mode(self, context, switch_bone_names, name_source=None):
		self.switch_bone_names = switch_bone_names

		obj = context.object

		if obj.mode != 'EDIT':
			bpy.ops.object.mode_set(mode='EDIT')

		self.fk_bone_names = duplicate_chain(obj.data, switch_bone_names, bone_template("fk"), 1.0, name_source)
		self.ik_bone_names = duplicate_chain(obj.data, switch_bone_names, bone_template("ik_mch"), 1.0, name_source)

		self.mechanism_bones.extend(self.ik_bone_names, 'mch')
		self.mechanism_bones.extend(self.fk_bone_names, 'fk')

		scales = chain_widget_scales([obj.data.edit_bones[name].length for name in self.fk_bone_names],
			normalize=self.normalize_fk_widget_scale, taper=self.taper_fk_widgets)
		for i in range(len(self.fk_bone_names)):
			fk_name = self.fk_bone_names[i]
			scale = scales[i]
			widget_type = self.fk_widget_type
			widget_class = None
			if i == len(self.fk_bone_names) - 1:
				if self.fk_end_widget_type != "SAME":
					widget_type = self.fk_end_widget_type
				widget_class = self.fk_end_widget_class
			self.mechanism_bones.style(fk_name,
			    widget=widget_type,
				widget_class=widget_class,
				wire_width=LIMB_FK_WIRE_WIDTH,
				scale=widget_scale_xyz(widget_type, scale)
			)

		return self

	def pose_mode(self, context):
		obj = context.object
		settings = get_armature_settings(obj.data, context)

		if obj.mode != 'POSE':
			bpy.ops.object.mode_set(mode='POSE')

		pose_bones = obj.pose.bones

		prop_bone_name = settings.property_bone_name
		prop_bone = pose_bones.get(prop_bone_name)
		prop_name = self.switch_property_name

		default_value = 0.0 if self.ik_switch_default == 'FK' else 1.0
		prop = self.tool_properties.add(prop_name, "FK_IK_SWITCH")
		prop.apply(prop_bone, default=default_value)

		for i, (switch_bone_name, fk_bone_name, ik_bone_name) in enumerate(zip(self.switch_bone_names, self.fk_bone_names, self.ik_bone_names)):
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

		return self
