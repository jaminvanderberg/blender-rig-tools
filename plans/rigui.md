# RigTools UI: animator script / add-on (`rig_ui.py`)

## Next steps (start here)
All build steps are done: 1-5, 6 (bow-out, conflict, version check), 7 (embed operator, tested incl. linking), 8 (build copies `rigtools_ui.py` with an import check; docs written). Docs, build and version check are not yet committed.
The file is `rigtools/rig_ui/rig_ui.py` (plan text below still says `rigui.py`). The embedded text block and the standalone add-on file are both named `rigtools_ui.py`.

**Resume here:**
1. Commit (stage all: `docs/operators/embed_ui.md`, `docs/rigui/animators.md`, `rigtools_ui.py` are new).
2. **Verification passed on Blender 5.x** (full checklist) **and 4.x** (embedded script after reload, RigTools UI add-on, RigTools). RigTools UI is complete.

## Context
Animators currently need full RigTools to see the Rig UI panels. The goal is **one small file**, `rigtools/rig_ui/rigui.py`, used three ways:
1. Embedded in the .blend as an auto-registering text block.
2. Installed as the **RigTools UI** add-on, for animators who don't want to deal with auto-run. It's the same file; a single `.py` with `bl_info` is a valid legacy add-on.
3. Imported by full rigtools, which registers rigui's panels/operators as its own animator UI.

Rigui contains **only** what animators need: collections (read-only), properties, FK/IK snapping, and visibility. Anything for building or editing stays in rigtools. Keep the file small; when in doubt, leave it out.

How we'll work: the user builds this. Claude explains, reviews and helps on request. We start and fix problems as they come up.

## Core design
- **Rigui registers no data classes.** It reads stored data by key through `stored(armature_data)` (already in `rigui.py`). Rigtools keeps its PropertyGroups exactly as they are.
  - 5.x: `armature_data.bl_system_properties_get()`. 4.x: `armature_data[...]`. Both confirmed with rigtools disabled.
  - Fields never written (e.g. a collection nothing was ever added to) have **no key**.
  - **No silent failures:** index required data directly (`assembly["name"]`) and let it raise. Use `.get(key, default)` only where absence is legitimate: no `rigtools` settings / not initialized, no assemblies, no snap chains, an assembly with no `properties`, a missing properties bone. Custom error messages only when they tell the user something actionable (e.g. missing `ui_label` → version incompatible).
  - Enum fields read back as ints. Rigui currently reads none.
- **What rigui reads** (the whole contract with rigtools — don't rename these in rigtools without updating rigui):
  - Collections: `rig_ui_layout[*]`: `collection_name`, `is_gap`, `same_row`, `hidden`; plus native bone collections.
  - Properties: `rigtools.is_initialized`, `rigtools.property_bone_name`; `rigtools_assemblies[*]`: `ui_label`, `org_states[*].name`, `mechanism_bones[*].name`, `properties[*]`: `name`/`role`/`qualifier`.
  - Snapping: `rig_ui_snap_chains[*]`: all fields.
  - Version check: `rigtools.rig_data_version`.
  - Visibility: nothing stored. Mask label separators are hardcoded (`-._ `).
- **Not initialized = no UI.** Rigui's polls read `armature.rigtools` directly and never auto-initialize.
- **Names stay as they are** (`RIG_PT_*`, `rig.*`). Only one copy is ever registered, so there's nothing to collide with.
- **Who registers** (built in `register()`/`unregister()`):
  - Whoever registers first owns the classes. It stamps `RIG_PT_collection_ui.rig_ui_embedded` (True for the text block, `__name__ == "__main__"`) and `RIG_PT_collection_ui.rig_ui_unregister` (its own `unregister`).
  - Later copies find the existing panel via `getattr(bpy.types, RIG_PT_collection_ui.bl_idname, None)`:
    - **Embedded text block:** bows out silently.
    - **Add-on finding the embedded copy:** calls `existing.rig_ui_unregister()` and takes over. Disabling that add-on later leaves no Rig UI until the file is reopened or the text re-run — accepted.
    - **Add-on finding another add-on** (RigTools UI + RigTools, a user error): prepends a red warning box to the existing Rig UI panel ("RigTools and RigTools UI are both enabled. Disable one, then restart Blender."). No separate panel.
  - `unregister()` only removes what that copy added (its classes, or its prepended warning), and resets `_registered` / `_conflict_panel` — module globals survive disable/enable.
  - Disabling the copy that loaded first while the other is still enabled leaves the second copy with no Rig UI. Covered by the "restart Blender" message.
- **Version check:** rigui hardcodes the newest `rig_data_version` it understands. If the rig's is higher, show a red "Update Rig UI" row and still draw what it can. No separate `rigui_version` field. Bump `RIG_DATA_VERSION` in rig_ui whenever `CURRENT_RIG_DATA_VERSION` goes up; rigtools' `register()` raises if they differ.
- **Blender 4.x support:** rigui must run on 4.x and 5.x. In rigtools, 5.0-only icons go through `icon()` in [utils/icons.py](rigtools/utils/icons.py) (fallback table). Rigui should stick to icons that exist in both.

## Build steps
1. ~~**Spike.**~~ Done on 4.x and 5.2: raw reads work with rigtools disabled; `rigui.py` registers as a text block and as an add-on.
2. ~~**Store `ui_label`.**~~ Done: field on `AssemblyData`, set in `create_assembly_data`, `migrate_5_to_6` backfills it.
3. ~~**Properties and snapping.**~~ Done: in `rig_ui.py` with `stored()` reads; X-mirror kept (`flip_side_name` copied in, `naming.py`/`bone.py` import it back); `snapping_data.py` registers the snap data classes.
4. ~~**Collections view.**~~ Done: panel, read helpers and `draw_collections_view` in rig_ui; edit mode stays in `collections_panel.py` and plugs in via `RIG_PT_collection_ui.edit_hook` (called as `self.edit_hook(context, armature_data)` — stored functions bind like methods). `_panel_armature()` fixes the armature-modifier-without-object crash.
5. ~~**Visibility.**~~ Done: in `rig_ui.py` with hardcoded separators.
6. ~~**Bow-out, conflict handling, version check.**~~ Done (see Core design > Who registers). Version check: `RIG_DATA_VERSION` in rig_ui; red box at the top of the Rig UI panel when the rig's `rig_data_version` is higher.
7. ~~**Embed operator.**~~ Done and tested (embed, update, linked into a shot file with library override).
   - [embed_ui.py](rigtools/rig_ui/embed_ui.py) (rigtools-only, never part of the embedded file): `RIG_OT_embed_ui` / `rig.embed_ui`. Button is the last item under Tools > Rig Setup ([panel.py](rigtools/panel.py)).
   - Click opens a confirmation dialog (`invoke_props_dialog`) explaining the script; wording changes for embed vs update. Undoable.
   - `execute` reads the add-on's `rig_ui.py` from disk into text `rigtools_ui.py` (reused if it exists), sets `use_module = True`, and points `armature.rigtools.ui_script` (new `PointerProperty(type=Text)` on `RigToolsArmatureSettings`, no migration needed) at it so linking the armature brings the text along (same trick as Rigify's `rigify_rig_ui`). Confirmed: the linked text runs when the shot file is next opened (not at link time).
   - Button states from `embed_state()`: MISSING "Embed Animator UI...", OUTDATED red "Update Animator UI (v0.1 > v0.2)...", CURRENT greyed "Animator UI Embedded (v0.2)". Version is parsed from the embedded text's `bl_info` with `ast` (never executed); a newer embedded copy counts as current (no downgrades).
   - **Release habit: bump `bl_info["version"]` in `rig_ui.py` on every change**, or old embedded copies won't be flagged. (Currently `(0, 2)`.)
   - Known gap (not yet decided): `execute` finds the text by name, so a renamed embedded text gets a fresh copy instead of an update. Fix: check `armature_data.rigtools.ui_script` before `texts.get(TEXT_NAME)`.
8. ~~**Build and docs.**~~ Done: `build.sh` / `build.bat` copy `rig_ui.py` out as `rigtools_ui.py` and fail if it imports `rigtools`. Docs: new [rigui/animators.md](docs/rigui/animators.md) and [operators/embed_ui.md](docs/operators/embed_ui.md); [rig_ui.md](docs/rig_ui.md) and [rigui/collections.md](docs/rigui/collections.md) updated.

## Later / optional
- Promote `limb_property_base_name` from options to an `AssemblyData.limb_name` field. Independent of rigui, since `ui_label` is computed at build time.
- Custom PNG icons for rigtools (not rigui) via `bpy.utils.previews`, if built-in icons can't tell templates apart.

## Verification
Final pass. **5.x: passed (full list). 4.x: passed (embedded script, RigTools UI add-on, RigTools).** Items marked *(seen)* were confirmed informally during development; re-check them once in the final pass.

**Setup for the pass:** run the build, so `rigtools.zip` and `rigtools_ui.py` are fresh. Use a rig saved at the current data version, plus one older (v5) copy for the migration check.

**RigTools only**
- [X] Build, reconfigure and delete an assembly; everything behaves as before.
- [X] Upgrade Rig on a v5 rig; property groups look the same afterward. *(seen)*
- [X] Rig UI: view, Edit toggle, and every edit operation (gap, move, shift, rename, hide/show, remove gap). *(seen)*
- [X] Rig Properties: FK/IK and On/Off buttons, auto-key on, both snap buttons, X-mirror selection. *(seen)*
- [X] Visibility: mask toggles, mesh eye toggles, Toggle Solidify. *(seen)*
- [X] Panels also show with a deformed mesh selected; a mesh whose Armature modifier has no object doesn't error.
- [X] Disable RigTools: no errors.

**Embedded script (RigTools disabled)**
- [X] Embed Animator UI: dialog, text block created with Register on, button shows "Embedded". *(seen)*
- [X] Reopen the file, allow scripts: all three panels work; no Edit button. *(seen)*
- [X] Bump `rig_ui.py` version: button turns red; Update replaces the text. *(seen)*
- [X] Link the character into a shot file + library override, save, reopen: panels appear. *(seen)*
- [X] Delete `rigtools_ui.py` in the Text Editor: button goes back to "Embed".

**RigTools UI add-on (`rigtools_ui.py`, RigTools disabled)**
- [X] Install from the build output, enable: panels work on a rig with no embedded script.
- [X] Disable: panels go away, no errors.

**Combinations**
- [X] RigTools + embedded file: no duplicate panels; Edit works (embedded bowed out). *(seen)*
- [X] RigTools UI + embedded file: no duplicate panels. *(seen)*
- [X] Open a file with an embedded script, then enable an add-on: the add-on takes over, no errors. *(seen)*
- [X] RigTools + RigTools UI, both enable orders: red warning in the Rig UI panel, no crash; disabling either gives no errors. *(seen)*

**Version check**
- [X] Set a rig's data version above `RIG_DATA_VERSION` (console: `C.object.data.rigtools.rig_data_version = 99` with RigTools enabled), then view it with RigTools UI: red "newer version of RigTools" box shows, panels still draw.

**Build**
- [X] Temporarily add `import rigtools` to `rig_ui.py`: the build fails with the import error. Remove it again.
