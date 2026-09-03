import bpy
import mathutils
import math
from .widgets import load_widget_shape

class EYE_OT_add_targets(bpy.types.Operator):
    """Create eye target bones and constraints"""
    bl_idname = "rig.add_eye_targets"
    bl_label = "Add Eye Targets"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):

        DIST = 0.1  # Target distance in meters
        ARM = bpy.context.object

        if ARM is None or ARM.type != 'ARMATURE' or bpy.context.mode != 'POSE':
            raise Exception("Please select an armature and be in Pose Mode.")

        selected = bpy.context.selected_pose_bones
        if len(selected) != 2:
            raise Exception("Select exactly two eye bones.")

        eye1, eye2 = selected[0], selected[1]

        # Switch to Edit Mode
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = ARM.data.edit_bones

        # Helper to create a target bone pointing upward at a distance in front of eye
        def make_target_bone(source_bone, name):
            src = edit_bones[source_bone.name]
            mat = ARM.matrix_world @ src.matrix
            head = mat.translation
            dir = mat.to_quaternion() @ mathutils.Vector((0, DIST, 0))
            pos = head + dir

            b = edit_bones.new(name)
            b.head = pos
            b.tail = pos + mathutils.Vector((0, 0, 0.1))  # Tail points up (Z+)
            b.parent = None
            return b.name

        # Create target bones
        target1_name = make_target_bone(eye1, f"target_{eye1.name}")
        target2_name = make_target_bone(eye2, f"target_{eye2.name}")

        # Midpoint for both eyes target
        pos1 = edit_bones[target1_name].head
        pos2 = edit_bones[target2_name].head
        mid = (pos1 + pos2) / 2

        b_both = edit_bones.new("target_eyes")
        b_both.head = mid
        b_both.tail = mid + mathutils.Vector((0, 0, 0.1))  # Point up
        b_both.parent = None
        target_both_name = b_both.name

        # Parent the two eye targets to the "both eyes" target
        edit_bones[target1_name].parent = b_both
        edit_bones[target2_name].parent = b_both

        # Back to Pose Mode for constraints
        bpy.ops.object.mode_set(mode='POSE')
        pose_bones = ARM.pose.bones

        # Add Damped Track and slow it down using influence and damping (via Copy Rotation if needed)
        for eye_name, target_name in [(eye1.name, target1_name), (eye2.name, target2_name)]:
            con = pose_bones[eye_name].constraints.new('DAMPED_TRACK')
            con.target = ARM
            con.subtarget = target_name
            con.track_axis = 'TRACK_Y'
            con.influence = 0.8  # Slight delay/softness

        shape_both = load_widget_shape("WGT-rounded")
        shape_single = load_widget_shape("WGT-circle")
        
        pose_bones["target_eyes"].custom_shape = shape_both
        pose_bones["target_eyes"].custom_shape_rotation_euler = (0, 0, math.radians(-90))
        pose_bones["target_eyes"].custom_shape_scale_xyz = (1.5, 1.5, 1.5)
        for name in ["target_" + eye1.name, "target_" + eye2.name]:
            bone = pose_bones[name]
            bone.custom_shape = shape_single
            bone.custom_shape_rotation_euler = (math.radians(90), 0, 0)
            bone.custom_shape_scale_xyz = (0.4, 0.4, 0.4)

        self.report({'INFO'}, "Eye targets created.")
        
        return {'FINISHED'}
