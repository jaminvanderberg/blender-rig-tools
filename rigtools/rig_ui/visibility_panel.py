import bpy
from bpy.props import BoolProperty, StringProperty, EnumProperty, CollectionProperty
from rigtools.armature_settings import get_armature_settings
from rigtools.preferences import get_separators

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
	seps = set(get_separators())
	while rest and rest[0] in seps:
		rest = rest[1:]
	return rest or name

def _draw_masks(layout, obj, context):
	col = layout.column(align=True)
	for mod in _mask_modifiers(obj):
		row = col.row(align=True)
		row.label(text=_mask_label(mod.name), translate=False)
		row.prop(mod, "show_viewport", text="", icon='HIDE_ON', invert_checkbox=True, emboss=False)

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
				header.label(text=mesh.name, translate=False)
				header.prop(mesh, "hide_viewport", text="", icon='HIDE_ON', invert_checkbox=True, emboss=False)
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
					row.prop(mesh, "hide_viewport", text="", icon='HIDE_ON', invert_checkbox=True, emboss=False)	
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

classes = (
	RIG_PT_visibility_ui,
	RIG_OT_toggle_solidify,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
