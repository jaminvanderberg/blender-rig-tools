# RigTools Human Skeleton

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

Adds a new human DEF skeleton, ready to fit to a character.

**Where:** Add > Armature > RigTools Human Skeleton (Object mode)
{ .where }

## Overview

Creates a new armature at the 3D cursor with a basic humanoid deform skeleton.  The bones are named and parented the way the RigTools templates expect, so the skeleton can go straight into the *[workflow](../workflow.md)* after it's fit to the character.

The skeleton includes:

- A root bone and a *[property bone](../armature_settings.md#property-bone)*.
- Hips, two spine bones, chest, neck, and head.
- Shoulders, arms, forearms, and hands.
- Palms, three-bone fingers, and three-bone thumbs (optional).
- Thighs, shins, feet, and toes.
- Heel pivots for both feet, already assigned for *[foot roll](../tools/foot_roll.md#heel-pivot)*.

The deform bones are placed in a **DEF** bone collection, the root and property bones in **Root**, and the heel pivots in **PIVOT**.

The skeleton doesn't include twist bones.  Add them with *[Create Twist Bones](create_twist_bones.md)* after fitting the skeleton, if desired.

!!! screenshot "Image placeholder"
    `image/human_skeleton.png` — The RigTools Human Skeleton in A-Pose, front view, next to the redo panel showing Height, Pose, Include Fingers, and Apply Root Widgets.

## Parameters

- Height: the total height of the skeleton.  Default: about 1.65 m.
- Pose: the arm pose.  Default: A-Pose.
    - A-Pose: arms lowered 45 degrees.
    - T-Pose: arms horizontal.
- Include Fingers: create the palm, finger, and thumb bones.  Default: on.
- Apply Root Widgets: add widgets to the root and property bones.  See *[Apply Root Widgets](apply_root_widgets.md)*.  Default: on.

!!! tip
    Use X-Axis Mirror in Edit mode while fitting the skeleton to keep the left and right sides matched.

## Related

- [Workflow](../workflow.md)
- [Create Twist Bones](create_twist_bones.md)
- [Generate ORG Bones](generate_org_bones.md)
- [Armature Settings](../armature_settings.md)
