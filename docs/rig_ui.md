# Rig UI

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

After you build assemblies, animators mostly work from the **Item** sidebar tab — not the
Rig Tools build panels. Rig UI surfaces bone-collection toggles, assembly custom properties,
FK/IK snapping, and related mesh visibility.

!!! tip
    Bone collections created by assemblies are **kept** when you delete or reconfigure an
    assembly, so your Rig UI layout can survive rebuilds. See [Assemblies](assemblies.md).

## Where to find it

With an armature active (or a mesh using that armature):

| Panel | Tab | Purpose |
| --- | --- | --- |
| **Rig UI** | Item | Toggle bone collections (layers) |
| **Rig Properties** | Item | Limb/assembly properties + snap buttons |
| **Visibility** | Item | Related mesh hide / mask / solidify helpers |

Build tools stay under **View3D → Sidebar → Rig Tools**.

## Rig UI (collections)

Shows buttons for bone collections so you can hide FK, IK, tweaks, MCH, etc. while animating.

- Layout is stored on the armature (`rig_ui_layout`): order, gaps, same-row grouping, and
  “hidden from Rig UI” (this is separate from Blender’s collection visibility).
- Collections not yet in the layout appear as extra rows at the end.
- If a parent collection is hidden in Blender, children won’t show usefully in the viewport
  even if the Rig UI toggle looks on.

### Edit mode

Turn on **Edit** on the Rig UI panel to rearrange the button layout:

- Select a collection or gap
- Join rows / move between rows / shift left–right
- Add or remove gaps
- Hide a collection from the Rig UI (e.g. bury `MCH-*` so animators don’t toggle it)

This is layout editing only — it does not delete Blender bone collections.

## Rig Properties

Shows custom properties for assemblies related to the **current bone selection**.

- Properties live on the armature’s **properties** bone (name from armature settings;
  default `properties`).
- Selecting any ORG or mechanism bone of an assembly pulls up that assembly’s props
  (FK/IK switch, IK parent, rotation isolation, etc.).
- Use the gear on a property to adjust its Rig UI label / enum presentation.

!!! note
    The properties bone must exist before assemblies are generated. Initialize armature
    settings (or create the bone) first — see [ORG & DEF](org_def.md#armature-settings).

### Snapping

For IK assemblies with snapping enabled, Rig Properties also shows snap operators next to
the FK/IK switch property:

| Button | Effect |
| --- | --- |
| **IK → FK** (names vary) | Matches IK control/pole to FK, then switches to IK |
| **FK → IK** | Matches FK bones to the IK pose, then switches to FK |

Snap chains are registered on the armature when the IK assembly is built. If you don’t see
buttons, the limb may have been built with snapping off, or the switch property isn’t the
one tied to a snap chain.

## Visibility

Helpers for meshes related to the armature (children / armature-deformed objects):

- Hide individual related meshes
- Toggle Mask modifiers (label cleanup for names like `mask…`)
- Toggle Solidify across related meshes

This is separate from bone-collection Rig UI.

## Typical animator loop

1. Build limbs/torso with Rig Tools ([IK](ik_assemblies.md) / [FK](fk_assemblies.md)).
2. **Edit** Rig UI collection layout once; hide MCH if you want a clean panel.
3. Animate using Rig UI toggles + Rig Properties (switch, parents, isolation).
4. Use snap buttons when changing FK vs IK on a limb.

## Related

- [Assemblies](assemblies.md)
- [IK Assemblies](ik_assemblies.md)
- [FK Assemblies](fk_assemblies.md)
- [ORG & DEF](org_def.md)
