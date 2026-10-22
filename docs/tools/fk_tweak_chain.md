# FK Tweak Chain

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

Creates an FK chain with tweak controls at each joint.

## Overview

Creates an FK control for each bone in the chain, plus a small tweak control at each joint.  An additional tweak is added at the end of the chain.  Moving a tweak stretches the bones on either side of it, which lets the animator adjust the deformation after the FK (or IK) pose is set.

This is used by the Simple FK, Skirt FK, Tail, and Finger assemblies.  The IK assemblies, the *[torso](torso_fk.md)*, and the *[twist bones](twist_bones.md)* use the same tweak controls.

See *[FK Chain](fk_chain.md)* for an FK chain without tweak controls.

!!! screenshot "Image placeholder"
    `image/fk_tweak_chain.png` — A 3-4 bone chain in Pose mode showing the FK widgets and the small sphere tweak widgets at each joint, including the extra tweak at the end of the chain.  Ideally one tweak is moved so the stretch is visible.

### Skip first tweak

When **Skip First Tweak** is enabled, no tweak is created at the start of the chain.  The Finger assemblies use this so the base of the finger doesn't get a tweak control sitting on top of the knuckle.

## Parameters

- Add Tweak Bones: create the tweak controls.  When disabled, the assembly creates an *[FK only](fk_chain.md)* chain.  Default: on.
- FK Widget: the custom bone shape to use for FK controls.  Default: CIRCLE.  See *[widgets](../utils/widget.md)*.
- Skip First Tweak: don't create a tweak at the start of the chain.  Default: off (on for the Finger assemblies).

## Related

- [FK Chain](fk_chain.md)
- [FK Assemblies](../fk_assemblies.md)
- [IK Assemblies](../ik_assemblies.md)
