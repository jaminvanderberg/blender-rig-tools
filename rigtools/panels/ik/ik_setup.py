import json
import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty, IntProperty, CollectionProperty
from rigtools.armature_settings import get_armature_settings
from rigtools.assemblies.reconfigure_assembly import reconfigure_assembly
from rigtools.assemblies.assembly_transaction import AssemblyTransactionError, run_assembly_transaction
from rigtools.assemblies.ik_templates import (
	get_ik_template,
	resolve_ik_parents,
	resolve_twist_segments,
	validate_ik_templates,
)
from rigtools.assemblies.template_options import resolve_template_options
from rigtools.panels.skirt_legs import draw_skirt_legs, fill_skirt_legs, iter_skirt_leg_slots
from rigtools.panels.template_draw import SplitSection, TemplateDraw
from rigtools.twist_bones import TwistChainStatus, evaluate_twist_snapshot, snapshot_twist_status
from rigtools.utils.naming import guess_limb_name
from rigtools.tool.spline_ik import spline_twist_type
from rigtools.tool.skirt_ride import SkirtLeg
from rigtools.tool.twist_bones import falloff_presets, twist_source_types
from rigtools.utils.widget import fk_widget_types
from rigtools.tool.ik_parent import IKParentTarget
from rigtools.utils.bone_chain import ChainBranchingError, find_chains_from_selection
from rigtools.assemblies.assembly_data import find_assembly, get_assembly_chains
from rigtools.assemblies.ik_assembly import IKAssemblyOptions, create_ik_assembly
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
	bl_label = "Generate IK Assembly"
	bl_options = {'REGISTER', 'UNDO'}
	bl_property = "limb_property_base_name"

	# FK/Tweak Settings
	limb_property_base_name: StringProperty(
		name="Limb Property Base Name",
		description="Base name of the property to store the limb. Example: 'arm', 'leg', 'tail', etc.",
		default=""
	)

	limb_type: StringProperty(
		name="Limb Type",
		description="Semantic limb type for assembly discovery (e.g. leg)",
		default="",
		options={'HIDDEN'},
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

	ik_bone_count: IntProperty(
		name="IK Bone Count",
		description="Number of bones to use for the IK chain",
		default=3,
		min=2,
		max=10
	)

	enable_ik_stretch: BoolProperty(
		name="Enable IK Stretch",
		description="Enable IK stretch for the IK chain",
		default=True
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

	spline_skip_last: BoolProperty(
		name="Skip Last Bone",
		description="Skip the last bone in the chain for the IK spline",
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
	
	fk_end_widget: EnumProperty(
		name="FK End Widget",
		description="Type of widget for the last bone in the FK chain (hand, foot, etc.)",
		items=fk_widget_types,
		default='BOX'
	)

	tip_widget: EnumProperty(
		name="Tip Widget",
		description="Type of widget for FK bones past the last IK control",
		items=fk_widget_types,
		default='CIRCLE'
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

	create_master_controllers: BoolProperty(
		name="Create FK Master Controllers / FK Follow",
		description="Create master controllers along the FK chain.",
		default=False
	)

	master_controllers_spacing: EnumProperty(
		name="Master Controllers Spacing",
		description="Spacing of the master controllers.",
		items=[
			('SINGLE', 'Single Controller', 'Use a single master controller'),
			('INTERVAL', 'Interval', 'Use an interval between master controllers'),
		],
		default='SINGLE'
	)

	master_controllers_interval: IntProperty(
		name="Interval",
		description="Number of bones to skip before creating a master controller.",
		options={'HIDDEN'}
	)

	master_controllers_interval_UI: IntProperty(
		name="Interval",
		description="Number of bones to skip before creating a master controller.",
		default=3,
		min=2,
	)

	master_controllers_skip_first: BoolProperty(
		name="Skip First",
		description="Skip the first bone when creating master controllers.",
		default=False
	)

	master_controllers_type: EnumProperty(
		name="Type",
		description="Type of master controller to create.",
		items=[
			('FK', 'Use FK Bones', 'Use the existing FK bones as master controllers (FK follow)'),
			('MASTER', 'Add Dedicated Masters', 'Create dedicated master controllers'),
		],
		default='FK'
	)

	master_controllers_widget: EnumProperty(
		name="Master Controller Widget",
		description="Type of widget to create for the master controllers.",
		items=fk_widget_types,
		default='CIRCLE'
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

	dialog_chains_json: StringProperty(
		name="Dialog Chains",
		description="Bone chains captured at invoke for dialog/redo UI",
		default="[]",
		options={'HIDDEN', 'SKIP_SAVE'}
	)

	dialog_twist_json: StringProperty(
		name="Dialog Twist Status",
		description="Twist registration snapshot captured at invoke",
		default="{}",
		options={'HIDDEN', 'SKIP_SAVE'}
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

	add_foot_roll: BoolProperty(
		name="Add Foot Roll",
		description="Add foot roll to the IK/FK switch chain",
		default=False
	)

	add_skirt_collision: BoolProperty(
		name="Add Skirt Collision",
		description="Add skirt collision to the FK bones.",
		default=False
	)

	add_skirt_ride: BoolProperty(
		name="Add Skirt Ride",
		description="Short skirts typically ride up when the leg is lifted.",
		default=False
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
	def _twist_parent_names(self, chains, segments):
		if segments:
			names = []
			for chain in chains:
				for seg in segments:
					if 0 <= seg.index < len(chain):
						names.append(chain[seg.index])
			return names
		return [name for chain in chains for name in chain]

	def _store_dialog_chains(self, chains):
		self.dialog_chains_json = json.dumps(chains)

	def _store_twist_snapshot(self, context, chains, *, require_chain):
		use_edit = context.object.mode == 'EDIT'
		parents = self._twist_parent_names(chains, context.window_manager.rig_twist_segments)
		snapshot = snapshot_twist_status(
			context.object.data,
			parents,
			use_edit_bones=use_edit,
			require_chain=require_chain,
		)
		self.dialog_twist_json = json.dumps(snapshot)

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

		self._store_dialog_chains(chains)
		self._store_twist_snapshot(context, chains, require_chain=True)
		limb_name = guess_limb_name(chains[0][0], context)
		self.limb_property_base_name = limb_name
		self.template_name = "Advanced"
		self.template_id = ""

	def _invoke_from_template(self, context):
		template = get_ik_template(self.template_id)
		if not template:
			self.report({'ERROR'}, f"Unknown IK template: '{self.template_id}'")
			return {'CANCELLED'}

		option_values = resolve_template_options(IKAssemblyOptions, template.options)
		if option_values.get("fk_end_widget") == "SAME":
			option_values["fk_end_widget"] = option_values["fk_widget"]
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

		try:
			chains = find_chains_from_selection(context)
		except ChainBranchingError as error:
			self.report({'ERROR'}, str(error))
			return {'CANCELLED'}

		if not chains:
			self.report({'ERROR'}, "No chains selected.")
			return {'CANCELLED'}

		self._store_dialog_chains(chains)
		if not self.limb_property_base_name:
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

		self._store_twist_snapshot(context, chains, require_chain=True)
		self.template_name = template.label

	def _invoke_from_assembly(self, context):
		assembly = find_assembly(context.object, self.assembly_uid)
		if not assembly:
			self.report({'ERROR'}, "Assembly not found.")
			return {'CANCELLED'}

		self.template_id = assembly.template_id

		options = assembly.get_options()
		twist_segments_raw = options.pop("twist_segments", [])
		for key, value in options.items():
			if hasattr(self, key):
				setattr(self, key, value)

		chains = assembly.get_chains()
		self._store_dialog_chains(chains)

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

		# Assembly already rewrote twist parenting under tweaks; count only.
		self._store_twist_snapshot(context, chains, require_chain=False)
		self.template_name = assembly.template_name
		self.template_id = assembly.template_id

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

		self.master_controllers_spacing = 'SINGLE' if self.master_controllers_interval <= 1 else 'INTERVAL'
		self.master_controllers_interval_UI = self.master_controllers_interval if self.master_controllers_interval >= 2 else 3
		fill_skirt_legs(context)

		if show_dialog:
			return context.window_manager.invoke_props_dialog(self, width=350)
		return self.execute(context)

	##################################################################################################
	# draw
	
	def draw(self, context):
		layout = self.layout

		template = get_ik_template(self.template_id) if self.template_id else None
		split_size = 0.5

		def field_visible(field_name):
			if field_name in ["tweak_relationship"]:
				return self.add_tweak_bones
			if field_name in ["inherit_scale_from_root"]:
				return self.add_rotation_isolation
			if field_name in ["ik_bone_count", "enable_snapping", "enable_ik_stretch", "add_foot_roll"]:
				return self.ik_type == 'IK'
			if field_name in ["spline_control_count", "twist_type", "spline_skip_first", "spline_skip_last"]:
				return self.ik_type == 'SPLINE'
			if field_name in ["ik_parents"]:
				return self.ik_parent
			if field_name in ["add_ik_control_as_pole_parent"]:
				return self.ik_parent and self.ik_type == 'IK'
			if field_name in ["use_twist_bones"]:
				return self.ik_type == 'IK'
			if field_name in ["twist_bone_count", "twist_segments"]:
				return self.use_twist_bones and self.ik_type == 'IK'
			if field_name in ["skirt_legs"]:
				return self.add_skirt_collision or self.add_skirt_ride
			if field_name in ["tip_widget"]:
				return self.ik_type == 'IK' or (self.ik_type == 'SPLINE' and self.spline_skip_last)
			if field_name in ["create_master_controllers"]:
				return True
			if field_name in ["master_controllers_spacing", "master_controllers_skip_first", "master_controllers_type"]:
				return self.create_master_controllers
			if field_name in ["master_controllers_interval_UI"]:
				return self.create_master_controllers and self.master_controllers_spacing == 'INTERVAL'
			if field_name in ["master_controllers_widget"]:
				return self.create_master_controllers and self.master_controllers_type == 'MASTER'
			return True

		draw = TemplateDraw(self, template, split_size=split_size, visible_func=field_visible,
			related_fields={
				"master_controllers_spacing": "master_controllers_interval",
				"master_controllers_interval_UI": "master_controllers_interval",
			}
		)

		draw.box_section(layout, ["limb_property_base_name", "switch_property_type", "fk_widget", "tip_widget", "add_tweak_bones", "tweak_relationship"], 
			"IK/FK Switch Settings:", "SETTINGS", lambda col: (

			draw.draw_section(col, ["limb_property_base_name", "switch_property_type", "fk_widget", "tip_widget"], lambda: (
				draw.split_field(col, "Limb Property Base Name:", "limb_property_base_name"),
				draw.split_field(col, "Switch Property Type:", "switch_property_type"),
				draw.split_field(col, "FK Widget:", "fk_widget"),
				draw.split_field(col, "FK End Widget:", "fk_end_widget"),
				draw.split_field(col, "Tip Widget:", "tip_widget"),
			)),
			draw.draw_section(col, ["add_tweak_bones", "tweak_relationship"], lambda: (
				draw.full_field(col, "Add Tweak Bones", "add_tweak_bones"),
				draw.split_field(col, "Tweak Relationship:", "tweak_relationship"),
			)),
		))
		draw.draw_section(layout, ["add_rotation_isolation", "inherit_scale_from_root"], lambda: (
			draw.full_field(layout, "Add Rotation Isolation", "add_rotation_isolation"),
			draw.full_field(layout, "Inherit Scale From Root", "inherit_scale_from_root"),
		))
		draw.draw_section(layout, ["create_master_controllers"], lambda: (
			draw.full_field(layout, "Create FK Master Controllers / FK Follow", "create_master_controllers"),
			draw.box_section(layout, ["master_controllers_spacing", "master_controllers_interval_UI", "master_controllers_skip_first", "master_controllers_type"],
				"", "NONE", lambda col: (

				draw.draw_section(col, ["master_controllers_type", "master_controllers_spacing", "master_controllers_interval_UI", "master_controllers_skip_first"], lambda: (
					draw.expand_field(col, "master_controllers_type"),
					draw.expand_field(col, "master_controllers_spacing"),
					draw.full_field(col, "Interval", "master_controllers_interval_UI"),
					draw.full_field(col, "Skip First", "master_controllers_skip_first"),
				)),
				draw.draw_section(col, ["master_controllers_widget"], lambda: (
					draw.split_field(col, "Master Controller Widget:", "master_controllers_widget"),
				)),
			))
		))
		draw.draw_section(layout, ["ik_type", "ik_bone_count", "enable_snapping", "enable_ik_stretch", "add_foot_roll", "spline_control_count", "twist_type", "spline_skip_first"], lambda: (
			draw.full_field(layout, "IK Type", "ik_type"),
			draw.box_section(layout, ["ik_bone_count", "enable_snapping", "enable_ik_stretch", "add_foot_roll"], "IK Settings", 'CON_KINEMATIC', lambda col: (
				draw.full_field(col, "IK Bone Count", "ik_bone_count"),
				draw.full_field(col, "Enable Snapping", "enable_snapping"),
				draw.full_field(col, "Enable IK Stretch", "enable_ik_stretch"),
				draw.full_field(col, "Add Foot Roll", "add_foot_roll"),
			)),
			draw.box_section(layout, ["spline_control_count", "twist_type", "spline_skip_first", "spline_skip_last"], "Spline IK Settings", 'CON_SPLINEIK', lambda col: (
				draw.full_field(col, "Spline Control Count", "spline_control_count"),
				draw.split_field(col, "Twist Type", "twist_type"),
				draw.split_row(col, [
					SplitSection(label="Skip First", prop="spline_skip_first"),
					SplitSection(label="Skip Last", prop="spline_skip_last"),
				])
			)),
		))


		def draw_ik_parents(context, box):
			if not draw.do_show("ik_parents"):
				return

			parents = context.window_manager.rig_ik_parents
			col = box.column(align=True)
			for i, parent in enumerate(parents):
				row = col.row(align=True)
				row.prop(parent, "label", text="")
				row.prop_search(parent, "bone", context.object.data, "bones", text="")
				op = row.operator("rig.remove_ik_parent", text="", icon='REMOVE')
				op.index = i
			box.operator("rig.add_ik_parent", text="Add Parent", icon='ADD')

		def draw_ik_control_as_pole_parent(context, box):
			if not draw.do_show("add_ik_control_as_pole_parent"):
				return

			row = box.row(align=True)
			split = row.split(align=True, factor=0.6)
			row = split.row(align=True)
			row.prop(self, "add_ik_control_as_pole_parent")
			if self.add_ik_control_as_pole_parent:
				row = split.row(align=True)
				row.prop(self, "ik_parent_self_parent_label", text="")			

		draw.draw_section(layout, ["ik_parent", "ik_parents", "add_ik_control_as_pole_parent"], lambda: (
			draw.full_field(layout, "Setup IK Parent Switching", "ik_parent"),
			draw.box_section(layout, ["ik_parents", "add_ik_control_as_pole_parent"], "IK Parents", 'CON_ARMATURE', lambda col: (
				draw_ik_parents(context, col),
				draw_ik_control_as_pole_parent(context, col),
			)),
		))

		def draw_twist_status(context, layout):
			if not self.use_twist_bones:
				return

			chains = json.loads(self.dialog_chains_json or "[]")
			if not chains:
				layout.label(text="No chains selected.", icon='ERROR')
				return

			expected = []
			for chain in chains:
				for seg in context.window_manager.rig_twist_segments:
					if 0 <= seg.index < len(chain):
						expected.append((chain[seg.index], self.twist_bone_count))

			snapshot = json.loads(self.dialog_twist_json or "{}")
			status, icon, message = evaluate_twist_snapshot(snapshot, expected)
			if self.assembly_uid and status == TwistChainStatus.OK:
				return

			row = layout.row()
			row.label(text=message, icon=icon)

		def draw_twist_segments(context, box):
			if not draw.do_show("twist_segments"):
				return

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

		draw.draw_section(layout, ["use_twist_bones", "twist_bone_count", "twist_segments"], lambda: (
			draw.full_field(layout, "Use Twist Bones", "use_twist_bones"),
			draw.box_section(layout, ["twist_segments"], "Twist Segments", 'BONE_DATA', lambda col: (
				draw.draw_section(col, ["twist_bone_count"], lambda: (
					draw_twist_status(context, col),
					draw.full_field(col, "Twist Bone Count", "twist_bone_count"),
				)),
				draw.draw_section(col, ["twist_segments"], lambda: (
					draw_twist_segments(context, col),
				)),
			)),
		))

		draw.draw_section(layout, ["add_skirt_collision", "add_skirt_ride", "skirt_legs"], lambda: (
			draw.full_field(layout, "Add Skirt Collision", "add_skirt_collision"),
			draw.full_field(layout, "Add Skirt Ride", "add_skirt_ride"),
			draw.box_section(layout, ["skirt_legs"], "", "NONE", lambda col: (
				draw_skirt_legs(context, col, show_axis=self.add_skirt_ride),
			)),
		))

	##################################################################################################
	# execute
	
	def execute(self, context):
		if not self.limb_property_base_name:
			self.report({'ERROR'}, "Limb property base name is required.")
			self.assembly_uid = ""
			return {'CANCELLED'}

		skirt_slots = list(iter_skirt_leg_slots(context))
		if (self.add_skirt_collision or self.add_skirt_ride) and not skirt_slots:
			self.report({'ERROR'}, "No skirt legs specified. Add leg assemblies or pick thigh bones.")
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

		interval = 0 if self.master_controllers_spacing == 'SINGLE' else self.master_controllers_interval_UI
		options = IKAssemblyOptions(
			limb_property_base_name=self.limb_property_base_name,
			add_tweak_bones=self.add_tweak_bones,
			switch_property_type=self.switch_property_type,
			limb_type=self.limb_type,
			add_rotation_isolation=self.add_rotation_isolation,
			inherit_scale_from_root=self.inherit_scale_from_root,
			override_collections=self.override_collections,
			ik_type=self.ik_type,
			enable_ik_stretch=self.enable_ik_stretch,
			spline_control_count=self.spline_control_count,
			spline_skip_first=self.spline_skip_first,
			spline_skip_last=self.spline_skip_last,
			twist_type=self.twist_type,
			tweak_relationship=self.tweak_relationship,
			fk_widget=self.fk_widget,
			tip_widget=self.tip_widget,
			fk_end_widget=self.fk_end_widget if self.fk_end_widget != "SAME" else self.fk_widget,
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
			add_foot_roll=self.add_foot_roll,
			add_skirt_collision=self.add_skirt_collision,
			skirt_collision_target_bone_names=[slot.thigh for slot in skirt_slots],
			add_skirt_ride=self.add_skirt_ride,
			skirt_ride_legs=[
				SkirtLeg(bone_name=slot.thigh, forward_axis=slot.forward_axis)
				for slot in skirt_slots
			],
			create_master_controllers=self.create_master_controllers,
			master_controllers_interval=interval,
			master_controllers_skip_first=self.master_controllers_skip_first,
			master_controllers_type=self.master_controllers_type,
			master_controllers_widget=self.master_controllers_widget,
		)

	
		assembly_uid = self.assembly_uid

		def rebuild():
			return reconfigure_assembly(
				context, 
				assembly_uid, 
				lambda prior_configs: create_ik_assembly(
					context,
					chains,
					self.template_id,
					self.template_name,
					options,
					replacement_uid=assembly_uid,
					prior_configs=prior_configs,
				),
			)

		try:
			tip_controls = run_assembly_transaction(rebuild)
		except AssemblyTransactionError as e:
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
