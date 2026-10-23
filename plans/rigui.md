# RigUI animator script / lite add-on (`rigui.py`)

## Context
Animators currently need full RigTools to see the Rig UI panels. The goal is **one file**, `rigtools/rig_ui/rigui.py`, used three ways:
1. Embedded in the .blend as an auto-registering text block.
2. Installed as a lite add-on, for animators who don't want to deal with auto-run. It's the same file; a single `.py` with `bl_info` is a valid legacy add-on.
3. Imported by full rigtools as the **single source of the stored-data schema** and the read-only drawing.

The main concern is **data/schema divergence**: there must be one definition of what's stored on the armature, not two. The file stays static between feature releases.

How we'll work: the user builds this. Claude explains, reviews and helps on request. Each step is testable on its own.

## Core design
- **`rigui.py` owns the stored-data schema.** These move into it:
  - Data-only PropertyGroups: `RoleRef`, `BoneRef`, `OrgState`, `AssemblyProperty`, `AssemblyObject`, `AssemblyParent`, `ReparentRule`, `AssemblyData` (minus `apply_tool`), `RigUICollectionLayoutItem`, `RigUISnapBoneItem`, `RigUISnapChainItem`, and the `RigToolsArmatureSettings` fields.
  - Read helpers: `find_assemblies`, `find_snap_chain`, `get_bones_by_role`, `get_options`, `get_config_defaults`, `get_chain`.
  - Rigtools imports and registers these exact class objects.
- **Build-only code stays in rigtools:**
  - `apply_tool` becomes a free function `apply_tool(assembly, armature_data, tool, limb_collections)`, called from the four `*_assembly.py` builders.
  - Also staying: `create_assembly_data`, `check_assembly_use`, `_options_to_json`, `LimbCollectionMap`, `get_armature_settings` / `initialize_armature_settings`, and migrations.
- **Rigui registers the schema only when full rigtools isn't enabled.**
  - The check reads `bpy.context.preferences.addons`, which works in any load order.
  - If rigtools is enabled later, its registration replaces the definitions. Stored data is untouched.
  - On unregister, rigui only `del`s `Armature.*` properties whose `bl_rna.properties[name].fixed_type` is its own class.
  - When registered, everything reads by normal attribute access. No raw IDProperty reads.
- **Names:**
  - Rigui panels and operators use `RIGUI_*` / `rigui.*`. Full rigtools keeps `RIG_*` / `rig.*`.
  - `RIGUI_PT_*` `poll()` returns False while full rigtools' panels exist.
  - Draw functions take an operator prefix.
- **Lite add-on vs embedded text block** (identical names):
  - On register, check for an existing `bpy.types.RIGUI_PT_collections` and its `rigui_version` class attribute.
  - Skip if that version is ≥ ours. Otherwise call its stored unregister and take over. Re-running the text block uses the same path.
- **Version contract:**
  - `RIGUI_VERSION` in the file and `armature.rigtools.rigui_version` on the rig. The rig's value is the minimum rigui that rig needs.
  - Any schema edit happens in rigui.py, so it's obvious when to bump.
  - An older rigui shows a red "update Rig UI" row and still draws what it can. Unknown stored fields are preserved.
- **No addon prefs in rigui.** Separators (default `-._`) and the property bone name (default `properties`) come from fields on `armature.rigtools`, stamped by full rigtools.

## Build steps
1. **Spike.**
   - Minimal `rigui.py` with `bl_info`, one PropertyGroup, one panel, and the guarded register/unregister.
   - Test as a text block with Register checked, and confirm how `__name__` behaves on file load.
   - Test as an installed add-on, and alongside full rigtools in both enable orders.
2. **Move the schema.**
   - Relocate the data classes and read helpers into rigui.py.
   - In [assembly_data.py](rigtools/assemblies/assembly_data.py), [snapping_data.py](rigtools/rig_ui/snapping_data.py), [collections_panel.py](rigtools/rig_ui/collections_panel.py) and [armature_settings.py](rigtools/armature_settings.py), import from rigui instead of defining. Re-export names so the ~40 existing imports keep working.
   - Convert `apply_tool` to a free function.
   - Full rigtools should behave identically after this step.
3. **Collections view.**
   - Move the readers (`_iter_rows`, `_hidden_map`, `_is_hidden`, `_hidden_by_ancestor`, `_has_rig_ui_children`, `_collection_toggle_icon`, `_coll_by_name`) and `draw_collections_view` into rigui.
   - `RIG_PT_collection_ui._draw_view` delegates to it, and edit mode stays in rigtools.
4. **Visibility.**
   - Move [visibility_panel.py](rigtools/rig_ui/visibility_panel.py) logic into rigui, with separators from the rig.
5. **Properties and snapping.**
   - Move `_iterate_assemblies`, `ROLE_DATA` and `draw_float_with_buttons` from [property_panel.py](rigtools/rig_ui/property_panel.py), and the snap operators from [snapping_operator.py](rigtools/rig_ui/snapping_operator.py).
   - Bring the naming helpers they need: `get_base_name`, `flip_side_name`, `side_display_name`, `limb_group_label`, `mirror_pose_selection`, `get_selected_bones`. Separators are passed in.
   - Rigtools' `naming.py` imports these back so they're defined once.
6. **Armature fields.**
   - Add `rigui_version` and `separators` to the settings schema.
   - Migration 5→6 in [migrate_rig.py](rigtools/migrate_rig.py).
7. **Embed operator `rig.embed_rigui`.**
   - Writes `rigui.py` into `bpy.data.texts` with `use_module=True` and stamps the rig fields.
   - Offers an update when the embedded copy's `RIGUI_VERSION` is older.
8. **Build and docs.**
   - `build.sh` / `build.bat` emit `rigtools_ui.py`.
   - Update [docs/rig_ui.md](docs/rig_ui.md).

## Verification
- **After step 2:** full rigtools builds, reconfigures and deletes assemblies exactly as before, and an existing rig still loads with migration.
- **Embedded script, rigtools disabled, reopened:**
  - collection layout, gaps and hidden collections match
  - properties and FK/IK buttons auto-key
  - snapping works
  - mask and solidify toggles work
- **Combinations, enabled in each order:** full + lite, full + embedded, lite + embedded (older and newer), and all three.
  - No duplicate panels and no register errors.
  - Disabling the lite add-on doesn't strip rigtools' Armature properties.
  - The newest rigui wins.
- **`rigui_version` set above the script's version:** the warning shows.
- **Blender 4.x and 5.x.**
