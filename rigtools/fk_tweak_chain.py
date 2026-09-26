import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty
from rigtools.utils.widget import fk_widget_types
from rigtools.preferences import get_preferences
from rigtools.tool.rotation_follow import RotationFollow
from rigtools.utils.bone_chain import find_chains_from_selection, find_hierarchy_chains, ChainBranchingError, get_assembly_chains
from rigtools.tool.fk_tweak_chain import FKTweakChain
from rigtools.armature_settings import get_armature_settings

###########################################################################################################        

class RIG_OT_create_fk_tweak_chain(bpy.types.Operator):
	"""Setup relationships between bones based on prefix"""
	bl_idname = "rig.create_fk_tweak_chain"
	bl_label = "Create FK Tweak Chain"
	bl_options = {'REGISTER', 'UNDO'}

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
		name="Create FK Widgets",
		description="Create widgets for the FK bones",
		items=fk_widget_types,
		default='CIRCLE'
	)

	override_collections: BoolProperty(
		name="Override Bone Collections",
		description="Specify the bone collections for various bone types",
		default=True
	)
	
	bone_selection: EnumProperty(
		name="Bone Selection",
		description="Which bones to process",
		items=[
			('SELECTED', 'Selected Bones', 'Only process selected bones'),
			('HIERARCHY', 'Hierarchy', 'Include all bones until end of chain'),
		],
		default='SELECTED'
	)   

	create_rotation_follow_setup: bpy.props.BoolProperty(
		name="Create Rotation Follow Setup",
		description="Create a rotation follow setup along the FK chain.",
		default=False
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

		try:
			chains, original_mode = get_assembly_chains(context)
		except Exception as e:
			self.report({'ERROR'}, str(e))
			return {'CANCELLED'}

		

				
		bpy.ops.ed.undo_push(message="Create FK Tweak Chain")
		
		chain_count = len(processed_chains)

		self.report({'INFO'}, f"Successfully generated {chain_count} FK/Tweak chain{'s' if chain_count != 1 else ''}.")
			
		return {'FINISHED'}

	def invoke(self, context, event):
		prefs = get_preferences()
		props = self.properties		

		if not props.is_property_set("fk_bone_template"):
			self.fk_bone_template = prefs.fk_template

		return context.window_manager.invoke_props_dialog(self, width=350)

	def draw(self, context):
		layout = self.layout
		box = layout.box()
		box.label(text="FK Tweak Chain Settings:", icon='SETTINGS')
		settings = get_armature_settings(context.object.data, context)

		col = box.column()
		col.prop(self, "do_create_fk")
		if self.do_create_fk:
			if settings.do_create_widgets:
				col.prop(self, "fk_widget")	
			col.prop(self, "fk_bone_template")

		col.separator()
		col.prop(self, "tweak_relationship")
		col.prop(self, "skip_first_tweak")

		layout.separator()
		col = layout.column()
		col.prop(self, "create_rotation_follow_setup")
		if self.create_rotation_follow_setup:
			box = layout.box()
			box.label(text="Rotation Follow Setup:", icon='CONSTRAINT')
			col = box.column()
			col.prop(self, "rotation_follow_skip")
			col.prop(self, "rotation_follow_relationship")

		layout.separator()
		col = layout.column()
		col.prop(self, "override_collections",
			icon='DOWNARROW_HLT' if self.override_collections else 'RIGHTARROW',
			toggle = True
		)
		if self.override_collections:
			col = layout.column()
			if self.do_create_fk:
				col.prop(self, "fk_collection_name")
			col.prop(self, "tweak_collection_name")


classes = (
	RIG_OT_create_fk_tweak_chain,
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
	
	bpy.ops.rig.create_fk_tweak_chain('INVOKE_DEFAULT')