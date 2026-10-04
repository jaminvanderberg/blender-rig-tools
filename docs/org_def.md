# ORG & DEF

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

Rig Tools expects a clear split between **deform** bones and the **ORG** layer assemblies
run on. Most pipelines author DEF (skinned) bones first, generate ORG mirrors, then build
assemblies on ORG chains.

!!! tip
    Assemblies select “the chain you want to control” — by convention that is ORG.
    Naming templates and Generate ORG Bones assume patterns like `DEF-{name}` / `ORG-{name}`.

## Mental model

| Layer | Role |
| --- | --- |
| **DEF** | Deform / skinning. Weights live here. |
| **ORG** | Target layer for assemblies. Usually non-deform; DEF follows ORG (Copy Transforms or parent). |
| **Controls / MCH** | Created by assemblies (FK, IK, tweaks, switches, isolators, …). |

Typical order:

1. Build and weight the **DEF** skeleton.
2. Optionally set [twist parents](twist_bones.md) and [heel pivots](#heel-pivots) on DEF.
3. **Generate ORG Bones**.
4. Select ORG chains → [IK](ik_assemblies.md) / [FK](fk_assemblies.md) / torso assemblies.
5. Animate via [Rig UI](rig_ui.md).

## Generate ORG Bones

**Where:** Rig Tools n-panel → **Generate ORG Bones**

Creates or updates ORG bones to match DEF bones:

- Safe to re-run: missing ORGs are created; relationships are reapplied for pairs that already exist.
- New ORGs copy hierarchy / `use_connect` from DEF where possible.
- DEF is linked to ORG with **Copy Transforms** (default) or by parenting DEF under ORG.
- ORG deform is disabled by default so only DEF deforms the mesh.
- Collection structure can be mirrored (`DEF…` → `ORG…`) or flattened into a single ORG collection.

Name templates default from addon preferences (`DEF-{name}`, `ORG-{name}`) and preserve `.L` / `.R`.

Selection modes: Selected / Visible / All matching DEF bones (Selected needs Edit or Pose mode).

### What carries over from DEF

| Data | Behavior |
| --- | --- |
| Twist parent map | Remapped onto new ORGs so [twist](twist_bones.md) chains survive |
| Heel pivot | Copied onto the corresponding ORG foot bone |

## Heel pivots

Foot roll on [leg IK](ik_assemblies.md) needs a heel pivot bone associated with the foot.

- Assign under **Bone Properties → Rig Tools → Heel Pivot** (assign to the **foot**, not the toe).
- Set on DEF before Generate ORG, or on ORG before/with a leg assembly that enables foot roll.

## Armature settings

Per-armature settings live on the armature (`Rig Tools → Armature Settings`) and are
initialized from addon preferences.

| Setting | Why it matters |
| --- | --- |
| **Root** | Parent for many IK / isolation / torso setups |
| **Properties** | Bone that holds assembly custom properties; required for generation and Rig Properties |
| **Torso / Hips / Chest / Head** | IK parent-switch targets; torso assembly also writes these when it creates controls |
| Widgets | Whether to create widgets and where to put them |

!!! warning
    If the properties bone is missing, assembly generation fails.
    Initialize armature settings (or create the bone) before building limbs.

### Preferences that matter here

Under addon preferences (trimmed naming surface):

- **DEF / ORG / FK** name templates — boundaries for Generate ORG and FK controls
- Strip tags / separators — how base names are derived
- MCH collection + MCH parent — where non-limb / nested MCH collections go
- Default armature structure names (root, properties, …)

## Tips

- Keep DEF and ORG naming consistent so Generate ORG and later tools stay predictable.
- Author custom [twist](twist_bones.md) chains on DEF, generate ORG, then run assemblies with a matching twist count to reuse them.
- After assemblies exist, don’t rename the properties bone casually — Rig UI and drivers depend on it.

## Related

- [Assemblies](assemblies.md)
- [Twist Bones](twist_bones.md)
- [IK Assemblies](ik_assemblies.md)
- [FK Assemblies](fk_assemblies.md)
- [Rig UI](rig_ui.md)
