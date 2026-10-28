# Bone styles: side colors, roles, and central styling

## Next steps (start here)
Not committed yet. The refactor works from start to finish on fresh and reconfigured builds:
- styles are saved on each assembly;
- **Reapply Bone Colors** recolors every rig in the file, including the root and properties bones;
- the end-user docs have been updated.

**Resume here:**
1. Commit.
2. Reconfigure every assembly in Sarah, then confirm each assembly shows `N/N` bones styled (console check below).
3. Migration: build `migrate_7_to_8` (see Stages), then run Upgrade Rig on Sarah from Object Mode.
4. Later: preserve hand edits across reconfigure, using the saved styles.

How we'll work: the user builds this. Claude explains, reviews and helps on request.

## Context
This started as the TODO item "L/R colors" and grew into a broader goal: tools *describe* how their bones should look, and one pass in `apply_tool` applies it. Side comes from the limb, so tools don't need to know their side.

Theme color sets are dark when unselected, so side colors are subtle. Custom colors (`palette = 'CUSTOM'`) could be added later inside `get_bone_color()`.

## Decisions
- **Roles:** `fk`, `ik`, `tweak`, `control`, `mch`. `master` is gone. Roles are only read for collections and the panel's select-by-role.
- **The role sets the collection; the color sets how prominent a bone looks.**
  - `control` is only for *separate* bones that drive a chain: MASTER-type masters (the tail case) and torso controls. It goes in the limb's base collection `{Name}{side}`.
  - Bones that are part of a chain keep `fk`, even when they act like masters. They're marked with `color='control'` instead. This covers FK-type masters, palm index/pinky and finger curl. You see all of a skirt's or hand's bones together.
- **Torso is special only in color.** Its bones use the `control` role with a `color='torso'` style override.
- **Color keys** (`get_bone_color`) are the roles, plus the color-only keys `torso` and `root`. `control` → FK Master color.
- **Color resolution:** an explicit `style.color` always wins. Otherwise a bone with exactly one role other than `mch` gets that role's color. A bone with several roles must be given a color explicitly; if not, it stays uncolored, which shows up in testing. There's no priority list.
- **Multi-role chains:** `FKChain` and `FKTweakChain` take `fk_color` (default `None`). The two `['fk', 'ik']` call sites pass `fk_color='fk'`.
- **No cross-assembly styling.** A tool may style a bone that an earlier tool in the *same assembly* registered (shoulder, foot roll). Styling a bone from another assembly raises `ValueError` in `apply_tool`.
- **Collections:** FK is promoted to `{Name}.FK{side}` when `control` bones claim the base collection. That happens with IK, torso, and FK assemblies with MASTER-type masters (`fk_assembly.py`). Hands never promote. Promotion is one-way, like the IK split.
- **Promoting an existing limb:** `rename()` renames the old collection, which keeps its RigUI slot, and the base collection is recreated at the bottom of the RigUI. This is intended.
- **Collections are never deleted while bones are assigned to them**, and deleting or reconfiguring an assembly doesn't delete collections at all. This preserves Rig UI data and collection state (see `docs/assemblies.md`). Leave `rename()` alone.
- **Root and properties bones:** styled by `apply_root_widgets()` in `root_widget.py`, which the operator and `human_skeleton` both call. They're colored `root`, with `ROOT_WIRE_WIDTH` and `replace_widget=True`. They aren't in any assembly, so there's no stored style. Reapply recolors them only if they're already colored (`palette != 'DEFAULT'`).
- **Wire widths** (`utils/widget.py`):
  - `LIMB_FK_WIRE_WIDTH = 1.5`: FK chains with an FK/IK switch, and the shoulder.
  - `TORSO_FK_WIRE_WIDTH = 1.5`: the torso's FK chain.
  - `CONTROL_WIRE_WIDTH = 2.0`: masters, finger curl, torso controls, and palm index/pinky.
  - `IK_WIRE_WIDTH = 2.0`: IK controls, poles and the pole line, spline controls and twist, and foot roll.
  - `ROOT_WIRE_WIDTH = 1.5`: root and properties.
  - Plain FK chains stay at Blender's default of 1.0.
- **`widget='NONE'` is recorded explicitly**, not skipped. `None` means "no change"; `'NONE'` means "no widget".
- **Default colors:** blue for left, red for right, the same for FK and IK. Center FK is blue and center IK is red. FK Master is orange, tweak and torso are yellow, and root is red. The user is trying these out. If they change, update `docs/armature_settings.md` (Control Colors) too.

## Core design
**`utils/bone_colors.py`**
- `get_bone_color(prefs, color_key, side)` looks the key up in a key → preference table, and appends `_left`/`_right` for sided keys (`fk`, `ik`).
- `side_letter(side)` lives here because `naming` → `preferences` → `bone_colors` would be a circular import.

**`assemblies/tool_data/mechanism_bones.py`**
- `BoneStyle`: `widget`, `color`, `wire_width`, `scale`, `translate`, `rotate`, `transform_bone`. Every field defaults to `None` ("no change").
  - `set(**settings)` rejects unknown names.
  - `append(style)` merges in the fields of another style that aren't `None`.
  - `apply(context, pose_bone, side, *, replace_widget=False)` sets every field that isn't `None` and returns the widget object, if one was created. `transform_bone` is looked up through `pose_bone.id_data`.
  - `to_json()` and `from_json()` store only the fields that are set.
- `MechanismBones.styles` is a dict keyed by bone name. `style(name, **settings)` creates or updates a style and returns it. `add(name, role)` registers the bone and returns its style. `append()` merges a child tool's bones and styles.
- Tools record styles in `edit_mode`, next to where they create the bones.

**`AssemblyData.apply_tool(context, tool, limb_collections)`**
1. **Loop over the tool's bones:** add rows and roles, assign collections, and resolve the color from the role when `style.color` is `None`.
2. **Loop over the tool's styles:**
   - find the row in this assembly (error if missing);
   - `style.apply(...)`, and add the widget to `objects`;
   - `row.add_style(style)` merges the style into the stored one.
   - Styles are applied in a separate loop because styled-only bones (shoulder, foot roll) aren't in the tool's bones.

**Storage:** `BoneRef.style_json` holds the merged style, with the color stored already resolved. Helpers: `get_style()`, `set_style()`, `add_style()`.

**Reapply:** `operators/bone_colors.py` defines `RIG_OT_reapply_bone_colors`. It goes through every armature in the file and calls `BoneStyle(color=...).apply()` for each stored color, using `assembly.side`, then recolors the root and properties bones. The button is in Preferences, under the color grid. Rigs built before style storage have empty `style_json` and are skipped until they're rebuilt.

**Console check** for saved styles:
```python
for i, a in enumerate(C.object.data.rigtools_assemblies):
    styled = [b for b in a.mechanism_bones if b.style_json]
    print(f"{i}: {a.name} ({a.assembly_type}) - {len(styled)}/{len(a.mechanism_bones)} bones styled")
```

## Status
- Every tool inside the assemblies has been converted: `fk_chain`, `fk_tweak_chain`, `fk_ik_switch`, `master_controllers`, `finger_curl`, `palm`, `shoulder`, `torso_fk`, `standard_ik`, `spline_ik` and `foot_roll`.
- `root_widget.py` and `human_skeleton.py` have been converted.
- `master` has been removed from `assembly_panel.py`.
- The end-user docs have been updated:
  - `armature_settings.md`: Control Colors and Reapply.
  - `rigui/collections.md`: FK promotion.
  - `tools/master_controllers.md`: color and collection.

## Stages
1. **Roles and collections:** done.
2. **Central styling:** done, including storage, reapply, and the root and properties bones.
3. **Migration: deferred.** Reconfiguring an assembly already converts it. Deletion removes bones by name and ignores roles, and the rebuild writes new roles, collections and styles. A rig that hasn't been reconfigured keeps working with its old colors and no saved styles. After reconfiguring, these are left behind:
   - empty `{Name}.Master{side}` collections and their RigUI layout entries;
   - the stored `master` value on each `LimbCollectionMap` row (`row.get("master")`).

   The user doesn't want to leave dangling data. Two options were discussed:
   - **Cleanup in `ensure_limb_collections`:** rejected. It puts legacy code in the normal build path.
   - **A real `migrate_7_to_8` in `migrate_rig.py`:** converts in place using each assembly's options. Finger curl `master` bones → `fk` in the FK collection. `master_controllers_type == 'MASTER'` bones → `control`, promoting the limb's FK and moving the bones to the base collection. Then delete the empty `.Master` collection and its layout entry, and remove the stored `master` value. Styles can't be rebuilt, so they fill in on the next reconfigure. This needs the rig data version bumped to 8 in `armature_settings.py` and `rig_ui.py`, so the embedded RigUI has to be re-embedded.

   **Decided: `migrate_7_to_8`, kept small.** Only `MasterControllers` type `MASTER` ever used the `master` role (finger curl was `control`, which is still valid, so it moves to FK on reconfigure). Bones that still have the role become `control`: the limb is promoted, the bone moves to the control collection, and `color='control'` is saved for Reapply. Every row's stored `master` is deleted, along with its collection and RigUI layout entry if the collection is empty. Version is 8 in `armature_settings.py` and `rig_ui/rig_ui.py`; `build.bat` regenerates `rigtools_ui.py`. Written (by Claude, on request) in `rigtools/operators/migrate_rig.py`, which moved there from `rigtools/`. Refuses to run in Edit Mode. Not yet tested.
4. **Preserve hand edits:** when rebuilding, compare the live pose bones against the stored styles and keep anything that differs. Reapplying widgets in full needs `replace_widget=True` and has to keep `objects` in sync.

## Side notes
- **Dev only:** the user's Addon Reloader calls `addon_disable`, which resets addon preferences to their defaults. The fix is to snapshot the preferences before disabling and restore them after enabling; there's a sketch in the conversation. Users who restart Blender normally aren't affected.
- **Optional:** in `__init__.py`, register `RigToolsPreferences` first and unregister it last. Then a bad preference fails before anything else is registered, which avoids orphaned panels.
