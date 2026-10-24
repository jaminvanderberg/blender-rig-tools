import bpy
from bpy.props import StringProperty, FloatProperty
from rigtools.armature_settings import get_armature_settings
from rigtools.assemblies.assembly_data import find_assemblies
from rigtools.rig_ui.snapping_data import find_snap_chain
from rigtools.utils.bone import get_selected_bones, mirror_pose_selection

ROLE_DATA = {
	"FK_IK_SWITCH": {"label": "FK > IK Switch", "order": 1},
	"IK_STRETCH": {"label": "IK Stretch", "order": 2},
	"ROTATION_ISOLATION": {"label": "FK Rotation Follow", "order": 3},
	"SKIRT_COLLISION": {"label": "Leg Collision", "order": 4},
	"SKIRT_RIDE": {"label": "Leg Ride", "order": 5},
	"IK_PARENT": {"label": "IK Parent", "order": 6},
}

def get_selected_assemblies(context):
	selected_bones = mirror_pose_selection(context, get_selected_bones(context))
	selected_names = [bone.name for bone in selected_bones]
	assemblies = find_assemblies(context.object.data, selected_names)
	return sorted(assemblies, key=lambda x: x.name)

def _iterate_assemblies(context, prop_bone):
	groups = {}
	for assembly in get_selected_assemblies(context):
		label = assembly.ui_label
		key = label.lower()
		group = groups.get(key)
		if group is None:
			group = {"label": label, "properties": {}, "snaps": {}}
			groups[key] = group

		for property in assembly.properties:
			if property.name.startswith("_"):
				continue
			if property.name not in prop_bone.keys():
				continue
			if property.name not in group["properties"]:
				group["properties"][property.name] = {
					"name": property.name,
					"role": property.role,
					"qualifier": property.qualifier,
				}

			snap = find_snap_chain(context.active_object.data, property.name)
			if snap and snap.switch_property not in group["snaps"]:
				group["snaps"][snap.switch_property] = {
					"name": snap.switch_property,
					"label": assembly.name,
				}

	for key in sorted(groups):
		group = groups[key]
		properties = sorted(
			group["properties"].values(),
			key=lambda p: (
				ROLE_DATA.get(p["role"], {}).get("order", 999),
				p["name"],
			),
		)
		snaps = list(group["snaps"].values())
		yield group["label"], properties, snaps

class RIG_OT_set_id_float(bpy.types.Operator):
	"""Set a float ID property on the properties bone."""
	bl_idname = "rig.set_id_float"
	bl_label = "Set Property"
	bl_options = {'UNDO', 'INTERNAL'}

	property_name: StringProperty()
	value: FloatProperty()
	tip: StringProperty()

	@classmethod
	def description(cls, context, properties):
		return properties.tip or "Set property value"

	def execute(self, context):
		settings = get_armature_settings(context.object.data, context)
		obj = context.active_object
		prop_bone = obj.pose.bones[settings.property_bone_name]
		prop_bone[self.property_name] = self.value

		obj.update_tag(refresh={'OBJECT'})
		for area in context.screen.areas:
			if area.type == 'VIEW_3D':
				area.tag_redraw()

		if context.scene.tool_settings.use_keyframe_insert_auto:
			prop_bone.keyframe_insert(f'["{self.property_name}"]')
		return {'FINISHED'}

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

		self.split_size = 0.7

		first = True
		for name, properties, snaps in _iterate_assemblies(context, prop_bone):
			if not first:
				layout.separator()
			first = False

			col = layout.box().column(align=True)
			col.label(text=name, translate=False, icon='ARMATURE_DATA')
			col.separator()

			for prop in properties:
				label = ROLE_DATA.get(prop["role"], {}).get("label", prop["name"])
				if prop["qualifier"]:
					label = f"{prop['qualifier']} {label}"

				match prop["role"]:
					case "FK_IK_SWITCH":
						self.draw_float_with_buttons(
							col, prop_bone, prop, label,
							(("FK", 0.0, "Set FK"), ("IK", 1.0, "Set IK")),
						)
					case "ROTATION_ISOLATION":
						self.draw_float_with_buttons(
							col, prop_bone, prop, label,
							(("Off", 0.0, "Isolate rotation"), ("On", 1.0, "Follow parent rotation")),
						)
					case "SKIRT_COLLISION":
						self.draw_float_with_buttons(
							col, prop_bone, prop, label,
							(("Off", 0.0, "Disable collision"), ("On", 1.0, "Enable collision")),
						)
					case "SKIRT_RIDE":
						self.draw_float_with_buttons(
							col, prop_bone, prop, label,
							(("Off", 0.0, "Disable ride"), ("On", 1.0, "Enable ride")),
						)
					case "IK_STRETCH":
						self.draw_float_with_buttons(
							col, prop_bone, prop, label,
							(("Off", 0.0, "Disable stretch"), ("On", 1.0, "Enable stretch")),
						)
					case _:
						col.separator()
						row = col.column()
						split = row.split(align=True, factor=0.5)
						split.row(align=True).label(text=label, translate=False)
						split.row(align=True).prop(prop_bone, f'["{prop["name"]}"]', text="", slider=True)

			for snap in snaps:
				col = layout.column(align=True)
				op = col.operator("rig.snap_ik_to_fk", text=snap["label"] + " IK > FK", icon='SNAP_ON')
				op.switch_property = snap["name"]
				op = col.operator("rig.snap_fk_to_ik", text=snap["label"] + " FK > IK", icon='SNAP_ON')
				op.switch_property = snap["name"]

	def draw_float_with_buttons(self, col, prop_bone, prop, label, buttons):
		row = col.row(align=True)
		split = row.split(factor=self.split_size)
		split.row(align=True).prop(
			prop_bone, f'["{prop["name"]}"]', text=label, slider=True
		)

		btns = split.row(align=True)
		val = prop_bone[prop["name"]]
		for text, value, tip in buttons:
			op = btns.operator(
				"rig.set_id_float",
				text=text,
				depress=(val < 0.01) if value < 0.5 else (val > 0.99),
			)
			op.property_name = prop["name"]
			op.value = value
			op.tip = tip

classes = (
	RIG_OT_set_id_float,
	RIG_PT_properties_ui,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
