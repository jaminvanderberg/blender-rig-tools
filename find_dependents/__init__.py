bl_info = {
	"name": "Find Dependents",
	"author": "Jamin VanderBerg",
	"version": (1, 0, 0),
	"blender": (4, 1, 0),
	"location": "View3D > Sidebar > Find Dependents",
	"description": "List bones that depend on the active bone (children, constraints, drivers)",
	"category": "Rigging",
}

from . import find_dependents


def register():
	find_dependents.register()


def unregister():
	find_dependents.unregister()


if __name__ == "__main__":
	register()
