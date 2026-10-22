# Rotation Isolation

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

Lets the first FK control of a chain choose whether or not to follow its parent's rotation.

## Overview

Normally, when a parent bone rotates, its children rotate with it.  Rotation isolation adds a switch so the first FK control of the chain can ignore its parent's rotation, while still moving with it.  For example, with an isolated arm, rotating the chest will carry the shoulder joint with it, but the arm will keep pointing in the same direction.

This creates a custom property on the *[property bone](../armature_settings.md#property-bone)*.  The *[Rig Properties](../rigui/properties.md)* panel displays it as **FK Rotation Follow**, a slider with On/Off buttons next to it:

- On (1.0): the FK control follows its parent's rotation.  This is the default.
- Off (0.0): the FK control's rotation is isolated from its parent.

Values in between blend the two.

The *[torso](torso_fk.md)* has separate rotation isolation for the neck and the head.  These show up as **Neck FK Rotation Follow** and **Head FK Rotation Follow**.

!!! note
    Rotation isolation only affects the FK controls.  IK controls already ignore the rotation of the chain's parent.  See *[IK parent switching](ik_parent.md)* for choosing what the IK controls follow.

!!! screenshot "Image placeholder"
    `image/rotation_isolation.png` — Side-by-side of an FK arm with the chest rotated: on the left with FK Rotation Follow on (arm swings with the chest), on the right with it off (arm keeps its world orientation).

## Parameters

- Add Rotation Isolation: add the rotation isolation switch to the first FK control.  Default: on for Arm, Leg, Skirt FK, Tail, and the spline assemblies.  Off for Simple FK and FK Only.
- Inherit Scale From Root: the FK chain takes its scale from the *[root bone](../armature_settings.md#settings)* instead of the chain's parent.  Scaling the chest, for example, won't scale the arm.  Only shown when rotation isolation is enabled.  Default: on for Arm, off for Leg.

The *[torso](torso_fk.md)* has the same options for the neck and the head:

- Add Neck Rotation Isolation / Add Head Rotation Isolation.  Default: on.
- Neck Inherit Scale From Root / Head Inherit Scale From Root.  Default: on.

## Related

- [FK Assemblies](../fk_assemblies.md)
- [IK Assemblies](../ik_assemblies.md)
- [Torso FK](torso_fk.md)
- [Rotation Follow](rotation_follow.md)
