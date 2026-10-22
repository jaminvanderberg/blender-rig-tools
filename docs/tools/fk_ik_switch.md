# FK/IK Switching

Builds the FK/IK blend mechanism so a limb can switch between FK and IK control stacks.

## Overview

Creates the primary mechanism for switching between FK and IK setups.  Creates a custom property on the *[property bone](../armature_settings.md#property-bone)*.  The *[RigUI Properties](../rigui/properties.md)* will display this property as a float slider with FK/IK radio buttons next to it. This makes it easy to switch between FK and IK, while still giving full animator control for transitioning between them.

This tool creates the final FK chain and controls, but doesn't create the IK chain.  It creates MCH-IK bones that will be controlled by an IK chain created in a later step.  See *[standard IK](standard_ik.md)* and *[spline IK](spline_ik.md)* for IK chain creation.

!!! screenshot "Image placeholder"
    `image/fk_ik_switch_property.png` — Close-up of the Rig Properties panel showing the FK > IK Switch slider with its FK / IK buttons, and the IK > FK / FK > IK snap buttons below.

## Parameters

- FK Widget: the custom bone shape to use for FK controls.  Default varies by assembly type.  See *[widgets](../utils/widget.md)*.
- FK End Widget: the custom bone shape for the last FK control in the chain (the hand or foot).  Default: CIRCLE.  See *[widgets](../utils/widget.md)*.

## Related

- [IK Assemblies](../ik_assemblies.md)
- [FK <> IK Snapping](../rigui/properties.md#snapping)
