import bpy

class RIG_OT_toggle_bone_collection(bpy.types.Operator):
    bl_idname = "rig.toggle_bone_collection"
    bl_label = "Toggle Bone Collection"
    bl_options = {'REGISTER', 'UNDO'}
    
    collection_name: bpy.props.StringProperty()
    
    def execute(self, context):
        # Find the armature object (should be selected but not active in weight paint mode)
        armature = None
        for obj in context.selected_objects:
            if obj.type == 'ARMATURE':
                armature = obj
                break
        
        if not armature:
            self.report({'ERROR'}, "No armature found in selection")
            return {'CANCELLED'}
        
        # Find and toggle the bone collection
        for coll in armature.data.collections:
            if coll.name == self.collection_name:
                coll.is_visible = not coll.is_visible
                break
        
        return {'FINISHED'}

class RIG_OT_solo_bone_collection(bpy.types.Operator):
    bl_idname = "rig.solo_bone_collection"
    bl_label = "Solo Bone Collection"
    bl_options = {'REGISTER', 'UNDO'}
    
    collection_name: bpy.props.StringProperty()
    
    def execute(self, context):
        # Find the armature object
        armature = None
        for obj in context.selected_objects:
            if obj.type == 'ARMATURE':
                armature = obj
                break
        
        if not armature:
            self.report({'ERROR'}, "No armature found in selection")
            return {'CANCELLED'}
        
        # Set solo for the specified collection
        for coll in armature.data.collections:
            coll.is_solo = (coll.name == self.collection_name)
        
        return {'FINISHED'}

class RIG_PT_bone_collections_panel(bpy.types.Panel):
    bl_label = "Bone Collections"
    bl_idname = "RIG_PT_bone_collections_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Rig Tools"
    
    @classmethod
    def poll(cls, context):
        # Only show in weight paint mode when an armature is selected
        if context.mode != 'PAINT_WEIGHT':
            return False
        
        # Check if any armature is selected
        for obj in context.selected_objects:
            if obj.type == 'ARMATURE':
                return True
        
        return False
    
    def draw(self, context):
        layout = self.layout
        
        # Find the armature object
        armature = None
        for obj in context.selected_objects:
            if obj.type == 'ARMATURE':
                armature = obj
                break
        
        if not armature:
            layout.label(text="No armature selected")
            return
        
        layout.label(text=f"Armature: {armature.name}")
        layout.separator()
        
        # Draw bone collections
        for coll in armature.data.collections:
            row = layout.row(align=True)
            
            # Visibility toggle
            icon = 'HIDE_OFF' if coll.is_visible else 'HIDE_ON'
            row.operator("rig.toggle_bone_collection", text="", icon=icon).collection_name = coll.name
            
            # Collection name
            row.label(text=coll.name)
            
            # Solo button
            solo_icon = 'SOLO_ON' if coll.is_solo else 'SOLO_OFF'
            row.operator("rig.solo_bone_collection", text="", icon=solo_icon).collection_name = coll.name
        
        # Add a "Show All" button
        layout.separator()
        row = layout.row()
        row.operator("rig.show_all_bone_collections", text="Show All", icon='HIDE_OFF')

class RIG_OT_show_all_bone_collections(bpy.types.Operator):
    bl_idname = "rig.show_all_bone_collections"
    bl_label = "Show All Bone Collections"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Find the armature object
        armature = None
        for obj in context.selected_objects:
            if obj.type == 'ARMATURE':
                armature = obj
                break
        
        if not armature:
            self.report({'ERROR'}, "No armature found in selection")
            return {'CANCELLED'}
        
        # Show all collections and clear solo
        for coll in armature.data.collections:
            coll.is_visible = True
            coll.is_solo = False
        
        return {'FINISHED'} 