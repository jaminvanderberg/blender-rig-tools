# Standard IK

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

Builds a standard IK chain with an IK control and a pole target.  Used by the Arm and Leg assemblies.

## Overview

Creates the IK chain that drives the MCH-IK bones created by the *[FK/IK switch](fk_ik_switch.md)*.  The last bone of the IK chain becomes the IK control (the hand or foot), and the bones before it are solved by the IK.  With the default IK bone count of 3, that's two IK bones (upper arm and forearm) and the hand as the control.

A pole target is created automatically and placed out from the middle joint (the elbow or knee) in the direction the chain bends.  A line is drawn from the pole to the joint so it's easy to see which joint it belongs to.

!!! tip
    Model the limb with a slight bend at the elbow or knee.  The bend tells the tool which direction the joint should bend and where to place the pole.  A perfectly straight limb will still work, but the pole may end up on the wrong side.

Any bones in the chain past the IK control (like the toe on a leg) get their own FK control that is shared between FK and IK.

The IK chain can stretch past its rest length.  This can be turned off by the animator with the **IK Stretch** property in the *[Rig Properties](../rigui/properties.md)* panel.  Stretch is on by default.

*[FK <> IK snapping](../rigui/properties.md#snapping)* is set up automatically.

!!! screenshot "Image placeholder"
    `image/standard_ik.png` — An arm assembly in Pose mode with IK enabled, showing the IK control on the hand, the pole target behind the elbow, and the line connecting the pole to the elbow.

## Parameters

- IK Bone Count: the number of bones from the start of the chain used for the IK, including the IK control.  Any remaining bones get FK controls that are shared between FK and IK.  Default: 3.  Minimum: 2.
- Add Foot Roll: adds a *[foot roll](foot_roll.md)* control to the IK control.  Requires a heel pivot and at least one bone past the IK chain (the toe).  Default: on for the Leg assembly.
- Tip Widget: the custom bone shape for the FK controls past the IK control (the toe).  Default: CIRCLE.  See *[widgets](../utils/widget.md)*.

## Related

- [IK Assemblies](../ik_assemblies.md)
- [FK/IK Switching](fk_ik_switch.md)
- [IK Parent Switching](ik_parent.md)
- [Foot Roll](foot_roll.md)
