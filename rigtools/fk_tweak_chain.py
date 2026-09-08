import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty
from dataclasses import dataclass, field
from rigtools.utils.bone import generate_bone_name, duplicate_bone
from rigtools.utils.widget import get_widget_collection, create_circle_widget, create_sphere_widget

class ChainBranchingError(Exception):
    """Creates FK/Tweak chain from an existing bone chain."""
    pass

@dataclass
class FKTweakChain:
    name: str
    original_bones: list[str] = field(default_factory=list)
    fk_bones: list[str] = field(default_factory=list)
    tweak_bones: list[str] = field(default_factory=list)
    terminal_tweak: str = ""
    bone_lengths: dict[str, float] = field(default_factory=dict)
    
BONE_COLOR_ITEMS = [
    ('THEME01', "01 - Theme Color Set", "01 - Theme Color Set", 'COLORSET_01_VEC', 1),
    ('THEME02', "02 - Theme Color Set", "02 - Theme Color Set", 'COLORSET_02_VEC', 2),
    ('THEME03', "03 - Theme Color Set", "03 - Theme Color Set", 'COLORSET_03_VEC', 3),
    ('THEME04', "04 - Theme Color Set", "04 - Theme Color Set", 'COLORSET_04_VEC', 4),
    ('THEME05', "05 - Theme Color Set", "05 - Theme Color Set", 'COLORSET_05_VEC', 5),
    ('THEME06', "06 - Theme Color Set", "06 - Theme Color Set", 'COLORSET_06_VEC', 6),
    ('THEME07', "07 - Theme Color Set", "07 - Theme Color Set", 'COLORSET_07_VEC', 7),
    ('THEME08', "08 - Theme Color Set", "08 - Theme Color Set", 'COLORSET_08_VEC', 8),
    ('THEME09', "09 - Theme Color Set", "09 - Theme Color Set", 'COLORSET_09_VEC', 9),
    ('THEME10', "10 - Theme Color Set", "10 - Theme Color Set", 'COLORSET_10_VEC', 10),
    ('THEME11', "11 - Theme Color Set", "11 - Theme Color Set", 'COLORSET_11_VEC', 11),
    ('THEME12', "12 - Theme Color Set", "12 - Theme Color Set", 'COLORSET_12_VEC', 12),
    ('THEME13', "13 - Theme Color Set", "13 - Theme Color Set", 'COLORSET_13_VEC', 13),
    ('THEME14', "14 - Theme Color Set", "14 - Theme Color Set", 'COLORSET_14_VEC', 14),
    ('THEME15', "15 - Theme Color Set", "15 - Theme Color Set", 'COLORSET_15_VEC', 15),
    ('THEME16', "16 - Theme Color Set", "16 - Theme Color Set", 'COLORSET_16_VEC', 16),
    ('THEME17', "17 - Theme Color Set", "17 - Theme Color Set", 'COLORSET_17_VEC', 17),
    ('THEME18', "18 - Theme Color Set", "18 - Theme Color Set", 'COLORSET_18_VEC', 18),
    ('THEME19', "19 - Theme Color Set", "19 - Theme Color Set", 'COLORSET_19_VEC', 19),
    ('THEME20', "20 - Theme Color Set", "20 - Theme Color Set", 'COLORSET_20_VEC', 20),
]   
    
###############################################################################################
# Functions for finding bone chains
    
def find_chains_from_selection(context):
    selected_bones = set(context.selected_editable_bones)
    if not selected_bones:
        return []
    
    heads = [
        bone for bone in selected_bones
        if bone.parent is None or bone.parent not in selected_bones
    ]
    chains = []
    
    def walk_chain(current_bone, current_chain):
        current_chain.append(current_bone.name)
        selected_children = [c for c in current_bone.children if c in selected_bones]
        
        if len(selected_children) > 1:
            raise ChainBranchingError(
                f"Branching detected at bone '{current_bone.name}'. All bones must have only one selected child."
            )
        elif len(selected_children) == 0:
            chains.append(current_chain)
            return

        walk_chain(selected_children[0], current_chain)
        
    for head in heads:
        walk_chain(head, [])
        
    return chains

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

    fk_bone_name: StringProperty(
        name="FK bone name", 
        description="Template using {name} as a placeholder (e.g., 'FK-{name}' or '{name}_FK'). L/R suffixes will be preserved.",
        default="FK-{name}"
    )
    
    fk_bone_color: EnumProperty(
        name="FK Bone Color",
        description="Select theme color palette for generated FK controls",
        items=BONE_COLOR_ITEMS,
        default='THEME04'  # Blue as default for FK controls
    )

    tweak_bone_name: StringProperty(
        name="Tweak bone name", 
        description="Template using {name} as a placeholder (e.g., '{name}.tweak' or 'TWEAK_{name}'). L/R suffixes will be preserved.",
        default="{name}.tweak"
    )
    
    term_bone_name: StringProperty(
        name="Terminal bone name",
        description="Template using {name} as a placeholder (e.g., '{name}.tip.tweak' or 'TWEAK-{name}.tip'). L/R suffixes will be preserved.",
        default="{name}.tip.tweak"
    )
    
    tweak_bone_color: EnumProperty(
        name="Tweak Bone Color",
        description="Select theme color palette for generated tweak controls",
        items=BONE_COLOR_ITEMS,
        default='THEME09'  # Yellow as default for tweak controls
    )
    
    do_create_fk_widgets: bpy.props.BoolProperty(
        name="Create FK Widgets",
        description="Create widgets for the FK bones",
        default=True
    )

    do_create_tweak_widgets: bpy.props.BoolProperty(
        name="Create Widgets",
        description="Create widgets for the tweak bones",
        default=True
    )
    
    widget_collection: bpy.props.StringProperty(
        name="Widget Collection Name",
        description="Name of collection for widgets",
        default="WGT"
    )

    widget_name: StringProperty(
        name="Widget Object Name",
        description="Template using {name} as a placeholder (e.g., 'WGT-{name}' or '{name}.widget'). L/R suffixes will be preserved.",
        default="WGT-{name}"
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


    fk_scale_factor: bpy.props.FloatProperty(
        name="FK Scale Factor",
        description="Percentage of average chain length for tweak bones",
        default=0.90,
        min=0.05,
        max=2.0
    ) 
        
    tweak_scale_factor: bpy.props.FloatProperty(
        name="Tweak Scale Factor",
        description="Percentage of average chain length for tweak bones",
        default=0.25,
        min=0.05,
        max=2.0
    )
    
    ################################################################################################
    # Bone generation functions

    def create_tweak_chain(self, armature_data, chain_bone_names) -> FKTweakChain :
        chain_name = generate_bone_name(chain_bone_names[0], "{name}")
        chain = FKTweakChain(
            name = chain_name,
            original_bones = chain_bone_names
        )
        
        edit_bones = armature_data.edit_bones
        
        total_length = sum(edit_bones[name].length for name in chain_bone_names)
        avg_length = total_length / len(chain_bone_names)
        tweak_length = avg_length * self.tweak_scale_factor
        
        last_parent = edit_bones[chain_bone_names[0]].parent
        
        for bone_name in chain_bone_names:
            org_bone = edit_bones[bone_name]
            chain.bone_lengths[bone_name] = org_bone.length

            if self.do_create_fk:
                fk_name = generate_bone_name(bone_name, self.fk_bone_name)
                fk_bone = duplicate_bone(armature_data, org_bone, fk_name, self.fk_scale_factor)
                fk_bone.parent = last_parent

                chain.fk_bones.append(fk_bone.name)
            
                last_parent = fk_bone
            
            tweak_name = generate_bone_name(bone_name, self.tweak_bone_name)
            tweak_bone = duplicate_bone(armature_data, org_bone, tweak_name, 1)
            tweak_bone.length = tweak_length
            
            if self.do_create_fk:
                tweak_bone.parent = fk_bone
            else:
                tweak_bone.parent = last_parent
                last_parent = tweak_bone
            
            chain.tweak_bones.append(tweak_bone.name)
            
        # Create terminal (tip) tweak bone            
        last_org_bone = edit_bones[chain_bone_names[-1]]
        term_name = generate_bone_name(chain_bone_names[-1], self.term_bone_name)
        term_bone = edit_bones.new(term_name)
        if self.do_create_fk:
            term_bone.parent = last_parent

        for coll in last_org_bone.collections:
            coll.assign(term_bone)
        
        term_bone.head = last_org_bone.tail
        direction = (last_org_bone.tail - last_org_bone.head).normalized()
        term_bone.tail = last_org_bone.tail + (direction * tweak_length)
        term_bone.roll = last_org_bone.roll
        
        chain.terminal_tweak = term_bone.name
        
        # Parent ORG bones to Tweak
        for org_name, tweak_name in zip(chain_bone_names, chain.tweak_bones):
            org_bone = edit_bones[org_name]
            tweak_bone = edit_bones[tweak_name]
            org_bone.use_connect = False
            org_bone.parent = tweak_bone
            
        # Children of the last bone need to be children of the terminal tweak bone instead
        last_children = [c for c in last_org_bone.children if c.name not in chain_bone_names]
        for child in last_children:
            child.use_connect = False
            child.parent = term_bone
            
        return chain
    
    def setup_constraints(self, obj, chain: FKTweakChain):
        pose_bones = obj.pose.bones

        # Targets for original bones: [T1, T2, T3, ..., T_END]
        targets = chain.tweak_bones[1:] + [chain.terminal_tweak]

        for orig_name, target_tweak in zip(chain.original_bones, targets):
            pbone = pose_bones[orig_name]

            c_name = "Stretch To Tweak"
            constraint = pbone.constraints.get(c_name)
            if not constraint:
                constraint = pbone.constraints.new(type='STRETCH_TO')
                constraint.name = c_name

            constraint.target = obj
            constraint.subtarget = target_tweak
            constraint.volume = 'VOLUME_XZX'
            constraint.rest_length = chain.bone_lengths[orig_name]
            
    def setup_colors(self, obj, chain: FKTweakChain):
        pose_bones = obj.pose.bones
        tweakers = chain.tweak_bones + [chain.terminal_tweak]
        
        for fk_name in chain.fk_bones:
            fk_bone = pose_bones[fk_name]
            fk_bone.color.palette = self.fk_bone_color
            
        for tweak_name in tweakers:
            tweak_bone = pose_bones[tweak_name]
            tweak_bone.color.palette = self.tweak_bone_color
            
    def setup_widgets(self, obj, context, chain: FKTweakChain):
        pose_bones = obj.pose.bones
        tweakers = chain.tweak_bones + [chain.terminal_tweak]
        
        coll = get_widget_collection(context, self.widget_collection)

        if self.do_create_fk_widgets:
            for fk_name in chain.fk_bones:
                fk_bone = pose_bones[fk_name]
                widget_name = generate_bone_name(fk_name, self.widget_name)
                wgt = create_circle_widget(widget_name, coll)
                fk_bone.custom_shape = wgt
            
        if self.do_create_tweak_widgets:
            for tweak_name in tweakers:
                tweak_bone = pose_bones[tweak_name]
                tweak_bone.color.palette = self.tweak_bone_color
                widget_name = generate_bone_name(tweak_name, self.widget_name)
                wgt = create_sphere_widget(widget_name, coll)
                tweak_bone.custom_shape = wgt

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
        
        processed_chains: list[FKTweakChain] = []
        for chain in chains:
            processed_chains.append(self.create_tweak_chain(bone_data, chain))
            
        bpy.ops.object.mode_set(mode='POSE')
        for chain in processed_chains:
            self.setup_constraints(obj, chain)
            self.setup_colors(obj, chain)
            if self.do_create_fk_widgets or self.do_create_tweak_widgets:
                self.setup_widgets(obj, context, chain)
                
        bpy.ops.ed.undo_push(message="Create FK Tweak Chain")
        
        chain_count = len(processed_chains)

        self.report({'INFO'}, f"Successfully generated {chain_count} FK/Tweak chain{'s' if chain_count != 1 else ''}.")
            
        return {'FINISHED'}

    def invoke(self, context, event):
        report_ready = False
        return context.window_manager.invoke_props_dialog(self, width=450)

    def draw(self, context):
        layout = self.layout

        # Settings dialog
        # Documentation section
        box = layout.box()
        box.label(text="Documentation:", icon='INFO')
        col = box.column()
        col.label(text="Creates FK/Tweak chain from an existing bone chain.")
        col.label(text="Chains must be linear (one child per parent), but don't need to be connected.")
        
        # Settings section
        box = layout.box()
        box.label(text="Settings:", icon='SETTINGS')
        
        col = box.column()
        col.prop(self, "do_create_fk")
        col.prop(self, "fk_bone_name")
        col.prop(self, "fk_bone_color")
        col.prop(self, "fk_scale_factor")
        col = box.column()
        col = box.column()
        col = box.column()
        col.prop(self, "tweak_bone_name")
        col.prop(self, "term_bone_name")
        col.prop(self, "tweak_bone_color")
        col.prop(self, "tweak_scale_factor")
        col = box.column()
        col = box.column()
        col = box.column()
        col.prop(self, "do_create_fk_widgets")
        col.prop(self, "do_create_tweak_widgets")
        col.prop(self, "widget_collection")
        col.prop(self, "widget_name")

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