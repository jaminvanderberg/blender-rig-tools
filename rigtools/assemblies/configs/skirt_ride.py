import json

import bpy
from bpy.props import CollectionProperty, FloatProperty, IntProperty, StringProperty
from bpy.types import PropertyGroup

from rigtools.tool.skirt_ride import SkirtRide


class SkirtRideLegSlot(PropertyGroup):
	thigh_name: StringProperty(name="Thigh")
	helper_name: StringProperty(name="Helper")
	bend_axis: StringProperty(name="Bend Axis")
	bend_sign: IntProperty(name="Bend Sign")
	influence: FloatProperty(name="Influence", min=0.0, soft_max=2.0)


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
	def sync_to_wm(wm, payload: dict):
		wm.rigtools_skirt_ride_mch_name = payload.get("mch_name", "")
		wm.rigtools_skirt_ride_legs.clear()
		for leg in payload.get("legs", []):
			slot = wm.rigtools_skirt_ride_legs.add()
			slot.thigh_name = leg.get("thigh_name", "")
			slot.helper_name = leg.get("helper_name", "")
			slot.bend_axis = leg.get("bend_axis", "")
			slot.bend_sign = int(leg.get("bend_sign", 1))
			slot.influence = float(leg.get("influence", 0.0))

	@staticmethod
	def payload_from_wm(wm) -> dict:
		return {
			"mch_name": wm.rigtools_skirt_ride_mch_name,
			"legs": [
				{
					"thigh_name": slot.thigh_name,
					"helper_name": slot.helper_name,
					"bend_axis": slot.bend_axis,
					"bend_sign": slot.bend_sign,
					"influence": slot.influence,
				}
				for slot in wm.rigtools_skirt_ride_legs
			],
		}

	@staticmethod
	def draw(layout, assembly, context):
		wm = context.window_manager
		if not wm.rigtools_skirt_ride_legs:
			layout.label(text="No skirt ride legs in range", icon='INFO')
			return
		for slot in wm.rigtools_skirt_ride_legs:
			label = slot.thigh_name or slot.helper_name or "Leg"
			layout.prop(slot, "influence", text=label)

	@staticmethod
	def apply(context, assembly, old: dict, new: dict):
		SkirtRide.apply_config(context, assembly, old, new)


classes = (
	SkirtRideLegSlot,
)
