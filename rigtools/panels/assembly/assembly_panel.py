import bpy
from rigtools.armature_settings import CURRENT_RIG_DATA_VERSION, needs_rig_upgrade
from rigtools.assemblies.assembly_data import find_assemblies, find_assembly
from rigtools.assemblies.config_registry import iterate_configs
from rigtools.assemblies.delete_assembly import delete_assembly
from rigtools.assemblies.limb_collections import find_limb_collections
from rigtools.utils.bone import get_selected_bones

ASSEMBLY_TYPE_OPERATORS = {
	'IK': "rig.advanced_ik_setup",
	'FK': "rig.advanced_fk_setup",
	'TORSO': "rig.advanced_torso_setup",
	'PALM': "rig.advanced_palm_setup"
}

def find_assemblies_from_selection(context):
	bones = get_selected_bones(context)
	return find_assemblies(context.object.data, [b.name for b in bones])

def get_active_assembly(context, assemblies):
	obj = context.object

	active = None
	if obj.mode == 'POSE' and context.active_pose_bone:
		active = context.active_pose_bone.name
	elif obj.mode == 'EDIT' and context.active_bone:
		active = context.active_bone.name

	if not active:
		return None

	for assembly in assemblies:
		names = {o.name for o in assembly.org_states}
		names.update(b.name for b in assembly.mechanism_bones)
		if active in names:
			return assembly
	return None

class RIG_OT_rename_assembly(bpy.types.Operator):
	bl_description = "Rename the selected assembly"
	bl_idname = "rig.rename_assembly"
	bl_label = "Rename Assembly"
	bl_options = {'REGISTER', 'UNDO'}

	assembly_uid: bpy.props.StringProperty()
	name: bpy.props.StringProperty(name="Name")

	def invoke(self, context, event):
		assembly = find_assembly(context.object, self.assembly_uid)
		if not assembly:
			self.report({'ERROR'}, "Assembly not found")
			return {'CANCELLED'}
		self.name = assembly.name
		return context.window_manager.invoke_props_dialog(self, width=250)

	def draw(self, context):
		self.layout.prop(self, "name")

	def execute(self, context):
		assembly = find_assembly(context.object, self.assembly_uid)
		if not assembly:
			self.report({'ERROR'}, "Assembly not found")
			return {'CANCELLED'}
		if not self.name.strip():
			self.report({'ERROR'}, "Name cannot be empty")
			return {'CANCELLED'}

		assembly.name = self.name.strip()
		
		return {'FINISHED'}

class RIG_OT_rename_limb_collections(bpy.types.Operator):
	bl_idname = "rig.rename_limb_collections"
	bl_label = "Rename Limb Collections"
	bl_description = "Rename the limb collections for the selected assembly"
	bl_options = {'REGISTER', 'UNDO'}

	limb: bpy.props.StringProperty(options={'HIDDEN'})
	side: bpy.props.StringProperty(options={'HIDDEN'})

	fk: bpy.props.StringProperty(name="FK")
	ik: bpy.props.StringProperty(name="IK")
	tweak: bpy.props.StringProperty(name="Tweak")
	mch: bpy.props.StringProperty(name="MCH")
	master: bpy.props.StringProperty(name="Master")
	control: bpy.props.StringProperty(name="Control")
	
	def _roles_in_use(self, armature_data):
		all_colls = getattr(armature_data, "collections_all", armature_data.collections)
		row = find_limb_collections(armature_data, self.limb, self.side)
		return [
			role for role in ("fk", "ik", "tweak", "mch", "master", "control")
			if all_colls.get(getattr(row, role))
		]

	def invoke(self, context, event):
		row = find_limb_collections(context.object.data, self.limb, self.side)
		for role in self._roles_in_use(context.object.data):
			setattr(self, role, getattr(row, role))
		return context.window_manager.invoke_props_dialog(self, width=250)

	def draw(self, context):
		ROLE_LABELS = {
			"fk": "FK",
			"ik": "IK",
			"tweak": "Tweak",
			"mch": "MCH",
			"master": "Master",
			"control": "Control",
		}
		split_size = 0.25
		col = self.layout.column()
		for role in self._roles_in_use(context.object.data):
			split = col.split(align=True, factor=split_size)
			row = split.row(align=True)
			row.label(text=ROLE_LABELS[role], translate=False)
			row = split.row(align=True)
			row.prop(self, role, text="")

	def execute(self, context):
		row = find_limb_collections(context.object.data, self.limb, self.side)
		count = 0
		for role in self._roles_in_use(context.object.data):
			new_name = getattr(self, role).strip()
			if new_name and new_name != getattr(row, role):
				row.rename(role, new_name)
				count += 1
		if count == 0:
			self.report({'INFO'}, "No collections renamed")
		else:
			self.report({'INFO'}, f"Renamed {count} collection{'s' if count != 1 else ''}")
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

class RIG_OT_reconfigure_selected_assemblies(bpy.types.Operator):
	bl_idname = "rig.reconfigure_selected_assemblies"
	bl_label = "Reconfigure All Selected"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(cls, context):
		assemblies = find_assemblies_from_selection(context)
		if len({a.assembly_type for a in assemblies}) > 1:
			cls.poll_message_set("All assemblies must be of the same type")
			return False
		if get_active_assembly(context, assemblies) is None:
			cls.poll_message_set("Active bone must belong to an assembly")
			return False
		cls.poll_message_set("Internal error RIG-RECONFIG-POLL. This error should not happen. Please report this to the developer.")
		print(f"RIG-RECONFIG-POLL: {len(assemblies)} assemblies, {len({a.assembly_type for a in assemblies})} types, active={get_active_assembly(context, assemblies)}")
		return False

	def execute(self, context):
		return {'CANCELLED'}


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

		armature_data = context.object.data
		if needs_rig_upgrade(armature_data):
			settings = armature_data.rigtools
			row = layout.row()
			row.alert = True
			row.operator(
				"rig.upgrade_rig",
				text=f"Upgrade Rig (v{settings.rig_data_version} -> v{CURRENT_RIG_DATA_VERSION})",
				icon='FILE_REFRESH',
			)
			layout.separator()

		assemblies = find_assemblies_from_selection(context)

		if len(assemblies) > 1:
			row = layout.row(align=True)
			types = {a.assembly_type for a in assemblies}
			source = get_active_assembly(context, assemblies)
			if len(types) > 1 or source is None:
				row.operator("rig.reconfigure_selected_assemblies", text="Reconfigure All Selected", icon='SETTINGS')
			else:
				op = row.operator(
					ASSEMBLY_TYPE_OPERATORS[source.assembly_type],
					text="Reconfigure All Selected",
					icon='SETTINGS',
				)
				op.assembly_uid = source.uid
				op.assembly_uids = ",".join(a.uid for a in assemblies)

		for assembly in assemblies:
			box = layout.box()
			col = box.column(align=True)
			row = col.row(align=True)
			template = assembly.template_name

			match assembly.assembly_type:
				case 'IK':
					op_id = "rig.advanced_ik_setup"
					template = f"IK - {template}"
				case 'FK':
					op_id = "rig.advanced_fk_setup"
					template = f"FK - {template}"
				case 'TORSO':
					op_id = "rig.advanced_torso_setup"
				case 'PALM':
					op_id = "rig.advanced_palm_setup"
				case _:
					op_id = ""

			row.label(text=assembly.name)
			
			row.label(text=template)

			op = row.operator("rig.rename_assembly", text="", icon='GREASEPENCIL')
			op.assembly_uid = assembly.uid

			row.separator(factor=0.5)
			
			op = row.operator("rig.rename_limb_collections", text="", icon='OUTLINER_COLLECTION')
			op.limb = assembly.get_options()["limb_property_base_name"]
			op.side = assembly.side

			col.separator(factor=0.5)
			row = col.row(align=True)

			op = row.operator(op_id, text="Reconfigure", icon='SETTINGS')
			op.assembly_uid = assembly.uid
			op = row.operator("rig.delete_assembly", text="Delete", icon='TRASH')
			op.assembly_uid = assembly.uid

			for config in iterate_configs(assembly):
				config.draw(col, assembly, context)

		if not assemblies:
			layout.label(text="No assemblies selected", icon='STATUS_INFO')

classes = (
	RIG_OT_delete_assembly,
	RIG_OT_rename_assembly,
	RIG_OT_rename_limb_collections,
	RIG_OT_reconfigure_selected_assemblies,
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