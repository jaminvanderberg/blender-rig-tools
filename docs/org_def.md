# ORG & DEF

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

RigTools splits the skeleton into two layers: **DEF** bones that deform the mesh, and **ORG** bones that the assemblies are built on.  The DEF bones follow the ORG bones.

!!! tip
    Assemblies are created on ORG chains.  When selecting a chain for an assembly, select the ORG bones.

## Why two layers?

The DEF bones are the ones that are weight painted.  Keeping them separate from the rig mechanics means:

- Assemblies can be created, deleted, and reconfigured without touching the weight painting.
- The DEF bones stay in a simple hierarchy that's easy to export to game engines and other tools.
- New DEF bones (an accessory, a skirt, a ponytail) can be added later, and ORG bones generated for just those.

| Layer | Role |
| --- | --- |
| **DEF** | Deform bones.  The mesh is weight painted to these. |
| **ORG** | The bones assemblies are built on.  Don't deform.  The DEF bones follow these. |
| **Controls / MCH** | Created by the assemblies: FK, IK, tweaks, and the mechanism (MCH) bones that make them work. |

!!! screenshot "Image placeholder"
    `image/org_def_layers.png` — An arm shown three ways: the DEF bones only, the ORG bones only, and the finished arm with FK/IK controls and tweaks visible.

## Typical order

1. Build the **DEF** skeleton, or start from the *[RigTools Human Skeleton](operators/human_skeleton.md)*.
2. Optionally, add *[twist bones](twist_bones.md)* and assign *[heel pivots](#heel-pivots)*.
3. Weight paint the DEF bones.
4. Run *[Generate ORG Bones](operators/generate_org_bones.md)*.
5. Select ORG chains and create the *[torso](fk_assemblies.md#torso)*, then the *[IK](ik_assemblies.md)* and *[FK](fk_assemblies.md)* assemblies.
6. Animate with the *[Rig UI](rig_ui.md)*.

See *[Workflow](workflow.md)* for the full process.

## Generate ORG Bones

*[Generate ORG Bones](operators/generate_org_bones.md)* creates an ORG bone for each DEF bone, with the same hierarchy, and makes the DEF bone follow it with a Copy Transforms constraint.  It's safe to run more than once; only the missing ORG bones are created.

Twist bone and heel pivot assignments made on the DEF bones are copied to the ORG bones.

## Heel pivots

*[Foot roll](tools/foot_roll.md)* on the *[Leg](ik_assemblies.md#leg)* assembly needs a heel pivot bone assigned to the foot.

- Assign it in **Bone Properties > Rig Tools > Heel Pivot**, with the **foot** bone active (not the toe).
- Assign it on the DEF foot before running Generate ORG Bones, or on the ORG foot before creating the leg.

See *[Foot Roll](tools/foot_roll.md#heel-pivot)* for where to place the heel pivot.

!!! screenshot "Image placeholder"
    `image/bone_properties_rigtools.png` — The Rig Tools section of Bone Properties with a foot bone active, showing the Twist Parent field and the Heel Pivot field.

## Naming

RigTools uses the bone names to tell DEF and ORG bones apart, and to name the bones it creates.  The defaults are `DEF-{name}` and `ORG-{name}`, with `.L` / `.R` suffixes kept at the end.  For example, `DEF-forearm.L` and `ORG-forearm.L`.  The naming templates can be changed in the *[addon preferences](armature_settings.md#naming)*.

## Tips

- Keep DEF and ORG naming consistent so Generate ORG Bones and the assemblies can find the right bones.
- Create twist bones on the DEF bones and weight paint them before generating ORG bones.  The assemblies will use the existing twist bones, as long as the twist bone count matches.
- Bone parenting is what makes a chain.  If your DEF chain isn't parented correctly, the ORG chain won't be either.  See *[Parent Along Chain](operators/parent_along_chain.md)*.

## Related

- [Assemblies](assemblies.md)
- [Generate ORG Bones](operators/generate_org_bones.md)
- [Twist Bones](twist_bones.md)
- [Armature Settings](armature_settings.md)
- [Workflow](workflow.md)
