import math
import bpy
from rigtools.assemblies.assembly_data import find_assemblies, find_org_state
from rigtools.preferences import get_preferences
from rigtools.utils.bone import duplicate_bone
from rigtools.utils.bone_collection import ensure_bone_collection
from rigtools.utils.naming import does_match_def_name, name_bone

class RIG_OT_create_corrective_bone(bpy.types.Operator):
	bl_idname = "rig.create_corrective_bone"
	bl_label = "Create Corrective Bone"
	bl_description = "Create a corrective bone that helps create the correct shape when bones are moved to extremes"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(cls, context):
		return (context.mode == 'POSE'
			and context.active_pose_bone is not None
			and len(context.selected_pose_bones) == 2)

	def execute(self, context):
		obj = context.object
		armature_data = obj.data

		corrective = context.active_pose_bone
		target = next(pb for pb in context.selected_pose_bones if pb != corrective)

		# Target bone can't be part of an assembly's mechanism bones (the ones that can get deleted)
		owners = find_assemblies(armature_data, [target.name], include_org_states=False)
		if owners:
			self.report({'ERROR'}, f"'{target.name}' belongs to assembly '{owners[0].name}'. Use the ORG bone.")
			return {'CANCELLED'}
		
		# Corrective shouldn't have any other constraint types (stacking transforms is ok)
		others = [c for c in corrective.constraints if c.type != 'TRANSFORM']
		if others:
			self.report({'ERROR'}, f"'{corrective.name}' has a {others[0].type} constraint.")
			return {'CANCELLED'}
		
		# An added protection to block DEF bones by name. Might not catch everything, but still good
		if does_match_def_name(context, target.name):
			self.report({'ERROR'}, f"'{target.name}' is a DEF bone. Use the ORG bone.")
			return {'CANCELLED'}
		if does_match_def_name(context, corrective.name):
			self.report({'ERROR'}, f"'{corrective.name}' is a DEF bone. Use the ORG bone.")
			return {'CANCELLED'}

		target_name = target.name
		corrective_name = corrective.name
		mch_name = name_bone("corrective", target_name)
		
		bpy.ops.object.mode_set(mode='EDIT')
		edit_bones = armature_data.edit_bones

		if mch_name not in edit_bones:
			target_bone = edit_bones[target_name]

			# If the target bone is part of an assembly, use the assemblies saved parent
			org_state = find_org_state(armature_data, target_name)
			if org_state:
				parent_name = org_state.parent
			else:
				parent_name = target_bone.parent.name if target_bone.parent else ""

			mch_bone = duplicate_bone(armature_data, target_bone, mch_name, 1.0)
			mch_bone.parent = edit_bones[parent_name] if parent_name else None
			mch_bone.use_deform = False

			for coll in list(mch_bone.collections):
				coll.unassign(mch_bone)
			ensure_bone_collection(armature_data, get_preferences().mch_collection_name, hidden=True).assign(mch_bone)

		bpy.ops.object.mode_set(mode='POSE')
		pose_bones = obj.pose.bones
		mch = pose_bones[mch_name]

		if not mch.constraints:
			copy = mch.constraints.new('COPY_TRANSFORMS')
			copy.target = obj
			copy.subtarget = target_name

		# Find the largest input axis on the reader
		context.view_layer.update()
		local = obj.convert_space(
			pose_bone=mch,
			matrix=mch.matrix,
			from_space='POSE',
			to_space='LOCAL',
		)
		reading = local.to_euler()
		axis = max(range(3), key=lambda i: abs(reading[i]))
		from_value = reading[axis]

		if abs(from_value) < 1e-4:
			self.report({'ERROR'},
				f"'{target_name}' is at rest. Pose it first.")
			return {'CANCELLED'}

		# Find the transforms for the corrective bone
		corrective = pose_bones[corrective_name]
		location = corrective.matrix_basis.to_translation() # matrix_basis ignores constraints
		rotation = corrective.matrix_basis.to_euler()

		apply_loc = bool(location.length > 1e-5)
		apply_rot = bool(max(abs(a) for a in rotation) > 1e-4)

		if not apply_loc and not apply_rot:
			self.report({'ERROR'},
				f"'{corrective_name}' isn't posed. Move or rotate it first.")
			return {'CANCELLED'}

		if apply_loc:
			self.add_transform(corrective, obj, mch_name, 
				axis, from_value, 'LOCATION', location)
		if apply_rot:
			self.add_transform(corrective, obj, mch_name,
				axis, from_value, 'ROTATION', rotation)

		# Clear the pose so the correction isn't applied twice			
		corrective.location = (0, 0, 0)
		corrective.rotation_quaternion = (1, 0, 0, 0)
		corrective.rotation_euler = (0, 0, 0)

		self.report({'INFO'}, f"")
		return {'FINISHED'}
	
	def add_transform(self, pose_bone, obj, mch_name,
			axis, from_value, map_to, values):
		c = pose_bone.constraints.new('TRANSFORM')
		c.name = f"Corrective {map_to.title()} ({mch_name})"
		c.target = obj
		c.subtarget = mch_name
		c.target_space = 'LOCAL'
		c.owner_space = 'LOCAL'

		c.map_from = 'ROTATION'
		c.from_rotation_mode = 'AUTO'
		axis_name = "xyz"[axis]
		# Keep the from range ordered (min < max); a negative reading
		# flips which end maps to the correction
		low, high = sorted((0.0, from_value))
		setattr(c, f"from_min_{axis_name}_rot", low)
		setattr(c, f"from_max_{axis_name}_rot", high)

		c.map_to = map_to
		suffix = "_rot" if map_to == 'ROTATION' else ""
		for i, out_name in enumerate("xyz"):
			setattr(c, f"map_to_{out_name}_from", axis_name.upper())
			if from_value < 0:
				at_low, at_high = values[i], 0.0
			else:
				at_low, at_high = 0.0, values[i]
			setattr(c, f"to_min_{out_name}{suffix}", at_low)
			setattr(c, f"to_max_{out_name}{suffix}", at_high)

		if map_to == 'ROTATION':
			c.to_euler_order = 'XYZ'
			c.mix_mode_rot = 'ADD'
		else:
			c.mix_mode = 'ADD'



classes = (
	RIG_OT_create_corrective_bone,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
