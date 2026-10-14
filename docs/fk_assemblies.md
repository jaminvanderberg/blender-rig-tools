# Forward Kinematics Assemblies

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

FK assemblies build control chains without a full IK stack: FK bones, optional tweaks,
optional rotation isolation / master controllers (rotation follow), and a dedicated
**Torso** template for spine–neck–head.
There are also options for skirt collision and ride on the Skirt FK template.

!!! tip "Requires"
    Read [Assemblies](assemblies.md) first for selection, templates, and delete/reconfigure rules.
    For twist details on Torso, see [Twist Bones](twist_bones.md).

!!! info "Requires"
    Armature selected · Edit or Pose mode · linear ORG chain(s)

## How to run

1. Select one or more linear chains (typically **ORG** bones — see [ORG & DEF](org_def.md)).
2. Open the **Forward Kinematics** section of the Rig Tools n-panel.
3. Click an FK template button (or **Torso** for the spine–neck–head assembly).

Prefer templates. The advanced generators expose more options than you usually need.

## Templates

| Template | Best for | Notes |
| --- | --- | --- |
| **Simple FK** | Generic FK chains | Tweaks + FK follow from the second bone; isolation off by default |
| **FK Only** | FK without tweaks | No tweak bones; FK follow from the second bone |
| **Skirt FK** | Skirts / cloth chains | Rectangle widgets; isolation on; skirt collision on; ride off |
| **Tail** | Tails | Named `tail`; isolation on; master controllers every 3 bones |
| **Finger** | Fingers | Skips the first tweak (metacarpal-friendly); FK follow |
| **Tweak Only** | Deform polish without FK | Tweaks only |
| **Torso** | Spine–neck–head | Master torso/hips/chest/head; optional neck/chest twists |

## Tools and Settings

- [FK/Tweak controls](tools/fk_chain.md)
- [FK Tweak Chain](tools/fk_tweak_chain.md)
- [Rotation Isolation](tools/rotation_isolation.md)
- [Rotation Follow](tools/rotation_follow.md)
- [FK Master Controls](tools/master_controllers.md)
- [Torso FK](tools/torso_fk.md)
- [Twist Bones](tools/twist_bones.md)
- [Skirt Collision](tools/skirt_collision.md)
- [Skirt Ride](tools/skirt_ride.md)

## Template details

### Simple FK

The Simple FK assembly is a general-purpose FK chain with tweaks. Use it for hair strands, cloth strips, or any chain that does not need a specialized template.

- Creates an [FK/Tweak chain](tools/fk_chain.md) with circle widgets by default.
- [Master Controllers](tools/master_controllers.md) are enabled as FK follow from the second bone (skip first).
- [Rotation Isolation](tools/rotation_isolation.md) is available but off by default.

### FK Only

Same idea as Simple FK, but without tweak bones — useful when you want animator FK controls without the deform polish layer.

- Creates FK controls only (no tweaks).
- [Master Controllers](tools/master_controllers.md) are enabled as FK follow from the second bone (skip first).
- [Rotation Isolation](tools/rotation_isolation.md) is available but off by default.

### Skirt FK

!!! tip "Requires"
    Skirt collision / ride options may reference leg and torso bones. Prefer having a [torso](#torso) (and legs, if using ride) set up first when enabling those features.

The Skirt FK assembly is intended for skirts and dresses. There is also a [Skirt - Spline](ik_assemblies.md#skirt-spline) IK template when you specifically want spline IK; Skirt FK is usually preferable.

- Creates an [FK/Tweak chain](tools/fk_chain.md) with rectangle widgets.
- [Rotation Isolation](tools/rotation_isolation.md) is enabled by default.
- [Skirt Collision](tools/skirt_collision.md) is enabled by default.
- [Skirt Ride](tools/skirt_ride.md) is intended for short skirts (the tendency for short skirts to ride up when the leg is lifted). It is disabled by default.
- [Master Controllers](tools/master_controllers.md) are enabled as master controllers from the second bone (skip first).

### Tail

The Tail assembly is an FK setup for tails. There is also a [Tail - Spline](ik_assemblies.md#tail-spline) IK template; choice is largely preference and may depend on tail length.

- Creates an [FK/Tweak chain](tools/fk_chain.md) with circle widgets; limb base name defaults to `tail`.
- [Rotation Isolation](tools/rotation_isolation.md) is enabled by default.
- [Master Controllers](tools/master_controllers.md) are enabled every 3 bones (skipping the first), as master controllers.

### Finger

The Finger assembly is a compact FK chain for fingers. It skips the first tweak so a metacarpal (or similar root) can sit without an extra tweak at the base.

- Creates an [FK/Tweak chain](tools/fk_chain.md) with circle widgets; skips the first tweak by default.
- [Master Controllers](tools/master_controllers.md) are enabled as FK follow from the second bone (skip first).
- [Rotation Isolation](tools/rotation_isolation.md) is available but off by default.

Apply fingers separately after an [Arm](ik_assemblies.md#arm) assembly; the arm template does not build palms or fingers.

### Tweak Only

Tweak Only builds the tweak layer without FK controls — useful for deform polish on a chain that is already driven elsewhere, or when you only want mid-chain adjustments.

- Creates tweak bones only (Stretch To by default).
- No FK controls, master controllers, or rotation isolation.

### Torso

Torso is its own assembly type (still under the FK panel), not a simple FK chain template.

!!! tip "Requires"
    A single spine-style chain that includes lower torso, chest/upper torso, neck, and head ORGs
    in one linear selection (exact counts are options).

The Torso assembly builds the core body controls that later IK assemblies parent to.

- Builds master controls: **torso**, **hips**, **chest**, plus FK along the spine/neck and a **head** control (names from [armature settings](org_def.md#armature-settings)).
- Optional [tweaks](tools/fk_tweak_chain.md) along the chain (including over [twist](tools/twist_bones.md) subdivisions).
- Optional **neck** and **chest** [twist bones](tools/twist_bones.md).
- Optional [neck / head rotation isolation](tools/rotation_isolation.md) (separate properties; on by default).
- Neck falloff so neck twists / FKs can ease toward the head (default: root).

Typical humanoid defaults: 2 lower-torso bones, 1 neck bone, twist bones on, neck/head isolation on.

!!! note
    Torso writes the hips/chest/torso/head control names into armature settings so later
    [IK parent](tools/ik_parent.md) targets on arms/legs can find them. Set up torso before arm/leg IK assemblies.

## When to use FK vs IK

| Use FK assemblies | Use IK assemblies |
| --- | --- |
| Fingers, tails, simple cloth, hair strands | Arms, legs, anything that needs poles / IK goals |
| You only want FK + tweaks | You need FK/IK switching and snapping |
| Torso / spine–neck–head | Spline IK skirts/hair/tails when you specifically want splines |

You can stack assemblies (e.g. torso first, then arms that parent-switch to chest/head).
Dependencies block deleting an assembly that another still references.

## Related

- [Assemblies](assemblies.md)
- [Twist Bones](twist_bones.md)
- [ORG & DEF](org_def.md)
- [Rig UI](rig_ui.md)
- [IK Assemblies](ik_assemblies.md)
