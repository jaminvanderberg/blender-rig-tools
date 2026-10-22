# Skirt Ride

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

Makes short skirts ride up when a leg is lifted.

!!! requires "Requires"
    Leg assemblies set up first (recommended) · or thigh bones picked manually

## Overview

When a leg is lifted, a short skirt tends to get pulled up with it.  Skirt ride shortens the top bone of each skirt chain as the thigh swings forward, which raises the rest of the chain.  Chains closest to the front of the lifted leg ride up the most; chains on the far side of the skirt aren't affected.

Skirt ride is intended for short skirts.  It's disabled by default, and is usually not needed for longer skirts and dresses.  It can be combined with *[skirt collision](skirt_collision.md)*.

Skirt ride works on the FK side of the chain.  On the Skirt - Spline assembly, ride only applies while the skirt is in FK.

The ride can be turned on and off by the animator with the **Leg Ride** property in the *[Rig Properties](../rigui/properties.md)* panel.  Ride is on by default when it's been added.

!!! screenshot "Image placeholder"
    `image/skirt_ride.png` — A short Skirt FK assembly with one thigh lifted forward, comparing Leg Ride on (front chains shortened and raised) vs. off.

### Skirt legs

Skirt ride uses the same **Skirt Legs** list as *[skirt collision](skirt_collision.md#skirt-legs)*.  When skirt ride is enabled, each leg also has a **Forward Axis**: the axis of the thigh bone that points forward, toward the front of the character.  This is detected automatically, and usually doesn't need to be changed.  If the skirt rides up when the leg moves backward instead of forward, try the opposite axis.

### Ride influence

Each skirt chain gets a ride influence for each leg, based on where the chain sits around the thigh.  After the assembly is created, these can be adjusted in the *[Assembly Panel](../assemblies.md#assembly-panel)*.  Each leg has a slider from 0 to 2 (higher values can be typed in).  Higher values make the chain ride up more for the same leg lift.

These values are kept when the assembly is reconfigured.

## Parameters

- Add Skirt Ride: add skirt ride to the chain.  Default: off.
- Skirt Legs: the thigh bones that make the skirt ride up, with the forward axis of each thigh.  Filled in automatically from the Leg assemblies.

## Related

- [Skirt Collision](skirt_collision.md)
- [FK Assemblies](../fk_assemblies.md#skirt-fk)
- [IK Assemblies](../ik_assemblies.md#skirt-spline)
