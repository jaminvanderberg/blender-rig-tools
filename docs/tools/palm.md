# Palm

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

Creates FK controls for the palm bones, with the index and pinky palms acting as controls for the palm bones between them.  Used by the Palm assembly.

!!! requires "Requires"
    Palm bones selected (one per finger) · usually children of the hand

## Overview

The palm bones (sometimes called metacarpals) are not a chain.  They are usually siblings, all parented to the hand.  So unlike the other assemblies, the palm is created from a selection of individual bones, one per finger.  Both hands can be selected at the same time.

Each palm bone gets an FK control.  The first palm (usually the index) and the last palm (usually the pinky) act as controls for the palm bones between them: rotating the index or pinky palm also rotates the middle palms, fading out toward the other side of the hand.  This makes cupping and spreading the hand easy with only two controls.  The middle palm controls can still be posed on top of that.

!!! screenshot "Image placeholder"
    `image/palm.png` — A hand with a Palm assembly, showing the pill-shaped FK controls on each palm bone, with the pinky palm rotated so the hand cups and the middle palms follow partway.

### Palm order

Since the palm bones aren't a chain, the Palm assembly opens a dialog to confirm the order of the bones, from index to pinky.  The order can be set by:

- Name: the trailing letter or number in the bone names (for example, `palm.A`, `palm.B`, ...).  Only available when all of the selected bones have one.
- X, Y, Z: the position of the bones along that axis.
- Manual: use the arrow buttons to move bones up or down the list.

**Reverse** flips the order.  When both hands are selected, the left and right bones are shown side by side and must mirror each other.

!!! screenshot "Image placeholder"
    `image/palm_order.png` — The Palm dialog showing the Order section with Name/X/Y/Z/Manual, Reverse, and the Left/Right columns with up/down arrows.

## Parameters

- Index Falloff Type: how quickly the first palm's (index) rotation fades across the middle palms.  Default: Sharp.
- Pinky Falloff Type: how quickly the last palm's (pinky) rotation fades across the middle palms.  Default: Linear.
- FK Widget: the custom bone shape to use for the palm FK controls.  Default: PILL.  See *[widgets](../utils/widget.md)*.

See *[Twist Bones (tool)](twist_bones.md#falloff)* for a description of the falloff types.  The palm also offers a **None** falloff, which turns off that side's influence on the middle palms.

## Related

- [FK Assemblies](../fk_assemblies.md#palm)
- [Finger Curl](finger_curl.md)
- [IK Assemblies](../ik_assemblies.md#arm)
