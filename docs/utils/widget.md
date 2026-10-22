# Widgets

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

Widgets are the custom bone shapes used to display controls in Pose mode.  Many assemblies have one or more widget parameters for choosing the shape of their controls.

## Overview

When an assembly is created, RigTools creates a widget object for each control and assigns it as the bone's custom shape.  Widgets are created in a separate, hidden collection in the scene (**WGT** by default; see *[addon preferences](../armature_settings.md#addon-preferences)*).

Widgets belong to the assembly that created them.  They are deleted when the assembly is deleted or reconfigured.

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
