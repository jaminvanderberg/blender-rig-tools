import bpy
from bpy.props import BoolProperty, StringProperty, EnumProperty, CollectionProperty

from rigtools.rig_ui import rig_ui
from rigtools.rig_ui.rig_ui import _coll_by_name, _hidden_map, _is_hidden, _iter_rows, draw_collections_view


class RigUICollectionLayoutItem(bpy.types.PropertyGroup):
	collection_name: StringProperty()
	is_gap: BoolProperty(default=False)
	same_row: BoolProperty(default=False)
	hidden: BoolProperty(default=False)

def rename_layout_collection(armature_data, old_name, new_name):
	if not old_name or old_name == new_name:
		return
	layout = armature_data.rig_ui_layout
	new_already_exists = any(
		not item.is_gap and item.collection_name == new_name
		for item in layout
	)
	for i in range(len(layout) - 1, -1, -1):
		item = layout[i]
		if item.is_gap or item.collection_name != old_name:
			continue
		if new_already_exists:
			layout.remove(i)
		else:
			item.collection_name = new_name

def _cleanup_rows(rows):
	rows[:] = [row for row in rows if row['type'] == 'gap' or row['colls']]

def _apply_rows(armature_data, rows):
	hidden = _hidden_map(armature_data)
	_cleanup_rows(rows)
	layout = armature_data.rig_ui_layout
	layout.clear()
	for row in rows:
		if row['type'] == 'gap':
			item = layout.add()
			item.is_gap = True
			continue
		for i, coll in enumerate(row['colls']):
			item = layout.add()
			item.collection_name = coll.name
			item.same_row = i > 0
			item.hidden = hidden.get(coll.name, False)

def _find_collection_row(rows, name):
	for i, row in enumerate(rows):
		if row['type'] != 'items':
			continue
		for j, coll in enumerate(row['colls']):
			if coll.name == name:
				return i, j, coll
	return -1, -1, None

def _find_gap_before(rows, owner_name):
	if owner_name:
		for i, row in enumerate(rows):
			if row['type'] != 'gap':
				continue
			if i + 1 < len(rows) and rows[i + 1]['type'] == 'items':
				if rows[i + 1]['colls'][0].name == owner_name:
					return i
		return -1
	if rows and rows[-1]['type'] == 'gap':
		return len(rows) - 1
	return -1

def _gap_owner_name(rows, gap_i):
	for row in rows[gap_i + 1:]:
		if row['type'] == 'items' and row['colls']:
			return row['colls'][0].name
	return ""

def _move_horizontal(rows, name, direction):
	row_i, col_i, _ = _find_collection_row(rows, name)
	if row_i < 0:
		return False
	new_i = col_i - 1 if direction == 'LEFT' else col_i + 1
	colls = rows[row_i]['colls']
	if new_i < 0 or new_i >= len(colls):
		return False
	colls[col_i], colls[new_i] = colls[new_i], colls[col_i]
	return True

def _join_row(rows, name, direction):
	src_i, src_j, coll = _find_collection_row(rows, name)
	if src_i < 0:
		return False

	if direction == 'UP':
		prev = rows[src_i - 1] if src_i > 0 else None
		if prev is not None and prev['type'] == 'items':
			rows[src_i]['colls'].pop(src_j)
			if not rows[src_i]['colls']:
				rows.pop(src_i)
			prev['colls'].append(coll)
			return True
		return _full_row(rows, name, 'UP')

	nxt = rows[src_i + 1] if src_i + 1 < len(rows) else None
	if nxt is not None and nxt['type'] == 'items':
		rows[src_i]['colls'].pop(src_j)
		if not rows[src_i]['colls']:
			rows.pop(src_i)
			nxt = rows[src_i]
		nxt['colls'].insert(0, coll)
		return True
	return _full_row(rows, name, 'DOWN')

def _full_row(rows, name, direction):
	src_i, src_j, coll = _find_collection_row(rows, name)
	if src_i < 0:
		return False
	if len(rows[src_i]['colls']) == 1:
		swap = src_i - 1 if direction == 'UP' else src_i + 1
		if swap < 0 or swap >= len(rows):
			return False
		rows[src_i], rows[swap] = rows[swap], rows[src_i]
		return True
	rows[src_i]['colls'].pop(src_j)
	new_row = {'type': 'items', 'colls': [coll]}
	if direction == 'UP':
		rows.insert(src_i, new_row)
	else:
		rows.insert(src_i + 1, new_row)
	return True

def _move_gap(rows, owner_name, direction):
	gap_i = _find_gap_before(rows, owner_name)
	if gap_i < 0:
		return -1
	swap = gap_i - 1 if direction == 'UP' else gap_i + 1
	if swap < 0 or swap >= len(rows):
		return -1
	rows[gap_i], rows[swap] = rows[swap], rows[gap_i]
	return swap

def _edit_selection(context):
	obj = context.object
	if not obj or obj.type != 'ARMATURE':
		return None, False, None
	wm = context.window_manager
	name = wm.rig_ui_sel_name
	is_gap = bool(wm.rig_ui_sel_gap)
	if is_gap:
		return _coll_by_name(obj.data, name), True, name
	if not name:
		return None, False, None
	coll = _coll_by_name(obj.data, name)
	if coll is None:
		return None, False, None
	return coll, False, name

def _set_selection(context, name, is_gap):
	wm = context.window_manager
	wm.rig_ui_sel_name = name
	wm.rig_ui_sel_gap = is_gap
	if not is_gap:
		coll = _coll_by_name(context.object.data, name)
		if coll is not None:
			context.object.data.collections.active = coll

class RIG_OT_ui_select_collection(bpy.types.Operator):
	bl_idname = "rig.ui_select_collection"
	bl_label = "Select Collection"
	bl_description = "Select this collection or gap for layout editing"
	bl_options = {'INTERNAL'}

	collection_name: StringProperty()
	is_gap: BoolProperty(default=False)

	def execute(self, context):
		if not self.is_gap and _coll_by_name(context.object.data, self.collection_name) is None:
			self.report({'ERROR'}, f"Collection '{self.collection_name}' not found.")
			return {'CANCELLED'}
		_set_selection(context, self.collection_name, self.is_gap)
		return {'FINISHED'}

class RIG_OT_ui_collection_move(bpy.types.Operator):
	bl_idname = "rig.ui_collection_move"
	bl_label = "Move Collection"
	bl_description = "Move the selection to another row"
	bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

	direction: EnumProperty(
		items=(
			('JOIN_UP', "Join Up", "Join the row above"),
			('JOIN_DOWN', "Join Down", "Join the row below"),
			('ROW_UP', "Row Up", "Move to its own row above"),
			('ROW_DOWN', "Row Down", "Move to its own row below"),
		),
	)

	@classmethod
	def poll(cls, context):
		if not context.window_manager.rig_ui_edit_collections:
			return False
		coll, is_gap, name = _edit_selection(context)
		if is_gap:
			return True
		return coll is not None

	def execute(self, context):
		armature_data = context.object.data
		coll, is_gap, name = _edit_selection(context)
		rows = _iter_rows(armature_data)
		is_up = self.direction in {'JOIN_UP', 'ROW_UP'}
		vert = 'UP' if is_up else 'DOWN'

		if is_gap:
			if self.direction in {'JOIN_UP', 'JOIN_DOWN'}:
				return {'CANCELLED'}
			new_gap_i = _move_gap(rows, name, vert)
			if new_gap_i < 0:
				return {'CANCELLED'}
			_apply_rows(armature_data, rows)
			_set_selection(context, _gap_owner_name(rows, new_gap_i), True)
			return {'FINISHED'}

		if self.direction in {'JOIN_UP', 'JOIN_DOWN'}:
			ok = _join_row(rows, name, vert)
		else:
			ok = _full_row(rows, name, vert)
		if not ok:
			return {'CANCELLED'}
		_apply_rows(armature_data, rows)
		_set_selection(context, name, False)
		return {'FINISHED'}

class RIG_OT_ui_collection_shift(bpy.types.Operator):
	bl_idname = "rig.ui_collection_shift"
	bl_label = "Shift Collection"
	bl_description = "Move this collection within its row"
	bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

	collection_name: StringProperty()
	direction: EnumProperty(
		items=(
			('LEFT', "Left", ""),
			('RIGHT', "Right", ""),
		),
	)

	@classmethod
	def poll(cls, context):
		obj = context.object
		return obj and obj.type == 'ARMATURE' and context.window_manager.rig_ui_edit_collections

	def execute(self, context):
		armature_data = context.object.data
		rows = _iter_rows(armature_data)
		if not _move_horizontal(rows, self.collection_name, self.direction):
			return {'CANCELLED'}
		_apply_rows(armature_data, rows)
		_set_selection(context, self.collection_name, False)
		return {'FINISHED'}

class RIG_OT_ui_collection_add_gap(bpy.types.Operator):
	bl_idname = "rig.ui_collection_add_gap"
	bl_label = "Add Gap"
	bl_description = "Insert an empty row above the selection"
	bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

	@classmethod
	def poll(cls, context):
		coll, is_gap, _ = _edit_selection(context)
		return context.window_manager.rig_ui_edit_collections and (coll is not None or is_gap)

	def execute(self, context):
		armature_data = context.object.data
		_, is_gap, name = _edit_selection(context)
		rows = _iter_rows(armature_data)

		if is_gap:
			gap_i = _find_gap_before(rows, name)
			if gap_i < 0:
				return {'CANCELLED'}
			rows.insert(gap_i, {'type': 'gap'})
		else:
			row_i, _, _ = _find_collection_row(rows, name)
			if row_i < 0:
				return {'CANCELLED'}
			rows.insert(row_i, {'type': 'gap'})

		_apply_rows(armature_data, rows)
		_set_selection(context, name, is_gap)
		return {'FINISHED'}

class RIG_OT_ui_collection_remove_gap(bpy.types.Operator):
	bl_idname = "rig.ui_collection_remove_gap"
	bl_label = "Remove Gap"
	bl_description = "Remove the selected gap"
	bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

	@classmethod
	def poll(cls, context):
		_, is_gap, _ = _edit_selection(context)
		return context.window_manager.rig_ui_edit_collections and is_gap

	def execute(self, context):
		armature_data = context.object.data
		_, is_gap, name = _edit_selection(context)
		rows = _iter_rows(armature_data)
		gap_i = _find_gap_before(rows, name)
		if gap_i < 0:
			return {'CANCELLED'}
		rows.pop(gap_i)
		_apply_rows(armature_data, rows)
		_set_selection(context, name, False)
		return {'FINISHED'}

class RIG_OT_ui_collection_hide(bpy.types.Operator):
	bl_idname = "rig.ui_collection_hide"
	bl_label = "Hide From Rig UI"
	bl_description = "Hide or show this collection in the normal Rig UI"
	bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

	@classmethod
	def poll(cls, context):
		coll, is_gap, _ = _edit_selection(context)
		return context.window_manager.rig_ui_edit_collections and coll is not None and not is_gap

	def execute(self, context):
		armature_data = context.object.data
		_, _, name = _edit_selection(context)
		_apply_rows(armature_data, _iter_rows(armature_data))
		for item in armature_data.rig_ui_layout:
			if not item.is_gap and item.collection_name == name:
				item.hidden = not item.hidden
				break
		_set_selection(context, name, False)
		return {'FINISHED'}

class RIG_OT_ui_collection_rename(bpy.types.Operator):
	bl_idname = "rig.ui_collection_rename"
	bl_label = "Rename Collection"
	bl_description = "Rename the selected collection and update any limb collections that reference it"
	bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

	collection_name: StringProperty()
	new_name: StringProperty(name="Name")

	@classmethod
	def poll(cls, context):
		coll, is_gap, _ = _edit_selection(context)
		return context.window_manager.rig_ui_edit_collections and coll is not None and not is_gap

	def invoke(self, context, event):
		_, _, name = _edit_selection(context)
		self.collection_name = name
		self.new_name = name
		return context.window_manager.invoke_props_dialog(self, width=250)

	def draw(self, context):
		self.layout.prop(self, "new_name")

	def execute(self, context):
		armature_data = context.object.data
		old_name = self.collection_name
		new_name = self.new_name.strip()

		if not new_name:
			self.report({'ERROR'}, "Name cannot be empty")
			return {'CANCELLED'}

		coll = _coll_by_name(armature_data, old_name)
		if coll is None:
			self.report({'ERROR'}, f"Collection '{old_name}' not found.")
			return {'CANCELLED'}

		if new_name == old_name:
			return {'FINISHED'}

		existing = _coll_by_name(armature_data, new_name)

		for row in armature_data.rigtools_limb_collections:
			for role in ("fk", "ik", "tweak", "mch", "master", "control"):
				if getattr(row, role) == old_name:
					setattr(row, role, new_name)

		rename_layout_collection(armature_data, old_name, new_name)

		if existing is not None:
			_merge_collection(context, armature_data, coll, existing)
			_set_selection(context, new_name, False)
			self.report({'INFO'}, f"Merged collection '{old_name}' into '{new_name}'")
			return {'FINISHED'}

		coll.name = new_name
		_set_selection(context, new_name, False)

		self.report({'INFO'}, f"Renamed collection '{old_name}' to '{new_name}'")
		return {'FINISHED'}

def _merge_collection(context, armature_data, src, dst):
	# Bone membership isn't synced to coll.bones in edit mode, so read edit bones there
	if context.mode == 'EDIT_ARMATURE':
		bones = [eb for eb in armature_data.edit_bones if src.name in eb.collections]
	else:
		bones = list(src.bones)
	for bone in bones:
		dst.assign(bone)
	for child in list(src.children):
		if child != dst:
			child.parent = dst
	armature_data.collections.remove(src)

class RIG_MT_ui_collection_actions(bpy.types.Menu):
	bl_idname = "RIG_MT_ui_collection_actions"
	bl_label = "Collection Actions"

	def draw(self, context):
		layout = self.layout
		layout.operator("rig.ui_collection_rename", text="Rename", icon='GREASEPENCIL')
		_, _, name = _edit_selection(context)
		hidden = _is_hidden(context.object.data, name) if name else False
		layout.operator(
			"rig.ui_collection_hide",
			text="Show" if hidden else "Hide",
			icon='HIDE_ON' if hidden else 'HIDE_OFF',
		)

###############################################################################
# Panel Hooks
 
def draw_collection_editing(panel, context, armature_data):	
	wm = context.window_manager

	if not wm.rig_ui_edit_collections:
		# Show the standard view with the edit button at the bottom
		draw_collections_view(panel.layout.column(align=True), armature_data)
		row = panel.layout.row(align=True)
		row.alignment = 'RIGHT'
		row.prop(wm, "rig_ui_edit_collections", text="Edit", icon='SETTINGS', toggle=True)
		return True
	
	_draw_edit_buttons(context, panel.layout)
	_draw_edit(
		panel.layout.column(align=True), 
		armature_data,
		wm.rig_ui_sel_name,
		wm.rig_ui_sel_gap
	)
	_draw_edit_buttons(context, panel.layout)
	return True

def _draw_edit_buttons(context, layout):
	wm = context.window_manager

	col = layout.column()
	header = col.row(align=True)
	header.operator("rig.ui_collection_add_gap", text="Gap")
	header.separator()
	header.operator("rig.ui_collection_move", text="", icon='TRIA_UP_BAR').direction = 'ROW_UP'
	header.operator("rig.ui_collection_move", text="", icon='TRIA_UP', emboss=False).direction = 'JOIN_UP'
	header.operator("rig.ui_collection_move", text="", icon='TRIA_DOWN', emboss=False).direction = 'JOIN_DOWN'
	header.operator("rig.ui_collection_move", text="", icon='TRIA_DOWN_BAR').direction = 'ROW_DOWN'
	header.separator()
	header.prop(wm, "rig_ui_edit_collections", text="Edit", icon='SETTINGS', toggle=True)

def _draw_edit(col, armature_data, sel_name, sel_gap):
	rows = _iter_rows(armature_data)
	for i, row in enumerate(rows):
		if row['type'] == 'gap':
			owner = _gap_owner_name(rows, i)
			ui_row = col.row(align=True)
			op = ui_row.operator(
				"rig.ui_select_collection",
				text="────",
				depress=(sel_gap and owner == sel_name),
			)
			op.collection_name = owner
			op.is_gap = True
			if sel_gap and owner == sel_name:
				ui_row.operator("rig.ui_collection_remove_gap", text="", icon='X')
			continue
		ui_row = col.row(align=True)
		count = len(row['colls'])
		for j, coll in enumerate(row['colls']):
			hidden = _is_hidden(armature_data, coll.name)
			selected = not sel_gap and coll.name == sel_name
			if count > 1 and j > 0 and selected:
				shift = ui_row.operator("rig.ui_collection_shift", text="", icon='TRIA_LEFT')
				shift.collection_name = coll.name
				shift.direction = 'LEFT'
			btn = ui_row.row(align=True)
			btn.active = not hidden
			op = btn.operator(
				"rig.ui_select_collection",
				text=coll.name,
				depress=selected,
			)
			op.collection_name = coll.name
			op.is_gap = False
			if selected:
				menu_cell = ui_row.row(align=True)
				menu_cell.emboss = 'NONE'
				menu_cell.menu("RIG_MT_ui_collection_actions", text="", icon='DOWNARROW_HLT')
			if count > 1 and j < count - 1 and selected:
				shift = ui_row.operator("rig.ui_collection_shift", text="", icon='TRIA_RIGHT')
				shift.collection_name = coll.name
				shift.direction = 'RIGHT'


classes = (
	RigUICollectionLayoutItem,
	RIG_OT_ui_select_collection,
	RIG_OT_ui_collection_move,
	RIG_OT_ui_collection_shift,
	RIG_OT_ui_collection_add_gap,
	RIG_OT_ui_collection_remove_gap,
	RIG_OT_ui_collection_hide,
	RIG_OT_ui_collection_rename,
	RIG_MT_ui_collection_actions,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	bpy.types.Armature.rig_ui_layout = CollectionProperty(type=RigUICollectionLayoutItem)
	bpy.types.WindowManager.rig_ui_edit_collections = BoolProperty(
		name="Edit",
		description="Rearrange collection buttons instead of toggling visibility",
		default=False,
	)
	bpy.types.WindowManager.rig_ui_sel_name = StringProperty(default="")
	bpy.types.WindowManager.rig_ui_sel_gap = BoolProperty(default=False)

	rig_ui.RIG_PT_collection_ui.edit_hook = draw_collection_editing

def unregister():
	rig_ui.RIG_PT_collection_ui.edit_hook = None
	del bpy.types.WindowManager.rig_ui_sel_gap
	del bpy.types.WindowManager.rig_ui_sel_name
	del bpy.types.WindowManager.rig_ui_edit_collections
	del bpy.types.Armature.rig_ui_layout
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
