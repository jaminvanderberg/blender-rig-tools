import bpy
from bpy.props import StringProperty
from bpy.types import Operator, Panel

from rigtools.utils.bone import flip_side_name, same_side_names

TWIST_MAP_KEY = "rigtools_twist_parents"


def _twist_map(armature):
	"""Return a plain dict copy of the armature twist map."""
	raw = armature.get(TWIST_MAP_KEY)
	if not raw:
		return {}
	return {str(k): str(v) for k, v in raw.items()}


def _write_twist_map(armature, mapping):
	"""Replace the armature twist map. Assigning a new dict keeps it as an ID property."""
	armature[TWIST_MAP_KEY] = mapping


def _bone_collection(armature, use_edit_bones=False):
	return armature.edit_bones if use_edit_bones else armature.bones


def _live_twist_map(armature, *, use_edit_bones=False):
	"""Map entries whose twist bones still exist. Draw-safe (no ID writes)."""
	coll = _bone_collection(armature, use_edit_bones)
	return {name: parent for name, parent in _twist_map(armature).items() if name in coll}


def prune_twist_map(armature, *, use_edit_bones=False):
	"""Persist a cleaned map by dropping entries for deleted twist bones."""
	mapping = _twist_map(armature)
	cleaned = _live_twist_map(armature, use_edit_bones=use_edit_bones)
	if cleaned != mapping:
		_write_twist_map(armature, cleaned)
	return cleaned


def get_twist_parent(armature, bone_name):
	return _twist_map(armature).get(bone_name, "")


def set_twist_parent(armature, bone_name, parent_name):
	use_edit_bones = len(armature.edit_bones) > 0
	mapping = prune_twist_map(armature, use_edit_bones=use_edit_bones)
	if parent_name:
		mapping[bone_name] = parent_name
	else:
		mapping.pop(bone_name, None)
	_write_twist_map(armature, mapping)


def get_twist_bones(armature, parent_name, *, use_edit_bones=False):
	"""Return bones registered as twists of parent_name. Order is undefined."""
	coll = _bone_collection(armature, use_edit_bones)
	mapping = _live_twist_map(armature, use_edit_bones=use_edit_bones)
	return [
		coll[name]
		for name, twist_parent in mapping.items()
		if twist_parent == parent_name
	]


def get_twist_chain(armature, parent_name, *, use_edit_bones=False):
	"""Return twist bone names for parent_name in parent-chain order.

	Raises ValueError if the registered twists are not a single linear chain.
	use_edit_bones=True reads parenting from edit_bones (needed in edit mode).
	"""
	twists = get_twist_bones(armature, parent_name, use_edit_bones=use_edit_bones)
	if not twists:
		return []

	names = {b.name for b in twists}
	coll = _bone_collection(armature, use_edit_bones)

	def parent_of(name):
		bone = coll.get(name)
		if not bone or not bone.parent:
			return None
		return bone.parent.name

	roots = [n for n in names if parent_of(n) not in names]
	if len(roots) != 1:
		raise ValueError(
			f"Twist bones for '{parent_name}' must form one chain "
			f"(found {len(roots)} roots, expected 1)"
		)

	children = {n: [] for n in names}
	for n in names:
		p = parent_of(n)
		if p in names:
			children[p].append(n)

	for n, kids in children.items():
		if len(kids) > 1:
			raise ValueError(
				f"Twist bones for '{parent_name}' branch at '{n}' "
				f"(expected a linear chain)"
			)

	order = []
	current = roots[0]
	seen = set()
	while current:
		if current in seen:
			raise ValueError(f"Twist bones for '{parent_name}' contain a cycle")
		seen.add(current)
		order.append(current)
		kids = children[current]
		current = kids[0] if kids else None

	if set(order) != names:
		raise ValueError(
			f"Twist bones for '{parent_name}' are not a single connected chain"
		)

	return order


def get_active_bone(context):
	"""Bone datablock for the active edit or pose bone."""
	obj = context.object
	if not obj or obj.type != 'ARMATURE':
		return None
	if context.edit_bone:
		return obj.data.bones.get(context.edit_bone.name)
	return context.bone


def _rna_get_twist_parent_ui(self):
	context = bpy.context
	bone = get_active_bone(context)
	if not bone or not context.object:
		return ""
	return get_twist_parent(context.object.data, bone.name)


def _rna_set_twist_parent_ui(self, value):
	context = bpy.context
	bone = get_active_bone(context)
	if not bone or not context.object:
		return
	set_twist_parent(context.object.data, bone.name, value)


class RIG_OT_set_twist_parent(Operator):
	bl_idname = "rig.set_twist_parent"
	bl_label = "Set Twist Parent"
	bl_description = "Set the active bone as twist parent of the other selected bones"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(cls, context):
		return (
			context.object
			and context.object.type == 'ARMATURE'
			and context.mode == 'EDIT_ARMATURE'
			and context.active_bone is not None
			and len(context.selected_editable_bones) >= 2
		)

	def execute(self, context):
		armature = context.object.data
		active = context.active_bone
		bones = armature.bones
		edit_bones = armature.edit_bones
		use_mirror = armature.use_mirror_x

		skip = {active.name}
		active_mirror = flip_side_name(active.name) if use_mirror else None
		if active_mirror and active_mirror in edit_bones:
			skip.add(active_mirror)

		selected_names = {b.name for b in context.selected_editable_bones}
		handled = set(skip)
		set_count = 0
		missing = []

		# Batch into one map write so we don't thrash ID properties
		mapping = prune_twist_map(armature, use_edit_bones=True)

		for edit_bone in context.selected_editable_bones:
			if edit_bone.name in handled:
				continue

			parent_name = active.name
			if use_mirror and active_mirror and not same_side_names(edit_bone.name, active.name):
				parent_name = active_mirror
				if parent_name not in bones:
					missing.append(edit_bone.name)
					continue

			mapping[edit_bone.name] = parent_name
			handled.add(edit_bone.name)
			set_count += 1

			if use_mirror and active_mirror:
				mirror_name = flip_side_name(edit_bone.name)
				if (
					mirror_name
					and mirror_name in edit_bones
					and mirror_name not in handled
					and mirror_name not in selected_names
				):
					if active_mirror in bones:
						mapping[mirror_name] = active_mirror
						handled.add(mirror_name)
						set_count += 1

		_write_twist_map(armature, mapping)

		if missing:
			self.report(
				{'WARNING'},
				f"Set {set_count} bone(s); skipped {len(missing)} with no mirrored parent '{active_mirror}'",
			)
		elif use_mirror and active_mirror:
			self.report({'INFO'}, f"Set twist parent on {set_count} bone(s) (X-Mirror active)")
		else:
			self.report({'INFO'}, f"Set twist parent on {set_count} bone(s)")
		return {'FINISHED'}


class RIG_OT_clear_twist_parent(Operator):
	bl_idname = "rig.clear_twist_parent"
	bl_label = "Clear Twist Parent"
	bl_description = "Clear the twist parent from the selected bones"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(cls, context):
		return (
			context.object
			and context.object.type == 'ARMATURE'
			and context.mode == 'EDIT_ARMATURE'
			and bool(context.selected_editable_bones)
		)

	def execute(self, context):
		armature = context.object.data
		mapping = prune_twist_map(armature, use_edit_bones=True)
		cleared = 0
		for edit_bone in context.selected_editable_bones:
			if mapping.pop(edit_bone.name, None) is not None:
				cleared += 1
		_write_twist_map(armature, mapping)

		self.report({'INFO'}, f"Cleared twist parent on {cleared} bone(s)")
		return {'FINISHED'}


class RIG_PT_bone(Panel):
	bl_label = "Rig Tools"
	bl_space_type = 'PROPERTIES'
	bl_region_type = 'WINDOW'
	bl_context = 'bone'

	@classmethod
	def poll(cls, context):
		return get_active_bone(context) is not None

	def draw(self, context):
		layout = self.layout
		bone = get_active_bone(context)
		armature = context.object.data

		layout.prop_search(
			context.window_manager,
			"rigtools_twist_parent",
			armature,
			"bones",
			text="Twist Parent",
		)

		twists = get_twist_bones(
			armature,
			bone.name,
			use_edit_bones=(context.mode == 'EDIT_ARMATURE'),
		)
		if not twists:
			return

		box = layout.box()
		box.label(text="Twist Bones:")
		col = box.column(align=True)
		for twist in twists:
			col.label(text=twist.name, icon='BONE_DATA')


def menu_edit_armature_parent(self, context):
	layout = self.layout
	layout.separator()
	layout.operator("rig.set_twist_parent", text="Set Twist Parent")
	layout.operator("rig.clear_twist_parent", text="Clear Twist Parent")


classes = (
	RIG_OT_set_twist_parent,
	RIG_OT_clear_twist_parent,
	RIG_PT_bone,
)

addon_keymaps = []


def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	bpy.types.WindowManager.rigtools_twist_parent = StringProperty(
		name="Twist Parent",
		description="Deform bone this twist belongs to. Leave empty if this is not a twist bone",
		get=_rna_get_twist_parent_ui,
		set=_rna_set_twist_parent_ui,
	)
	bpy.types.VIEW3D_MT_edit_armature_parent.append(menu_edit_armature_parent)

	wm = bpy.context.window_manager
	kc = wm.keyconfigs.addon
	if kc:
		km = kc.keymaps.new(name='Armature', space_type='EMPTY')
		kmi = km.keymap_items.new(
			"rig.set_twist_parent",
			type='P',
			value='PRESS',
			ctrl=True,
			shift=True,
		)
		addon_keymaps.append((km, kmi))
		kmi = km.keymap_items.new(
			"rig.clear_twist_parent",
			type='P',
			value='PRESS',
			ctrl=True,
			alt=True,
		)
		addon_keymaps.append((km, kmi))


def unregister():
	for km, kmi in addon_keymaps:
		km.keymap_items.remove(kmi)
	addon_keymaps.clear()

	bpy.types.VIEW3D_MT_edit_armature_parent.remove(menu_edit_armature_parent)
	del bpy.types.WindowManager.rigtools_twist_parent
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
