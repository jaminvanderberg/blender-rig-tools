# Bone style edits: keep hand edits across reconfigure

## Next steps (start here)
Steps 1–3c are built and committed as WIP (`e88fa9f`). Tested: every Custom Shape setting and edited widgets survive a reconfigure. Deleting every assembly left only `WGT-root` and `WGT-properties` in the widget collection, so edited widgets are deleted with their assembly. That was expected, and it's what 3e changes.

### Where I left off: 3e, partway through (not committed)
**Don't test yet.** `apply_tool` is half-done: `owned_widgets` isn't defined, and `self.objects.add()` has been removed.

**Settled since last time:**
- **Look for the old widget *before* `style.apply`.** The fresh widget doesn't exist yet, so the lookup can't return it. The fresh widget is still created for its fingerprint, then deleted if an old one is found.
- **"Unused" replaces `owned_widgets`.** A leftover is a widget nothing uses: `wgt.users == 1`, held only by the widget collection. A bone's custom shape counts as a user, so a widget in use has 2. That stops a rebuild from taking a widget another rig uses, without scanning every armature. Check it in the console once: `D.objects['WGT-...'].users`.
- **Widget names include a per-rig prefix,** so two rigs in one file don't share widget names: `WIDGET_TEMPLATE = "WGT-{prefix}-{name}"`.
  - `widget_prefix` is a hidden setting (`options={'HIDDEN'}`) in `armature_settings.py`. Initialize sets it once to the rig object's name, and only if it's empty, so Reinitialize never changes it and renaming the rig doesn't break lookups.
  - `generate_widget_name(name, context)` reads it with `get_armature_settings(context.object.data, context)`. Every caller already has `context`.
  - Sarah: click **Reinitialize from Preferences** once to get a prefix. The next reconfigure moves her widgets to the new names: edited ones are renamed as their assembly is deleted, and the rebuild finds them.
- **Bug: `stale` could delete another rig's widget.** It removed any unused-by-*this*-rig object with the bone's widget name. Use the same "unused" test: keep only `stale` widgets with `users == 1`. The prefix makes this rare, but the check is the actual guarantee.

**To do:**
1. `apply_tool`, in the "Bone Styles" loop:
   ```python
   pose_bone = pose_bones[bone_name]
   # Widget a delete left behind for this bone (see delete_assemblies)
   old = find_widget(context, bone_name) if style.widget not in (None, 'NONE') else None
   wgt = style.apply(context, pose_bone, limb_collections.side)
   if style.widget is not None:
       mech_bone.widget_fingerprint = widget_fingerprint(wgt)
   if style.color is not None:
       mech_bone.palette = pose_bone.color.palette

   if old:
       remove_object(wgt) # only needed for its fingerprint
       pose_bone.custom_shape = wgt = old

   prior_style = prior_styles.get(bone_name)
   if prior_style:
       prior_style.apply(pose_bone)
   if wgt and pose_bone.custom_shape != wgt: # user's own object: never ours
       remove_object(wgt)
       wgt = None
   if wgt:
       self.objects.add().name = wgt.name
   ```
   Remove the old swap block (`objects.remove(i)`).
2. `find_widget(context, bone_name)`: look up `generate_widget_name(bone_name, context)` in the widget collection, and return it only if `wgt.users == 1`. Drop the `owned_names` parameter.
3. `delete_assemblies`:
   - `stale` uses `users == 1` (see above);
   - pass `context` to both `generate_widget_name` calls;
   - remove the unused `keep_objects` parameter.
4. Widget prefix:
   - `widget_prefix` setting, hidden;
   - in `initialize_armature_settings`: `if not settings.widget_prefix: settings.widget_prefix = context.object.name`;
   - `generate_widget_name(name, context)` and `WIDGET_TEMPLATE`;
   - `create_widget` passes `context`.
5. Put `get_armature_settings(armature_data, context)` back to requiring `context`. It was changed to an optional `context` that silently skips initialization.
6. Cleanup:
   - `reconfigure_assembly.py`'s unused `bpy` and `BoneStyleConfig` imports;
   - the stray space in `collection.objects .get`;

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
- **How `generate_widget_name` gets the rig's prefix.** It uses `generate_widget_name(name, context)` for now, because it works and every caller has `context`. It still doesn't feel right: a name function shouldn't need rig state. Rejected so far: passing the prefix, passing the settings, passing the armature data (which needs `get_armature_settings` without `context`), an optional `context` on `get_armature_settings`, and splitting initialize from get. The pointer list (no prefix at all) was rejected as more data. There may be an assumption we haven't questioned yet, as with widgets being found by name. Revisit when it comes to mind. One clue: Reapply Bone Colors (`operators/bone_colors.py`) goes through every armature in the file, so there `context.object` isn't the rig being worked on. It reads `obj.data.rigtools` directly and skips uninitialized rigs. That's deliberate: calling `get_armature_settings(obj.data, context)` would initialize those rigs with the active rig's name as their prefix. So initialize uses `context` as a stand-in for "this rig's object", which only works while the two are the same.
- Silent or a summary? The leaning is silent. One option is a single INFO line from the reconfigure operator, such as "Kept hand edits on 12 bones; 2 no longer exist." It shows briefly in the status bar and stays in the Info log. No per-bone messages either way.
