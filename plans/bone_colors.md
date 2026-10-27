# Bone styles: side colors, roles, and central styling

## Next steps (start here)
Work in progress and not committed. The central styling works: a fresh build of Sarah has correct widgets, colors and wire widths, styles are saved on each assembly, and **Reapply Bone Colors** recolors every rig in the file.

**Resume here:**
1. Finish Stage 1 leftovers:
   - `assembly_panel.py` still lists `"master"` (lines 22, 62 and 82).
   - `fk_assembly.py:66`: promote only for MASTER-type masters (`create_master_controllers and master_controllers_type == 'MASTER'`).
   - `finger_curl.py`: role `fk` with `color='control'`, instead of role `control`.
2. Convert the code outside assemblies: `root_widget.py:23` and `human_skeleton.py:209` still read `prefs.control_bone_color`, which no longer exists. Switch them to `get_bone_color(prefs, 'root')`. Then the reapply operator can also recolor the root bone (`settings.root_bone_name`).
3. Fresh build of Sarah: check the collections, especially a MASTER-type tail (`Tail.L` masters, `Tail.FK.L` FK bones).
4. Migration (last).
5. Later: preserve hand edits across reconfigure, using the saved styles.

How we'll work: the user builds this. Claude explains, reviews and helps on request.

## Context
This started as the TODO item "L/R colors" and grew into a broader goal: tools *describe* how their bones should look, and one pass in `apply_tool` applies it. Side comes from the limb, so tools don't need to know their side.

Theme color sets are dark when unselected, so side colors are subtle. Custom colors (`palette = 'CUSTOM'`) could be added later inside `get_bone_color()`.

## Decisions
- **Roles:** `fk`, `ik`, `tweak`, `control`, `mch`. `master` is gone.
- **The role sets the collection; the color sets how prominent a bone looks.**
  - `control` is only for *separate* bones that drive a chain: MASTER-type masters (the tail case) and torso controls. It goes in the limb's base collection `{Name}{side}`.
  - Bones that are part of a chain keep `fk`, even when they act like masters. They're marked with `color='control'` instead. This covers FK-type masters, palm index/pinky and finger curl. You see all of a skirt's or hand's bones together.
- **Torso is special only in color.** Its bones use the `control` role with a `color='torso'` style override.
- **Color keys** (`get_bone_color`) are the roles, plus the color-only keys `torso` and `root`. `control` → FK Master color.
- **Color resolution:** an explicit `style.color` always wins. Otherwise a bone with exactly one role other than `mch` gets that role's color. A bone with several roles must be given a color explicitly; if not, it stays uncolored, which shows up in testing. There's no priority list.
- **Multi-role chains:** `FKChain` and `FKTweakChain` take `fk_color` (default `None`). The two `['fk', 'ik']` call sites pass `fk_color='fk'`.
- **No cross-assembly styling.** A tool may style a bone that an earlier tool in the *same assembly* registered (shoulder, foot roll). Styling a bone from another assembly raises `ValueError` in `apply_tool`.
- **Collections:** FK is promoted to `{Name}.FK{side}` when `control` bones claim the base collection. That happens with IK, torso, and FK assemblies with MASTER-type masters. Hands never promote. Promotion is one-way, like the IK split.
- **Promoting an existing limb:** `rename()` renames the old collection, which keeps its RigUI slot, and the base collection is recreated at the bottom of the RigUI. This is intended. `rename()` only deletes a collection once no bones are assigned to it; that's also intentional, so leave it alone.
- **Wire widths** (`utils/widget.py`):
  - `LIMB_FK_WIRE_WIDTH = 1.5`: FK chains with an FK/IK switch, and the shoulder.
  - `TORSO_FK_WIRE_WIDTH = 1.5`: the torso's FK chain.
  - `CONTROL_WIRE_WIDTH = 2.0`: masters, finger curl, torso controls, and palm index/pinky.
  - `IK_WIRE_WIDTH = 2.0`: IK controls, poles and the pole line, spline controls and twist, and foot roll.
  - Plain FK chains stay at Blender's default of 1.0.
- **`widget='NONE'` is recorded explicitly**, not skipped. `None` means "no change"; `'NONE'` means "no widget".
- **Default colors:** blue for left, red for right, the same for FK and IK. Center FK is blue and center IK is red. FK Master is orange, and tweak and torso are yellow. The user is trying these out.
- **Pinned:** renaming the old `control_bone_color` name everywhere (see step 2).

## Core design
**`utils/bone_colors.py`**
- `get_bone_color(prefs, color_key, side)` looks the key up in a key → preference table, and appends `_left`/`_right` for sided keys (`fk`, `ik`).
- `side_letter(side)` lives here because `naming` → `preferences` → `bone_colors` would be a circular import.

**`assemblies/tool_data/mechanism_bones.py`**
- `BoneStyle`: `widget`, `color`, `wire_width`, `scale`, `translate`, `rotate`, `transform_bone`. Every field defaults to `None` ("no change").
  - `set(**settings)` rejects unknown names.
  - `append(style)` merges in the fields of another style that aren't `None`.
  - `apply(context, pose_bone, side)` sets every field that isn't `None` and returns the widget object, if one was created. `transform_bone` is looked up through `pose_bone.id_data`.
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

**Reapply:** `operators/bone_colors.py` defines `RIG_OT_reapply_bone_colors`. It goes through every armature in the file and calls `BoneStyle(color=...).apply()` for each stored color, using `assembly.side`. The button is in Preferences, under the color grid. Rigs built before style storage have empty `style_json` and are skipped until they're rebuilt.

## Tool status
All tools inside assemblies have been converted:
- `fk_chain`, `fk_tweak_chain`, `fk_ik_switch`
- `master_controllers`, `finger_curl`, `palm`, `shoulder`
- `torso_fk`
- `standard_ik`, `spline_ik`, `foot_roll`

`self.side` and the leftover color and widget code have been removed.

**Outside assemblies:** `root_widget.py` and `human_skeleton.py` still need converting (step 2).

## Stages
1. **Roles and collections:** mostly done. The panel still has `master`, and promotion isn't done yet.
2. **Central styling:** done, including storage and reapplying colors.
3. **Migration:**
   - Existing rigs have `master` roles in `BoneRef.roles`, bones in `{Name}.Master{side}` collections, and the `master` value on `LimbCollectionMap`. The property is removed, but `row.get("master")` still reads the stored value.
   - Move those bones to the base collection, promote FK, and fix the RigUI layout.
   - Write it against a before/after of Sarah's rig.
   - Styles don't need migrating; a rebuild fills them in.
4. **Preserve hand edits:** when rebuilding, compare the live pose bones against the stored styles and keep anything that differs. Reapplying widgets in full needs `apply_widget(..., replace=True)` and has to keep `objects` in sync.

## Risk to watch
**Shared limbs:** resolved. Hands no longer promote, so the five finger chains and the palm all stay in `Hand.L`. Promoting a limb that's already built behaves as intended (see Decisions).
