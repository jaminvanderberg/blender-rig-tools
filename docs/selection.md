# Selection

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

Tools for selecting bones and chains.  Every assembly starts with a selection, so these come up a lot.

**Where:** n-Panel > RigTools > Selection (Edit or Pose mode)
{ .where }

!!! screenshot "Image placeholder"
    `image/selection_panel.png` — The Selection panel showing the quick select buttons, the search field, and the Select Connected / Select Mirror buttons.

## Quick select buttons

A grid of buttons that select every visible bone whose name contains the button's text.  For example, **FK** selects all visible bones with "FK" in the name.  Matching is not case sensitive, and the buttons add to the current selection.

The buttons can be changed in the *[addon preferences](armature_settings.md#quick-bone-selection)*.  The default buttons are `FK, IK-, Tweak, DEF, ORG, MCH`.

Below the buttons is a search field.  Type part of a bone name and click the select button next to it to select all visible bones that contain that text.

!!! tip
    Hide the bone collections you don't want, then use a quick select button.  For example, show only the ORG collections and click **ORG** to select all of the ORG bones.

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

## Related

- [Assemblies](assemblies.md#selection)
- [Armature Settings](armature_settings.md#quick-bone-selection)
