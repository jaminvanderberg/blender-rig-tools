import bpy
from bpy.props import BoolProperty, StringProperty, EnumProperty, CollectionProperty
from rigtools.armature_settings import get_armature_settings
from rigtools.rig_ui.property_name import guess_property_label, guess_group
from itertools import groupby
from rna_prop_ui import rna_idprop_ui_create
from bpy.utils import escape_identifier

class RigUIPropertyItem(bpy.types.PropertyGroup):
	property_name: StringProperty()
	label: StringProperty()
	group: StringProperty()
	subgroup: StringProperty()
	hidden: BoolProperty(default=False)

def _find_property_item(armature_data, property_name):
	for item in armature_data.rig_ui_properties:
		if item.property_name == property_name:
			return item
	return None

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

class RIG_OT_ui_property_modify(bpy.types.Operator):
	"""Modify the Rig UI settings for a custom property."""
	bl_idname = "rig.ui_property_modify"
	bl_label = "Modify Rig UI Settings"
	bl_options = {'REGISTER', 'UNDO'}

	property_name: StringProperty()
	label: StringProperty()
	group: StringProperty()
	subgroup: StringProperty()
	hidden: BoolProperty(default=False)

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
		item = _find_property_item(armature_data, self.property_name)
		if not item:
			item = armature_data.rig_ui_properties.add()
			item.property_name = self.property_name
		item.label = self.label
		item.group = self.group
		item.subgroup = self.subgroup
		item.hidden = self.hidden

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
		item = _find_property_item(armature_data, self.property_name)
		guessed_group, guessed_side = guess_group(self.property_name, context)
		self.label = (item.label if item else guess_property_label(self.property_name, context))
		self.group = (item.group if item else guessed_group)
		self.subgroup = (item.subgroup if item else guessed_side)
		self.hidden = (item.hidden if item else False)

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
		layout.prop(self, "group", text="Group")
		layout.prop(self, "subgroup", text="Subgroup")
		layout.prop(self, "hidden", text="Hidden")
		layout.separator()
		layout.prop(self, "is_enum")
		if self.is_enum:
			layout.prop(self, "enum_items")


def _iterate_properties(armature_data, prop_bone, context, show_hidden=False):
	overlay = {item.property_name: item for item in armature_data.rig_ui_properties}
	rows = []
	for prop in prop_bone.keys():
		if prop.startswith("_"):
			continue
		item = overlay.get(prop)
		group, side = guess_group(prop, context)
		label = (item.label if item else guess_property_label(prop, context))
		group = (item.group if item else group)
		subgroup = (item.subgroup if item else side)
		hidden = (item.hidden if item else False)
		if hidden and not show_hidden:
			continue

		rows.append({
			"name": prop,
			"label": label,
			"group": group,
			"subgroup": subgroup,
			"hidden": hidden})

	side_order = {"": 0, "L": 1, "R": 2}
	rows.sort(key=lambda r: (
		r["group"].lower(),
		side_order.get(r["subgroup"], 3),
		r["label"].lower(),
		r["name"]
	))
	return rows


class RIG_PT_properties_ui(bpy.types.Panel):
	bl_label = "Rig Properties"
	bl_idname = "RIG_PT_properties_ui"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = "Item"

	@classmethod
	def poll(cls, context):
		return context.object and context.object.type == 'ARMATURE'

	def draw(self, context):
		settings = get_armature_settings(context.object.data, context)
		prop_bone_name = settings.property_bone_name
		obj = context.active_object
		prop_bone = obj.pose.bones[prop_bone_name]
		if not prop_bone:
			self.report({'ERROR'}, "Property bone not found")
			return {'CANCELLED'}
		
		layout = self.layout
		split_size = 0.7

		wm = context.window_manager
		header = layout.row(align=True)
		header.alignment = 'RIGHT'
		icon = 'HIDE_OFF' if wm.rig_ui_show_hidden_properties else 'HIDE_ON'
		header.prop(wm, "rig_ui_show_hidden_properties", icon=icon, toggle=True)

		props = _iterate_properties(obj.data, prop_bone, context, wm.rig_ui_show_hidden_properties)

		for group, group_props in groupby(props, key=lambda x: x["group"]):
			header, body = layout.panel(f"rig_ui_props_{group}", default_closed=True)
			header.label(text=f"{group} Properties")
			if not body:
				continue

			current_sub = object() # force first box
			col = None
			for prop_data in group_props:
				if prop_data["subgroup"] != current_sub:
					current_sub = prop_data["subgroup"]
					col = body.box().column(align=True)
				row = col.row()
				row.active = not prop_data["hidden"]
				split = row.split(align=True, factor=split_size)
				row = split.row(align=True)
				row.label(text=prop_data["label"], translate=False)
				row = split.row(align=True)
				row.prop(prop_bone, f'["{prop_data["name"]}"]', text = "", slider=True)
				op = row.operator("rig.ui_property_modify", text="", icon='MODIFIER')
				op.property_name = prop_data["name"]

classes = (
	RigUIPropertyItem,
	RIG_OT_ui_property_modify,
	RIG_PT_properties_ui,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	bpy.types.Armature.rig_ui_properties = CollectionProperty(type=RigUIPropertyItem)
	bpy.types.WindowManager.rig_ui_show_hidden_properties = BoolProperty(
		name="Show Hidden",
		description="Show hidden properties in the properties UI",
		default=False
	)

def unregister():
	del bpy.types.Armature.rig_ui_properties
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
