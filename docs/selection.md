# Armature Panel

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

Quick switches for the rig and the meshes it deforms, plus tools for selecting bones and chains.  Every assembly starts with a selection, so these come up a lot.

**Where:** n-Panel > RigTools > Armature (the rig, or any mesh it deforms, is active)
{ .where }

!!! screenshot "Image placeholder"
    `image/armature_panel.png` — The Armature panel with the Pose/Rest toggle, the mode buttons, and the Select Connected / Select Mirror buttons.

## Pose and Rest Position

The **Pose** / **Rest** toggle switches the rig between its posed and rest positions.  It's the same setting as the armature's Pose Position / Rest Position, always one click away.

## Mode buttons

With the rig active, the buttons switch the rig between Object, Edit and Pose mode.

With the rig active, the **Meshes** list shows each mesh the rig deforms.  Click a mesh's name to select it, or use its buttons to jump straight to Edit mode or Weight Paint, or to hide or show it.  The list is alphabetical until you change it: click the sort button in the Meshes header to show up and down arrows.  The order is saved with each mesh, and the Shape Keys panel uses it too.

With a mesh active, the panel works from the rig that deforms it:

- **Pose** and **Edit** make the rig active and switch it to that mode, from any mode on the mesh.
- **Weight Paint** selects the rig too, so its bones can be clicked to pick a vertex group while painting.
- The **eye** hides or shows the rig, for when the bones are in the way.

## Select Connected

Extends the selection down the chain from each selected bone, following children that are **connected** to their parent.  It stops at bones that aren't connected, and at hidden bones.

This is useful for selecting several chains at once: select the first bone of each chain, then click Select Connected.  It's also useful for branching chains, like hair with flyaways, where only the connected part of the chain should be selected.

## Select Mirror

Adds the opposite side of each selected bone to the selection.  For example, selecting the left leg chain and clicking Select Mirror also selects the right leg chain, so both legs can be created as assemblies at the same time.

## Select Hierarchy

Blender's built-in hierarchy selection is also useful for chains, particularly when the bones aren't connected:

- Pose mode: **Select > Child** / **Extend Child** (++bracket-right++ / ++shift+bracket-right++)
- Edit mode: **Select > Child** / **Extend Child** (++bracket-right++ / ++shift+bracket-right++)

Extend Child adds the next bone down the chain to the selection.  Repeat it to walk down the chain one bone at a time.

## Select by name

Blender's **Select > Select Pattern** selects bones by name, for example `*FK*` for every bone with FK in its name.

## Related

- [Assemblies](assemblies.md#selection)
