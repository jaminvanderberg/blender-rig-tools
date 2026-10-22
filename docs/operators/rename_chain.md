# Rename Chain(s)

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

Renames one or more selected chains using a template, with a number or letter for each chain and each bone.

**Where:** n-Panel > RigTools > Tools > Rename Chain(s) (Edit or Pose mode)
{ .where }

## Overview

Renaming dozens of skirt or hair bones by hand is tedious.  This tool renames every bone in the selected chains in one step.  For example, with the default template `bone.{chain}.{bone}`, three skirt chains become:

- `bone.a.01`, `bone.a.02`, `bone.a.03`, ...
- `bone.b.01`, `bone.b.02`, `bone.b.03`, ...
- `bone.c.01`, `bone.c.02`, `bone.c.03`, ...

With only one chain selected, `{chain}` isn't replaced, so leave it out of the template (for example, `ponytail.{bone}`).

Bones are numbered from the root of each chain toward the tip.  When multiple chains are selected, the chains are ordered the same way as the *[Weight Paint Proxy](weight_paint_proxy.md#chain-order)*, and the order is shown in the viewport while the dialog is open.

!!! tip
    Include the `DEF-` prefix and side suffix in the template when renaming deform bones, for example `DEF-skirt.{chain}.{bone}`, so *[Generate ORG Bones](generate_org_bones.md)* can find them.

!!! screenshot "Image placeholder"
    `image/rename_chain.png` — The Rename Chain(s) dialog with several skirt chains selected, and the chain order letters drawn in the viewport next to each chain.

## Parameters

- Name Template: the template for the new names.  `{chain}` is replaced with the chain's number or letter, and `{bone}` with the bone's number or letter.  Default: `bone.{chain}.{bone}`.
- Chain Name Type: how chains are numbered.  Only shown when more than one chain is selected.  Default: Lowercase Letter.
- Bone Name Type: how bones are numbered.  Default: 2 Digit.

The name types are:

- 2 Digit: `01`, `02`, `03`, ...
- 3 Digit: `001`, `002`, `003`, ...
- Lowercase Letter: `a`, `b`, `c`, ...
- Uppercase Letter: `A`, `B`, `C`, ...

The chain order settings (Order Mode, Order Axis, Order Start Angle, Order Invert) are the same as the *[Weight Paint Proxy](weight_paint_proxy.md#chain-order)*.

## Related

- [Selection](../selection.md)
- [Weight Paint Proxy](weight_paint_proxy.md)
- [Parent Along Chain](parent_along_chain.md)
