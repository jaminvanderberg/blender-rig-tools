import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty
from dataclasses import dataclass, field
import re
import math

class ChainBranchingError(Exception):
    """Custom exception raised on branching bone chain"""
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
# Functions for bone creation

def generate_bone_name(org_name, strip_prefix, strip_suffix, template):
    name = org_name
    
    symmetry_pattern = r'(\.[LR]|\_[LR])(\.\d+)?$'
    match = re.search(symmetry_pattern, name, re.IGNORECASE)
    
    if match:
        base_name = name[:match.start()]
        extension = match.group(0)
    else:
        base_name = name
        extension = ""
        
    if strip_prefix and base_name.startswith(strip_prefix):
        base_name = base_name[len(strip_prefix):]
        
    if strip_suffix and base_name.endswith(strip_suffix):
        base_name = base_name[:-len(strip_suffix)]
        
    if "{name}" not in template:
        # Gentle fallback behavior for when {name} is missing.
        # If it starts with a separator, assume the used just mean a suffix
        separators = ('.', '_', '-')
        if template.startswith(separators):
            template = f"{{name}}{template}"
        else:
            # Otherwise, we just assume it's a prefix.
            # empty string template will just return the same bone name,
            # which is probably fine
            template = f"{template}{{name}}"
            
    formatted_base = template.format(name=base_name)
    
    return f"{formatted_base}{extension}"

###########################################################################################################
# Widget creation

def get_widget_collection(context, collection_name):
    coll = bpy.data.collections.get(collection_name)
    if not coll:
        coll = bpy.data.collections.new(collection_name)
        context.scene.collection.children.link(coll)
        coll.hide_viewport = True
        coll.hide_render = True
    return coll

def create_sphere_widget(widget_name, collection):    
    verts = []
    edges = []
    segments = 12
    
    for axis in ['XY', 'XZ', 'YZ']:
        start_idx = len(verts)
        for i in range(segments):
            angle = (2 * math.pi * i) / segments
            cos_a = math.cos(angle) * 0.5
            sin_a = math.sin(angle) * 0.5
            
            match axis:
                case 'XY':
                    verts.append((cos_a, sin_a, 0.0))
                case 'XZ':
                    verts.append((cos_a, 0.0, sin_a))
                case 'YZ':
                    verts.append((0.0, cos_a, sin_a))
                    
            next_i = (i + 1) % segments
            edges.append((start_idx + i, start_idx + next_i))
            
    mesh = bpy.data.meshes.new(widget_name)
    mesh.from_pydata(verts, edges, [])
    mesh.update()
    
    wgt = bpy.data.objects.new(widget_name, mesh)
    collection.objects.link(wgt)
    
    return wgt

def create_circle_widget(widget_name, collection):
    verts = []
    edges = []
    segments = 16
    
    for i in range(segments):
        angle = (2 * math.pi * i) / segments
        verts.append((math.cos(angle) * 0.5, 0.0, math.sin(angle) * 0.5))
        edges.append((i, (i + 1) % segments))
        
    mesh = bpy.data.meshes.new(widget_name)
    mesh.from_pydata(verts, edges, [])
    mesh.update()
    
    wgt = bpy.data.objects.new(widget_name, mesh)
    collection.objects.link(wgt)
    return wgt

###########################################################################################################        

class RIG_OT_create_fk_tweak_chain(bpy.types.Operator):
    """Setup relationships between bones based on prefix"""
    bl_idname = "rig.create_fk_tweak_chain"
    bl_label = "Create FK Tweak Chain"
    bl_options = {'REGISTER', 'UNDO'}

    # Properties for the popup
    org_prefix: StringProperty(
        name="Strip prefix",
        description="Prefix to remove from original bones (e.g., 'ORG-' or 'DEF_')",
        default="ORG-"
    )

    org_suffix: StringProperty(
        name="Strip suffix",
        description="Suffix to remove from original bones (e.g., 'ORG-' or 'DEF_')",
        default=""
    )

    fk_bone_name: StringProperty(
        name="FK bone name", 
        description="Template using {name} as a placeholder (e.g., 'FK-{name}' or '{name}_FK'). L/R suffixes will be preserved.",
        default="FK-{name}"
    )
    
    fk_bone_color: bpy.props.EnumProperty(
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
    
    tweak_bone_color: bpy.props.EnumProperty(
        name="Tweak Bone Color",
        description="Select theme color palette for generated tweak controls",
        items=BONE_COLOR_ITEMS,
        default='THEME09'  # Yellow as default for tweak controls
    )
    
    do_create_widgets: bpy.props.BoolProperty(
        name="Create Widgets",
        description="Create widgets for FK and tweak bones",
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
        default=0.60,
        min=0.05,
        max=1.0
    ) 
        
    tweak_scale_factor: bpy.props.FloatProperty(
        name="Tweak Scale Factor",
        description="Percentage of average chain length for tweak bones",
        default=0.25,
        min=0.05,
        max=1.0
    )
    
    ################################################################################################
    # Bone generation functions

    def create_tweak_chain(self, armature_data, chain_bone_names) -> FKTweakChain :
        chain_name = generate_bone_name(chain_bone_names[0], self.org_prefix, self.org_suffix, "{name}")
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
            direction = (org_bone.tail - org_bone.head).normalized()
            chain.bone_lengths[bone_name] = org_bone.length
            
            fk_name = generate_bone_name(bone_name, self.org_prefix, self.org_suffix, self.fk_bone_name)
            fk_bone = edit_bones.new(fk_name)
            fk_bone.parent = last_parent
            
            fk_bone.head = org_bone.head
            fk_bone.tail = org_bone.head + (direction * org_bone.length * self.fk_scale_factor)
            fk_bone.roll = org_bone.roll
            
            chain.fk_bones.append(fk_bone.name)
            
            last_parent = fk_bone
            
            tweak_name = generate_bone_name(bone_name, self.org_prefix, self.org_suffix, self.tweak_bone_name)
            tweak_bone = edit_bones.new(tweak_name)
            tweak_bone.parent = fk_bone
            
            tweak_bone.head = org_bone.head
                        
            tweak_bone.tail = org_bone.head + (direction * tweak_length)
            tweak_bone.roll = org_bone.roll
            
            chain.tweak_bones.append(tweak_bone.name)
            
        # Create terminal (tip) tweak bone            
        last_org_bone = edit_bones[chain_bone_names[-1]]
        term_name = generate_bone_name(chain_bone_names[-1], self.org_prefix, self.org_suffix, self.term_bone_name)
        term_bone = edit_bones.new(term_name)
        term_bone.parent = last_parent
        
        term_bone.head = last_org_bone.tail
        direction = (last_org_bone.tail - last_org_bone.head).normalized()
        term_bone.tail = last_org_bone.tail + (direction * tweak_length)
        term_bone.roll = last_org_bone.roll
        
        chain.terminal_tweak = term_bone.name
        
        # Parent ORG bones to Tweak
        for org_name, tweak_name in zip(chain_bone_names, chain.tweak_bones):
            org_bone = edit_bones[org_name]
            tweak_bone = edit_bones[tweak_name]
            org_bone.parent = tweak_bone
            org_bone.use_connect = False
            
        # Children of the last bone need to be children of the terminal tweak bone instead
        last_children = [c for c in last_org_bone.children if c.name not in chain_bone_names]
        for child in last_children:
            child.parent = term_bone
            child.use_connect = False
            
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
                
        for fk_name in chain.fk_bones:
            fk_bone = pose_bones[fk_name]
            widget_name = generate_bone_name(fk_name, self.org_prefix, self.org_suffix, self.widget_name)
            wgt = create_circle_widget(widget_name, coll)
            fk_bone.custom_shape = wgt
            
        for tweak_name in tweakers:
            tweak_bone = pose_bones[tweak_name]
            tweak_bone.color.palette = self.tweak_bone_color
            widget_name = generate_bone_name(tweak_name, self.org_prefix, self.org_suffix, self.widget_name)
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
        pose_bones = obj.pose.bones
        
        # Switch to edit mode
        original_mode = obj.mode
        if obj.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')
            
        if not context.selected_editable_bones:
            self.report({'ERROR'}, "No edit bones selected. Select at least one bone chain.")
            bpy.ops.object.mode_set(mode=original_mode)
            return {'CANCELLED'}                    

        all_bones = bone_data.edit_bones
        
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
            if self.do_create_widgets:
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
        col.prop(self, "bone_selection")
        col.prop(self, "org_prefix")
        col.prop(self, "org_suffix")
        col = box.column()
        col = box.column()
        col = box.column()
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
        col.prop(self, "do_create_widgets")
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