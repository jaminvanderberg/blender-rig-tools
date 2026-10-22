# IK Parent Switching

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

Lets the animator choose what the IK controls follow: the root, the torso, the hips, the chest, the head, and so on.

## Overview

Creates a custom property on the *[property bone](../armature_settings.md#property-bone)*.  The *[Rig Properties](../rigui/properties.md)* panel displays it as **IK Parent**, a dropdown with one entry per parent.  The IK control and the pole both follow the selected parent.  For spline IK, all of the spline controls follow the selected parent.

For example, with an arm set to **Chest**, the hand stays in place relative to the chest as the torso moves.  Set to **Root**, the hand stays planted in the world while the body moves around it.

!!! warning
    Changing the IK parent does not compensate for the change.  The IK controls will jump to their new position relative to the new parent.

The default parents for each template come from the bone names in the *[Armature Settings](../armature_settings.md)*.  The *[torso](../fk_assemblies.md#torso)* creates the torso, hips, chest, and head bones, so it needs to be set up before the IK assemblies.

| Assembly | Default parents |
| --- | --- |
| Arm | Root, Torso, Hips, Chest, Head |
| Leg | Root, Torso, Foot |
| Skirt - Spline | Root, Torso, Hips |
| Hair - Spline | Root, Torso, Head |
| Tail - Spline | Root, Torso, Hips |

### IK control as pole parent

The Leg assembly adds a **Foot** option.  When Foot is selected, the knee pole follows the IK foot control, so the knee points wherever the foot points.  The IK foot control itself follows the root.  This is the default for legs.

### Changing IK parents

IK parents can be changed without reconfiguring the assembly.  Select a bone in the assembly, then click **IK Parents** in the *[Assembly Panel](../assemblies.md#assembly-panel)*.  The dialog lets you:

- Add, remove, or rename parents.  Any bone in the armature can be used as a parent.
- Enable or disable **Add IK Control as Pole Parent**, and set its label.

The animator's current selection is kept where possible.

!!! screenshot "Image placeholder"
    `image/ik_parents_dialog.png` — The IK Parents dialog opened from the Assembly Panel for a leg, showing the label/bone rows, Add Parent button, and the "Add IK Control as Pole Parent" option with the "Foot" label.

## Parameters

- Setup IK Parent Switching: enable IK parent switching.  Default: on for Skirt - Spline, Hair - Spline, and Tail - Spline.  Always on for Arm and Leg.
- IK Parents: the list of parents.  Each parent has a label (shown in the Rig Properties dropdown) and a bone.

## Related

- [IK Assemblies](../ik_assemblies.md)
- [FK Assemblies](../fk_assemblies.md#torso)
- [Armature Settings](../armature_settings.md)
- [Standard IK](standard_ik.md)
- [Spline IK](spline_ik.md)
