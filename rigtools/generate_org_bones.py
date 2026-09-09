import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty, CollectionProperty, IntProperty
from rigtools.utils.bone import is_bone_visible, generate_bone_name, get_base_name, bone_name_matches, duplicate_bone
from rigtools.preferences import get_preferences, get_separators

class RIG_OT_generate_org_bones(bpy.types.Operator):
    """Create missing ORG bones from DEF bones and link them. Safe to run multiple times for the entire armature."""
    bl_idname = "rig.generate_org_bones"
    bl_label = "Generate ORG Bones"
    bl_options = {'REGISTER', 'UNDO'}

    # Properties for the popup
    def_bone_name: StringProperty(
        name="DEF Bone Name",
        description="Template using {name} as placeholder. L/R suffixes will be preserved.",
        default="DEF-{name}"
    )
    
    target_bone_name: StringProperty(
        name="Target Bone Name", 
        description="Template using {name} as placeholder. L/R suffixes will be preserved.",
        default="ORG-{name}"
    )

    target_bone_collection: StringProperty(
        name="Target Bone Collection",
        description="Name of collection to create target bones in, leave blank to copy from DEF bone. Will not move existing bones.",
        default="ORG"
    )
    
    relationship_type: EnumProperty(
        name="Relationship Type",
        description="How to connect DEF bones to target bones",
        items=[
            ('COPY_TRANSFORMS', 'Copy Transforms', 'Use copy transform constraints'),
            ('PARENT', 'Parent/Child', 'Make DEF bone child of target bone')
        ],
        default='COPY_TRANSFORMS'
    )
    
    bone_selection: EnumProperty(
        name="Bone Selection",
        description="Which bones to process",
        items=[
            ('SELECTED', 'Selected Bones', 'Only process selected DEF bones'),
            ('VISIBLE', 'Visible Bones', 'Process all visible DEF bones'),
            ('ALL', 'All Bones', 'Process all DEF bones in armature')
        ],
        default='SELECTED'
    )

    disable_control_deform: BoolProperty(
        name="Disable To Bone Deform",
        description="Disable deformation on to-bones",
        default=True
    )

    def create_bones(self, context, pairs):
        edit_bones = context.object.data.edit_bones

        created_bones = []
        existing = 0

        if self.target_bone_collection:
            colls = context.object.data.collections
            collection = colls.get(self.target_bone_collection) or colls.new(self.target_bone_collection)
        else:
            collection = None

        for def_name, target_name in pairs:
            def_bone = edit_bones[def_name]
            if target_name not in edit_bones:
                target_bone = duplicate_bone(context.object.data, def_bone, target_name, 1.0, collection == None)
                if collection:
                    collection.assign(target_bone)
                created_bones.append(target_bone.name)
            else:
                target_bone = edit_bones[target_name]
                existing += 1

            if self.disable_control_deform:
                target_bone.use_deform = False

        lookup = dict(pairs)
        # Create proper bone hierarchy for newly created bones
        for def_name, target_name in pairs:
            if target_name not in created_bones:
                # Don't update existing bones
                continue

            def_bone = edit_bones[def_name]
            target_bone = edit_bones[target_name]

            parent = def_bone.parent
            if not parent:
                target_bone.parent = None
            elif parent.name in lookup:
                target_bone.parent = edit_bones[lookup[parent.name]]
                target_bone.use_connect = def_bone.use_connect
            else:
                prefix, suffix = self.get_affixes()
                base_name = self.get_def_base_name(parent.name, prefix, suffix)
                inferred = generate_bone_name(base_name, self.target_bone_name, strip_name=False)
                if inferred in edit_bones:
                    target_bone.parent = edit_bones[inferred]
                else:
                    target_bone.parent = parent
                target_bone.use_connect = def_bone.use_connect

        # Apply the relationship type to all bone pairs (new and existing)
        if self.relationship_type == 'PARENT':
            for def_name, target_name in pairs:
                def_bone = edit_bones[def_name]
                target_bone = edit_bones[target_name]
                def_bone.use_connect = False
                def_bone.parent = target_bone

        return existing

    def apply_constraints(self, context, pairs):
        bpy.ops.object.mode_set(mode='POSE')
        pose_bones = context.object.pose.bones
        for def_name, target_name in pairs:
            def_bone = pose_bones[def_name]
            existing_constraints = [c for c in def_bone.constraints if c.type == 'COPY_TRANSFORMS' and c.subtarget == target_name]
            
            if not existing_constraints:
                constraint = def_bone.constraints.new('COPY_TRANSFORMS')
                constraint.target = context.object
                constraint.subtarget = target_name

    def get_affixes(self):
        separators = tuple(get_separators())
        if '{name}' in self.def_bone_name:
            fixes = self.def_bone_name.split('{name}')
            prefix = fixes[0]
            suffix = fixes[1]
        elif self.def_bone_name.startswith(separators):
            # If it starts with a separator, we'll treat it as a suffix
            prefix = ''
            suffix = self.def_bone_name
        else:
            # Anything else, we'll treat as a prefix
            prefix = self.def_bone_name
            suffix = ''
        return prefix, suffix

    def get_def_base_name(self, def_name, prefix, suffix):
        core_base_name, extension = get_base_name(def_name)
        end = -len(suffix) if suffix else None
        base_name = core_base_name[len(prefix):end]
        return base_name + extension

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'ARMATURE':
            self.report({'ERROR'}, "Active object must be an armature.")
            return {'CANCELLED'}
        
        if obj.mode == 'OBJECT' and self.bone_selection == 'SELECTED':
            self.report({'WARNING'}, f"Can't use 'Selected Bones' from Object mode")
            return {'CANCELLED'}

        bone_data = obj.data
        prefix, suffix = self.get_affixes()
        original_mode = obj.mode

        all_bones = bone_data.bones
        if obj.mode == 'EDIT':
            all_bones = bone_data.edit_bones

        # Find all the bones within selection mode scope
        if self.bone_selection == 'SELECTED':
            if obj.mode == 'EDIT':
                scope_bones = [bone.name for bone in context.selected_editable_bones]
            else: # POSE
                scope_bones = [b.name for b in context.selected_pose_bones]
        elif self.bone_selection == 'VISIBLE':
            scope_bones = [b.name for b in all_bones if is_bone_visible(b)]
        else:  # ALL
            scope_bones = [b.name for b in all_bones]

        # Find the DEF bones within the scope
        def_bones = [b for b in scope_bones if bone_name_matches(b, prefix, suffix)]

        if not def_bones:
            self.report({'WARNING'}, f"No bones found with name matching '{self.def_bone_name}'")
            if obj.mode != original_mode:
                bpy.ops.object.mode_set(mode=original_mode)
            return {'CANCELLED'}

        if obj.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')

        pairs = []

        for def_bone in def_bones:
            # Extract target bone name by removing DEF prefix and adding target prefix
            base_name = self.get_def_base_name(def_bone, prefix, suffix)
            target_name = generate_bone_name(base_name, self.target_bone_name, strip_name=False)

            pairs.append((def_bone, target_name))

        existing = self.create_bones(context, pairs)
        if self.relationship_type == 'COPY_TRANSFORMS':
            self.apply_constraints(context, pairs)

        if obj.mode != original_mode:
            bpy.ops.object.mode_set(mode=original_mode)

        created = len(pairs) - existing

        self.report({'INFO'}, f"Created {created} new target bones. {existing} pairs updated.")            
        return {'FINISHED'}

    def invoke(self, context, event):
        prefs = get_preferences(context)
        props = self.properties

        if not props.is_property_set("def_bone_name"):
            self.def_bone_name = prefs.def_template
        if not props.is_property_set("target_bone_name"):
            self.target_bone_name = prefs.org_template
        if not props.is_property_set("target_bone_collection"):
            self.target_bone_collection = prefs.org_collection
        
        return context.window_manager.invoke_props_dialog(self, width=450)

    def draw(self, context):
        layout = self.layout

        # Settings dialog
        # Documentation section
        box = layout.box()
        box.label(text="Documentation:", icon='INFO')
        col = box.column()
        col.label(text="Creates new target (ORG) bones from DEF bones and sets up relationships between them.")
        col.label(text="This tool will not duplicate existing target bones.")
        col.label(text="If a target already exists, the tool will create the appropriate relationship, but will not update the collection assignment.")
        col = box.column()
        col.label(text="It is safe to run this tool multiple times for the entire armature, as long as the naming conventions are followed.")
        
        # Settings section
        box = layout.box()
        box.label(text="Settings:", icon='SETTINGS')
        
        col = box.column()
        col.prop(self, "bone_selection")
        col.prop(self, "def_bone_name")
        col.prop(self, "target_bone_name")
        col.prop(self, "target_bone_collection")
        col.prop(self, "relationship_type")

classes = (
    RIG_OT_generate_org_bones,
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
    
    bpy.ops.rig.generate_org_bones('INVOKE_DEFAULT')