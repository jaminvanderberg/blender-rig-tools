# Generate ORG Bones

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

Creates an ORG bone for every DEF bone, and links the DEF bones to follow the ORG bones.

**Where:** n-Panel > RigTools > Tools > Generate ORG Bones
{ .where }

## Overview

Assemblies are built on ORG bones, not on the deform bones directly.  Generate ORG Bones duplicates each DEF bone as an ORG bone, with the same hierarchy, and adds a Copy Transforms constraint so the DEF bone follows its ORG bone.  See *[ORG & DEF](../org_def.md)* for why the rig is split this way.

It's safe to run Generate ORG Bones more than once.  ORG bones that already exist aren't changed (other than making sure the DEF bone is linked to them), and only the missing ORG bones are created.  This makes it easy to add new DEF bones to the rig later, such as an accessory or a skirt, and generate ORG bones for just those.

Twist bone and heel pivot assignments are copied from the DEF bones to the new ORG bones.  See *[Twist Bones](../twist_bones.md)* and *[Foot Roll](../tools/foot_roll.md#heel-pivot)*.

!!! screenshot "Image placeholder"
    `image/generate_org_bones.png` — The Generate ORG Bones dialog with its default settings.

## Parameters

- Bone Selection: which DEF bones to process.  Default: Selected Bones.
    - Selected Bones: only the selected DEF bones.  Requires Edit or Pose mode.
    - Visible Bones: all visible DEF bones.
    - All Bones: all DEF bones in the armature.
- DEF Bone Name: the naming template used to find DEF bones.  Default: `DEF-{name}` (from the *[addon preferences](../armature_settings.md#naming)*).
- Target Bone Name: the naming template for the new ORG bones.  Default: `ORG-{name}` (from the addon preferences).
- Relationship Type: how the DEF bones follow the ORG bones.  Default: Copy Transforms.
    - Copy Transforms: the DEF bone gets a Copy Transforms constraint targeting its ORG bone.  The DEF hierarchy is left alone.
    - Parent/Child: the DEF bone is parented to its ORG bone.
- DEF Bone Collection: the name used for DEF bone collections.  Default: `DEF`.
- Target Bone Collection: the name used for ORG bone collections.  Default: `ORG`.
- Copy Collection Structure: copy the DEF bone collections for the ORG bones, replacing "DEF" with "ORG" in the collection names.  For example, bones in `DEF.Skirt` go into `ORG.Skirt`.  When disabled, all ORG bones go into a single collection.  Default: on.
- Disable To Bone Deform: turn off deform on the new ORG bones, so only the DEF bones deform the mesh.  Default: on.

`.L` / `.R` suffixes are always kept at the end of the name, so `DEF-forearm.L` becomes `ORG-forearm.L`.

## Related

- [ORG & DEF](../org_def.md)
- [Workflow](../workflow.md)
- [Create Twist Bones](create_twist_bones.md)
