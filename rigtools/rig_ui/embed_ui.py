import ast
import bpy
from rigtools.rig_ui import rig_ui

TEXT_NAME = "rigtools_ui.py"

class RIG_OT_embed_ui(bpy.types.Operator):
	"""Embed the RigTools UI script in this file so animators don't need RigTools"""
	bl_idname = "rig.embed_ui"
	bl_label = "Embed Animator UI"
	bl_options = {'REGISTER', 'UNDO'}
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self, width=360)

	def draw(self, context):
		state, version = embed_state(context.object.data)
		col = self.layout.column(align=True)
		if state == 'OUTDATED':
			latest = _version_label(rig_ui.bl_info["version"])
			col.label(text=f"Replaces the embedded Animator UI script (v{_version_label(version)})")
			col.label(text=f"with the current version (v{latest}).")
		else:
			col.label(text="Adds an auto-run script to this file that shows the Rig UI,")
			col.label(text="Rig Properties and Visibility panels without RigTools.")
		col.separator()
		col.label(text="Animators must allow Python scripts when opening the file.")
		col.label(text="Not needed if animators install the RigTools UI add-on.")

	def execute(self, context):
		with open(rig_ui.__file__, encoding="utf-8") as f:
			source = f.read()
		text = bpy.data.texts.get(TEXT_NAME) or bpy.data.texts.new(TEXT_NAME)
		text.from_string(source)
		text.use_module = True # the "Register" checkbox
		context.object.data.rigtools.ui_script = text
		self.report({'INFO'}, f"Embedded {TEXT_NAME}. Animators must allow scripts when opening the file.")
		return {'FINISHED'}

def embedded_version(text):
	"""bl_info version of an embedded rig_ui text, read without running it."""
	for node in ast.parse(text.as_string()).body:
		if isinstance(node, ast.Assign) and node.targets[0].id == "bl_info":
			return ast.literal_eval(node.value)["version"]
	raise ValueError(f"{text.name} has no bl_info")

def embed_state(armature_data):
	"""Returns ('MISSING' | 'OUTDATED' | 'CURRENT', embedded version or None)."""
	text = armature_data.rigtools.ui_script
	if text is None:
		return 'MISSING', None
	version = embedded_version(text)
	if version < rig_ui.bl_info["version"]:
		return 'OUTDATED', version
	return 'CURRENT', version

def _version_label(version):
	return ".".join(str(v) for v in version)

def draw_embed_button(layout, armature_data):
	state, version = embed_state(armature_data)
	row = layout.row()
	if state == 'MISSING':
		row.operator("rig.embed_ui", text="Embed Animator UI...", icon='TEXT')
	elif state == 'OUTDATED':
		row.alert = True
		latest = _version_label(rig_ui.bl_info["version"])
		row.operator("rig.embed_ui", text=f"Update Animator UI (v{_version_label(version)} > v{latest})...", icon='FILE_REFRESH')
	else:
		row.enabled = False
		row.operator("rig.embed_ui", text=f"Animator UI Embedded (v{_version_label(version)})", icon='CHECKMARK')

classes = (
	RIG_OT_embed_ui,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
