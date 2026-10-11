import bpy

class AssemblyTransactionError(RuntimeError):
	pass

def _rollback():
	wm = bpy.context.window_manager
	with bpy.context.temp_override(window=wm.windows[0]):
		bpy.ops.object.mode_set(mode='POSE')
		bpy.ops.ed.undo_push(message="Failed assembly rebuild")
		bpy.ops.ed.undo()

def run_assembly_transaction(operation, *, rollback=True):
	try:
		return operation()
	except Exception as e:
		if rollback:
			bpy.app.timers.register(_rollback)
		raise AssemblyTransactionError(str(e)) from None
