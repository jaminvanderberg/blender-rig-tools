from rigtools.armature_settings import get_armature_settings

class PropertyValuesConfig:
	id = "property_values"
	name = "Property Values"
	description = "Keeps rig property values across reconfigure."

	@staticmethod
	def present(assembly) -> bool:
		return len(assembly.properties) > 0

	@staticmethod
	def snapshot(context, assembly) -> dict:
		obj = context.object
		prop_bone = obj.pose.bones.get(get_armature_settings(obj.data, context).property_bone_name)
		if not prop_bone:
			return {}
		return {p.name: prop_bone[p.name] for p in assembly.properties if p.name in prop_bone}

	@staticmethod
	def draw(layout, assembly, context):
		pass
