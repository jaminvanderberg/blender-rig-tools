import bpy
from bpy.props import BoolProperty, StringProperty

from rigtools.tool.ik_parent import CONFIG_KEY, IKParent, IKParentTarget


class IkParentConfig:
	id = "ik_parent"
	name = "IK Parents"
	description = "Switchable parent targets for IK controls."

	@staticmethod
	def present(assembly) -> bool:
		if assembly.assembly_type != 'IK':
			return False
		options = assembly.get_options()
		if not options.get("ik_parent"):
			return False
		payload = options.get(CONFIG_KEY)
		return bool(payload and payload.get("parent_bone_names") and payload.get("property_name"))

	@staticmethod
	def load(assembly) -> dict:
		options = assembly.get_options()
		payload = dict(options.get(CONFIG_KEY) or {})
		return {
			"parents": [
				{"label": parent.label, "bone": parent.bone}
				for parent in assembly.ik_parents
			],
			"add_ik_control_as_pole_parent": bool(
				options.get(
					"add_ik_control_as_pole_parent",
					payload.get("add_ik_control_as_pole_parent", False),
				)
			),
			"self_parent_label": options.get(
				"ik_parent_self_parent_label",
				payload.get("self_parent_label", "Self"),
			),
			"property_name": payload.get("property_name", ""),
			"parent_bone_names": list(payload.get("parent_bone_names") or []),
		}

	@staticmethod
	def sync_to_wm(wm, data: dict):
		wm.rig_ik_parents.clear()
		for parent in data.get("parents") or []:
			slot = wm.rig_ik_parents.add()
			slot.label = parent.get("label", "")
			slot.bone = parent.get("bone", "")
		wm.rigtools_ik_parent_add_self = bool(data.get("add_ik_control_as_pole_parent", False))
		wm.rigtools_ik_parent_self_label = data.get("self_parent_label") or "Self"

	@staticmethod
	def payload_from_wm(wm) -> dict:
		return {
			"parents": [
				{"label": slot.label, "bone": slot.bone}
				for slot in wm.rig_ik_parents
			],
			"add_ik_control_as_pole_parent": bool(wm.rigtools_ik_parent_add_self),
			"self_parent_label": wm.rigtools_ik_parent_self_label,
		}

	@staticmethod
	def draw(layout, assembly, context):
		row = layout.row(align=True)
		op = row.operator("rig.assembly_config", text="IK Parents", icon='CON_ARMATURE')
		op.assembly_uid = assembly.uid
		op.config_id = IkParentConfig.id

	@staticmethod
	def draw_dialog(layout, assembly, context):
		wm = context.window_manager
		parents = wm.rig_ik_parents

		col = layout.column(align=True)
		for i, parent in enumerate(parents):
			row = col.row(align=True)
			row.prop(parent, "label", text="")
			row.prop_search(parent, "bone", context.object.data, "bones", text="")
			op = row.operator("rig.remove_ik_parent", text="", icon='REMOVE')
			op.index = i
		col.operator("rig.add_ik_parent", text="Add Parent", icon='ADD')

		layout.separator()
		row = layout.row(align=True)
		split = row.split(align=True, factor=0.6)
		split.prop(wm, "rigtools_ik_parent_add_self")
		if wm.rigtools_ik_parent_add_self:
			split.prop(wm, "rigtools_ik_parent_self_label", text="")

	@staticmethod
	def apply(context, assembly, old, new):
		parents = [
			IKParentTarget(label=entry["label"], bone=entry["bone"])
			for entry in new.get("parents") or []
		]
		add_self = bool(new.get("add_ik_control_as_pole_parent", False))
		self_label = new.get("self_parent_label") or "Self"

		if not parents and not add_self:
			raise ValueError("At least one IK parent is required")

		bones = context.object.data.bones
		for parent in parents:
			if not parent.label.strip():
				raise ValueError("IK parent labels cannot be empty")
			if not parent.bone:
				raise ValueError("IK parent bones cannot be empty")
			if parent.bone not in bones:
				raise ValueError(f"IK parent bone '{parent.bone}' was not found")

		IKParent.apply_from_assembly(
			context,
			assembly,
			parents,
			add_self=add_self,
			self_label=self_label,
		)


classes = ()


def register():
	wm = bpy.types.WindowManager
	wm.rigtools_ik_parent_add_self = BoolProperty(
		name="Add IK Control as Pole Parent",
		description="Add the IK control as a parent option (typically for the pole)",
		default=False,
	)
	wm.rigtools_ik_parent_self_label = StringProperty(
		name="Parent Label",
		description="Label for the self parent of the IK parent",
		default="Self",
	)


def unregister():
	wm = bpy.types.WindowManager
	del wm.rigtools_ik_parent_self_label
	del wm.rigtools_ik_parent_add_self
