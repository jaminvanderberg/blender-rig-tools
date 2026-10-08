import json

class SkirtRideConfig:
	id = "skirt_ride"
	name = "Skirt Ride"
	description = "Short skirts typically ride up when the leg is lifted."
	
	@staticmethod
	def present(assembly) -> bool:
		options = assembly.get_options()
		return bool(options.get("add_skirt_ride"))

	@staticmethod
	def load(assembly) -> dict:
		options = assembly.get_options()
		return {
			"influences": options.get("skirt_ride_influences", {}),
		}

	@staticmethod
	def default(assembly) -> dict:
		raw = getattr(assembly, "config_defaults_json", "") or "{}"
		defaults = json.loads(raw)
		return defaults.get(SkirtRideConfig.id, SkirtRideConfig.load(assembly))

	@staticmethod
	def draw(layout, data, context):
		layout.prop(data, "skirt_ride_influences[ORG-thigh.L]", text="Thigh.L")
		layout.prop(data, "skirt_ride_influences[ORG-thigh.R]", text="Thigh.R")
	
	@staticmethod
	def apply(context, assembly, old: dict, new: dict):
		options = assembly.get_options()
