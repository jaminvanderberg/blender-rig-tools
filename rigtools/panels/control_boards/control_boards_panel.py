import bpy

from rigtools.rig_data.control_board import (
	RigToolsBoardControl, RigToolsBoardGroup, RigToolsControlBoard,
	get_control_boards, get_ordered_children,
)
from rigtools.panels.control_boards.tree_actions import get_selected_item

def list_tree_rows(armature_data):
	"""Every board, group and control, top to bottom: (path, depth, text, detail, icon)"""
	rows = []
	def add_children(group, depth):
		for child in get_ordered_children(group):
			if isinstance(child, RigToolsBoardGroup):
				flow = child.bl_rna.properties["flow"].enum_items[child.flow].name
				rows.append((child.path_from_id(), depth, child.name, flow, 'FILE_FOLDER'))
				add_children(child, depth + 1)
			else:
				icon = 'ARROW_LEFTRIGHT' if child.dimensions == '1D' else 'EMPTY_ARROWS'
				rows.append((child.path_from_id(), depth, child.bone_name, child.dimensions, icon))
	for board in get_control_boards(armature_data):
		rows.append((board.path_from_id(), 0, board.name, "", 'MESH_GRID'))
		add_children(board.root, 1)
	return rows

def draw_group_settings(layout, group):
	layout.prop(group, "flow")
	if group.flow == 'GRID':
		layout.prop(group, "columns")

class RIG_PT_control_boards(bpy.types.Panel):
	bl_label = "Control Boards"
	bl_idname = "RIG_PT_control_boards"
	bl_space_type = 'PROPERTIES'
	bl_region_type = 'WINDOW'
	bl_context = 'data'

	@classmethod
	def poll(cls, context):
		return context.object is not None and context.object.type == 'ARMATURE'

	def draw(self, context):
		layout = self.layout
		armature_data = context.object.data
		boards = armature_data.rigtools_boards

		row = layout.row()
		tree = row.box().column(align=True)
		rows = list_tree_rows(armature_data)
		if not rows:
			tree.label(text="No boards")
		for path, depth, text, detail, icon in rows:
			is_active = path == boards.active_path
			# Blender centres button text, so buttons shrink to their text to stay at the left.
			# The empty label after them fills the rest, which keeps the box full width
			full_row = tree.row()
			tree_row = full_row.row(align=True)
			tree_row.alignment = 'LEFT'
			full_row.label(text="")
			if depth:
				tree_row.separator(factor=depth * 2)
			label = f"{text}  ·  {detail}" if detail else text
			button = tree_row.operator("rig.select_board_item", text=label, icon=icon,
				emboss=is_active, depress=is_active)
			button.path = path

		buttons = row.column(align=True)
		buttons.operator("rig.add_control_board", text="", icon='ADD')
		buttons.operator("rig.add_board_group", text="", icon='NEWFOLDER')
		buttons.operator("rig.add_board_control", text="", icon='BONE_DATA')
		buttons.operator("rig.remove_board_item", text="", icon='REMOVE')
		buttons.separator()
		buttons.operator("rig.move_board_item", text="", icon='TRIA_UP').direction = 'UP'
		buttons.operator("rig.move_board_item", text="", icon='TRIA_DOWN').direction = 'DOWN'

		item = get_selected_item(armature_data)
		if item is None:
			return
		layout.use_property_split = True
		layout.use_property_decorate = False
		if isinstance(item, RigToolsControlBoard):
			col = layout.column(align=True)
			col.prop(item, "width")
			col.prop(item, "height")
			draw_group_settings(layout, item.root)
		elif isinstance(item, RigToolsBoardGroup):
			layout.prop(item, "name")
			draw_group_settings(layout, item)
		elif isinstance(item, RigToolsBoardControl):
			layout.prop(item, "bone_name", text="Bone")
			layout.prop(item, "dimensions")
			if item.dimensions == '1D':
				layout.prop(item, "direction")
				layout.prop(item, "rest")

classes = (
	RIG_PT_control_boards,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
