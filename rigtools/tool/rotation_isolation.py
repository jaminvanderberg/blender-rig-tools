from rigtools.utils.naming import name_bone
from rigtools.utils.bone_collection import set_bone_collection
from rigtools.preferences import get_preferences
from rigtools.armature_settings import get_armature_settings
import mathutils
import bpy
from rna_prop_ui import rna_idprop_ui_create


class RotationIsolation:
	def __init__(self, *,
		property_name: str,
		mch_collection_name: str | None = None,
		include_scale: bool = True,
		disable_scale: bool = False,
		inherit_scale_from_root: bool = False,
	):
		self.property_name = property_name
		self.mch_collection_name = mch_collection_name
		self.include_scale = include_scale
		self.disable_scale = disable_scale
		self.inherit_scale_from_root = inherit_scale_from_root

		self.created_bones = None
		self.root_bone_name = None

		self.mechanism_bone_names = []
		self.property_names = []
		self.object_names = []

	def edit_mode(self, context, armature_data, bone_names):
		prefs = get_preferences()
		settings = get_armature_settings(armature_data, context)

		root_bone = armature_data.edit_bones.get(settings.root_bone_name)
		self.root_bone_name = settings.root_bone_name

		bpy.ops.armature.select_all(action='DESELECT')

		self.created_bones = []
		for bone_name in bone_names:
			bone = armature_data.edit_bones[bone_name]

			socket_name = name_bone("socket", bone.name)
			socket_bone = armature_data.edit_bones.new(socket_name)

			socket_bone.head = bone.head.copy()
			socket_bone.tail = socket_bone.head + mathutils.Vector((0.0, 0.0, bone.length * 0.5))
			socket_bone.roll = 0.0
			socket_bone.parent = bone.parent
			if self.inherit_scale_from_root:
				socket_bone.inherit_scale = 'NONE'

			int_name = name_bone("int", bone.name)
			int_bone = armature_data.edit_bones.new(int_name)

			int_bone.head = bone.head.copy()
			int_bone.tail = socket_bone.tail
			int_bone.length = bone.length * 0.4
			int_bone.roll = 0.0

			int_bone.parent = root_bone

			if self.mch_collection_name:
				set_bone_collection(armature_data, int_bone, self.mch_collection_name, prefs.mch_parent_collection)
				set_bone_collection(armature_data, socket_bone, self.mch_collection_name, prefs.mch_parent_collection)
			else:
				for coll in bone.collections:
					coll.assign(socket_bone)
					coll.assign(int_bone)

			bone.use_connect = False
			bone.parent = int_bone

			self.created_bones.append((socket_bone.name, int_bone.name))

			self.mechanism_bone_names.append(socket_bone.name)
			self.mechanism_bone_names.append(int_bone.name)
			
		self.property_names.append(self.property_name)

		return self

	def pose_mode(self, context):
		obj = context.object
		settings = get_armature_settings(obj.data, context)
		prop_bone = obj.pose.bones[settings.property_bone_name]
		property_name = self.property_name

		if property_name not in prop_bone:
			prop_bone[property_name] = 1.0
			
			rna_idprop_ui_create(
				prop_bone,
				property_name,
				default=1.0,
				min=0.0,
				max=1.0
			)
			prop_bone.property_overridable_library_set(f'["{property_name}"]', True)

		root_name = self.root_bone_name or settings.root_bone_name

		for socket_name, int_name in self.created_bones:
			socket_bone = obj.pose.bones[socket_name]
			int_bone = obj.pose.bones[int_name]

			if self.inherit_scale_from_root:
				root_scale = socket_bone.constraints.new('COPY_SCALE')
				root_scale.target = obj
				root_scale.subtarget = root_name

			loc_constraint = int_bone.constraints.new('COPY_LOCATION')
			loc_constraint.target = obj
			loc_constraint.subtarget = socket_name

			if self.include_scale:
				scale_constraint = int_bone.constraints.new('COPY_SCALE')
				scale_constraint.target = obj
				scale_constraint.subtarget = socket_name
				scale_constraint.mute = self.disable_scale

			rot_constraint = int_bone.constraints.new('COPY_ROTATION')
			rot_constraint.target = obj
			rot_constraint.subtarget = socket_name
			rot_constraint.name = property_name

			driver = rot_constraint.driver_add("influence").driver
			driver.type = 'AVERAGE'

			var = driver.variables.new()
			var.name = "isolation_val"
			var.type = 'SINGLE_PROP'
			var.targets[0].id = obj
			var.targets[0].data_path = f'pose.bones["{prop_bone.name}"]["{property_name}"]'

		return self
