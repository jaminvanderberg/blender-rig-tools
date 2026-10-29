# Bone style edits: keep hand edits across reconfigure

## Next steps (start here)
Steps 1 and 2 are committed (`35638f7`). 3a is built and tested. Its fixes, and the spline IK duplicate fix, aren't committed yet.

**Resume here:**
1. ~~Fix the shared-widget delete bug.~~ Done, see below.
2. ~~Store the widget fingerprint and the resolved palette.~~ Done.
3. Build `BoneStyleConfig`:
   - ~~3a. The diff: `style_diff()`.~~ Done and tested. See "Learned while testing 3a".
   - 3b. The snapshot: `BoneStyleConfig.snapshot()`, plus the list of widgets for `delete_assemblies` to keep.
   - 3c. The overlay: `finish_rebuild()`.
   - 3d. Data viewer: mark edited settings on each bone.
4. UI: the signal row, Reset All, and the right-click Reset to Assembly Default.
5. Docs. In `docs/data_viewer.md`, the line saying hand edits "aren't shown" changes with 3d.

How we'll work: the user builds this. Claude explains, reviews and helps on request.

## Context
This comes from the TODO item "preserve hand-edited widgets/shape settings across reconfigure". Bone styles are already stored per bone in `BoneRef.style_json` (see `plans/bone_colors.md`, which is done). Today a reconfigure deletes the assembly and rebuilds it, so any style a user changed by hand is lost.

Style is the one kind of assembly data users are expected to edit. They already know Blender's tools for it (the Custom Shape panel, Copy to Selected), and those should keep working. Most other assembly data isn't safe to edit, so the UI has to make it clear that this data is.

## Decisions
- **It's an assembly config.** `BoneStyleConfig` follows the existing pattern in `config_registry.py`: `snapshot()` reads the live pose bones before the delete, `prepare_rebuild` carries the result in `prior_configs`, and the rebuild applies it. `SkirtCollisionConfig.snapshot()` is the model.
- **`style_json` always holds the assembly default.** Hand edits aren't stored anywhere. The live pose bone is the diff, and the snapshot only exists for the length of one rebuild.
- **The snapshot is the difference between the live bone and its default.** Bones are matched by name. There's no comparison between the old build and the new build, because the old build is deleted before the new one exists.
- **Everything in Blender's Custom Shape panel is kept, plus the pose bone color.** That includes settings no style sets, such as Wireframe and Scale to Bone Length. Reconfigure recreates the bones, so anything not kept goes back to Blender's default, and the signal row says edits on that panel are kept.
- **A hand edit always wins over the rebuild.** If a user edited a widget and then changes the widget type in Reconfigure, they keep their edited widget. Resetting is how they get out of that.
- **Bones that no longer exist are dropped silently.** That covers bones removed by an option change, such as fewer twist bones or a different master type. Reconfigure can be undone.
- **Renaming is out of scope.** Renaming bones already means deleting the assembly, renaming, and recreating it. Configs aren't carried across a delete.
- **Reset works one field at a time, or on everything.** See UI.

## Core design

**The diff: `style_diff(pose_bone, bone_ref)`** in `assemblies/configs/bone_styles.py`. It returns `{property: live value}` for every setting that differs from the default:
- **Custom Shape settings** (`CUSTOM_SHAPE_PROPS`): scale, translation, rotation, wire width, Scale to Bone Length, Wireframe. The default is the `BoneStyle` field when the style sets it (`STYLE_FIELDS`), and Blender's own default otherwise, hardcoded in `CUSTOM_SHAPE_PROPS`. Floats are compared with a tolerance. Wireframe (`show_wire`) is on `Bone`, not `PoseBone` (`BONE_PROPS`, `_get_prop`).
- **Override Transform** (`custom_shape_transform`): compared and stored by bone name. An unset style field is `None`, which is also Blender's default.
- **Shape** (`custom_shape`): decided only by the fingerprint. A hand-made object or an edited mesh has a different fingerprint. A copy of an identical generated widget has the same fingerprint, so it doesn't count as an edit, and the rebuild giving that bone a fresh copy looks the same. With `widget` `None` or `'NONE'`, any shape counts as an edit. The value is the object name.
- **Color:** the pose bone palette is compared with the stored palette. For `CUSTOM`, the normal, select and active colors are stored too.
- **Rigs built before step 2** have no fingerprint or palette, so the diff skips their shape and color.

The snapshot, the signal row, Reset and the data viewer all use this same function.

**Widget fingerprint.** `widget_fingerprint(wgt)` in `utils/widget.py` returns a `hashlib` SHA-1 of the rounded vertex coordinates and edge indices. It uses `hashlib`, not `hash()`, because `hash()` has changed between Python versions. Widgets aren't regenerated to compare against, because a later change to a widget's design would make every old widget look edited.

**Stored on `BoneRef`, next to `style_json`:**
- `widget_fingerprint`: the mesh of the widget the style created.
- `palette`: the `color.palette` the style's color resolved to, for example `'THEME03'`.

These record what the style produced, which is why they aren't in `style_json`. `apply_tool` sets each one only when the style sets that field, so a later tool styling the same bone (shoulder, foot roll) only updates what it changed. Reapply Bone Colors updates `palette`. The palette is stored because comparing against the current preferences would make every bone look hand-colored after a preference change that hasn't been reapplied. The data viewer shows the palette with each bone's style.

**Snapshot (3b).** `BoneStyleConfig.snapshot()` runs `style_diff` on every bone in the assembly and returns `{bone name: diff}` for the bones that have one. It also records which edited widgets the assembly owns, so `delete_assemblies` can skip them.

**Overlay (3c).** A new `finish_rebuild(context, prior_configs)` next to `prepare_rebuild` in `reconfigure_assembly.py`. Each reconfigure operator calls it inside its `build()` (for example `fk_setup.py`, around `prepare_rebuild`), so it runs inside the assembly transaction. The rebuild reuses each assembly's uid, so the overlay finds each assembly by uid. Tools don't need to know about it.
- Each setting is applied by name. A missing bone, or a missing Override Transform target, is dropped.
- `show_wire` is set on `pose_bone.bone`. Use the `BONE_PROPS` check from `_get_prop`.
- A kept `custom_shape` can be `None`, if the user cleared a styled bone's shape.
- Kept widgets:
  - a kept widget is reassigned to its bone, replacing the freshly built widget. The fresh one is deleted, and the `objects` row is pointed at the kept widget;
  - a shape the user made from their own object was never ours. It's never deleted, just reassigned, and the fresh widget is deleted;
  - if the bone is gone, the kept widget is deleted, the same as a dropped style. This leaves no orphans.

**Reset.** `BoneStyle` already treats `None` as "no change", so resetting one field means applying a style that holds only that field from `style_json`:
```python
stored = bone_ref.get_style()
BoneStyle(wire_width=stored.wire_width).apply(context, pose_bone, side)
```
Settings the style doesn't set reset to Blender's default. Resetting the shape replaces the widget, so it needs its own "remove only if we own it" check. `apply_widget(replace=True)` removes whatever is assigned. That's fine for the root widgets (its only caller today), but here it would delete a user's own object.

## UI
An add-on can't put buttons next to Blender's own fields. It can add rows to a panel, or add items to the right-click menu.

**Signal row.** Append a draw function to Blender's Custom Shape panel and Pose Bone Color panel in Bone Properties. It's shown only on bones that have a stored style:
```
▾ Custom Shape
    Custom Object    [WGT-forearm_fk.L  ]
    Translation      ...
    Rotation         ...
    Scale            ...
    Wire Width       [ 2.5 ]
  ────────────────────────────────────────
  ✓ Rig Tools: edits kept on Reconfigure
    Edited: Scale, Wire Width     [Reset All]
```
- The ✓ line tells users this data is safe to edit.
- "Edited:" lists the settings that `style_diff` reports, and is hidden when there are none.
- Reset All restores every setting on the selected bones.

**Right-click: Reset to Assembly Default.** Append to `WM_MT_button_context`, the right-click menu on any property:
```
┌──────────────────────────────┐
│ Reset to Default Value       │  ← Blender's (e.g. wire width 1.0)
│ Reset to Assembly Default    │  ← ours
│ ──────────────────────────── │
│ Copy to Selected             │
│ ...                          │
└──────────────────────────────┘
```
- It resets only the property that was right-clicked.
- It's shown only for the kept settings, on bones that have a stored style.
- It works wherever the property is drawn, including Blender's own panels.
- It acts on the selected bones, like Copy to Selected.

**Data viewer (3d).** Mark edited settings on each bone, for example "Wire width: 2.0 (edited)". Optionally, a count of edited bones per assembly with a reset button for the whole assembly. Editing a widget's mesh and seeing the marker appear is also the test for the fingerprint.

**Not doing:** a separate panel that repeats every style field with a reset icon on each row. It would give users two copies of every control.

## Done: shared widgets no longer get deleted
`delete_assemblies` used to delete every object in `assembly.objects`. When Copy to Selected had given a bone in assembly B a widget owned by assembly A, reconfiguring or deleting A left B's bone with no shape.

**Fix (in `delete_assemblies`):**
- An owned widget that a bone outside the deleted assemblies still uses is kept and renamed after that bone.
- That bone's own widget is usually unused after Copy to Selected. If no surviving bone uses it, it's deleted first, so the kept widget gets the clean name.
- `objects` rows track widgets by name, so taking the name also moves ownership to the keeping bone's assembly. No extra bookkeeping is needed.
- Bones outside any assembly (root, properties) can still end up with a `.001`. That's rare.

## Learned while testing 3a
- **RNA defaults aren't reliable.** `PoseBone.bl_rna.properties[...].default` doesn't match the value a new bone gets. The values a new bone starts with come from Blender's DNA defaults, which RNA doesn't always mirror. Wire width read as wrong on every bone, so the defaults are now hardcoded.
- **`show_wire` lives on `Bone`.** The Custom Shape panel draws it from `pose_bone.bone`.
- **`SplineIK` registered its controls and twist bones twice** (`add()`, then `extend()`). `apply_tool` makes one `BoneRef` row per entry and stores the style only on the last one, so the first row had an empty style and looked fully hand-edited. The `extend()` calls are removed. Spline assemblies need a reconfigure to drop the duplicate rows. `MechanismBones.add` still doesn't check for duplicates.
- **Install the new build before testing.** `rigtools.zip` from `35638f7` predates `bone_styles.py`.

## Testing
**`style_diff`:** reconfigure the assemblies, so they have a fingerprint and palette, then:
```python
from rigtools.assemblies.configs.bone_styles import style_diff
for a in C.object.data.rigtools_assemblies:
    for ref in a.mechanism_bones:
        pb = C.object.pose.bones.get(ref.name)
        d = style_diff(pb, ref) if pb else None
        if d:
            print(a.name, ref.name, d)
```
1. Right after the reconfigure, nothing should print. Anything printed means a default is wrong, or a bone has a duplicate row.
2. Change a bone's wire width, color and scale, and edit its widget's mesh. Each change should show up for that bone and no other.

## To check
- The class names of Blender's Custom Shape and Pose Bone Color panels in the targeted Blender version. They have changed between versions.
- How a `WM_MT_button_context` draw function finds the right-clicked property (`context.button_pointer` / `context.button_prop`) in the targeted version.
- Blender has two bone colors: the Bone color and the Pose Bone color. We set the Pose Bone color. If a user changes the Bone color instead, nothing changes in Pose Mode. The signal row on the Pose Bone Color panel helps, but the docs should say so too.

## Open questions
- Silent or a summary? The leaning is silent. One option is a single INFO line from the reconfigure operator, such as "Kept hand edits on 12 bones; 2 no longer exist." It shows briefly in the status bar and stays in the Info log. No per-bone messages either way.
