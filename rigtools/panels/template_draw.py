from dataclasses import dataclass

@dataclass
class SplitSection:
	label: str
	prop: str
	icon: str = "NONE"

class TemplateDraw:
	def __init__(self, op, template, *, split_size=0.6, visible_func=None):
		self.op = op
		self.template = template
		self.split_size = split_size
		self.visible_func = visible_func
		self._prev = False

	def is_allowed(self, field_name):
		if not self.template:
			return True
		return field_name in self.template.redo_fields

	def do_show(self, field_name):
		if not self.is_allowed(field_name):
			return False
		if self.visible_func and not self.visible_func(field_name):
			return False
		return True

	def do_show_any(self, field_names):
		return any(self.do_show(field_name) for field_name in field_names)

	def split_field(self, layout, label, prop):
		if not self.do_show(prop):
			return
		split = layout.split(align=True, factor=self.split_size)
		row = split.row(align=True)
		row.label(text=label, translate=False)
		row = split.row(align=True)
		row.prop(self.op, prop, text="")
		
	def full_field(self, layout, label, prop):
		if not self.do_show(prop):
			return
		layout.prop(self.op, prop, text=label)

	def split_row(self, layout, sections: list[SplitSection]):
		if not self.do_show_any([section.prop for section in sections]):
			return
		row = layout.row(align=True)
		for section in sections:
			row.prop(self.op, section.prop, text=section.label, icon=section.icon)
		
	def draw_section(self, layout, fields, draw_func):
		if not self.do_show_any(fields):
			return
		if self._prev:
			layout.separator()
		draw_func()
		self._prev = True

	def box_section(self, layout, fields, label, icon, draw_func):
		if not self.do_show_any(fields):
			return
		box = layout.box()
		box.label(text=label, icon=icon)
		col = box.column()
		self._prev = False
		draw_func(col)
