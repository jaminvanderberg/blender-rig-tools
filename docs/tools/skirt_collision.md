# Skirt Collision

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

Pushes skirt chains out of the way of the legs, so the legs don't poke through the skirt.

!!! requires "Requires"
    Leg assemblies set up first (recommended) · or thigh bones picked manually

## Overview

Each bone in the skirt chain is kept outside of the nearest thigh.  When the leg swings forward into the skirt, the skirt chain is pushed forward with it.  The FK controls can still be posed on top of the collision.

Skirt collision works on the FK side of the chain.  On the Skirt - Spline assembly, collision only applies while the skirt is in FK.

The collision can be turned on and off by the animator with the **Leg Collision** property in the *[Rig Properties](../rigui/properties.md)* panel.  Collision is on by default.

!!! screenshot "Image placeholder"
    `image/skirt_collision.png` — A Skirt FK assembly with one leg raised forward, showing the skirt chains in front of the thigh pushed outward instead of passing through the leg.

### Skirt legs

Skirt collision needs to know which bones are the legs.  When a skirt assembly is created, the **Skirt Legs** list is filled in automatically with the thigh of every Leg assembly in the rig.  Thighs can be added or removed from the list in the redo panel.

!!! tip
    Set up both legs with the *[Leg assembly](../ik_assemblies.md#leg)* before creating the skirt, and the skirt legs will be filled in for you.

### Collision influence

After the assembly is created, the collision strength of each bone in the skirt chain can be adjusted in the *[Assembly Panel](../assemblies.md#assembly-panel)*.  Each bone has a slider from 0 to 1 (values up to 2 can be typed in).  A value of 0 turns collision off for that bone; values above 1 push the skirt further out.

These values are kept when the assembly is reconfigured.

!!! screenshot "Image placeholder"
    `image/skirt_collision_influence.png` — The Assembly Panel for a skirt assembly, showing the Skirt Collision sliders for each bone in the chain.

## Parameters

- Add Skirt Collision: add skirt collision to the chain.  Default: on for Skirt FK and Skirt - Spline.
- Skirt Legs: the thigh bones the skirt collides with.  Filled in automatically from the Leg assemblies.

## Related

- [Skirt Ride](skirt_ride.md)
- [FK Assemblies](../fk_assemblies.md#skirt-fk)
- [IK Assemblies](../ik_assemblies.md#skirt-spline)
