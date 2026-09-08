import bpy
from rigtools.utils.bone import generate_bone_name, duplicate_bone, is_collection_visible

class RIG_PT_create_mch_bones(bpy.types.Panel):
    bl_label = "Create MCH Bones"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tool"

    def draw(self, context):
        if context.mode not in {'EDIT_ARMATURE', 'POSE'}:
            return

        layout = self.layout

        col = layout.column()
        col.prop(context.scene, "mch_bone_name")
        col = layout.column()
        col.operator("rig.create_mch_bones", text="Create MCH Bones")        

class RIG_OT_create_mch_bones(bpy.types.Operator):
    """Create a mechanism bone for each selected bone and optionally parent the bone to it."""
    bl_idname = "rig.create_mch_bones"
    bl_label = "Create MCH bones"
    bl_options = {'REGISTER', 'UNDO'}
    
    ################################################################################################
    # Bone generation functions

    def create_bones(self, context, armature_data, selection):
        mch_bone_names = []

        bpy.ops.armature.select_all(action='DESELECT')

        for bone in selection:
            bone_name = generate_bone_name(bone.name, context.scene.mch_bone_name)
            mch_bone = duplicate_bone(armature_data, bone, bone_name, 0.35)

            mch_bone.parent = bone.parent
            bone.use_connect = False
            bone.parent = mch_bone

            mch_bone.select = True
            mch_bone.select_head = True
            mch_bone.select_tail = True
            armature_data.edit_bones.active = mch_bone

            mch_bone.color.palette = 'DEFAULT'
            
            mch_bone_names.append(mch_bone.name)

        return mch_bone_names
    
    def remove_pose_attr(self, obj, mch_bone_names):
            
        for bone_name in mch_bone_names:
            pose_bone = obj.pose.bones[bone_name]
            pose_bone.select = True

            pose_bone.color.palette = 'DEFAULT'
            
            pose_bone.custom_shape = None

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
            self.report({'ERROR'}, "No edit bones selected. Select at least one bone.")
            bpy.ops.object.mode_set(mode=original_mode)
            return {'CANCELLED'}
        
        bones = self.create_bones(context, bone_data, context.selected_editable_bones)

        # We need to switch to pose mode so the newly created pose bones to update
        bpy.ops.object.mode_set(mode='POSE')
        self.remove_pose_attr(obj, bones)

        bpy.ops.object.mode_set(mode=original_mode)
        
        self.report({'INFO'}, f"Successfully generated {len(bones)} MCH bone{'s' if len(bones) != 1 else ''}.")              
            
        return {'FINISHED'}

classes = (
    RIG_PT_create_mch_bones,
    RIG_OT_create_mch_bones,
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
    
    bpy.ops.rig.create_mch_bones()