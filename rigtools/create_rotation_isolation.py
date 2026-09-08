import bpy
from rigtools.utils.bone import generate_bone_name
from bpy.props import StringProperty, BoolProperty
import mathutils
from rna_prop_ui import rna_idprop_ui_create

class RIG_OT_create_rotation_isolation(bpy.types.Operator):
    """Create a isolate rotation mechanism for the selected bone and drive it by a custom property."""
    bl_idname = "rig.create_rotation_isolation"
    bl_label = "Create Rotation Isolation Mechanism"
    bl_options = {'REGISTER', 'UNDO'}
    bl_property = "property_name"

    property_name: StringProperty(
        name = "Property Name",
        default = "",
        description = "Name of the custom property driving the rotation isolation mechanism."
    )
    root_bone_name: bpy.props.StringProperty(
        name = "Root Bone",
        default = "root",
        description = "Name of parent bone for intermediate isolation bone."
    )
    socket_bone_name: StringProperty(
        name="Socket bone name", 
        description="Template using {name} as a placeholder (e.g., 'MCH-{name}' or 'MCH_{name}_socket'). L/R suffixes will be preserved.",
        default="MCH-SOCKET-{name}"
    )
    int_bone_name: StringProperty(
        name="Intermediate bone name", 
        description="Template using {name} as a placeholder (e.g., 'MCH-INT-{name}' or 'MCH_{name}_int'). L/R suffixes will be preserved.",
        default="MCH-INT-{name}"
    )
    property_bone_name: StringProperty(
        name = "Property Bone",
        default = "properties",
        description = "Name of the bone to hold the custom property."
    )
    include_scale: BoolProperty(
        name = "Copy Scale",
        default = True,
        description = "Create a copy scale constraint."
    )
    disable_scale: BoolProperty(
        name = "Disable Scale",
        default = False,
        description = "Leave the copy scale constraint disabled."
    )    
    
    ################################################################################################
    # Bone generation functions

    def create_bones(self, context, armature_data, selection):
        created_bones = []

        root_bone = armature_data.edit_bones.get(self.root_bone_name)

        bpy.ops.armature.select_all(action='DESELECT')

        for bone in selection:
            socket_name = generate_bone_name(bone.name, self.socket_bone_name)
            socket_bone = armature_data.edit_bones.new(socket_name)

            socket_bone.head = bone.head.copy()
            socket_bone.tail = socket_bone.head + mathutils.Vector((0.0, 0.0, bone.length * 0.5))
            socket_bone.roll = 0.0
            socket_bone.parent = bone.parent

            int_name = generate_bone_name(bone.name, self.int_bone_name)
            int_bone = armature_data.edit_bones.new(int_name)

            int_bone.head = bone.head.copy()
            int_bone.tail = socket_bone.tail
            int_bone.length = bone.length * 0.4
            int_bone.roll = 0.0

            int_bone.parent = root_bone

            bone.use_connect = False
            bone.parent = int_bone

            for coll in bone.collections:
                coll.assign(socket_bone)
                coll.assign(int_bone)

            created_bones.append((socket_bone.name, int_bone.name))
        return created_bones
    
    def setup_constraints(self, obj, bone_list):
        prop_bone = obj.pose.bones.get(self.property_bone_name)
        prop_name = self.property_name

        if prop_name not in prop_bone:
            prop_bone[prop_name] = 1.0
            
            rna_idprop_ui_create(
                prop_bone,
                prop_name,
                default=1.0,
                min=0.0,
                max=1.0
            )
            prop_bone.property_overridable_library_set(f'["{prop_name}"]', True)

        for socket_name, int_name in bone_list:
            int_bone = obj.pose.bones[int_name]

            loc_constraint = int_bone.constraints.new('COPY_LOCATION')
            loc_constraint.target = obj
            loc_constraint.subtarget = socket_name

            if self.include_scale:
                scale_constraint = int_bone.constraints.new('COPY_SCALE')
                scale_constraint.target = obj
                scale_constraint.subtarget = socket_name
                scale_constraint.mute = self.disable_scale

            rot_constraint = int_bone.constraints.new('COPY_ROTATION')
            rot_constraint.target = obj
            rot_constraint.subtarget = socket_name
            rot_constraint.name = prop_name

            driver = rot_constraint.driver_add("influence").driver
            driver.type = 'AVERAGE'

            var = driver.variables.new()
            var.name = "isolation_val"
            var.type = 'SINGLE_PROP'
            var.targets[0].id = obj
            var.targets[0].data_path = f'pose.bones["{prop_bone.name}"]["{prop_name}"]'

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
        

        # Switch to edit mode
        original_mode = obj.mode
        if obj.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')
            
        bone_data = obj.data

        if not bone_data.edit_bones.get(self.root_bone_name):
            self.report({'ERROR'}, "Root bone not found")
            bpy.ops.object.mode_set(mode=original_mode)
            return {'CANCELLED'}

        if not bone_data.edit_bones.get(self.property_bone_name):
            self.report({'ERROR'}, "Property bone not found")
            bpy.ops.object.mode_set(mode=original_mode)
            return {'CANCELLED'}

        if not context.selected_editable_bones:
            self.report({'ERROR'}, "No edit bones selected. Select at least one bone.")
            bpy.ops.object.mode_set(mode=original_mode)
            return {'CANCELLED'}
        
        bones = self.create_bones(context, bone_data, context.selected_editable_bones)

        # We need to switch to pose mode so the newly created pose bones to update
        bpy.ops.object.mode_set(mode='POSE')
        self.setup_constraints(obj, bones)

        bpy.ops.object.mode_set(mode=original_mode)
        
        self.report({'INFO'}, f"Successfully generated {len(bones)} rotation isolation mechanism{'s' if len(bones) != 1 else ''}.")              
            
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=350)

    def draw(self, context):
        layout = self.layout
        
        box = layout.box()
        box.prop(self, "root_bone_name")
        box.prop(self, "property_bone_name")
        box.prop(self, "socket_bone_name")
        box.prop(self, "int_bone_name")     
        
        # Primary clean focus
        layout.prop(self, "property_name")
        row = layout.row()
        row.prop(self, "include_scale")
        row.prop(self, "disable_scale")

classes = (
    RIG_OT_create_rotation_isolation,
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
    
    bpy.ops.rig.create_rotation_isolation('INVOKE_DEFAULT')