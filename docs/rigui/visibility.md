# Visibility

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

Shows and hides the character's meshes, mask modifiers, and solidify modifiers.

**Where:** n-Panel > Item > Visibility
{ .where }

## Overview

With the armature selected, the Visibility panel lists every mesh that belongs to the rig: meshes parented to the armature, and meshes deformed by it.  Each mesh has an eye button to show or hide it.  This is handy for hiding clothing or hair that's in the way while animating.

Meshes with **Mask** modifiers get their own box, with a toggle for each mask modifier.  Mask modifiers are often used to hide parts of the body that are under clothing.  A mask modifier named like `Mask-Shirt` is shown as "Shirt".

If any of the meshes have **Solidify** modifiers, a **Toggle Solidify** button turns them all on or off at once.  Solidify is often turned off while animating to keep the viewport fast.

With a mesh selected instead of the armature, the panel shows that mesh's mask modifiers and solidify toggle.

!!! tip
    Modifiers whose names start with an underscore (`_`) are ignored by the Visibility panel.  Use this for modifiers that animators shouldn't touch.

!!! screenshot "Image placeholder"
    `image/visibility_panel.png` — The Visibility panel for a clothed character, showing the body mesh box with its mask modifier toggles, the list of other meshes with eye toggles, and the Toggle Solidify button.

## Related

- [Rig UI](../rig_ui.md)
- [Rig Properties](properties.md)
- [Collections](collections.md)
