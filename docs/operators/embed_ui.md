# Embed Animator UI

Stores the Rig UI panels inside the .blend file, so animators can use the rig without installing RigTools.

**Where:** n-Panel > RigTools > Tools > Embed Animator UI
{ .where }

## Overview

Adds a text block named `rigtools_ui.py` to the file, containing the *[RigTools UI](../rigui/animators.md)* script, and sets it to run when the file opens.  The script draws the *[Rig UI](../rigui/collections.md)*, *[Rig Properties](../rigui/properties.md)* and *[Visibility](../rigui/visibility.md)* panels.  The armature keeps a reference to the script, so it comes along when the character is linked into another file.

Not every rig needs this.  Skip it if animators will have RigTools or the RigTools UI add-on installed, or if they shouldn't be asked to allow scripts.  See *[Sharing with Animators](../rigui/animators.md)* for the options.

Clicking the button opens a confirmation first.  The embed can be undone with *Ctrl+Z*, or by unlinking the text block in the Scripting tab in Blender.

If the file has more than one rig, each rig can be embedded; they share the same `rigtools_ui.py`.

## When to update

The script doesn't contain anything specific to your rig.  Everything the panels show (the collection layout, each limb's properties, the snapping setup) is stored on the armature and read by the script when it draws.  You can add, reconfigure, or delete assemblies and rearrange the Rig UI without embedding again.

The script only needs updating when you install a newer version of RigTools that comes with a newer version of the script.  The button turns red when that happens.

## Button states

| Button | Meaning |
| --- | --- |
| **Embed Animator UI...** | This rig has no embedded script. |
| **Update Animator UI (v0.1 > v0.2)...** (red) | The embedded script is older than the one in RigTools.  Click to replace it. |
| **Animator UI Embedded (v0.2)** (greyed out) | The embedded script is up to date. |

## Removing

Delete `rigtools_ui.py` in the Text Editor.  The button goes back to **Embed Animator UI...**.

## Related

- [Sharing with Animators](../rigui/animators.md)
- [Rig UI](../rig_ui.md)
