from dataclasses import dataclass

import bpy
from rigtools.assemblies.assembly_data import find_assemblies, find_org_state
from rigtools.preferences import get_preferences
from rigtools.rig_data.correctives import (correction_end, corrective_constraints,
	corrective_target, find_box, find_corrective_boxes, find_correctives, get_box_base_name,
	join_constraints, make_box_names, read_box_range, read_input,
	remove_box_properties_if_unused)
from rigtools.rig_ui.rig_ui import flip_side_name
from rigtools.utils.bone import duplicate_bone
from rigtools.utils.bone_collection import ensure_bone_collection
from rigtools.utils.naming import does_match_def_name, name_bone
from bpy.props import BoolProperty, StringProperty

EXTRAPOLATE_DESCRIPTION = ("Keep correcting past Full instead of stopping there. "
	"Works both ways: below Begin it corrects backward, so a joint bent the other way "
	"moves the corrective the wrong way, and a dead zone no longer holds still")

def clean(value):
	"""Snap -0.0 and small numbers to 0.0"""
	return 0.0 if abs(value) < 1e-6 else value

@dataclass
class Correction:
	"""One constraint's output: what it moves, by how much at Full, and its settings"""
	map_to: str # 'LOCATION' or 'ROTATION'
	values: tuple # (x, y, z) at full strength
	influence: float = 1.0
	extrapolate: bool = False

class CorrectiveSetup:
	def __init__(self, target_name, corrective_name):
		self.target_name = target_name
		self.corrective_name = corrective_name
		self.mch_name = name_bone("corrective", target_name)
		self.created = False

		self.location = None
		self.rotation = None
		self.from_channel = None # 'ROTATION' or 'LOCATION': what the driving bone's pose is read from
		self.axis = None
		self.from_begin = 0.0 # the reading where the correction starts
		self.from_full = None # the reading where the correction is fully applied
		self.corrections = [] # one Correction per constraint

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
		self.corrections = []
		if self.uses_location():
			self.corrections.append(Correction('LOCATION', tuple(self.location)))
		if self.uses_rotation():
			self.corrections.append(Correction('ROTATION', tuple(self.rotation)))
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
		"""Store the largest axis on the reader: rotation if the target turned,
		otherwise location. Error message if the target is at rest.
		Call context.view_layer.update() first."""
		mch = obj.pose.bones[self.mch_name]
		local = obj.convert_space(
			pose_bone=mch,
			matrix=mch.matrix,
			from_space='POSE',
			to_space='LOCAL',
		)
		# Rotation first, so joints that also moved read as before
		rotation = local.to_euler()
		location = local.to_translation()
		if max(abs(a) for a in rotation) >= 1e-4:
			self.from_channel, reading = 'ROTATION', rotation
		elif location.length > 1e-5:
			self.from_channel, reading = 'LOCATION', location
		else:
			return f"'{self.target_name}' is at rest. Pose it first."
		# Find the largest input axis on the reader
		self.axis = max(range(3), key=lambda i: abs(reading[i]))
		self.from_full = reading[self.axis]
		return None

	def read_input(self):
		"""What the constraints read, matching read_input in rig_data/correctives.py"""
		return (self.mch_name, self.from_channel, "XYZ"[self.axis], self.from_full < 0)

	def get_box_base_name(self):
		return get_box_base_name(self.mch_name, self.from_channel, self.axis, self.from_full)

	def apply(self, obj, box_name):
		"""Add the Transformation constraints, joined as box_name unless it's None,
		and clear the corrective's pose"""
		self.add_constraints(obj, box_name)

		# Clear the pose so the correction isn't applied twice
		corrective = obj.pose.bones[self.corrective_name]
		corrective.location = (0, 0, 0)
		corrective.rotation_quaternion = (1, 0, 0, 0)
		corrective.rotation_euler = (0, 0, 0)

	def add_constraints(self, obj, box_name):
		"""One constraint per correction, joined as box_name unless it's None.
		Returns the constraints"""
		constraints = [self.add_transform(obj, correction) for correction in self.corrections]
		if box_name is not None:
			pose_bone = obj.pose.bones[self.corrective_name]
			join_constraints(pose_bone, constraints, box_name, self.from_begin, self.from_full)
		return constraints

	def mirror_from(self, source):
		"""Copy source's captured values, flipped across X.
		Assumes symmetric rest rolls: location X flips, rotation Y and Z flip"""
		self.from_channel = source.from_channel
		self.axis = source.axis
		if source.from_channel == 'LOCATION':
			flips = source.axis == 0
		else:
			flips = source.axis != 0
		sign = -1 if flips else 1
		self.from_full = sign * source.from_full
		self.from_begin = sign * source.from_begin
		self.corrections = []
		for correction in source.corrections:
			x, y, z = correction.values
			if correction.map_to == 'ROTATION':
				values = (x, -y, -z)
			else:
				values = (-x, y, z)
			self.corrections.append(Correction(correction.map_to, values,
				correction.influence, correction.extrapolate))

	@classmethod
	def from_box(cls, obj, pose_bone, box):
		"""Setup with values read back from an existing corrective box"""
		first = box.constraints[0]
		setup = cls(corrective_target(obj, first), pose_bone.name)
		setup.from_channel = first.map_from
		setup.axis = "xyz".index(first.map_to_x_from.lower())
		setup.from_begin, setup.from_full = read_box_range(pose_bone, box)
		for constraint in box.constraints:
			end = correction_end(pose_bone, constraint)
			suffix = "_rot" if constraint.map_to == 'ROTATION' else ""
			values = tuple(getattr(constraint, f"to_{end}_{out}{suffix}") for out in "xyz")
			setup.corrections.append(Correction(constraint.map_to, values,
				constraint.influence, constraint.use_motion_extrapolate))
		return setup

	def add_transform(self, obj, correction):
		map_to, values = correction.map_to, correction.values
		pose_bone = obj.pose.bones[self.corrective_name]
		c = pose_bone.constraints.new('TRANSFORM')
		c.name = f"Corrective {map_to.title()} ({self.mch_name})"
		c.target = obj
		c.subtarget = self.mch_name
		c.target_space = 'LOCAL'
		c.owner_space = 'LOCAL'
		c.influence = correction.influence
		c.use_motion_extrapolate = correction.extrapolate

		c.map_from = self.from_channel
		if self.from_channel == 'ROTATION':
			c.from_rotation_mode = 'AUTO'
		from_suffix = "_rot" if self.from_channel == 'ROTATION' else ""
		axis_name = "xyz"[self.axis]
		# Full goes at max, or at min for a negative reading, so the range stays ordered;
		# Begin takes the other end
		full_end = "min" if self.from_full < 0 else "max"
		begin_end = "max" if full_end == "min" else "min"
		setattr(c, f"from_{full_end}_{axis_name}{from_suffix}", clean(self.from_full))
		setattr(c, f"from_{begin_end}_{axis_name}{from_suffix}", clean(self.from_begin))

		c.map_to = map_to
		suffix = "_rot" if map_to == 'ROTATION' else ""
		for i, out_name in enumerate("xyz"):
			setattr(c, f"map_to_{out_name}_from", axis_name.upper())
			setattr(c, f"to_{full_end}_{out_name}{suffix}", clean(values[i]))
			setattr(c, f"to_{begin_end}_{out_name}{suffix}", 0.0)

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
		# A capture that both moved and turned the corrective starts as one joined box. Both
		# sides share a name suffix, so Mirror finds the matching box later
		box_names = [None] * len(setups)
		if len(source.corrections) > 1:
			box_names = make_box_names([(obj.pose.bones[s.corrective_name], s.get_box_base_name())
				for s in setups])
		for setup, box_name in zip(setups, box_names):
			setup.apply(obj, box_name)
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
	bl_description = ("Remove this corrective (every constraint in its box), "
		"and its MCH if nothing else uses it")
	bl_options = {'REGISTER', 'UNDO'}

	bone_name: StringProperty()
	constraint_name: StringProperty() # any constraint in the box

	def execute(self, context):
		obj = context.object
		pose_bone = obj.pose.bones[self.bone_name]
		box = find_box(pose_bone, self.constraint_name)
		if box is None:
			self.report({'ERROR'}, f"'{self.constraint_name}' isn't a corrective.")
			return {'CANCELLED'}
		mch_name = box.constraints[0].subtarget
		# Removing a constraint also removes the drivers on its own fields
		for constraint in box.constraints:
			pose_bone.constraints.remove(constraint)
		if box.name is not None:
			remove_box_properties_if_unused(pose_bone, box.name)

		# Keep the MCH if another corrective still reads it
		still_used = any(c.subtarget == mch_name
			for _, c in find_correctives(obj))
		if not still_used:
			bpy.ops.object.mode_set(mode='EDIT')
			edit_bones = obj.data.edit_bones
			edit_bones.remove(edit_bones[mch_name])
			bpy.ops.object.mode_set(mode='POSE')

		self.report({'INFO'}, f"Removed the corrective from '{self.bone_name}'.")
		return {'FINISHED'}

class RIG_OT_mirror_corrective(bpy.types.Operator):
	bl_idname = "rig.mirror_corrective"
	bl_label = "Mirror Corrective"
	bl_description = ("Copy this corrective to the opposite side, "
		"replacing the matching one there")
	bl_options = {'REGISTER', 'UNDO'}

	bone_name: StringProperty()
	constraint_name: StringProperty() # any constraint in the box

	def execute(self, context):
		obj = context.object
		pose_bone = obj.pose.bones[self.bone_name]
		box = find_box(pose_bone, self.constraint_name)
		if box is None:
			self.report({'ERROR'}, f"'{self.constraint_name}' isn't a corrective.")
			return {'CANCELLED'}

		source = CorrectiveSetup.from_box(obj, pose_bone, box)
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
		mirrored.mirror_from(source)
		mirror_bone = obj.pose.bones[mirrored.corrective_name]

		# A joined box mirrors to the box with the same suffix on the other side
		mirror_box_name = None
		if box.name is not None:
			base = source.get_box_base_name()
			suffix = box.name[len(base):] if box.name.startswith(base) else ""
			mirror_box_name = mirrored.get_box_base_name() + suffix

		# Replace what's there so mirroring twice doesn't stack: the same-named box on the other
		# side, whole, so it becomes a copy of this one; and split constraints there with the
		# same input and an output this box has. Other joined boxes on the same input are
		# separate captures, and are left alone
		outputs = {correction.map_to for correction in source.corrections}
		replaced = []
		for other in find_corrective_boxes(mirror_bone):
			if other.name is not None and other.name == mirror_box_name:
				replaced += other.constraints
			elif other.name is None:
				replaced += [c for c in other.constraints
					if c.map_to in outputs and read_input(mirror_bone, c) == mirrored.read_input()]
		for constraint in replaced:
			mirror_bone.constraints.remove(constraint)

		mirrored.add_constraints(obj, mirror_box_name)

		self.report({'INFO'}, f"Mirrored to '{mirrored.corrective_name}'.")
		return {'FINISHED'}

class RIG_OT_set_corrective_extrapolate(bpy.types.Operator):
	bl_idname = "rig.set_corrective_extrapolate"
	bl_label = "Extrapolate"
	bl_description = EXTRAPOLATE_DESCRIPTION
	bl_options = {'REGISTER', 'UNDO'}

	bone_name: StringProperty(options={'HIDDEN'})
	constraint_name: StringProperty(options={'HIDDEN'}) # any constraint in the box
	extrapolate: BoolProperty(name="Extrapolate", description=EXTRAPOLATE_DESCRIPTION)

	def execute(self, context):
		pose_bone = context.object.pose.bones.get(self.bone_name)
		box = find_box(pose_bone, self.constraint_name) if pose_bone else None
		if box is None:
			self.report({'ERROR'}, f"'{self.constraint_name}' isn't a corrective.")
			return {'CANCELLED'}
		# Every constraint in the box, so a joined box stays one thing
		for constraint in box.constraints:
			constraint.use_motion_extrapolate = self.extrapolate
		return {'FINISHED'}

addon_keymaps = []

def draw_pose_menu(self, context):
	self.layout.operator(RIG_OT_create_corrective_bone.bl_idname)

classes = (
	RIG_OT_create_corrective_bone,
	RIG_OT_delete_corrective,
	RIG_OT_mirror_corrective,
	RIG_OT_set_corrective_extrapolate,
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

