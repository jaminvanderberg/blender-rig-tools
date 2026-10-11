import bpy
from bpy.props import StringProperty, EnumProperty, IntProperty, CollectionProperty
from rigtools.utils.skirt_legs import FORWARD_AXIS_ITEMS, scan_leg_assemblies

class SkirtLegSlot(bpy.types.PropertyGroup):
	thigh: StringProperty(name="Thigh", default="")
	shin: StringProperty(name="Shin", default="")
	forward_axis: EnumProperty(
		name="Forward Axis",
		items=FORWARD_AXIS_ITEMS,
		default='+X',
	)

class RIG_OT_add_skirt_leg(bpy.types.Operator):
	bl_idname = "rig.add_skirt_leg"
	bl_label = "Add Skirt Leg"

	def execute(self, context):
		context.window_manager.rig_skirt_legs.add()
		return {'FINISHED'}


class RIG_OT_remove_skirt_leg(bpy.types.Operator):
	bl_idname = "rig.remove_skirt_leg"
	bl_label = "Remove Skirt Leg"
	index: IntProperty()

	def execute(self, context):
		context.window_manager.rig_skirt_legs.remove(self.index)
		return {'FINISHED'}

def fill_skirt_legs(context):
	wm = context.window_manager
	wm.rig_skirt_legs.clear()
	for row in scan_leg_assemblies(context.object):
		slot = wm.rig_skirt_legs.add()
		slot.thigh = row["thigh"]
		slot.shin = row["shin"]
		slot.forward_axis = row["forward_axis"]

def draw_skirt_legs(context, layout, *, show_axis: bool):
	legs = context.window_manager.rig_skirt_legs

	leg_col = layout.column(align=True)
	header = leg_col.row(align=True)
	header.label(text="Thigh")
	if show_axis:
		header.label(text="Forward Axis")
	header.label(text="", icon='BLANK1')

	for i, leg in enumerate(legs):
		row = leg_col.row(align=True)
		row.prop_search(leg, "thigh", context.object.data, "bones", text="")
		if show_axis:
			row.prop(leg, "forward_axis", text="")
		op = row.operator("rig.remove_skirt_leg", text="", icon='REMOVE')
		op.index = i

	layout.operator("rig.add_skirt_leg", text="Add Leg", icon='ADD')

def iter_skirt_leg_slots(context):
	for slot in context.window_manager.rig_skirt_legs:
		if slot.thigh:
			yield slot

classes = (
	SkirtLegSlot,
	RIG_OT_add_skirt_leg,
	RIG_OT_remove_skirt_leg,
)


def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	bpy.types.WindowManager.rig_skirt_legs = CollectionProperty(type=SkirtLegSlot)


def unregister():
	del bpy.types.WindowManager.rig_skirt_legs
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
