# Master Controllers

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

Adds controls that rotate a group of FK bones at once.  Useful for curling tails, hair, and cloth with a single control.

## Overview

Master controllers come in two types:

- **Use FK Bones** (FK follow): an existing FK control acts as the master.  When it rotates, the FK controls after it rotate by the same amount, which curls the rest of the chain.  No extra controls are created.  See *[Rotation Follow](rotation_follow.md)*.
- **Add Dedicated Masters**: a separate, larger master control is created for each group.  Rotating, moving, or scaling the master moves every FK control in its group, including the first one.  The individual FK controls can still be posed on top of that.

Each FK control still works normally.  The master controllers add on top of the animator's FK pose.

Masters use the FK Master *[color](../armature_settings.md#control-colors)*.  FK follow masters stay in the limb's FK collection.  Dedicated masters get their own collection, and the FK controls move to a separate FK collection.  See *[bone collections](../rigui/collections.md#assembly-bone-collections)*.

The chain can be split into groups with an interval, so a long tail can have a master every few bones instead of one for the whole chain.

!!! screenshot "Image placeholder"
    `image/master_controllers.png` — A Tail assembly in Pose mode with dedicated master controls (every 3 bones).  One master is rotated, showing its group of FK controls curling together.

## Parameters

- Create FK Master Controllers / FK Follow: enable master controllers.  Default: on for Simple FK, FK Only, Skirt FK, Tail, Finger (FK), and the spline assemblies.  Off for Arm, Leg, Finger (Curl), and Shoulder.
- Type: the type of master controller.  Default: Use FK Bones (Add Dedicated Masters for Skirt FK, Tail, and Tail - Spline).
    - Use FK Bones: existing FK controls act as masters (FK follow).
    - Add Dedicated Masters: separate master controls are created.
- Spacing: how the chain is divided.
    - Single Controller: one master for the whole chain.
    - Interval: a new master every *Interval* bones.  Default interval: 3 (minimum 2).
- Skip First: leave the first bone of the chain out of the master controllers.  The second bone becomes the first master.  Default: on for all templates.
- Master Controller Widget: the custom bone shape for dedicated masters.  Only shown when the type is Add Dedicated Masters.  Default: CIRCLE (RECTANGLE for skirts).  See *[widgets](../utils/widget.md)*.

!!! tip
    Skip First is useful when the first bone acts as an anchor, like the base of a tail or the top of a skirt.  For fingers, it lets the second knuckle curl the finger without moving the knuckle at the base.

## Related

- [Rotation Follow](rotation_follow.md)
- [FK Assemblies](../fk_assemblies.md)
- [IK Assemblies](../ik_assemblies.md)
