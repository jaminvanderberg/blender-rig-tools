import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty
from rigtools.rig_ui.property_name import guess_limb_name
from rigtools.utils.widget import fk_widget_types
from rigtools.preferences import get_preferences
from rigtools.utils.bone_chain import find_chains_from_selection, find_hierarchy_chains, ChainBranchingError, get_assembly_chains
from rigtools.armature_settings import get_armature_settings
from rigtools.assemblies.fk_assembly import FKAssemblyOptions, create_fk_assembly

###########################################################################################################        

class RIG_OT_advanced_fk_tweak_setup(bpy.types.Operator):
	"""Setup FK/Tweak setup with advanced options"""
	bl_idname = "rig.advanced_fk_setup"
	bl_label = "Advanced FK Setup"
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
	
	skip_first_tweak: bpy.props.BoolProperty(
		name="Skip First Tweak",
		description="Skip the first tweak bone",
		default=False
	)

	fk_widget: bpy.props.EnumProperty(
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

	create_rotation_follow_setup: bpy.props.BoolProperty(
		name="Create Rotation Follow Setup",
		description="Create a rotation follow setup along the FK chain.",
		default=True
	)

	rotation_follow_skip: bpy.props.IntProperty(
		name="Rotation Follow Skip",
		description="Number of bones to skip before creating a rotation follow setup.",
		default=1
	)

	rotation_follow_relationship: bpy.props.EnumProperty(
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
	##################################################################################################
	# execute
	
	def execute(self, context):
		if self.add_rotation_isolation and not self.limb_property_base_name:
			self.report({'ERROR'}, "Limb property base name is required for rotation isolation.")
			return {'CANCELLED'}

		try:
			chains, original_mode = get_assembly_chains(context, check_property_bone=self.add_rotation_isolation)
		except Exception as e:
			self.report({'ERROR'}, str(e))
			return {'CANCELLED'}

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
			create_fk_assembly(context, chains, options)
		except Exception as e:
			self.report({'ERROR'}, str(e))
			bpy.ops.object.mode_set(mode=original_mode)
			return {'CANCELLED'}

		chain_count = len(chains)
		self.report({'INFO'}, f"Successfully generated {chain_count} FK/Tweak chain{'s' if chain_count != 1 else ''}.")
		return {'FINISHED'}

	def invoke(self, context, event):
		prefs = get_preferences()
		props = self.properties		

		if not props.is_property_set("fk_bone_template"):
			self.fk_bone_template = prefs.fk_template

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

		return context.window_manager.invoke_props_dialog(self, width=350)

	def draw(self, context):
		layout = self.layout
		box = layout.box()
		box.label(text="FK Tweak Chain Settings:", icon='SETTINGS')
		settings = get_armature_settings(context.object.data, context)

		split_size = 0.4

		col = box.column()
		split = col.split(align=True, factor=split_size)
		row = split.row(align=True)
		row.label(text="Limb Property Base Name:", translate=False)
		row = split.row(align=True)
		row.prop(self, "limb_property_base_name", text="")

		col.prop(self, "do_create_fk")
		if self.do_create_fk:
			if settings.do_create_widgets:
				split = col.split(align=True, factor=split_size)
				row = split.row(align=True)
				row.label(text="FK Widget:", translate=False)
				row = split.row(align=True)
				row.prop(self, "fk_widget", text="")	
			split = col.split(align=True, factor=split_size)
			row = split.row(align=True)
			row.label(text="FK Bone Template:", translate=False)
			row = split.row(align=True)
			row.prop(self, "fk_bone_template", text="")

		col.separator()
		col = box.column(align=True)
		split = col.split(align=True, factor=split_size)
		row = split.row(align=True)
		row.label(text="Tweak Relationship:", translate=False)
		row = split.row(align=True)
		row.prop(self, "tweak_relationship", text="")
		col.prop(self, "skip_first_tweak")

		if self.do_create_fk:
			layout.separator()
			col = layout.column()
			col.prop(self, "add_rotation_isolation")
			col.prop(self, "create_rotation_follow_setup")
			if self.create_rotation_follow_setup:
				box = layout.box()
				box.label(text="Rotation Follow Setup:", icon='CONSTRAINT')
				col = box.column()
				col.prop(self, "rotation_follow_skip")
				col.prop(self, "rotation_follow_relationship")


classes = (
	RIG_OT_advanced_fk_tweak_setup,
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
	
	bpy.ops.rig.advanced_fk_tweak_setup('INVOKE_DEFAULT')