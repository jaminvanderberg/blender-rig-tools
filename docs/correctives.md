# Corrective Bones

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

Corrective bones fix the shape of the mesh when a joint bends a long way, such as the shoulder when the arm is raised, or the elbow when it's fully bent.  You set one up from a pose: bend the joint, move the corrective bone to where it should be, and RigTools makes it move there by itself whenever the joint bends that way.

**Where:** n-Panel > RigTools > Corrective Bones > Create Corrective Bone (Pose mode)
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

**Moving instead of bending:** the driving bone can also be moved rather than rotated, such as a jaw control that slides down.  The corrective then follows how far it moved.  If the driving bone was both rotated and moved, the rotation is used.

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

Select the corrective bone.  Its settings show in the *Corrective Bones* panel, under the Create button, one box per corrective on that bone.

- **Begin**: how far the joint bends (or the driving bone moves) before the correction starts.  0 by default; raise it for a dead zone, such as teeth that stay shut while the mouth starts to open.
- **Full**: how far the joint bends before the correction is at full strength.  Going further than this doesn't add any more.
- **Extrapolate**: keep correcting past Full instead of stopping there.  It works both ways: below Begin it corrects *backward*, so bending the joint the other way moves the corrective the wrong way, and a dead zone no longer holds still.  Best for joints that only bend one way.
- **Move** and **Rotate** X / Y / Z: the correction at full strength.  A corrective that both moves and rotates shows both rows in one box, sharing one Begin and Full.
- The **mirror** button copies this corrective to the other side, replacing the matching one that's already there.  Use it after adjusting one side.
- The **trash** button deletes the corrective.
- The **join** and **split** buttons are described under *Combining correctives*.

!!! tip
    Hold ++shift++ while dragging a value for finer adjustments.

!!! screenshot "Image placeholder"
    `image/corrective_panel.png` — The Corrective Bones panel with a corrective bone selected, showing the corrective box (Begin, Full, Move X/Y/Z) under the Create button.

## Combining correctives

- **Move and rotate:** if you both move and rotate the corrective bone before clicking Create, you get one box with both, sharing one Begin and Full.  To add a rotation to a corrective that only moves, pose the joint again, rotate the corrective bone, and click **Create Corrective Bone** again.  The two add together, as two boxes.
- **Join:** the link button pulls another corrective on the same bone into this one, so they share this one's Begin and Full.  Only correctives driven by the same bone in the same direction can be joined; the button is greyed out otherwise.  In the redo panel, pick which one to join, and how its amounts are handled:
    - **Keep** (default): its Move and Rotate amounts stay the same.  It now reaches them at this corrective's Full.
    - **Scale**: its amounts are scaled so that at this corrective's Full it's where it was before.
- **Split:** the unlink button on a joined box gives each part its own Begin and Full again, keeping their current values.
- **More than one joint:** one corrective bone can react to several joints.  For example, a shoulder blade corrective can react to both the shoulder and the arm.  Create one corrective for each driving bone; their effects add together.

## Good to know

- **Mirroring assumes the two sides are symmetrical.**  If the left and right bones weren't made with Symmetrize, the mirrored corrective may move the wrong way.
- **RigTools adds a hidden helper bone** in the MCH collection for each driving bone, named like `MCH-CORR-arm.L`.  All correctives driven by that bone share it, and it's removed when the last one is deleted.  Don't rename it.
- **Correctives aren't assemblies.**  Deleting or reconfiguring an assembly doesn't change them.
- **Joined correctives keep their Begin and Full as custom properties** on the corrective bone, named like `CORR MCH-CORR-arm.L +RX Begin`.  Edit them from the box rather than the Custom Properties panel.
- **Join or split both sides.**  Mirror replaces the matching box on the other side, but it can't undo a join or split made on one side only.  Do the same on both sides, or mirror each box.
- **The *[Data Viewer](data_viewer.md#correctives)*** lists every corrective on the rig.

## Related

- [ORG & DEF](org_def.md)
- [Generate ORG Bones](operators/generate_org_bones.md)
- [Assemblies](assemblies.md)
- [Data Viewer](data_viewer.md)
