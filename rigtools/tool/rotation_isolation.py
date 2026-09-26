from rigtools.utils.bone import generate_bone_name, set_bone_collection
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
		disable_scale: bool = False
	):
		self.property_name = property_name
		self.mch_collection_name = mch_collection_name
		self.include_scale = include_scale
		self.disable_scale = disable_scale

		self.created_bones = None

	def edit_mode(self, context, armature_data, bone_names):
		prefs = get_preferences()
		settings = get_armature_settings(armature_data, context)

		root_bone = armature_data.edit_bones.get(settings.root_bone_name)

		bpy.ops.armature.select_all(action='DESELECT')

		self.created_bones = []
		for bone_name in bone_names:
			bone = armature_data.edit_bones[bone_name]

			socket_name = generate_bone_name(bone.name, prefs.socket_template)
			socket_bone = armature_data.edit_bones.new(socket_name)

			socket_bone.head = bone.head.copy()
			socket_bone.tail = socket_bone.head + mathutils.Vector((0.0, 0.0, bone.length * 0.5))
			socket_bone.roll = 0.0
			socket_bone.parent = bone.parent

			int_name = generate_bone_name(bone.name, prefs.int_template)
			int_bone = armature_data.edit_bones.new(int_name)

			int_bone.head = bone.head.copy()
			int_bone.tail = socket_bone.tail
			int_bone.length = bone.length * 0.4
			int_bone.roll = 0.0

			int_bone.parent = root_bone

			if self.mch_collection_name:
				set_bone_collection(armature_data, int_bone, self.mch_collection_name)
				set_bone_collection(armature_data, socket_bone, self.mch_collection_name)
			elif prefs.mch_collection_name:
				set_bone_collection(armature_data, int_bone, prefs.mch_collection_name)
				set_bone_collection(armature_data, socket_bone, prefs.mch_collection_name)
			else:
				for coll in bone.collections:
					coll.assign(socket_bone)
					coll.assign(int_bone)

			bone.use_connect = False
			bone.parent = int_bone

			self.created_bones.append((socket_bone.name, int_bone.name))
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

		for socket_name, int_name in self.created_bones:
			int_bone = obj.pose.bones[int_name]

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