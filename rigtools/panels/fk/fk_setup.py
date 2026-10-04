import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty, IntProperty

from rigtools.assemblies.delete_assembly import delete_assembly
from rigtools.assemblies.assembly_data import find_assembly, get_assembly_chains
from rigtools.assemblies.fk_assembly import FKAssemblyOptions, create_fk_assembly
from rigtools.assemblies.fk_templates import get_fk_template, validate_fk_templates
from rigtools.assemblies.template_options import resolve_template_options
from rigtools.armature_settings import get_armature_settings
from rigtools.preferences import get_preferences
from rigtools.utils.naming import guess_limb_name
from rigtools.utils.bone_chain import ChainBranchingError, find_chains_from_selection
from rigtools.utils.widget import fk_widget_types


class RIG_OT_advanced_fk_tweak_setup(bpy.types.Operator):
	"""Setup FK/Tweak setup with advanced options"""
	bl_idname = "rig.advanced_fk_setup"
	bl_label = "Generate FK Assembly"
	bl_options = {'REGISTER', 'UNDO'}

	limb_property_base_name: StringProperty(
		name="Limb Property Base Name",
		description="Base name of the property to store the limb. Example: 'arm', 'leg', 'tail', etc.",
		default=""
	)

	do_create_fk: BoolProperty(
		name="Create FK Bones",
		description="Create the FK bone chain. If unchecked, the tweak bones will be parented in a chain.",
		default=True
	)

	fk_bone_template: StringProperty(
		name="FK bone name",
		description="Template using {name} as a placeholder (e.g., 'FK-{name}' or '{name}_FK'). L/R suffixes will be preserved.",
		default="FK-{name}"
	)

	skip_first_tweak: BoolProperty(
		name="Skip First Tweak",
		description="Skip the first tweak bone",
		default=False
	)

	fk_widget: EnumProperty(
		name="FK Widget",
		description="Create widgets for the FK bones",
		items=fk_widget_types,
		default='CIRCLE'
	)

	override_collections: BoolProperty(
		name="Override Bone Collections",
		description="Specify the bone collections for various bone types",
		default=True
	)

	add_rotation_isolation: BoolProperty(
		name="Add Rotation Isolation",
		description="Add rotation isolation to the FK bones.",
		default=False
	)

	create_rotation_follow_setup: BoolProperty(
		name="Create Rotation Follow Setup",
		description="Create a rotation follow setup along the FK chain.",
		default=True
	)

	rotation_follow_skip: IntProperty(
		name="Rotation Follow Skip",
		description="Number of bones to skip before creating a rotation follow setup.",
		default=1,
		min=0,
	)

	rotation_follow_relationship: EnumProperty(
		name="Rotation Follow Relationship",
		description="Type of relationship for the rotation follow setup.",
		items=[
			('COPY_ROTATION', 'Copy Rotation', 'Copy rotation from the master bone'),
			('COPY_TRANSFORMS', 'Copy Transforms', 'Copy transforms from the master bone'),
		],
		default='COPY_ROTATION'
	)

	fk_collection_name: StringProperty(
		name="FK Collection Name",
		description="Name of the collection to store the FK bones, or blank to copy collection from selected bones",
		default=""
	)

	tweak_collection_name: StringProperty(
		name="Tweak Collection Name",
		description="Name of the collection to store the tweak bones, or blank to copy collection from selected bones",
		default=""
	)

	tweak_relationship: EnumProperty(
		name="Tweak Relationship",
		description="Type of relationship for the tweak bones",
		items=[
			('STRETCH_TO', 'Stretch To', 'Stretch the tweak bone to the target bone'),
			('DAMPED_TRACK', 'Damped Track', 'Damped track the tweak bone to the target bone'),
		],
		default='STRETCH_TO'
	)

	assembly_uid: StringProperty(
		name="Assembly UID",
		description="UID of the assembly to use for the FK/Tweak chain",
		default="",
		options={'HIDDEN'}
	)

	template_id: StringProperty(
		name="Template ID",
		description="FK template to apply on invoke",
		default="",
		options={'HIDDEN'}
	)

	template_name: StringProperty(
		name="Template Name",
		description="Name of the template to use for the FK/Tweak chain",
		default="",
		options={'HIDDEN'}
	)

	@classmethod
	def description(cls, context, properties):
		if properties.template_id:
			template = get_fk_template(properties.template_id)
			if template:
				return template.description
		return "Setup FK/Tweak setup with advanced options"

	##################################################################################################
	# invoke

	def _invoke_from_selection(self, context):
		prefs = get_preferences()
		if not self.properties.is_property_set("fk_bone_template"):
			self.fk_bone_template = prefs.fk_template

		try:
			chains = find_chains_from_selection(context)
		except ChainBranchingError as e:
			self.report({'ERROR'}, str(e))
			return {'CANCELLED'}

		if not chains:
			self.report({'ERROR'}, "No chains selected.")
			return {'CANCELLED'}

		self.limb_property_base_name = guess_limb_name(chains[0][0], context)
		self.template_name = "Advanced"

	def _invoke_from_template(self, context):
		template = get_fk_template(self.template_id)
		if not template:
			self.report({'ERROR'}, f"Unknown FK template: '{self.template_id}'")
			return {'CANCELLED'}

		option_values = resolve_template_options(FKAssemblyOptions, template.options)
		for key, value in option_values.items():
			setattr(self, key, value)

		if "fk_bone_template" not in template.options:
			self.fk_bone_template = get_preferences().fk_template

		if not self.limb_property_base_name:
			try:
				chains = find_chains_from_selection(context)
			except ChainBranchingError as error:
				self.report({'ERROR'}, str(error))
				return {'CANCELLED'}

			if not chains:
				self.report({'ERROR'}, "No chains selected.")
				return {'CANCELLED'}

			self.limb_property_base_name = guess_limb_name(chains[0][0], context)

		self.template_name = template.label

	def _invoke_from_assembly(self, context):
		assembly = find_assembly(context.object, self.assembly_uid)
		if not assembly:
			self.report({'ERROR'}, "Assembly not found.")
			return {'CANCELLED'}

		options = assembly.get_options()
		for key, value in options.items():
			setattr(self, key, value)

		self.template_name = assembly.template_name

	def invoke(self, context, event):
		show_dialog = True

		if self.assembly_uid:
			result = self._invoke_from_assembly(context)
		elif self.template_id:
			result = self._invoke_from_template(context)
			template = get_fk_template(self.template_id)
			if template:
				show_dialog = template.show_dialog
		else:
			result = self._invoke_from_selection(context)

		if result == {'CANCELLED'}:
			return result

		if show_dialog:
			return context.window_manager.invoke_props_dialog(self, width=350)
		return self.execute(context)

	##################################################################################################
	# draw

	def do_show_field(self, field_name, template):
		if not template:
			return True
		return field_name in template.redo_fields

	def do_show_any_field(self, field_names, template):
		if not template:
			return True
		return any(field in template.redo_fields for field in field_names)

	def draw(self, context):
		layout = self.layout
		box = layout.box()
		box.label(text="FK Tweak Chain Settings:", icon='SETTINGS')
		settings = get_armature_settings(context.object.data, context)

		template = get_fk_template(self.template_id) if self.template_id else None
		split_size = 0.4

		col = box.column()
		if self.do_show_field("limb_property_base_name", template):
			split = col.split(align=True, factor=split_size)
			row = split.row(align=True)
			row.label(text="Limb Property Base Name:", translate=False)
			row = split.row(align=True)
			row.prop(self, "limb_property_base_name", text="")

		if self.do_show_field("do_create_fk", template):
			col.prop(self, "do_create_fk")

		if self.do_create_fk:
			if settings.do_create_widgets and self.do_show_field("fk_widget", template):
				split = col.split(align=True, factor=split_size)
				row = split.row(align=True)
				row.label(text="FK Widget:", translate=False)
				row = split.row(align=True)
				row.prop(self, "fk_widget", text="")

			if self.do_show_field("fk_bone_template", template):
				split = col.split(align=True, factor=split_size)
				row = split.row(align=True)
				row.label(text="FK Bone Template:", translate=False)
				row = split.row(align=True)
				row.prop(self, "fk_bone_template", text="")

		if self.do_show_any_field(
			["limb_property_base_name", "do_create_fk", "fk_widget", "fk_bone_template"],
			template,
		):
			col.separator()

		col = box.column(align=True)
		if self.do_show_field("tweak_relationship", template):
			split = col.split(align=True, factor=split_size)
			row = split.row(align=True)
			row.label(text="Tweak Relationship:", translate=False)
			row = split.row(align=True)
			row.prop(self, "tweak_relationship", text="")

		if self.do_show_field("skip_first_tweak", template):
			col.prop(self, "skip_first_tweak")

		if self.do_show_field("override_collections", template):
			col.prop(self, "override_collections")

		col = layout.column()
		if self.do_show_field("add_rotation_isolation", template):
			col.prop(self, "add_rotation_isolation")
		if self.do_show_field("create_rotation_follow_setup", template):
			col.prop(self, "create_rotation_follow_setup")
		if self.create_rotation_follow_setup and self.do_show_any_field(
			["rotation_follow_skip", "rotation_follow_relationship"],
			template,
		):
			box = layout.box()
			box.label(text="Rotation Follow Setup:", icon='CONSTRAINT')
			col = box.column()
			if self.do_show_field("rotation_follow_skip", template):
				col.prop(self, "rotation_follow_skip")
			if self.do_show_field("rotation_follow_relationship", template):
				col.prop(self, "rotation_follow_relationship")

	##################################################################################################
	# execute

	def execute(self, context):
		if self.add_rotation_isolation and not self.limb_property_base_name:
			self.report({'ERROR'}, "Limb property base name is required for rotation isolation.")
			return {'CANCELLED'}

		try:
			chains, original_mode, original_mirror = get_assembly_chains(
				context,
				self.assembly_uid,
				check_property_bone=self.add_rotation_isolation,
			)
		except Exception as e:
			self.report({'ERROR'}, str(e))
			return {'CANCELLED'}

		if self.assembly_uid:
			delete_assembly(context, self.assembly_uid)
			self.assembly_uid = ""

		options = FKAssemblyOptions(
			limb_property_base_name=self.limb_property_base_name,
			do_create_fk=self.do_create_fk,
			fk_bone_template=self.fk_bone_template,
			skip_first_tweak=self.skip_first_tweak,
			fk_widget=self.fk_widget,
			create_rotation_follow_setup=self.create_rotation_follow_setup,
			rotation_follow_skip=self.rotation_follow_skip,
			rotation_follow_relationship=self.rotation_follow_relationship,
			fk_collection_name=self.fk_collection_name,
			tweak_collection_name=self.tweak_collection_name,
			tweak_relationship=self.tweak_relationship,
			add_rotation_isolation=self.add_rotation_isolation,
			override_collections=self.override_collections,
		)

		try:
			create_fk_assembly(context, chains, self.template_name, options)
		except Exception as e:
			self.report({'ERROR'}, str(e))
			bpy.ops.object.mode_set(mode=original_mode)
			context.object.data.use_mirror_x = original_mirror
			return {'CANCELLED'}

		chain_count = len(chains)
		self.report({'INFO'}, f"Successfully generated {chain_count} FK/Tweak chain{'s' if chain_count != 1 else ''}.")
		context.object.data.use_mirror_x = original_mirror
		return {'FINISHED'}


classes = (
	RIG_OT_advanced_fk_tweak_setup,
)


def register():
	validate_fk_templates()
	for cls in classes:
		bpy.utils.register_class(cls)


def unregister():
	for cls in classes:
		bpy.utils.unregister_class(cls)


if __name__ == "__main__":
	try:
		unregister()
	except Exception:
		pass
	register()

	bpy.ops.rig.advanced_fk_setup('INVOKE_DEFAULT')
