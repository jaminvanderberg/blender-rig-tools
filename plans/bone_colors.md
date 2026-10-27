# Bone styles: side colors, roles, and central styling

## Next steps (start here)
Work in progress, not committed. The addon **won't run** until the apply pass exists: the tools converted so far record styles but no longer set them.

**Resume here:**
1. Write the **apply pass** in `AssemblyData.apply_tool` (see Core design). Nothing visible works until this exists.
2. Finish converting the tools (see Tool status).
3. Finish Stage 1 leftovers: `assembly_panel.py` still lists `"master"` (lines 22 and 82). There's no promotion in `fk_assembly.py` yet.
4. Convert the code outside assemblies: `root_widget.py`, `human_skeleton.py`.
5. Fresh build of Sarah: check colors, widgets, wire widths and collections, especially the hands (the shared `Hand` limb).
6. Migration (last).

How we'll work: the user builds this. Claude explains, reviews and helps on request.

## Context
This started as the TODO item "L/R colors" and grew into a broader goal: tools *describe* how their bones should look, and one pass in `apply_tool` applies it. Side comes from the limb, so tools don't need to know their side.

Theme color sets are dark when unselected, so side colors are subtle. We judged them still worth having. Custom colors (`palette = 'CUSTOM'`) could be added later inside `get_bone_color()`.

## Decisions
- **Roles:** `fk`, `ik`, `tweak`, `control`, `mch`. `master` is gone. FK masters, finger curl and torso controls are all `control`, which is the limb's base collection `{Name}{side}`.
- **Torso is special only in color.** Its bones use the `control` role with a `color='torso'` style override.
- **Color keys** (`get_bone_color`) are the roles, plus the color-only keys `torso` and `root`. `control` → FK Master color.
- **Collections:** the base `{Name}{side}` holds the limb's main controls. FK is promoted to `{Name}.FK{side}` when something else claims the base. Torso already works this way. For fingers: `Hand.L` holds the masters, and `Hand.FK.L` holds the FK bones. Promotion is one-way, like the IK split.
- **Wire widths** (`utils/widget.py`): `LIMB_FK_WIRE_WIDTH = 1.5` for FK chains with an FK/IK switch, and `CONTROL_WIRE_WIDTH = 2.0` for masters, torso controls and IK controls. Plain FK chains stay at Blender's default of 1.0.
- **`widget='NONE'` is recorded explicitly**, not skipped. `None` means "no change"; `'NONE'` means "no widget". It matters once styles are saved or reapplied.
- **Empty styles are fine.** `add()` returns the bone's style, so `mch` bones get empty ones. They only exist during one build; skip empty styles when saving.
- **Pinned:** renaming the `control_bone_color` preference to match. The preference itself is now `torso_bone_color`, but some callers still use the old name (see Known breakage).

## Preferences (done)
- Theme color set enums. FK and IK have left, center and right. FK Master, Tweak, Torso and Root are center only.
- `fk_bone_color` and `ik_bone_color` are the center colors, so old exported settings still import.
- `draw()`: a label column, then a fixed-width 3-column `grid_flow` with centered cells.

## Core design
**`utils/bone_colors.py`**
- `get_bone_color(prefs, role, side)` looks the role up in a role → preference table, and appends `_left`/`_right` for sided roles (`fk`, `ik`). An unknown key raises `KeyError`.
- `side_letter(side)` lives here because `naming` → `preferences` → `bone_colors` would be a circular import.

**`assemblies/tool_data/mechanism_bones.py`**
- `BoneStyle`: `widget`, `color`, `wire_width`, `scale`, `translation`, `rotation`, `transform_bone`. Every field defaults to `None` ("no change"). `set(**settings)` rejects unknown names.
- `MechanismBones.styles` is a dict keyed by bone name. `style(name, **settings)` creates or updates the style and returns it. `add(name, role)` registers the bone and returns its style.
- **Overrides:** a tool can style a bone that another tool registered, by name. FK-type master controllers do this (`color='control'`). Later settings win, field by field.
- `append()` merges a child tool's styles into the parent.
- Tools record styles in `edit_mode`, next to where they create the bones. Bone lengths are available there, so scale calculations move to edit mode.

**The apply pass (`AssemblyData.apply_tool`), to do**
- Take `context` instead of `armature_data`. Widget creation needs it. Update the 4 callers in `fk_assembly`, `ik_assembly`, `palm_assembly` and `torso_assembly`.
- For each bone, if the style has:
  - **widget:** `apply_widget`, and add the widget's name to the assembly's `objects`. `'NONE'` → `custom_shape = None`.
  - **scale, translation, rotation, transform_bone, wire_width:** set the matching `custom_shape_*` property.
  - **color:** use `style.color` if set, otherwise the bone's first role that isn't `mch` (FK beats IK for shared `['fk', 'ik']` bones), with `limb_collections.side`.
  - **`mch` only, no style:** leave the color at default.
- Set pose bone properties (`obj.pose.bones[...]`). This runs in pose mode, right after `tool.pose_mode()`.
- Delete each tool's own color, widget and wire-width code, and `self.side`, as it's converted.

## Tool status
**Converted (style recorded in edit mode):**
- `fk_chain.py`: still has an unused `side` parameter and `get_bone_color` import.
- `fk_ik_switch.py`
- `master_controllers.py`: role `control`, FK-type override.
- `finger_curl.py`: role `control`. Still has `self.side` and old imports.

**Not converted (still color directly, most with `self.side`):**
- `fk_tweak_chain.py`: FK chain styling plus tweak spheres.
- `torso_fk.py`: custom sizing and offsets per bone; `color='torso'` on torso, hips, chest, neck and head. The sketch is in the conversation history; all values can be computed in edit mode.
- `palm.py`: index and pinky are FK bones from its internal `FKChain`; give them an override with `color='control'`. Stop passing `side` to the inner `FKChain`.
- `shoulder.py`: still uses `'fk_master'` as a color key (no longer valid); it should be sided FK.
- `standard_ik.py`, `spline_ik.py`, `foot_roll.py`: IK styling. `spline_ik.py:295` still reads `prefs.ik_bone_color`.

**Outside assemblies:** `root_widget.py` and `human_skeleton.py` set `color.palette` directly. Switch them to `get_bone_color(prefs, 'root')`.

## Known breakage
- `prefs.control_bone_color` no longer exists (it's `torso_bone_color`), but it's still read in `torso_fk.py` (lines 436-450), `root_widget.py:23` and `human_skeleton.py:209`.
- `'fk_master'` isn't a valid color key, but `palm.py` and `shoulder.py` still pass it.
- `MechanismBones.add()` still has unused `widget`, `weight` and `scale` keyword arguments from an earlier version.

## Stages
1. **Roles and collections:** mostly done. The panel still has `master`, and promotion isn't done yet.
2. **Central styling** (above): in progress. This replaced "color only in `apply_tool`".
3. **Migration:** existing rigs have `master` roles in `BoneRef.roles`, bones in `{Name}.Master{side}` collections, and the `master` value on `LimbCollectionMap`. The property is removed, but `row.get("master")` still reads the stored value. Move those bones to the base collection, promote FK, and fix the RigUI layout. Write it against a before/after of Sarah's rig.
4. **Later:** save styles on the assembly to preserve hand edits across reconfigure (TODO item). Only save styles that have at least one field set.

## Risk to watch
**Shared limbs:** five finger chains plus the palm use `Hand`/`.L`. When promotion happens after some chains are built, `rename()` only moves the RigUI layout slot if the old collection ends up empty (`limb_collections.py`, `rename`). Either `Hand.FK.L` gets no layout slot, or `Hand.L` loses its position. Check this in step 5 of Resume here.
