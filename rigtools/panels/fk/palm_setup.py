from collections import defaultdict
import json
import math
import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty, IntProperty, CollectionProperty
from rigtools.armature_settings import get_armature_settings
from rigtools.assemblies.reconfigure_assembly import reconfigure_assembly
from rigtools.assemblies.assembly_data import find_assembly
from rigtools.assemblies.assembly_transaction import AssemblyTransactionError, run_assembly_transaction
from rigtools.assemblies.palm_assembly import PalmAssemblyOptions, create_palm_assembly
from rigtools.assemblies.palm_templates import get_palm_template, validate_palm_templates
from rigtools.assemblies.template_options import resolve_template_options
from rigtools.panels.template_draw import TemplateDraw
from rigtools.tool.twist_bones import falloff_presets
from rigtools.utils.bone import get_selected_bones, select_bones
from rigtools.utils.bone_chain import sort_chains
from rigtools.utils.naming import flip_side_name, get_base_name, get_chain_order_key
from rigtools.utils.widget import fk_widget_types

class PalmOrderSlot(bpy.types.PropertyGroup):
	left: StringProperty(default="")
	right: StringProperty(default="")

class RIG_OT_move_palm_order(bpy.types.Operator):
	"""Move the palm order"""
	bl_idname = "rig.move_palm_order"
	bl_label = "Move Palm Order"
	bl_options = {'INTERNAL'}

	index: IntProperty()
	direction: IntProperty() # -1 or 1

	def execute(self, context):
		slots = context.window_manager.rig_palm_order
		j = self.index + self.direction
		if self.index < 0 or j < 0 or j >= len(slots):
			return {'CANCELLED'}

		slots.move(self.index, j)

		context.window_manager.rig_palm_order_mode = 'MANUAL'
		return {'FINISHED'}	

def find_palm_chains_from_selection(context):
	selected_bones = get_selected_bones(context)
	if not selected_bones:
		return {}

	by_side = defaultdict(list)
	for bone in selected_bones:
		_base, side = get_base_name(bone.name)
		key = "L" if "L" in side.upper() else ("R" if "R" in side.upper() else "C")
		by_side[key].append(bone.name)
		
	return by_side

def sort_palm_names(context, names, mode, invert):
	if mode == 'NAME':
		ordered = sorted(names, key=get_chain_order_key)
	else:
		chains = sort_chains(context, [[n] for n in names], 'LINEAR', mode, 0.0, False)
		ordered = [c[0] for c in chains]

	if invert:
		ordered = list(reversed(ordered))
	return ordered

def fill_palm_order(context, mode, invert):
	wm = context.window_manager
	left = [s.left for s in wm.rig_palm_order if s.left]
	right = [s.right for s in wm.rig_palm_order if s.right]

	if not left and not right:
		by_side = find_palm_chains_from_selection(context)
		if not by_side:
			return
		left = by_side.get("L") or by_side.get("C") or []
		right = by_side.get("R") or []

		if "C" in by_side and (("L" in by_side) or ("R" in by_side)):
			raise ValueError("Can't mix unsuffixed palm bones with .L/.R bones.")

	right_set = set(right)
	if left and right:
		left = sort_palm_names(context, left, mode, invert)
		right = []
		for name in left:
			flipped = flip_side_name(name)
			if not flipped or flipped not in right_set:
				raise ValueError(f"No matching right bone found for {name}")
			right.append(flipped)
		if set(right) != right_set:
			raise ValueError("Left/Right palm bones don't mirror.")
	elif left:
		left = sort_palm_names(context, left, mode, invert)
		right = []
	else:
		left = []
		right = sort_palm_names(context, right, mode, invert)

	wm.rig_palm_order.clear()
	for i in range(max(len(left), len(right))):
		slot = wm.rig_palm_order.add()
		slot.left = left[i] if i < len(left) else ""
		slot.right = right[i] if i < len(right) else ""

def _order_settings_changed(self, context):
	order_mode = context.window_manager.rig_palm_order_mode
	if order_mode == 'MANUAL':
		return
	try:
		fill_palm_order(context, order_mode, context.window_manager.rig_palm_order_invert)
	except ValueError as e:
		print(e)

def _palm_order_mode_items(self, context):
	items = []
	if getattr(self, "rig_palm_name_order_valid", True):
		items.append(('NAME', "Name", "Order by trailing letter/number", 1))
	items.extend([
		('X', 'X', "Order by X axis", 2),
		('Y', 'Y', "Order by Y axis", 3),
		('Z', 'Z', "Order by Z axis", 4),
		('MANUAL', 'Manual', "Manual order", 5),
	])
	return items

def get_palm_chains(context):
	slots = context.window_manager.rig_palm_order
	left = [slot.left for slot in slots if slot.left]
	right = [slot.right for slot in slots if slot.right]
	chains = []
	if left: 
		chains.append(left)
	if right:
		chains.append(right)
	return chains


class RIG_OT_advanced_palm_setup(bpy.types.Operator):
	"""Setup Palm Assembly with advanced options"""
	bl_idname = "rig.advanced_palm_setup"
	bl_label = "Generate Palm Assembly"
	bl_options = {'REGISTER', 'UNDO'}

	limb_property_base_name: StringProperty(
		name="Limb Name",
		description="Base name of the property to store the limb. Example: 'arm', 'leg', 'tail', etc.",
		default="hand"
	)

	fk_widget: EnumProperty(
		name="FK Widget",
		description="Type of widget to use for the FK bones",
		items=fk_widget_types,
		default='PILL'
	)

	index_falloff_type: EnumProperty(
		name="Index Falloff Type",
		description="Type of falloff for the index",
		items=falloff_presets + [('NONE', "None", "No falloff", '', 5)],
		default='SHARP'
	)

	pinky_falloff_type: EnumProperty(
		name="Pinky Falloff Type",
		description="Type of falloff for the pinky",
		items=falloff_presets + [('NONE', "None", "No falloff", '', 5)],
		default='LINEAR'
	)

	assembly_uid: StringProperty(
		name="Assembly UID",
		description="UID of the assembly to use for the palm assembly",
		default="",
		options={'HIDDEN'}
	)

	template_id: StringProperty(
		name="Template ID",
		description="Palm template to apply on invoke",
		default="",
		options={'HIDDEN'}
	)

	template_name: StringProperty(
		name="Template Name",
		description="Name of the template to use for the palm assembly",
		default="",
		options={'HIDDEN'}
	)


	@classmethod
	def description(cls, context, properties):
		if properties.template_id:
			template = get_palm_template(properties.template_id)
			if template:
				return template.description
		return "Setup palm assembly"

	##################################################################################################
	# invoke

	def _invoke_from_selection(self, context):
		chains = find_palm_chains_from_selection(context)

		if not chains:
			self.report({'ERROR'}, "No chains selected.")
			return {'CANCELLED'}

		self.template_name = "Advanced"

	def _invoke_from_template(self, context):
		template = get_palm_template(self.template_id)
		if not template:
			self.report({'ERROR'}, f"Unknown palm template: '{self.template_id}'")
			return {'CANCELLED'}

		option_values = resolve_template_options(PalmAssemblyOptions, template.options)
		for key, value in option_values.items():
			setattr(self, key, value)

		chains = find_palm_chains_from_selection(context)
		if not chains:
			self.report({'ERROR'}, "No chains selected.")
			return {'CANCELLED'}

		self.template_name = template.label

	def _invoke_from_assembly(self, context):
		assembly = find_assembly(context.object, self.assembly_uid)
		if not assembly:
			self.report({'ERROR'}, "Assembly not found.")
			return {'CANCELLED'}

		options = assembly.get_options()
		for key, value in options.items():
			setattr(self, key, value)

		self.template_name = assembly.template_name
		self.template_id = assembly.template_id

		wm = context.window_manager
		wm.rig_palm_order.clear()
		chain = assembly.get_chains()[0]
		side = assembly.side
		for name in chain:
			slot = wm.rig_palm_order.add()
			if "R" in side.upper():
				slot.right = name
			else:
				slot.left = name
		wm.rig_palm_order_mode = 'MANUAL'

	def invoke(self, context, event):
		show_dialog = True

		if self.assembly_uid:
			result = self._invoke_from_assembly(context)
		elif self.template_id:
			result = self._invoke_from_template(context)
			template = get_palm_template(self.template_id)
			if template:
				show_dialog = template.show_dialog
		else:
			result = self._invoke_from_selection(context)

		if result == {'CANCELLED'}:
			return result

		if not self.assembly_uid:
			by_side = find_palm_chains_from_selection(context)
			names = [n for group in by_side.values() for n in group]
			if not names:
				self.report({'ERROR'}, "No chains selected.")
				return {'CANCELLED'}

			wm = context.window_manager
			wm.rig_palm_order.clear()
			if any(math.isinf(get_chain_order_key(n)) for n in names):
				wm.rig_palm_name_order_valid = False
				wm.rig_palm_order_mode = 'Y'
			else:
				wm.rig_palm_name_order_valid = True
				wm.rig_palm_order_mode = 'NAME'
			wm.rig_palm_order_invert = False
			try:
				fill_palm_order(context, wm.rig_palm_order_mode, False)
			except ValueError as e:
				self.report({'ERROR'}, str(e))
				return {'CANCELLED'}

		if show_dialog:
			return context.window_manager.invoke_props_dialog(self, width=350)
		return self.execute(context)

	##################################################################################################
	# draw

	def draw(self, context):
		layout = self.layout
		template = get_palm_template(self.template_id) if self.template_id else None
		split_size = 0.6

		def field_visible(field_name):
			return True

		draw = TemplateDraw(self, template, split_size=split_size)

		draw.box_section(layout, ["limb_property_base_name", "fk_widget", "index_falloff_type", "pinky_falloff_type"], 
			"Palm Settings:", "SETTINGS", lambda col: (

			draw.draw_section(col, ["limb_property_base_name"], lambda: (
				draw.split_field(col, "Limb Name:", "limb_property_base_name"),
			)),
			draw.draw_section(col, ["fk_widget", "index_falloff_type", "pinky_falloff_type"], lambda: (
				draw.split_field(col, "Index Falloff Type:", "index_falloff_type"),
				draw.split_field(col, "Pinky Falloff Type:", "pinky_falloff_type"),
				draw.split_field(col, "FK Widget:", "fk_widget"),
			)),
		))

		def draw_palm_order(col):
			wm = context.window_manager
			slots = wm.rig_palm_order
			show_l = any(slot.left for slot in slots)
			show_r = any(slot.right for slot in slots)

			row = col.row(align=True)
			row.prop(wm, "rig_palm_order_mode", expand=True)
			col.prop(wm, "rig_palm_order_invert", text="Reverse")

			header = col.row(align=True)
			header.label(text="#")
			if show_l and show_r:
				header.label(text="Left")
				header.label(text="Right")
			elif show_l or show_r:
				header.label(text="Bones")
			header.label(text="", icon="BLANK1")

			for i, slot in enumerate(slots):
				row = col.row(align=True)
				row.label(text=str(i))
				if show_l and show_r:
					row.label(text=slot.left)
					row.label(text=slot.right)
				elif show_l:
					row.label(text=slot.left)
				elif show_r:
					row.label(text=slot.right)
				up = row.operator("rig.move_palm_order", text="", icon="TRIA_UP")
				up.index = i
				up.direction = -1
				down = row.operator("rig.move_palm_order", text="", icon="TRIA_DOWN")
				down.index = i
				down.direction = 1

		box = layout.box()
		box.label(text="Order:", icon="EMPTY_AXIS")
		col = box.column()
		draw_palm_order(col)


	##################################################################################################
	# execute

	def execute(self, context):
		if not self.limb_property_base_name:
			self.report({'ERROR'}, "Limb name is required.")
			return {'CANCELLED'}
		
		obj = context.object
		if not obj or obj.type != 'ARMATURE':
			self.report({'ERROR'}, "Active object must be an armature.")
			return {'CANCELLED'}
		armature_data = obj.data
		if obj.mode == 'OBJECT':
			self.report({'ERROR'}, "Can't use from Object mode")
			return {'CANCELLED'}

		if self.assembly_uid:
			assembly = find_assembly(obj, self.assembly_uid)
			if not assembly:
				self.report({'ERROR'}, f"Assembly '{self.assembly_uid}' not found.")
				return {'CANCELLED'}

		chains = get_palm_chains(context)
		if not chains:
			raise ValueError("No bones selected. Select at least one bone.")			

		# Switch to edit mode
		original_mode = obj.mode
		if obj.mode != 'EDIT':
			bpy.ops.object.mode_set(mode='EDIT')

		original_mirror = armature_data.use_mirror_x
		armature_data.use_mirror_x = False

		options = PalmAssemblyOptions(
			limb_property_base_name=self.limb_property_base_name.strip().lower(),
			fk_widget=self.fk_widget,
			index_falloff_type=self.index_falloff_type,
			pinky_falloff_type=self.pinky_falloff_type,
		)

		assembly_uid = self.assembly_uid

		def rebuild():
			return reconfigure_assembly(
				context, 
				assembly_uid, 
				lambda prior_configs: create_palm_assembly(
					context,
					chains,
					self.template_id,
					self.template_name,
					options,
					replacement_uid=assembly_uid,
					prior_configs=prior_configs,
				),
			)

		try:
			palm_controls = run_assembly_transaction(rebuild)
		except AssemblyTransactionError as e:
			self.report({'ERROR'}, str(e))
			bpy.ops.object.mode_set(mode=original_mode)
			context.object.data.use_mirror_x = original_mirror
			return {'CANCELLED'}

		if palm_controls:
			bpy.ops.pose.select_all(action='DESELECT')
			select_bones(context.object, palm_controls)

		chain_count = len(chains)
		self.report({'INFO'}, f"Successfully generated {chain_count} palm assembl{'ies' if chain_count != 1 else 'y'}.")
		context.object.data.use_mirror_x = original_mirror
		return {'FINISHED'}


classes = (
	PalmOrderSlot,
	RIG_OT_move_palm_order,
	RIG_OT_advanced_palm_setup,
)


def register():
	validate_palm_templates()
	for cls in classes:
		bpy.utils.register_class(cls)
	bpy.types.WindowManager.rig_palm_name_order_valid = BoolProperty(default=True)
	bpy.types.WindowManager.rig_palm_order = CollectionProperty(type=PalmOrderSlot)
	bpy.types.WindowManager.rig_palm_order_mode = EnumProperty(
		name="Order",
		items=_palm_order_mode_items,
		update=_order_settings_changed
	)
	bpy.types.WindowManager.rig_palm_order_invert = BoolProperty(
		name="Invert Order",
		description="Invert the order of the bones",
		default=False,
		update=_order_settings_changed
	)


def unregister():
	del bpy.types.WindowManager.rig_palm_order
	del bpy.types.WindowManager.rig_palm_order_mode
	del bpy.types.WindowManager.rig_palm_order_invert
	del bpy.types.WindowManager.rig_palm_name_order_valid
	for cls in classes:
		bpy.utils.unregister_class(cls)


if __name__ == "__main__":
	try:
		unregister()
	except Exception:
		pass
	register()

	bpy.ops.rig.advanced_palm_setup('INVOKE_DEFAULT')
