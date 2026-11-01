from mathutils import Euler, Vector
import bpy
from rigtools.assemblies.assembly_data import find_assemblies, find_org_state
from rigtools.preferences import get_preferences
from rigtools.rig_data.correctives import correction_end, corrective_constraints, corrective_target, find_correctives
from rigtools.rig_ui.rig_ui import flip_side_name
from rigtools.utils.bone import duplicate_bone
from rigtools.utils.bone_collection import ensure_bone_collection
from rigtools.utils.naming import does_match_def_name, name_bone
from bpy.props import BoolProperty, StringProperty

def clean(value):
	"""Snap -0.0 and small numbers to 0.0"""
	return 0.0 if abs(value) < 1e-6 else value

class CorrectiveSetup:
	def __init__(self, target_name, corrective_name):
		self.target_name = target_name
		self.corrective_name = corrective_name
		self.mch_name = name_bone("corrective", target_name)
		self.created = False

		self.location = None
		self.rotation = None
		self.axis = None
		self.from_value = None

	def mirrored(self, obj):
		"""Setup for the opposite side, or None if there isn't one"""
		target_name = flip_side_name(self.target_name)
		corrective_name = flip_side_name(self.corrective_name)
		if not target_name or not corrective_name:
			return None
		pose_bones = obj.pose.bones
		if target_name not in pose_bones or corrective_name not in pose_bones:
			return None
		return CorrectiveSetup(target_name, corrective_name)

	def validate(self, context):
		armature_data = context.object.data
		pose_bones = context.object.pose.bones

		# Target bone can't be part of an assembly's mechanism bones (the ones that can get deleted)
		owners = find_assemblies(armature_data, [self.target_name], include_org_states=False)
		if owners:
			return (f"'{self.target_name}' belongs to assembly "
				f"'{owners[0].name}'. Use the ORG bone.")
		
		# Corrective shouldn't have any other constraint types (stacking transforms is ok)
		corrective = pose_bones[self.corrective_name]
		others = [c for c in corrective.constraints if c.type != 'TRANSFORM']
		if others:
			return f"'{corrective.name}' has a {others[0].type} constraint."
		
		# An added protection to block DEF bones by name. Might not catch everything, but still good
		for name in (self.target_name, self.corrective_name):
			if does_match_def_name(name):
				return f"'{name}' is a DEF bone. Use the ORG bone."
		
		return None

	def edit_mode(self, armature_data):
		edit_bones = armature_data.edit_bones
		if self.mch_name in edit_bones:
			return
		target_bone = edit_bones[self.target_name]

		# If the target bone is part of an assembly, use the assembly's saved parent
		org_state = find_org_state(armature_data, self.target_name)
		if org_state:
			parent_name = org_state.parent
		elif target_bone.parent:
			parent_name = target_bone.parent.name
		else:
			parent_name = ""

		mch_bone = duplicate_bone(armature_data, target_bone,
			self.mch_name, 1.0)
		mch_bone.parent = edit_bones[parent_name] if parent_name else None
		mch_bone.use_deform = False

		for coll in list(mch_bone.collections):
			coll.unassign(mch_bone)
		mch_coll = ensure_bone_collection(armature_data,
			get_preferences().mch_collection_name, hidden=True)
		mch_coll.assign(mch_bone)
		self.created = True

	def capture_corrective_pose(self, obj):
		"""Store the corrective's pose. Error message if it isn't posed."""
		corrective = obj.pose.bones[self.corrective_name]
		# Find the transforms for the corrective bone
		self.location = corrective.matrix_basis.to_translation() # matrix_basis ignores constraints
		self.rotation = corrective.matrix_basis.to_euler()
		if not self.uses_location() and not self.uses_rotation():
			return (f"'{self.corrective_name}' isn't posed. "
				"Move or rotate it first.")
		return None
	
	def uses_location(self):
		return self.location.length > 1e-5

	def uses_rotation(self):
		return max(abs(a) for a in self.rotation) > 1e-4

	def pose_mode(self, obj):
		mch = obj.pose.bones[self.mch_name]
		if not mch.constraints:
			copy = mch.constraints.new('COPY_TRANSFORMS')
			copy.target = obj
			copy.subtarget = self.target_name

	def capture_target_pose(self, obj):
		"""Store the largest rotation axis on the reader. Error message if
		the target is at rest. Call context.view_layer.update() first."""
		mch = obj.pose.bones[self.mch_name]
		local = obj.convert_space(
			pose_bone=mch,
			matrix=mch.matrix,
			from_space='POSE',
			to_space='LOCAL',
		)
		reading = local.to_euler()
		# Find the largest input axis on the reader
		self.axis = max(range(3), key=lambda i: abs(reading[i]))
		self.from_value = reading[self.axis]
		if abs(self.from_value) < 1e-4:
			return f"'{self.target_name}' is at rest. Pose it first."
		return None
	
	def apply(self, obj):
		"""Add the Transformation constraints and clear the corrective's pose"""
		if self.uses_location():
			self.add_transform(obj, self.axis, self.from_value,
				'LOCATION', self.location)
		if self.uses_rotation():
			self.add_transform(obj, self.axis, self.from_value,
				'ROTATION', self.rotation)

		# Clear the pose so the correction isn't applied twice
		corrective = obj.pose.bones[self.corrective_name]
		corrective.location = (0, 0, 0)
		corrective.rotation_quaternion = (1, 0, 0, 0)
		corrective.rotation_euler = (0, 0, 0)

	def mirror_from(self, source):
		"""Copy source's captured values, flipped across X.
		Assumes symmetric rest rolls: location X flips, rotation Y and Z flip"""
		self.axis = source.axis
		if source.axis == 0:
			self.from_value = source.from_value
		else:
			self.from_value = -source.from_value
		x, y, z = source.location
		self.location = Vector((-x, y, z))
		rx, ry, rz = source.rotation
		self.rotation = Euler((rx, -ry, -rz))

	@classmethod
	def from_constraint(cls, obj, bone_name, constraint):
		"""Setup with values read back from an existing corrective constraint"""
		setup = cls(corrective_target(obj, constraint), bone_name)
		axis_name = constraint.map_to_x_from.lower()
		end = correction_end(constraint)
		setup.axis = "xyz".index(axis_name)
		setup.from_value = getattr(constraint, f"from_{end}_{axis_name}_rot")

		suffix = "_rot" if constraint.map_to == 'ROTATION' else ""
		values = [getattr(constraint, f"to_{end}_{out}{suffix}")
			for out in "xyz"]
		# mirror_from flips both, so the unused one is zeros
		if constraint.map_to == 'ROTATION':
			setup.location = Vector((0, 0, 0))
			setup.rotation = Euler(values)
		else:
			setup.location = Vector(values)
			setup.rotation = Euler((0, 0, 0))
		return setup

	
	def add_transform(self, obj, axis, from_value, map_to, values):
		pose_bone = obj.pose.bones[self.corrective_name]
		c = pose_bone.constraints.new('TRANSFORM')
		c.name = f"Corrective {map_to.title()} ({self.mch_name})"
		c.target = obj
		c.subtarget = self.mch_name
		c.target_space = 'LOCAL'
		c.owner_space = 'LOCAL'

		c.map_from = 'ROTATION'
		c.from_rotation_mode = 'AUTO'
		axis_name = "xyz"[axis]
		# Keep the from range ordered (min < max); a negative reading
		# flips which end maps to the correction
		low, high = sorted((0.0, from_value))
		setattr(c, f"from_min_{axis_name}_rot", clean(low))
		setattr(c, f"from_max_{axis_name}_rot", clean(high))

		c.map_to = map_to
		suffix = "_rot" if map_to == 'ROTATION' else ""
		for i, out_name in enumerate("xyz"):
			setattr(c, f"map_to_{out_name}_from", axis_name.upper())
			if from_value < 0:
				at_low, at_high = values[i], 0.0
			else:
				at_low, at_high = 0.0, values[i]
			setattr(c, f"to_min_{out_name}{suffix}", clean(at_low))
			setattr(c, f"to_max_{out_name}{suffix}", clean(at_high))

		if map_to == 'ROTATION':
			c.to_euler_order = 'XYZ'
			c.mix_mode_rot = 'ADD'
		else:
			c.mix_mode = 'ADD'

		return c

	def remove_mch(self, edit_bones):
		"""Edit mode only. Remove the MCH if this setup created it."""
		if self.created:
			edit_bones.remove(edit_bones[self.mch_name])	


class RIG_OT_create_corrective_bone(bpy.types.Operator):
	bl_idname = "rig.create_corrective_bone"
	bl_label = "Create Corrective Bone"
	bl_description = "Create a corrective bone that helps create the correct shape when bones are moved to extremes"
	bl_options = {'REGISTER', 'UNDO'}

	mirror: BoolProperty(
		name="Mirror",
		description="Also create the corrective on the opposite side",
		default=True,
	)

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

		source = CorrectiveSetup(target.name, corrective.name)
		setups = [source]
		mirrored = source.mirrored(obj) if self.mirror else None
		if mirrored:
			setups.append(mirrored)

		for setup in setups:
			error = setup.validate(context)
			if error:
				self.report({'ERROR'}, error)
				return {'CANCELLED'}
		
		error = source.capture_corrective_pose(obj)
		if error:
			self.report({'ERROR'}, error)
			return {'CANCELLED'}
		
		bpy.ops.object.mode_set(mode='EDIT')
		for setup in setups:
			setup.edit_mode(armature_data)

		bpy.ops.object.mode_set(mode='POSE')
		for setup in setups:
			setup.pose_mode(obj)

		context.view_layer.update()
		error = source.capture_target_pose(obj)
		if error:
			bpy.ops.object.mode_set(mode='EDIT')
			for setup in setups:
				setup.remove_mch(armature_data.edit_bones)
			bpy.ops.object.mode_set(mode='POSE')
			self.report({'ERROR'}, error)
			return {'CANCELLED'}
		
		if mirrored:
			mirrored.mirror_from(source)
		for setup in setups:
			setup.apply(obj)
		if self.mirror and not mirrored:
			self.report({'INFO'}, "No mirror found; created one side only.")
		elif mirrored:
			self.report({'INFO'}, "Successfully created mirrored corrective bones.")
		else:
			self.report({'INFO'}, "Successfully created corrective bone.")

		return {'FINISHED'}
	
class RIG_OT_delete_corrective(bpy.types.Operator):
	bl_idname = "rig.delete_corrective"
	bl_label = "Delete Corrective"
	bl_description = ("Remove this corrective constraint, "
		"and its MCH if nothing else uses it")
	bl_options = {'REGISTER', 'UNDO'}

	bone_name: StringProperty()
	constraint_name: StringProperty()

	def execute(self, context):
		obj = context.object
		pose_bone = obj.pose.bones[self.bone_name]
		constraint = pose_bone.constraints[self.constraint_name]
		mch_name = constraint.subtarget
		pose_bone.constraints.remove(constraint)

		# Keep the MCH if another corrective still reads it
		still_used = any(c.subtarget == mch_name
			for _, c in find_correctives(obj))
		if not still_used:
			bpy.ops.object.mode_set(mode='EDIT')
			edit_bones = obj.data.edit_bones
			edit_bones.remove(edit_bones[mch_name])
			bpy.ops.object.mode_set(mode='POSE')

		self.report({'INFO'}, f"Removed '{self.constraint_name}'.")
		return {'FINISHED'}
	
class RIG_OT_mirror_corrective(bpy.types.Operator):
	bl_idname = "rig.mirror_corrective"
	bl_label = "Mirror Corrective"
	bl_description = ("Copy this corrective to the opposite side, "
		"replacing the matching one there")
	bl_options = {'REGISTER', 'UNDO'}

	bone_name: StringProperty()
	constraint_name: StringProperty()

	def execute(self, context):
		obj = context.object
		pose_bone = obj.pose.bones[self.bone_name]
		constraint = pose_bone.constraints[self.constraint_name]

		source = CorrectiveSetup.from_constraint(obj, self.bone_name,
			constraint)
		mirrored = source.mirrored(obj)
		if not mirrored:
			self.report({'ERROR'},
				f"No mirror found for '{self.bone_name}'.")
			return {'CANCELLED'}

		error = mirrored.validate(context)
		if error:
			self.report({'ERROR'}, error)
			return {'CANCELLED'}

		# Only switch modes if the opposite MCH doesn't exist yet
		if mirrored.mch_name not in obj.pose.bones:
			bpy.ops.object.mode_set(mode='EDIT')
			mirrored.edit_mode(obj.data)
			bpy.ops.object.mode_set(mode='POSE')
		mirrored.pose_mode(obj)

		# Replace the opposite side's matching corrective so mirroring twice doesn't stack
		mirror_bone = obj.pose.bones[mirrored.corrective_name]
		for old in corrective_constraints(mirror_bone):
			if (old.subtarget == mirrored.mch_name
					and old.map_to == constraint.map_to):
				mirror_bone.constraints.remove(old)

		mirrored.mirror_from(source)
		if constraint.map_to == 'ROTATION':
			values = mirrored.rotation
		else:
			values = mirrored.location
		new = mirrored.add_transform(obj, mirrored.axis,
			mirrored.from_value, constraint.map_to, values)
		new.influence = constraint.influence

		self.report({'INFO'}, f"Mirrored to '{mirrored.corrective_name}'.")
		return {'FINISHED'}

addon_keymaps = []

def draw_pose_menu(self, context):
	self.layout.operator(RIG_OT_create_corrective_bone.bl_idname)

classes = (
	RIG_OT_create_corrective_bone,
	RIG_OT_delete_corrective,
	RIG_OT_mirror_corrective,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	bpy.types.VIEW3D_MT_pose_constraints.append(draw_pose_menu)

	keyconfig = bpy.context.window_manager.keyconfigs.addon
	if keyconfig:
		km = keyconfig.keymaps.new(name="Pose", space_type='EMPTY')
		kmi = km.keymap_items.new(RIG_OT_create_corrective_bone.bl_idname,
			'C', 'PRESS', shift=True, alt=True)
		addon_keymaps.append((km, kmi))

def unregister():
	for km, kmi in addon_keymaps:
		km.keymap_items.remove(kmi)
	addon_keymaps.clear()
	bpy.types.VIEW3D_MT_pose_constraints.remove(draw_pose_menu)

	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)

