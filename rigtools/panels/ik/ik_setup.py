import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty, IntProperty, CollectionProperty
from rigtools.armature_settings import get_armature_settings
from rigtools.assemblies.delete_assembly import delete_assembly
from rigtools.assemblies.ik_templates import (
	get_ik_template,
	resolve_ik_parents,
	resolve_twist_segments,
	validate_ik_templates,
)
from rigtools.assemblies.template_options import resolve_template_options
from rigtools.rig_ui.property_name import guess_limb_name
from rigtools.tool.spline_ik import spline_twist_type
from rigtools.tool.twist_bones import falloff_presets, twist_source_types
from rigtools.utils.widget import fk_widget_types
from rigtools.tool.ik_parent import IKParentTarget
from rigtools.utils.bone_chain import ChainBranchingError, find_chains_from_selection, get_assembly_chains
from rigtools.assemblies.ik_assembly import IKAssemblyOptions, create_ik_assembly
from rigtools.assemblies.assembly_data import find_assembly
from rigtools.utils.bone import select_bones

class IKParentSlot(bpy.types.PropertyGroup):
	label: bpy.props.StringProperty(name="Label", default="")
	bone: bpy.props.StringProperty(name="Bone", default="")

class TwistSegmentSlot(bpy.types.PropertyGroup):
	name: StringProperty(name="Name", default="")
	index: IntProperty(name="Bone Index", default=0, min=0)
	source: EnumProperty(name="Source", items=twist_source_types, default='SELF')
	falloff: EnumProperty(name="Falloff", items=falloff_presets, default='LINEAR')

class RIG_OT_add_ik_parent(bpy.types.Operator):
	bl_idname = "rig.add_ik_parent"
	bl_label = "Add IK Parent"
	def execute(self, context):
		context.window_manager.rig_ik_parents.add()
		return {'FINISHED'}

class RIG_OT_remove_ik_parent(bpy.types.Operator):
	bl_idname = "rig.remove_ik_parent"
	bl_label = "Remove IK Parent"
	index: IntProperty()
	def execute(self, context):
		context.window_manager.rig_ik_parents.remove(self.index)
		return {'FINISHED'}

class RIG_OT_add_twist_segment(bpy.types.Operator):
	bl_idname = "rig.add_twist_segment"
	bl_label = "Add Twist Segment"
	def execute(self, context):
		context.window_manager.rig_twist_segments.add()
		return {'FINISHED'}

class RIG_OT_remove_twist_segment(bpy.types.Operator):
	bl_idname = "rig.remove_twist_segment"
	bl_label = "Remove Twist Segment"
	index: IntProperty()
	def execute(self, context):
		context.window_manager.rig_twist_segments.remove(self.index)
		return {'FINISHED'}

class RIG_OT_advanced_ik_setup(bpy.types.Operator):
	"""Create a FK/IK switching setup with advanced options."""
	bl_idname = "rig.advanced_ik_setup"
	bl_label = "Geenrate IK Assembly"
	bl_options = {'REGISTER', 'UNDO'}
	bl_property = "limb_property_base_name"

	# FK/Tweak Settings
	limb_property_base_name: StringProperty(
		name="Limb Property Base Name",
		description="Base name of the property to store the limb. Example: 'arm', 'leg', 'tail', etc.",
		default=""
	)

	add_tweak_bones: BoolProperty(
		name="Add Tweak Bones",
		description="Add tweak bones to the FK/IK switch",
		default=True
	)

	override_collections: BoolProperty(
		name="Override Bone Collections",
		description="Specify the bone collections for various bone types",
		default=True
	)
	
	switch_property_type: EnumProperty(
		name="Switch Property Type",
		description="Type of the switch property",
		items=[
			('ENUM', "Enum", "Enum property; dropdown with 'FK' and 'IK' options"),
			('FLOAT', "Float", "A float slider with values between 0.0 and 1.0"),
		],
		default='ENUM'
	)

	ik_type: EnumProperty(
		name="IK Type",
		description="Type of IK to create",
		items=[
			('IK', "IK", "Standard IK setup"),
			('SPLINE', "Spline IK", "Spline IK"),
		],
		default='IK'
	)

	enable_ik_stretch: BoolProperty(
		name="Enable IK Stretch",
		description="Enable IK stretch for the IK chain",
		default=True
	)

	pole_distance: FloatProperty(
		name="Pole Distance",
		description="Distance from the IK chain to place the pole bone",
		default=1.0,
		min=0.0
	)

	spline_control_count: IntProperty(
		name="Control Count",
		description="Number of controls to create for the spline IK",
		default=3,
		min=2,
		max=10
	)

	spline_skip_first: BoolProperty(
		name="Skip First Bone",
		description="Skip the first bone in the chain for the IK spline",
		default=False
	)

	twist_type: EnumProperty(
		name="Twist Controllers",
		description="Type of twist to create for the IK spline",
		items=spline_twist_type,
		default='START_END'
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

	fk_widget: EnumProperty(
		name="FK Widget",
		description="Type of widget to create for the FK bones",
		items=fk_widget_types,
		default='FK'
	)

	enable_snapping: BoolProperty(
		name="Enable FK<->IK Snapping",
		description="Setup additional bones for IK>FK snapping, and enable the snapping UI",
		default=True
	)

	ik_parent: BoolProperty(
		name="Setup IK Parent Switching",
		default=True,
		description="Setup IK parent switching"
	)

	add_ik_control_as_pole_parent: BoolProperty(
		name="Add IK Control as Pole Parent",
		description="Add the IK control as the pole parent",
		default=False
	)
	
	ik_parent_self_parent_label: StringProperty(
		name="Parent Label",
		description="Label for the self parent of the IK parent",
		default="Foot"
	)

	add_rotation_isolation: BoolProperty(
		name="Add Rotation Isolation",
		description="Add rotation isolation to the start of the FK chain.",
		default=True
	)

	inherit_scale_from_root: BoolProperty(
		name="Inherit Scale From Root",
		description="Socket inherits scale from the root bone instead of its parent.",
		default=False
	)

	use_twist_bones: BoolProperty(
		name="Twist Bones",
		description="Create deform twist bones along limb segments",
		default=False
	)

	twist_bone_count: IntProperty(
		name="Twist Bone Count",
		description="Number of twist bones per segment",
		default=4,
		min=2,
		max=16
	)

	assembly_uid: StringProperty(
		name="Assembly UID",
		description="UID of the assembly to load",
		default="",
		options={'HIDDEN'}
	)

	template_id: StringProperty(
		name="Template ID",
		description="IK template to apply on invoke",
		default="",
		options={'HIDDEN'}
	)

	template_name: StringProperty(
		name="Template Name",
		description="Name of the template to use for the IK/FK switch chain",
		default="",
		options={'HIDDEN'}
	)

	@classmethod
	def description(cls, context, properties):
		if properties.template_id:
			template = get_ik_template(properties.template_id)
			if template:
				return template.description
		return "Create a FK/IK switching setup with advanced options."
	
	##################################################################################################
	# invoke
	def _invoke_from_selection(self, context):
		wm = context.window_manager
		if len(wm.rig_ik_parents) == 0:
			settings = get_armature_settings(context.object.data, context)
			root = wm.rig_ik_parents.add()
			root.label, root.bone = "Root", settings.root_bone_name
			torso = wm.rig_ik_parents.add()
			torso.label, torso.bone = "Torso", settings.torso_bone_name

		wm.rig_twist_segments.clear()

		try:
			chains = find_chains_from_selection(context)
		except ChainBranchingError as e:
			self.report({'ERROR'}, str(e))
			return {'CANCELLED'}

		if not chains:
			self.report({'ERROR'}, "No chains selected.")
			return {'CANCELLED'}

		limb_name = guess_limb_name(chains[0][0], context)
		self.limb_property_base_name = limb_name
		self.template_name = "Advanced"
		self.bl_label = "Advanced IK Setup"

	def _invoke_from_template(self, context):
		template = get_ik_template(self.template_id)
		if not template:
			self.report({'ERROR'}, f"Unknown IK template: '{self.template_id}'")
			return {'CANCELLED'}

		option_values = resolve_template_options(IKAssemblyOptions, template.options)
		parent_names = option_values.pop("ik_parents", ())
		twist_segments_raw = option_values.pop("twist_segments", ())

		try:
			parents, include_self = resolve_ik_parents(context, parent_names)
		except ValueError as error:
			self.report({'ERROR'}, str(error))
			return {'CANCELLED'}

		for key, value in option_values.items():
			if hasattr(self, key):
				setattr(self, key, value)

		self.add_ik_control_as_pole_parent = include_self

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

		wm = context.window_manager
		wm.rig_ik_parents.clear()
		for parent in parents:
			slot = wm.rig_ik_parents.add()
			slot.label = parent.label
			slot.bone = parent.bone

		wm.rig_twist_segments.clear()
		for segment in resolve_twist_segments(twist_segments_raw):
			slot = wm.rig_twist_segments.add()
			slot.name = segment.name
			slot.index = segment.index
			slot.source = segment.source
			slot.falloff = segment.falloff

		self.template_name = template.label

	def _invoke_from_assembly(self, context):
		assembly = find_assembly(context.object, self.assembly_uid)
		if not assembly:
			self.report({'ERROR'}, "Assembly not found.")
			return {'CANCELLED'}

		options = assembly.get_options()
		twist_segments_raw = options.pop("twist_segments", [])
		for key, value in options.items():
			if hasattr(self, key):
				setattr(self, key, value)

		wm = context.window_manager
		wm.rig_ik_parents.clear()
		for parent in assembly.ik_parents:
			slot = wm.rig_ik_parents.add()
			slot.label = parent.label
			slot.bone = parent.bone

		wm.rig_twist_segments.clear()
		for segment in resolve_twist_segments(twist_segments_raw):
			slot = wm.rig_twist_segments.add()
			slot.name = segment.name
			slot.index = segment.index
			slot.source = segment.source
			slot.falloff = segment.falloff

		self.template_name = assembly.template_name
		self.bl_label = assembly.template_name or "Advanced IK Setup"

	def invoke(self, context, event):
		show_dialog = True

		if self.assembly_uid:
			result = self._invoke_from_assembly(context)
		elif self.template_id:
			result = self._invoke_from_template(context)
			template = get_ik_template(self.template_id)
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
		if not template: return True
		redo_fields = template.redo_fields
		return field_name in redo_fields

	def do_show_any_field(self, field_names, template):
		if not template: return True
		redo_fields = template.redo_fields
		return any(field in redo_fields for field in field_names)
	
	def draw(self, context):
		layout = self.layout
		split_size = 0.4

		box = layout.box()
		box.label(text="IK/FK Switch Settings:", icon='SETTINGS')

		template = None
		if self.template_id:
			template = get_ik_template(self.template_id)

		col = box.column()
		if self.do_show_field("limb_property_base_name", template):
			split = col.split(align=True, factor=split_size)
			row = split.row(align=True)
			row.label(text="Limb Property Base Name:", translate=False)
			row = split.row(align=True)
			row.prop(self, "limb_property_base_name", text="")

		if self.do_show_field("switch_property_type", template):
			split = col.split(align=True, factor=split_size)
			row = split.row(align=True)
			row.label(text="Switch Property Type:", translate=False)
			row = split.row(align=True)
			row.prop(self, "switch_property_type", text="")

		if self.do_show_any_field(["limb_property_base_name", "switch_property_type"], template):
			layout.separator()

		if self.do_show_field("add_rotation_isolation", template):
			col = layout.column()
			col.prop(self, "add_rotation_isolation")
			if self.add_rotation_isolation and self.do_show_field("inherit_scale_from_root", template):
				col.prop(self, "inherit_scale_from_root")

		if self.do_show_field("fk_widget", template):
			split = col.split(align=True, factor=split_size)
			row = split.row(align=True)
			row.label(text="FK Widget:", translate=False)
			row = split.row(align=True)
			row.prop(self, "fk_widget", text="")

		if self.do_show_any_field(["add_rotation_isolation", "inherit_scale_from_root", "fk_widget"], template):
			col.separator()

		if self.do_show_field("add_tweak_bones", template):
			col.prop(self, "add_tweak_bones")

		if self.add_tweak_bones and self.do_show_field("tweak_relationship", template):
			split = col.split(align=True, factor=split_size)
			row = split.row(align=True)
			row.label(text="Tweak Relationship:", translate=False)
			row = split.row(align=True)
			row.prop(self, "tweak_relationship", text="")

		if self.do_show_any_field(["add_tweak_bones", "tweak_relationship"], template):
			layout.separator()
		
		if self.do_show_field("ik_type", template):
			col = layout.column()
			col.prop(self, "ik_type")

		if self.do_show_any_field(["spline_control_count", "twist_type", "spline_skip_first", "enable_snapping", "enable_ik_stretch", "pole_distance"], template):
			box = layout.box()
			if self.ik_type == 'SPLINE':
				box.label(text="Spline IK Settings:", icon='CON_SPLINEIK')
				col = box.column()

				if self.do_show_field("spline_control_count", template):
					col.prop(self, "spline_control_count")

				if self.do_show_field("twist_type", template):
					split = col.split(align=True, factor=split_size)
					row = split.row(align=True)
					row.label(text="Twist Controllers:", translate=False)
					row = split.row(align=True)
					row.prop(self, "twist_type", text="")

				if self.do_show_field("spline_skip_first", template):
					col.prop(self, "spline_skip_first")

			elif self.ik_type == 'IK':
				box.label(text="IK Settings:", icon='CON_KINEMATIC')
				col = box.column()

				if self.do_show_field("enable_snapping", template):
					col.prop(self, "enable_snapping")

				if self.do_show_field("enable_ik_stretch", template):
					col.prop(self, "enable_ik_stretch")

				if self.do_show_field("pole_distance", template):
					col.prop(self, "pole_distance")

		if self.do_show_any_field(["ik_type", "spline_control_count", "twist_type", "spline_skip_first", "enable_snapping", "enable_ik_stretch", "pole_distance"], template):
			layout.separator()
		
		if self.do_show_field("ik_parent", template):
			col = layout.column(align=True)
			col.prop(self, "ik_parent")
		if self.ik_parent and self.do_show_field("ik_parents", template):
			col = layout.column()
			box = col.box()
			box.label(text="IK Parents:", icon='CON_ARMATURE')
			parents = context.window_manager.rig_ik_parents
			col = box.column(align=True)
			for i, parent in enumerate(parents):
				row = col.row(align=True)
				row.prop(parent, "label", text="")
				row.prop_search(parent, "bone", context.object.data, "bones", text="")
				op = row.operator("rig.remove_ik_parent", text="", icon='REMOVE')
				op.index = i
			box.operator("rig.add_ik_parent", text="Add Parent", icon='ADD')

			if self.ik_type == 'IK':
				row = box.row(align=True)
				split = row.split(align=True, factor=0.6)
				row = split.row(align=True)
				row.prop(self, "add_ik_control_as_pole_parent")
				if self.add_ik_control_as_pole_parent:
					row = split.row(align=True)
					row.prop(self, "ik_parent_self_parent_label", text="")

		if self.ik_type == 'IK' and self.do_show_any_field(
			["use_twist_bones", "twist_bone_count", "twist_segments"], template
		):
			layout.separator()
			col = layout.column(align=True)
			if self.do_show_field("use_twist_bones", template):
				col.prop(self, "use_twist_bones")

			if self.use_twist_bones:
				if self.do_show_field("twist_bone_count", template):
					split = col.split(align=True, factor=split_size)
					row = split.row(align=True)
					row.label(text="Twist Count:", translate=False)
					row = split.row(align=True)
					row.prop(self, "twist_bone_count", text="")

				if self.do_show_field("twist_segments", template):
					box = col.box()
					box.label(text="Twist Segments:", icon='BONE_DATA')
					segments = context.window_manager.rig_twist_segments
					seg_col = box.column(align=True)
					header = seg_col.row(align=True)
					header.label(text="Name")
					idx_header = header.row(align=True)
					idx_header.ui_units_x = 2.5
					idx_header.label(text="Index")
					header.label(text="Source")
					header.label(text="Falloff")
					header.label(text="", icon='BLANK1')
					for i, segment in enumerate(segments):
						row = seg_col.row(align=True)
						row.prop(segment, "name", text="")
						idx = row.row(align=True)
						idx.ui_units_x = 2.5
						idx.prop(segment, "index", text="")
						row.prop(segment, "source", text="")
						sub = row.row(align=True)
						sub.enabled = segment.source != 'NONE'
						sub.prop(segment, "falloff", text="")
						op = row.operator("rig.remove_twist_segment", text="", icon='REMOVE')
						op.index = i
					box.operator("rig.add_twist_segment", text="Add Segment", icon='ADD')


	##################################################################################################
	# execute
	
	def execute(self, context):
		if not self.limb_property_base_name:
			self.report({'ERROR'}, "Limb property base name is required.")
			self.assembly_uid = ""
			return {'CANCELLED'}

		try:
			chains, original_mode, original_mirror = get_assembly_chains(context, self.assembly_uid)
		except Exception as e:
			self.report({'ERROR'}, str(e))
			self.assembly_uid = ""
			return {'CANCELLED'}

		for chain in chains:
			if len(chain) == 1:
				self.report({'ERROR'}, "All chains must have at least 2 bones.")
				bpy.ops.object.mode_set(mode=original_mode)
				self.assembly_uid = ""
				context.object.data.use_mirror_x = original_mirror
				return {'CANCELLED'}

		if self.assembly_uid:
			delete_assembly(context, self.assembly_uid)
		self.assembly_uid = ""

		options = IKAssemblyOptions(
			limb_property_base_name=self.limb_property_base_name,
			add_tweak_bones=self.add_tweak_bones,
			switch_property_type=self.switch_property_type,
			add_rotation_isolation=self.add_rotation_isolation,
			inherit_scale_from_root=self.inherit_scale_from_root,
			override_collections=self.override_collections,
			ik_type=self.ik_type,
			enable_ik_stretch=self.enable_ik_stretch,
			pole_distance=self.pole_distance,
			spline_control_count=self.spline_control_count,
			spline_skip_first=self.spline_skip_first,
			twist_type=self.twist_type,
			tweak_relationship=self.tweak_relationship,
			fk_widget=self.fk_widget,
			enable_snapping=self.enable_snapping,
			ik_parent=self.ik_parent,
			ik_parents=[
				IKParentTarget(label=s.label, bone=s.bone)
				for s in context.window_manager.rig_ik_parents
				if s.bone
			],
			add_ik_control_as_pole_parent=self.add_ik_control_as_pole_parent,
			ik_parent_self_parent_label=self.ik_parent_self_parent_label,
			use_twist_bones=self.use_twist_bones,
			twist_bone_count=self.twist_bone_count,
			twist_segments=resolve_twist_segments(
				[
					{
						"name": s.name,
						"index": s.index,
						"source": s.source,
						"falloff": s.falloff,
					}
					for s in context.window_manager.rig_twist_segments
				]
			) if self.use_twist_bones else [],
		)

		try:
			tip_controls = create_ik_assembly(context, chains, self.template_name, options)
		except Exception as e:
			self.report({'ERROR'}, str(e))
			bpy.ops.object.mode_set(mode=original_mode)
			context.object.data.use_mirror_x = original_mirror
			return {'CANCELLED'}

		# If everything succeeds, we leave it in Pose mode so the user can see the result
		if tip_controls:
			if context.object.mode != 'POSE':
				bpy.ops.object.mode_set(mode='POSE')
			bpy.ops.pose.select_all(action='DESELECT')
			select_bones(context.object, tip_controls)

		self.report({'INFO'}, f"Successfully generated {len(chains)} FK/IK switch chain{'s' if len(chains) != 1 else ''}.")
		context.object.data.use_mirror_x = original_mirror
		return {'FINISHED'}

##################################################################################################
# registration

classes = (
	IKParentSlot,
	TwistSegmentSlot,
	RIG_OT_add_ik_parent,
	RIG_OT_remove_ik_parent,
	RIG_OT_add_twist_segment,
	RIG_OT_remove_twist_segment,
	RIG_OT_advanced_ik_setup,
)

def register():
	validate_ik_templates()
	for cls in classes:
		bpy.utils.register_class(cls)

	bpy.types.WindowManager.rig_ik_parents = CollectionProperty(type=IKParentSlot)
	bpy.types.WindowManager.rig_ik_parent_index = IntProperty()
	bpy.types.WindowManager.rig_twist_segments = CollectionProperty(type=TwistSegmentSlot)

def unregister():
	del bpy.types.WindowManager.rig_ik_parents
	del bpy.types.WindowManager.rig_ik_parent_index
	del bpy.types.WindowManager.rig_twist_segments

	for cls in classes:
		bpy.utils.unregister_class(cls)
	
if __name__ == "__main__":
	try:
		unregister()
	except Exception:
		pass
	register()
	
	bpy.ops.rig.advanced_ik_setup()
