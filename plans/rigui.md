# RigTools UI: animator script / add-on (`rig_ui.py`)

## Next steps (start here)
Steps 1–5 are done, tested and committed (step 4 in `389802a`). Step 6 bow-out/conflict handling is built and tested, not yet committed; the version check is still to do.
The file is now **`rigtools/rig_ui/rig_ui.py`** (renamed from `rigui.py`; plan text below still says `rigui.py`).

**Resume here:**
1. Commit the step 6 bow-out/conflict work.
2. **Step 6, version check:** `RIG_DATA_VERSION` constant in rig_ui; red "Update RigTools UI" row when the rig's `rig_data_version` is higher.
3. **Step 7:** embed operator.

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
- **Version check:** rigui hardcodes the newest `rig_data_version` it understands. If the rig's is higher, show a red "Update Rig UI" row and still draw what it can. No separate `rigui_version` field. Bump the constant in rigui whenever `CURRENT_RIG_DATA_VERSION` goes up.
- **Blender 4.x support:** rigui must run on 4.x and 5.x. In rigtools, 5.0-only icons go through `icon()` in [utils/icons.py](rigtools/utils/icons.py) (fallback table). Rigui should stick to icons that exist in both.

## Build steps
1. ~~**Spike.**~~ Done on 4.x and 5.2: raw reads work with rigtools disabled; `rigui.py` registers as a text block and as an add-on.
2. ~~**Store `ui_label`.**~~ Done: field on `AssemblyData`, set in `create_assembly_data`, `migrate_5_to_6` backfills it.
3. ~~**Properties and snapping.**~~ Done: in `rig_ui.py` with `stored()` reads; X-mirror kept (`flip_side_name` copied in, `naming.py`/`bone.py` import it back); `snapping_data.py` registers the snap data classes.
4. ~~**Collections view.**~~ Done: panel, read helpers and `draw_collections_view` in rig_ui; edit mode stays in `collections_panel.py` and plugs in via `RIG_PT_collection_ui.edit_hook` (called as `self.edit_hook(context, armature_data)` — stored functions bind like methods). `_panel_armature()` fixes the armature-modifier-without-object crash.
5. ~~**Visibility.**~~ Done: in `rig_ui.py` with hardcoded separators.
6. **Bow-out, conflict handling, version check.** Bow-out and conflict done (see Core design → Who registers). Remaining: version check.
7. **Embed operator `rig.embed_rigui`.** Writes `rigui.py` into `bpy.data.texts` with `use_module=True`. Offers an update when the embedded copy is older.
8. **Build and docs.**
   - `build.sh` / `build.bat` copy `rigui.py` out as `rigtools_ui.py`, and fail if it imports `rigtools`.
   - Update [docs/rig_ui.md](docs/rig_ui.md).

## Later / optional
- Promote `limb_property_base_name` from options to an `AssemblyData.limb_name` field. Independent of rigui, since `ui_label` is computed at build time.
- Custom PNG icons for rigtools (not rigui) via `bpy.utils.previews`, if built-in icons can't tell templates apart.

## Verification
- **Full rigtools only:** builds, reconfigures and deletes assemblies as before; an existing rig migrates to v6 and shows the same property groups.
- **Embedded script, rigtools disabled, file reopened:**
  - collection layout, gaps and hidden collections match
  - properties and FK/IK buttons auto-key
  - snapping works
  - mask and solidify toggles work
- **Rigtools + embedded:** no duplicate panels; embedded bows out.
- **RigTools UI + embedded:** no duplicate panels.
- **RigTools UI + RigTools:** red error panel, no crash, in both enable orders.
- **Rig with a newer `rig_data_version` than rigui knows:** the warning shows.
- **Blender 4.x and 5.x.**
