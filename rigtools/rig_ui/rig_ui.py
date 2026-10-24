bl_info = {
	"name": "RigTools UI",
	"author": "Jamin VanderBerg",
	"version": (0, 1),
	"blender": (4, 0, 0),
	"location": "View3D > Sidebar > Item",
	"description": "Animator panels for rigs built with Rig Tools",
	"category": "Rigging"
}

import bpy
import re
from bpy.props import StringProperty, FloatProperty, BoolProperty

# Data
def stored(id_data):
	"""Rigtools data stored on an ID, whether or not rigtools is registered."""
	if hasattr(id_data, "bl_system_properties_get"): # Blender 5.0+
		return id_data.bl_system_properties_get() or {}
	return id_data # 4.x: add-on properties live with regular ID properties

def property_bone(obj):
	"""The rig's properties pose bone, or None if not applicable."""
	settings = stored(obj.data).get("rigtools")
	if not settings or not settings.get("is_initialized"):
		return None
	return obj.pose.bones.get(settings["property_bone_name"])

def find_assemblies(armature_data, bone_names):
	wanted = set(bone_names)
	assemblies = []
	for assembly in stored(armature_data).get("rigtools_assemblies", ()):
		names = {o["name"] for o in assembly["org_states"]}
		names.update(b["name"] for b in assembly["mechanism_bones"])
		if names & wanted:
			assemblies.append(assembly)
	return assemblies

def find_snap_chain(armature_data, switch_property):
	for item in stored(armature_data).get("rig_ui_snap_chains", ()):
		if item["switch_property"] == switch_property:
			return item
	return None

# Selection

def get_selected_bones(context):
	if context.mode == 'EDIT_ARMATURE':
		return list(context.selected_editable_bones)
	elif context.mode == 'POSE':
		return list(context.selected_pose_bones)
	return []

def mirror_pose_selection(context, selected):
	"""If X-Mirror is on in Pose mode, append each bone's L/R counterpart (no ID writes)."""
	obj = context.object
	if not obj or obj.type != 'ARMATURE' or context.mode != 'POSE':
		return selected
	if not obj.pose.use_mirror_x:
		return selected

	pose_bones = obj.pose.bones
	seen = {b.name for b in selected}
	expanded = list(selected)
	for bone in selected:
		flipped = flip_side_name(bone.name)
		if not flipped or flipped in seen:
			continue
		mirror = pose_bones.get(flipped)
		if mirror is None:
			continue
		expanded.append(mirror)
		seen.add(flipped)
	return expanded

# Naming
def get_base_name(bone_name) -> tuple[str, str]:
	symmetry_pattern = r'(\.[LR]|\_[LR])(\.\d+)?$'
	match = re.search(symmetry_pattern, bone_name, re.IGNORECASE)

	if match:
		base_name = bone_name[:match.start()]
		extension = match.group(0)
	else:
		base_name = bone_name
		extension = ""

	return base_name, extension

def flip_side_name(bone_name):
	"""Return the L/R flipped bone name, or None if there is no side suffix."""
	base_name, extension = get_base_name(bone_name)
	if not extension:
		return None
	flipped = extension.replace('L', '\0').replace('R', 'L').replace('\0', 'R')
	flipped = flipped.replace('l', '\0').replace('r', 'l').replace('\0', 'r')
	if flipped == extension:
		return None
	return base_name + flipped


###############################################################################
# PROPERTY PANEL

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
	return sorted(assemblies, key=lambda x: x["name"])

def _iterate_assemblies(context, prop_bone):
	groups = {}
	for assembly in get_selected_assemblies(context):
		label = assembly.get("ui_label", "*ERROR - Version incompatible")
		key = label.lower()
		group = groups.get(key)
		if group is None:
			group = {"label": label, "properties": {}, "snaps": {}}
			groups[key] = group

		for property in assembly.get("properties", ()):
			name = property["name"]
			if name.startswith("_"):
				continue
			if name not in prop_bone.keys():
				continue
			if name not in group["properties"]:
				group["properties"][name] = {
					"name": name,
					"role": property["role"],
					"qualifier": property["qualifier"],
				}

			snap = find_snap_chain(context.active_object.data, name)
			if snap and name not in group["snaps"]:
				group["snaps"][name] = {
					"name": name,
					"label": assembly["name"],
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
		obj = context.active_object
		prop_bone = property_bone(obj) # we know it exists if we reached this far
		prop_bone[self.property_name] = self.value # same

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
		prop_bone = property_bone(context.object)
		if not prop_bone:
			return False
		return any(not k.startswith("_") for k in prop_bone.keys())

	def draw(self, context):
		obj = context.active_object
		prop_bone = property_bone(obj) # Already validated this exists in poll()

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
				role = prop["role"]
				label = ROLE_DATA.get(role, {}).get("label", prop["name"])
				if prop["qualifier"]:
					label = f"{prop['qualifier']} {label}"

				match role:
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

###############################################################################
# SNAPPING OPERATORS

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
	def poll(cls, context):
		return context.active_object and context.active_object.type == 'ARMATURE'

	def execute(self, context):
		obj = context.active_object
		item = find_snap_chain(obj.data, self.switch_property)
		pose_bones = obj.pose.bones
		prop_bone = property_bone(obj)
		if item is None or prop_bone is None:
			self.report({'ERROR'}, "Snap data not found for this rig.")
			return {'CANCELLED'}

		ik_control = pose_bones[item["ik_control"]]
		snap_control = pose_bones[item["snap_control"]]
		ik_control.matrix = get_matrix(obj, snap_control, ik_control)
		context.view_layer.update()

		if item["ik_pole"] and item["snap_pole"]:
			ik_pole = pose_bones[item["ik_pole"]]
			snap_pole = pose_bones[item["snap_pole"]]
			ik_pole.matrix = get_matrix(obj, snap_pole, ik_pole)
			context.view_layer.update()

		prop_bone[item["switch_property"]] = 1 #IK

		return {'FINISHED'}

class RIG_OT_snap_fk_to_ik(bpy.types.Operator):
	bl_idname = "rig.snap_fk_to_ik"
	bl_label = "Snap FK > IK"
	bl_description = "Snap FK > IK"
	bl_options = {'UNDO', 'INTERNAL'}

	switch_property: StringProperty()

	@classmethod
	def poll(cls, context):
		return context.active_object and context.active_object.type == 'ARMATURE'

	def execute(self, context):
		arm = context.active_object
		item = find_snap_chain(arm.data, self.switch_property)
		pose_bones = arm.pose.bones
		prop_bone = property_bone(arm)
		if item is None or prop_bone is None:
			self.report({'ERROR'}, "Snap data not found for this rig.")
			return {'CANCELLED'}

		for i, fk_bone in enumerate(item["fk_bones"]):
			fk_bone = pose_bones[fk_bone["name"]]
			mch_bone = pose_bones[item["ik_bones"][i]["name"]]
			fk_bone.matrix = get_matrix(arm, mch_bone, fk_bone)
			context.view_layer.update()

		prop_bone[item["switch_property"]] = 0 #FK 

		return {'FINISHED'}

###############################################################################
# VISIBILITY PANEL

def _mask_modifiers(obj):
	return [mod for mod in obj.modifiers if mod.type == 'MASK' and not mod.name.startswith('_')]

def _solidify_modifiers(obj):
	return [mod for mod in obj.modifiers if mod.type == 'SOLIDIFY' and not mod.name.startswith('_')]

def _related_meshes(armature_obj, view_layer):
	seen = set()
	meshes = []
	def consider(obj):
		if obj.name in seen:
			return
		if obj.type != 'MESH':
			return
		if "rigtools_helper" in obj:
			return
		seen.add(obj.name)
		meshes.append(obj)
	
	for child in armature_obj.children_recursive:
		consider(child)
	for obj in view_layer.objects:
		if obj.find_armature() == armature_obj:
			consider(obj)
	return meshes

def _mask_label(name):
	if name.lower() == "mask":
		return name
	prefix = "mask"
	if not name.lower().startswith(prefix):
		return name
	rest = name[len(prefix):]
	seps = set("._-")
	while rest and rest[0] in seps:
		rest = rest[1:]
	return rest or name

def _draw_masks(layout, obj, context):
	col = layout.column(align=True)
	for mod in _mask_modifiers(obj):
		row = col.row(align=True)
		row.label(text=_mask_label(mod.name), translate=False)
		row.prop(mod, "show_viewport", text="", icon='HIDE_ON', invert_checkbox=True, emboss=False)

def _draw_visibility_toggle(layout, obj, context):
	hidden = obj.hide_get(view_layer=context.view_layer)
	op = layout.operator(
		"rig.ui_toggle_object_visibility",
		text="",
		icon='HIDE_ON' if hidden else 'HIDE_OFF',
		emboss=False,
	)
	op.obj_name = obj.name
	op.hidden = not hidden

class RIG_OT_toggle_object_visibility(bpy.types.Operator):
	bl_idname = "rig.ui_toggle_object_visibility"
	bl_label = "Toggle Object Visibility"
	bl_description = "Toggle the object's visibility in the active view layer"
	bl_options = {'INTERNAL'}

	obj_name: StringProperty()
	hidden: BoolProperty()

	def execute(self, context):
		obj = context.view_layer.objects.get(self.obj_name)
		if not obj:
			self.report({'ERROR'}, f"Object '{self.obj_name}' is not in the active view layer.")
			return {'CANCELLED'}

		obj.hide_set(self.hidden, view_layer=context.view_layer)
		return {'FINISHED'}

class RIG_OT_toggle_solidify(bpy.types.Operator):
	bl_idname = "rig.ui_toggle_solidify"
	bl_label = "Toggle Solidify"
	bl_description = "Toggle the solidify modifier(s) for the selected object or all meshes related to the armature"
	bl_options = {'INTERNAL'}

	obj_name: StringProperty()
	enabled: BoolProperty(default=False)

	def execute(self, context):
		obj = context.scene.objects.get(self.obj_name)
		if not obj:
			self.report({'ERROR'}, f"Object '{self.obj_name}' not found.")
			return {'CANCELLED'}

		if obj.type == 'ARMATURE':
			meshes = _related_meshes(obj, context.view_layer)
			for mesh in meshes:
				solidify = _solidify_modifiers(mesh)
				if solidify:
					for mod in solidify:
						mod.show_viewport = self.enabled
			return {'FINISHED'}
		solidify = _solidify_modifiers(obj)
		if solidify:
			for mod in solidify:
				mod.show_viewport = self.enabled
		return {'FINISHED'}

class RIG_PT_visibility_ui(bpy.types.Panel):
	bl_label = "Visibility"
	bl_idname = "RIG_PT_visibility_ui"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = "Item"

	@classmethod
	def poll(cls, context):
		if not context.object:
			return False
		if context.object.type == 'ARMATURE':
			return bool(_related_meshes(context.object, context.view_layer))
		return bool(_mask_modifiers(context.object)) or bool(_solidify_modifiers(context.object))

	def draw(self, context):
		obj = context.object
		has_solidify = False
		all_solidify_enabled = True
		if obj.type == 'ARMATURE':
			masked_count = 0
			related = _related_meshes(obj, context.view_layer)

			for mesh in related:
				solidify = _solidify_modifiers(mesh)
				if solidify:
					has_solidify = True
					for mod in solidify:
						if not mod.show_viewport:
							all_solidify_enabled = False
							break

				if not _mask_modifiers(mesh):
					continue
				box = self.layout.box()
				header = box.row(align=True)
				header.scale_y = 1.2
				header.label(text=mesh.name, icon='OUTLINER_OB_MESH', translate=False)
				_draw_visibility_toggle(header, mesh, context)
				_draw_masks(box, mesh, context)
				masked_count += 1
			if masked_count < len(related):
				box = self.layout.box()
				col = box.column(align=True)
				for mesh in related:
					if _mask_modifiers(mesh):
						continue
					row = col.row(align=True)
					row.label(text=mesh.name, translate=False)
					_draw_visibility_toggle(row, mesh, context)
		else:
			_draw_masks(self.layout, obj, context)
			solidify = _solidify_modifiers(obj)
			if solidify:
				has_solidify = True
				all_solidify_enabled = all(mod.show_viewport for mod in solidify)


		if has_solidify:
			op = self.layout.operator("rig.ui_toggle_solidify", text="Toggle Solidify", icon='MOD_SOLIDIFY', depress=all_solidify_enabled)
			op.obj_name = obj.name
			op.enabled = not all_solidify_enabled

###############################################################################
# REGISTER

classes = (
	RIG_OT_set_id_float,
	RIG_OT_snap_ik_to_fk,
	RIG_OT_snap_fk_to_ik,
	RIG_PT_properties_ui,
	RIG_OT_toggle_object_visibility,
	RIG_OT_toggle_solidify,
	RIG_PT_visibility_ui,	
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)

if __name__ == "__main__":
	register()
