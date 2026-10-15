from dataclasses import dataclass

@dataclass
class SplitSection:
	label: str
	prop: str
	icon: str = "NONE"
	expand: bool = False
	enabled: bool = True

class TemplateDraw:
	def __init__(self, op, template, *, split_size=0.6, visible_func=None, related_fields={}):
		self.op = op
		self.template = template
		self.split_size = split_size
		self.visible_func = visible_func
		self._prev = False
		self.related_fields = related_fields

	def is_allowed(self, field_name):
		if not self.template:
			return True
		if field_name in self.template.redo_fields:
			return True
		related = self.related_fields.get(field_name)
		return bool(related and related in self.template.redo_fields)

	def do_show(self, field_name):
		if not self.is_allowed(field_name):
			return False
		if self.visible_func and not self.visible_func(field_name):
			return False
		return True

	def do_show_any(self, field_names):
		return any(self.do_show(field_name) for field_name in field_names)
	
	def get_field_label(self, field_name, default_label):
		if self.template and field_name in self.template.field_labels:
			return self.template.field_labels[field_name]
		return default_label

	def split_field(self, layout, label, prop, *, expand=False, split_size=0):
		if split_size == 0:
			split_size = self.split_size
			
		if not self.do_show(prop):
			return
		split = layout.split(align=True, factor=split_size)
		row = split.row(align=True)
		row.label(text=self.get_field_label(prop, label), translate=False)
		row = split.row(align=True)
		if expand:
			row.prop(self.op, prop, expand=expand)
		else:
			row.prop(self.op, prop, text="")
		
	def full_field(self, layout, label, prop):
		if not self.do_show(prop):
			return
		layout.prop(self.op, prop, text=label)

	def expand_field(self, layout, prop):
		if not self.do_show(prop):
			return
		row = layout.row(align=True)
		row.prop(self.op, prop, expand=True)

	def split_row(self, layout, sections: list[SplitSection]):
		if not self.do_show_any([section.prop for section in sections]):
			return
		row = layout.row(align=True)
		for section in sections:
			if not self.do_show(section.prop):
				continue
			sub = row.row(align=True)
			sub.enabled = section.enabled
			if section.expand:
				sub.prop(self.op, section.prop, icon=section.icon, expand=True)
			else:
				sub.prop(self.op, section.prop, text=section.label, icon=section.icon)
		
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
		if label:
			box.label(text=label, icon=icon)
		col = box.column()
		self._prev = False
		draw_func(col)
