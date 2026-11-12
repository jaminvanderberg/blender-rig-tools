from rigtools.panels.shape_keys import connect, key_curve, symmetrize, split, mirror, reverse, key_actions, shape_keys_panel

modules = (
	connect,
	symmetrize,
	split,
	mirror,
	reverse,
	key_actions,
	key_curve,
	shape_keys_panel,
)

def register():
	for mod in modules:
		mod.register()

def unregister():
	for mod in reversed(modules):
		mod.unregister()

