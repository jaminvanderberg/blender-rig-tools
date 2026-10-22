# Apply Root Widgets

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

Adds widgets to the root bone and the property bone.

**Where:** n-Panel > RigTools > Tools > Apply Root Widgets
{ .where }

## Overview

Gives the *[root bone](../armature_settings.md#settings)* a root widget, and the *[property bone](../armature_settings.md#property-bone)* a gear widget.  The property bone's location, rotation, and scale are locked, since it only holds properties and should never be moved by the animator.

The bone names come from the *[Armature Settings](../armature_settings.md)*.  If the property bone can't be found, only the root widget is applied.

Running the tool again replaces the existing widgets.

The *[RigTools Human Skeleton](human_skeleton.md)* applies these widgets automatically.

!!! screenshot "Image placeholder"
    `image/root_widgets.png` — Pose mode view of a rig showing the root widget on the ground and the gear widget on the property bone above the head.

## Related

- [Armature Settings](../armature_settings.md)
- [Widgets](../utils/widget.md)
- [RigTools Human Skeleton](human_skeleton.md)
