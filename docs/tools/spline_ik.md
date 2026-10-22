# Spline IK

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

Builds a spline IK setup with controls placed along a curve, plus optional twist controllers.  Used by the Skirt - Spline, Hair - Spline, and Tail - Spline assemblies.

## Overview

Creates a hidden curve that runs along the chain, and a set of controls evenly spaced along it.  Moving a control bends the curve, and the chain follows the curve.  The controls can only be moved; rotation and scale are locked.

Twist controllers can be added at the start, end, or every control.  Twist controllers only rotate around their length.  Twist is blended along the chain between neighboring twist controllers.

Like the *[standard IK](standard_ik.md)*, spline IK drives the MCH-IK bones created by the *[FK/IK switch](fk_ik_switch.md)*, so the chain can be switched between FK and spline IK.

!!! note
    Spline IK does not support *[FK <> IK snapping](../rigui/properties.md#snapping)*.  A spline IK pose often cannot match an FK chain.
    Limb *[twist bones](twist_bones.md)* are also unavailable; use the spline twist controllers instead.

!!! screenshot "Image placeholder"
    `image/spline_ik.png` — A Hair - Spline assembly in Pose mode with IK enabled, showing the sphere controls along the chain and the twist widgets on each control.  Ideally the middle control is moved so the chain is visibly bent.

## Parameters

- Spline Control Count: the number of controls along the curve.  Controls are always placed at the start and end of the chain, with the rest evenly spaced between them.  Default: 3 (4 for Tail - Spline).  Range: 2-10.
- Twist Type: where to create twist controllers.  Default: Start and End (All for Hair - Spline).
    - None: no twist controllers.
    - Start and End: twist controllers on the first and last controls.
    - Start: twist controller on the first control only.
    - End: twist controller on the last control only.
    - All: twist controllers on every control.
- Skip First: leave the first bone out of the spline.  The first bone stays attached to the parent of the chain and the spline starts at the second bone.  Useful for skirts, where the top of the skirt should stay attached to the hips.  Default: off (on for Skirt - Spline).
- Skip Last: leave the last bone out of the spline.  The last bone gets an FK control instead.  Default: off.
- Tip Widget: the custom bone shape for the last bone when Skip Last is enabled.  Default: CIRCLE.  See *[widgets](../utils/widget.md)*.

## Related

- [IK Assemblies](../ik_assemblies.md)
- [FK/IK Switching](fk_ik_switch.md)
- [IK Parent Switching](ik_parent.md)
- [Master Controllers](master_controllers.md)
