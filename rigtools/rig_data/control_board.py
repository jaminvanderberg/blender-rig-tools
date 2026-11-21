import bpy
from bpy.props import CollectionProperty, EnumProperty, FloatProperty, IntProperty, StringProperty, PointerProperty

FLOW_ITEMS = (
	('HORIZONTAL', "Horizontal", "Side by side"),
	('VERTICAL', "Vertical", "Stacked"),
	('GRID', "Grid", "Rows of a set number of columns"),
)

class RigToolsBoardControl(bpy.types.PropertyGroup):
	"""One control on a board: its bone, and how it moves in its frame"""
	order: IntProperty(description="Position among the subgroups and controls within a group")
	bone_name: StringProperty()
	dimensions: EnumProperty(items=(
		('1D', "1D", "Moves along a track"),
		('2D', "2D", "Moves in a square, both directions on two axes"),
	))
	# 1D only
	direction: EnumProperty(items=(
		('HORIZONTAL', "Horizontal", "Moves left and right"),
		('VERTICAL', "Vertical", "Moves up and down"),
	))
	rest: EnumProperty(items=(
		('START', "Start", "Rests at the start and moves in one direction"),
		('CENTER', "Center", "Rests in the middle and moves in both directions"),
		('END', "End", "Rests at the end and moves in one direction"),
	), default='CENTER')

class RigToolsBoardGroup(bpy.types.PropertyGroup):
	"""Grouping of controls and subgroups within a board"""
	order: IntProperty(description="Position among the subgroups and controls within a group")
	flow: EnumProperty(items=FLOW_ITEMS)
	columns: IntProperty(default=2, min=1, description="Controls per row in a grid")
	controls: CollectionProperty(type=RigToolsBoardControl)

# A group holds groups. A class can't name itself in its own body, so it's added here
RigToolsBoardGroup.__annotations__["groups"] = CollectionProperty(type=RigToolsBoardGroup)

class RigToolsControlBoard(bpy.types.PropertyGroup):
	"""A board: its size, and the root group.  Placement determined by its root bone position"""
	width: FloatProperty(default=0.1, min=0.0001, subtype='DISTANCE',
		description="Width of the board. Its groups divide it, and track lengths follow")
	height: FloatProperty(default=0.1, min=0.0001, subtype='DISTANCE',
		description="Height of the board. Its groups divide it, and track lengths follow")
	root: PointerProperty(type=RigToolsBoardGroup)

class RigToolsControlBoards(bpy.types.PropertyGroup):
	"""Every board on the armature, plus the tree's selection"""
	items: CollectionProperty(type=RigToolsControlBoard)
	# The selected board, group or control, as its data path from the armature
	active_path: StringProperty()

def get_control_boards(armature_data):
	"""The armature's boards, in list order"""
	return armature_data.rigtools_boards.items

def get_ordered_children(group):
	"""The group's subgroups and controls, combined, in order"""
	return sorted([*group.groups, *group.controls], key=lambda child: child.order)

def renumber_children(group):
	"""Fixes group's children order before performing an edit"""
	for order, child in enumerate(get_ordered_children(group)):
		child.order = order

def _find_control_in_group(group, bone_name):
	"""Find the control for this bone within this group or any group inside it, or None"""
	for control in group.controls:
		if control.bone_name == bone_name:
			return control
	for child in group.groups:
		control = _find_control_in_group(child, bone_name)
		if control:
			return control
	return None

def find_board_control(armature_data, bone_name):
	"""(board, control) for the control on this bone, or None"""
	for board in get_control_boards(armature_data):
		control = _find_control_in_group(board.root, bone_name)
		if control:
			return board, control
	return None

classes = (
	RigToolsBoardControl,
	RigToolsBoardGroup,
	RigToolsControlBoard,
	RigToolsControlBoards,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	bpy.types.Armature.rigtools_boards = PointerProperty(type=RigToolsControlBoards)

def unregister():
	del bpy.types.Armature.rigtools_boards
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)