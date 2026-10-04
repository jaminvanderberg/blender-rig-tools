import bpy
from bpy.props import BoolProperty, StringProperty, CollectionProperty
from rigtools.armature_settings import get_armature_settings
from rigtools.assemblies.assembly_data import find_assemblies
from rigtools.rig_ui.property_item import RigUIPropertyItem, find_property_item
from rigtools.rig_ui.snapping_data import find_snap_chain
from rigtools.utils.bone import get_selected_bones
from rigtools.utils.naming import guess_property_label
from rna_prop_ui import rna_idprop_ui_create
from bpy.utils import escape_identifier

def _parse_enum_items(enum_items):
	parts = []
	for chunk in enum_items.split(","):
		name = chunk.strip()
		if name:
			parts.append(name)
	return [(str(i), name, name) for i, name in enumerate(parts)]

def _apply_enum(prop_bone, name, items):
	value = prop_bone[name]
	if isinstance(value, bool):
		value = int(value)
	else:
		value = int(round(float(value)))
	value = max(0, min(value, len(items) - 1)) if items else 0

	overridable = prop_bone.is_property_overridable_library(f'["{name}"]')
	try:
		prop_bone.id_properties_ui(name).update(
			min=0,
			max=max(len(items) - 1, 0),
			items=items,
		)
		prop_bone[name] = value
	except(TypeError, ValueError):
		del prop_bone[name]
		rna_idprop_ui_create(
			prop_bone,
			name,
			default=value,
			min=0,
			max=max(len(items) - 1, 0),
			items=items,
		)
	if overridable:
		prop_bone.property_overridable_library_set(f'["{name}"]', True)

def get_selected_assemblies(context):
	selected_bones = get_selected_bones(context)
	selected_names = [bone.name for bone in selected_bones]
	assemblies = find_assemblies(context.object.data, selected_names)
	return sorted(assemblies, key=lambda x: x.name)

class RIG_OT_ui_property_modify(bpy.types.Operator):
	"""Modify the Rig UI settings for a custom property."""
	bl_idname = "rig.ui_property_modify"
	bl_label = "Modify Rig UI Settings"
	bl_options = {'REGISTER', 'UNDO'}

	property_name: StringProperty()
	label: StringProperty()

	is_enum: BoolProperty(
		name="Enum Property",
		default=False,
		description="Setup this property as an enum property"
	)

	enum_items: StringProperty(
		name="Enum Items",
		description="The items for the enum property",
		default=""
	)

	@classmethod
	def poll(cls, context):
		return context.object and context.object.type == 'ARMATURE'

	def execute(self, context):
		armature_data = context.object.data
		item = find_property_item(armature_data, self.property_name)
		if not item:
			item = armature_data.rig_ui_properties.add()
			item.property_name = self.property_name
		item.label = self.label

		settings = get_armature_settings(armature_data, context)
		prop_bone = context.active_object.pose.bones[settings.property_bone_name]
		if self.is_enum:
			items = _parse_enum_items(self.enum_items)
			if not items:
				self.report({'ERROR'}, "No enum items provided")
				return {'CANCELLED'}
			_apply_enum(prop_bone, self.property_name, items)
		return {'FINISHED'}

	def invoke(self, context, event):
		armature_data = context.object.data
		item = find_property_item(armature_data, self.property_name)
		self.label = (item.label if item else guess_property_label(self.property_name, context))

		settings = get_armature_settings(armature_data, context)
		prop_bone = context.active_object.pose.bones[settings.property_bone_name]
		ui = prop_bone.id_properties_ui(self.property_name).as_dict()
		items = ui.get("items") or []
		self.is_enum = bool(items)
		self.enum_items = ",".join(item[1] for item in items)
		return context.window_manager.invoke_props_dialog(self, width=350)

	def draw(self, context):
		layout = self.layout
		layout.use_property_split = True
		#layout.use_property_decorate = False

		settings = get_armature_settings(context.object.data, context)
		prop_bone = context.active_object.pose.bones[settings.property_bone_name]

		col = layout.column()
		col.enabled = False			  
		col.prop(self, "property_name", text="Property Name")

		op = layout.operator("wm.properties_edit", text="Edit Property…", icon='PREFERENCES')
		op.data_path = f'object.pose.bones["{escape_identifier(prop_bone.name)}"]'
		op.property_name = self.property_name			
		layout.separator()

		layout.prop(self, "label", text="Label")
		layout.separator()
		layout.prop(self, "is_enum")
		if self.is_enum:
			layout.prop(self, "enum_items")


def _iterate_assemblies(context, prop_bone):
	overlay = {item.property_name: item for item in context.active_object.data.rig_ui_properties}
	for assembly in get_selected_assemblies(context):
		properties = []
		snaps = []
		for property in assembly.properties:
			if property.name.startswith("_"):
				continue
			if property.name not in prop_bone.keys():
				continue
			item = overlay.get(property.name)
			label = (item.label if item else guess_property_label(property.name, context))
			properties.append({
				"name": property.name,
				"label": label,
			})

			snap = find_snap_chain(context.active_object.data, property.name)
			if snap:
				snaps.append({
					"name": snap.switch_property,
				})
		properties.sort(key=lambda x: x["label"].lower())

		yield assembly.name, properties, snaps

class RIG_PT_properties_ui(bpy.types.Panel):
	bl_label = "Rig Properties"
	bl_idname = "RIG_PT_properties_ui"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = "Item"

	@classmethod
	def poll(cls, context):
		if not context.object or context.object.type != 'ARMATURE':
			return False
		settings = get_armature_settings(context.object.data, context)
		prop_bone = context.active_object.pose.bones.get(settings.property_bone_name)
		if not prop_bone:
			return False
		return any(not k.startswith("_") for k in prop_bone.keys())

	def draw(self, context):
		settings = get_armature_settings(context.object.data, context)
		prop_bone_name = settings.property_bone_name
		obj = context.active_object
		prop_bone = obj.pose.bones[prop_bone_name]
		
		layout = self.layout
		split_size = 0.6

		first = True
		for name, properties, snaps in _iterate_assemblies(context, prop_bone):
			if not first:
				layout.separator()
			first = False
			
			col = layout.box().column(align=True)

			for prop in properties:
				row = col.row()
				split = row.split(align=True, factor=split_size)
				row = split.row(align=True)
				row.label(text=prop["label"], translate=False)
				row = split.row(align=True)
				row.prop(prop_bone, f'["{prop["name"]}"]', text = "", slider=True)
				op = row.operator("rig.ui_property_modify", text="", icon='SETTINGS')
				op.property_name = prop["name"]

			for snap in snaps:
				col = layout.column(align=True)
				op = col.operator("rig.snap_ik_to_fk", text=name + " IK > FK", icon='SNAP_ON')
				op.switch_property = snap["name"]
				op = col.operator("rig.snap_fk_to_ik", text=name + " FK > IK", icon='SNAP_ON')
				op.switch_property = snap["name"]

classes = (
	RigUIPropertyItem,
	RIG_OT_ui_property_modify,
	RIG_PT_properties_ui,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	bpy.types.Armature.rig_ui_properties = CollectionProperty(type=RigUIPropertyItem)

def unregister():
	del bpy.types.Armature.rig_ui_properties
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
