import re

import bpy
from bpy.props import EnumProperty, StringProperty

from rigtools.rig_data.control_board import (
	RigToolsBoardControl, RigToolsBoardGroup, RigToolsControlBoard,
	get_control_boards, get_ordered_children, renumber_children,
)

# rigtools_boards.items[0].root.groups[1] -> ("rigtools_boards.items[0].root", "groups", 1)
CHILD_PATH = re.compile(r"^(.*)\.(groups|controls)\[(\d+)\]$")

def get_selected_item(armature_data):
	"""The selected board, group or control, or None"""
	path = armature_data.rigtools_boards.active_path
	if not path:
		return None
	try:
		return armature_data.path_resolve(path)
	except ValueError:
		return None

def get_parent_group(armature_data, item):
	"""The group holding this group or control, or None for a board"""
	match = CHILD_PATH.match(item.path_from_id())
	if not match:
		return None
	return armature_data.path_resolve(match.group(1))

def get_target_group(armature_data, item):
	"""Where a new group or control goes: into the selected board or group, or beside the selected control"""
	if isinstance(item, RigToolsControlBoard):
		return item.root
	if isinstance(item, RigToolsBoardGroup):
		return item
	return get_parent_group(armature_data, item)

def find_free_control_name(armature_data, base_name="Control"):
	"""Control, Control.001... the first one not used by a bone or another control"""
	used = set(armature_data.bones.keys())
	def collect(group):
		used.update(control.bone_name for control in group.controls)
		for child in group.groups:
			collect(child)
	for board in get_control_boards(armature_data):
		collect(board.root)
	name = base_name
	number = 0
	while name in used:
		number += 1
		name = f"{base_name}.{number:03d}"
	return name

class BoardTreeOperator:
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(cls, context):
		return context.object is not None and context.object.type == 'ARMATURE'

class RIG_OT_select_board_item(BoardTreeOperator, bpy.types.Operator):
	bl_idname = "rig.select_board_item"
	bl_label = "Select"
	bl_description = "Select this board, group or control"

	path: StringProperty(options={'SKIP_SAVE'})

	def execute(self, context):
		context.object.data.rigtools_boards.active_path = self.path
		return {'FINISHED'}

class RIG_OT_add_board_group(BoardTreeOperator, bpy.types.Operator):
	bl_idname = "rig.add_board_group"
	bl_label = "Add Group"
	bl_description = "Add a group to the selected board or group"

	def execute(self, context):
		armature_data = context.object.data
		item = get_selected_item(armature_data)
		if item is None:
			self.report({'ERROR'}, "Select a board or group first")
			return {'CANCELLED'}
		parent = get_target_group(armature_data, item)
		renumber_children(parent)
		group = parent.groups.add()
		group.name = "Group"
		group.order = len(parent.groups) + len(parent.controls)
		armature_data.rigtools_boards.active_path = group.path_from_id()
		return {'FINISHED'}

class RIG_OT_add_board_control(BoardTreeOperator, bpy.types.Operator):
	bl_idname = "rig.add_board_control"
	bl_label = "Add Control"
	bl_description = "Add a control to the selected board or group"

	def execute(self, context):
		armature_data = context.object.data
		item = get_selected_item(armature_data)
		if item is None:
			self.report({'ERROR'}, "Select a board or group first")
			return {'CANCELLED'}
		parent = get_target_group(armature_data, item)
		renumber_children(parent)
		control = parent.controls.add()
		# Prototype: data only, no bone yet
		control.bone_name = find_free_control_name(armature_data)
		control.order = len(parent.groups) + len(parent.controls)
		armature_data.rigtools_boards.active_path = control.path_from_id()
		return {'FINISHED'}

class RIG_OT_remove_board_item(BoardTreeOperator, bpy.types.Operator):
	bl_idname = "rig.remove_board_item"
	bl_label = "Remove"
	bl_description = "Remove the selected group or control, and everything inside it"

	def execute(self, context):
		armature_data = context.object.data
		item = get_selected_item(armature_data)
		if item is None:
			return {'CANCELLED'}
		if isinstance(item, RigToolsControlBoard):
			self.report({'ERROR'}, "Removing boards isn't built yet")
			return {'CANCELLED'}
		parent = get_parent_group(armature_data, item)
		_parent_path, collection_name, index = CHILD_PATH.match(item.path_from_id()).groups()
		getattr(parent, collection_name).remove(int(index))
		renumber_children(parent)
		# The root group has no row of its own, so select its board instead
		armature_data.rigtools_boards.active_path = parent.path_from_id().removesuffix(".root")
		return {'FINISHED'}

class RIG_OT_move_board_item(BoardTreeOperator, bpy.types.Operator):
	bl_idname = "rig.move_board_item"
	bl_label = "Move"
	bl_description = "Move the selected item up or down among its neighbours"

	direction: EnumProperty(items=(('UP', "Up", ""), ('DOWN', "Down", "")))

	def execute(self, context):
		armature_data = context.object.data
		boards = armature_data.rigtools_boards
		item = get_selected_item(armature_data)
		if item is None:
			return {'CANCELLED'}
		step = -1 if self.direction == 'UP' else 1

		if isinstance(item, RigToolsControlBoard):
			index = list(boards.items).index(item)
			new_index = index + step
			if not 0 <= new_index < len(boards.items):
				return {'CANCELLED'}
			boards.items.move(index, new_index)
			boards.active_path = boards.items[new_index].path_from_id()
			return {'FINISHED'}

		# Groups and controls only swap order numbers, so their paths don't change
		parent = get_parent_group(armature_data, item)
		renumber_children(parent)
		children = get_ordered_children(parent)
		index = item.order
		new_index = index + step
		if not 0 <= new_index < len(children):
			return {'CANCELLED'}
		children[index].order, children[new_index].order = new_index, index
		return {'FINISHED'}

classes = (
	RIG_OT_select_board_item,
	RIG_OT_add_board_group,
	RIG_OT_add_board_control,
	RIG_OT_remove_board_item,
	RIG_OT_move_board_item,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
