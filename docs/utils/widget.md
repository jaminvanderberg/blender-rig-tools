# Widgets

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

Widgets are the custom bone shapes used to display controls in Pose mode.  Many assemblies have one or more widget parameters for choosing the shape of their controls.

## Overview

When an assembly is created, RigTools assigns each control a widget as its custom shape.  Widgets are shared: each rig has one widget per shape, and every control with that shape uses it.  Widgets are named after the rig (for example, **WGT-Sarah-Circle**) and kept in a separate, hidden collection in the scene (**WGT** by default; see *[addon preferences](../armature_settings.md#addon-preferences)*).

Sharing keeps the number of widgets small and makes the one you want easy to find.  Widgets are never deleted, even when their assembly is deleted.  To remove leftover widgets, use **Clear Unused Widgets** in the *[Data Viewer](../data_viewer.md#widgets)*.

## Editing widgets

!!! warning
    Editing a shared widget changes every control that uses it.  The Custom Shape panel shows which bones share a widget, and the 3D View header shows a warning while you edit one.

Some controls have a widget of their own, so they're safe to edit:

- **Torso:** torso, hips, chest, neck and head
- **Arms and legs:** FK and IK hands, FK and IK feet, and toes

Left and right share the hand, foot and toe widgets, so an edit to one side applies to both.

To customize any other control, assign your own object as its custom shape.  RigTools keeps it when you reconfigure the assembly.  Only edit a shared widget if you want to change every control that uses it.

## Bone Style

**Where:** n-Panel > Rig Tools > Bone Style (Pose mode)

Shows the active bone's widget settings and color in one place, the same settings as Blender's Custom Shape and Pose Bone Color panels.  It works on any bone, on any armature.  On a control built by an assembly, a setting that differs from what the assembly built has a reset button next to it, which resets just that setting on the selected controls.

**Slide** moves the widget along the bone.  On the Torso, Chest and Hips controls, it moves the widget up and down the body.

**Scale** sizes the widget relative to how the assembly built it, so 1.0 is the original size.  On other bones, it's the widget's scale.  Widgets that run along the bone keep their length; round and flat widgets, and your own widgets, scale evenly.

Click the **Slide** or **Scale** label to show the full X, Y and Z values instead.

**Widget** shows the bone's current widget shape.  Pick another to give the selected bones a different widget.  It uses the shared widget for that shape, the same one every other bone on the rig with that shape uses.

Hands, feet, toes, head, neck and the torso controls have their own widgets.  Changing one of these gives it its own widget for the new shape, not the one other bones use.  Only the selected controls change, so select both sides to change both.  The original widget is kept, edits included, and comes back when you change back to its shape.

On a control built by an assembly, it's kept when you reconfigure, like any change, and reset brings back the original.

**Reset Widget Mesh** appears under the widget when its shape has been edited.  It puts the shape back the way RigTools made it, on every bone that uses the widget.  A dialog shows how many bones that is.  With **Keep a copy of the edited mesh** on, your edited shape is kept as a separate object named **WGT-EDITED-**, for example **WGT-EDITED-Sarah-FK-Hand**, so you can assign it to a bone yourself.  **Clear Unused Widgets** removes copies no bone uses.

## Reset to Default

**Where:** Properties > Bone > Viewport Display > Custom Shape, or right-click > Reset Style to Default (Pose mode)

Changes to a control's custom shape settings and bone color are kept when you reconfigure its assembly.  The Custom Shape panel lists what you've changed under **Edited**.

**Reset to Default** sets the selected controls back to the way their assembly built them.  It's only available when something on the selected controls has changed.  A dialog lists what has changed, so you can choose what to reset: Widget, Widget Mesh, Color, Translation, Rotation, Scale, Wire Width, Override Transform, and Display (Wireframe and Scale to Bone Length).  Your choices are remembered for next time.

**Widget Mesh** undoes edits to the shared widget's shape.  Because the widget is shared, this changes every control that uses it.  Use it to recover a widget you edited by accident.  **Keep a copy of the edited mesh** works the same as in Reset Widget Mesh above.

Resetting the widget doesn't delete your own object; it's just no longer assigned.

!!! screenshot "Image placeholder"
    `image/widgets.png` — A row of bones in Pose mode, each showing one of the selectable widget shapes (Circle, Rectangle, FK Shape, Box, Pill, Shoulder, IK Shape), labeled.

## Widget types

These are the shapes available in widget parameters (FK Widget, FK End Widget, Tip Widget, Master Controller Widget, etc.):

| Widget | Description | Used by default for |
| --- | --- | --- |
| Circle | A ring around the bone. | Most FK controls, toes, tails |
| Rectangle | A flat, narrow rectangle along the bone. | Skirt FK controls and masters |
| FK Shape | The FK limb shape. | Arm and leg FK controls |
| Box | A box around the bone. | — |
| Pill | A rounded, pill-shaped outline. | Palm controls |
| Shoulder | A curved shoulder shape. | Shoulder |
| IK Shape | The IK control shape. | — |
| None | No widget.  The bone is drawn normally. | — |

Some controls always use a fixed widget, such as the IK controls, poles, tweaks, spline controls, twist controllers, foot roll, finger curl, and the torso master controls.

## Root widgets

The **Apply Root Widgets** tool adds widgets to the root and property bones.  See *[Apply Root Widgets](../operators/apply_root_widgets.md)*.

## Related

- [FK Chain](../tools/fk_chain.md)
- [FK Tweak Chain](../tools/fk_tweak_chain.md)
- [Master Controllers](../tools/master_controllers.md)
- [Armature Settings](../armature_settings.md)
