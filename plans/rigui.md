# RigUI animator script / lite add-on (`rigui.py`)

## Next steps (start here)
Step 2 is done and tested. Steps 3 (properties + snapping) and 5 (visibility) are moved into `rig_ui.py` and wired into rigtools' `__init__.py`; old `property_panel.py`, `snapping_operator.py`, `visibility_panel.py`, `rig_ui_sample.py` deleted; `snapping_data.py` registers the snap data classes. Not yet tested or committed.
The file is now **`rigtools/rig_ui/rig_ui.py`** (renamed from `rigui.py`; plan text below still says `rigui.py`).

**Resume here:**
1. **Fix in `rig_ui.py`:**
   - `_iterate_assemblies`: `find_snap_chain(..., property.name)` → `name`; the `snap["switch_property"]` read runs before `if snap` (crashes on every non-switch property). Use `if snap and name not in group["snaps"]` and drop `switch_prop`.
   - `find_assemblies`: `o.get("name")` / `b.get("name")` → `o["name"]` / `b["name"]`.
2. **Test with rigtools enabled:** Upgrade Rig on the dev rig (v5 → v6) first. Then properties panel groups, FK/IK and On/Off buttons (with auto-key), both snap buttons, X-mirror selection, visibility masks/solidify, and disabling rigtools without errors.
3. **Test with rigtools disabled:** `rig_ui.py` as a text block, then as an add-on, on 4.x and 5.x. Same checks.
   - Bow-out (step 6) isn't built yet: **never load `rig_ui.py` while rigtools is enabled.**
4. **Commit.**
5. **Step 4: collections view** — the hardest split (see below).

## Context
Animators currently need full RigTools to see the Rig UI panels. The goal is **one small file**, `rigtools/rig_ui/rigui.py`, used three ways:
1. Embedded in the .blend as an auto-registering text block.
2. Installed as a lite add-on, for animators who don't want to deal with auto-run. It's the same file; a single `.py` with `bl_info` is a valid legacy add-on.
3. Imported by full rigtools, which registers rigui's panels/operators as its own animator UI.

Rigui contains **only** what animators need: collections (read-only), properties, FK/IK snapping, and visibility. Anything for building or editing stays in rigtools. Keep the file small; when in doubt, leave it out.

How we'll work: the user builds this. Claude explains, reviews and helps on request. We start and fix problems as they come up.

## Core design
- **Rigui registers no data classes.** It reads stored data by key through `stored(arm)` (already in `rigui.py`). Rigtools keeps its PropertyGroups exactly as they are.
  - 5.x: `arm.bl_system_properties_get()`. 4.x: `arm[...]`. Both confirmed with rigtools disabled.
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
- **Who registers:**
  - Add-ons load at startup; the embedded text only runs when a trusted file is opened. The embedded copy bows out silently if Rig UI panels are already registered (by lite or rigtools).
  - Lite + full rigtools enabled together is a **user error**. Whichever registers second shows only a red panel telling the user to disable one. No crash and no attempt to make both work.
- **Version check:** rigui hardcodes the newest `rig_data_version` it understands. If the rig's is higher, show a red "Update Rig UI" row and still draw what it can. No separate `rigui_version` field. Bump the constant in rigui whenever `CURRENT_RIG_DATA_VERSION` goes up.
- **Blender 4.x support:** rigui must run on 4.x and 5.x. In rigtools, 5.0-only icons go through `icon()` in [utils/icons.py](rigtools/utils/icons.py) (fallback table). Rigui should stick to icons that exist in both.

## Build steps
1. ~~**Spike.**~~ Done on 4.x and 5.2: raw reads work with rigtools disabled; `rigui.py` registers as a text block and as an add-on.
2. **Store `ui_label`.** *(code done, needs testing)*
   - `ui_label` field on `AssemblyData`, set in `create_assembly_data`; `CURRENT_RIG_DATA_VERSION = 6`; `migrate_5_to_6` backfills it; property panel groups by `ui_label`.
3. **Properties and snapping.**
   - Move the read-only parts of [property_panel.py](rigtools/rig_ui/property_panel.py) and [snapping_operator.py](rigtools/rig_ui/snapping_operator.py) into rigui, rewritten to use `stored()` reads. Drop `get_armature_settings`.
   - X-mirror selection: copy `flip_side_name` (hardcoded regex, ~10 lines) into rigui, or drop the feature from rigui. Decide here.
   - Rigtools registers rigui's classes instead of its own.
   - Delete the spike panel.
4. **Collections view.**
   - Move the read-only drawing (`_iter_rows`, `_hidden_map`, `_is_hidden`, `_hidden_by_ancestor`, `_has_rig_ui_children`, `_collection_toggle_icon`, `_coll_by_name`, view draw) into rigui.
   - Edit mode and its operators stay in rigtools, layered on top.
5. **Visibility.** Move [visibility_panel.py](rigtools/rig_ui/visibility_panel.py) into rigui with hardcoded separators.
6. **Bow-out, conflict handling, version check.** Embedded skip, lite+full red panel, "Update Rig UI" row.
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
- **Lite + embedded:** no duplicate panels.
- **Lite + rigtools:** red error panel, no crash, in both enable orders.
- **Rig with a newer `rig_data_version` than rigui knows:** the warning shows.
- **Blender 4.x and 5.x.**
