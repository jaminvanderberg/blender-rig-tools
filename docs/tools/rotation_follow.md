# Rotation Follow

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

Makes the FK controls further down a chain follow the rotation of an earlier FK control.  This is the "Use FK Bones" type of *[master controller](master_controllers.md)*, often called "FK follow".

## Overview

With FK follow, rotating an FK control also rotates the FK controls after it by the same amount.  Rotating the base of a tail by 10 degrees bends every following bone by 10 degrees as well, so the whole tail curls instead of swinging as a straight line.

The following FK controls can still be rotated on their own.  Their rotation is added on top of what they pick up from the master.

FK follow is the default for Simple FK, FK Only, Finger (FK), Hair - Spline, and Skirt - Spline.  With Skip First enabled (the default), the second FK control is the master, so the first bone can be posed without curling the rest of the chain.

With an interval, each master only drives the bones up to the next master.  See *[Master Controllers](master_controllers.md)* for the full set of parameters.

!!! note
    This is not the same as the **FK Rotation Follow** property in the *[Rig Properties](../rigui/properties.md)* panel.  That property is part of *[rotation isolation](rotation_isolation.md)*, and controls whether the first FK control follows its parent.

!!! screenshot "Image placeholder"
    `image/rotation_follow.png` — A Simple FK hair strand with the second FK control rotated, showing the rest of the strand curling with it.

## Related

- [Master Controllers](master_controllers.md)
- [Rotation Isolation](rotation_isolation.md)
- [FK Assemblies](../fk_assemblies.md)
