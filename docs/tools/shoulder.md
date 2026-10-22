# Shoulder

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

Creates a single FK control for a humanoid shoulder (clavicle).  Used by the Shoulder assembly.

!!! requires "Requires"
    The shoulder bone selected · usually parented to the chest

## Overview

Creates one FK control with a shoulder-shaped widget.  The widget is drawn above the shoulder, angled slightly downward toward the arm, so it's easy to grab without getting in the way of the arm controls.

The shoulder is grouped with the arm on the same side.  Its control shows up in both the arm's FK and IK bone collections, so it's available no matter which mode the arm is in.

Create the shoulder before or after the *[Arm](../ik_assemblies.md#arm)* assembly.  Select only the shoulder bone; the arm should be a separate assembly.

!!! screenshot "Image placeholder"
    `image/shoulder.png` — Front view of the upper body in Pose mode with both shoulder controls visible above the clavicles, alongside the arm FK controls.

## Parameters

- FK Widget: the custom bone shape to use for the shoulder control.  Default: SHOULDER.  See *[widgets](../utils/widget.md)*.

## Related

- [FK Assemblies](../fk_assemblies.md#shoulder)
- [IK Assemblies](../ik_assemblies.md#arm)
- [FK Chain](fk_chain.md)
