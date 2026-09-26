import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty, IntProperty, CollectionProperty
from rigtools.armature_settings import get_armature_settings
from rigtools.tool.spline_ik import spline_twist_type
from rigtools.utils.widget import fk_widget_types
from rigtools.tool.ik_parent import IKParentTarget
from rigtools.utils.bone_chain import get_assembly_chains
from rigtools.assemblies.ik_assembly import IKAssemblyOptions, create_ik_assembly

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
		default=True
	)
	
	##################################################################################################
	# execute
	
	def execute(self, context):
		if not self.limb_property_base_name:
			self.report({'ERROR'}, "Limb property base name is required.")
			return {'CANCELLED'}

		try:
			chains, original_mode = get_assembly_chains(context)
		except Exception as e:
			self.report({'ERROR'}, str(e))
			return {'CANCELLED'}

		for chain in chains:
			if len(chain) == 1:
				self.report({'ERROR'}, "All chains must have at least 2 bones.")
				bpy.ops.object.mode_set(mode=original_mode)
				return {'CANCELLED'}

		options = IKAssemblyOptions(
			limb_property_base_name=self.limb_property_base_name,
			add_tweak_bones=self.add_tweak_bones,
			switch_property_type=self.switch_property_type,
			add_rotation_isolation=self.add_rotation_isolation,
			override_collections=self.override_collections,
			ik_type=self.ik_type,
			enable_ik_stretch=self.enable_ik_stretch,
			pole_distance=self.pole_distance,
			spline_control_count=self.control_count,
			spline_skip_first=self.skip_first,
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
		)

		try:
			create_ik_assembly(context, chains, options)
		except Exception as e:
			self.report({'ERROR'}, str(e))
			bpy.ops.object.mode_set(mode=original_mode)
			return {'CANCELLED'}

		# If everything succeeds, we leave it in Pose mode so the user can see the result

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