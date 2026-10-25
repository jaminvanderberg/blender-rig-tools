# Rig UI

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

After the assemblies are built, animators work from the Rig UI panels in the **Item** tab of the n-panel, not the RigTools build panels.  The panels are built into RigTools, and can also be shared with animators who don't have RigTools installed.  See *[Sharing with Animators](rigui/animators.md)*.

!!! tip
    Bone collections created by assemblies are **kept** when you delete or reconfigure an
    assembly, so your Rig UI layout survives rebuilds.  See [Assemblies](assemblies.md).

## Panels

With the armature selected (or a mesh deformed by the armature):

| Panel | Tab | Purpose |
| --- | --- | --- |
| *[Rig UI](rigui/collections.md)* | Item | Buttons to show and hide bone collections |
| *[Rig Properties](rigui/properties.md)* | Item | FK/IK switching, IK parents, rotation follow, and other assembly properties, plus FK <> IK snapping |
| *[Visibility](rigui/visibility.md)* | Item | Show and hide the character's meshes and mask modifiers |

!!! screenshot "Image placeholder"
    `image/rig_ui_overview.png` — The Item tab with all three panels open (Rig UI, Rig Properties, Visibility) while an arm control is selected.

!!! note
    Animators don't need RigTools to see these panels.  Embed the script in the rig with *[Embed Animator UI](operators/embed_ui.md)*, or have animators install the **RigTools UI** add-on.  See *[Sharing with Animators](rigui/animators.md)*.

## Typical animator workflow

1. Set up the *[Rig UI](rigui/collections.md)* layout once: arrange the buttons, and hide the collections animators don't need (like MCH and ORG).
2. Select a control.  The *[Rig Properties](rigui/properties.md)* panel shows the properties for that limb.
3. Switch between FK and IK with the FK/IK buttons, using the *[snap buttons](rigui/properties.md#snapping)* to keep the pose.
4. Use the *[Visibility](rigui/visibility.md)* panel to hide clothing or meshes that are in the way.

## Related

- [Sharing with Animators](rigui/animators.md)
- [Assemblies](assemblies.md)
- [IK Assemblies](ik_assemblies.md)
- [FK Assemblies](fk_assemblies.md)
- [Armature Settings](armature_settings.md)
