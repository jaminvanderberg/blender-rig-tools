# Create Twist Bones

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

Creates a chain of twist bones on each selected DEF bone.

**Where:** n-Panel > RigTools > Tools > Create Twist Bones (Edit or Pose mode)
{ .where }

## Overview

Splits each selected DEF bone into a chain of twist bones, and assigns them as twist bones of the original bone.  Use this before weight painting, so the twist bones can be weight painted along with the rest of the rig.

Twist bones are usually created on the upper arms, forearms, thighs, shins, chest, and neck.  See *[Twist Bones](../twist_bones.md)* for more information.

- Only DEF bones (names starting with `DEF-`) are processed.  Other selected bones are skipped.
- Bones that already have the requested number of twist bones are skipped.
- If a bone already has twist bones, but a different number, the tool stops with an error.

The twist bones are created as deform bones in the same bone collections as the original bone.  The original bone isn't changed, including its deform setting.

!!! tip
    After the twist bones are created, run *[Generate ORG Bones](generate_org_bones.md)*.  The ORG twist bones are created and assigned automatically.

!!! screenshot "Image placeholder"
    `image/create_twist_bones.png` — An upper arm and forearm in Edit mode after Create Twist Bones, showing the twist bones running along each bone.

## Parameters

- Twist Bone Count: the number of twist bones created on each bone.  Default: 2.  Minimum: 2.

!!! note
    The *[Arm](../ik_assemblies.md#arm)* and *[Leg](../ik_assemblies.md#leg)* assemblies use 4 twist bones by default.  Use the same count here, or change the count in the assembly to match.

## Related

- [Twist Bones](../twist_bones.md)
- [Twist Bones (tool)](../tools/twist_bones.md)
- [Generate ORG Bones](generate_org_bones.md)
- [Workflow](../workflow.md)
