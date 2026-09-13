import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty
from dataclasses import dataclass, field
from rigtools.utils.bone import generate_bone_name, duplicate_bone
from rigtools.utils.bone_colors import BONE_COLOR_ITEMS
from rigtools.utils.widget import get_widget_collection, create_circle_widget, create_sphere_widget
from rigtools.preferences import get_preferences
from rigtools.tool.rotation_follow import create_rotation_follow_setup
from rigtools.utils.bone_chain import find_chains_from_selection, ChainBranchingError
from rigtools.tool.fk_tweak_chain import create_tweak_chain_edit_mode, create_tweak_chain_pose_mode, FKTweakChain, TweakChainOptions

###############################################################################################
# Functions for finding bone chains

def is_ancestor_selected(bone, selected_set):
	parent = bone.parent
	while parent:
		if parent in selected_set:
			return True
		parent = parent.parent
	return False

def find_hierarchy_chains(context):
	selected_bones = set(context.selected_editable_bones)
	if not selected_bones:
		return []
	
	heads = [
		bone for bone in selected_bones
		if not is_ancestor_selected(bone, selected_bones)
	]
	chains = []
	
	def walk_hierarchy(current_bone, current_chain):
		current_chain.append(current_bone.name)
		children = current_bone.children
		
		if len(children) > 1:
			raise ChainBranchingError(
				f"Branching detected at bone '{current_bone.name}'. Use selection mode and select a linear chain."
			)
		elif len(children) == 0:
			chains.append(current_chain)
			return
		
		walk_hierarchy(children[0], current_chain)
		
	for head in heads:
		walk_hierarchy(head, [])
		
	return chains

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

	do_create_fk_widgets: bpy.props.BoolProperty(
		name="Create FK Widgets",
		description="Create widgets for the FK bones",
		default=True
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
		
		bone_data = obj.data
		
		# Switch to edit mode
		original_mode = obj.mode
		if obj.mode != 'EDIT':
			bpy.ops.object.mode_set(mode='EDIT')
			
		if not context.selected_editable_bones:
			self.report({'ERROR'}, "No edit bones selected. Select at least one bone chain.")
			bpy.ops.object.mode_set(mode=original_mode)
			return {'CANCELLED'}                    

		# Find all of the indivual bone chains
		try:
			if self.bone_selection == 'SELECTED':
				chains = find_chains_from_selection(context)
			else:
				chains = find_hierarchy_chains(context)                
		except ChainBranchingError as e:
			self.report({'ERROR'}, str(e))
			bpy.ops.object.mode_set(mode=original_mode)
			return {'CANCELLED'}
		
		options = TweakChainOptions(
			fk_bone_template = self.fk_bone_template,
			skip_first_tweak = self.skip_first_tweak,
			do_create_fk = self.do_create_fk,
			do_create_fk_widgets = self.do_create_fk_widgets,
			fk_collection_name = self.fk_collection_name if self.override_collections else None,
			tweak_collection_name = self.tweak_collection_name if self.override_collections else None,
		)

		processed_chains: list[FKTweakChain] = []
		for chain in chains:
			processed_chains.append(create_tweak_chain_edit_mode(bone_data, chain, options))
			
		bpy.ops.object.mode_set(mode='POSE')
		for chain in processed_chains:
			create_tweak_chain_pose_mode(context, obj, chain, options)

		if self.create_rotation_follow_setup:
			for chain in processed_chains:
				create_rotation_follow_setup(context, 
					chain.fk_bones[self.rotation_follow_skip:], 
					self.rotation_follow_relationship
				)
				
		bpy.ops.ed.undo_push(message="Create FK Tweak Chain")
		
		chain_count = len(processed_chains)

		self.report({'INFO'}, f"Successfully generated {chain_count} FK/Tweak chain{'s' if chain_count != 1 else ''}.")
			
		return {'FINISHED'}

	def invoke(self, context, event):
		prefs = get_preferences()

		if not props.is_property_set("fk_bone_template"):
			self.fk_bone_template = prefs.fk_template

		return context.window_manager.invoke_props_dialog(self, width=350)

	def draw(self, context):
		layout = self.layout
		box = layout.box()
		box.label(text="FK Tweak Chain Settings:", icon='SETTINGS')

		col = box.column()
		col.prop(self, "do_create_fk")
		if self.do_create_fk:
			col.prop(self, "do_create_fk_widgets")
			col.prop(self, "fk_bone_template")

		col.separator()
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