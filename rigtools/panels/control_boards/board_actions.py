import bpy
from mathutils import Vector

from rigtools.armature_settings import get_armature_settings
from rigtools.rig_data.control_board import get_control_boards
from rigtools.utils.bone_collection import set_bone_collection
from rigtools.utils.naming import bone_template

BOARDS_COLLECTION = "Control Boards"
POSITION_PIN = "Board Position"
SCALE_PIN = "Board Scale"

def get_board_bone_name(board_name):
	return bone_template("board").format(name=board_name)

def find_free_board_name(armature_data, base_name="Board"):
	"""Board, Board.001, Board.002... the first one not used by a board or its bone"""
	board_names = {board.name for board in get_control_boards(armature_data)}
	name = base_name
	number = 0
	while name in board_names or get_board_bone_name(name) in armature_data.bones:
		number += 1
		name = f"{base_name}.{number:03d}"
	return name

def create_board_bone(armature_data, bone_name, prop_bone_name, board_name, board_count):
	"""The board's root bone, beside the property bone and in proportion to it, pointing +Y.
	Each new board goes further right, so boards don't stack. Call in Edit Mode"""
	edit_bones = armature_data.edit_bones
	prop_bone = edit_bones[prop_bone_name]
	length = prop_bone.length
	board_bone = edit_bones.new(bone_name)
	board_bone.head = prop_bone.head + Vector((length * 2 * (board_count + 1), 0, 0))
	board_bone.tail = board_bone.head + Vector((0, length, 0))
	board_bone.roll = 0
	board_bone.parent = prop_bone.parent
	board_bone.use_deform = False
	set_bone_collection(armature_data, board_bone, board_name, BOARDS_COLLECTION)

def add_board_pins(pose_bone):
	"""Hold the root bone where the board's sliders put it, whatever the pose says"""
	position = pose_bone.constraints.new('LIMIT_LOCATION')
	position.name = POSITION_PIN
	position.owner_space = 'LOCAL'
	for axis in "xyz":
		setattr(position, f"use_min_{axis}", True)
		setattr(position, f"use_max_{axis}", True)
	scale = pose_bone.constraints.new('LIMIT_SCALE')
	scale.name = SCALE_PIN
	scale.owner_space = 'LOCAL'
	for axis in "xyz":
		setattr(scale, f"use_min_{axis}", True)
		setattr(scale, f"use_max_{axis}", True)
		setattr(scale, f"min_{axis}", 1.0)
		setattr(scale, f"max_{axis}", 1.0)

class RIG_OT_add_control_board(bpy.types.Operator):
	bl_idname = "rig.add_control_board"
	bl_label = "Add Control Board"
	bl_description = "Add a control board beside the property bone"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(cls, context):
		return context.object is not None and context.object.type == 'ARMATURE'

	def execute(self, context):
		armature_obj = context.object
		armature_data = armature_obj.data
		prop_bone_name = get_armature_settings(armature_data, context).property_bone_name
		if prop_bone_name not in armature_data.bones:
			self.report({'ERROR'}, f"The rig has no property bone ('{prop_bone_name}'). "
				"Set one in Armature Settings")
			return {'CANCELLED'}

		board_name = find_free_board_name(armature_data)
		bone_name = get_board_bone_name(board_name)
		mode = armature_obj.mode
		bpy.ops.object.mode_set(mode='EDIT')
		create_board_bone(armature_data, bone_name, prop_bone_name, board_name,
			len(get_control_boards(armature_data)))
		bpy.ops.object.mode_set(mode='POSE')
		add_board_pins(armature_obj.pose.bones[bone_name])
		bpy.ops.object.mode_set(mode=mode)

		boards = armature_data.rigtools_boards
		board = boards.items.add()
		board.name = board_name
		boards.active_path = board.path_from_id()
		return {'FINISHED'}

classes = (
	RIG_OT_add_control_board,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
