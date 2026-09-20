import bpy
from bpy.props import BoolProperty, StringProperty, EnumProperty, CollectionProperty


class RigUICollectionLayoutItem(bpy.types.PropertyGroup):
	collection_name: StringProperty()
	is_gap: BoolProperty(default=False)
	same_row: BoolProperty(default=False)
	hidden: BoolProperty(default=False)


def _all_collections(arm):
	return list(getattr(arm, "collections_all", arm.collections))


def _coll_by_name(arm, name):
	if not name:
		return None
	colls = getattr(arm, "collections_all", arm.collections)
	if hasattr(colls, "get"):
		return colls.get(name)
	for coll in colls:
		if coll.name == name:
			return coll
	return None


def _iter_rows(arm):
	rows = []
	item_row = None
	seen = set()
	for item in arm.rig_ui_layout:
		if item.is_gap:
			rows.append({'type': 'gap'})
			item_row = None
			continue
		coll = _coll_by_name(arm, item.collection_name)
		if coll is None:
			continue
		seen.add(coll.name)
		if item.same_row and item_row is not None:
			item_row.append(coll)
		else:
			item_row = [coll]
			rows.append({'type': 'items', 'colls': item_row})
	for coll in _all_collections(arm):
		if coll.name not in seen:
			rows.append({'type': 'items', 'colls': [coll]})
	return rows


def _cleanup_rows(rows):
	rows[:] = [row for row in rows if row['type'] == 'gap' or row['colls']]


def _hidden_map(arm):
	return {
		item.collection_name: item.hidden
		for item in arm.rig_ui_layout
		if not item.is_gap
	}


def _is_hidden(arm, name):
	return _hidden_map(arm).get(name, False)


def _apply_rows(arm, rows):
	hidden = _hidden_map(arm)
	_cleanup_rows(rows)
	layout = arm.rig_ui_layout
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
		arm = context.object.data
		coll, is_gap, name = _edit_selection(context)
		rows = _iter_rows(arm)
		is_up = self.direction in {'JOIN_UP', 'ROW_UP'}
		vert = 'UP' if is_up else 'DOWN'

		if is_gap:
			if self.direction in {'JOIN_UP', 'JOIN_DOWN'}:
				return {'CANCELLED'}
			new_gap_i = _move_gap(rows, name, vert)
			if new_gap_i < 0:
				return {'CANCELLED'}
			_apply_rows(arm, rows)
			_set_selection(context, _gap_owner_name(rows, new_gap_i), True)
			return {'FINISHED'}

		if self.direction in {'JOIN_UP', 'JOIN_DOWN'}:
			ok = _join_row(rows, name, vert)
		else:
			ok = _full_row(rows, name, vert)
		if not ok:
			return {'CANCELLED'}
		_apply_rows(arm, rows)
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
		arm = context.object.data
		rows = _iter_rows(arm)
		if not _move_horizontal(rows, self.collection_name, self.direction):
			return {'CANCELLED'}
		_apply_rows(arm, rows)
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
		arm = context.object.data
		_, is_gap, name = _edit_selection(context)
		rows = _iter_rows(arm)

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

		_apply_rows(arm, rows)
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
		arm = context.object.data
		_, is_gap, name = _edit_selection(context)
		rows = _iter_rows(arm)
		gap_i = _find_gap_before(rows, name)
		if gap_i < 0:
			return {'CANCELLED'}
		rows.pop(gap_i)
		_apply_rows(arm, rows)
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
		arm = context.object.data
		_, _, name = _edit_selection(context)
		_apply_rows(arm, _iter_rows(arm))
		for item in arm.rig_ui_layout:
			if not item.is_gap and item.collection_name == name:
				item.hidden = not item.hidden
				break
		_set_selection(context, name, False)
		return {'FINISHED'}


class RIG_PT_collection_ui(bpy.types.Panel):
	bl_label = "Rig UI"
	bl_idname = "RIG_PT_collection_ui"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = "Item"

	@classmethod
	def poll(cls, context):
		if context.object.type == 'ARMATURE':
			return True
		if bool([mod for mod in context.object.modifiers if mod.type == 'ARMATURE']):
			return True
		return False

	def draw(self, context):

		if context.object.type == 'ARMATURE':
			arm = context.object.data
		else:
			arm = [mod for mod in context.object.modifiers if mod.type == 'ARMATURE'][0].object.data
		wm = context.window_manager
		editing = wm.rig_ui_edit_collections
		sel_name = wm.rig_ui_sel_name
		sel_gap = wm.rig_ui_sel_gap

		layout = self.layout
		header = layout.row(align=True)
		if not editing: header.alignment = 'RIGHT'
		header.prop(wm, "rig_ui_edit_collections", text="Edit", icon='SETTINGS', toggle=True)

		if editing:
			header.separator()
			header.operator("rig.ui_collection_move", text="", icon='TRIA_UP_BAR').direction = 'ROW_UP'
			header.operator("rig.ui_collection_move", text="", icon='TRIA_UP', emboss=False).direction = 'JOIN_UP'
			header.operator("rig.ui_collection_move", text="", icon='TRIA_DOWN', emboss=False).direction = 'JOIN_DOWN'
			header.operator("rig.ui_collection_move", text="", icon='TRIA_DOWN_BAR').direction = 'ROW_DOWN'
			header.separator()
			header.operator("rig.ui_collection_add_gap", text="Gap")

		col = layout.column(align=True)

		if editing:
			self._draw_edit(col, arm, sel_name, sel_gap)
		else:
			self._draw_view(col, arm)

	def _draw_view(self, col, arm):
		for row in _iter_rows(arm):
			if row['type'] == 'gap':
				col.separator()
				continue
			visible = [coll for coll in row['colls'] if not _is_hidden(arm, coll.name)]
			if not visible:
				continue
			ui_row = col.row(align=True)
			for coll in visible:
				ui_row.prop(coll, "is_visible", text=coll.name, toggle=True)

	def _draw_edit(self, col, arm, sel_name, sel_gap):
		rows = _iter_rows(arm)
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
				hidden = _is_hidden(arm, coll.name)
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
					ui_row.operator(
						"rig.ui_collection_hide",
						text="",
						icon='HIDE_ON' if hidden else 'HIDE_OFF',
					)
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
	RIG_PT_collection_ui,
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

def unregister():
	del bpy.types.WindowManager.rig_ui_sel_gap
	del bpy.types.WindowManager.rig_ui_sel_name
	del bpy.types.WindowManager.rig_ui_edit_collections
	del bpy.types.Armature.rig_ui_layout
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
