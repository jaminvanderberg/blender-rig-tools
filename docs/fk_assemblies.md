# Forward Kinematics Assemblies

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

FK assemblies build control chains without a full IK stack: FK bones, optional tweaks,
optional rotation isolation / rotation follow, and a dedicated **Torso** template for
spine–neck–head.

!!! tip "Requires"
    Read [Assemblies](assemblies.md) first for selection, templates, and delete/reconfigure rules.

!!! info "Requires"
    Armature selected · Edit or Pose mode · linear ORG chain(s)

## How to run

1. Select one or more linear chains (typically **ORG** bones — see [ORG & DEF](org_def.md)).
2. Open the **Forward Kinematics** section of the Rig Tools n-panel.
3. Click a template, or use **Generate FK Assembly** / **Generate Torso Assembly** for full dialogs.

Prefer templates. The advanced generators expose more options than you usually need.

## FK templates

| Template | Best for | Notes |
| --- | --- | --- |
| **Simple FK** | Generic FK chains | Rotation follow along the chain; isolation off by default |
| **Skirt FK** | Skirt / cloth chains | Rectangle widgets; rotation isolation on |
| **Tail** | Tails | Named `tail`; isolation + rotation follow |
| **Finger** | Fingers | Skips the first tweak (metacarpal-friendly) |
| **Tweak Only** | Deform polish without FK | Tweaks only; collections not overridden by default |

### What a typical FK assembly builds

1. **FK chain** (unless Tweak Only) — control bones following the ORG chain
2. **Tweak bones** — usually Stretch To / Damped Track between joints (and a tip tweak)
3. Optional **rotation isolation** on the first FK
4. Optional **rotation follow** — later FKs copy rotation from an earlier “master” in the chain
   (skip count controls how many root FKs are excluded)

ORG bones parent under the tweaks so deformation follows the control stack.

Limb/base name still matters for collections and isolation property names when those features are on.

### Useful options

| Option | Meaning |
| --- | --- |
| FK widget | Shape used for FK controls (circle, rectangle, FK shape, none, …) |
| Skip first tweak | No tweak at the chain root (common for fingers) |
| Tweak relationship | Stretch To vs Damped Track |
| Rotation follow | Secondary FKs follow a master; skip chooses where follow starts |
| Rotation isolation | Root FK can blend out of parent orientation |
| FK bone template | Naming pattern for FK bones (defaults from preferences, e.g. `FK-{name}`) |
| Override collections | Put FK/tweak bones into generated collections vs leave them where they are |

## Torso

Torso is its own assembly type (still under the FK panel), not a simple FK chain template.

!!! info "Requires"
    A single spine-style chain that includes lower torso, chest/upper torso, neck, and head ORGs
    in one linear selection (exact counts are options).

### What it builds

- Master controls: **torso**, **hips**, **chest**, plus FK along the spine/neck and a **head** control
  (names from [armature settings](org_def.md#armature-settings))
- Optional **tweaks** along the chain (including over [twist](twist_bones.md) subdivisions)
- Optional **neck** and **chest** twist bones
- Optional **neck / head rotation isolation** (separate properties)
- Neck falloff so neck twists / FKs can ease toward the head

### Template defaults (humanoid-oriented)

| Option | Typical default |
| --- | --- |
| Lower torso bone count | 2 |
| Neck bone count | 1 |
| Use twist bones | On (neck/chest twist counts on redo) |
| Neck falloff | Root |
| Neck / head isolation | On |

Redo commonly exposes lower-torso count, neck count, twist toggles/counts, and neck falloff.

!!! note
    Torso writes the hips/chest/torso/head control names into armature settings so later
    **IK parent** targets on arms/legs can find them.

## When to use FK vs IK

| Use FK assemblies | Use IK assemblies |
| --- | --- |
| Fingers, tails, simple cloth, hair strands | Arms, legs, anything that needs poles / IK goals |
| You only want FK + tweaks | You need FK/IK switching and snapping |
| Torso / spine–neck–head | — |

You can stack assemblies (e.g. torso first, then arms that parent-switch to chest/head).
Dependencies block deleting an assembly that another still references.

## Related

- [Assemblies](assemblies.md)
- [Twist Bones](twist_bones.md)
- [ORG & DEF](org_def.md)
- [Rig UI](rig_ui.md)
- [IK Assemblies](ik_assemblies.md)
