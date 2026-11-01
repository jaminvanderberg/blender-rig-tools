# Corrective Bones

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

Corrective bones fix the shape of the mesh when a joint bends a long way, such as the shoulder when the arm is raised, or the elbow when it's fully bent.  You set one up from a pose: bend the joint, move the corrective bone to where it should be, and RigTools makes it move there by itself whenever the joint bends that way.

**Where:** n-Panel > RigTools > Tools > Create Corrective Bone (Pose mode)
{ .where }

Also in **Pose > Constraints**, or press ++shift+alt+c++.

!!! screenshot "Image placeholder"
    `image/correctives.png` — A raised arm with and without a shoulder corrective, showing the shoulder collapsing without it and holding its shape with it.

## Before you start

- **The corrective bone needs to be an ORG bone**, like the rest of the rig.  Add the corrective as a DEF bone, weight paint it, then run *[Generate ORG Bones](operators/generate_org_bones.md)*.  Use the ORG bone; its DEF bone follows it as usual.  See *[ORG & DEF](org_def.md)*.
- **The bone that drives it is also an ORG bone**, such as `ORG-arm.L` for a shoulder corrective.  Not the FK or IK control, and not the DEF bone.
- **For mirroring**, the left and right bones need matching names (`.L` / `.R`) and need to be symmetrical, for example made with Symmetrize.

## Creating a corrective

1. Pose the rig so the joint is at the extreme you want to fix, for example with the arm raised.  It works best when the joint mostly bends one way; the corrective follows whichever direction moved the most.
2. Move or rotate the corrective bone to where it should be in that pose.
3. Select the bone that drives it, then Shift-select the corrective bone so it's the active bone.
4. Click **Create Corrective Bone**.

The corrective bone snaps back to its rest position, then moves to your corrected position on its own.  As the joint bends toward that pose, the corrective bone eases into place.  When the joint is back at rest, so is the corrective bone.

### Mirror

**Mirror** is on by default, in the redo panel.  It creates the same corrective on the other side of the rig.  If there's no matching bone on the other side, only one side is created, and you get a note saying so.

### If it doesn't work

| Message | What to do |
| --- | --- |
| *... is a DEF bone. Use the ORG bone.* | Select the ORG bone instead. |
| *... belongs to assembly .... Use the ORG bone.* | A control or mechanism bone was selected as the driving bone.  Select the ORG bone instead. |
| *... has a ... constraint.* | The corrective bone is already following something else, so a corrective would fight with it.  Use a bone with no constraints. |
| *... isn't posed. Move or rotate it first.* | Move the corrective bone to its corrected position before clicking. |
| *... is at rest. Pose it first.* | Bend the joint before clicking. |

## Adjusting a corrective

Select the corrective bone.  Its settings show at the top of the *[Assembly panel](assemblies.md#assembly-panel)*, one box per corrective on that bone.

- **From**: how far the joint bends before the correction is at full strength.  Bending further than this doesn't add any more.
- **Move** or **Rotate** X / Y / Z: the correction at full strength.
- The **mirror** button copies this corrective to the other side, replacing the one that's already there.  Use it after adjusting one side.
- The **trash** button deletes the corrective.

!!! tip
    Hold ++shift++ while dragging a value for finer adjustments.

!!! screenshot "Image placeholder"
    `image/corrective_panel.png` — The Assembly panel with a corrective bone selected, showing the corrective box (From, Move X/Y/Z) above the assembly list.

## Combining correctives

- **Move and rotate:** to add a rotation to a corrective that only moves, pose the joint the same way again, rotate the corrective bone, and click **Create Corrective Bone** again.  The two add together.
- **More than one joint:** one corrective bone can react to several joints.  For example, a shoulder blade corrective can react to both the shoulder and the arm.  Create one corrective for each driving bone; their effects add together.

## Good to know

- **Mirroring assumes the two sides are symmetrical.**  If the left and right bones weren't made with Symmetrize, the mirrored corrective may move the wrong way.
- **RigTools adds a hidden helper bone** in the MCH collection for each driving bone, named like `MCH-CORR-arm.L`.  All correctives driven by that bone share it, and it's removed when the last one is deleted.  Don't rename it.
- **Correctives aren't assemblies.**  Deleting or reconfiguring an assembly doesn't change them.
- **The *[Data Viewer](data_viewer.md#correctives)*** lists every corrective on the rig.

## Related

- [ORG & DEF](org_def.md)
- [Generate ORG Bones](operators/generate_org_bones.md)
- [Assemblies](assemblies.md)
- [Data Viewer](data_viewer.md)
