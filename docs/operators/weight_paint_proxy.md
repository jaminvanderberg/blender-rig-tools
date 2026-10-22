# Weight Paint Proxy

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

Creates a simple mesh from the selected bone chains, with starting weights, to help weight paint chains like skirts, capes, and hair.

**Where:** n-Panel > RigTools > Tools > Weight Paint Proxy (Edit or Pose mode)
{ .where }

## Overview

Automatic weights often struggle with cloth and hair chains, especially when the chains are close together like a skirt.  The weight paint proxy is a stand-in mesh built directly from the bones.  It gets a vertex at each joint, a vertex group for each bone, and starting weights that blend between neighboring bones.  The proxy can be cleaned up in Weight Paint mode, then the weights transferred to the real mesh (for example, with a Data Transfer modifier).

With multiple chains selected, the chains can be stitched together into a single surface, like a skirt or a cape.  The chains can also be stitched into a closed loop, like a skirt that goes all the way around.

When the tool runs, it switches to Weight Paint mode on the new proxy so you can start painting right away.

This tool might help in some niche cases.  For most characters, standard weight painting is all that's needed.

!!! note
    The proxy is flagged as a helper object, so it's ignored by the *[Visibility](../rigui/visibility.md)* panel.

!!! screenshot "Image placeholder"
    `image/weight_paint_proxy.png` — A skirt's bone chains with a stitched, closed-loop weight paint proxy in Weight Paint mode, showing the blended weights for one bone.

### Chain order

To stitch chains together, the tool needs to know which chain is next to which.  While the dialog is open, the order of the chains is shown in the viewport as numbers next to the first bone of each chain.

- Order Mode: Angular orders the chains by their angle around the center of the selection (good for skirts).  Linear orders the chains along an axis (good for capes or bangs).
- Order Axis: the axis to rotate around (Angular) or sort along (Linear).  Default: Z.
- Order Start Angle: the angle where the first chain starts (Angular only).  Default: 0.
- Order Invert: reverse the order.

## Parameters

- Stitch Chain: join multiple chains into a single surface.  When disabled, each chain is a separate line of vertices.  Default: on.
- Chain Align: when chains have different lengths, which end lines up.  Start lines up the roots; End lines up the tips.  Only shown when the chains are different lengths.  Default: Start.
- Close Loop: stitch the last chain back to the first.  Default: on.
- Object Name: the name of the new object.  `{armature}` is replaced with the name of the armature.  Default: `WProxy-{armature}`.
- Seed Weights: create vertex groups for each bone, with each joint weighted fully to its bone.  Default: on.
- Spread Weights: blend the weights between neighboring vertices.  Default: on.
    - Spread Along Chain: how much weight spreads up and down each chain.  Default: 0.10.
    - Spread Across Chain: how much weight spreads to neighboring chains.  Default: 0.10.
    - Iterations: how many times to repeat the spread.  More iterations give smoother, wider blending.  Default: 1.
    - Lock Root Rows: the number of rows at the root of the chains that don't spread weight along the chain.  Keeps the top of a skirt firmly attached.  Default: 1.
- Armature Modifier: add an Armature modifier to the proxy.  Default: on.

## Related

- [Workflow](../workflow.md)
- [Rename Chain(s)](rename_chain.md)
