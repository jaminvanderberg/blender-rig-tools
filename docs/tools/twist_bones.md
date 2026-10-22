# Twist Bones (tool)

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

Drives twist bones along a limb segment and adds tweak controls to them.  Used by the Arm and Leg assemblies.

## Overview

For each twist segment (for example, the upper arm and the forearm), the tool finds the twist bones that belong to that bone.  If there aren't any, it creates them.  The twist bones are then set up to pick up rotation from a control bone, with more rotation toward one end of the segment than the other.  How quickly the rotation fades along the segment is set by the falloff.

Each twist bone also gets a tweak control, the same as an *[FK Tweak Chain](fk_tweak_chain.md)*.  This gives arms and legs extra tweak controls along their length, even on segments that don't twist.

For concepts, creating twist bones ahead of time, and what happens when an assembly is deleted, see the main *[Twist Bones](../twist_bones.md)* page.

!!! warning
    If twist bones already exist for a segment, the twist bone count must match.  Otherwise, the assembly will fail with an error.

!!! screenshot "Image placeholder"
    `image/twist_segments.png` — The Twist Segments section of the Arm redo panel, showing the twist status message, Twist Bone Count, and the segment list (Name, Index, Source, Falloff).

## Parameters

- Use Twist Bones: enable twist bones for the assembly.  Default: on for Arm and Leg.
- Twist Bone Count: the number of twist bones per segment.  Default: 4.  Range: 2-16.
- Twist Segments: the list of limb bones that get twist bones.  Each segment has:
    - Name: a label for the segment.  Only used in the UI.
    - Index: which bone in the selected chain the segment belongs to, starting from 0.  For an arm, 0 is the upper arm and 1 is the forearm.
    - Source: where the twist comes from.
        - Self: twist comes from the segment's own control, like the upper arm or thigh.  The twist is strongest at the end of the segment, and fades out toward the shoulder or hip.
        - Child: twist comes from the next bone in the chain, like the forearm twisting with the hand.
        - None: no twist.  The twist bones are only used for deformation and extra tweak controls, like the shin.
    - Falloff: how the twist fades along the segment.  Not used when the source is None.

The twist status above the segment list shows whether twist bones already exist ("All twist bones present"), will be created ("Twist bones will be created"), or have a problem that needs to be fixed first.

### Falloff

Falloff controls how much of the twist each twist bone receives.  The bone at the end of the segment always gets the full twist.  The table below shows the amount of twist each bone receives with 4 twist bones, from the start of the segment to the end.

| Falloff | Bone 1 | Bone 2 | Bone 3 | Bone 4 |
| --- | --- | --- | --- | --- |
| Linear | 25% | 50% | 75% | 100% |
| Smooth | 16% | 50% | 84% | 100% |
| Round | 66% | 87% | 97% | 100% |
| Root | 13% | 29% | 50% | 100% |
| Sharp | 6% | 25% | 56% | 100% |

Root and Sharp keep most of the twist near the end of the segment.  Round spreads the twist almost evenly along the whole segment.

Default segments:

| Assembly | Segment | Source | Falloff |
| --- | --- | --- | --- |
| Arm | Arm | Self | Root |
| Arm | Forearm | Child | Linear |
| Leg | Thigh | Self | Sharp |
| Leg | Shin | None | — |

## Related

- [Twist Bones](../twist_bones.md)
- [IK Assemblies](../ik_assemblies.md)
- [Torso FK](torso_fk.md)
- [Create Twist Bones](../operators/create_twist_bones.md)
