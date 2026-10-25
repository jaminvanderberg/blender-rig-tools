# Sharing with Animators

How animators get the Rig UI panels without installing RigTools.

## Overview

The *[Rig UI](collections.md)*, *[Rig Properties](properties.md)* and *[Visibility](visibility.md)* panels don't need the full RigTools add-on.  They come from a single script, **RigTools UI**, that can reach animators in three ways:

| Option | Who sets it up | Best for |
| --- | --- | --- |
| **RigTools** add-on | Rigger | Riggers.  The panels are built in, plus the editing tools. |
| **Embedded script** | Rigger, once per rig | Handing a rig to animators who shouldn't need to install anything. |
| **RigTools UI** add-on | Each animator | Studios or animators who don't want scripts running from .blend files. |

All three show the same panels and read the same data from the rig.  Only the RigTools add-on can edit the Rig UI layout.

## Embedded script

**Where:** n-Panel > RigTools > Tools > Embed Animator UI
{ .where }

The rigger clicks *[Embed Animator UI](../operators/embed_ui.md)* once.  This stores the RigTools UI script inside the .blend as a text block named `rigtools_ui.py`, set to run automatically when the file opens.

The animator opens the file and clicks **Allow Execution** in the bar at the top of the window (or has *Auto Run Python Scripts* turned on in *Preferences > Save & Load*).  The panels then appear in the **Item** tab.

!!! note
    Blender only runs embedded scripts when a file is opened.  If scripts aren't allowed, the panels don't appear, but the rig itself still works.

### Linked rigs

The embedded script travels with the armature, so it comes along when the character is linked into a shot file.

1. In the shot file, *File > Link*, open the rig's .blend, and link the character's collection from the **Collection** folder.
2. Make it editable with *Object > Library Override > Make > Selected & Content*.
3. **Save and reopen the shot file.**  The script is linked in right away, but it only runs when the file is opened.  Allow execution when Blender asks.

## RigTools UI add-on

The same script can be installed as a normal add-on: *Edit > Preferences > Add-ons > Install from Disk*, then select `rigtools_ui.py`.  The panels then work for every RigTools rig, with or without an embedded script, and without allowing scripts in each file.

!!! warning
    Don't enable the **RigTools** and **RigTools UI** add-ons at the same time.  If both are enabled, the Rig UI panel shows a red warning.  Disable one of them, then restart Blender.

## When more than one copy is present

Rigs embedded with the script still work for animators who have an add-on installed:

- **An add-on is enabled:** the embedded script steps aside, and the add-on's panels are used.

## Updating

When RigTools has a newer version of the script than the one embedded in a rig, the *[Embed Animator UI](../operators/embed_ui.md)* button turns red and offers to update it.  Animators using the RigTools UI add-on update by installing the newer `rigtools_ui.py`.

## Related

- [Rig UI](../rig_ui.md)
- [Embed Animator UI](../operators/embed_ui.md)
- [Rig UI (Collections)](collections.md)
