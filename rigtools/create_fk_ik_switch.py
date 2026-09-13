import bpy
from rigtools.utils.bone import set_bone_collection
from rigtools.tool.fk_ik_switch import create_fk_ik_switch_edit_mode, create_fk_ik_switch_pose_mode
from rigtools.utils.bone_chain import find_chains_from_selection
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty, IntProperty
from rigtools.preferences import get_preferences
from rigtools.utils.bone_colors import BONE_COLOR_ITEMS
from rigtools.tool.fk_tweak_chain import create_tweak_chain_edit_mode, create_tweak_chain_pose_mode, FKTweakChain, TweakChainOptions
from rigtools.armature_settings import get_armature_settings
from rigtools.tool.standard_ik import StandardIKOptions, create_standard_ik_edit_mode, create_standard_ik_pose_mode
from rigtools.tool.spline_ik import SplineIKOptions, create_spline_ik_edit_mode, create_spline_ik_object_mode, create_spline_ik_pose_mode

class RIG_OT_create_fk_ik_switch(bpy.types.Operator):
	"""Create a FK/IK switch for the selected bone chains."""
	bl_idname = "rig.create_fk_ik_switch"
	bl_label = "Create FK/IK Switch"
	bl_options = {'REGISTER', 'UNDO'}
	bl_property = "switch_property_name"

	# FK/Tweak Settings

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
	
	switch_property_name: StringProperty(
		name="Switch Property Name",
		description="Name of the property to switch the FK/IK",
		default=""
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
		name="Skip First",
		description="Skip the first bone in the chain for the IK spline",
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

		if not self.switch_property_name:
			self.report({'ERROR'}, "Switch property name is required.")
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
			do_create_fk_widgets = False,
			tweak_collection_name = self.tweak_collection_name if self.override_collections else None,
			fk_collection_name = "" # These are the switch bones
		)

		ik_options = StandardIKOptions(
			enable_ik_stretch = self.enable_ik_stretch,
			pole_distance = self.pole_distance,
			ik_collection_name = self.ik_collection_name if self.override_collections else None
		)

		spline_options = SplineIKOptions(
			control_count = self.control_count,
			skip_first = self.skip_first,
			ik_collection_name = self.ik_collection_name if self.override_collections else None
		)

		created_chains = []
		created_tweak_chains = []
		created_ik_chains = []
		created_ik_chains_with_spline = []
		for chain in chains:
			org_chain = chain
			if self.add_tweak_bones:
				tweak_chain = create_tweak_chain_edit_mode(bone_data, chain, options)
				chain = tweak_chain.fk_bones
				created_tweak_chains.append(tweak_chain)

			fk_bone_names, ik_bone_names = create_fk_ik_switch_edit_mode(context, chain, name_source = org_chain)
			created_chains.append((chain, fk_bone_names, ik_bone_names))

			if self.override_collections and self.fk_collection_name:
				for bone_name in fk_bone_names:
					bone = bone_data.edit_bones[bone_name]
					set_bone_collection(bone_data, bone, self.fk_collection_name)

			if self.ik_type == 'IK':
				ik_chain = create_standard_ik_edit_mode(context, ik_bone_names, ik_options, name_source=org_chain)
				created_ik_chains.append(ik_chain)
			elif self.ik_type == 'SPLINE':
				ik_chain = create_spline_ik_edit_mode(context, ik_bone_names, spline_options, name_source=org_chain)
				created_ik_chains.append(ik_chain)

		if self.ik_type == 'SPLINE':
			for ik_chain in created_ik_chains:
				spline_chain = create_spline_ik_object_mode(context, ik_chain, spline_options)
				created_ik_chains_with_spline.append(spline_chain)

		for tweak_chain in created_tweak_chains:
			create_tweak_chain_pose_mode(context, obj, tweak_chain, options)

		for chain, fk_bone_names, ik_bone_names in created_chains:
			create_fk_ik_switch_pose_mode(context, chain, fk_bone_names, ik_bone_names, self.switch_property_name)

		if self.ik_type == 'IK':
			for ik_chain in created_ik_chains:
				create_standard_ik_pose_mode(context, ik_chain, ik_options)
		
		if self.ik_type == 'SPLINE':
			for ik_chain in created_ik_chains_with_spline:
				create_spline_ik_pose_mode(context, ik_chain, spline_options)

		# Leave it in pose mode so the user can test the rig
		#bpy.ops.object.mode_set(mode=original_mode)
		
		self.report({'INFO'}, f"Successfully generated {len(chains)} FK/IK switch chain{'s' if len(chains) != 1 else ''}.")              
			
		return {'FINISHED'}

	def invoke(self, context, event):
		prefs = get_preferences(context)
		props = self.properties

		return context.window_manager.invoke_props_dialog(self, width=350)

	def draw(self, context):
		layout = self.layout
		box = layout.box()
		box.label(text="IK/FK Switch Settings:", icon='SETTINGS')

		col = box.column()
		col.prop(self, "switch_property_name")
		col.prop(self, "add_tweak_bones")

		layout.separator()
		
		col = layout.column()
		col.prop(self, "ik_type")
		box = layout.box()
		if self.ik_type == 'SPLINE':
			box.label(text="Spline IK Settings:", icon='CON_SPLINEIK')
			col = box.column()
			col.prop(self, "control_count")
			col.prop(self, "skip_first")
		elif self.ik_type == 'IK':
			box.label(text="IK Settings:", icon='CON_KINEMATIC')
			col = box.column()
			col.prop(self, "enable_ik_stretch")
			col.prop(self, "pole_distance")

		layout.separator()
		layout.prop(self, "override_collections",
			icon='DOWNARROW_HLT' if self.override_collections else 'RIGHTARROW',
			toggle = True
		)
		if self.override_collections:
			col = layout.column()
			col.prop(self, "fk_collection_name")
			col.prop(self, "ik_collection_name")
			if self.add_tweak_bones:
				col.prop(self, "tweak_collection_name")

classes = (
	RIG_OT_create_fk_ik_switch,
)

def register():
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
	
	bpy.ops.rig.create_fk_ik_switch()