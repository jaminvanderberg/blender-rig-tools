# Parent Along Chain

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

Parents the selected bones into chains, based on where their heads and tails meet.

**Where:** n-Panel > RigTools > Tools > Parent Along Chain (Edit mode)
{ .where }

## Overview

Assemblies only care about parenting, so bones that line up end to end but aren't parented won't be recognized as a chain.  This tool fixes that.  For each selected bone, it looks for another selected bone whose tail sits on its head, and parents the bone to it.

Many chains can be fixed at once.  Select all of the bones in all of the chains, and run the tool.

A bone is skipped (and reported) when:

- More than one selected bone's tail is close enough to its head.  The tool can't tell which one should be the parent.
- Parenting it would create a loop.

Bones with nothing close enough are left alone.  These are usually the first bone of each chain.

!!! screenshot "Image placeholder"
    `image/parent_along_chain.png` — Before/after Edit mode view of several unparented skirt bones (no relationship lines) and the same bones parented into chains (relationship lines visible).

## Parameters

- Scan Distance: how close a bone's tail must be to another bone's head to be parented.  Increase this if the bones don't line up exactly.  Default: 0.0001 m.
- Parent Connected: connect each bone to its new parent, locking its head to the parent's tail.  Default: off.

## Related

- [Assemblies](../assemblies.md#selection)
- [Selection](../selection.md)
- [Rename Chain(s)](rename_chain.md)
