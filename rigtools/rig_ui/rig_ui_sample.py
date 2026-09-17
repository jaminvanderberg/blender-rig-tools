import bpy
from mathutils import Euler, Matrix, Vector, Quaternion
from rna_prop_ui import rna_idprop_ui_create

###Set a rig ID in your armature custom properties using a string
rig_id = "es39IRSBDPNObRb3"

######################################################################################

### Displaying bone collections (Blender 4.0 and above)
class RIG_PT_rigui(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Item'
    bl_label = "Rig UI"
    bl_idname = "RIG_PT_rigui"


### Check if the selected rig has the corresponding RigID
    @classmethod
    def poll(self, context):
        try:
            return (context.active_object.data.get("rig_id") == rig_id)
        except (AttributeError, KeyError, TypeError):
            return False


    def draw(self, context):
        layout = self.layout
        col = layout.column()
        ### get the bone collection from our Armature. "Armature" is the name of our armature
        collection = bpy.data.armatures["Armature"].collections_all

        ### We can create rows exposing the visibility of our bone collection and give them a name 
        row = col.row(align = True)  
        row.prop(collection["Root"], 'is_visible', toggle=True, text='Root')
        row = col.row(align = True)  
        row = col.row(align = True)  
        row = col.row(align = True)  
        row.prop(collection["DEF"], 'is_visible', toggle=True, text='DEF')
        row = col.row(align = True)  
        row = col.row(align = True)  
        row = col.row(align = True)  
        row.prop(collection["ORG"], 'is_visible', toggle=True, text='ORG')
        row = col.row(align = True)  
        row.prop(collection["ORG.Body"], 'is_visible', toggle=True, text='Body')
        row.prop(collection["ORG.Belt"], 'is_visible', toggle=True, text='Belt')
        row.prop(collection["ORG.Belt.Upper"], 'is_visible', toggle=True, text='Belt.Upper')
        row = col.row(align = True)  
        row.prop(collection["ORG.Shorts"], 'is_visible', toggle=True, text='Shorts')
        row.prop(collection["ORG.Cloth.Back"], 'is_visible', toggle=True, text='Cloth.Back')
        row.prop(collection["ORG.Ponytail"], 'is_visible', toggle=True, text='Ponytail')
        row = col.row(align = True)  
        row.prop(collection["ORG.Sword"], 'is_visible', toggle=True, text='Sword')
        row.prop(collection["ORG.Staff"], 'is_visible', toggle=True, text='Staff')
        row.prop(collection["ORG.COR"], 'is_visible', toggle=True, text='COR')
        row.prop(collection["ORG.Detail"], 'is_visible', toggle=True, text='Detail')
        row = col.row(align = True)  
        row = col.row(align = True)  
        row = col.row(align = True)  
        row.prop(collection["MCH"], 'is_visible', toggle=True, text='MCH')        
        row = col.row(align = True)  
        row = col.row(align = True)  
        row = col.row(align = True)  
        row.prop(collection["TMP"], 'is_visible', toggle=True, text='TMP')
        row.prop(collection["MCH-TMP"], 'is_visible', toggle=True, text='MCH-TMP')
        
        row = col.row(align = True)  
        row = col.row(align = True)  
        row = col.row(align = True)  
        row.prop(collection["Torso"], 'is_visible', toggle=True, text='Torso')                
        row.prop(collection["Torso.FK"], 'is_visible', toggle=True, text='Torso.FK')                
        row.prop(collection["Torso.Tweak"], 'is_visible', toggle=True, text='Torso.Tweak')
        
        row = col.row(align = True)  
        row = col.row(align = True)  
        row = col.row(align = True)  
        row.prop(collection["Ponytail"], 'is_visible', toggle=True, text='Ponytail')                
        row.prop(collection["Ponytail.FK"], 'is_visible', toggle=True, text='Ponytail.FK')                
        row.prop(collection["Ponytail.Tweak"], 'is_visible', toggle=True, text='PTail.Tweak')

        row = col.row(align = True)  
        row = col.row(align = True)  
        row = col.row(align = True)  
        row.prop(collection["Arm.IK.L"], 'is_visible', toggle=True, text='Arm.IK.L')
        row.prop(collection["Arm.IK.R"], 'is_visible', toggle=True, text='Arm.IK.R')
        row = col.row(align = True)  
        row.prop(collection["Arm.FK.L"], 'is_visible', toggle=True, text='Arm.FK.L')
        row.prop(collection["Arm.FK.R"], 'is_visible', toggle=True, text='Arm.FK.R')
        row = col.row(align = True)  
        row.prop(collection["Arm.Tweak.L"], 'is_visible', toggle=True, text='Arm.Tweak.L')
        row.prop(collection["Arm.Tweak.R"], 'is_visible', toggle=True, text='Arm.Tweak.R')

        row = col.row(align = True)  
        row = col.row(align = True)  
        row = col.row(align = True)  
        row.prop(collection["Hand.L"], 'is_visible', toggle=True, text='Hand.L')
        row.prop(collection["Hand.R"], 'is_visible', toggle=True, text='Hand.R')
        row = col.row(align = True)  
        row.prop(collection["Hand.Tweak.L"], 'is_visible', toggle=True, text='Hand.Tweak.L')
        row.prop(collection["Hand.Tweak.R"], 'is_visible', toggle=True, text='Hand.Tweak.R')
        
        
        row = col.row(align = True)  
        row = col.row(align = True)  
        row = col.row(align = True)  
        row.prop(collection["Leg.IK.L"], 'is_visible', toggle=True, text='Leg.IK.L')
        row.prop(collection["Leg.IK.R"], 'is_visible', toggle=True, text='Leg.IK.R')
        row = col.row(align = True)  
        row.prop(collection["Leg.FK.L"], 'is_visible', toggle=True, text='Leg.FK.L')
        row.prop(collection["Leg.FK.R"], 'is_visible', toggle=True, text='Leg.FK.R')
        row = col.row(align = True)  
        row.prop(collection["Leg.Tweak.L"], 'is_visible', toggle=True, text='Leg.Tweak.L')
        row.prop(collection["Leg.Tweak.R"], 'is_visible', toggle=True, text='Leg.Tweak.R')
        
        
        row = col.row(align = True)  
        row = col.row(align = True)  
        row = col.row(align = True)  
        row.prop(collection["Belt"], 'is_visible', toggle=True, text='Belt')
        row.prop(collection["Belt.Tweak"], 'is_visible', toggle=True, text='Belt.Tweak')
        
        row = col.row(align = True)  
        row.prop(collection["Cloth.Front"], 'is_visible', toggle=True, text='Cloth.Front')
        row.prop(collection["Cloth.Front.Tweak"], 'is_visible', toggle=True, text='Cloth.Front.Tweak')        

        row = col.row(align = True)  
        row.prop(collection["Cloth.Back"], 'is_visible', toggle=True, text='Cloth.Back')
        row.prop(collection["Cloth.Back.Tweak"], 'is_visible', toggle=True, text='Cloth.Back.Tweak')        

        row = col.row(align = True)  
        row.prop(collection["Shorts"], 'is_visible', toggle=True, text='Shorts')
        row.prop(collection["Shorts.Tweak"], 'is_visible', toggle=True, text='Shorts.Tweak')        
        
        row = col.row(align = True)  
        row = col.row(align = True)  
        row = col.row(align = True)
        row.prop(collection["Sword"], 'is_visible', toggle=True, text='Sword')
        row.prop(collection["Sword.Tweak"], 'is_visible', toggle=True, text='Sword.Tweak')  
        row.prop(collection["Sword.Master"], 'is_visible', toggle=True, text='Sword.Master')  
        
        row = col.row(align = True)  
        row = col.row(align = True)  
        row = col.row(align = True)
        row.prop(collection["Staff"], 'is_visible', toggle=True, text='Staff')
        row.prop(collection["Staff.Tweak"], 'is_visible', toggle=True, text='Staff.Tweak')  
        row.prop(collection["Staff.Master"], 'is_visible', toggle=True, text='Staff.Master') 
        
######################################################################################

bone = bpy.data.objects["Armature"].pose.bones["properties"]

##################
# Left Arm Parent
left_arm_parent = ['Root', 'Torso', 'Hips', 'Chest', 'Head']

property_key = "arm.IK.parent.L"

if property_key not in bone:
    rna_idprop_ui_create(
        bone,
        property_key,
        default=0,
        min=0,
        max=len(left_arm_parent),
        items=[(str(i), item, item) for i,item in enumerate(left_arm_parent)],
        description="Arm IK Parent"
    )

    bone.property_overridable_library_set('["' + property_key + '"]', True)

##################
# Right Arm Parent
right_arm_parent = ['Root', 'Torso', 'Hips', 'Chest', 'Head']

property_key = "arm.IK.parent.R"

if property_key not in bone:
    rna_idprop_ui_create(
        bone,
        property_key,
        default=0,
        min=0,
        max=len(right_arm_parent),
        items=[(str(i), item, item) for i,item in enumerate(right_arm_parent)],
        description="Arm IK Parent"
    )

    bone.property_overridable_library_set('["' + property_key + '"]', True)

##################
# Arm FK/IK
fk_ik = ['FK', 'IK']

property_key = "arm.FK.IK.L"

if property_key not in bone:
    rna_idprop_ui_create(
        bone,
        property_key,
        default=0,
        min=0,
        max=len(fk_ik),
        items=[(str(i), item, item) for i,item in enumerate(fk_ik)],
        description="Arm FK > IK.L"
    )

    bone.property_overridable_library_set('["' + property_key + '"]', True)

property_key = "arm.FK.IK.R"

if property_key not in bone:
    rna_idprop_ui_create(
        bone,
        property_key,
        default=0,
        min=0,
        max=len(fk_ik),
        items=[(str(i), item, item) for i,item in enumerate(fk_ik)],
        description="Arm FK > IK.R"
    )

    bone.property_overridable_library_set('["' + property_key + '"]', True)

##################
#Leg Parent
leg_parent = ['Root', 'Foot', 'Torso']

property_key = "leg.IK.parent.L"

if property_key not in bone:
    rna_idprop_ui_create(
        bone,
        property_key,
        default=1,
        min=0,
        max=len(leg_parent),
        items=[(str(i), item, item) for i,item in enumerate(leg_parent)],
        description="Leg IK Parent"
    )

    bone.property_overridable_library_set('["' + property_key + '"]', True)

property_key = "leg.IK.parent.R"

if property_key not in bone:
    rna_idprop_ui_create(
        bone,
        property_key,
        default=1,
        min=0,
        max=len(leg_parent),
        items=[(str(i), item, item) for i,item in enumerate(leg_parent)],
        description="Leg IK Parent"
    )

    bone.property_overridable_library_set('["' + property_key + '"]', True)

##################
# Leg FK/IK
property_key = "leg.FK.IK.L"

if property_key not in bone:
    rna_idprop_ui_create(
        bone,
        property_key,
        default=0,
        min=0,
        max=len(fk_ik),
        items=[(str(i), item, item) for i,item in enumerate(fk_ik)],
        description="Leg FK > IK.L"
    )

    bone.property_overridable_library_set('["' + property_key + '"]', True)

property_key = "leg.FK.IK.R"

if property_key not in bone:
    rna_idprop_ui_create(
        bone,
        property_key,
        default=0,
        min=0,
        max=len(fk_ik),
        items=[(str(i), item, item) for i,item in enumerate(fk_ik)],
        description="Leg FK > IK.R"
    )

    bone.property_overridable_library_set('["' + property_key + '"]', True)


weapon_parent = ['Root', 'Left Hand', 'Right Hand']

property_key = "sword.parent"

rna_idprop_ui_create(
    bone,
    property_key,
    default=0,
    min=0,
    max=len(weapon_parent),
    items=[(str(i), item, item) for i,item in enumerate(weapon_parent)],
    description="Sword Parent"
)

bone.property_overridable_library_set('["' + property_key + '"]', True)


weapon_master_parent = ['Root', 'Torso']

property_key = "sword.master.parent"

rna_idprop_ui_create(
    bone,
    property_key,
    default=0,
    min=0,
    max=len(weapon_master_parent),
    items=[(str(i), item, item) for i,item in enumerate(weapon_master_parent)],
    description="Sword Master Parent"
)

bone.property_overridable_library_set('["' + property_key + '"]', True)


property_key = "staff.parent"

rna_idprop_ui_create(
    bone,
    property_key,
    default=0,
    min=0,
    max=len(weapon_parent),
    items=[(str(i), item, item) for i,item in enumerate(weapon_parent)],
    description="Staff Parent"
)

bone.property_overridable_library_set('["' + property_key + '"]', True)


property_key = "staff.master.parent"

rna_idprop_ui_create(
    bone,
    property_key,
    default=0,
    min=0,
    max=len(weapon_master_parent),
    items=[(str(i), item, item) for i,item in enumerate(weapon_master_parent)],
    description="Staff Master Parent"
)

bone.property_overridable_library_set('["' + property_key + '"]', True)

        
######################################################################################

###Custom properties panel 
### THIS IS ONLY THE PARENT PANEL FOR ALL THE SUB PANELS
class RIG_PT_customprops(bpy.types.Panel):
    bl_category = 'Item'
    bl_label = "Rig Properties"
    bl_idname = "RIG_PT_customprops"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(self, context):
        try:
            return (context.active_object.data.get("rig_id") == rig_id)
        except (AttributeError, KeyError, TypeError):
            return False
        
    def draw(self, context):
        layout = self.layout
        

# Head Properties
class RIG_PT_head_props(bpy.types.Panel):
    bl_label = "Head Properties" 
    bl_idname = "RIG_PT_head_props"
    bl_space_type = 'VIEW_3D'
    bl_parent_id = "RIG_PT_customprops"
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        
        arm = context.active_object
        bone = arm.pose.bones["properties"]
        
        layout = self.layout
        split_size = 0.7
        
        box = layout.box()
        col = box.column(align=True)
        
        # Head Rotation Follow
        row = col.row()              
        split = row.split(align=True, factor=split_size)
        row = split.row(align=True)        
        row.label(text='Head Rotation Follow', translate=False)
        row = split.row(align=True)
        row.prop(bone, '["head.rot.follow"]', text = "", slider=True)
        
        # Neck Rotation Follow
        row = col.row() 
        split = row.split(align=True, factor=split_size)
        row = split.row(align=True)
        row.label(text='Neck Rotation Follow', translate=False)
        row = split.row(align=True)
        row.prop(bone, '["neck.rot.follow"]', text = "", slider=True)   
        
        
# Ponytail Properties
class RIG_PT_ponytail_props(bpy.types.Panel):
    bl_label = "Ponytail Properties" 
    bl_idname = "RIG_PT_ponytail_props"
    bl_space_type = 'VIEW_3D'
    bl_parent_id = "RIG_PT_customprops"
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        
        arm = context.active_object
        bone = arm.pose.bones["properties"]
        
        layout = self.layout
        split_size = 0.7
        
        box = layout.box()
        col = box.column(align=True)

        row = col.row()              
        split = row.split(align=True, factor=split_size)
        row = split.row(align=True)        
        row.label(text='Ponytail Rotation Follow.1', translate=False)
        row = split.row(align=True)
        row.prop(bone, '["ponytail.rot.follow.01"]', text = "", slider=True)
        
        row = col.row() 
        split = row.split(align=True, factor=split_size)
        row = split.row(align=True)
        row.label(text='Ponytail Rotation Follow.2', translate=False)
        row = split.row(align=True)
        row.prop(bone, '["ponytail.rot.follow.02"]', text = "", slider=True)
        
        row = col.row() 
        split = row.split(align=True, factor=split_size)
        row = split.row(align=True)
        row.label(text='Ponytail Rotation Follow.3', translate=False)
        row = split.row(align=True)
        row.prop(bone, '["ponytail.rot.follow.03"]', text = "", slider=True)

        row = col.row() 
        split = row.split(align=True, factor=split_size)
        row = split.row(align=True)
        row.label(text='Ponytail Rotation Follow.4', translate=False)
        row = split.row(align=True)
        row.prop(bone, '["ponytail.rot.follow.04"]', text = "", slider=True)

        row = col.row() 
        split = row.split(align=True, factor=split_size)
        row = split.row(align=True)
        row.label(text='Ponytail Rotation Follow.5', translate=False)
        row = split.row(align=True)
        row.prop(bone, '["ponytail.rot.follow.05"]', text = "", slider=True)
        
        row = col.row() 
        split = row.split(align=True, factor=split_size)
        row = split.row(align=True)
        row.label(text='Ponytail Twist Lock', translate=False)
        row = split.row(align=True)
        row.prop(bone, '["ponytail.twist.lock"]', text = "", slider=True)
        

# Arms Properties
class RIG_PT_arm_props(bpy.types.Panel):
    bl_label = "Arm Properties" 
    bl_idname = "RIG_PT_arm_props"
    bl_space_type = 'VIEW_3D'
    bl_parent_id = "RIG_PT_customprops"
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        
        arm = context.active_object
        bone = arm.pose.bones["properties"]
        
        layout = self.layout
        split_size = 0.7
        
        box = layout.box()
        col = box.column(align=True)
        row = col.row()              
        
        split = row.split(align=True, factor=split_size)
        row = split.row(align=True)        
        row.label(text='Arm FK > IK.L', translate=False)
        row = split.row(align=True)
        row.prop(bone, '["arm.FK.IK.L"]', text = "", slider=True)
               
        row = col.row() 
        split = row.split(align=True, factor=split_size)
        row = split.row(align=True)
        row.label(text='Arm Rotation Follow.L', translate=False)
        row = split.row(align=True)
        row.prop(bone, '["arm.rot.follow.L"]', text = "", slider=True)  
        
        row = col.row() 
        split = row.split(align=True, factor=split_size)
        row = split.row(align=True)
        row.label(text='Arm IK Parent.L', translate=False)
        row = split.row(align=True)
        row.prop(bone, '["arm.IK.parent.L"]', text = "", slider=True)              

        box = layout.box()
        col = box.column(align=True)
        row = col.row()              

        split = row.split(align=True, factor=split_size)
        row = split.row(align=True)        
        row.label(text='Arm FK > IK.R', translate=False)
        row = split.row(align=True)
        row.prop(bone, '["arm.FK.IK.R"]', text = "", slider=True)
               
        row = col.row() 
        split = row.split(align=True, factor=split_size)
        row = split.row(align=True)
        row.label(text='Arm Rotation Follow.R', translate=False)
        row = split.row(align=True)
        row.prop(bone, '["arm.rot.follow.R"]', text = "", slider=True)
        
        row = col.row() 
        split = row.split(align=True, factor=split_size)
        row = split.row(align=True)
        row.label(text='Arm IK Parent.R', translate=False)
        row = split.row(align=True)
        row.prop(bone, '["arm.IK.parent.R"]', text = "", slider=True)                  
            
# Leg Properties
class RIG_PT_leg_props(bpy.types.Panel):
    bl_label = "Leg Properties" 
    bl_idname = "RIG_PT_leg_props"
    bl_space_type = 'VIEW_3D'
    bl_parent_id = "RIG_PT_customprops"
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        
        arm = context.active_object
        bone = arm.pose.bones["properties"]
        
        layout = self.layout
        split_size = 0.7
        
        box = layout.box()
        col = box.column(align=True)

        row = col.row()              
        split = row.split(align=True, factor=split_size)
        row = split.row(align=True)        
        row.label(text='Leg FK > IK.L', translate=False)
        row = split.row(align=True)
        row.prop(bone, '["leg.FK.IK.L"]', text = "", slider=True)
        
        row = col.row() 
        split = row.split(align=True, factor=split_size)
        row = split.row(align=True)
        row.label(text='Leg Rotation Follow.L', translate=False)
        row = split.row(align=True)
        row.prop(bone, '["leg.rot.follow.L"]', text = "", slider=True)  
        
        row = col.row() 
        split = row.split(align=True, factor=split_size)
        row = split.row(align=True)
        row.label(text='Leg IK Parent.L', translate=False)
        row = split.row(align=True)
        row.prop(bone, '["leg.IK.parent.L"]', text = "", slider=True)              
        
        box = layout.box()
        col = box.column(align=True)

        row = col.row()              
        split = row.split(align=True, factor=split_size)
        row = split.row(align=True)        
        row.label(text='Leg FK > IK.R', translate=False)
        row = split.row(align=True)
        row.prop(bone, '["leg.FK.IK.R"]', text = "", slider=True)
        
        
        row = col.row() 
        split = row.split(align=True, factor=split_size)
        row = split.row(align=True)
        row.label(text='Leg Rotation Follow.R', translate=False)
        row = split.row(align=True)
        row.prop(bone, '["leg.rot.follow.R"]', text = "", slider=True)
        
        row = col.row() 
        split = row.split(align=True, factor=split_size)
        row = split.row(align=True)
        row.label(text='Leg IK Parent.R', translate=False)
        row = split.row(align=True)
        row.prop(bone, '["leg.IK.parent.R"]', text = "", slider=True)
        
# Accessory Properties
class RIG_PT_acc_props(bpy.types.Panel):
    bl_label = "Accessory Properties" 
    bl_idname = "RIG_PT_accessory_props"
    bl_space_type = 'VIEW_3D'
    bl_parent_id = "RIG_PT_customprops"
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        
        arm = context.active_object
        bone = arm.pose.bones["properties"]
        
        layout = self.layout
        split_size = 0.7
        
        box = layout.box()
        col = box.column(align=True)

        row = col.row()              
        split = row.split(align=True, factor=split_size)
        row = split.row(align=True)        
        row.label(text='Cloth.Front Rotation Follow', translate=False)
        row = split.row(align=True)
        row.prop(bone, '["cloth.front.rot.follow"]', text = "", slider=True)
        
        row = col.row() 
        split = row.split(align=True, factor=split_size)
        row = split.row(align=True)
        row.label(text='Cloth.Back Rotation Follow', translate=False)
        row = split.row(align=True)
        row.prop(bone, '["cloth.back.rot.follow"]', text = "", slider=True)  
        
        row = col.row() 
        split = row.split(align=True, factor=split_size)
        row = split.row(align=True)
        row.label(text='Cloth.Front Leg Collision', translate=False)
        row = split.row(align=True)
        row.prop(bone, '["cloth.front.collide"]', text = "", slider=True)          
        
# Weapon Properties
class RIG_PT_weapon_props(bpy.types.Panel):
    bl_label = "Weapon Properties" 
    bl_idname = "RIG_PT_weapon_props"
    bl_space_type = 'VIEW_3D'
    bl_parent_id = "RIG_PT_customprops"
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        
        # get armature and "PROPERTIES" bone 
        arm = context.active_object
        bone = arm.pose.bones["properties"]
        
        layout = self.layout
        split_size = 0.7
        
        box = layout.box()
        col = box.column(align=True)

        row = col.row()              
        split = row.split(align=True, factor=split_size)
        row = split.row(align=True)        
        row.label(text='Sword Parent', translate=False)
        row = split.row(align=True)
        row.prop(bone, '["sword.parent"]', text = "", slider=True)
        
        row = col.row() 
        split = row.split(align=True, factor=split_size)
        row = split.row(align=True)
        row.label(text='Sword Master', translate=False)
        row = split.row(align=True)
        row.prop(bone, '["sword.master"]', text = "", slider=True) 
        
        row = col.row()
        split = row.split(align=True, factor=split_size)
        row = split.row(align=True)
        row.label(text='Sword Master Parent', translate=False)
        row = split.row(align=True)
        row.prop(bone, '["sword.master.parent"]', text = "", slider=True) 
        

        box = layout.box()
        col = box.column(align=True)

        row = col.row()              
        split = row.split(align=True, factor=split_size)
        row = split.row(align=True)        
        row.label(text='Staff Parent', translate=False)
        row = split.row(align=True)
        row.prop(bone, '["staff.parent"]', text = "", slider=True)
        
        row = col.row() 
        split = row.split(align=True, factor=split_size)
        row = split.row(align=True)
        row.label(text='Staff Master', translate=False)
        row = split.row(align=True)
        row.prop(bone, '["staff.master"]', text = "", slider=True) 
        
        row = col.row()
        split = row.split(align=True, factor=split_size)
        row = split.row(align=True)
        row.label(text='Staff Master Parent', translate=False)
        row = split.row(align=True)
        row.prop(bone, '["staff.master.parent"]', text = "", slider=True) 
                
######################################################################################

class RIG_PT_vis_props(bpy.types.Panel):
    bl_label = "Visibility Properties" 
    bl_idname = "RIG_PT_vis_props"
    bl_space_type = 'VIEW_3D'
    bl_category = 'Item'
    bl_parent_id = "RIG_PT_customprops"
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        
        # object list (if you change object names it you will have to change these too) We can create as many variable as we want to source asmany objects as we want
        my_object =  bpy.data.objects['KIBALI']
               
        # character modifiers use modifier names (if you change modifier names it you will have to change these too). Here we have an edxample with mask modifiers.
        # creating a variable to source the modifier (name_of_the_variable = my_object.modifiers["exact_modifier_name"])
        mask_arms = my_object.modifiers["Mask.Arms"]
        mask_legs = my_object.modifiers["Mask.Legs"]
        mask_acc = my_object.modifiers["Mask.Accessories"]
        mask_pony = my_object.modifiers["Mask.Ponytail"]
        mask_staff = bpy.data.objects['KIBALI_STAFF'].modifiers["Mask"]
        mask_sword = bpy.data.objects['KIBALI_SWORD'].modifiers["Mask"]
        
        # start panel layout
        layout = self.layout
        layout.use_property_split = False
        layout.use_property_decorate = False 
        
        # character modifiers
        # if I didn't break it down above the code would be: (kinda messy)
        # row.prop(bpy.data.objects['my_object'].modifiers["MASK-TORSO"], 'show_viewport', text="", toggle = True, icon='HIDE_ON', emboss=False)  
        # here we use Blender's eye/hide icon
        box = layout.box()
        col = box.column(align=True)
        row = col.row() 
        row.label(text='Arms', translate=False)   
        row.prop(mask_arms, 'show_viewport', text="", icon='HIDE_ON', invert_checkbox=True, emboss=False)
        
        row = col.row(align = True)  
        row.label(text='Legs', translate=False)             
        row.prop(mask_legs, 'show_viewport', text="", icon='HIDE_ON', invert_checkbox=True, emboss=False)
      
        row = col.row(align = True)  
        row.label(text='Accessories', translate=False)             
        row.prop(mask_acc, 'show_viewport', text="", icon='HIDE_ON', invert_checkbox=True, emboss=False)

        row = col.row(align = True)  
        row.label(text='Ponytail', translate=False)             
        row.prop(mask_pony, 'show_viewport', text="", icon='HIDE_ON', invert_checkbox=True, emboss=False)

        row = col.row(align = True)  
        row.label(text='Staff', translate=False)             
        row.prop(mask_staff, 'show_viewport', text="", icon='HIDE_ON', invert_checkbox=True, emboss=False)

        row = col.row(align = True)  
        row.label(text='Sword', translate=False)             
        row.prop(mask_sword, 'show_viewport', text="", icon='HIDE_ON', invert_checkbox=True, emboss=False)


######################################################################################

######################### Snap functions ############################

# returns final world matrix accounting for offset in rest pose
def get_matrix(armature, source_bone, target_bone):
    # rest post matrices
    source_bone_rest_matrix = source_bone.bone.matrix_local
    target_bone_rest_matrix = target_bone.bone.matrix_local

    # rest pose offset matrix
    offset_matrix = source_bone_rest_matrix.inverted() @ target_bone_rest_matrix

    # world_space_matrices
    source_world_matrix = source_bone.matrix

    #world space matrix
    matrix_final =  source_world_matrix @ offset_matrix
    
    return matrix_final

######################### Snap Operators ############################

### ARMS ###
### Snapping IK to FK ####
### We create MCH bones that are children of the FK chain to snap our IK controllers to###

class RIG_OT_ik_fk_arm(bpy.types.Operator):
    bl_idname = "RIG.ik_fk_arm"
    bl_label = ""
    bl_description = "Snap IK > FK"
    bl_options = {'UNDO', 'INTERNAL'}
    
    side: bpy.props.StringProperty(name="'L' or 'R'")

    @classmethod
    def poll(self, context):
        try:
            return (context.active_object.data.get("rig_id") == rig_id)
        except (AttributeError, KeyError, TypeError):
            return False
    
    def execute(self, context):
        side = self.side
        armature = bpy.context.active_object
        pose_bones = armature.pose.bones
        #name of the custom properties bone
        properties = pose_bones['properties']
        
        # FK BONES TO SNAP TO
        fk_hand = pose_bones[f'FK-hand.{side}']
        fk_pole = pose_bones[f'MCH-IK-FK-IK-pole.arm.{side}']
                
        # IK BONES
        ik_hand = pose_bones[f'IK-hand.{side}']
        ik_pole = pose_bones[f'IK-pole.arm.{side}']
                
        select_set = (ik_hand, ik_pole, properties) 
        
        hand_matrix = get_matrix(armature, fk_hand, ik_hand )
        pole_matrix = get_matrix(armature, fk_pole, ik_pole )
        
        ik_hand.matrix = hand_matrix
        bpy.context.view_layer.update()        
        ik_pole.matrix = pole_matrix
        bpy.context.view_layer.update()
        
        # switch_mode   
        properties[f'arm.FK.IK.{side}'] = 1        
        
        bpy.ops.pose.select_all(action='DESELECT')
        
        for pbone in select_set:
            armature.data.bones.active = pbone.bone

            if bpy.context.scene.tool_settings.use_keyframe_insert_auto:
                try:
                    bpy.ops.anim.keyframe_insert_menu(type='Available')
                except RuntimeError:
                    self.report({'WARNING'}, f'{pbone.name} has no active keyframes')
                    pass        
        
        return {'FINISHED'}      


### ARMS ###
### Snapping FK to IK ####
### We use the MCH bones of the IK chain to snap the FK chain to ###

class RIG_OT_fk_ik_arm(bpy.types.Operator):
    bl_idname = "RIG.fk_ik_arm"
    bl_label = ""
    bl_description = "Snap IK > FK"
    bl_options = {'UNDO', 'INTERNAL'}
    
    side: bpy.props.StringProperty(name="'L' or 'R'")

    @classmethod
    def poll(self, context):
        try:
            return (context.active_object.data.get("rig_id") == rig_id)
        except (AttributeError, KeyError, TypeError):
            return False
    
    def execute(self, context):
        side = self.side
        armature = bpy.context.active_object
        pose_bones = armature.pose.bones
        #name of the custom properties bone
        properties = pose_bones['properties']
        
        # FK BONES
        fk_hand = pose_bones[f'FK-hand.{side}']
        fk_forearm = pose_bones[f'FK-forearm.{side}']
        fk_arm = pose_bones[f'FK-arm.{side}']
                
        # IK BONES TO SNAP TO
        ik_hand = pose_bones[f'IK-hand.{side}']
        ik_forearm = pose_bones[f'MCH-IK-forearm.{side}']
        ik_arm = pose_bones[f'MCH-IK-arm.{side}']
                
        select_set = (fk_hand, fk_forearm, fk_arm, properties) 
        
        hand_matrix = get_matrix(armature, ik_hand, fk_hand )
        forearm_matrix = get_matrix(armature, ik_forearm, fk_forearm )
        arm_matrix = get_matrix(armature, ik_arm, fk_arm )
        
### order may matrer ##
        fk_arm.matrix = arm_matrix
        bpy.context.view_layer.update()
        fk_forearm.matrix = forearm_matrix
        bpy.context.view_layer.update()
        fk_hand.matrix = hand_matrix
        bpy.context.view_layer.update()        
                
        
        # switch_mode   
        properties[f'arm.FK.IK.{side}'] = 0
        
        bpy.ops.pose.select_all(action='DESELECT')
        
        for pbone in select_set:
            armature.data.bones.active = pbone.bone

            if bpy.context.scene.tool_settings.use_keyframe_insert_auto:
                try:
                    bpy.ops.anim.keyframe_insert_menu(type='Available')
                except RuntimeError:
                    self.report({'WARNING'}, f'{pbone.name} has no active keyframes')
                    pass        
        
        return {'FINISHED'}      

### LEGS ###
### Snapping IK to FK ####
### We create MCH bones that are children of the FK chain to snap our IK controllers to###

class RIG_OT_ik_fk_leg(bpy.types.Operator):
    bl_idname = "RIG.ik_fk_leg"
    bl_label = ""
    bl_description = "Snap IK > FK"
    bl_options = {'UNDO', 'INTERNAL'}
    
    side: bpy.props.StringProperty(name="'L' or 'R'")

    @classmethod
    def poll(self, context):
        try:
            return (context.active_object.data.get("rig_id") == rig_id)
        except (AttributeError, KeyError, TypeError):
            return False
    
    def execute(self, context):
        side = self.side
        armature = bpy.context.active_object
        pose_bones = armature.pose.bones
        #name of the custom properties bone
        properties = pose_bones['properties']
        
        # FK BONES TO SNAP TO
        fk_foot = pose_bones[f'MCH-IK-FK-IK.foot.master.{side}']
        fk_pole = pose_bones[f'MCH-IK-FK-IK.leg.pole.{side}']
                
        # IK BONES
        ik_foot = pose_bones[f'IK.foot.master.{side}']
        ik_pole = pose_bones[f'IK.leg.pole.{side}']
                
        select_set = (ik_foot, ik_pole, properties) 
        
        foot_matrix = get_matrix(armature, fk_foot, ik_foot )
        pole_matrix = get_matrix(armature, fk_pole, ik_pole )
        
        ik_foot.matrix = foot_matrix
        bpy.context.view_layer.update()        
        ik_pole.matrix = pole_matrix
        bpy.context.view_layer.update()
        
        # switch_mode   
        properties[f'leg.FK.IK.{side}'] = 1       
        
        bpy.ops.pose.select_all(action='DESELECT')
        
        for pbone in select_set:
            armature.data.bones.active = pbone.bone

            if bpy.context.scene.tool_settings.use_keyframe_insert_auto:
                try:
                    bpy.ops.anim.keyframe_insert_menu(type='Available')
                except RuntimeError:
                    self.report({'WARNING'}, f'{pbone.name} has no active keyframes')
                    pass        
        
        return {'FINISHED'}      


### LEGS ###
### Snapping FK to IK ####
### We use the MCH bones of the IK chain to snap the FK chain to ###

class RIG_OT_fk_ik_leg(bpy.types.Operator):
    bl_idname = "RIG.fk_ik_leg"
    bl_label = ""
    bl_description = "Snap IK > FK"
    bl_options = {'UNDO', 'INTERNAL'}
    
    side: bpy.props.StringProperty(name="'L' or 'R'")

    @classmethod
    def poll(self, context):
        try:
            return (context.active_object.data.get("rig_id") == rig_id)
        except (AttributeError, KeyError, TypeError):
            return False
    
    def execute(self, context):
        side = self.side
        armature = bpy.context.active_object
        pose_bones = armature.pose.bones
        #name of the custom properties bone
        properties = pose_bones['properties']
        
        # FK BONES
        fk_foot = pose_bones[f'FK-foot.{side}']
        fk_shin = pose_bones[f'FK-shin.{side}']
        fk_thigh = pose_bones[f'FK-thigh.{side}']
                
        # IK BONES TO SNAP TO
        ik_foot = pose_bones[f'IK.foot.master.{side}']
        ik_shin = pose_bones[f'MCH-IK-shin.{side}']
        ik_thigh = pose_bones[f'MCH-IK-thigh.{side}']
                
        select_set = (fk_foot, fk_shin, fk_thigh, properties) 
        
        foot_matrix = get_matrix(armature, ik_foot, fk_foot )
        shin_matrix = get_matrix(armature, ik_shin, fk_shin )
        thigh_matrix = get_matrix(armature, ik_thigh, fk_thigh )
        
### order may matrer ##
        fk_thigh.matrix = thigh_matrix
        bpy.context.view_layer.update()
        fk_shin.matrix = shin_matrix
        bpy.context.view_layer.update()
        fk_foot.matrix = foot_matrix
        bpy.context.view_layer.update()        
                
        
        # switch_mode   
        properties[f'leg.FK.IK.{side}'] = 0        
        
        bpy.ops.pose.select_all(action='DESELECT')
        
        for pbone in select_set:
            armature.data.bones.active = pbone.bone

            if bpy.context.scene.tool_settings.use_keyframe_insert_auto:
                try:
                    bpy.ops.anim.keyframe_insert_menu(type='Available')
                except RuntimeError:
                    self.report({'WARNING'}, f'{pbone.name} has no active keyframes')
                    pass        
        
        return {'FINISHED'}      



##################################################################################  

### We display our snapping tools in a panel ###

class RIG_PT_snap_panel(bpy.types.Panel):
    bl_category = 'Item'
    bl_label = "Snap Utilities"
    bl_idname = "RIG_PT_snap_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(self, context):
        try:
            return (context.active_object.data.get("rig_id") == rig_id)
        except (AttributeError, KeyError, TypeError):
            return False
        
    def draw(self, context):
        layout = self.layout
        #box = layout.box()
        col = layout.column(align=True)
        row = col.row()
        row.operator("RIG.ik_fk_arm", emboss=True, text="Arm L IK > FK", icon='SNAP_ON').side = 'L'
        row.operator("RIG.ik_fk_arm", emboss=True, text="Arm R IK > FK", icon='SNAP_ON').side = 'R'
        
        row = col.row()
        row.operator("RIG.fk_ik_arm", emboss=True, text="Arm L FK > IK", icon='SNAP_ON').side = 'L'
        row.operator("RIG.fk_ik_arm", emboss=True, text="Arm R FK > IK", icon='SNAP_ON').side = 'R'
        
        col = layout.column(align=True)
        row = col.row()
        row.operator("RIG.ik_fk_leg", emboss=True, text="Leg L IK > FK", icon='SNAP_ON').side = 'L'
        row.operator("RIG.ik_fk_leg", emboss=True, text="Leg R IK > FK", icon='SNAP_ON').side = 'R'
        
        row = col.row()
        row.operator("RIG.fk_ik_leg", emboss=True, text="Leg L FK > IK", icon='SNAP_ON').side = 'L'
        row.operator("RIG.fk_ik_leg", emboss=True, text="Leg R FK > IK", icon='SNAP_ON').side = 'R'
                                            
##################################################################################                                            

### Operators and panels must be registered #######                                            

### To use and display classes, we need to register them. Add your panerls and operators to the list below. This is the end of our script
                                            
classes = (RIG_PT_rigui, 
    RIG_PT_customprops,
    RIG_PT_head_props,
    RIG_PT_ponytail_props,
    RIG_PT_arm_props,
    RIG_PT_leg_props,
    RIG_PT_acc_props,
    RIG_PT_weapon_props,
    RIG_PT_vis_props,
    RIG_PT_snap_panel,
    RIG_OT_ik_fk_arm,
    RIG_OT_fk_ik_arm,
    RIG_OT_ik_fk_leg,
    RIG_OT_fk_ik_leg,
)

register, unregister = bpy.utils.register_classes_factory(classes)

if __name__ == "__main__":
    register()