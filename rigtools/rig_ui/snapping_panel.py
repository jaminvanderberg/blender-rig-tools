import bpy
from bpy.props import BoolProperty, StringProperty, EnumProperty, CollectionProperty
from rigtools.armature_settings import get_armature_settings
from rigtools.rig_ui.property_name import guess_snapping_label
from itertools import groupby
from rna_prop_ui import rna_idprop_ui_create
from bpy.utils import escape_identifier

class RigUISnapBoneItem(bpy.types.PropertyGroup):
	name: StringProperty()

class RigUISnapChainItem(bpy.types.PropertyGroup):
	label: StringProperty(name="Label", default="")
	group: StringProperty(name="Group", default="")
	hidden: BoolProperty(name="Hidden", default=False)

	switch_property: StringProperty(name="Switch Property")
	fk_bones: CollectionProperty(type=RigUISnapBoneItem)
	ik_bones: CollectionProperty(type=RigUISnapBoneItem)
	ik_control: StringProperty(default="")
	ik_pole: StringProperty(default="")
	snap_control: StringProperty(default="")
	snap_pole: StringProperty(default="")

def register_snap_chain(armature_data, *, switch_property, fk_bones, ik_mch_bones, ik_control, ik_pole, snap_control, snap_pole, context):
	item = armature_data.rig_ui_snap_chains.add()
	item.switch_property = switch_property
	for bone in fk_bones:
		item.fk_bones.add().name = bone
	for bone in ik_mch_bones:
		item.ik_bones.add().name = bone
	item.ik_control = ik_control
	item.ik_pole = ik_pole
	item.snap_control = snap_control
	item.snap_pole = snap_pole

	item.label, item.group = guess_snapping_label(switch_property, context)
	return item

def _find_snap_chain_item(armature_data, switch_property):
	for item in armature_data.rig_ui_snap_chains:
		if item.switch_property == switch_property:
			return item
	return None

class RIG_OT_snap_chain_modify(bpy.types.Operator):
	"""Modify the Rig UI settings for a custom property."""
	bl_idname = "rig.snap_chain_modify"
	bl_label = "Modify Snapping Chain"
	bl_options = {'REGISTER', 'UNDO'}

	switch_property: StringProperty()
	label: StringProperty(name="Label", default="")
	group: StringProperty(name="Group", default="")
	hidden: BoolProperty(name="Hidden", default=False)

	@classmethod
	def poll(cls, context):
		return context.object and context.object.type == 'ARMATURE'

	def execute(self, context):
		armature_data = context.object.data
		item = _find_snap_chain_item(armature_data, self.switch_property)
		if not item:
			item = armature_data.rig_ui_snap_chains.add()
			item.switch_property = self.switch_property
		item.label = self.label
		item.group = self.group
		item.hidden = self.hidden
		return {'FINISHED'}

	def invoke(self, context, event):
		armature_data = context.object.data
		item = _find_snap_chain_item(armature_data, self.switch_property)
		self.label = item.label
		self.group = item.group
		self.hidden = item.hidden
		return context.window_manager.invoke_props_dialog(self, width=350)

	def draw(self, context):
		layout = self.layout
		layout.use_property_split = True

		layout.prop(self, "switch_property", text="Switch Property")
		layout.prop(self, "label", text="Label")
		layout.prop(self, "group", text="Group")
		layout.prop(self, "hidden", text="Hidden")

def _iterate_snapping_chains(armature_data, context, show_hidden=False):
	rows = []
	for item in armature_data.rig_ui_snap_chains:
		hidden = (item.hidden if item else False)
		if hidden and not show_hidden:
			continue
		rows.append({
			"name": item.switch_property,
			"label": item.label,
			"group": item.group,
			"hidden": item.hidden,
			"item": item
		})

	rows.sort(key=lambda r: (
		r["group"].lower(),
		r["label"].lower(),
		r["name"]
	))
	return rows

# returns final world matrix accounting for offset in rest pose
def get_matrix(armature, source_bone, target_bone):
	# rest post matrices
	source_bone_rest_matrix = source_bone.bone.matrix_local
	target_bone_rest_matrix = target_bone.bone.matrix_local

	# rest pose offset matrix
	offset_matrix = source_bone_rest_matrix.inverted() @ target_bone_rest_matrix

	# world_space_matrices
	source_world_matrix = source_bone.matrix

	#world space matrix
	matrix_final =  source_world_matrix @ offset_matrix
	
	return matrix_final

class RIG_OT_snap_ik_to_fk(bpy.types.Operator):
	bl_idname = "rig.snap_ik_to_fk"
	bl_label = "Snap IK > FK"
	bl_description = "Snap IK > FK"
	bl_options = {'UNDO', 'INTERNAL'}

	switch_property: StringProperty()

	@classmethod
	def poll(self, context):
		return context.active_object and context.active_object.type == 'ARMATURE'

	def execute(self, context):
		arm = context.active_object
		item = _find_snap_chain_item(arm.data, self.switch_property)
		pose_bones = arm.pose.bones
		settings = get_armature_settings(arm.data, context)
		props = pose_bones[settings.property_bone_name]

		ik_control = pose_bones[item.ik_control]
		snap_control = pose_bones[item.snap_control]
		ik_control.matrix = get_matrix(arm, snap_control, ik_control)
		context.view_layer.update()

		if item.ik_pole and item.snap_pole:
			ik_pole = pose_bones[item.ik_pole]
			snap_pole = pose_bones[item.snap_pole]
			ik_pole.matrix = get_matrix(arm, snap_pole, ik_pole)
			context.view_layer.update()

		props[item.switch_property] = 1 #IK

		return {'FINISHED'}

class RIG_OT_snap_fk_to_ik(bpy.types.Operator):
	bl_idname = "rig.snap_fk_to_ik"
	bl_label = "Snap FK > IK"
	bl_description = "Snap FK > IK"
	bl_options = {'UNDO', 'INTERNAL'}

	switch_property: StringProperty()

	@classmethod
	def poll(self, context):
		return context.active_object and context.active_object.type == 'ARMATURE'

	def execute(self, context):
		arm = context.active_object
		item = _find_snap_chain_item(arm.data, self.switch_property)
		pose_bones = arm.pose.bones
		settings = get_armature_settings(arm.data, context)
		props = pose_bones[settings.property_bone_name]

		select_set = [props.name]
		for i, fk_bone in enumerate(item.fk_bones):
			fk_bone = pose_bones[fk_bone.name]
			mch_bone = pose_bones[item.ik_bones[i].name]
			fk_bone.matrix = get_matrix(arm, mch_bone, fk_bone)
			context.view_layer.update()
			select_set.append(fk_bone.name)

		props[item.switch_property] = 0 #FK 

		return {'FINISHED'}

class RIG_PT_snapping_ui(bpy.types.Panel):
	bl_label = "Snapping Utilities"
	bl_idname = "RIG_PT_snapping_ui"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = "Item"

	@classmethod
	def poll(cls, context):
		if not context.object or context.object.type != 'ARMATURE':
			return False
		# Don't show if there's no snapping chains
		return context.object.data.rig_ui_snap_chains


	def draw(self, context):
		settings = get_armature_settings(context.object.data, context)
		prop_bone_name = settings.property_bone_name
		obj = context.active_object
		prop_bone = obj.pose.bones[prop_bone_name]
		
		layout = self.layout
		split_size = 0.7

		wm = context.window_manager

		props = _iterate_snapping_chains(obj.data, context, wm.rig_ui_show_hidden_snapping_chains)

		for group, group_props in groupby(props, key=lambda x: x["group"]):

			col = layout.column(align=True)
			col.label(text=f"{group} Snapping")

			for prop_data in group_props:
				col = layout.box().column(align=True)

				row = col.row()
				row.active = not prop_data["hidden"]
				split = row.split(align=True, factor=split_size)
				row = split.row(align=True)
				row.label(text=prop_data["label"], translate=False)
				row = split.row(align=True)
				row.prop(prop_bone, f'["{prop_data["name"]}"]', text = "", slider=True)
				op = row.operator("rig.snap_chain_modify", text="", icon='SETTINGS')
				op.switch_property = prop_data["name"]

				row = col.row(align=True)
				op = row.operator("rig.snap_ik_to_fk", text="Snap IK > FK", icon='SNAP_ON')
				op.switch_property = prop_data["name"]
				op = row.operator("rig.snap_fk_to_ik", text="Snap FK > IK", icon='SNAP_OFF')
				op.switch_property = prop_data["name"]

			col.separator()

		hidden_count = sum(1 for prop_data in props if prop_data["hidden"])
		if hidden_count > 0:
			header = layout.row(align=True)
			header.alignment = 'RIGHT'
			icon = 'HIDE_OFF' if wm.rig_ui_show_hidden_snapping_chains else 'HIDE_ON'
			header.prop(wm, "rig_ui_show_hidden_snapping_chains", icon=icon, toggle=True)

classes = (
	RigUISnapBoneItem,
	RigUISnapChainItem,
	RIG_OT_snap_chain_modify,
	RIG_OT_snap_ik_to_fk,
	RIG_OT_snap_fk_to_ik,
	RIG_PT_snapping_ui,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	bpy.types.Armature.rig_ui_snap_chains = CollectionProperty(type=RigUISnapChainItem)
	bpy.types.WindowManager.rig_ui_show_hidden_snapping_chains = BoolProperty(
		name="Show Hidden",
		description="Show hidden snapping chains in the snapping UI",
		default=False
	)

def unregister():
	del bpy.types.Armature.rig_ui_snap_chains
	del bpy.types.WindowManager.rig_ui_show_hidden_snapping_chains
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
