import bpy
from bpy.props import StringProperty, CollectionProperty

class RigUISnapBoneItem(bpy.types.PropertyGroup):
	name: StringProperty()

class RigUISnapChainItem(bpy.types.PropertyGroup):
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

	return item

def delete_snap_chain(armature_data, switch_property):
	for i, item in enumerate(armature_data.rig_ui_snap_chains):
		if item.switch_property == switch_property:
			armature_data.rig_ui_snap_chains.remove(i)
			break

def find_snap_chain(armature_data, switch_property):
	for item in armature_data.rig_ui_snap_chains:
		if item.switch_property == switch_property:
			return item
	return None