# Inverse Kinematics Assemblies

IK assemblies build a limb with FK/IK switching and additional options.
Additional options include tweak controls (on by default), FK rotation isolation,
FK master controllers, IK parent switching, FK<>IK snapping,
and additional mechanisms for skirt collision and ride.
There are also options for spline IK, on top of the standard arm/leg IK setups.
Spline IK setups do not include FK<>IK snapping, as it is often impossible for the
spline IK to match an FK chain.

!!! tip "Requires"
    Read [Assemblies](assemblies.md) first for selection, templates, and delete/reconfigure rules.
    For twist details, see [Twist Bones](twist_bones.md).

!!! info "Requires"
    Armature selected · Edit or Pose mode · linear ORG chain(s)

## How to run

1. Select one or more linear chains (typically **ORG** bones — see [ORG & DEF](org_def.md)).
2. Open the **Inverse Kinematics** section of the Rig Tools n-panel.
3. Click an IK template button.

## Templates

| Template | Best for | Notes |
| --- | --- | --- |
| **Arm** | Humanoid arms (3 bones) | FK/IK, tweaks, twist (arm + forearm), rotation isolation, IK parents (root/torso/hips/chest/head), snapping |
| **Leg** | Humanoid legs (4 bones) | Same core as arm; thigh/shin twists; toe included; **foot roll** on by default (needs heel pivot) |
| **Skirt - Spline** | Skirts/Dresses | Spline IK with 3 controls by default; twist at start/end; skirt collision options |
| **Hair - Spline** | Long ponytails/pigtails | Spline IK with 3 controls by default; twist at every control |
| **Tail - Spline** | Tails | Spline IK with 4 controls by default; twist at start/end; master controllers every 3 bones |

## Tools and Settings

- [FK/IK Switching](tools/fk_ik_switch.md)
- [FK/Tweak controls](tools/fk_chain.md)
- [Standard IK](tools/standard_ik.md)
- [Spline IK](tools/spline_ik.md)
- [Twist Bones](tools/twist_bones.md)
- [Rotation Isolation](tools/rotation_isolation.md)
- [FK Master Controls](tools/master_controllers.md)
- [FK <> IK Snapping](rig_ui.md#snapping)
- [Foot Roll](tools/foot_roll.md)
- [IK Parent Switching](tools/ik_parent.md)
- [Skirt Collision](tools/skirt_collision.md)
- [Skirt Ride](tools/skirt_ride.md)

## Template details

### Arm

!!! tip "Requires"
    Requires a [torso](fk_assemblies.md#torso) to be set up first. It will reference torso bones for IK parenting.

The Arm assembly is a standard setup for a humanoid arm. In most cases, the chain should be exactly 3 bones (arm, forearm, hand). The arm assembly does not include additional mechanisms for the palms or fingers. Those should be applied separately (see [FK Assemblies](fk_assemblies.md)).

- Creates a [standard IK setup](tools/standard_ik.md) with 2 IK bones, a pole, and the hand as the control.
- Includes [FK/IK switching](tools/fk_ik_switch.md) and [FK/Tweak controls](tools/fk_chain.md).
- [FK <> IK Snapping](rig_ui.md#snapping) is set up automatically.
- [Rotation Isolation](tools/rotation_isolation.md) is available and enabled by default.

Arms can include [twist bones](tools/twist_bones.md), as is often desirable for a high-quality rig. Twist bones can be set up ahead of time, or the tool will add them automatically if the setting is enabled. It is recommended to set them up ahead of time so they can be weight painted with the rest of the rig. By default it uses 4 twist bones each for the arm and forearm, with "root" falloff on the upper arm (slightly softer than "sharp") and "linear" falloff on the forearm. These are decent defaults for most models and can be tweaked as needed.

The arm template automatically sets up [IK parent switching](tools/ik_parent.md) with root, torso, hips, chest, and head as parent targets. The [torso](fk_assemblies.md#torso) must be set up first so those bones exist. IK parents can be adjusted without reconfiguring the assembly.

### Leg

!!! tip "Requires"
    Requires a [torso](fk_assemblies.md#torso) to be set up first. It will be referenced for IK parenting.

The Leg assembly is a standard setup for a humanoid leg. The chain should be exactly 4 bones long (thigh, shin, foot, toe). Include the toe even when you are not using foot roll.

- Creates a [standard IK setup](tools/standard_ik.md) with 2 IK bones, a pole, and the foot as the control.
- Includes [FK/IK switching](tools/fk_ik_switch.md) and [FK/Tweak controls](tools/fk_chain.md), plus an additional FK control for the toe.
- [Foot roll](tools/foot_roll.md) is enabled by default (requires a heel pivot).
- [FK <> IK Snapping](rig_ui.md#snapping) is set up automatically.
- [Rotation Isolation](tools/rotation_isolation.md) is available and enabled by default.

Legs can include [twist bones](tools/twist_bones.md), as is often desirable for a high-quality rig. Twist bones can be set up ahead of time, or the tool will add them automatically if the setting is enabled. It is recommended to set them up ahead of time so they can be weight painted with the rest of the rig. By default it uses 4 twist bones each for the thigh and shin, with "sharp" falloff on the thigh and no falloff on the shin. The shin does not typically twist on most rigs, but the twist bones are included by default for consistency and for the additional tweak bones. These are decent defaults for most models and can be tweaked as needed.

The leg template automatically sets up [IK parent switching](tools/ik_parent.md) with root, torso, and foot as parent targets for the legs. A [torso](fk_assemblies.md#torso) must be set up first. The "foot" option parents the pole to the foot, and the foot is parented to the root. IK parents can be adjusted without reconfiguring the assembly.

### Skirt - Spline

!!! tip "Requires"
    Requires a [torso](fk_assemblies.md#torso) and hips bones to be set up first. These bones will be referenced for IK parenting.

The skirt assembly is a spline IK setup intended for skirts and dresses. There is also a [Skirt FK](fk_assemblies.md#skirt-fk) setup that may be more desirable in most cases. Skirt - Spline adds extra complexity and should only be used when spline IK is desirable.

- Creates a [spline IK setup](tools/spline_ik.md) with 3 controllers and twist controls at the start and end.
- Includes [FK/IK switching](tools/fk_ik_switch.md) and [FK/Tweak controls](tools/fk_chain.md).
- [Rotation Isolation](tools/rotation_isolation.md) is available and enabled by default.
- [Skirt Collision](tools/skirt_collision.md) is enabled by default.
- [Skirt Ride](tools/skirt_ride.md) is intended for short skirts (the tendency for short skirts to ride up when the leg is lifted). It is disabled by default.
- [Master Controllers](tools/master_controllers.md) can be set up. The default configuration is FK follow from the second bone in the chain (skip first).

!!! note "Spline IK limitations"
    Spline IK assemblies do not support limb [twist bones](tools/twist_bones.md) (they use spline twist controllers instead) or [FK <> IK snapping](rig_ui.md#snapping) (a spline IK pose often cannot match an FK chain).

The skirt template automatically sets up [IK parent switching](tools/ik_parent.md) with root, torso, and hips as parent targets. The [torso](fk_assemblies.md#torso) and hips bones must be set up first. IK parents can be adjusted without reconfiguring the assembly.

### Hair - Spline

!!! tip "Requires"
    Requires a [torso](fk_assemblies.md#torso) and head bones to be set up first. These bones will be referenced for IK parenting.

The hair assembly is a spline IK setup intended for long hair, especially ponytails and pigtails. A [Simple FK](fk_assemblies.md#simple-fk) setup is usually more desirable for most hair. Hair - Spline adds extra complexity and should only be used when spline IK is desirable.

- Creates a [spline IK setup](tools/spline_ik.md) with 3 controllers and twist controls at every control point.
- Includes [FK/IK switching](tools/fk_ik_switch.md) and [FK/Tweak controls](tools/fk_chain.md).
- [Rotation Isolation](tools/rotation_isolation.md) is available and enabled by default.
- [Master Controllers](tools/master_controllers.md) can be set up. The default configuration is FK follow from the second bone in the chain (skip first).

!!! note "Spline IK limitations"
    Spline IK assemblies do not support limb [twist bones](tools/twist_bones.md) (they use spline twist controllers instead) or [FK <> IK snapping](rig_ui.md#snapping) (a spline IK pose often cannot match an FK chain).

The hair template automatically sets up [IK parent switching](tools/ik_parent.md) with root, torso, and head as parent targets. The [torso](fk_assemblies.md#torso) and head bones must be set up first. IK parents can be adjusted without reconfiguring the assembly.

### Tail - Spline

!!! tip "Requires"
    Requires a [torso](fk_assemblies.md#torso) and hips bones to be set up first. These bones will be referenced for IK parenting.

The tail assembly is a spline IK setup intended for long tails. There is also a [Tail FK](fk_assemblies.md#tail) that may be more desirable for some tails. This is largely preference and may depend on tail length.

- Creates a [spline IK setup](tools/spline_ik.md) with 4 controllers and twist controls at the beginning and end.
- Includes [FK/IK switching](tools/fk_ik_switch.md) and [FK/Tweak controls](tools/fk_chain.md).
- [Rotation Isolation](tools/rotation_isolation.md) is available and enabled by default.
- [Master Controllers](tools/master_controllers.md) can be set up. The default configuration is master controllers every 3 bones (skipping the first).

!!! note "Spline IK limitations"
    Spline IK assemblies do not support limb [twist bones](tools/twist_bones.md) (they use spline twist controllers instead) or [FK <> IK snapping](rig_ui.md#snapping) (a spline IK pose often cannot match an FK chain).

The tail template automatically sets up [IK parent switching](tools/ik_parent.md) with root, torso, and hips as parent targets. The [torso](fk_assemblies.md#torso) and hips bones must be set up first. IK parents can be adjusted without reconfiguring the assembly.

## Related

- [Assemblies](assemblies.md)
- [Twist Bones](twist_bones.md)
- [ORG & DEF](org_def.md)
- [Rig UI](rig_ui.md)
- [FK Assemblies](fk_assemblies.md)
