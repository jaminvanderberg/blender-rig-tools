# Armature Settings


Each armature stores a few bone names that RigTools needs to know about: the root, the property bone, and the torso bones.  These are set in the **Armature Settings** panel.

**Where:** n-Panel > RigTools > Armature Settings
{ .where }

## Overview

The first time RigTools is used on an armature, the armature settings are filled in from the *[addon preferences](#addon-preferences)*.  After that, each armature keeps its own settings, so different rigs can use different names.

**Reinitialize from Preferences** resets the armature's settings back to the current addon preferences.

!!! warning
    The property bone must exist before any assemblies are created.  The assembly will fail with an error if it can't be found.
    The *[RigTools Human Skeleton](operators/human_skeleton.md)* includes a root and property bone.  If you're building your own skeleton, create these bones before creating assemblies.

!!! screenshot "Image placeholder"
    `image/armature_settings.png` — The Armature Settings panel in the RigTools n-panel with the default bone names filled in, plus the Reinitialize from Preferences button.

## Settings

**Root** and **Property** must already exist in your rig (`root` and `properties` by default).  See *[property bone](#property-bone)* below.

**Torso**, **Hips**, **Chest**, and **Head** are the names the *[torso](fk_assemblies.md#torso)* assembly gives the controls it creates (`torso`, `hips`, `chest`, and `head` by default).  *[IK parent switching](tools/ik_parent.md)* finds them by these names, which is why the torso should be set up before the arms, legs, and spline assemblies.

Change these if your rig already uses different names, for example when adding RigTools to an existing rig.

### Property bone

The property bone holds all of the custom properties that animators use to control the rig: FK/IK switches, rotation isolation, IK parents, IK stretch, and skirt collision and ride.  These are displayed in the *[Rig Properties](rigui/properties.md)* panel.

The property bone is usually placed above the character's head, and doesn't deform.  *[Apply Root Widgets](operators/apply_root_widgets.md)* gives it a gear widget and locks its transforms.

!!! warning
    Don't rename the property bone after assemblies have been created.  The rig's drivers and the Rig Properties panel look for properties on this bone.

## Upgrade Rig

Occasionally, an update to RigTools changes the data it stores on the armature.  When an older rig is opened with a newer version of RigTools, an **Upgrade Rig** button appears at the top of the Armature Settings panel and the *[Assembly Panel](assemblies.md#assembly-panel)*.  Click it to update the rig's data.

!!! tip
    Save a backup of the file before upgrading the rig.

## Addon Preferences

**Where:** Edit > Preferences > Add-ons > Rig Tools
{ .where }

The addon preferences set the defaults for new rigs.  Changing the preferences doesn't change existing armatures; use **Reinitialize from Preferences** for that.

**Export Settings...** and **Import Settings...** save and load the preferences as a JSON file.  This is useful for sharing settings between machines or Blender versions.

### Quick Bone Selection

- Selection Buttons: comma-separated list of the *[quick selection](selection.md#quick-select-buttons)* buttons.  Default: `FK, IK-, Tweak, DEF, ORG, MCH`.
- Columns: the number of columns for the selection buttons.  Default: 3.

### Name Stripping

- Tags to Strip: comma-separated list of prefixes and suffixes removed from bone names when RigTools names new bones.  Default: `ORG, DEF, MCH, CTRL`.  For example, `ORG-forearm.L` becomes `FK-forearm.L` instead of `FK-ORG-forearm.L`.
- Separators: the characters that separate tags from the rest of the name.  Default: `-._`

### Naming

- DEF Bone: the naming template for deform bones.  Default: `DEF-{name}`.
- Target/ORG Bone: the naming template for ORG bones.  Default: `ORG-{name}`.
- FK Bone: the naming template for FK controls.  Default: `FK-{name}`.

`{name}` is replaced with the base name of the bone.  `.L` / `.R` suffixes are always kept at the end of the name.  These are used by *[Generate ORG Bones](operators/generate_org_bones.md)* and the assemblies.

### Rig Structure Defaults

- Root Bone, Torso Bone, Hips Bone, Chest Bone, Head Bone, Property Bone: the defaults for the *[armature settings](#settings)* above.
- Non-Limb MCH Collection: the bone collection for mechanism bones that don't belong to a limb.  Default: `MCH-TMP`.
- MCH Parent Collection: the parent collection for all MCH bone collections.  Default: `MCH`.
- Widget Collection: the scene collection where *[widgets](utils/widget.md)* are created.  Default: `WGT`.

### Control Colors

The bone color sets used for each type of control.

- FK Color: default Theme 4.
- IK Color: default Theme 1.
- Master Control Color: used for the root, torso controls, master controllers, and other special controls.  Default Theme 2.
- Tweak Color: default Theme 9.

## Related

- [ORG & DEF](org_def.md)
- [Rig UI](rig_ui.md)
- [IK Parent Switching](tools/ik_parent.md)
- [Torso FK](tools/torso_fk.md)
