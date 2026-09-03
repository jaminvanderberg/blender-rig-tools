import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty, CollectionProperty, IntProperty

class RIG_PG_def_result(bpy.types.PropertyGroup):
    def_bone: StringProperty()
    control_bone: StringProperty()
    message: StringProperty()
    icon: StringProperty(default='NONE')
    
class RIG_UL_def_results(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row()
        row.label(text=f"{item.def_bone} > {item.control_bone} - {item.message}", icon=item.icon)
        #if item.message:
            #ow.label(text=item.message)
            
def is_bone_visible(bone):
    if bone.hide:
        return False
    if not bone.collections:
        return True
    return any(coll.is_visible for coll in bone.collections)

class RIG_OT_setup_def_constraints(bpy.types.Operator):
    """Setup relationships between bones based on prefix"""
    bl_idname = "rig.setup_def_constraints"
    bl_label = "Pair Bones"
    bl_icon = "CON_TRANSLIKE"
    bl_options = {'REGISTER', 'UNDO'}

    # Properties for the popup
    def_prefix: StringProperty(
        name="From Bone Prefix",
        description="Prefix for deformation bones (e.g., 'DEF-')",
        default="DEF-"
    )
    
    control_prefix: StringProperty(
        name="To Bone Prefix", 
        description="Prefix for control bones (e.g., 'ORG-', 'MCH-', or leave empty)",
        default="ORG-"
    )
    
    relationship_type: EnumProperty(
        name="Relationship Type",
        description="How to connect DEF bones to control bones",
        items=[
            ('COPY_TRANSFORMS', 'Copy Transforms', 'Use copy transform constraints'),
            ('PARENT', 'Parent/Child', 'Make DEF bone child of control bone')
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
    
    remove_control_constraints: BoolProperty(
        name="Remove Control Bone Constraints",
        description="Remove all constraints from control bones",
        default=True
    )
    
    disable_control_deform: BoolProperty(
        name="Disable Control Bone Deform",
        description="Disable deformation on control bones",
        default=True
    )
    
    show_details: BoolProperty(name="Details", default=False)

    report_ready: BoolProperty(options={'HIDDEN', 'SKIP_SAVE'})
    
    result_rows: CollectionProperty(type=RIG_PG_def_result)
    result_index: IntProperty()    

    def execute(self, context):
        # Prevent re-running after showing the results dialog
        if self.report_ready:
            return {'FINISHED'}
        
        obj = context.object
        if not obj or obj.type != 'ARMATURE':
            self.report({'ERROR'}, "Active object must be an armature.")
            return {'CANCELLED'}
        
        if obj.mode == 'OBJECT' and self.bone_selection == 'SELECTED':
            self.report({'WARNING'}, f"Can't use 'Selected Bones' from Object mode")
            return {'CANCELLED'}        


        bone_data = obj.data
        pose_bones = obj.pose.bones
        
        # For parenting bones, we need to be in edit mode
        original_mode = obj.mode
        if self.relationship_type == 'PARENT' and obj.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')

        all_bones = bone_data.bones
        if obj.mode == 'EDIT':
            all_bones = bone_data.edit_bones

        # Find DEF bones based on selection mode
        if self.bone_selection == 'SELECTED':
            if obj.mode == 'EDIT':
                def_bones = [b for b in context.selected_editable_bones if b.name.startswith(self.def_prefix)]
            else: # POSE
                def_bones = [b for b in context.selected_pose_bones if b.name.startswith(self.def_prefix)]
        elif self.bone_selection == 'VISIBLE':
            # Only visible DEF bones
            def_bones = [b for b in all_bones if b.name.startswith(self.def_prefix) and is_bone_visible(b)]
        else:  # ALL
            # All DEF bones in armature
            def_bones = [b for b in all_bones if b.name.startswith(self.def_prefix)]
        
        if not def_bones:
            self.report({'WARNING'}, f"No bones found with prefix '{self.def_prefix}'")
            if obj.mode != original_mode:
                bpy.ops.object.mode_set(mode=original_mode)
            return {'CANCELLED'}

        results = []
        success_count = 0
        skipped_count = 0
        missing_controls = []

        for def_bone in def_bones:
            # Extract control bone name by removing DEF prefix and adding control prefix
            def_name = def_bone.name
            base_name = def_name[len(self.def_prefix):]
            control_name = self.control_prefix + base_name if self.control_prefix else base_name
            
            result = {
                'def_bone': def_name,
                'control_bone': control_name,
                'found': False,
                'action': 'skipped'
            }
            
            # Check if control bone exists
            if control_name not in all_bones:
                result['message'] = f"Control bone '{control_name}' not found"
                missing_controls.append(control_name)
                results.append(result)
                skipped_count += 1
                continue
            
            result['found'] = True
            control_bone = all_bones[control_name]
            def_pose = pose_bones[def_name]
            control_pose = pose_bones[control_name]

            # Handle control bone setup
            if self.remove_control_constraints:
                constraints_removed = len(control_pose.constraints)
                for c in control_pose.constraints[:]:  # Copy list to avoid modification during iteration
                    control_pose.constraints.remove(c)
                result['constraints_removed'] = constraints_removed

            if self.disable_control_deform:
                control_bone.use_deform = False
                result['deform_disabled'] = True

            # Setup relationship
            if self.relationship_type == 'COPY_TRANSFORMS':
                # Check if constraint already exists
                existing_constraints = [c for c in def_pose.constraints if c.type == 'COPY_TRANSFORMS' and c.subtarget == control_name]
                
                if existing_constraints:
                    result['action'] = 'skipped'
                    result['message'] = f"Constraint already exists"
                    skipped_count += 1
                else:
                    constraint = def_pose.constraints.new('COPY_TRANSFORMS')
                    constraint.target = obj
                    constraint.subtarget = control_name
                    result['action'] = 'constraint_added'
                    result['message'] = f"Constraint added"
                    success_count += 1
                    
            elif self.relationship_type == 'PARENT':
                # Check if already parented
                if def_bone.parent and def_bone.parent.name == control_name:
                    result['action'] = 'skipped'
                    result['message'] = f"Already parented"
                    skipped_count += 1
                else:
                    # Set the parent (we already checked we're in Edit Mode)
                    edit_bones = obj.data.edit_bones
                    def_edit_bone = edit_bones[def_name]
                    control_edit_bone = edit_bones[control_name]
                    
                    def_edit_bone.parent = control_edit_bone
                    result['action'] = 'parented'
                    result['message'] = "Parented"
                    success_count += 1

            results.append(result)

        # Show user report in UI
        self.missing_bones = missing_controls
        self.success_count = success_count
        self.skipped_count = skipped_count
        
        self.result_rows.clear()
        for result in results:
            item = self.result_rows.add()
            item.def_bone = result['def_bone']
            item.control_bone = result['control_bone']
            item.message = result.get('message', '')
            if not result['found']:
                item.icon = 'ERROR'
            elif result['action'] == 'skipped':
                item.icon = "CHECKBOX_DEHLT"
            else:
                item.icon = "CHECKMARK"
            
        self.report_ready = True
                            
        if obj.mode != original_mode:
            bpy.ops.object.mode_set(mode=original_mode)            
            
        return context.window_manager.invoke_props_dialog(self, width=500)


    def invoke(self, context, event):
        report_ready = False
        return context.window_manager.invoke_props_dialog(self, width=450)

    def draw(self, context):
        layout = self.layout
        
        # Check if this is a results dialog (missing bones found)
        if self.report_ready:
            # Results dialog
            box = layout.box()
            box.label(text="Setup Results:", icon='INFO')
            col = box.column()
            col.label(text=f"Success: {self.success_count}", icon="CHECKBOX_HLT")
            col.label(text=f"Skipped: {self.skipped_count}", icon="CHECKBOX_DEHLT")
            if self.missing_bones:
                col.label(text=f"Missing: {len(self.missing_bones)}", icon="ERROR")
            
                layout.separator()
            
                # Missing bones section
                box = layout.box()
                box.label(text="Missing Control Bones:", icon='ERROR')
                col = box.column()
                col.label(text="The following control bones were not found:")
                col.label(text="")
                
                # Show missing bones in a scrollable list
                for missing in self.missing_bones:
                    col.label(text=f"• {missing}")
                
                col.label(text="")
                col.label(text="Please create these control bones or check your naming convention.")
                
            layout.separator()
            row = layout.row()
            row.alignment = 'LEFT'
            row.use_property_split = False
            row.prop(self,"show_details", icon='TRIA_DOWN' if self.show_details else 'TRIA_RIGHT', emboss=False)
            
            if self.show_details:
                layout.template_list("RIG_UL_def_results", "", self, "result_rows", self, "result_index",
                    rows=4, maxrows=16)
   
                
        else:
            # Settings dialog
            # Documentation section
            box = layout.box()
            box.label(text="Documentation:", icon='INFO')
            col = box.column()
            col.label(text="This tool sets up relationships between bones.")
            col.label(text="From-bones get the constraint, or become childen of To-bones.")
            col.label(text="Bones must have matching names, but with different prefixes.")
            
            # Settings section
            box = layout.box()
            box.label(text="Settings:", icon='SETTINGS')
            
            col = box.column()
            col.prop(self, "bone_selection")
            col.prop(self, "def_prefix")
            col.prop(self, "control_prefix")
            col.prop(self, "relationship_type")
            
            col.separator()
            col.prop(self, "remove_control_constraints")
            col.prop(self, "disable_control_deform")
            
            # Preview section
            box = layout.box()
            box.label(text="Preview:", icon='VIEWZOOM')
            col = box.column()
            col.label(text=f"From bone: '{self.def_prefix}Arm'")
            col.label(text=f"To bone: '{self.control_prefix}Arm'")
            if self.relationship_type == 'COPY_TRANSFORMS':
                col.label(text=f"{self.def_prefix}Arm will receive a Copy Transform constraint targeting {self.control_prefix}Arm")
            else:
                col.label(text=f"{self.def_prefix}Arm will become a child of {self.control_prefix}Arm")

classes = (
    RIG_PG_def_result,
    RIG_UL_def_results,
    RIG_OT_setup_def_constraints,
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
    
    bpy.ops.rig.setup_def_constraints('INVOKE_DEFAULT')