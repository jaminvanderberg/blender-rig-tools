import bpy
from rigtools.utils.bone import set_bone_collection
from rigtools.tool.fk_ik_switch import create_fk_ik_switch_edit_mode, create_fk_ik_switch_pose_mode
from rigtools.utils.bone_chain import find_chains_from_selection
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty, IntProperty, CollectionProperty
from rigtools.preferences import get_preferences
from rigtools.utils.bone_colors import BONE_COLOR_ITEMS
from rigtools.tool.fk_tweak_chain import create_tweak_chain_edit_mode, create_tweak_chain_pose_mode, FKTweakChain, TweakChainOptions
from rigtools.armature_settings import get_armature_settings
from rigtools.tool.standard_ik import StandardIKOptions, create_standard_ik_edit_mode, create_standard_ik_pose_mode
from rigtools.tool.spline_ik import SplineIKOptions, create_spline_ik_edit_mode, create_spline_ik_object_mode, create_spline_ik_pose_mode, spline_twist_type
from rigtools.utils.widget import fk_widget_types
from rigtools.rig_ui.snapping_panel import register_snap_chain
from rigtools.tool.ik_parent import IKParentOptions, IKParentTarget, create_ik_parent_edit_mode, create_ik_parent_pose_mode
from rigtools.utils.property import generate_property_name
from rigtools.utils.bone import find_side

class IKParentSlot(bpy.types.PropertyGroup):
	label: bpy.props.StringProperty(name="Label", default="")
	bone: bpy.props.StringProperty(name="Bone", default="")

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

class RIG_OT_create_fk_ik_switch(bpy.types.Operator):
	"""Create a FK/IK switch for the selected bone chains."""
	bl_idname = "rig.create_fk_ik_switch"
	bl_label = "Create FK/IK Switch"
	bl_options = {'REGISTER', 'UNDO'}
	bl_property = "switch_property_name"

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

	fk_collection_name: StringProperty(
		name="FK Collection Name",
		description="Name of the collection to store the FK bones, or blank to copy collection from selected bones",
		default=""
	)

	ik_collection_name: StringProperty(
		name="IK Collection Name",
		description="Name of the collection to store the IK bones, or blank to copy collection from selected bones",
		default=""
	)

	tweak_collection_name: StringProperty(
		name="Tweak Collection Name",
		description="Name of the collection to store the tweak bones, or blank to copy collection from selected bones",
		default=""
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

	control_count: IntProperty(
		name="Control Count",
		description="Number of controls to create for the spline IK",
		default=3,
		min=2,
		max=10
	)

	skip_first: BoolProperty(
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
		default=False
	)
	
	##################################################################################################
	# execute
	
	def execute(self, context):
	
		obj = context.object
		if not obj or obj.type != 'ARMATURE':
			self.report({'ERROR'}, "Active object must be an armature.")
			return {'CANCELLED'}
		
		if obj.mode == 'OBJECT':
			self.report({'ERROR'}, f"Can't use from Object mode")
			return {'CANCELLED'}

		if not self.limb_property_base_name:
			self.report({'ERROR'}, "Limb property base name is required.")
			return {'CANCELLED'}

		settings = get_armature_settings(obj.data, context)
		prefs = get_preferences()
		if settings.property_bone_name not in obj.pose.bones:
			self.report({'ERROR'}, f"Property bone '{settings.property_bone_name}' not found.")
			return {'CANCELLED'}

		bone_data = obj.data
		
		# Switch to edit mode
		original_mode = obj.mode
		if obj.mode != 'EDIT':
			bpy.ops.object.mode_set(mode='EDIT')
			
		if not context.selected_editable_bones:
			self.report({'ERROR'}, "No edit bones selected. Select at least one bone.")
			bpy.ops.object.mode_set(mode=original_mode)
			return {'CANCELLED'}

		bone_data = obj.data
		
		# Find all of the indivual bone chains
		try:
			chains = find_chains_from_selection(context)
		except Exception as e:
			self.report({'ERROR'}, str(e))
			bpy.ops.object.mode_set(mode=original_mode)
			return {'CANCELLED'}

		for chain in chains:
			if len(chain) == 1:
				self.report({'ERROR'}, "All chains must have at least 2 bones.")
				bpy.ops.object.mode_set(mode=original_mode)
				return {'CANCELLED'}

		options = TweakChainOptions(
			fk_bone_template = prefs.switch_template,
			skip_first_tweak = False,
			do_create_fk = True,
			fk_widget = "None",
			tweak_collection_name = self.tweak_collection_name if self.override_collections else None,
			fk_collection_name = "", # These are the switch bones
			tweak_relationship = self.tweak_relationship,
		)

		ik_options = StandardIKOptions(
			enable_ik_stretch = self.enable_ik_stretch,
			pole_distance = self.pole_distance,
			ik_collection_name = self.ik_collection_name if self.override_collections else None,
			enable_snapping = self.enable_snapping
		)

		spline_options = SplineIKOptions(
			control_count = self.control_count,
			skip_first = self.skip_first,
			ik_collection_name = self.ik_collection_name if self.override_collections else None,
			twist_type = self.twist_type
		)

		created_chains = []
		created_tweak_chains = []
		created_ik_chains = []
		created_ik_chains_with_spline = []
		created_ik_parents = []
		chain_sides = []
		##############
		# Edit mode
		##############
		for chain in chains:
			org_chain = chain
			try:
				chain_sides.append(find_side(chain))
			except ValueError as e:
				self.report({'ERROR'}, str(e))
				bpy.ops.object.mode_set(mode=original_mode)
				return {'CANCELLED'}

			if self.add_tweak_bones:
				tweak_chain = create_tweak_chain_edit_mode(bone_data, chain, options)
				chain = tweak_chain.fk_bones
				created_tweak_chains.append(tweak_chain)

			fk_bone_names, ik_bone_names = create_fk_ik_switch_edit_mode(context, chain, name_source = org_chain)
			created_chains.append((chain, fk_bone_names, ik_bone_names))

			if self.ik_type == 'IK':
				ik_chain = create_standard_ik_edit_mode(context, ik_bone_names, fk_bone_names, ik_options, name_source=org_chain)
				created_ik_chains.append(ik_chain)

				if self.enable_snapping:
					register_snap_chain(obj.data, 
						switch_property=self.switch_property_name,
						fk_bones=fk_bone_names,
						ik_mch_bones=ik_bone_names, 
						ik_control=ik_chain.ik_control_name, 
						ik_pole=ik_chain.pole_name, 
						snap_control=ik_chain.snap_control_name, 
						snap_pole=ik_chain.snap_pole_name, 
						context=context)
			elif self.ik_type == 'SPLINE':
				ik_chain = create_spline_ik_edit_mode(context, ik_bone_names, spline_options, name_source=org_chain)
				created_ik_chains.append(ik_chain)

			if self.ik_parent:
				if self.ik_type == 'IK':
					bones_to_parent = [ik_chain.ik_control_name, ik_chain.pole_name]
					self_target = ik_chain.ik_control_name
				else: #SPLINE
					bones_to_parent = ik_chain.control_names
					self_target = ik_chain.control_names[0]
				parent_bone_names = create_ik_parent_edit_mode(context, bones_to_parent)
				created_ik_parents.append((parent_bone_names, self_target))

			# Bone collections
			# This is done last, so they don't get copied
			if prefs.mch_collection_name and self.add_tweak_bones:
				# chain is the switch bones
				for bone_name in chain:
					bone = bone_data.edit_bones[bone_name]
					set_bone_collection(bone_data, bone, prefs.mch_collection_name)

			if self.override_collections and self.fk_collection_name:
				# these are the final FK bones
				for bone_name in fk_bone_names:
					bone = bone_data.edit_bones[bone_name]
					set_bone_collection(bone_data, bone, self.fk_collection_name)

			if prefs.mch_collection_name:
				# these are the MCH-IK bones
				for bone_name in ik_bone_names:
					bone = bone_data.edit_bones[bone_name]
					set_bone_collection(bone_data, bone, prefs.mch_collection_name)

		##############
		# Object mode
		##############
		if self.ik_type == 'SPLINE':
			for ik_chain in created_ik_chains:
				spline_chain = create_spline_ik_object_mode(context, ik_chain, spline_options)
				created_ik_chains_with_spline.append(spline_chain)

		##############
		# Pose mode
		##############
		for tweak_chain in created_tweak_chains:
			create_tweak_chain_pose_mode(context, obj, tweak_chain, options)

		for (chain, fk_bone_names, ik_bone_names), side in zip(created_chains, chain_sides, strict=True):
			switch_property_name = generate_property_name(prefs.switch_template, self.limb_property_base_name, side)
			create_fk_ik_switch_pose_mode(context, chain, fk_bone_names, ik_bone_names,
				switch_property_name, self.switch_property_type, self.fk_widget)

		if self.ik_type == 'IK':
			for ik_chain in created_ik_chains:
				create_standard_ik_pose_mode(context, ik_chain, ik_options)
		
		if self.ik_type == 'SPLINE':
			for ik_chain in created_ik_chains_with_spline:
				create_spline_ik_pose_mode(context, ik_chain, spline_options)

		if self.ik_parent:
			for (parent_bone_names, self_target), side in zip(created_ik_parents, chain_sides, strict=True):
				ik_parent_property_name = generate_property_name(prefs.ik_parent_template, self.limb_property_base_name, side)
				options = IKParentOptions(
					property_name=ik_parent_property_name,
					parents=[
						IKParentTarget(label=s.label, bone=s.bone)
						for s in context.window_manager.rig_ik_parents
						if s.bone
					],
					self_parent_mch = (
						parent_bone_names[1] # pole parent
						if self.ik_type == 'IK' and self.add_ik_control_as_pole_parent 
						else None
					),
					self_parent_name = self_target,
					self_parent_label = self.ik_parent_self_parent_label
				)
				create_ik_parent_pose_mode(context, parent_bone_names, options)

		# Leave it in pose mode so the user can test the rig
		#bpy.ops.object.mode_set(mode=original_mode)
		
		self.report({'INFO'}, f"Successfully generated {len(chains)} FK/IK switch chain{'s' if len(chains) != 1 else ''}.")              
			
		return {'FINISHED'}

	def invoke(self, context, event):
		wm = context.window_manager
		if len(wm.rig_ik_parents) == 0:
			settings = get_armature_settings(context.object.data, context)
			root = wm.rig_ik_parents.add()
			root.label, root.bone = "Root", settings.root_bone_name
			torso = wm.rig_ik_parents.add()
			torso.label, torso.bone = "Torso", settings.torso_bone_name

		return context.window_manager.invoke_props_dialog(self, width=350)

	def draw(self, context):
		layout = self.layout
		split_size = 0.4

		box = layout.box()
		box.label(text="IK/FK Switch Settings:", icon='SETTINGS')

		col = box.column()
		split = col.split(align=True, factor=split_size)
		row = split.row(align=True)
		row.label(text="Limb Property Base Name:", translate=False)
		row = split.row(align=True)
		row.prop(self, "limb_property_base_name", text="")

		split = col.split(align=True, factor=split_size)
		row = split.row(align=True)
		row.label(text="Switch Property Type:", translate=False)
		row = split.row(align=True)
		row.prop(self, "switch_property_type", text="")

		col.separator()

		col = layout.column()
		col.prop(self, "add_rotation_isolation")

		split = col.split(align=True, factor=split_size)
		row = split.row(align=True)
		row.label(text="FK Widget:", translate=False)
		row = split.row(align=True)
		row.prop(self, "fk_widget", text="")

		col.separator()
		col.prop(self, "add_tweak_bones")

		if self.add_tweak_bones:
			split = col.split(align=True, factor=split_size)
			row = split.row(align=True)
			row.label(text="Tweak Relationship:", translate=False)
			row = split.row(align=True)
			row.prop(self, "tweak_relationship", text="")

		layout.separator()
		
		col = layout.column()
		col.prop(self, "ik_type")
		box = layout.box()
		if self.ik_type == 'SPLINE':
			box.label(text="Spline IK Settings:", icon='CON_SPLINEIK')
			col = box.column()
			col.prop(self, "control_count")

			split = col.split(align=True, factor=split_size)
			row = split.row(align=True)
			row.label(text="Twist Controllers:", translate=False)
			row = split.row(align=True)
			row.prop(self, "twist_type", text="")

			col.prop(self, "skip_first")
		elif self.ik_type == 'IK':
			box.label(text="IK Settings:", icon='CON_KINEMATIC')
			col = box.column()
			col.prop(self, "enable_snapping")
			col.prop(self, "enable_ik_stretch")
			col.prop(self, "pole_distance")

		layout.separator()
		col = layout.column(align=True)
		col.prop(self, "ik_parent")
		if self.ik_parent:
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

		layout.separator()
		box = layout.box()

		col = box.column(align=True)

		split = col.split(align=True, factor=split_size)
		row = split.row(align=True)
		row.label(text="FK Collection Name:", translate=False)
		row = split.row(align=True)
		row.prop(self, "fk_collection_name", text="")

		split = col.split(align=True, factor=split_size)
		row = split.row(align=True)
		row.label(text="IK Collection Name:", translate=False)
		row = split.row(align=True)
		row.prop(self, "ik_collection_name", text="")

		if self.add_tweak_bones:
			split = col.split(align=True, factor=split_size)
			row = split.row(align=True)
			row.label(text="Tweak Collection Name:", translate=False)
			row = split.row(align=True)
			row.prop(self, "tweak_collection_name", text="")

classes = (
	IKParentSlot,
	RIG_OT_add_ik_parent,
	RIG_OT_remove_ik_parent,
	RIG_OT_create_fk_ik_switch,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)

	bpy.types.WindowManager.rig_ik_parents = CollectionProperty(type=IKParentSlot)
	bpy.types.WindowManager.rig_ik_parent_index = IntProperty()

def unregister():
	del bpy.types.WindowManager.rig_ik_parents
	del bpy.types.WindowManager.rig_ik_parent_index

	for cls in classes:
		bpy.utils.unregister_class(cls)
	
if __name__ == "__main__":
	try:
		unregister()
	except Exception:
		pass
	register()
	
	bpy.ops.rig.create_fk_ik_switch()