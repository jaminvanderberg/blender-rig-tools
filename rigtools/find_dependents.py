import re
import bpy

_BONE_PATH_RE = re.compile(r'pose\.bones\["([^"]+)"\]')


class RIG_PG_dependent_item(bpy.types.PropertyGroup):
	bone_name: bpy.props.StringProperty()
	kind: bpy.props.EnumProperty(
		items=[
			('CHILD', "Child", ""),
			('CONSTRAINT', "Constraint", ""),
			('DRIVER', "Driver", ""),
		],
	)
	detail: bpy.props.StringProperty()


def _path_refs_bone(data_path, bone_name):
	if not data_path:
		return False
	return any(m.group(1) == bone_name for m in _BONE_PATH_RE.finditer(data_path))


def _owner_bone_from_path(data_path):
	if not data_path:
		return ""
	match = _BONE_PATH_RE.search(data_path)
	return match.group(1) if match else ""


def _constraint_hits(constraint, obj, bone_name):
	hits = []
	if getattr(constraint, "target", None) == obj and getattr(constraint, "subtarget", "") == bone_name:
		hits.append("target")
	if getattr(constraint, "pole_target", None) == obj and getattr(constraint, "pole_subtarget", "") == bone_name:
		hits.append("pole")
	if constraint.type == 'ARMATURE':
		for i, t in enumerate(constraint.targets):
			if t.target == obj and t.subtarget == bone_name:
				hits.append(f"target[{i}]")
	return hits


def find_dependents(obj, bone_name):
	results = []

	bones = obj.data.bones
	if bone_name not in bones:
		return results

	bone = bones[bone_name]
	for child in bone.children:
		results.append({
			"bone_name": child.name,
			"kind": 'CHILD',
			"detail": "",
		})

	for pbone in obj.pose.bones:
		for constraint in pbone.constraints:
			hits = _constraint_hits(constraint, obj, bone_name)
			for hit in hits:
				muted = " (muted)" if constraint.mute else ""
				results.append({
					"bone_name": pbone.name,
					"kind": 'CONSTRAINT',
					"detail": f"{constraint.type} · {constraint.name} · {hit}{muted}",
				})

	anim = obj.animation_data
	if anim:
		for fcurve in anim.drivers:
			driver = fcurve.driver
			if not driver:
				continue
			matched = False
			var_notes = []
			for var in driver.variables:
				for target in var.targets:
					if target.id != obj:
						continue
					if target.bone_target == bone_name or _path_refs_bone(target.data_path, bone_name):
						matched = True
						src = target.bone_target or target.data_path
						var_notes.append(f"{var.name} ← {src}")
			if matched:
				owner = _owner_bone_from_path(fcurve.data_path)
				results.append({
					"bone_name": owner or bone_name,
					"kind": 'DRIVER',
					"detail": f"{fcurve.data_path}" + (f" · {', '.join(var_notes)}" if var_notes else ""),
				})

	return results


def _store_results(wm, source_bone, results):
	wm.rig_dependent_source = source_bone
	wm.rig_dependent_items.clear()
	for item in results:
		row = wm.rig_dependent_items.add()
		row.bone_name = item["bone_name"]
		row.kind = item["kind"]
		row.detail = item["detail"]


def _reveal_bone(obj, bone_name):
	data_bone = obj.data.bones.get(bone_name)
	if not data_bone:
		return False

	pbone = obj.pose.bones.get(bone_name)
	if pbone is not None and hasattr(pbone, "hide"):
		pbone.hide = False
	else:
		data_bone.hide = False

	for coll in data_bone.collections:
		coll.is_visible = True
	return True


def _activate_bone(context, obj, bone_name):
	if not _reveal_bone(obj, bone_name):
		return False

	if obj.mode == 'EDIT':
		edit_bones = obj.data.edit_bones
		for eb in edit_bones:
			eb.select = False
			eb.select_head = False
			eb.select_tail = False
		eb = edit_bones[bone_name]
		eb.select = True
		eb.select_head = True
		eb.select_tail = True
		edit_bones.active = eb
	else:
		if obj.mode != 'POSE':
			bpy.ops.object.mode_set(mode='POSE')
		pose_bones = obj.pose.bones
		# Blender 5+: selection is on PoseBone; 4.x keeps it on Bone
		if hasattr(pose_bones[bone_name], "select"):
			for pb in pose_bones:
				pb.select = False
			pose_bones[bone_name].select = True
		else:
			for b in obj.data.bones:
				b.select = False
			obj.data.bones[bone_name].select = True
		obj.data.bones.active = obj.data.bones[bone_name]

	return True


class RIG_OT_find_dependents(bpy.types.Operator):
	"""List bones that depend on the active bone (children, constraints, drivers)"""
	bl_idname = "rig.find_dependents"
	bl_label = "Find Dependents"
	bl_options = {'REGISTER'}

	bone_name: bpy.props.StringProperty(
		name="Bone",
		description="Bone to inspect. Leave empty to use the active bone.",
		default="",
	)

	def execute(self, context):
		obj = context.active_object
		if not obj or obj.type != 'ARMATURE':
			self.report({'ERROR'}, "Active object must be an armature.")
			return {'CANCELLED'}

		bone_name = self.bone_name
		if not bone_name:
			if obj.mode == 'EDIT':
				active = obj.data.edit_bones.active
				bone_name = active.name if active else ""
			else:
				active = obj.data.bones.active
				bone_name = active.name if active else ""

		if not bone_name:
			self.report({'ERROR'}, "No active bone.")
			return {'CANCELLED'}

		if obj.mode == 'EDIT':
			bpy.ops.object.mode_set(mode='POSE')

		results = find_dependents(obj, bone_name)
		_store_results(context.window_manager, bone_name, results)

		self.report({'INFO'}, f"{len(results)} dependent(s) of '{bone_name}'")
		return {'FINISHED'}


class RIG_OT_jump_to_dependent(bpy.types.Operator):
	"""Select and frame a dependent bone"""
	bl_idname = "rig.jump_to_dependent"
	bl_label = "Jump to Bone"
	bl_options = {'REGISTER', 'UNDO'}

	bone_name: bpy.props.StringProperty()
	frame_view: bpy.props.BoolProperty(default=True)

	def execute(self, context):
		obj = context.active_object
		if not obj or obj.type != 'ARMATURE':
			self.report({'ERROR'}, "Active object must be an armature.")
			return {'CANCELLED'}

		if not self.bone_name or self.bone_name not in obj.data.bones:
			self.report({'ERROR'}, f"Bone '{self.bone_name}' not found.")
			return {'CANCELLED'}

		if not _activate_bone(context, obj, self.bone_name):
			self.report({'ERROR'}, f"Could not activate '{self.bone_name}'.")
			return {'CANCELLED'}

		if self.frame_view:
			for area in context.screen.areas:
				if area.type != 'VIEW_3D':
					continue
				for region in area.regions:
					if region.type != 'WINDOW':
						continue
					with context.temp_override(area=area, region=region):
						bpy.ops.view3d.view_selected()
					break
				break

		return {'FINISHED'}


class RIG_OT_clear_dependents(bpy.types.Operator):
	"""Clear the dependents report"""
	bl_idname = "rig.clear_dependents"
	bl_label = "Clear"
	bl_options = {'REGISTER'}

	def execute(self, context):
		wm = context.window_manager
		wm.rig_dependent_source = ""
		wm.rig_dependent_items.clear()
		return {'FINISHED'}


class RIG_PT_find_dependents(bpy.types.Panel):
	bl_label = "Find Dependents"
	bl_idname = "RIG_PT_find_dependents"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = "Rig Tools"

	@classmethod
	def poll(cls, context):
		return context.object and context.object.type == 'ARMATURE' and context.mode in {'EDIT_ARMATURE', 'POSE'}

	def draw(self, context):
		layout = self.layout
		wm = context.window_manager

		row = layout.row(align=True)
		row.operator("rig.find_dependents", icon='VIEWZOOM')
		if wm.rig_dependent_source:
			row.operator("rig.clear_dependents", text="", icon='X')

		source = wm.rig_dependent_source
		if not source:
			return

		layout.label(text=f"Of: {source}", icon='BONE_DATA')

		by_kind = {'CHILD': [], 'CONSTRAINT': [], 'DRIVER': []}
		for i, item in enumerate(wm.rig_dependent_items):
			by_kind[item.kind].append((i, item))

		sections = [
			('CHILD', "Children", 'OUTLINER_OB_ARMATURE'),
			('CONSTRAINT', "Constrained by", 'CONSTRAINT_BONE'),
			('DRIVER', "Driven from", 'DRIVER'),
		]

		if not wm.rig_dependent_items:
			layout.label(text="No dependents found.")
			return

		for kind, title, icon in sections:
			rows = by_kind[kind]
			if not rows:
				continue
			box = layout.box()
			box.label(text=f"{title} ({len(rows)})", icon=icon)
			for _i, item in rows:
				col = box.column(align=True)
				jump = col.operator(
					"rig.jump_to_dependent",
					text=item.bone_name,
					icon='RESTRICT_SELECT_OFF',
				)
				jump.bone_name = item.bone_name
				jump.frame_view = True
				if item.detail:
					col.label(text=item.detail)


classes = (
	RIG_PG_dependent_item,
	RIG_OT_find_dependents,
	RIG_OT_jump_to_dependent,
	RIG_OT_clear_dependents,
	RIG_PT_find_dependents,
)


def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	bpy.types.WindowManager.rig_dependent_source = bpy.props.StringProperty(
		name="Dependent Source Bone",
		default="",
	)
	bpy.types.WindowManager.rig_dependent_items = bpy.props.CollectionProperty(
		type=RIG_PG_dependent_item,
	)


def unregister():
	del bpy.types.WindowManager.rig_dependent_items
	del bpy.types.WindowManager.rig_dependent_source
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)


if __name__ == "__main__":
	try:
		unregister()
	except Exception:
		pass
	register()
