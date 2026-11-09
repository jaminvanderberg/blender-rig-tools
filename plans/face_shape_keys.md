# Face rig: shape key capture

## Next steps (start here)
Only the items under "Decided" are the user's decisions; everything under "Proposed" is still open. These are general add-on tools for anyone building a face rig; nothing here edits a specific rig. Kendra is only the test case: `Z:\Data\Blender\Kendra\Kendra-Character1.blend` (RigTools rig `Armature`, 1519 bones, no face controls).

**Status (2026-11-09): the Connect redesign is built and committed** (`2b21dba`: direct drivers, connection records, extent, range) and tested headless on Kendra in Blender 5.2; the user has tried the bone view's list and Extent in the UI, not yet Range. Claude wrote it at the user's request. **Mirror Shape Key and lock support are built and working (2026-11-09)** (`mirror.py`, the user wrote most of it and Claude finished it; lock checks and the lock toggle by Claude): tested headless, and the user confirmed everything works in the UI. Not committed yet. **Next:** the remaining Connect work below; mirroring connections after.

Built, all in `rigtools/panels/shape_keys/`:
- `shape_keys_panel.py`: shown with the rig or any mesh it deforms active (`get_controlled_meshes` in `utils/object.py`; meshes with shape keys and an armature modifier using the rig). A mesh active shows just its list; the rig active shows one collapsible `layout.panel()` per mesh, in the Meshes list's manual order. Rows: name, value (greyed when driven), Blender's lock toggle (`lock_shape`, Basis included), Connect button (hidden on split sources and the Basis). Built-in search, invert and sort. Header: Blender's pin, Edit Key and Sculpt Key (click again for pose mode). Under the list: add, remove, the ▾ Specials menu, move up/down. Below that, for the active key: Vertex Group with an apply button, Create/Update L/R Shape Keys with Falloff, Mirror to <name>, and a Connections heading with one row per bone driving the key, from the connection records (bone name selects it, direction like `-X`, ✕ disconnects). **Bone view:** in pose mode, when the active bone has connections: its name with the Limited/Unlocked toggle, a UIList of its connection records (`RIG_UL_active_bone_connections`: key, mesh, direction, ✕), and for the selected record, Extent (moves the bone) and the key's Range (`slider_min`/`slider_max`, drawn directly).
- `connect.py`: Connect, Disconnect, Select Control, Select Connected Key, the limits, and the Extent slider properties (details below).
- `rig_data/shape_key_connections.py`: the connection records (PropertyGroup on `PoseBone`) and the only functions that touch them.
- `split.py`: Create/Update L/R Shape Keys. Smoothstep falloff across X = 0, stored per source as `split_falloff:<name>` on the Key. Respects the source's vertex group. New sides go right under the source, .L then .R, in one block move. Refuses driven keys.
- `mirror.py`: Mirror Shape Key, a "Mirror to <name>" button under the active key (greyed when the target is locked). Copies the key's shape mirrored across X onto its mirror key (`mirror_shape_key_name`), creating it under the source if missing; writes coordinates only. Mirror pairs from the Basis with a KD-tree (0.1mm); unmatched vertices are left alone and reported.
- `reverse.py`: Reverse Shape Key, in the ▾ menu. Folds the key into the Basis and makes the key take it back out; the mesh looks the same at every value, value and slider range flip. Refuses driven or keyframed keys, split sources and sides, muted keys, keys not relative to the Basis.
- `key_actions.py`: our own Remove and Move (Blender 5's act on every *selected* key, which deleted Kendra's Basis), and Apply Vertex Group (bake the key's group in and clear it). Built because the user often fixes stray edits with a vertex group.
- `shape_key_utils.py`: shared helpers (side names, `mirror_shape_key_name`, `has_sides`, `can_split`, `can_mirror`, `is_key_driven`, `is_locked`, key data, vertex group weights, moving keys).
- The Armature panel (`panels/armature/armature_panel.py`) replaced Selection: Pose/Rest, mode buttons, rig hide, a Meshes list with Edit, Weight Paint, select, hide and manual order.

Blender 5 notes: `shape_key_move` and remove act on all selected keys (`ShapeKey.select`, 5.0+); every move call re-evaluates the mesh and its modifiers (~0.1s on Kendra, mostly the Data Transfer), so moves are done as one block. Bone selection is `PoseBone.select` (was `Bone.select`). `Operator.check` is reserved; don't name a method `check`.

**Connect as built (2026-11-08)** (`connect.py`, `rig_data/shape_key_connections.py`):
- **Connection records:** `pose_bone.rigtools_shape_keys.items`, one per key the bone drives: `mesh` (Object pointer), `key_name`, `axis` ('X'/'Y'/'Z'), `positive`; plus `active_index` for the list. Functions: `get_`, `find_`, `add_`, `remove_shape_key_connection`, and `find_bone_connections_for_shape_key(armature_obj, mesh, key_name)` (every bone recorded as driving a key). The records are the source; drivers are output, built from them and never read back. No expression parsing anywhere.
- **Extent:** `SK ±Axis` custom property on the control per connected side (e.g. `SK +Z`), a positive distance. Connect sets it from the pose every time. Shared by every key on that side. Removed when the side's last connection goes.
- **Key driver** (`_build_driver`), rewritten from the records on every Connect and Disconnect: per bone, `capture_n` (Transform Channel, `LOCAL_SPACE`, location axis) and `extent_n` (the side's `SK` property); expression `max(capture_0 / extent_0, capture_1 / extent_1, 0)`, `-capture_n` on a negative side. No upper clamp: the key's own Range Max caps it. Removed (key set to 0) when no records are left.
- **Limits** (`update_limits`, `_build_limit_driver`): one "Shape Key Limits" Limit Location per control (local space, Affect Transform). Each connected side's field is driven by `extent * max(range_max_0, ..., 1)`, the Range Max (`slider_max`) of every key connected on that side. A key's Range Max of 1.2 lets the bone travel 20% past the extent and the key reach 1.2 (overshoot), with no lag. Unconnected sides are free; no connections removes the constraint. The Limited/Unlocked toggle mutes it; Connect turns it back on.
- **Extent slider:** a get/set `FloatProperty` on `PoseBone` (`rigtools_drive_pos_z` etc.) that writes `SK ±Axis` and moves the bone to that extent. Nothing saved. **The user dislikes this complexity and wants it scaled back later.**
- **Capture:** `matrix_basis` location, largest axis; rotated, scaled or unposed is refused.
- **Checks:** not the Basis, not a split source, mesh deformed by the armature, control isn't the property bone, not an assembly mechanism bone, not DEF-named. A key driver with no records behind it is someone else's: refused.
- **Disconnect:** takes bone, mesh, key and side; removes the record, updates the limits, rebuilds the key's driver.
- **Split sources can't be connected, and driven keys can't be split.**
- **Naming:** `armature_obj`, never `rig`; operator properties are `armature_name`.

**Lock checks built (2026-11-09)** with `is_locked` in `shape_key_utils.py`: Mirror refuses a locked target; Split skips a locked side and updates the other (user's choice), refusing only when both are locked; Reverse refuses if the key or the Basis is locked (other keys' locks don't matter, what they do is unchanged); Apply Vertex Group refuses a locked key.

**Still to do for Connect:**
- **Remove button:** the ✕ in each list row reads as text unembossed and looks poor embossed. Proposed: a − button in a column beside the list (Blender's convention), acting on the selected row; room there later for "select this key".
- **Repair** stale records (see Connect redesign).
- **MIN** per key; **interpolation** on the key driver's F-curve.
- **Range Min below 0** does nothing yet (the driver floors at 0). Making it work means the bone's opposite side drives the key negative, and that side may already belong to another key (eyelid). Later.
- **Limited/Unlocked toggle:** may be redundant now that Extent moves the bone and Range sets overshoot.
- **Old channel-layer leftovers** on Kendra (`SK-` properties and channel drivers on the property bone, key drivers reading them) are invisible to the new code and block reconnecting those keys: delete by hand or a one-off script.
- **Mirroring connections:** `.L` bone to `.R` with `flip_side_name`, the key with `mirror_shape_key_name` (so `Eye.Left.L` goes to `Eye.Right.R`), location X flipped.
- Deferred: leftover split falloff settings (see Open design questions).

### Connect redesign (decided and built 2026-11-08)
Started from the user's request for an **extent slider**: change how far a side must move to reach 1 without re-posing. The slider is the critical feature.

**Decisions:**
- **Direct drivers; the channel layer is dropped.** Sharing keys by matching name is an implicit coupling and a *cost* (the teeth's `Mouth.Open` following the face's should be a deliberate connection); a renamed key left a stale `SK-` channel; clutter on the property bone. A direct driver survives a key rename.
- **A real UIList, backed by stored records.** Hand-drawn rows posing as a list are out of the question; listing the rig's drivers through a filter was rejected. The user accepted stored add-on data here as necessary, in its own file (protected-members rule).
- **Repair against the drivers (not built).** Keys are stored by name, so a rename makes a record stale while the rig keeps working. Repair: when a record's key is missing on its mesh, find the key on that mesh whose driver reads this bone, axis and side, skipping keys claimed by another record, and take its name. No match: remove or flag. Ambiguous: flag. Draw can only show stale records; operators fix them.
- **Range instead of a separate Limit.** The user found "Range 0 to 1.2" far more natural than a limit distance with a link toggle. The key's own Range Max (Blender's field, no new data) drives the bone's limit, rather than the limit driving the key's slider max (tested: that lagged one update). Per key, not per key and bone: every bone driving a key lets it reach its Range Max; the user can't think of a case wanting otherwise.
- **No invert, anywhere.** Keys that are on at rest are fixed at the source with Reverse Shape Key.
- **MAX/MIN is per key.** MAX is the default and stores nothing. MIN (not built) would be a custom property on the mesh's Key, like `split_falloff:<name>`.

**Two separate relationships** (don't conflate them):
1. **One side, several keys.** A side is a bone plus a direction (upper lid −Z). It owns one extent; its limit is the extent times the largest Range Max among its keys. No combining.
2. **One key, several bones.** The key's driver combines its bones with MAX (default) or MIN.

**The eyelid case (why both are needed, no MCH bones).** Upper lid −Z drives `Eyelid.Upper`, `Eyelid.Lower` and `Eyelid.Smile`, all at the same distance. `Eyelid.Lower` is MAX(upper lid −Z, lower lid +Z): closing the upper lid pulls the lower one up, but the lower lid also moves on its own. `Eyelid.Smile` is MIN(upper lid −Z, lower lid +Z): it only shapes when both are applied (curved anime eye smile). The user rejected MCH follow bones for this, and a one-key-per-side rule was dropped because of it.

**Ground rules:**
- Keep blend data minimal: Blender's own fields first; visible custom properties only where a driver must read a value; add-on data only where necessary, owned by one module.
- Simple expressions only: no Python, no auto-run. Check `driver.is_simple_expression`.
- Old-format connections vanished from the panel when the expression format changed: the reason drivers are never the thing we read.

How we'll work: Claude does the plumbing (panels, registration, boilerplate) and answers lookups; the user writes the logic unless they ask Claude to (they did for Connect, Split, Reverse). Claude reviews on request. The user is also improving Kendra's face rig alongside the tools, and may ask best-practice questions as we go.

## Context
Wiring shape keys to bones by hand is the tedious part of a face rig. FaceIt can make shape keys, but its control rig is a separate armature and joining its deform rig to the body is destructive. RigTools only handles the wiring, so it doesn't care where keys come from (sculpted, or baked with FaceIt).

**The core mechanism:** pose a control at its extreme, pick a shape key or dial up a mix of them, click capture. Each key gets a driver reading that control. Same gesture as corrective bones. **All of this happens in pose mode.** The problem it solves is the old loop: pose mode to find the property, object mode to add the driver on the key, pose mode to test, object mode to tweak.

Example: bone 1cm up on local Y, `Mouth.Smile.L` at 1.0, `Cheek.Puff.L` at 0.4:
```
Mouth.Smile.L: clamp(var / 0.01, 0, 1)
Cheek.Puff.L:  clamp(0.4 * var / 0.01, 0, 0.4)
```
Moving the same bone the other way can capture different keys, so one control covers smile and frown.

## Control placement
- **On the face:** anything with a place on the face. Brows, lids, mouth corners, sneers, cheeks.
- **Flat panel:** states and choices with no natural spot. Mouth shapes for speech, highlights, pupils, blush, emotes.

Capture works the same for both. Face shapes are mostly keys, with small deform bones layered on top where keys don't give enough control (brows, lids). The jaw should be able to go either way: a key (Kendra's `Mouth.Open`) or a real bone.

## State of Kendra (2026-11-06)
- `Kendra` has 67 keys including Basis. Its 43 drivers have no live targets, and the `SK` bones they name are gone. They should be deleted: a driven key can't be dialled by hand, and capture skips driven keys.
- Ignore the normal cage meshes. Their shape keys are only there because they were duplicated from the body.
- `Pupil.L` and `Pupil.R` have a slider range of -1 to 1. Everything else is 0 to 1.
- **Many of her keys lost their sides.** Measured on all four files: `Kendra.blend` (8880 verts) has correct one-sided keys. `Kendra-Character.blend` (4534 verts) is a half mesh, where `.L` keys are intact and `.R` keys are empty. In `Kendra-Character2.blend` and `Kendra-Character1.blend` the mesh is whole again, so `.L` keys move **both** sides, and `.R` keys are empty or nearly so. This looks like the result of cutting the mesh in half and mirroring it back. Good shape data for both sides still exists in `Kendra.blend`.
- **L/R keys can't be assumed correct.** The user relied on vertex groups in places instead of making true mirrored keys, because applying a shape to a new key is annoying. They'll repair the keys with the tool, which makes this its first real use.
- Current `.L` keys are effectively whole-face keys, so they can be the source for that repair. The `Left Face` and `Right Face` vertex groups still exist in `Kendra-Character1.blend`.
- Splitting direction keys needs care: the mirrored half of `Eye.Left.L` is really the shape for `Eye.Right.R`, not `Eye.Left.R`.
- The non-side keys of a set (`Mouth.Smile`) were never whole-face keys. In `Kendra.blend` they hold one side only, with a `Right Face` vertex group. In `Kendra-Character1.blend` most of them are empty.

## Decided
- **Everything works from pose mode.** Pick one key or mix several, without leaving pose mode. Baseline requirement.
- **Symmetric key management is core.** Editing the full face and updating the sides quickly is one of the most tedious jobs, so it needs to be fast. Making a true one-sided key has to be easier than leaning on a vertex group, or the shortcut wins again.
- **Emotes, blush and similar are core**, not later. See Emotes and sliders.
- **Add-on tools only.** Nothing is written for one specific rig.
- **The panel lists every object the rig controls.** A pose mode panel shows the shape keys for each object with shape keys and an armature modifier pointing at this rig. An armature modifier is required, no exceptions. Objects can collapse when there are several. Kendra has two: the main model and the hair. The normal cages have no armature modifier, so they're left out automatically.
- **The full-face key is the source for the sides.** Build it with mirror on, then split it. Update overwrites the sides, and that's accepted.
- **A key's vertex group counts as applied (2026-11-09).** Any tool that reads a key's shape uses its delta multiplied by its vertex group, as Split already does. No tool refuses because a key has a group.
- **Locked keys are respected (2026-11-09).** Blender's `lock_shape` is shown in the list, and no tool writes to a locked key.
- **Mirror Shape Key (2026-11-09).** Copies a key onto its mirror key, side to side, and never writes back to the full-face key. Split stays as it is. Full-face keys become optional once you mirror, but the tool never deletes them; it only offers tools that help. Direction words flip with the side: `Eye.Left.L` mirrors to `Eye.Right.R`. See "Sculpting one side".
- **The side weight is calculated.** No vertex group needed: the same tiny falloff at the center the user normally paints.
- **Jump to edit.** One click into editing a key on its mesh, one click back to pose mode.
- **Emote sliders support both** bones and Rig UI custom properties, chosen per emote.
- **Emotes are reversed.** Rest is out and visible, and off is the captured extreme, in the head and scaled down. An MCH bone takes the driving, so the control stays free. See Emotes and sliders.
- **Emote off poses are location and scale only.** No rotation.
- **Capture writes bone limits.** A checkbox on the operator, on by default.
- **Corrective bones get an Extrapolate setting** in their tweak panel. See Limits and extrapolation.
- **Capture connects, it doesn't mix.** Pose a bone to an extreme, pick one shape key, click to connect them. The extreme sets that key to 1, or to 0 if inverted. An Invert option is the only setting. Driving another key from the same bone is another click. No dialed values.
- **Easing is optional,** hidden, linear by default. The jaw needs it: it should spend more time barely open.
- **Extra play past the extreme isn't critical.** The old mouth controls' 1.25 at the limit was either rough manual math or deliberate play. Worth trying later.

## Proposed (open)
- **The panel.** Each key row has a Connect button and shows what already drives it. Rows are drawn from the mesh's data, so the mesh doesn't need to be active.
- **Location only.** The user has never rotated a shape key control. A Transform Channel variable can read rotation later without changing the format.
- **Leave the control posed after capture.** Correctives clear the pose so the correction isn't applied twice. Here the bone is the input, so staying posed means the result is visible and testable at once, with no jump.
- **Control names.** Drop the `SK-` prefix. It means nothing to Blender or RigTools, and RigTools controls have no prefix (`BONE["control"]` is `{name}`). Capture works on any bone name and recognizes its drivers by variable name, so it doesn't depend on this.
- **ORG bones.** Controls that only drive keys get no ORG or DEF bone; Generate ORG Bones works from DEF bones, so it won't touch them. A face bone that actually deforms is a normal DEF + ORG bone, and the pinning rules still apply to it.
- **Driver format:** a Transform Channel variable in `LOCAL_SPACE`, which handles rotation modes. The old drivers read `location[n]` as a Single Property; don't copy that.
- **Clamp in the expression:** `clamp(var / E, 0, 1)`, or `1 - clamp(var / E, 0, 1)` inverted. (Superseded the mix formula `clamp(V * var / E, -V * reverse, V * limit)`; `limit` and `reverse` in Limits and extrapolation are now open questions under the connect model.) The slider range isn't enough: it doesn't stop at `V` for partial values, and doesn't stop at 0 on keys like `Pupil.L`. `clamp` and `min`/`max` are simple expressions, so they don't need Python auto-run (tested, see Tested behaviour).
- **Reading the control:** `matrix_basis`, as in `capture_corrective_pose`, and largest channel wins. Open: if a control has both location and rotation posed, either report an error or prefer location. Start with the error.
- **No stored records.** Same as correctives; the drivers hold everything. Recognize our drivers by variable name (`capture_0`, `capture_1`, ...).
- **Custom drivers are left alone.** A driver with any other variable name is hand-written: skip it and report it. Kendra's old rig had 8 of these, such as the lower lid follow and `Eye.Smile`'s `min(a, b)`.
- **Second bone adds a term.** Capturing a key we already drive from a *different* bone adds a variable: `clamp(capture_0 / E0 + capture_1 / E1, 0, V)`. This covers the old master + individual setups. The same bone and channel replaces its term.
- **Mirroring:** same rules as correctives, location X flips, rotation Y and Z flip, assuming symmetric rest rolls. `flip_side_name` works on key names as well as bones, since `.L` and `.R` match its pattern. Old rig agrees: `Mouth.Wide.R` is `-var`, `Mouth.Smile.R` is `+var`.

### Easing (decided: optional, hidden, linear by default)
The jaw has always felt too snappy; it should spend more time barely open. Easing goes on the driver's own F-curve: the expression still normalizes and clamps, and the curve's keyframes reshape 0 to 1. No keyframes means linear, as now. Tested: an ease-in curve on `Mouth.Open` gave 0.03 at a quarter open, 0.16 at half and 1.0 at full, with constant extrapolation holding it at 1.0 past the extreme. The expression stays simple. Editing the curve can be left to the Graph Editor; the panel only needs a way to add one and jump to it.

### Channel layer (dropped and removed 2026-11-08: see Connect redesign)
Controls drive named channels (custom properties on the property bone), and channels drive keys: `control > channel > key`. Every input (face bone, slider, Rig UI property, emote, later mocap) writes to a channel the same way. The user wants to try it in practice on a real rig before deciding; a toy demo didn't settle anything.
- Tested: both layers are simple expressions and evaluate in one update.
- **A driven channel can't be keyframed.** Keying `smile.L` at 0.8 gave 0, because the driver overwrites it. If channels must also take animation or mocap, the channel driver needs a separate animatable input added to it (untested).

### Limits and extrapolation
Same concept in both tools (what happens past the captured extreme), but different mechanisms.

**Shape keys, proposed:** one `limit` custom property on each control, default 1.0. It's set after creation, and tweaks live because the drivers read it:
- The driver caps at `V * limit`, so 1.2 allows a little overshoot and a large value acts like extrapolate. No separate extrapolate setting.
- The key's `slider_max` has to rise with it, or Blender stops the key at 1.0. The tool sets this.
- Bone limits follow through a driver on the Limit Location's max or min, `E * limit`.

Tested: at 1.5x past the extreme, the key stopped at 1.0 with `slider_max` 1, and at 1.2 with `slider_max` 1.5. Changing `limit` updated the key and the constraint's `max_y`. No cycles, and the expression stays simple.

**Locking (user's example).** The mouth corner connects three keys: side out to `Mouth.Wide`, up to `Mouth.Smile`, down to `Mouth.Frown`. Side in and towards/away have no key, so they should be locked. "Locked" means per side, not per axis: X is free outward and stopped at rest inward. User's two options: a final "lock all unused axes" button, or lock by default with a quick button to disable the limit while setting up a new connection, after which it locks again including the new side. Proposed: the second. Every side is always either at its connected extreme or at 0, so the rig is never left half set up, and the toggle replaces Lift Limits. Mechanism: one Limit Location per control, rewritten on each connect; the toggle mutes it.

**Negative is a post-connection tweak (user),** like the limits, not part of connecting. `Mouth.Smile` could go negative when the corner moves down. It stacks with `Mouth.Frown` on the same side rather than conflicting.

Earlier proposal (before connect): a key can run negative when the control moves the other way. The common case is an eyelid key run in reverse to widen the eye; Kendra's `Pupil` keys have a -1 to 1 range too. `reverse` sets how far, and defaults to 0.
- **It has to be per key, not per control.** The same control can use up for smile and down for frown, and smile must not go negative. So `reverse` is written as a number in that key's expression and edited from the key's row in the panel, not stored as a bone property.
- The key's `slider_min` has to go down with it. The tool sets this. Tested: with `slider_min` 0 the key stopped at 0, and with -1 it went to the -0.3 set in the expression, and the mesh moved past its rest shape.
- The bone limit on that side becomes `E * reverse`.
- **One key can use both.** An eyelid key with `reverse` 0.3 and `limit` 1.2 runs from -0.3 (wide) to 1.2 (overshoot), with the tool setting both slider ends. Each end was tested on its own, not yet both on one key.
- **A side with nothing captured stays unlimited.** Otherwise capturing smile would stop the bone at rest, and it could never be posed down to capture frown.
- **Recapturing further out:** solved by the mute toggle on the Connections row (built).

**Correctives, decided:** add `use_motion_extrapolate` to the panel. Tested: it removes the clamp in **both** directions. With a correction of 0.1 at rotation 1.0, a rotation of 1.5 gives 0.15, but a rotation of -0.5 gives -0.05. So a corrective moves the wrong way when the joint bends backward, and the tooltip should say so.

**Correctives at 1.2, open:** multiply the From and Move values by the same number. The slope stays the same, the cap rises, and the negative side stays clamped. This already works by hand in the panel, so it may not need a tool.

### Open design questions (side topics)
- **Eyelids only open and close.** Kendra's lids had no tilt and it felt off. Options: a lid deform bone rotating around the eye's center, layered on the blink key (no new tool needed, can be tried on Kendra now); or inner and outer lid keys connected to a second axis of the lid control.
- **Mouth scale.** Possibly right with four directions: X down/up, Z down/up. Alternative: a flat control in a frame where X is narrow/wide and Z squash/stretch, which is plain location connects. Or sliders.
- **Leftover split falloff settings (deferred).** Split stores each source's falloff as an ID property `split_falloff:<name>` on the Key (shape keys can't hold custom properties). It's keyed by name, so renaming or deleting the source leaves it behind, and a renamed source silently goes back to the default 0.002. Options, either or both:
  - Carry the property over when a key is renamed from our list, and delete it in our Remove. Blender's own delete in the ▾ menu would still leave one behind.
  - A data check over the rig's meshes: INFO "falloff setting for missing key", with a fix that deletes it. It fits the `Issue` / `fix_id` pattern in `data_viewer/checks.py`, about 25 lines.

### Symmetric key sets
A set is a source key plus its sides: `Mouth.Smile`, `Mouth.Smile.L`, `Mouth.Smile.R`.

**Decided flow:** build the full-face key with mirror on, then split it. To change a shape, edit the full-face key and click Update. This replaces about six manual steps each time. Both sides regenerate as real shape data: `side = Basis + (source - Basis) * side weight`. The result doesn't depend on any vertex group, so deleting one can't break a key.

**Proposed details:**
- **The weight:** a smooth ramp across X with a small width, where the left and right weights always add up to 1, so `.L` + `.R` at full strength equals the full-face key exactly.
- **Falloff width:** a setting with a tiny default, in case a shape creases at the center.
- **Update keeps drivers.** It only writes coordinates, so captured drivers on the sides survive. If `.L` or `.R` doesn't exist yet, it creates them.
- **Mirror Side:** superseded by Mirror Shape Key (built 2026-11-09, see "Sculpting one side").
- **Test first:** writing key coordinates from pose mode, without entering the mesh.

Things Kendra's keys show the tool has to handle:
- **Direction keys mirror to a different name.** `Eye.Left.L` (22.6mm) mirrors to `Eye.Right.R` (22.6mm), and `Eye.Left.R` to `Eye.Right.L`, not to `Eye.Left.R`. The same goes for `Mouth.Left`/`Mouth.Right` and `Jaw.Left`/`Jaw.Right`.
- **Some keys cross the center.** `Mouth.Wide.L` moves 9.4mm on its own side and 5.4mm on the other, and `Lip.Lower.Down.L` 4.0mm and 0.3mm. These can't be regenerated with a hard split.
- Her mesh is exactly symmetrical: every vertex has a mirror at distance 0 after rounding to 5 decimals. Other users' meshes may not be, so report vertices with no match.

**Sculpting one side (decided 2026-11-09: Mirror).** The full-face-then-split flow is indirect in practice: sculpting on the posed (deformed) mesh doesn't work with symmetry, so the user kept switching to rest pose, turning on the full-face key and copying it to view it. They also edited a `.L` key directly by accident, which Update from the full-face key would overwrite.

**Mirror Shape Key:** sculpt one side in pose with no symmetry, then copy it onto the mirror key. For each vertex `v` of the target: `target(v) = basis(v) + flip_x(source(m) - basis(m))`, where `m` is `v`'s mirror vertex.
- **Doesn't touch the full-face key**, so nothing is re-split. (Rejected: "Mirror from .L", which rebuilt the full-face key and re-split, reshaping the falloff zone a little every time.)
- **The center line holds.** Split's smoothstep is symmetric (`1 - s(x) = s(-x)`), so mirroring a split `.L` gives exactly the `.R` that Update would. Center vertices edited directly on a side double up with both sides on; the user doesn't see that as a problem (they see the result with both on), so no warning and no re-weighting.
- **Target name:** flip the side suffix and any `Left`/`Right` word: `Eye.Left.L` to `Eye.Right.R`, and keys with no side too, `Mouth.Left` to `Mouth.Right` (whole-mesh mirror). A key with no mirror name (`Mouth.Smile`) has no Mirror.
- **Either direction:** acts on the active key and writes its mirror. Created if missing (relative key, slider range copied, placed beside the source); if it exists, only coordinates are written, so its drivers and settings survive.
- **Mirror pairs** from the Basis with a KD-tree and a small tolerance. Vertices with no match are left alone and reported.
- **Vertex group:** the source's group is treated as applied (see Decided).
- **Full-face keys stay optional.** The tool never deletes them. Once sides are mirrored, the full-face key is stale; Update L/R would overwrite the sides.

- **Locking is Blender's own `lock_shape` (decided 2026-11-09),** exposed as a toggle in each list row; users manage their own protection. Every tool that writes key coordinates (Split, Mirror, Reverse, Apply Vertex Group) refuses a locked target. Rejected: an Update guard comparing `.L + .R` to the full-face key.

Proposed, not decided:
- **Refusals (built):** the Basis, no mirror name, a locked target. Allowed: driven source or target (only coordinates change), split sources (`Eye.Left` to `Eye.Right` is a valid full-face mirror), whole-word Left/Right names without a side suffix.

### Emotes and sliders
Two independent choices: what reads the input, and what gets driven.

| Input | Output: shape key | Output: bone moves |
|---|---|---|
| Bone location (control, slider bone) | Capture, step 1 | New; correctives only read rotation |
| Bone rotation | Capture, step 1 | Correctives today |
| Custom property (Rig UI) | New | New |

- **Blush:** shape key only, driven by a slider.
- **Emotes:** live inside the head and move out with a slider. May also have a bone so they can be moved around once out. The slider can be a Rig UI custom property or a bone on the rig, chosen per emote; the user expects to favor the Rig UI for these.

**Emote setup: reversed (the user's idea, decided).** The emote's rest position is out and visible, where it's easy to place, and "off" is the captured extreme:
```
parent bone
|-- MCH-EMOTE-name    channels driven by the slider; the user never touches it
    |-- emote control    free for the animator to move; stays clean
```
1. Place the emote outside the head and weight it. That's its rest position, and "on".
2. Set the slider to its "on" extreme.
3. Pose the emote control into the head and scale it down. That's "off".
4. Capture. The tool inserts the MCH, moves the control's pose onto it as driven channels, and clears the control.

Every channel uses the same reversed amount, with `on = clamp(var / E, 0, 1)`:
```
location: (1 - on) * L
scale:    1 + (1 - on) * (S - 1)
```
The slider at rest gives `on = 0`, so **emotes are hidden by default in the pose, but visible in Rest Position** for placing and weighting. The Transformation constraint that correctives use can't read a custom property, which is why this uses drivers.

Tested in a throwaway scene, with both a bone slider and a custom property:
- No cycles. Each driver is a simple expression.
- On leaves the emote exactly at its rest position.
- **If the animator moves the emote, off still pulls it back in**, because the MCH's scale collapses the control's offset. On brings it back to where the animator left it.
- Scaling to exactly 0 and to 0.001 gave the same result. Not tested: constraints on bones under the emote, where a zero scale could misbehave.

**Shape keys reverse the same way.** Sculpt the key as the off state, and capture with an invert option: `V * (1 - on)`. Kendra's `Blush.Off` (`1 - var * 6.67`) already works like this.

Open questions:
- **Rig UI placement.** The Rig Properties panel groups properties by the assemblies of the selected bones. Emotes have no assembly, and shouldn't depend on selection, so they need their own always-visible section. It has to work in the embedded script too, without RigTools.

### Pinned controls
A control that follows the mesh is two bones plus a vertex group:
```
face.root (non-deform, child of the bone the user picks, e.g. ORG-head)
|-- VIS-brow.L   Copy Location from mesh group ANCHOR-brow.L
|-- brow.L       the control; custom shape override points at VIS-brow.L
```
The operator can't assume any bone names, so the user chooses the parent. The control sits at rest and only its widget follows the mesh. Two rules keep this free of cycles:
1. **The anchor group never shares a bone's name.** An armature modifier depends on every bone with a matching vertex group, even non-deforming ones. This was the source of all 14 cycles on the old rig.
2. **Nothing depends on a VIS bone.** No children, and no other bone reads it. Parenting the control under VIS is a real cycle and the follow breaks.

Bone envelopes on the armature modifier must stay off, since they make the modifier depend on the whole pose.

Check while testing: VIS reads the mesh's final evaluated geometry, after Kendra's `_Mask` modifiers. Make sure anchor vertices aren't masked away.

### Tested behaviour (Blender 5.2, throwaway scenes)
| Setup | Cycle? | Follow works? |
|---|---|---|
| Anchor group shares VIS bone name | Yes | Yes |
| Renamed group, control under head | No | Yes |
| Renamed group, widget override to VIS | No | Yes |
| Renamed group, control child of VIS | **Yes** | **No** |
| Renamed group, envelopes on | Yes | Yes |
| Renamed group, control also deforms the mesh | No | Yes |

- Renaming groups and constraint targets on an in-memory load of old `Kendra.blend` took it from 14 cycles to 0.
- `var*100` / `-var*100` on 0-to-1 keys: each direction drives only its own key.
- `clamp(0.4*var/0.02, 0, 0.4)`: 0.2 at half, 0.4 at full, 0.4 past the extreme, 0 the other way. Reported as a simple expression.

## Build steps
Proposed order, not decided:
1. **Capture.** Pose mode key panel (per object, collapsible, pick or mix), jump to edit, the operator, mirroring, and adding a second bone as a term.
2. **Symmetric key sets.** Split and Update from a full-face source, the calculated weight, and the name swaps for direction keys.
3. **Editing.** Adjust and delete in the panel. Data Viewer sub-panel and checks: dead drivers, and anchor name collisions.
4. **Sliders, properties and emotes.** Custom property as an input, a location-driven bone as an output (also a real jaw bone), and the Rig UI section.
5. **Pinned control creator.** Select vertices on the mesh, run it, and it makes the anchor group, VIS bone, control, widget and collection.
6. **Frames and the matrix.** A frame is a bone with the rectangle widget, sized from captured extremes using custom shape scale so no new mesh is needed.
7. **Corner capture.** A pose using two axes writes `min(a, b)`.

## Code locations
- Corrective bones to model this on: `rigtools/operators/corrective_bones.py`. Capture at `capture_corrective_pose` (line 89), mirroring at `mirror_from` (line 146), rotation-only input at line 190.
- Corrective Extrapolate: the panel row goes in `draw_constraint` in `rigtools/panels/assembly/corrective_subpanel.py`. The Mirror operator rebuilds the constraint and copies influence (`corrective_bones.py` line 375), so it has to copy this too.
- Read-back helpers pattern: `rigtools/rig_data/correctives.py`.
- Side names: `flip_side_name` in `rigtools/rig_ui/rig_ui.py` (line 92).
- Bone templates: `BONE` in `rigtools/utils/naming.py`. `"vis"` is at line 27. Add the anchor group template here.
- Widgets: `apply_widget` (line 213) and `widget_scale_xyz` (line 53) in `rigtools/utils/widget.py`.
- Tools panel, "Pose Tools:" section: `rigtools/panels/main/main_panel.py` (line 29).
- Rig UI properties: `RIG_PT_properties_ui` in `rigtools/rig_ui/rig_ui.py` (line 322). Properties live on the property bone; see `ToolProperty` in `rigtools/assemblies/tool_data/tool_properties.py` (line 5).
- Registration: `rigtools/__init__.py` (lines 28, 77, 98).
- Data Viewer: `rigtools/data_viewer/checks.py`, and the Correctives sub-panel at `rigtools/data_viewer/panel.py` (line 471).

## Old driver reference
All 50 from the old `Kendra.blend` rig, kept as test cases and for travel distances. `n` in `bone[n]` is the location channel unless noted. A multiplier of 100 means full strength at 1cm. The old bones no longer exist, so names are only a guide.

**Single control (32).** Capture should reproduce these directly.
| Keys | Bone and channel | Expression |
|---|---|---|
| `Mouth.Open` | `SK-jaw[2]` | `var * -100` |
| `Jaw.Left` / `Jaw.Right` | `SK-jaw[0]` | `var * -100` / `var * 100` |
| `Mouth.Wide.L` / `.R` | `SK-mouth_corner.L[0]` / `.R[0]` | `var * 100` / `-var * 100` |
| `Mouth.Smile.L` / `.R` | `SK-mouth_corner.L[1]` / `.R[1]` | `var * 100` |
| `Mouth.Frown.L` / `.R` | `SK-mouth_corner.L[1]` / `.R[1]` | `-var * 100` |
| `Lip.Upper.Up.L` / `.R` | `SK-upper_lip_up.L[1]` / `.R[1]` | `var * 200` |
| `Lip.Lower.Down.L` / `.R` | `SK-lower_lip_down.L[1]` / `.R[1]` | `var * 200` |
| `Lip.Upper.In` | `SK-upper_lip_in[2]` | `-var * 200` |
| `Lip.Lower.In` | `SK-lower_lip_in[2]` | `var * 200` |
| `Mouth.Left` / `Mouth.Right` | `SK-mouth[0]` | `-var * 50` / `var * 50` |
| `Mouth.Up` / `Mouth.Down` | `SK-mouth[1]` | `var * 50` / `-var * 50` |
| `Cheek.Puff.L` / `.R` | `SK-cheek_puff.L[1]` / `.R[1]` | `var * 100` |
| `Brow.Up.L` / `.R` | `SK_brow.L[1]` / `.R[1]` | `var * 100` |
| `Brow.Down.L` / `.R` | `SK_brow.L[1]` / `.R[1]` | `-var * 100` |
| `Brow.Inner.Up.L` / `.R` | `SK-inner_brow.L[1]` / `.R[1]` | `var * 100` |
| `Brow.Inner.Down.L` / `.R` | `SK-inner_brow.L[1]` / `.R[1]` | `-var * 100` |
| `Brow.Squeeze` | `SK-brow_squeeze[1]` | `var * -50` |
| `Eyelid.Upper.L` / `.R` | `SK_eyelid.L[1]` / `.R[1]` | `var * -30` |

**Additive (10).** Captured from two bones, as a second term.
| Keys | Bones and channel | Expression |
|---|---|---|
| `Eye.Left.L` / `.R` | `eye.L[0]` / `eye.R[0]` + `eye.master[0]` | `(master + location) * 20` |
| `Eye.Right.L` / `.R` | `eye.L[0]` / `eye.R[0]` + `eye.master[0]` | `-(master + location) * 20` |
| `Eye.Up.L` / `.R` | `eye.L[2]` / `eye.R[2]` + `eye.master[2]` | `-(master + location) * 20` |
| `Eye.Down.L` / `.R` | `eye.L[2]` / `eye.R[2]` + `eye.master[2]` | `(master + location) * 20` |
| `Pupil.L` / `.R` | `CTRL_Dilate.L[0]` / `.R[0]` + `CTRL_Dilate[0]` | `master * 13.4 + location * 20` |

**Custom (8).** Hand-written; the tool has to leave these alone.
| Keys | Bones and channel | Expression |
|---|---|---|
| `Eye.Highlight.L` / `.R` | `CTRL_Highlight.L[0]` / `.R[0]` + `CTRL_Highlight[0]` | `-pow(master * 6.7, 3) - pow(location * 10, 3)` |
| `Eyelid.Lower.L` / `.R` | `SK_eyelid.L[1]` / `.R[1]`, `SK_squint.L[1]` / `.R[1]` | `var * -30 + lower * 40` |
| `Eye.Smile.L` / `.R` | `SK_eyelid.L[1]` / `.R[1]`, `SK_squint.L[1]` / `.R[1]` | `min(var * -30, lower * 40)` |
| `Mouth.Narrow` | `SK-mouth` scale[0] | `2 - abs(var * 2)` |
| `Blush.Off` | `CTRL_Blush[0]` | `1 - var * 6.67` |

Replace `Mouth.Narrow`'s scale gesture rather than rebuilding it: thinning the mouth by scaling didn't feel right. Use a direction on the mouth control or the matrix's wide/pucker axis.
