import bpy
from rigtools.armature_settings import get_armature_settings
from rigtools.assemblies.mechanism_bones import MechanismBones
from rigtools.preferences import get_preferences
from rigtools.utils.bone import duplicate_bone, generate_mch_bones
from rigtools.utils.bone_chain import find_curl_axis
from rigtools.utils.naming import bone_template, generate_bone_name, name_bone
from rigtools.utils.widget import create_paddle_widget, get_widget_collection


class FingerCurl:
	def __init__(self, *,
		mch_collection_name: str = "",
		curl_axis: str = "AUTO", # AUTO, X, -X ,Z, -Z
	):
		self.mch_collection_name = mch_collection_name
		self.curl_axis = curl_axis

		self.fk_bone_names = None
		self.mch_bone_names = []
		self.control_bone_name = None

		self.sign = 0
		self.axis = ""

		self.mechanism_bones = MechanismBones()
		self.property_names = []
		self.object_names = []

	def edit_mode(self, context, fk_bone_names):
		self.fk_bone_names = fk_bone_names

		obj = context.object
		armature_data = obj.data
		
		bpy.ops.object.mode_set(mode='EDIT')
		edit_bones = armature_data.edit_bones

		self.mch_bone_names = generate_mch_bones(armature_data, fk_bone_names, bone_template('mch'))
		self.mechanism_bones.extend(self.mch_bone_names, 'mch')

		control_name = name_bone('control', self.fk_bone_names[0], strip_numbers=True)
		control_bone = duplicate_bone(armature_data, edit_bones[self.fk_bone_names[0]], control_name, 3.0)
		self.control_bone_name = control_bone.name
		self.mechanism_bones.add(self.control_bone_name, 'control')

		fk_bones = [edit_bones[name] for name in self.fk_bone_names]
		self.axis, self.sign = find_curl_axis(fk_bones, self.curl_axis)
		
		return self

	def pose_mode(self, context):
		obj = context.object
		pose_bones = obj.pose.bones
		prefs = get_preferences(context)
		settings = get_armature_settings(obj.data, context)

		seg1 = pose_bones[self.fk_bone_names[0]]
		c = seg1.constraints.new('COPY_LOCATION')
		c.target = obj
		c.subtarget = self.control_bone_name
		c.target_space = c.owner_space = 'WORLD'
		
		c2 = seg1.constraints.new('COPY_ROTATION')
		c2.target = obj
		c2.subtarget = self.control_bone_name
		c2.target_space = c2.owner_space = 'LOCAL'

		control = pose_bones[self.control_bone_name]
		control.lock_scale = (True, False, True) # Y only

		axis_index = {"X": 0, "Y": 1, "Z": 2}[self.axis]
		expr = f"{self.sign} * (1 - sy) * pi"

		for mch_name in self.mch_bone_names[1:]:
			mch = pose_bones[mch_name]
			mch.rotation_mode = 'YZX'

			fcurve = mch.driver_add('rotation_euler', axis_index)
			driver = fcurve.driver
			driver.type = 'SCRIPTED'
			
			var = driver.variables.new()
			var.name = 'sy'
			var.type = 'TRANSFORMS'
			t = var.targets[0]
			t.id = obj
			t.bone_target = self.control_bone_name
			t.transform_type = 'SCALE_Y'
			t.transform_space = 'LOCAL_SPACE'

			driver.expression = expr

		# Widgets
		coll = get_widget_collection(context, settings.widget_collection)
		if settings.do_create_widgets:
			control_widget_name = generate_bone_name(self.control_bone_name, settings.widget_template)
			control_wgt = create_paddle_widget(control_widget_name, coll)
			control.custom_shape = control_wgt
			self.object_names.append(control_wgt.name)

		# Bone Colors
		control.color.palette = prefs.control_bone_color
		control.custom_shape_wire_width = 1.5			

		return self