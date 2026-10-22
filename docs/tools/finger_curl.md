# Finger Curl

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

Adds a single curl control to a finger, similar to Rigify's finger controls.  Used by the Finger (Curl) assembly.

## Overview

Creates a large control over the finger.  The control works like an FK control for the whole finger: rotating it rotates the finger from the base.  Scaling the control along its length curls the finger:

- Scale down: the finger curls into a fist.
- Scale back to 1.0: the finger straightens.

The individual FK controls and tweaks can still be posed on top of the curl.

The Finger (Curl) assembly also creates an *[FK Tweak Chain](fk_tweak_chain.md)* without a tweak at the base of the finger.

!!! screenshot "Image placeholder"
    `image/finger_curl.png` — A hand with Finger (Curl) assemblies, showing the paddle-shaped curl controls over each finger, with one curl control scaled down so its finger is curled.

## Parameters

- Finger Curl Axis: the axis the finger curls around.  Default: Auto.
    - Auto: detects the direction from the bend in the finger.  If the finger is completely straight, it uses X.
    - X, -X, Z, -Z: curl around this axis of the finger bones.  Use these if Auto curls the finger the wrong way.
- FK Widget: the custom bone shape to use for FK controls.  Default: CIRCLE.  See *[widgets](../utils/widget.md)*.
- Add Tweak Bones / Skip First Tweak: see *[FK Tweak Chain](fk_tweak_chain.md)*.

!!! tip
    Model the fingers with a slight natural curl.  This helps Auto pick the correct curl direction.

## Related

- [FK Assemblies](../fk_assemblies.md#finger-curl)
- [FK Tweak Chain](fk_tweak_chain.md)
- [Palm](palm.md)
