# Bone style edits: keep hand edits across reconfigure

## Next steps (start here)
Nothing is built yet. This is the design.

**Resume here:**
1. Fix the shared-widget delete bug (below). It's a standalone bug and should be fixed first.
2. Add the widget mesh fingerprint and the resolved palette to `style_json`.
3. Build `BoneStyleConfig` (snapshot + overlay).
4. UI: the signal row, Reset All, and the right-click Reset to Assembly Default.
5. Docs.

How we'll work: the user builds this. Claude explains, reviews and helps on request.

## Context
This comes from the TODO item "preserve hand-edited widgets/shape settings across reconfigure". Bone styles are already stored per bone in `BoneRef.style_json` (see `plans/bone_colors.md`, which is done). Today a reconfigure deletes the assembly and rebuilds it, so any style a user changed by hand is lost.

Style is the one kind of assembly data users are expected to edit. They already know Blender's tools for it (the Custom Shape panel, Copy to Selected), and those should keep working. Most other assembly data isn't safe to edit, so the UI has to make it clear that this data is.

## Decisions
- **It's an assembly config.** `BoneStyleConfig` follows the existing pattern in `config_registry.py`: `snapshot()` reads the live pose bones before the delete, `prepare_rebuild` carries the result in `prior_configs`, and the rebuild applies it. `SkirtCollisionConfig.snapshot()` is the model.
- **`style_json` always holds the assembly default.** Hand edits aren't stored anywhere. The live pose bone is the diff, and the snapshot only exists for the length of one rebuild.
- **The snapshot is the difference between the live bone and its own `style_json`.** Bones are matched by name. There's no comparison between the old build and the new build, because the old build is deleted before the new one exists.
- **A hand edit always wins over the rebuild.** If a user edited a widget and then changes the widget type in Reconfigure, they keep their edited widget. Resetting is how they get out of that.
- **Bones that no longer exist are dropped silently.** That covers bones removed by an option change, such as fewer twist bones or a different master type. Reconfigure can be undone.
- **Renaming is out of scope.** Renaming bones already means deleting the assembly, renaming, and recreating it. Configs aren't carried across a delete.
- **Reset works one field at a time, or on everything.** See UI.

## Core design

**What's compared (per bone, live vs. `style_json`):**
- **Shape:** which object is assigned to `custom_shape`, and whether our generated widget's mesh has been edited (see fingerprint).
- **Transform:** `custom_shape_scale_xyz`, `custom_shape_translation`, `custom_shape_rotation_euler`, `custom_shape_transform`.
- **Wire width:** `custom_shape_wire_width`.
- **Color:** the whole `pose_bone.color`: the palette and, for `CUSTOM`, the normal, select and active colors. `BoneStyle.apply` only sets the palette today.

Floats are compared with a tolerance. Panel and reset code use the same diff function as the snapshot.

**Widget mesh fingerprint.** `style_json` stores the widget type (`'CIRCLE'`), which can't show that the mesh was edited. When `apply_widget` creates a widget, store a fingerprint next to the default: the vertex count plus a hash of the rounded coordinates. Don't regenerate a widget to compare against, because a later change to a widget's design would make every old widget look edited. Rigs without a fingerprint count as unedited (today's behavior) until they're rebuilt.

**Resolved palette.** `style_json` stores the color key (`'fk'`). If the preferences change and Reapply hasn't run, comparing against the current preferences makes every bone look hand-colored. Store the resolved palette (for example `'THEME03'`) in `style_json` when the style is applied, and compare against that. Reapply Bone Colors updates it.

**Kept widgets:**
- The snapshot records the names of edited widget objects that we own.
- `delete_assemblies` skips those objects.
- After the rebuild, a kept widget is reassigned to its bone and added back to `assembly.objects`, replacing the freshly built widget.
- If the bone is gone, the kept widget is deleted, the same as a dropped style. This leaves no orphans.
- A shape the user assigned from their own object was never ours. It's never deleted; it's just reassigned to the bone.

**Overlay.** Applied once, after all the assembly's tools have run, in the same place as `apply_tool`'s style pass. Tools don't need to know about it.

**Reset.** `BoneStyle` already treats `None` as "no change", so resetting one field means applying a style that holds only that field from `style_json`:
```python
stored = bone_ref.get_style()
BoneStyle(wire_width=stored.wire_width).apply(context, pose_bone, side)
```
Resetting the shape replaces the widget, so it needs its own "remove only if we own it" check. `apply_widget(replace=True)` removes whatever is assigned, which is fine for the root widgets (its only caller today) but would delete a user's own object here.

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
- "Edited:" lists the fields that differ from the assembly default, and is hidden when none do.
- Reset All restores every style field on the selected bones.

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
- It's shown only for style properties on bones that have a stored style.
- It works wherever the property is drawn, including Blender's own panels.
- It acts on the selected bones, like Copy to Selected.

**Data viewer (optional).** A count of edited bones per assembly, with a reset button for the whole assembly.

**Not doing:** a separate panel that repeats every style field with a reset icon on each row. It would give users two copies of every control.

## Bug to fix first: shared widgets get deleted
`delete_assemblies` deletes every object in `assembly.objects` ([delete_assembly.py:59](../rigtools/assemblies/delete_assembly.py#L59)). `remove_objects` only checks users on the mesh data, after the objects are already removed. The bone dependency check doesn't look at widgets.

So if Copy to Selected gives a bone in assembly B the widget owned by assembly A, reconfiguring or deleting A leaves B's bone with no shape. This feature encourages Copy to Selected, so it will happen more often.

**Fix:** before removing anything, take out every owned widget that is still the `custom_shape` of a pose bone outside the assemblies being deleted.

## To check
- The class names of Blender's Custom Shape and Pose Bone Color panels in the targeted Blender version. They have changed between versions.
- How a `WM_MT_button_context` draw function finds the right-clicked property (`context.button_pointer` / `context.button_prop`) in the targeted version.
- Blender has two bone colors: the Bone color and the Pose Bone color. We set the Pose Bone color. If a user changes the Bone color instead, nothing changes in Pose Mode. The signal row on the Pose Bone Color panel helps, but the docs should say so too.

## Open questions
- Silent or a summary? The leaning is silent. One option is a single INFO line from the reconfigure operator, such as "Kept hand edits on 12 bones; 2 no longer exist." It shows briefly in the status bar and stays in the Info log. No per-bone messages either way.
