# Bone style edits: keep hand edits across reconfigure

## Next steps (start here)
Steps 1–3c are built and committed as WIP (`e88fa9f`). Tested: every Custom Shape setting and edited widgets survive a reconfigure. Deleting every assembly left only `WGT-root` and `WGT-properties` in the widget collection, so edited widgets are deleted with their assembly. That was expected, and it's what 3e changes.

### Where I left off: 3e, partway through (not committed)
**Don't test yet. `apply_tool` is broken in its current state:** `owned_widgets` isn't defined (NameError), and with `self.objects.add()` removed, no widget is registered as owned.

- **Done:**
  - `delete_assemblies`: keeps edited widgets (`edited`), alongside `kept` (shared) and `stale`.
  - `prepare_rebuild`: back to snapshot and delete, without `keep_objects`.
  - `find_widget()` in `utils/widget.py`.
- **Left in `apply_tool`** (the "Bone Styles" loop): after `old = find_widget(...)`, finish the pattern from the conversation:
  ```python
  if old:
      pose_bone.custom_shape = old
  prior_style = prior_styles.get(bone_name)
  if prior_style:
      prior_style.apply(pose_bone)

  # Hand edits replaced the fresh widget: only a kept widget becomes ours, never a user's own object
  if wgt and pose_bone.custom_shape != wgt:
      remove_object(wgt)
      wgt = old if pose_bone.custom_shape == old else None
  if wgt:
      self.objects.add().name = wgt.name
  ```
  And before the loop:
  ```python
  # Widgets any rig in the file owns. Anything else in the widget collection was left behind by a delete
  owned_widgets = {o.name for arm in bpy.data.armatures for a in arm.rigtools_assemblies for o in a.objects}
  ```
  Remove the old swap block (the `objects.remove(i)` code under `if prior_style:`).
- **Cleanup:**
  - `delete_assemblies` still takes `keep_objects`, but nothing uses it.
  - `reconfigure_assembly.py` still imports `bpy` and `BoneStyleConfig`, but nothing uses them.
  - `find_widget` has a stray space: `collection.objects .get`.

**Your questions, answered for when you pick it up:**
- **Why create the fresh widget and then look for the old one, instead of checking first?** Two reasons:
  - The fresh widget gives `widget_fingerprint`, the default that Reset and `style_diff` compare against. Without it, a bone that picks up an old widget would have nothing to compare against, and the old widget would look unedited.
  - `BoneStyle.apply` sets the widget along with everything else. Skipping only the widget would mean changing `apply`.

  Creating it and then deleting it is the simplest way to get both.
- **What's `owned_widgets` for?** It isn't about the fresh widget, which isn't owned yet; you're right about that. It stops `find_widget` from picking up a widget that an assembly that still exists is using. That mostly happens with **two rigs in one file**, which share the widget collection and can have the same bone names. Without the check, rebuilding rig 1's `thigh_fk.L` would take rig 2's `WGT-thigh_fk.L`, and both assemblies would own it. Within one rig it can't happen: the bones of the assembly being rebuilt were deleted first, and no two assemblies share a bone.
- **`find_widget` can return the fresh widget itself.** On a first build with nothing left over, Blender gives the fresh widget the clean name, and it isn't in `owned_widgets` yet. That's harmless: `custom_shape` stays `wgt`, nothing is removed, and the row is added. An explicit `if old is wgt: old = None` would make that obvious, if you'd rather spell it out.
- **A possible simpler check, not verified yet:** a leftover widget is one that no bone uses, so `wgt.users == 1` (linked only by the widget collection) might replace `owned_widgets`. That only works if a pose bone's `custom_shape` counts as a user in Blender. Test it in the console before relying on it.

**Resume here:**
1. ~~Fix the shared-widget delete bug.~~ Done, see below.
2. ~~Store the widget fingerprint and the resolved palette.~~ Done.
3. Build `BoneStyleConfig`:
   - ~~3a. The diff: `style_diff()`.~~ Done and tested. See "Learned while testing 3a".
   - ~~3b. The snapshot: `BoneStyleConfig.snapshot()`, plus `keep_objects` for `delete_assemblies`.~~ Done and tested.
   - ~~3c. The overlay, in `apply_tool`.~~ Done and tested.
   - 3e. Edited widgets survive a delete and are found again by bone name. See "Edited widgets outlive their assembly". This replaces `keep_objects` and the widget swap in `apply_tool`.
   - 3f. Optional, do last: Clear Unused Widgets in the data viewer. 3e works without it. Leftover widgets cost almost nothing, so wait and see whether anyone wants to clear them.
   - 3d. Data viewer: mark edited settings on each bone.
4. UI: the signal row, Reset All, and the right-click Reset to Assembly Default.
5. Docs:
   - In `docs/data_viewer.md`, the line saying hand edits "aren't shown" changes with 3d.
   - Clear Unused Widgets, plus one line in step 9 of `docs/workflow.md` (Check the rig's data).
   - Explain that edited widgets come back when an assembly is recreated.

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
- **Edited widgets outlive their assembly.** Deleting an assembly keeps any widget whose mesh was edited, under its bone's widget name. Building a bone with that name later picks it up again, whether that's from a reconfigure or from recreating the assembly. Unedited widgets are still deleted. Clear Unused Widgets is how users remove leftover widgets.
- **Renaming is out of scope.** Renaming bones already means deleting the assembly, renaming, and recreating it. Style settings aren't carried across a delete. Only edited widgets are, by name, so a rename leaves them for Clear Unused Widgets.
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

**Snapshot (3b, built).** `BoneStyleConfig.snapshot()` runs `style_diff` on every bone in the assembly and returns `{bone name: BoneStyleDiff}` for the bones that have one. Before the delete, `prepare_rebuild` collects every `custom_shape` named in those diffs and passes it to `delete_assemblies(keep_objects=...)`, which leaves those objects alone. 3e replaces this.

**Overlay (3c, built).** The overlay lives in `apply_tool`, not in a separate `finish_rebuild`. Each `create_*_assembly` passes its chain's `prior_configs` to `apply_tool`. The rebuild reuses each assembly's uid, so the configs line up. After each bone's style is applied:
- the bone's `BoneStyleDiff` is applied on top of it. Settings are applied by name, and `show_wire` goes on `pose_bone.bone`;
- if the result is a different shape, the fresh widget is deleted and its `objects` row removed, and the kept shape gets a row if it doesn't have one.

A bone that's gone simply never comes up, so its diff is dropped. 3e replaces the shape swap.

## Edited widgets outlive their assembly (3e)
Today a widget kept for a reconfigure is passed through `keep_objects`, and one whose bone is gone is deleted along with the assembly. Instead, a delete keeps edited widgets under their bone's widget name, and the build finds them again by that name. A reconfigure is a delete followed by a build, so it uses the same path and needs no special handling.

**On delete (`delete_assemblies`):**
- **Rule: RigTools keeps one widget per bone.** Kept widgets are found by the bone's widget name, so there's only one per bone. When two widgets compete for the name, the one the bone uses wins. That's what `stale` handles. Put this rule in the user docs.
- **So a widget is kept if it's edited and still in use.** An edited widget that the user has replaced themselves, for example with Copy to Selected, counts as abandoned and is deleted. That includes the `stale` case in the shared-widget fix. Undo brings it back.
- An owned widget is kept when its fingerprint differs from its bone's `widget_fingerprint`. That's the same test `style_diff` uses for the shape. A copy of a standard widget has the same fingerprint, so it's still deleted.
- The kept widget is renamed to `generate_widget_name(bone)` for the bone that uses it, in case it came from another bone. Its `objects` row goes away with the assembly, so nothing owns it.
- `keep_objects` and the `prepare_rebuild` code that builds it are no longer needed.
- A shape the user made from their own object was never ours. It's never deleted, as before.

**On build (`apply_tool`):**
- Right after the style creates a bone's widget, look in the widget collection for an unowned object named `generate_widget_name(bone)`. Blender will have named the fresh widget `.001` because that name is taken.
- If one exists: the bone uses it, the fresh widget is deleted, and the `objects` row is pointed at the kept widget.
- `widget_fingerprint` is still recorded from the fresh widget before it's deleted, so Reset knows what the default looks like.
- "Unowned" means no assembly's `objects` lists it. Only the widget collection is searched.

**Consequence:** a hand-edited widget now beats a changed widget type even across a delete. If someone deletes an assembly and recreates it with a different widget type, their edited widget comes back. Reset, or Clear Unused Widgets before recreating, gets the new type.

## Clear Unused Widgets (3f)
A button in the data viewer. It removes objects in the widget collection (the `widget_collection` preference) that no bone in any armature in the file uses as `custom_shape`.
- It never touches anything outside the widget collection.
- Root and properties widgets are in use, so they're safe.
- **Confirmation:** a dialog lists every widget it will delete, followed by Delete. It can be undone. The list also covers a widget the user put in the collection and hasn't assigned yet.
- **It's a separate button, not a Check Data fix.** The data viewer docs promise that fixes "never delete bones, objects or properties".
- Optional: Check Data reports "N unused widgets" as an Info item, pointing at the button.

**Reset.** `BoneStyle` already treats `None` as "no change", so resetting one field means applying a style that holds only that field from `style_json`:
```python
stored = bone_ref.get_style()
BoneStyle(wire_width=stored.wire_width).apply(context, pose_bone, side)
```
Settings the style doesn't set reset to Blender's default.

**Resetting the shape** uses the stored widget type (`style_json`'s `widget`, for example `'CIRCLE'`). That's enough to rebuild the default, because every widget is created by `BoneStyle.apply` → `apply_widget` from the type alone. No caller passes extra arguments, and scale, translation and rotation are separate fields.
```python
BoneStyle(widget=bone_ref.get_style().widget).apply(context, pose_bone, side)
```
Then the old shape is handled:
- **An owned widget, including a kept edited one:** if nothing else uses it, delete it and point its `objects` row at the new widget. Throwing the edited widget away is the point of resetting it, and Undo covers it.
- **An object the user made themselves:** leave it, and add a row for the new widget.

Don't use `apply_widget(replace=True)` here. It removes whatever is assigned, which is fine for the root widgets (its only caller today), but here it would delete a user's own object.

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
