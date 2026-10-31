# Data Viewer

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

Shows everything RigTools has stored about the armature's assemblies, and checks for stored data that no longer matches the rig.

**Where:** Properties > Armature (Object Data) > RigTools
{ .where }

## Assemblies

A list of all assemblies on the armature. Unlike the *[Assembly panel](assemblies.md)*, it doesn't depend on which bones are selected. Each assembly shows the icon of the button that created it, such as Shoulder or Simple FK. Assemblies with a problem from the last *[data check](#data-check)* have a warning icon.

Below the list are details for the selected assembly:

- **Select Bones** selects the assembly's ORG bones and the bones it created.
- **Reconfigure** and **Delete** work the same as in the Assembly panel.
- Collapsible sections list the ORG bones, twist bones, created bones, properties, objects, reparent rules, IK parents and options. Anything that's missing from the rig is shown in red. Click a bone to select it.
- Created bones are grouped by what they're for (FK, IK, tweak, control, mechanism). Under each bone are the widget, color and shape settings RigTools gave it when the assembly was built. Changes made by hand afterward aren't shown.

Selecting bones, Reconfigure and Delete need Pose or Edit mode.

## Limbs

Each limb and side, such as Left Arm, has its own set of bone collections for its FK, IK, tweak and control bones. Every assembly with that limb name and side shares them, so a shoulder, arm and fingers all end up in the same Left Arm collections.

Each limb shows:

- The assemblies that use it. A limb that no assembly uses is shown in red.
- **FK/IK split** if the limb has both FK and IK bones, which gives FK its own collection name.
- Each collection name and how many bones use it. A name shown greyed out with "not created" is reserved: the collection is created when a bone first needs it. A collection that bones need but that no longer exists is shown in red.
- The select button selects the controls of every assembly that uses the limb, ready for **Reconfigure All Selected** in the Assembly panel. It needs Pose or Edit mode.
- The pencil button renames the limb's collections, the same as in the *[Assembly panel](assemblies.md)*.

## Data Check

RigTools remembers bones, collections, objects and properties by name. If you rename or delete one by hand, or an operation is interrupted, RigTools can end up remembering something that isn't there anymore.

**Check Data** looks for these problems and lists them:

- **Errors** mean an assembly may not reconfigure or delete correctly. For example, an ORG bone was renamed or deleted, or two assemblies use the same bone. These can't be fixed automatically. Rename the bone back, or undo the change.
- **Warnings** are references to things that no longer exist, such as a deleted bone, widget object, bone collection, or FK/IK snapping data for a removed assembly.
- **Info** items are worth a look but often harmless, such as bones in the MCH collection that no assembly owns.

Click the select button next to an issue to show its assembly in the list and select its bone.

Click the wrench next to an issue to fix it, or **Fix All** to fix everything that can be fixed. Fixes only make RigTools forget things that no longer exist. They never delete bones, objects or properties, and they can be undone.

!!! tip
    Run Check Data after renaming bones or collections by hand, and before handing the rig off.

## Widgets

RigTools never deletes widgets on its own, so widgets can be left over after you delete assemblies or change widget types.  This section shows how many RigTools widgets no bone uses.

**Clear Unused Widgets** lists them and deletes them after you confirm.  It only deletes widgets RigTools created.  Your own objects are never deleted, even if they're in the widget collection.  It can be undone.
