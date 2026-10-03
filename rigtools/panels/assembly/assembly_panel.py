import bpy
from rigtools.assemblies.assembly_data import find_assemblies
from rigtools.assemblies.delete_assembly import delete_assembly
from rigtools.utils.bone import get_selected_bones, select_bones

class RIG_OT_select_assembly(bpy.types.Operator):
	bl_description = "Select all the bones associated with the assembly"
	bl_idname = "rig.select_assembly"
	bl_label = "Select Assembly"
	bl_options = {'REGISTER', 'UNDO'}

	assembly_uid: bpy.props.StringProperty()

	def execute(self, context):
		assembly = None
		for a in context.object.data.rigtools_assemblies:
			if a.uid == self.assembly_uid:
				assembly = a
				break
		else:
			self.report({'ERROR'}, "Assembly not found")
			return {'CANCELLED'}

		names = [b.name for b in assembly.mechanism_bones] + [b.name for b in assembly.org_states]
		print(names)
		count, hidden = select_bones(context.object, names, select_hidden=True)

		self.report({'INFO'}, f"Selected {count} bone{'s' if count != 1 else ''}, {hidden} hidden")
		return {'FINISHED'}

class RIG_OT_delete_assembly(bpy.types.Operator):
	bl_description = "Delete the selected assembly"
	bl_idname = "rig.delete_assembly"
	bl_label = "Delete Assembly"
	bl_options = {'REGISTER', 'UNDO'}

	assembly_uid: bpy.props.StringProperty()

	def invoke(self, context, event):
		return context.window_manager.invoke_confirm(self, event)	

	def execute(self, context):
		try:
			assembly_name = delete_assembly(context, self.assembly_uid)
		except Exception as e:
			self.report({'ERROR'}, str(e))
			return {'CANCELLED'}

		self.report({'INFO'}, f"Assembly {assembly_name} deleted")
		return {'FINISHED'}

class RIG_PT_assembly_panel(bpy.types.Panel):
	bl_label = "Assembly"
	bl_idname = "RIG_PT_assembly_panel"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = "Rig Tools"

	@classmethod
	def poll(cls, context):
		if not (context.object and context.object.type == 'ARMATURE' and context.mode in {'EDIT_ARMATURE', 'POSE'}):
			return False
		return True

	def draw(self, context):
		layout = self.layout

		bones = get_selected_bones(context)
		assemblies = find_assemblies(context.object.data, [b.name for b in bones])
		for assembly in assemblies:
			row = layout.row(align=True)
			row.label(text=assembly.name)
			row.label(text=assembly.template_name)

			match assembly.assembly_type:
				case 'IK':
					op_id = "rig.advanced_ik_setup"
				case 'FK':
					op_id = "rig.advanced_fk_setup"
				case 'TORSO':
					op_id = "rig.advanced_torso_setup"
				case _:
					op_id = ""

			op = row.operator(op_id, text="", icon='SETTINGS')
			op.assembly_uid = assembly.uid
			op = row.operator("rig.delete_assembly", text="", icon='TRASH')
			op.assembly_uid = assembly.uid

		if not assemblies:
			layout.label(text="No assemblies selected", icon='STATUS_INFO')

classes = (
	RIG_OT_select_assembly,
	RIG_OT_delete_assembly,
	RIG_PT_assembly_panel,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
	
if __name__ == "__main__":
	try:
		unregister()
	except Exception:
		pass
	register()