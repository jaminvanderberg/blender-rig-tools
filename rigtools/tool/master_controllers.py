import bpy
from rigtools.armature_settings import get_armature_settings
from rigtools.utils.bone import duplicate_bone, generate_mch_bones
from rigtools.utils.naming import bone_template, generate_bone_name, name_bone
from rigtools.preferences import get_preferences
from rigtools.utils.widget import create_fk_widget, get_widget_collection
from rigtools.assemblies.mechanism_bones import MechanismBones

class MasterControllers:
	def __init__(self, *,
		interval: int = 0,
		skip_first: bool = False,
		master_controller_type: str = "FK", # or "MASTER"
		master_controller_widget: str = 'CIRCLE',
	):
		self.interval = interval
		self.skip_first = skip_first
		self.master_controller_type = master_controller_type
		self.master_controller_widget = master_controller_widget

		self.segments = []

		self.mechanism_bones = MechanismBones()
		self.property_names = []
		self.object_names = []

	def edit_mode(self, context, bone_names: list[str], name_source=None):
		obj = context.object
		edit_bones = obj.data.edit_bones

		# Interval of 1 describes a pointless mechanism, so we skip it
		if self.interval == 1:
			return self

		# Skipping all bones isn't an error, but there's nothing for us to do
		if self.skip_first and len(bone_names) <= 1:
			return self

		if obj.mode != 'EDIT':
			bpy.ops.object.mode_set(mode='EDIT')

		# Get the bones to use
		use_names = bone_names[1 if self.skip_first else 0:]
		if not use_names:
			return self

		interval = self.interval
		if interval == 0:
			interval = len(use_names)

		master_indexes = list(range(0, len(use_names), interval))
		base_name = name_source[0] if name_source else bone_names[0]

		for i, master_index in enumerate(master_indexes):
			fk_name = use_names[master_index]
			start_index = master_index + 1 if self.master_controller_type == "FK" else master_index
			end_index = master_indexes[i + 1] if i + 1 < len(master_indexes) else len(use_names)
			driven_names = use_names[start_index:end_index]
			if not driven_names:
				continue

			# Create the master controller
			master_bone = None
			if self.master_controller_type == "MASTER":
				fk_bone = edit_bones[fk_name]
				master_bone_name = name_bone("fk_master", base_name, i=f"{i+1:02d}", strip_numbers=True)
				master_bone = duplicate_bone(obj.data, fk_bone, master_bone_name, 1.5)
				master_bone.parent = fk_bone.parent

				self.mechanism_bones.add(master_bone.name, 'master')

			# Create the driven mch bones
			mch_names = generate_mch_bones(obj.data, driven_names, bone_template("fk_follow"))
			self.mechanism_bones.extend(mch_names, 'mch')

			self.segments.append({
				"master": master_bone.name if master_bone else fk_name,
				"mch": mch_names,
			})

		return self

	def pose_mode(self, context):
		obj = context.object

		pose_bones = obj.pose.bones
		settings = get_armature_settings(obj.data, context)
		prefs = get_preferences()

		coll = get_widget_collection(context, settings.widget_collection)

		for segment in self.segments:
			master_name = segment["master"]
			mch_names = segment["mch"]
			if not mch_names:
				continue

			for mch_name in mch_names:
				mch_bone = pose_bones[mch_name]
				loc = mch_bone.constraints.new("COPY_LOCATION")
				loc.target = obj
				loc.subtarget = master_name
				loc.target_space = 'LOCAL'
				loc.owner_space = 'LOCAL'

				rot = mch_bone.constraints.new("COPY_ROTATION")
				rot.target = obj
				rot.subtarget = master_name
				rot.target_space = 'LOCAL'
				rot.owner_space = 'LOCAL'

			master_bone = pose_bones[master_name]
			if self.master_controller_type == "MASTER":
				# Scale only on the first driven bone so it does not stack per segment bone
				scale = pose_bones[mch_names[0]].constraints.new("COPY_SCALE")
				scale.target = obj
				scale.subtarget = master_name
				scale.target_space = 'LOCAL'
				scale.owner_space = 'LOCAL'

				# Widgets
				if settings.do_create_widgets:
					widget_name = generate_bone_name(master_name, settings.widget_template)
					wgt = create_fk_widget(self.master_controller_widget, widget_name, coll)
					master_bone.custom_shape = wgt
					self.object_names.append(wgt.name)

			# Bone Colors
			master_bone.color.palette = prefs.control_bone_color
			# Make the controller bone thicker
			master_bone.custom_shape_wire_width = 1.5

		return self
