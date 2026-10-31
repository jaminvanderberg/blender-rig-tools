import json
import bpy
from bpy.props import BoolProperty, CollectionProperty, IntProperty, PointerProperty, StringProperty
from rigtools.armature_settings import CURRENT_RIG_DATA_VERSION, needs_rig_upgrade
from rigtools.assemblies.assembly_data import CONFIG_OPTION_KEYS
from rigtools.assemblies.fk_templates import get_fk_template
from rigtools.assemblies.ik_templates import get_ik_template
from rigtools.assemblies.palm_templates import get_palm_template
from rigtools.assemblies.torso_templates import get_torso_template
from rigtools.data_viewer.checks import apply_fix, assemblies_by_limb, bone_names, collection_names, get_property_bone, limb_label, run_checks
from rigtools.panels.assembly.assembly_panel import ASSEMBLY_TYPE_OPERATORS, SELECT_SIMILAR_ROLES
from rigtools.utils.bone import select_bones
from rigtools.utils.icons import icon
from rigtools.utils.naming import LIMB_COLLECTION_ROLES, side_display_name
from rigtools.utils.widget import remove_widget, unused_standard_widgets

# Up to this many widgets are named in the Clear Unused Widgets dialog; more are just counted
LISTED_WIDGETS_MAX = 20

TEMPLATE_GETTERS = {
	'IK': get_ik_template,
	'FK': get_fk_template,
	'TORSO': get_torso_template,
	'PALM': get_palm_template,
}

TYPE_LABELS = {
	'IK': "IK",
	'FK': "FK",
	'TORSO': "Torso",
	'PALM': "Palm",
}

SEVERITY_ICONS = {
	'ERROR': 'STATUS_ERROR_FILLED',
	'WARNING': 'STATUS_WARNING_FILLED',
	'INFO': 'STATUS_INFO',
}

SECTIONS = (
	("org", "ORG Bones"),
	("twist", "Twist Bones"),
	("mechanism", "Mechanism Bones"),
	("properties", "Properties"),
	("objects", "Objects"),
	("reparent", "Reparent Rules"),
	("ik_parents", "IK Parents"),
	("options", "Options"),
)

def can_select(context):
	return context.mode in {'POSE', 'EDIT_ARMATURE'}

def flagged_uids(wm):
	return {i.assembly_uid for i in wm.rigtools_data_issues if i.assembly_uid and i.severity != 'INFO'}

def template_icon(assembly):
	getter = TEMPLATE_GETTERS.get(assembly.assembly_type)
	template = getter(assembly.template_id) if getter else None
	return icon(template.icon) if template else 'NONE'

def _format_value(value):
	if isinstance(value, float):
		return f"{value:.3f}".rstrip("0").rstrip(".")
	if isinstance(value, (list, tuple)):
		return ", ".join(_format_value(v) for v in value)
	return str(value)

STYLE_FIELDS_PER_LINE = 3

def balanced_lines(items, max_per_line):
	"""Split into as few lines as max_per_line allows, sized evenly: 4 items at 3 per line -> 2 + 2, not 3 + 1"""
	line_count = -(-len(items) // max_per_line)
	lines = []
	start = 0
	for i in range(line_count):
		size = len(items) // line_count + (1 if i < len(items) % line_count else 0)
		lines.append(items[start:start + size])
		start += size
	return lines

def style_fields(style_json) -> list[tuple[str, str]]:
	"""(label, value) per stored style setting"""
	try:
		style = json.loads(style_json or "{}")
	except ValueError:
		return [("style", "can't be read")]
	return [(key.replace("_", " ").capitalize(), _format_value(value)) for key, value in style.items()]

class RigDataIssue(bpy.types.PropertyGroup):
	severity: StringProperty()
	message: StringProperty()
	assembly_uid: StringProperty()
	bone: StringProperty()
	fix_id: StringProperty()
	fix_args_json: StringProperty()

class RigDataSections(bpy.types.PropertyGroup):
	org: BoolProperty(default=True)
	twist: BoolProperty(default=False)
	mechanism: BoolProperty(default=False)
	properties: BoolProperty(default=False)
	objects: BoolProperty(default=False)
	reparent: BoolProperty(default=False)
	ik_parents: BoolProperty(default=False)
	options: BoolProperty(default=False)

def store_issues(context):
	wm = context.window_manager
	wm.rigtools_data_issues.clear()
	for issue in run_checks(context.object):
		row = wm.rigtools_data_issues.add()
		row.severity = issue.severity
		row.message = issue.message
		row.assembly_uid = issue.assembly_uid
		row.bone = issue.bone
		row.fix_id = issue.fix_id
		row.fix_args_json = json.dumps(issue.fix_args)
	wm.rigtools_data_checked = context.object.name

class RIG_OT_data_select(bpy.types.Operator):
	bl_idname = "rig.data_select"
	bl_label = "Select"
	bl_description = "Show this assembly in the list and select its bones"
	bl_options = {'REGISTER', 'UNDO'}

	assembly_uid: StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
	bone_names_json: StringProperty(options={'HIDDEN', 'SKIP_SAVE'})

	def execute(self, context):
		obj = context.object
		if self.assembly_uid:
			for i, assembly in enumerate(obj.data.rigtools_assemblies):
				if assembly.uid == self.assembly_uid:
					context.window_manager.rigtools_data_assembly_index = i
					break

		names = json.loads(self.bone_names_json or "[]")
		if names:
			if not can_select(context):
				self.report({'INFO'}, "Enter Pose or Edit mode to select bones")
			else:
				select_bones(obj, names, deselect=True)
		return {'FINISHED'}

class RIG_OT_data_check(bpy.types.Operator):
	bl_idname = "rig.data_check"
	bl_label = "Check Data"
	bl_description = "Look for RigTools data that no longer matches the rig"

	def execute(self, context):
		store_issues(context)
		count = len(context.window_manager.rigtools_data_issues)
		self.report({'INFO'}, f"{count} issue{'s' if count != 1 else ''} found")
		return {'FINISHED'}

class RIG_OT_data_fix_issue(bpy.types.Operator):
	bl_idname = "rig.data_fix_issue"
	bl_label = "Fix Issue"
	bl_description = "Remove the reference that points at nothing"
	bl_options = {'REGISTER', 'UNDO'}

	index: IntProperty(options={'HIDDEN', 'SKIP_SAVE'})

	def execute(self, context):
		issues = context.window_manager.rigtools_data_issues
		if not 0 <= self.index < len(issues) or not issues[self.index].fix_id:
			return {'CANCELLED'}
		issue = issues[self.index]
		apply_fix(context.object, issue.fix_id, json.loads(issue.fix_args_json))
		store_issues(context)
		return {'FINISHED'}

class RIG_OT_data_fix_all(bpy.types.Operator):
	bl_idname = "rig.data_fix_all"
	bl_label = "Fix All"
	bl_description = "Apply every available fix. Fixes only remove references to things that no longer exist"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(cls, context):
		return any(i.fix_id for i in context.window_manager.rigtools_data_issues)

	def execute(self, context):
		fixes = [(i.fix_id, json.loads(i.fix_args_json)) for i in context.window_manager.rigtools_data_issues if i.fix_id]
		for fix_id, fix_args in fixes:
			apply_fix(context.object, fix_id, fix_args)
		store_issues(context)
		self.report({'INFO'}, f"Applied {len(fixes)} fix{'es' if len(fixes) != 1 else ''}")
		return {'FINISHED'}

class RIG_UL_data_viewer_assemblies(bpy.types.UIList):
	def draw_item(self, context, layout, data, item, icon_value, active_data, active_propname, index):
		row = layout.row(align=True)
		item_icon = template_icon(item)
		row.label(text=item.name, icon=item_icon)
		sub = row.row()
		sub.alignment = 'RIGHT'
		# Without a template icon, the type is the next most useful thing to show
		sub.label(text=item.template_name if item_icon != 'NONE' else f"{TYPE_LABELS[item.assembly_type]}  ·  {item.template_name}")
		if item.uid in flagged_uids(context.window_manager):
			sub.label(text="", icon=icon('STATUS_WARNING_FILLED'))

class RIG_PT_data_viewer(bpy.types.Panel):
	bl_label = "RigTools"
	bl_idname = "RIG_PT_data_viewer"
	bl_space_type = 'PROPERTIES'
	bl_region_type = 'WINDOW'
	bl_context = 'data'
	bl_options = {'DEFAULT_CLOSED'}

	@classmethod
	def poll(cls, context):
		return context.object and context.object.type == 'ARMATURE'

	def draw(self, context):
		layout = self.layout
		armature_data = context.object.data
		settings = armature_data.rigtools
		layout.label(text=f"Rig data version {settings.rig_data_version}")
		if needs_rig_upgrade(armature_data):
			row = layout.row()
			row.alert = True
			row.operator(
				"rig.upgrade_rig",
				text=f"Upgrade Rig (v{settings.rig_data_version} -> v{CURRENT_RIG_DATA_VERSION})",
				icon='FILE_REFRESH',
			)

class RIG_PT_data_viewer_assemblies(bpy.types.Panel):
	bl_label = "Assemblies"
	bl_idname = "RIG_PT_data_viewer_assemblies"
	bl_space_type = 'PROPERTIES'
	bl_region_type = 'WINDOW'
	bl_context = 'data'
	bl_parent_id = "RIG_PT_data_viewer"

	def draw(self, context):
		layout = self.layout
		obj = context.object
		wm = context.window_manager
		assemblies = obj.data.rigtools_assemblies

		layout.template_list(
			"RIG_UL_data_viewer_assemblies", "",
			obj.data, "rigtools_assemblies",
			wm, "rigtools_data_assembly_index",
			rows=6,
		)

		index = wm.rigtools_data_assembly_index
		if not 0 <= index < len(assemblies):
			return
		assembly = assemblies[index]
		bones = bone_names(obj.data)
		selectable = can_select(context)

		box = layout.box()
		col = box.column(align=True)
		col.label(text=f"{assembly.name}  ·  {TYPE_LABELS[assembly.assembly_type]} {assembly.template_name}", icon=template_icon(assembly))
		if assembly.side:
			col.label(text=f"Side: {side_display_name(assembly.side) or assembly.side}")
		if assembly.ui_label:
			col.label(text=f"Rig UI label: {assembly.ui_label}")

		row = box.row(align=True)
		sub = row.row(align=True)
		sub.enabled = selectable
		op = sub.operator(RIG_OT_data_select.bl_idname, text="Select Bones", icon='RESTRICT_SELECT_OFF')
		op.bone_names_json = json.dumps(assembly.get_chain() + [b.name for b in assembly.mechanism_bones])
		op = sub.operator(ASSEMBLY_TYPE_OPERATORS[assembly.assembly_type], text="Reconfigure", icon='SETTINGS')
		op.assembly_uid = assembly.uid
		op = sub.operator("rig.delete_assembly", text="Delete", icon='TRASH')
		op.assembly_uid = assembly.uid

		sections = wm.rigtools_data_sections
		drawers = {
			"org": lambda c: [self._bone_row(c, s.name, bones, selectable, self._parent_text(s)) for s in assembly.org_states],
			"twist": lambda c: [self._bone_row(c, s.name, bones, selectable, self._parent_text(s)) for s in assembly.twist_states],
			"mechanism": lambda c: self._draw_mechanism(c, assembly, bones, selectable),
			"properties": lambda c: self._draw_properties(c, obj, assembly),
			"objects": lambda c: [self._row(c, o.name, 'OBJECT_DATA', o.name in bpy.data.objects) for o in assembly.objects],
			"reparent": lambda c: [self._row(c, f"{r.from_bone} → {r.to_bone}", 'CON_CHILDOF', r.from_bone in bones and r.to_bone in bones) for r in assembly.reparent_rules],
			"ik_parents": lambda c: [self._row(c, f"{p.label} → {p.bone}", 'CON_ARMATURE', not p.bone or p.bone in bones) for p in assembly.ik_parents],
			"options": lambda c: self._draw_options(c, assembly),
		}
		counts = {
			"org": len(assembly.org_states),
			"twist": len(assembly.twist_states),
			"mechanism": len(assembly.mechanism_bones),
			"properties": len(assembly.properties),
			"objects": len(assembly.objects),
			"reparent": len(assembly.reparent_rules),
			"ik_parents": len(assembly.ik_parents),
			"options": None,
		}
		for key, label in SECTIONS:
			count = counts[key]
			if count == 0:
				continue
			box = layout.box()
			is_open = getattr(sections, key)
			header = box.row()
			header.alignment = 'LEFT'
			header.prop(
				sections, key,
				text=label if count is None else f"{label} ({count})",
				icon='DISCLOSURE_TRI_DOWN' if is_open else 'DISCLOSURE_TRI_RIGHT',
				emboss=False,
			)
			if is_open:
				drawers[key](box.column(align=True))

	@staticmethod
	def _parent_text(state):
		if not state.parent:
			return "no parent"
		return f"{'connected to' if state.use_connect else 'parent'} {state.parent}"

	@staticmethod
	def _split(col, exists, extra):
		# Left-aligned rows so names line up instead of centering in emboss-less buttons
		row = col.row(align=True)
		row.alert = not exists
		if extra:
			split = row.split(factor=0.6, align=True)
			left = split.row(align=True)
			right = split.row(align=True)
			right.alignment = 'LEFT'
			right.label(text=extra)
		else:
			left = row.row(align=True)
		left.alignment = 'LEFT'
		return left

	def _row(self, col, text, row_icon, exists, extra=""):
		self._split(col, exists, extra).label(text=text, icon=row_icon)

	def _bone_row(self, col, name, bones, selectable, extra=""):
		exists = name in bones
		left = self._split(col, exists, extra)
		if exists and selectable:
			op = left.operator(RIG_OT_data_select.bl_idname, text=name, icon='BONE_DATA', emboss=False)
			op.bone_names_json = json.dumps([name])
		else:
			left.label(text=name, icon='BONE_DATA')

	def _draw_mechanism(self, col, assembly, bones, selectable):
		groups = {}
		for ref in assembly.mechanism_bones:
			roles = ", ".join(r.name for r in ref.roles) or "no role"
			groups.setdefault(roles, []).append(ref)

		for roles, refs in groups.items():
			header = col.row()
			header.alignment = 'LEFT'
			header.label(text=f"{roles.upper()} ({len(refs)})")
			for ref in refs:
				self._bone_row(col, ref.name, bones, selectable)
				fields = [f"{label}: {value}" for label, value in style_fields(ref.style_json)]
				if ref.palette:
					fields.append(f"Palette: {ref.palette}")
				for line in balanced_lines(fields, STYLE_FIELDS_PER_LINE):
					row = col.row()
					row.active = False
					row.separator(factor=3)
					row.label(text="  ·  ".join(line))
			col.separator()

	def _draw_properties(self, col, obj, assembly):
		prop_bone = get_property_bone(obj)
		for prop in assembly.properties:
			exists = prop_bone is not None and prop.name in prop_bone
			extra = " ".join(p for p in (prop.role, prop.qualifier) if p)
			self._row(col, prop.name, 'PROPERTIES', exists, extra)

	@staticmethod
	def _draw_options(col, assembly):
		try:
			options = assembly.get_options()
		except ValueError:
			row = col.row()
			row.alert = True
			row.label(text="Options can't be read")
			return
		for key in sorted(options):
			value = options[key]
			if key in CONFIG_OPTION_KEYS and value:
				text = f"({len(value)} entries)" if isinstance(value, (list, dict)) else "(set)"
			else:
				text = json.dumps(value)
				if len(text) > 60:
					text = text[:57] + "..."
			split = col.split(factor=0.5)
			left = split.row()
			left.alignment = 'LEFT'
			left.label(text=key)
			right = split.row()
			right.alignment = 'LEFT'
			right.label(text=text)

class RIG_PT_data_viewer_limbs(bpy.types.Panel):
	bl_label = "Limbs"
	bl_idname = "RIG_PT_data_viewer_limbs"
	bl_space_type = 'PROPERTIES'
	bl_region_type = 'WINDOW'
	bl_context = 'data'
	bl_parent_id = "RIG_PT_data_viewer"
	bl_options = {'DEFAULT_CLOSED'}

	def draw(self, context):
		layout = self.layout
		armature_data = context.object.data
		rows = armature_data.rigtools_limb_collections
		if not rows:
			layout.label(text="No limbs")
			return

		limbs = assemblies_by_limb(armature_data)
		collections = collection_names(armature_data)

		for row in rows:
			assemblies = limbs.get((row.limb, row.side), [])
			box = layout.box()
			col = box.column(align=True)

			header = col.row(align=True)
			header.alert = not assemblies
			header.label(text=limb_label(row), icon='OUTLINER_COLLECTION')
			if row.split:
				sub = header.row()
				sub.active = False
				sub.label(text="FK/IK split")
			sub = header.row(align=True)
			sub.enabled = bool(assemblies) and can_select(context)
			op = sub.operator(RIG_OT_data_select.bl_idname, text="", icon='RESTRICT_SELECT_OFF')
			# Same bones as Select Similar, so Reconfigure All Selected picks these assemblies up
			op.bone_names_json = json.dumps([name for a in assemblies for role in SELECT_SIMILAR_ROLES for name in a.get_bones_by_role(role)])
			op = header.operator("rig.rename_limb_collections", text="", icon='GREASEPENCIL')
			op.limb = row.limb
			op.side = row.side

			used_by = ", ".join(a.name for a in assemblies) or "no assemblies"
			sub = col.row()
			sub.active = False
			sub.label(text=f"Used by: {used_by}")

			col.separator(factor=0.5)
			for role in LIMB_COLLECTION_ROLES:
				name = getattr(row, role)
				if not name:
					continue
				bone_count = sum(len(a.get_bones_by_role(role)) for a in assemblies)
				split = col.split(factor=0.25)
				split.label(text=role.upper())
				right = split.row()
				if name in collections:
					right.label(text=f"{name}  ({bone_count} bones)")
				elif bone_count:
					right.alert = True
					right.label(text=f"{name}  (missing, {bone_count} bones)")
				else:
					# Reserved name; the collection is created when a bone first uses it
					right.active = False
					right.label(text=f"{name}  (not created)")

class RIG_PT_data_viewer_check(bpy.types.Panel):
	bl_label = "Data Check"
	bl_idname = "RIG_PT_data_viewer_check"
	bl_space_type = 'PROPERTIES'
	bl_region_type = 'WINDOW'
	bl_context = 'data'
	bl_parent_id = "RIG_PT_data_viewer"

	def draw(self, context):
		layout = self.layout
		wm = context.window_manager
		obj = context.object

		row = layout.row(align=True)
		row.operator(RIG_OT_data_check.bl_idname, icon='VIEWZOOM')
		row.operator(RIG_OT_data_fix_all.bl_idname, icon='MODIFIER')

		if wm.rigtools_data_checked != obj.name:
			layout.label(text="Not checked yet", icon=icon('STATUS_INFO'))
			return

		issues = wm.rigtools_data_issues
		if not issues:
			layout.label(text="No issues found", icon='CHECKMARK')
			return

		col = layout.column(align=True)
		for i, issue in enumerate(issues):
			row = col.row(align=True)
			row.label(text=issue.message, icon=icon(SEVERITY_ICONS.get(issue.severity, 'STATUS_INFO')))
			if issue.assembly_uid or issue.bone:
				op = row.operator(RIG_OT_data_select.bl_idname, text="", icon='RESTRICT_SELECT_OFF')
				op.assembly_uid = issue.assembly_uid
				op.bone_names_json = json.dumps([issue.bone] if issue.bone else [])
			if issue.fix_id:
				op = row.operator(RIG_OT_data_fix_issue.bl_idname, text="", icon='MODIFIER')
				op.index = i

class RIG_OT_clear_unused_widgets(bpy.types.Operator):
	bl_idname = "rig.clear_unused_widgets"
	bl_label = "Clear Unused Widgets"
	bl_description = "Delete RigTools widgets that no bone uses. Your own objects are never deleted"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(cls, context):
		return bool(unused_standard_widgets())

	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self, confirm_text="Delete")

	def draw(self, context):
		widgets = sorted(wgt.name for wgt in unused_standard_widgets())
		col = self.layout.column(align=True)
		col.label(text=f"Delete {len(widgets)} unused widget{'s' if len(widgets) != 1 else ''}:")
		for name in widgets[:LISTED_WIDGETS_MAX]:
			col.label(text=name, icon='OBJECT_DATA')
		if len(widgets) > LISTED_WIDGETS_MAX:
			col.label(text=f"...and {len(widgets) - LISTED_WIDGETS_MAX} more")

	def execute(self, context):
		widgets = unused_standard_widgets()
		for wgt in widgets:
			remove_widget(wgt)
		self.report({'INFO'}, f"Deleted {len(widgets)} unused widget{'s' if len(widgets) != 1 else ''}")
		return {'FINISHED'}

class RIG_PT_data_viewer_widgets(bpy.types.Panel):
	bl_label = "Widgets"
	bl_idname = "RIG_PT_data_viewer_widgets"
	bl_space_type = 'PROPERTIES'
	bl_region_type = 'WINDOW'
	bl_context = 'data'
	bl_parent_id = "RIG_PT_data_viewer"

	def draw(self, context):
		layout = self.layout
		count = len(unused_standard_widgets())
		if count:
			layout.label(text=f"{count} unused widget{'s' if count != 1 else ''}", icon=icon('STATUS_INFO'))
		else:
			layout.label(text="No unused widgets", icon='CHECKMARK')
		layout.operator(RIG_OT_clear_unused_widgets.bl_idname, icon='TRASH')

classes = (
	RigDataIssue,
	RigDataSections,
	RIG_OT_data_select,
	RIG_OT_data_check,
	RIG_OT_data_fix_issue,
	RIG_OT_data_fix_all,
	RIG_OT_clear_unused_widgets,
	RIG_UL_data_viewer_assemblies,
	RIG_PT_data_viewer,
	RIG_PT_data_viewer_assemblies,
	RIG_PT_data_viewer_limbs,
	RIG_PT_data_viewer_check,
	RIG_PT_data_viewer_widgets,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	wm = bpy.types.WindowManager
	wm.rigtools_data_issues = CollectionProperty(type=RigDataIssue)
	wm.rigtools_data_checked = StringProperty()
	wm.rigtools_data_assembly_index = IntProperty()
	wm.rigtools_data_sections = PointerProperty(type=RigDataSections)

def unregister():
	wm = bpy.types.WindowManager
	del wm.rigtools_data_sections
	del wm.rigtools_data_assembly_index
	del wm.rigtools_data_checked
	del wm.rigtools_data_issues
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
