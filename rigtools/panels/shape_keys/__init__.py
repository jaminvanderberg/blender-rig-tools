from rigtools.panels.shape_keys import (connect, extent_slider, key_actions, key_combine, key_curve,
	limits, mirror, reverse, shape_keys_panel, split, symmetrize)

modules = (
	limits,
	extent_slider,
	connect,
	symmetrize,
	split,
	mirror,
	reverse,
	key_actions,
	key_curve,
	key_combine,
	shape_keys_panel,
)

def register():
	for mod in modules:
		mod.register()

def unregister():
	for mod in reversed(modules):
		mod.unregister()

