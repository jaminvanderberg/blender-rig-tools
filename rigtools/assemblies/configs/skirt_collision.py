import json

class SkirtCollisionConfig:
	id = "skirt_collision"
	name = "Skirt Collision"
	description = "Handles skirt collision with legs."

	@staticmethod
	def present(assembly) -> bool:
		options = assembly.get_options()
		if not options.get("add_skirt_collision"):
			return False
		payload = options.get("skirt_collision")
		return bool(payload and payload.get("joints"))

	@staticmethod
	def load(assembly) -> dict:
		options = assembly.get_options()
		return dict(options.get("skirt_collision") or {})

	@staticmethod
	def default(assembly) -> dict:
		raw = getattr(assembly, "config_defaults_json", "") or "{}"
		defaults = json.loads(raw)
		return dict(defaults.get(SkirtCollisionConfig.id) or SkirtCollisionConfig.load(assembly))

	@staticmethod
	def draw(layout, assembly, context):
		payload = assembly.get_options().get("skirt_collision") or {}
		joints = payload.get("joints", [])
		if not joints:
			return

		col = layout.column(align=True)
		col.label(text="Skirt Collision")
		for joint in joints:
			pb = context.object.pose.bones.get(joint["collision_name"])
			if not pb:
				continue
			col.prop(pb, f'["influence"]', text=joint["fk_name"], slider=True)

classes = ()
