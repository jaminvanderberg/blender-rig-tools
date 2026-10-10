import json

class SkirtRideConfig:
	id = "skirt_ride"
	name = "Skirt Ride"
	description = "Short skirts typically ride up when the leg is lifted."

	@staticmethod
	def present(assembly) -> bool:
		options = assembly.get_options()
		if not options.get("add_skirt_ride"):
			return False
		payload = options.get("skirt_ride")
		return bool(payload and payload.get("legs"))

	@staticmethod
	def load(assembly) -> dict:
		options = assembly.get_options()
		return dict(options.get("skirt_ride") or {})

	@staticmethod
	def default(assembly) -> dict:
		raw = getattr(assembly, "config_defaults_json", "") or "{}"
		defaults = json.loads(raw)
		return dict(defaults.get(SkirtRideConfig.id) or SkirtRideConfig.load(assembly))

	@staticmethod
	def draw(layout, assembly, context):
		payload = assembly.get_options().get("skirt_ride") or {}
		mch_name = payload.get("mch_name", "")
		legs = payload.get("legs", [])
		pb = context.object.pose.bones.get(mch_name) if mch_name else None
		if not pb or not legs:
			return

		col = layout.column(align=True)
		col.label(text="Skirt Ride")
		for leg in legs:
			col.prop(pb, f'["{leg["thigh_name"]}"]', text=leg["thigh_name"], slider=True)

classes = ()
