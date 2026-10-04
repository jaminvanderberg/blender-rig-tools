# Inverse Kinematics Assemblies

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

IK assemblies build a full limb (or similar chain) with FK controls, IK controls,
optional tweaks and twist bones, FK/IK switching, and usually IK parent switching.
They are the densest assembly type in Rig Tools.

!!! tip "Requires"
    Read [Assemblies](assemblies.md) first for selection, templates, and delete/reconfigure rules.
    For twist details, see [Twist Bones](twist_bones.md).

!!! info "Requires"
    Armature selected · Edit or Pose mode · linear ORG chain(s)

## How to run

1. Select one or more linear chains (typically **ORG** bones — see [ORG & DEF](org_def.md)).
2. Open the **Inverse Kinematics** section of the Rig Tools n-panel.
3. Click a template (recommended) or **Generate IK Assembly** for the full dialog.

Templates apply sensible defaults immediately and expose a focused redo panel.
The advanced generator shows almost every option — useful once you know what you need.

## Templates

| Template | Best for | Notes |
| --- | --- | --- |
| **Arm** | Humanoid arms (~3 bones) | FK/IK, tweaks, twist (arm + forearm), rotation isolation, IK parents (root/torso/hips/chest/head), snapping |
| **Leg** | Humanoid legs (~3 bones) | Same core as arm; thigh/shin twists; **foot roll** when a heel pivot is set; IK parents include “Foot” (self) |
| **Skirt - Spline** | Long chains (skirts, etc.) | Spline IK instead of pole IK; spline twist controllers (not limb twist bones); no FK↔IK snap |

Exact redo fields differ per template. Settings are always subject to change as templates evolve.

## What gets built (standard IK)

For Arm / Leg style assemblies, generation roughly does:

1. Optional intermediate chain (for tweaks / switch targets)
2. **FK / IK switch** — FK control chain + IK mechanism chain driven by a custom property
3. Optional **rotation isolation** on the limb root FK
4. Optional **twist bones** + tweaks on configured segments
5. **IK control** + **pole** (and snap helpers if snapping is on)
6. Optional **foot roll** (legs)
7. Optional **IK parent** switching for the IK control (and pole)

Bones land in collections such as `{Name}.FK`, `{Name}.IK`, `{Name}.Tweak`, and `MCH-{Name}`
(under your MCH parent collection when collections are overridden).

Custom properties (switch, parent, isolation, etc.) live on the armature’s **properties** bone
(see [Armature settings](org_def.md#armature-settings) and [Rig UI](rig_ui.md)).

## Important options

### Limb name

Used for collection names, property names, and assembly naming heuristics
(e.g. `arm` → `Arm.FK.L`, `arm.FK.IK.L`). Templates usually fill this in; skirt/spline may ask you.

### IK bone count

How many bones from the start of the chain participate in the pole IK.
Arms/legs default to **3**. Extra bones after that (e.g. hand/foot ORG, toes) stay available
for tips / foot roll / parenting.

### Tweaks

When enabled, creates tweak controls along the limb (and on twist subdivisions when twists are on).
Relationship is typically **Stretch To** or **Damped Track** toward the next tweak.

### FK / IK switch

Enum or float property on the properties bone. Drives blending between FK and IK mechanism chains.
With **snapping** enabled, Rig Properties also gets IK↔FK snap buttons for that limb
(see [Rig UI](rig_ui.md#snapping)).

### Rotation isolation

Lets the limb root FK follow (or not follow) the torso/root orientation via a property —
useful so arms don’t inherit unwanted chest rotation.

### IK parent

Adds a parent-switch property so the IK control can sit under root, torso, hips, etc.
(or “Foot” / self on legs). Targets come from [armature settings](org_def.md#armature-settings)
bone names (`root`, `torso`, …).

### Foot roll

Leg template option. Needs a **heel pivot** assigned on the foot ORG (or carried over from DEF
via Generate ORG Bones). See [ORG & DEF](org_def.md#heel-pivots).

### Twist bones

See [Twist Bones](twist_bones.md). Arm/Leg templates enable them by default with segment lists
(source + falloff per segment).

### Spline IK

Skirt-style assemblies use spline controls along the chain instead of a pole vector.
**Spline twist** here means controllers on the spline — not the limb twist-bone system.

## Workflow tips

- Build **ORG** chains first ([ORG & DEF](org_def.md)), then run Arm/Leg on matching L/R selections.
- Set heel pivot on the foot before (or with) a leg that uses foot roll.
- After generation, select any bone in the limb and use **Item → Rig Properties** for switch / parent / snap.
- Organize FK/IK/Tweak visibility under **Item → Rig UI**.

## Related

- [Assemblies](assemblies.md)
- [Twist Bones](twist_bones.md)
- [ORG & DEF](org_def.md)
- [Rig UI](rig_ui.md)
- [FK Assemblies](fk_assemblies.md)
