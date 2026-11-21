from rigtools.panels.control_boards import board_actions, tree_actions, control_boards_panel

modules = (
	board_actions,
	tree_actions,
	control_boards_panel,
)

def register():
	for mod in modules:
		mod.register()

def unregister():
	for mod in reversed(modules):
		mod.unregister()
