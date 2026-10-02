import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty, IntProperty
from rigtools.assemblies.delete_assembly import delete_assembly
from rigtools.assemblies.assembly_data import find_assembly
from rigtools.assemblies.template_options import resolve_template_options
from rigtools.assemblies.torso_assembly import TorsoAssemblyOptions, create_torso_assembly
from rigtools.assemblies.torso_templates import get_torso_template, validate_torso_templates
from rigtools.rig_ui.property_name import guess_limb_name
from rigtools.utils.bone_chain import ChainBranchingError, find_chains_from_selection, get_assembly_chains
from rigtools.utils.widget import fk_widget_types


class RIG_OT_advanced_torso_setup(bpy.types.Operator):
	"""Setup Torso Assembly with advanced options"""
	bl_idname = "rig.advanced_torso_setup"
	bl_label = "Generate Torso Assembly"
	bl_options = {'REGISTER', 'UNDO'}

	limb_property_base_name: StringProperty(
		name="Limb Property Base Name",
		description="Base name of the property to store the limb. Example: 'arm', 'leg', 'tail', etc.",
		default="torso"
	)

	lower_torso_bone_count: IntProperty(
		name="Lower Torso Bone Count",
		description="Number of bones in the lower torso",
		default=2
	)

	fk_widget: EnumProperty(
		name="FK Widget",
		description="Type of widget to use for the FK bones",
		items=fk_widget_types,
		default='CIRCLE'
	)

	neck_bone_count: IntProperty(
		name="Neck Bone Count",
		description="Number of bones in the neck",
		default=1
	)

	use_twist_bones: BoolProperty(
		name="Use Twist Bones",
		description="Use twist bones for the neck and/or chest",
		default=True
	)

	neck_twist_bone_count: IntProperty(
		name="Neck Twist Bone Count",
		description="Number of bones in the neck twist",
		default=2
	)

	chest_twist_bone_count: IntProperty(
		name="Chest Twist Bone Count",
		description="Number of bones in the chest twist",
		default=2
	)

	add_tweak_bones: BoolProperty(
		name="Add Tweak Bones",
		description="Add tweak bones for the neck and/or chest",
		default=True
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
		description="UID of the assembly to use for the torso assembly",
		default="",
		options={'HIDDEN'}
	)

	template_id: StringProperty(
		name="Template ID",
		description="Torso template to apply on invoke",
		default="",
		options={'HIDDEN'}
	)

	template_name: StringProperty(
		name="Template Name",
		description="Name of the template to use for the torso assembly",
		default="",
		options={'HIDDEN'}
	)

	add_neck_rotation_isolation: BoolProperty(
		name="Add Neck Rotation Isolation",
		description="Add rotation isolation for the neck",
		default=True
	)

	add_chest_rotation_isolation: BoolProperty(
		name="Add Chest Rotation Isolation",
		description="Add rotation isolation for the chest",
		default=True
	)

	override_collections: BoolProperty(
		name="Override Collections",
		description="Override the collections for the torso assembly",
		default=True
	)

	@classmethod
	def description(cls, context, properties):
		if properties.template_id:
			template = get_torso_template(properties.template_id)
			if template:
				return template.description
		return "Setup torso assembly with advanced options"

	##################################################################################################
	# invoke

	def _invoke_from_selection(self, context):
		try:
			chains = find_chains_from_selection(context)
		except ChainBranchingError as e:
			self.report({'ERROR'}, str(e))
			return {'CANCELLED'}

		if not chains:
			self.report({'ERROR'}, "No chains selected.")
			return {'CANCELLED'}

		self.template_name = "Advanced"

	def _invoke_from_template(self, context):
		template = get_torso_template(self.template_id)
		if not template:
			self.report({'ERROR'}, f"Unknown torso template: '{self.template_id}'")
			return {'CANCELLED'}

		option_values = resolve_template_options(TorsoAssemblyOptions, template.options)
		for key, value in option_values.items():
			setattr(self, key, value)

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
			template = get_torso_template(self.template_id)
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
		box.label(text="Torso Settings:", icon='SETTINGS')

		template = get_torso_template(self.template_id) if self.template_id else None
		split_size = 0.4

		col = box.column()
		if self.do_show_field("limb_property_base_name", template):
			split = col.split(align=True, factor=split_size)
			row = split.row(align=True)
			row.label(text="Limb Property Base Name:", translate=False)
			row = split.row(align=True)
			row.prop(self, "limb_property_base_name", text="")

		col.separator()

		if self.do_show_field("lower_torso_bone_count", template):
			split = col.split(align=True, factor=split_size)
			row = split.row(align=True)
			row.label(text="Lower Torso Bone Count:", translate=False)
			row = split.row(align=True)
			row.prop(self, "lower_torso_bone_count", text="")

		if self.do_show_field("neck_bone_count", template):
			split = col.split(align=True, factor=split_size)
			row = split.row(align=True)
			row.label(text="Neck Bone Count:", translate=False)
			row = split.row(align=True)
			row.prop(self, "neck_bone_count", text="")

		layout.separator()
		col = layout.column()

		if self.do_show_field("use_twist_bones", template):
			col.prop(self, "use_twist_bones")
			if self.use_twist_bones and self.do_show_any_field(["neck_twist_bone_count", "chest_twist_bone_count"], template):
				box = layout.box()
				box.label(text="Twist Bones:", icon='SETTINGS')
				col = box.column()
				if self.do_show_field("neck_twist_bone_count", template):
					split = col.split(align=True, factor=split_size)
					row = split.row(align=True)
					row.label(text="Neck Twist Bone Count:", translate=False)
					row = split.row(align=True)
					row.prop(self, "neck_twist_bone_count", text="")

				if self.do_show_field("chest_twist_bone_count", template):
					split = col.split(align=True, factor=split_size)
					row = split.row(align=True)
					row.label(text="Chest Twist Bone Count:", translate=False)
					row = split.row(align=True)
					row.prop(self, "chest_twist_bone_count", text="")

		layout.separator()
		col = layout.column()

		if self.do_show_field("fk_widget", template):
			split = col.split(align=True, factor=split_size)
			row = split.row(align=True)
			row.label(text="FK Widget:", translate=False)
			row = split.row(align=True)
			row.prop(self, "fk_widget", text="")

		if self.do_show_field("add_tweak_bones", template):
			col.prop(self, "add_tweak_bones")

		if self.add_tweak_bones and self.do_show_field("tweak_relationship", template):
			split = col.split(align=True, factor=split_size)
			row = split.row(align=True)
			row.label(text="Tweak Relationship:", translate=False)
			row = split.row(align=True)
			row.prop(self, "tweak_relationship", text="")	

		layout.separator()
		col = layout.column()
		if self.do_show_field("add_neck_rotation_isolation", template):
			col.prop(self, "add_neck_rotation_isolation")
		if self.do_show_field("add_chest_rotation_isolation", template):
			col.prop(self, "add_chest_rotation_isolation")

	##################################################################################################
	# execute

	def execute(self, context):
		if not self.limb_property_base_name:
			self.report({'ERROR'}, "Limb property base name is required.")
			return {'CANCELLED'}

		try:
			chains, original_mode, original_mirror = get_assembly_chains(
				context,
				self.assembly_uid,
				check_property_bone=self.add_neck_rotation_isolation or self.add_chest_rotation_isolation,
			)
		except Exception as e:
			self.report({'ERROR'}, str(e))
			return {'CANCELLED'}

		if self.assembly_uid:
			delete_assembly(context, self.assembly_uid)
			self.assembly_uid = ""

		options = TorsoAssemblyOptions(
			limb_property_base_name=self.limb_property_base_name,
			lower_torso_bone_count=self.lower_torso_bone_count,
			neck_bone_count=self.neck_bone_count,
			use_twist_bones=self.use_twist_bones,
			neck_twist_bone_count=self.neck_twist_bone_count,
			chest_twist_bone_count=self.chest_twist_bone_count,
			add_tweak_bones=self.add_tweak_bones,
			tweak_relationship=self.tweak_relationship,
			add_neck_rotation_isolation=self.add_neck_rotation_isolation,
			add_chest_rotation_isolation=self.add_chest_rotation_isolation,
			fk_widget=self.fk_widget,
			override_collections=self.override_collections,
		)

		try:
			create_torso_assembly(context, chains, self.template_name, options)
		except Exception as e:
			self.report({'ERROR'}, str(e))
			bpy.ops.object.mode_set(mode=original_mode)
			context.object.data.use_mirror_x = original_mirror
			return {'CANCELLED'}

		chain_count = len(chains)
		self.report({'INFO'}, f"Successfully generated {chain_count} torso assembl{'ies' if chain_count != 1 else 'y'}.")
		context.object.data.use_mirror_x = original_mirror
		return {'FINISHED'}


classes = (
	RIG_OT_advanced_torso_setup,
)


def register():
	validate_torso_templates()
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

	bpy.ops.rig.advanced_torso_setup('INVOKE_DEFAULT')
