import bpy
from rigtools.assemblies.tool_data.mechanism_bones import MechanismBones
from rigtools.utils.bone import duplicate_bone
from rigtools.utils.naming import generate_bone_name
from rigtools.utils.widget import chain_widget_scales, widget_scale_xyz

class FKChain:
	def __init__(self, *,
		fk_bone_template: str = "FK-{name}",
		fk_widget: str = "CIRCLE",
		normalize_fk_widget_scale: bool = False,
		taper_fk_widgets: bool = False,
		fk_role: str | list[str] = 'fk',
		fk_color: str | None = None,
	):
		self.fk_bone_template = fk_bone_template
		self.fk_widget = fk_widget
		self.normalize_fk_widget_scale = normalize_fk_widget_scale
		self.taper_fk_widgets = taper_fk_widgets
		self.fk_role = fk_role
		self.fk_color = fk_color

		self.org_bone_names = None
		self.fk_bone_names = []

		self.mechanism_bones = MechanismBones()
		self.property_names = []
		self.object_names = []

	def edit_mode(self, context, org_bone_names):
		self.org_bone_names = org_bone_names

		obj = context.object
		armature_data = obj.data

		if obj.mode != 'EDIT':
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
			self.mechanism_bones.add(fk_bone.name, self.fk_role)
			last_parent = fk_bone

		scales = chain_widget_scales([edit_bones[name].length for name in self.fk_bone_names],
			normalize=self.normalize_fk_widget_scale, taper=self.taper_fk_widgets)
		for fk_name, scale in zip(self.fk_bone_names, scales):
			self.mechanism_bones.style(fk_name, 
			    widget=self.fk_widget,
			    color=self.fk_color,
			    scale=widget_scale_xyz(self.fk_widget, scale)
			)

		return self

	def pose_mode(self, context):
		obj = context.object
		pose_bones = obj.pose.bones

		if obj.mode != 'POSE':
			bpy.ops.object.mode_set(mode='POSE')

		for org_name, fk_name in zip(self.org_bone_names, self.fk_bone_names):
			o = pose_bones[org_name]
			c = o.constraints.new(type="COPY_TRANSFORMS")
			c.target = obj
			c.subtarget = fk_name

		return self