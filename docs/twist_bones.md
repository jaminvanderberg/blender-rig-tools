# Twist Bones

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

Twist bones spread a twist along a limb, so the forearm twists smoothly from the wrist to the elbow instead of all at once at the wrist.  They're deform bones, not animator controls.

The Arm, Leg, and Torso assemblies use twist bones.  They can create the twist bones for you, or use twist bones you've already created.  Each twist bone also gets a tweak control, which gives the animator extra controls along the limb.

!!! tip "Start here"
    Twist bones are set up by the *[assemblies](assemblies.md)*.  Read Assemblies first if you haven't.

!!! note "Not spline twist"
    Spline IK has its own twist controllers on the spline.  That's a separate feature; see *[Spline IK](tools/spline_ik.md)*.

!!! screenshot "Image placeholder"
    `image/twist_bones.png` — A forearm with 4 twist bones, shown with the hand rotated 90 degrees so the twist is visibly spread along the forearm.  Ideally side-by-side with the same pose and no twist bones (candy-wrapper deformation at the wrist).

## Concepts

### Twist parent

RigTools doesn't rely on bone names to know which bones are twist bones.  Instead, each twist bone is assigned a **twist parent**: the bone it belongs to.  For example, the forearm twist bones have the forearm as their twist parent.

The twist bones for one bone must form a single chain, parented from the start of the bone to the end.

The twist parent of the active bone can be viewed and changed in **Bone Properties > Rig Tools > Twist Parent**.  The panel also lists the twist bones that belong to the active bone.

To assign many twist bones at once, select the twist bones, then select the twist parent last so it's the active bone, and use **Set Twist Parent** (++ctrl+shift+p++) from the Edit mode **Armature > Parent** menu.  **Clear Twist Parent** (++ctrl+alt+p++) removes the assignment.  Both work with X-Axis Mirror, so the other side is assigned at the same time.

!!! note
    *[Generate ORG Bones](operators/generate_org_bones.md)* copies twist parents from the DEF bones to the ORG bones.  Twist bones created on the DEF bones will carry over.

### Creating twist bones

Twist bones can be created three ways:

1. **Create Twist Bones**: the *[Create Twist Bones](operators/create_twist_bones.md)* tool splits each selected DEF bone into twist bones.  This is the recommended approach, since the twist bones can be weight painted along with the rest of the rig.
2. **By the assembly**: if an assembly needs twist bones and none exist, it creates them, both DEF and ORG.  The new DEF twist bones will need to be weight painted.
3. **Manually**: create the bones yourself, parent them into a chain, and assign their twist parent.  This is useful for custom layouts.

### Deleting assemblies

When an assembly is deleted or reconfigured, its twist bones are **kept**, so the weight painting isn't lost.  The next assembly will use the same twist bones.

!!! warning "Twist bone count"
    If twist bones already exist for a bone, the assembly's twist bone count must match.  Otherwise, the assembly fails with an error.  The redo panel shows the status of the twist bones before the assembly is created.

## In assemblies

### Arm and Leg

The Arm and Leg assemblies use twist bones by default, on the upper arm and forearm, or the thigh and shin.  The twist is picked up from the controls, and fades along each segment.

| Assembly | Segment | Twist from | Falloff | Twist bones |
| --- | --- | --- | --- | --- |
| Arm | Upper arm | Upper arm | Root | 4 |
| Arm | Forearm | Hand | Linear | 4 |
| Leg | Thigh | Thigh | Sharp | 4 |
| Leg | Shin | (none) | — | 4 |

The shin twist bones don't twist by default.  They're included for consistency, and for the additional tweak controls.

See *[Twist Bones (tool)](tools/twist_bones.md)* for the parameters, and what each falloff does.

### Torso

The *[torso](fk_assemblies.md#torso)* has optional twist bones on the chest and the neck (2 each by default).  The neck twist bones follow the head, with the falloff set by **Neck Falloff**.  The chest twist bones don't twist; they add an extra tweak control to the chest.  See *[Torso FK](tools/torso_fk.md)*.

## Related

- [Assemblies](assemblies.md)
- [Inverse Kinematics Assemblies](ik_assemblies.md) (Arm / Leg twist options)
- [Forward Kinematics Assemblies](fk_assemblies.md#torso) (Torso twist options)
- [Twist Bones (tool)](tools/twist_bones.md)
- [Create Twist Bones](operators/create_twist_bones.md)
