import bpy
from rigtools.utils.bone import duplicate_bone
from rigtools.utils.naming import generate_bone_name
from rigtools.utils.bone_collection import set_bone_collection
from rigtools.utils.widget import get_widget_collection, create_fk_widget
from rigtools.armature_settings import get_armature_settings
from rigtools.preferences import get_preferences

class FKChain:
	def __init__(self, *,
		fk_bone_template: str = "FK-{name}",
		fk_widget: str = "CIRCLE",
		fk_collection_name: str = "",
	):
		self.fk_bone_template = fk_bone_template
		self.fk_widget = fk_widget
		self.fk_collection_name = fk_collection_name

		self.org_bone_names = None
		self.fk_bone_names = []

		self.mechanism_bone_names = []
		self.property_names = []
		self.object_names = []

	def edit_mode(self, armature_data, org_bone_names):
		self.org_bone_names = org_bone_names

		bpy.ops.object.mode_set(mode='EDIT')

		edit_bones = armature_data.edit_bones

		last_parent = edit_bones[self.org_bone_names[0]].parent
		for bone_name in self.org_bone_names:
			org_bone = edit_bones[bone_name]
			fk_name = generate_bone_name(bone_name, self.fk_bone_template)
			fk_bone = duplicate_bone(armature_data, org_bone, fk_name, 1.0)
			fk_bone.parent = last_parent

			if org_bone.use_connect:
				fk_bone.use_connect = True

			self.fk_bone_names.append(fk_bone.name)
			self.mechanism_bone_names.append(fk_bone.name)
			
			last_parent = fk_bone

			if self.fk_collection_name:
				set_bone_collection(armature_data, fk_bone, self.fk_collection_name)

		return self

	def pose_mode(self, context):
		obj = context.object
		prefs = get_preferences()
		pose_bones = obj.pose.bones
		settings = get_armature_settings(obj.data, context)

		if obj.mode != 'POSE':
			bpy.ops.object.mode_set(mode='POSE')

		for org_name, fk_name in zip(self.org_bone_names, self.fk_bone_names):
			o = pose_bones[org_name]
			c = o.constraints.new(type="COPY_TRANSFORMS")
			c.target = obj
			c.subtarget = fk_name

		# Bone Colors
		for fk_name in self.fk_bone_names:
			fk_bone = pose_bones[fk_name]
			fk_bone.color.palette = prefs.fk_bone_color
			
		# Widgets
		coll = get_widget_collection(context, settings.widget_collection)
		if settings.do_create_widgets and self.fk_widget != "NONE":
			for fk_name in self.fk_bone_names:
				fk_bone = pose_bones[fk_name]
				widget_name = generate_bone_name(fk_name, settings.widget_template)
				wgt = create_fk_widget(self.fk_widget, widget_name, coll)
				fk_bone.custom_shape = wgt

				self.object_names.append(wgt.name)

		return self