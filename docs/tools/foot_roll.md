# Foot Roll

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

Adds a foot roll control to the IK foot, for rolling onto the heel or the ball of the foot, and rocking side to side.  Used by the Leg assembly.

!!! requires "Requires"
    A heel pivot bone assigned to the foot · at least one bone past the foot (the toe)

## Overview

Creates a roll control attached to the IK foot control.  Rotating the roll control:

- **Forward/back (X rotation)**: rolls the foot onto the heel in one direction, and onto the ball of the foot in the other.  When rolling onto the ball, the toe stays planted on the ground.
- **Side to side (Z rotation)**: rocks the foot onto its inside or outside edge.

The roll control's location and scale are locked.  The IK foot control is moved down to the ground, from the heel to the tip of the toe, so it's easier to see and select.

!!! screenshot "Image placeholder"
    `image/foot_roll.png` — A leg in IK mode showing the flattened IK foot control on the ground and the roll control behind the heel.  Ideally a second shot with the roll control rotated so the foot is up on the ball with the toe planted.

### Heel pivot

The heel pivot is a bone that tells the foot roll where the heel is.  It should sit at the back of the heel, on the ground, and run across the width of the foot.  The ends of the heel pivot are used as the pivot points when the foot rocks side to side.

The heel pivot is assigned to the **foot** bone (not the toe) in **Bone Properties > Rig Tools > Heel Pivot**.  The *[RigTools Human Skeleton](../operators/human_skeleton.md)* includes heel pivots that are already assigned.

Heel pivots can be assigned to the DEF foot bones before creating the ORG bones.  *[Generate ORG Bones](../operators/generate_org_bones.md)* copies the assignment to the ORG foot.

!!! screenshot "Image placeholder"
    `image/heel_pivot.png` — Edit mode view of a foot showing where the heel pivot bone should be placed (at the back of the heel, on the ground, spanning the width of the foot), plus the Heel Pivot field in Bone Properties > Rig Tools.

## Parameters

- Add Foot Roll: add the foot roll control.  Default: on for the Leg assembly.

## Related

- [IK Assemblies](../ik_assemblies.md#leg)
- [Standard IK](standard_ik.md)
- [ORG & DEF](../org_def.md#heel-pivots)
