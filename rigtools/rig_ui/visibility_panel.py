import bpy
from bpy.props import BoolProperty, StringProperty, EnumProperty, CollectionProperty
from rigtools.armature_settings import get_armature_settings

def _mask_modifiers(obj):
	return [mod for mod in obj.modifiers if mod.type == 'MASK' and not mod.name.startswith('_')]	

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

def _draw_masks(layout, obj, context):
	col = layout.column(align=True)
	for mod in _mask_modifiers(obj):
		row = col.row(align=True)
		row.label(text=mod.name, translate=False)
		row.prop(mod, "show_viewport", text="", icon='HIDE_ON', invert_checkbox=True, emboss=False)

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
		return bool(_mask_modifiers(context.object))

	def draw(self, context):
		obj = context.object
		if obj.type == 'ARMATURE':
			masked_count = 0
			related = _related_meshes(obj, context.view_layer)
			for mesh in related:
				if not _mask_modifiers(mesh):
					continue
				box = self.layout.box()
				header = box.row(align=True)
				header.label(text=mesh.name, translate=False)
				header.prop(mesh, "hide_viewport", text="", icon='HIDE_ON', invert_checkbox=True, emboss=False)
				_draw_masks(box, mesh, context)
				masked_count += 1
			if masked_count == len(related):
				return
			box = self.layout.box()
			col = box.column(align=True)
			for mesh in related:
				if _mask_modifiers(mesh):
					continue
				row = col.row(align=True)
				row.label(text=mesh.name, translate=False)
				row.prop(mesh, "hide_viewport", text="", icon='HIDE_ON', invert_checkbox=True, emboss=False)
			
			return
		_draw_masks(self.layout, obj, context)
				

classes = (
	RIG_PT_visibility_ui,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
