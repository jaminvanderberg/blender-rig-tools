# Forward Kinematics Assemblies

FK assemblies build control chains without a full IK stack: FK bones, optional tweaks,
optional rotation isolation / master controllers (rotation follow), and a dedicated
**Torso** template for spine–neck–head.
There are also options for skirt collision and ride on the Skirt FK template.

!!! requires "Requires"
    Read [Assemblies](assemblies.md) first for selection, templates, and delete/reconfigure rules.
    For twist details on Torso, see [Twist Bones](twist_bones.md).

!!! requires "Requires"
    Armature selected · Edit or Pose mode · linear ORG chain(s)

## How to run

1. Select one or more linear chains (typically **ORG** bones — see [ORG & DEF](org_def.md)).
2. Open the **Forward Kinematics** section of the Rig Tools n-panel.
3. Click an FK template button.

## When to use FK vs IK

| Use FK assemblies | Use IK assemblies |
| --- | --- |
| Fingers, tails, simple cloth, hair strands | Arms, legs, anything that needs poles / IK goals |
| You only want FK + tweaks | You need FK/IK switching and snapping |
| Torso / spine–neck–head | Spline IK skirts/hair/tails when you specifically want splines |

Use FK assemblies when you have simple mechanisms that don't require IK.  Generally, arm and legs should use IK assemblies.
The spline IK assemblies are available, but are generally special-case uses.  Consider using FK first for hair, cloth, tails, etc., and switch to IK if you can't get the results you want.

## Templates

| Template | Best for | Notes |
| --- | --- | --- |
| **Torso** | Spine–neck–head | Master torso/hips/chest/head; optional neck/chest twists |
| **Simple FK** | Generic FK chains | Tweaks + FK follow from the second bone; isolation off by default |
| **FK Only** | FK without tweaks | No tweak bones; FK follow from the second bone |
| **Skirt FK** | Skirts / cloth chains | Rectangle widgets; isolation on; skirt collision on; ride off |
| **Tail** | Tails | Named `tail`; isolation on; master controllers every 3 bones |
| **Finger (FK)** | Fingers | Skips the first tweak (metacarpal-friendly); FK follow |
| **Finger (Curl)** | Fingers | Skips the first tweak; single curl control per finger (Rigify style) |
| **Shoulder** | Shoulders / clavicles | Single FK control with a shoulder widget; grouped with the arm |
| **Palm** | Palms / metacarpals | Index and pinky palms control the palms between them; opens a dialog to confirm bone order |

## Tools and Settings

- [FK/Tweak controls](tools/fk_chain.md)
- [FK Tweak Chain](tools/fk_tweak_chain.md)
- [Rotation Isolation](tools/rotation_isolation.md)
- [FK Master Controls](tools/master_controllers.md)
- [Torso FK](tools/torso_fk.md)
- [Twist Bones](tools/twist_bones.md)
- [Skirt Collision](tools/skirt_collision.md)
- [Skirt Ride](tools/skirt_ride.md)
- [Finger Curl](tools/finger_curl.md)
- [Shoulder](tools/shoulder.md)
- [Palm](tools/palm.md)

## Template details

### Torso

!!! note
    The torso assembly includes the head and neck, not just the spine. All head and neck bones should be included in the selection.

Torso is a special assembly type with a [torso FK](tools/torso_fk.md) tool that is specifically built for constructing a torso.

The default torso configuration includes 6 bones: ORG-hips, ORG-spine.01, ORG-spine.02, ORG-chest, ORG-neck, and ORG-head (or similar).  The hips and spine.01 are the lower torso bones, and will be controlled by a **hips** controller. The spine.02 and chest bones are the upper torso bones, and will be controlled by a **chest** controller.  These default settings are configurable.  For more information, see [torso FK](tools/torso_fk.md).

- Builds master controls: **torso**, **hips**, **chest**, plus FK along the spine/neck and a **head** control (names from [armature settings](armature_settings.md#settings)).
- Optional [tweaks](tools/fk_tweak_chain.md) along the chain (including over [twist](tools/twist_bones.md) subdivisions).
- Optional **neck** and **chest** [twist bones](tools/twist_bones.md).
- Optional [neck / head rotation isolation](tools/rotation_isolation.md) (separate properties; on by default).
- Neck falloff so neck twists / FKs can ease toward the head (default: root).

!!! note
    Torso creates the hips/chest/torso/head controls that [IK parent](tools/ik_parent.md) tools will reference later. Set up torso before other IK assemblies.

The torso includes the option for [twist bones](tools/twist_bones.md) on the chest and neck. The chest twist bones won't actually twist (see [torso FK](tools/torso_fk.md) for more information), they just provide an additional tweak controller on the chest.  The neck twist bones do twist, following the head.  The default fall-off setting is "root" (slightly softer than "sharp").  It is recommended to use the default setting of 1 neck bone with 2 twist bones for most humanoid characters.  For characters with longer necks, see [torso FK](tools/torso_fk.md).

!!! screenshot "Image placeholder"
    `image/fk_torso.png` — A finished Torso assembly in Pose mode, showing the torso, hips, chest, neck, and head controls.

### Simple FK

The Simple FK assembly is a general-purpose FK chain with tweaks. Use it for hair strands, cloth strips, or any chain that does not need a specialized template.

- Creates an [FK/Tweak chain](tools/fk_tweak_chain.md) with circle widgets by default.
- [Master Controllers](tools/master_controllers.md) are enabled as FK follow from the second bone (skip first).
- [Rotation Isolation](tools/rotation_isolation.md) is available but off by default.

### FK Only

Same idea as Simple FK, but without tweak bones — especially useful for short (1-2 bone) chains.

- Creates [FK controls](tools/fk_chain.md) only (no tweaks).
- [Master Controllers](tools/master_controllers.md) are enabled as FK follow from the second bone (skip first).
- [Rotation Isolation](tools/rotation_isolation.md) is available but off by default.

### Skirt FK

!!! requires "Requires"
    Skirt collision / ride reference leg bones.  Set up both leg assemblies first for easier setup.

The Skirt FK assembly is intended for skirts and dresses. There is also a [Skirt - Spline](ik_assemblies.md#skirt-spline) IK template when you specifically want spline IK; Skirt FK is usually preferable.

- Creates an [FK/Tweak chain](tools/fk_tweak_chain.md) with rectangle widgets.
- [Rotation Isolation](tools/rotation_isolation.md) is enabled by default.
- [Skirt Collision](tools/skirt_collision.md) is enabled by default.
- [Skirt Ride](tools/skirt_ride.md) is intended for short skirts (the tendency for short skirts to ride up when the leg is lifted). It is disabled by default.
- [Master Controllers](tools/master_controllers.md) are enabled as master controllers from the second bone (skip first).

!!! screenshot "Image placeholder"
    `image/fk_skirt.png` — A finished Skirt FK assembly in Pose mode, showing the rectangle FK widgets and the master controls, with one leg raised so the skirt collision is visible.

### Tail

The Tail assembly is an FK setup for tails. There is also a [Tail - Spline](ik_assemblies.md#tail-spline) IK template; choice is largely preference and may depend on tail length.

- Creates an [FK/Tweak chain](tools/fk_tweak_chain.md) with circle widgets; limb base name defaults to `tail`.
- [Rotation Isolation](tools/rotation_isolation.md) is enabled by default.
- [Master Controllers](tools/master_controllers.md) are enabled every 3 bones (skipping the first), as master controllers.

!!! screenshot "Image placeholder"
    `image/fk_tail.png` — A finished Tail assembly in Pose mode, showing the FK controls, tweaks, and a master control every 3 bones, with one master rotated so the tail curls.

### Finger (FK)

The Finger (FK) assembly is a compact FK chain for fingers. It skips the first tweak so a metacarpal (or similar root) can sit without an extra tweak at the base.

- Creates an [FK/Tweak chain](tools/fk_tweak_chain.md) with circle widgets; skips the first tweak by default.
- [Master Controllers](tools/master_controllers.md) are enabled as FK follow from the second bone (skip first).

Apply fingers separately after an [Arm](ik_assemblies.md#arm) assembly; the arm template does not build palms or fingers.

### Finger (Curl)

The Finger (Curl) assembly is an alternative to Finger (FK), similar to Rigify's finger controls.  Each finger gets a single, larger curl control: rotate it to rotate the whole finger, and scale it down to curl the finger.

- Creates an [FK/Tweak chain](tools/fk_tweak_chain.md) with circle widgets; skips the first tweak by default.
- Adds a [finger curl](tools/finger_curl.md) control.  The curl axis is detected automatically, and can be changed in the redo panel.
- [Master Controllers](tools/master_controllers.md) are not used.

!!! screenshot "Image placeholder"
    `image/fk_fingers_compare.png` — Side-by-side of one hand with Finger (FK) assemblies and one with Finger (Curl) assemblies, showing the difference in controls (FK circles vs. a single curl control per finger).

### Shoulder

!!! requires "Requires"
    Select only the shoulder bone.  The arm should be a separate [Arm](ik_assemblies.md#arm) assembly.

The Shoulder assembly creates a single FK control for a humanoid shoulder (clavicle).

- Creates a [shoulder](tools/shoulder.md) FK control with a shoulder widget, drawn above the shoulder so it's easy to grab.
- The shoulder is grouped with the arm on the same side, and its control is visible in both the arm's FK and IK bone collections.

### Palm

!!! requires "Requires"
    Select the palm bones (one per finger), not a chain.  Both hands can be selected at once.

The Palm assembly creates FK controls for the palm bones.  Unlike the other assemblies, the palm bones aren't a chain, so the Palm assembly opens a dialog to confirm the order of the bones, from index to pinky.

- Creates a [palm](tools/palm.md) FK control for each palm bone, with pill widgets.
- The first (index) and last (pinky) palms also control the palms between them, with a falloff.  This makes cupping and spreading the hand easy with only two controls.

## Related

- [Assemblies](assemblies.md)
- [Twist Bones](twist_bones.md)
- [ORG & DEF](org_def.md)
- [Rig UI](rig_ui.md)
- [IK Assemblies](ik_assemblies.md)
