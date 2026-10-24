# RigUI animator script / lite add-on (`rigui.py`)

## Next steps (start here)
Steps 1, 2, 3 and 5 are done, tested (rig_ui alone and inside rigtools) and committed (`b585c50`).
The file is now **`rigtools/rig_ui/rig_ui.py`** (renamed from `rigui.py`; plan text below still says `rigui.py`).
Bow-out (step 6) isn't built yet: **never load `rig_ui.py` as a text block/add-on while rigtools is enabled.**

**Resume here: step 4, collections view** (details under Build steps).

## Context
Animators currently need full RigTools to see the Rig UI panels. The goal is **one small file**, `rigtools/rig_ui/rigui.py`, used three ways:
1. Embedded in the .blend as an auto-registering text block.
2. Installed as a lite add-on, for animators who don't want to deal with auto-run. It's the same file; a single `.py` with `bl_info` is a valid legacy add-on.
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
- **Who registers:**
  - Add-ons load at startup; the embedded text only runs when a trusted file is opened. The embedded copy bows out silently if Rig UI panels are already registered (by lite or rigtools).
  - Lite + full rigtools enabled together is a **user error**. Whichever registers second shows only a red panel telling the user to disable one. No crash and no attempt to make both work.
- **Version check:** rigui hardcodes the newest `rig_data_version` it understands. If the rig's is higher, show a red "Update Rig UI" row and still draw what it can. No separate `rigui_version` field. Bump the constant in rigui whenever `CURRENT_RIG_DATA_VERSION` goes up.
- **Blender 4.x support:** rigui must run on 4.x and 5.x. In rigtools, 5.0-only icons go through `icon()` in [utils/icons.py](rigtools/utils/icons.py) (fallback table). Rigui should stick to icons that exist in both.

## Build steps
1. ~~**Spike.**~~ Done on 4.x and 5.2: raw reads work with rigtools disabled; `rigui.py` registers as a text block and as an add-on.
2. ~~**Store `ui_label`.**~~ Done: field on `AssemblyData`, set in `create_assembly_data`, `migrate_5_to_6` backfills it.
3. ~~**Properties and snapping.**~~ Done: in `rig_ui.py` with `stored()` reads; X-mirror kept (`flip_side_name` copied in, `naming.py`/`bone.py` import it back); `snapping_data.py` registers the snap data classes.
4. **Collections view.** `RIG_PT_collection_ui` mixes an animator view and a rigger edit mode in one panel. The panel moves to rig_ui; edit mode stays in rigtools and plugs in through a hook.
   - **Moves to `rig_ui.py`:** the panel, `_all_collections`, `_coll_by_name`, `_hidden_by_ancestor`, `_iter_descendants`, `_has_rig_ui_children`, `_collection_toggle_icon`, `_iter_rows`, `_hidden_map`, `_is_hidden`, and the view drawing (`_draw_view` → module function `draw_collections_view(col, armature_data)`).
   - **Stays in [collections_panel.py](rigtools/rig_ui/collections_panel.py):** `RigUICollectionLayoutItem` + `Armature.rig_ui_layout` registration, the WindowManager edit/selection props, all `RIG_OT_ui_collection_*` operators, `RIG_MT_ui_collection_actions`, `rename_layout_collection`, `_apply_rows` and the row-editing helpers, `draw_edit_buttons`, `_draw_edit`. It imports `_iter_rows` / `_is_hidden` back from rig_ui.
   - **The hook:** the rig_ui panel has a class attribute `edit_hook = None`. In `draw()`, if `edit_hook` is set, call it; if it returns True it drew the edit UI and the view is skipped. Rigtools sets `rig_ui.RIG_PT_collection_ui.edit_hook = draw_collection_editing` in `collections_panel.register()` and sets it back to `None` in `unregister()`. Standalone rig_ui never sets it, so it only draws the view and has no Edit button.
   - **Raw reads:** `stored(armature_data).get("rig_ui_layout", ())` (no layout yet is legitimate). `_apply_rows` is the only code that creates layout items: it writes `collection_name`/`same_row`/`hidden` on every collection item and only `is_gap` on gaps. So `item.get("is_gap", False)` (never written on collection items), and `item["collection_name"]`, `item["same_row"]`, `item["hidden"]` (always written, required).
   - **Register the panel in rig_ui's `classes`, before `RIG_PT_properties_ui`** (registration order = sidebar order).
   - **Fix while there:** `poll()` accepts any object with an Armature modifier, but `draw()` does `[...][0].object.data` and crashes if the modifier has no object. Put the lookup in one helper (`_panel_armature(obj)` returning armature data or None) used by both.
   - **Test:** rigtools enabled — view, Edit toggle, all edit operations, disabling rigtools. Rigtools disabled — view matches layout/gaps/hidden collections, no Edit button.
5. ~~**Visibility.**~~ Done: in `rig_ui.py` with hardcoded separators.
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
