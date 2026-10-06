import bpy

class AssemblyTransactionError(RuntimeError):
    pass

def run_assembly_transaction(operation):
    bpy.ops.ed.undo_push(message="Before assembly rebuild")

    try:
        return operation()
    except Exception as e:
        message = str(e)
        try:
            bpy.ops.ed.undo()
        except Exception as rollback_error:
            raise AssemblyTransactionError(
                f"{message}; rollback failed: {rollback_error}"
            ) from rollback_error

        raise AssemblyTransactionError(message) from None