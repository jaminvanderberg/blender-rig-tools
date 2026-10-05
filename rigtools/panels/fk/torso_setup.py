import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty, IntProperty
from rigtools.assemblies.delete_assembly import delete_assembly
from rigtools.assemblies.assembly_data import find_assembly, get_assembly_chains
from rigtools.assemblies.template_options import resolve_template_options
from rigtools.assemblies.torso_assembly import TorsoAssemblyOptions, create_torso_assembly
from rigtools.assemblies.torso_templates import get_torso_template, validate_torso_templates
from rigtools.panels.template_draw import SplitSection, TemplateDraw
from rigtools.utils.naming import guess_limb_name
from rigtools.tool.twist_bones import falloff_presets
from rigtools.utils.bone_chain import ChainBranchingError, find_chains_from_selection
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

	neck_base_property_name: StringProperty(
		name="Neck Base Property Name",
		description="Base property name for the neck",
		default="neck"
	)

	neck_inherit_scale_from_root: BoolProperty(
		name="Neck Inherit Scale From Root",
		description="Inherit scale from the root for the neck",
		default=True
	)

	add_head_rotation_isolation: BoolProperty(
		name="Add Head Rotation Isolation",
		description="Add rotation isolation for the head",
		default=True
	)

	head_base_property_name: StringProperty(
		name="Head Base Property Name",
		description="Base property name for the head",
		default="head"
	)

	head_inherit_scale_from_root: BoolProperty(
		name="Head Inherit Scale From Root",
		description="Inherit scale from the root for the head",
		default=True
	)

	neck_falloff_type: EnumProperty(
		name="Neck Falloff Type",
		description="Type of falloff for the neck",
		items=falloff_presets + [('NONE', "None", "No falloff", '', 5)],
		default='LINEAR'
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
		self.template_id = assembly.template_id

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

	def draw(self, context):
		layout = self.layout
		template = get_torso_template(self.template_id) if self.template_id else None
		split_size = 0.6

		def field_visible(field_name):
			if field_name in ["tweak_relationship"]:
				return self.add_tweak_bones
			if field_name in ["neck_base_property_name", "neck_inherit_scale_from_root"]:
				return self.add_neck_rotation_isolation
			if field_name in ["head_base_property_name", "head_inherit_scale_from_root"]:
				return self.add_head_rotation_isolation
			if field_name in ["neck_twist_bone_count", "chest_twist_bone_count"]:
				return self.use_twist_bones

			return True

		draw = TemplateDraw(self, template, split_size=split_size, visible_func=field_visible)

		draw.box_section(layout, ["limb_property_base_name", "lower_torso_bone_count", "neck_bone_count"], 
			"Torso Settings:", "SETTINGS", lambda col: (

			draw.draw_section(col, ["limb_property_base_name"], lambda: (
				draw.split_field(col, "Limb Property Base Name:", "limb_property_base_name"),
			)),
			draw.draw_section(col, ["lower_torso_bone_count", "neck_bone_count"], lambda: (
				draw.split_field(col, "Lower Torso Bone Count:", "lower_torso_bone_count"),
				draw.split_field(col, "Neck Bone Count:", "neck_bone_count"),
			)),
		))
		draw.draw_section(layout, ["use_twist_bones", "neck_twist_bone_count", "chest_twist_bone_count"], lambda: (
			draw.full_field(layout, "Use Twist Bones", "use_twist_bones"),
			draw.box_section(layout, ["neck_twist_bone_count", "chest_twist_bone_count"], "Twist Bones:", 'MOD_SCREW', lambda col: (
				draw.full_field(col, "Neck Twist Bone Count:", "neck_twist_bone_count"),
				draw.full_field(col, "Chest Twist Bone Count:", "chest_twist_bone_count"),
			)),
		))
		draw.draw_section(layout, ["fk_widget", "add_tweak_bones", "tweak_relationship"], lambda: (
			draw.split_field(layout, "FK Widget:", "fk_widget"),
			draw.full_field(layout, "Add Tweak Bones", "add_tweak_bones"),
			draw.split_field(layout, "Tweak Relationship:", "tweak_relationship"),
		))

		draw.box_section(layout, ["add_neck_rotation_isolation", "add_head_rotation_isolation", "neck_base_property_name", "neck_inherit_scale_from_root", "head_base_property_name", "head_inherit_scale_from_root"], 
			"Rotation Isolation:", 'SETTINGS', lambda col: (

			draw.draw_section(col, ["add_neck_rotation_isolation", "neck_base_property_name"], lambda: (
				draw.split_row(col, [
					SplitSection(label="Add Neck Rotation Isolation", prop="add_neck_rotation_isolation"),
					SplitSection(label="", prop="neck_base_property_name"),
				]),
				draw.full_field(col, "Neck Inherit Scale From Root", "neck_inherit_scale_from_root"),
			)),

			draw.draw_section(col, ["add_head_rotation_isolation", "head_base_property_name"], lambda: (
				draw.split_row(col, [
					SplitSection(label="Add Head Rotation Isolation", prop="add_head_rotation_isolation"),
					SplitSection(label="Head Base Property Name", prop="head_base_property_name"),
				]),
				draw.full_field(col, "Head Inherit Scale From Root", "head_inherit_scale_from_root"),
			)),
		))

		draw.draw_section(layout, ["neck_falloff_type"], lambda: (
			draw.split_field(layout, "Neck Falloff:", "neck_falloff_type"),
		))

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
				check_property_bone=self.add_neck_rotation_isolation or self.add_head_rotation_isolation,
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
			neck_base_property_name=self.neck_base_property_name,
			neck_inherit_scale_from_root=self.neck_inherit_scale_from_root,
			add_head_rotation_isolation=self.add_head_rotation_isolation,
			head_base_property_name=self.head_base_property_name,
			head_inherit_scale_from_root=self.head_inherit_scale_from_root,
			fk_widget=self.fk_widget,
			neck_falloff_type=self.neck_falloff_type,
		)

		try:
			create_torso_assembly(context, chains, self.template_id, self.template_name, options)
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
