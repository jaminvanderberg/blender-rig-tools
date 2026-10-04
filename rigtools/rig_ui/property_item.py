import bpy
from bpy.props import StringProperty, BoolProperty

class RigUIPropertyItem(bpy.types.PropertyGroup):
	property_name: StringProperty()
	label: StringProperty()

def find_property_item(armature_data, property_name):
	for item in armature_data.rig_ui_properties:
		if item.property_name == property_name:
			return item
	return None