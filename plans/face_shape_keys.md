# Face rig: shape key capture

## Next steps (start here)
Only the items under "Decided" are the user's decisions; everything under "Proposed" is still open. These are general add-on tools for anyone building a face rig; nothing here edits a specific rig. Kendra is only the test case: `Z:\Data\Blender\Kendra\Kendra-Character1.blend` (RigTools rig `Armature`, 1519 bones, no face controls).

**Status (2026-11-11): everything below marked built is committed.** Connect redesign `2b21dba`; Mirror Shape Key and lock checks `ac019a5`; Range on the bone and copied/stale record repair `066d0ac`; rotation connections and Symmetrize Connections `c9b5c97`; Lock Unused `b439aea`. Range with several keys per side and several bones per key, and Lock Unused, are tested headless; not yet confirmed in the UI. **Key curve presets work in the UI (user, 2026-11-11), not committed;** left: Symmetrize copying the curve (see "Key curve presets" under Easing). **Next after that:** Pin to Mesh (the user's pick, 2026-11-11; see "Pinned controls"), then the tidy bug (below), the Remove button, the Data Viewer checks.

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
- **Key driver** (`build_key_drivers`), rewritten from the records on every Connect and Disconnect: per bone, `capture_n` (Transform Channel, `LOCAL_SPACE`, location axis) and `extent_n` (the side's `SK` property); expression `max(capture_0 / extent_0, capture_1 / extent_1, 0)`, `-capture_n` on a negative side. No upper clamp: the key's own Range Max caps it. Removed (key set to 0) when no records are left.
- **Limits** (`update_limits`, `_build_limit_driver`; **replaced 2026-11-09**, this bullet describes the old version: see "Range and locks on the bone"): one "Shape Key Limits" Limit Location per control (local space, Affect Transform). Each connected side's field is driven by `extent * max(range_max_0, ..., 1)`, the Range Max (`slider_max`) of every key connected on that side. A key's Range Max of 1.2 lets the bone travel 20% past the extent and the key reach 1.2 (overshoot), with no lag. Unconnected sides are free; no connections removes the constraint. The Limited/Unlocked toggle mutes it; Connect turns it back on.
- **Extent slider:** a get/set `FloatProperty` on `PoseBone` (`rigtools_drive_pos_z` etc.) that writes `SK ±Axis` and moves the bone to that extent. Nothing saved. **The user dislikes this complexity and wants it scaled back later.**
- **Capture:** `matrix_basis` location, largest axis; rotated, scaled or unposed is refused.
- **Checks:** not the Basis, not a split source, mesh deformed by the armature, control isn't the property bone, not an assembly mechanism bone, not DEF-named. A key driver with no records behind it is someone else's: refused.
- **Disconnect:** takes bone, mesh, key and side; removes the record, updates the limits, rebuilds the key's driver.
- **Split sources can't be connected, and driven keys can't be split.**
- **Naming:** `armature_obj`, never `rig`; operator properties are `armature_name`.

**Lock checks built (2026-11-09)** with `is_locked` in `shape_key_utils.py`: Mirror refuses a locked target; Split skips a locked side and updates the other (user's choice), refusing only when both are locked; Reverse refuses if the key or the Basis is locked (other keys' locks don't matter, what they do is unchanged); Apply Vertex Group refuses a locked key.

**Range on the bone is built (2026-11-09, Claude; `066d0ac`);** fixes the dependency cycle. Tested headless: no cycles, all drivers simple, multiple keys per side and bones per key. **Lock Unused is built (2026-11-10, Claude; `b439aea`):** one setting per bone, not lock rows. See "Range and locks on the bone" below.

**Still to do for Connect:**
- **Bug: tidy only covers the operated bone (found 2026-11-11, not fixed).** `tidy_connections` runs on the bone being operated on, but `build_key_drivers` finds records by the key's current name. If bones A and B drive a key that was renamed, Connect on A renames A's record only; the rebuild leaves B's term out (B's record still has the old name), and B's record is then DEAD and deleted on its next operation. B's connection is silently lost. Fix: tidy every bone driving the key (or the whole rig) before looking up records.
- **Key curve presets (built 2026-11-11 by the user, works in the UI, not committed):** Symmetrize copying the curve is left; see "Key curve presets" under Easing.
- **Remove button:** the ✕ in each list row reads as text unembossed and looks poor embossed. Proposed: a − button in a column beside the list (Blender's convention), acting on the selected row; room there later for "select this key".
- **Repair:** built with copy detection (2026-11-09, Claude; not committed), see "Copied and stale records" below. Left: the Data Viewer check and cleanup.
- **MIN** per key.
- **Followers** (proposed 2026-11-13): bones that follow a control, e.g. teeth and tongue on a hinge following the chin. See "Followers".
- **Rotation connections (built 2026-11-09, Claude; `c9b5c97`).** Needed for lip curl and the anime mouth rotate. The user's chibi rig (`\\Jefe\Ubertaco\Data\Blender\Chibii\Chibit2.blend`) had `mouth.move` driving Left/Right/Up/Down on location and `Mouth.Rotate.L/.R` on ROT_Y (0.5 rad) with Limit Rotation ±30°, so one bone drives both channels. As built: records have `channel` (`LOC`/`ROT`, default `LOC`, no migration); rotation sides are `SK ±RX/RY/RZ` (+ Min/Max), radians shown in degrees, capped at 179°; capture reads swing/twist around Y exactly as the driver does (`read_turns`: the twist angle, and the swing as `2·asin` of its components, tested against Blender's own, which isn't axis × angle) and refuses a bone both moved and turned; value variables are `ROT_n` with `SWING_TWIST_Y`; a second constraint, "Shape Key Rotation Limits" (Limit Rotation, local, non-legacy, Affect Transform), driven like location and capped short of a half turn, free sides at ±180° (Limit Rotation has one switch per axis); the Limited toggle is a get/set `rigtools_limits_enabled` covering both constraints; the Extent slider turns the bone on rotation sides; Symmetrize flips rotation Y and Z (X keeps its sign), Blender's flip-pose rule. Known approximation: Limit Rotation clamps Euler angles while the driver reads swing/twist, so a pose on two axes at once reads slightly under (0.9989 at the captured pose for an X swing with a 0.05 twist; 1.0 with the limits off). Tested headless: three channels on one bone, motion and limits, Max overshoot, the moved-and-turned refusal, capture matching the driver, the slider, the toggle, mirrored tails for RX, RY and RZ, and the earlier range, symmetrize and copy tests unchanged.
- **Pinned control operators:** Pin to Mesh is next (decided 2026-11-11, see "Pin to Mesh" under "Pinned controls"). Later: symmetrize (including a mirrored anchor group; check what Blender's Symmetrize does with a vertex group subtarget), delete (with clearing connections). See "Pinned controls".
- **Range Min below 0:** now part of Range on the bone (below).
- **Limited/Unlocked toggle:** kept (decided 2026-11-09). Needed to pose past the limits for a new connection; Connect and Lock Unused turn it back on, and the Data Viewer check reports it muted.
- **Kendra's data** (old channel-layer leftovers, broken L/R keys): the user fixes it by hand while testing; not tool work unless they ask.
- **Mirroring connections:** decided and built as Symmetrize Connections (2026-11-09), see below.
- Deferred: leftover split falloff settings (see Open design questions).

### Range and locks on the bone (decided 2026-11-09; Range built, locks not)
**The cycle (found on Kendra, confirmed headless):** the limit driver reads the key's `slider_max`, and the key's value driver reads the bone. Blender evaluates a shape key's settings and its value driver as one node (`PARAMETERS_EVAL(<key>)`), so reading `slider_max` waits on the value driver, which waits on the bone: bone → constraint → limit driver → key → value driver → bone. It already lagged one update in the built version (half extent gave 0, not 0.5). Reading the bone's location before constraints (`TRANSFORM_SPACE`) or the raw `location[n]` still cycles: the constraint's driver feeds the bone's local transform. **Rule: nothing on the bone may read the Key.** Custom properties on the bone are safe to read from anywhere: nothing computes them (the extent already works that way).

**Rejected:** a message-bus subscription baking Range into the limit as a number. Not live through drivers alone; the user wants the numbers easy to adjust in one place with everything following.

**Decided:**
- **Range lives on the bone, per side,** next to the extent: `SK +Z` (extent), `SK +Z Min` (default 0), `SK +Z Max` (default 1). Created on Connect only if missing (reconnecting keeps the range), removed with the side's last connection. Edited in the bone view, where Range is now.
- **Per side, not per key** (user accepted): every key on a side shares its Max. The old limit already took the largest Range Max on the side, so the limit is the same; what's lost is a lower cap for one key on a shared side. A per-key cap can't be driven without a loop, and per-connection properties named after keys break on rename (the channel layer's problem).
- **Key range is driven from the bones:** `slider_max = max(Max of every bone and side driving the key)`, `slider_min = min(Min of ...)`. Built from `find_bone_connections_for_shape_key`, like the value driver, on every Connect and Disconnect; removed (values kept) when the key has no connections. The key's own Range fields show as driven.
- **Value driver drops its 0 floor:** `max(capture_0 / extent_0, ...)`, one term written bare (Python's `max` needs two). Blender clamps to the key's range, so Min 0 behaves as now and Min −0.3 lets the key go negative with no other change.
- **Limits:** per bone and per side, reading only that bone's properties. A limited side's field is `max(extent * Max, opposite extent * -opposite Min, 0)`: its own reach, or the opposite side's backward reach for negative values, whichever is further. Keys clamp themselves, so one side going negative while the other drives a key positive needs no special case (Min defaults to 0, so it's opt-in).
- **Which sides are limited:** connected sides, plus every other side when Lock Unused is on. Unconnected sides on an unlocked bone stay free, whatever the opposite side's Min. No driver on the `use_` switches.
- **Lock Unused (decided and built 2026-11-10, Claude; not committed):** a saved setting on the bone, `rigtools_lock_unused`, off by default, set by the `rig.lock_unused_sides` operator: a "Lock Unused Sides" button under the connection list, which becomes an "Unused sides locked" line with an ✕ to undo (user, 2026-11-10: it's setup, an operation, not a mode; Limited stays the temporary toggle in the header). Lock rows in the list were dropped: with rotation there are 12 sides, so a one-key bone would show 11 lock rows. On, every side with no connection, location and rotation, is held at rest: a locked side's field is 0, or `max(opposite extent * -opposite Min, 0)` when the opposite side is connected, so negative Min still works. Both constraints exist while it's on, even for a channel with no connections (a location-only bone gets a Limit Rotation at 0; clamping to 0 is exact, no Euler approximation). The Limited toggle mutes both, so posing past the lock for a new connection works as before. Turning it on also turns Limited on. A bone with no connections left isn't locked (constraints removed). Symmetrize copies it. Trade-off accepted: no freeing a single side. Scale isn't covered (Blender's `lock_scale` would be the tool). Tested headless: locks location and rotation, Min reach, Limited off, Connect on a locked side, Symmetrize, turning it off, disconnecting everything; earlier tests unchanged.
- **Data Viewer check, "Shape key controls not locked":** per control, muted limits and free sides (`brow.L: free sides +X, ±Y`); fix unmutes and locks unused sides. The reminder for "done"; nothing locks automatically.
- **Existing connections aren't migrated:** Connect or Disconnect on a bone rebuilds it in the new form.

**Testing note:** setting a bone's custom property from Python doesn't tag the depsgraph, so drivers reading it don't re-run until something else changes; UI edits do tag. Headless tests must call `armature_obj.update_tag()` after setting one.

**As built:** `build_key_drivers` builds `_build_range_drivers` (slider_max = `max(max_n)`, slider_min = `min(min_n)`) then `_build_value_driver`; one term is written bare (`_combine`). Range properties get UI limits Min in [-10, 0], Max in [0, 10].

**Decided (2026-11-10):** Lock Unused locks every unused side, all 12.

**Code changes** (`connect.py` unless noted): `range_name(axis, positive, end)` beside `side_name`; Connect creates Min/Max if missing; `update_limits` deletes them with the side `_build_limit_driver` drops the Key variables and `side_connections`, reads extent/Max and the opposite extent/Min; new `_build_range_drivers` beside `build_key_drivers`; value expression without the floor; bone view draws the side's Min/Max instead of the key's `slider_min`/`slider_max`, and the Lock Unused Sides button; docstrings.

### Symmetrize Connections (decided and built 2026-11-09, Claude; `c9b5c97`)
Makes each selected bone's mirror an exact copy of its connections, flipped. Records and bone properties are written, then the same `update_limits` and `build_key_drivers` as Connect rebuild everything.

**Decided:**
- **Bones follow bone rules:** the mirror is `flip_side_name`, the same as the corrective Mirror. No Left/Right swapping in bone names. **Bones with no side have no mirror** (a jaw driving `Mouth.Left` and `Mouth.Right` gets two Connects).
- **Keys follow `mirror_shape_key_name`, and location X flips** (Y and Z keep their sign), assuming symmetric rest rolls like `mirror_from` in `corrective_bones.py`. `+X Eye.Left.L` on `Eye.L` mirrors to `-X Eye.Right.R` on `Eye.R`: the X flip is the mirror, and the name flip relabels the key for the motion it now gets. Whole bones keep "+X looks left" on both sides. `Mouth.Wide` shows X must flip (old rig: `Mouth.Wide.R` is `-var`).
- **Replace, like symmetry:** the target's records become the mirrored source's, and connections the source doesn't have are removed (their keys are rebuilt without that bone, set to 0 if undriven). Extent, Min and Max are copied for each side; unused sides lose their properties. Other bones driving the same keys (masters) keep their terms. The target's limits are unmuted and its list takes the source's active row.
- **The selected bones, not just the active one.** If both sides of a pair are selected, a Left to Right / Right to Left option in the redo panel picks the source (default Left to Right). Sources without connections are skipped.
- **All or nothing:** everything is checked first. Any problem refuses the whole thing with the full list: target bone missing or not allowed as a control (Connect's checks), stale source record, key with no mirror name, target key missing or split, target key with a hand-written driver. Missing keys are made with Mirror Shape Key first; Symmetrize never creates keys.
- **Rebuilt once at the end,** after every bone's records are written, since two selected bones can drive one key.
- **Button:** its own row at the top of the panel in pose mode ("Symmetrize Connections"), shown only when a selected bone has connections and a mirror bone. Hidden otherwise; a mirror with problems still shows and refuses with the list. Draw and poll share one helper.
- **Locks** (not built) will mirror the same way once they exist.
- **Widgets: later** (user, 2026-11-09; in `TODO.md`). Built first as its own widget Symmetrize (the Bone Style tool in `TODO.md`, beside "copy all to selected"), then Symmetrize Connections calls that same function on each pair, so the two always mirror the same way. Rules discussed: widget object by flipped name if one exists, else the same one; translation X negated; rotation Y and Z negated; scale, wire width, bone size, show wire copied; override transform by flipped name if it exists; color undecided (maybe a redo-panel checkbox, off). A widget that isn't symmetric across its own X needs its own mirrored object.

**As built** (`symmetrize.py`): `RIG_OT_symmetrize_connections` (`rig.symmetrize_connections`) with a `direction` enum in the redo panel; helpers `mirror_bone`, `mirrored_side`, `can_symmetrize` (panel and poll), `symmetrize_pairs`, `pair_problems`, `mirror_connections`. Connect's pieces were pulled out for it in `connect.py`: `set_side_props` (extent plus Min/Max if missing), `control_problem` (property bone, assembly, DEF name), `has_foreign_driver`; `_build_driver` is now public as `build_key_drivers`. Tested headless (bones made with Armature Symmetrize, rolled): mirrored records and properties, the replaced connection's key undriven and at 0, mirrored world motion, limits, a key shared by two selected bones (two terms on the mirror key), Right to Left with a pair selected, center bone alone hides the button, and the all-or-nothing refusal (no mirror name, missing key, foreign driver).

### Copied and stale records (decided and built 2026-11-09, Claude; `066d0ac`)
**The problem (tested):** Blender's Duplicate and edit mode Symmetrize copy a bone's records (registered PropertyGroups are copied like custom properties), its `SK` properties and the limit constraint, but not the drivers. The copy's records claim keys that don't read it (`brow.R` claimed `Brow.Up.L`, unflipped), and the next rebuild of that key added the copy as a term: raising `brow.R` set `Brow.Up.L` to 1.

**Decided:**
- **A record is live only if its key's value driver reads it:** the `extent_n` variable reading this bone's `SK ±A` names the bone, axis and side at once. Blender updates it on a bone rename and never copies it with a bone, so copies are dead from the start and renames need nothing. No new field, no expression parsing; records still decide what's built.
- **Same check as the key-rename repair, no conflict:** a copy is a different bone, so it can't match a renamed key's driver. Claims count only this bone's own records.
- **Trust the record being written,** not the whole bone (Connect trusts its new record, Symmetrize each target's), or a copy's dead records would come back on a rebuild.
- **Silent:** rebuilds ignore dead records; the first operation on the bone (Connect, Disconnect, Symmetrize) fixes renamed keys, then erases the dead records, and `update_limits` clears their properties. The bone view hides dead records. No note about the copied constraint (user: copying a bone with a constraint is on you).
- **Data Viewer:** reports dead and ambiguous records and cleans up the whole rig (not built).

**As built** (`connect.py`): `connection_status` (LIVE / RENAMED with the new name / AMBIGUOUS / DEAD), `_reads_side`, `has_connections`, `live_connections_for_key`, `record_id` (records by value: items move in memory as the list grows), `tidy_connections`. `build_key_drivers(..., trust)` and `has_foreign_driver` use live records only. Disconnect rebuilds the key under its current name. Symmetrize skips dead source records, refuses ambiguous ones, mirrors renamed ones under their new name. Panel: the bone view's list hides dead records (`filter_items`) and shows renamed keys by their new name, ambiguous with a warning icon; the key's Connections rows list live records; a bone with only dead records shows no bone view and no Symmetrize button. Tested headless: copies after Symmetrize and Duplicate are dead, recapturing no longer pulls in the copy, renaming the original keeps it live, a renamed key is repaired on the next Connect and Disconnect removes its driver, connecting a copy on purpose clears its dead records first.

### Connect redesign (decided and built 2026-11-08)
Started from the user's request for an **extent slider**: change how far a side must move to reach 1 without re-posing. The slider is the critical feature.

**Decisions:**
- **Direct drivers; the channel layer is dropped.** Sharing keys by matching name is an implicit coupling and a *cost* (the teeth's `Mouth.Open` following the face's should be a deliberate connection); a renamed key left a stale `SK-` channel; clutter on the property bone. A direct driver survives a key rename.
- **A real UIList, backed by stored records.** Hand-drawn rows posing as a list are out of the question; listing the rig's drivers through a filter was rejected. The user accepted stored add-on data here as necessary, in its own file (protected-members rule).
- **Repair against the drivers (built 2026-11-09, see "Copied and stale records").** Keys are stored by name, so a rename makes a record stale while the rig keeps working. Repair: when a record's key is missing on its mesh, find the key on that mesh whose driver reads this bone, axis and side, skipping keys claimed by another record, and take its name. No match: remove or flag. Ambiguous: flag. Draw can only show stale records; operators fix them.
- **Range instead of a separate Limit.** (Where Range lives changed 2026-11-09: see "Range and locks on the bone".) The user found "Range 0 to 1.2" far more natural than a limit distance with a link toggle. The key's own Range Max (Blender's field, no new data) drives the bone's limit, rather than the limit driving the key's slider max (tested: that lagged one update). Per key, not per key and bone: every bone driving a key lets it reach its Range Max; the user can't think of a case wanting otherwise.
- **No invert, anywhere.** Keys that are on at rest are fixed at the source with Reverse Shape Key.
- **MAX/MIN is per key.** MAX is the default and stores nothing. MIN (not built) would be a custom property on the mesh's Key, like `split_falloff:<name>`.

**Two separate relationships** (don't conflate them):
1. **One side, several keys.** A side is a bone plus a direction (upper lid −Z). It owns one extent and one range (Min/Max); its limit is the extent times its Max. Every key on the side shares that overshoot. No combining.
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
The jaw has always felt too snappy; it should spend more time barely open. Easing goes on the driver's own F-curve: the expression is unchanged, and the curve's keyframes reshape its result (X = expression result, Y = key value). No keyframes means linear, as now.

### Key curve presets (decided 2026-11-11; built by the user, works in the UI, not committed)
**Decided:**
- **Per key, on the key's value driver F-curve.** Applied after the `max` combines the key's bones. Per connection was considered (easing math in each expression term), but only ease in works cleanly past 1 and below 0 that way.
- **Nothing stored.** The panel reads the keyframes' own fields (`co`, `interpolation`, `easing`) and the F-curve's `extrapolation`. That's reading Blender's typed fields, not parsing the expression, so it's neither fragile nor broken by format changes (the user's two objections to reading drivers). Rebuilds already leave keyframes alone (`_create_new_driver` clears them only on creation). Removing a key's last connection deletes the driver and its curve: accepted, no problem.
- **Presets, not a curve widget.** Blender's curve mapping widget can't be given to a shape key. A dropdown with words, not the brush icon row (those are one-shot resets and show falloff shapes): Linear (no keyframes), Ease In (Quad, Ease In), Ease Out (Quad, Ease Out), Ease In-Out (Sine, Ease In-Out). Each is two keyframes at (0,0) and (1,1) with the same interpolation and easing, and Linear extrapolation. Step dropped (it only snaps at the very end). Anything else shows as "Custom" (hand-edited in the Drivers editor), shown only as a label, never picked.
- **Matching:** no keyframes is Linear (extrapolation ignored); exactly two keyframes at (0,0) and (1,1), Linear extrapolation and the first keyframe's (interpolation, easing) matching a preset is that preset; anything else is Custom. Easing is per segment, stored on the keyframe where it starts, so keyframe 0 holds it.
- **In the bone view,** a "Curve" row under Extent and Range for the selected connection's key. It's the key's setting, so another bone driving the same key shares it.
- **No lock check:** `lock_shape` protects the shape, and the curve isn't shape data.

**Tested headless (Blender 5.2):** with keyframes at (0,0), (1,1) and Linear extrapolation, non-Bezier curves continue at slope 1 past both ends (1.2 gives 1.2, −0.5 gives −0.5), so overshoot and negative Min work as without a curve. Quad Ease In: 0.062 / 0.25 / 0.562 at a quarter, half, three quarters; Quad Ease Out: 0.438 / 0.75 / 0.938; Sine Ease In-Out: 0.146 / 0.5 / 0.854; Cubic Ease In (stronger): 0.016 / 0.125 / 0.422. `UILayout.operator_menu_enum` returns the operator's properties, so the dropdown needs no menu class.

**As built** (`panels/shape_keys/key_curve.py`): `CURVE_PRESETS`, `CURVE_PRESET_ITEMS`, `match_curve_preset`, `apply_curve_preset`, `curve_preset_label` (the preset's name, or "Custom"), `RIG_OT_set_key_curve` (`rig.set_key_curve`; `object_name`, `shape_key_name`, `preset`). `find_driver(anim_owner, path)` lives in `shape_key_utils.py` (public; connect.py uses it too). Review notes applied: `find_driver` gets `key`, `shape_keys` None is guarded, the `description` classmethod is gone. The panel row is at the end of `draw_active_bone` in `shape_keys_panel.py`: split 0.4, a right-aligned "Curve" label, `operator_menu_enum`, shown only when the connection is live and the key has a driver. It goes into `col`, so it sits with Extent and Range, above the separator.

**Registration changed (2026-11-11, the user):** `rigtools/panels/shape_keys/__init__.py` has its own `modules` tuple and `register()`/`unregister()`; the top-level `rigtools/__init__.py` imports the package (`from rigtools.panels import shape_keys`) and registers through its own `modules` tuple, unregistering in strict reverse. A new shape key module goes in the package tuple, before `shape_keys_panel`.

**Left:** Symmetrize copies the keyframes (interpolation, easing, positions, extrapolation) to the mirror key. Small tidy: the continuation line of the `operator_menu_enum` call is indented with spaces, trailing spaces after `return name` in `match_curve_preset`, an extra blank line before `RIG_PT_shape_keys`.

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

#### Pin to Mesh (decided 2026-11-11)
- **Pins an existing bone; it doesn't create one.** Select the control in pose mode and click Pin to Mesh. The operator adds only what pinning needs: the `ANCHOR-{name}` vertex group, `VIS-{name}` (Copy Location to that group), and the control's custom shape override pointing at VIS. The parent, widget and collection are whatever the user gave the bone, and the name comes from the bone.
- **Anchor vertices, chosen in the redo panel** (`REGISTER`, `UNDO`): **Closest** (default) finds the vertices nearest the bone's head, so it all stays in pose mode; **Selection** uses the mesh's stored edit mode selection (`mesh.vertices[i].select`).
- **Copy Location averages a vertex group by weight (tested 2026-11-12, Blender 5.2, headless):** the weighted average divided by the total weight, so weights needn't sum to 1, and weight 0 vertices are ignored. 0.6/0.3/0.1 on a triangle landed exactly on the weighted point, not the plain mean. So Closest can land VIS exactly on the closest surface point.
- **Which mesh (decided 2026-11-12):** candidates are `get_related_meshes` (`rig_ui.py`: parented under the rig or `find_armature()` is the rig, not `rigtools_helper`; no shape keys needed) that are `visible_get()`, so hidden cages and proxies are skipped. `invoke` picks the nearest (world-space distance, so mesh scale doesn't skew it) and stores its name in the `mesh` enum; the redo panel then shows which mesh it picked, and changing it re-runs `execute` only. Selection uses the same mesh, not "whichever mesh has a selection" (every mesh keeps a stale one). No close-call warning: the redo panel showing the pick is enough. The enum's items come from a function, kept in a module-level list (Blender only holds pointers to the strings), with `SKIP_SAVE` (dynamic enums store a position, not a name). Tested headless: nearest picks right with a scaled mesh; setting the dynamic enum in the operator works. Not tested: the redo panel showing the picked name (background mode skips `invoke`).
- **Closest code is written and tested** (`rigtools/operators/pin_to_mesh.py`, the user): `barycentric_weights` (area method, with a collapsed-triangle fallback to the nearest corner) and the closest-point search with `BVHTree` on the original mesh's loop triangles. Landed VIS exactly on Blender's `closest_point_on_mesh` for edge and face hits.
- **Proposed, not decided:**
  - Closest as the surface point: the nearest face's vertices, weighted so their average lands on the closest point.
  - The anchor group template goes in `BONE` in `rigtools/utils/naming.py` next to `"vis"`.
- **Deferred (the user, 2026-11-12; not part of the first pass):** the widget only follows the mesh, so grabbing the control doesn't move it; it moves only as far as the shape key moves the anchor vertices. Fine when the anchor sits on what the key moves (brow on the brow). If not, VIS would also need the control's offset (allowed: VIS may depend on the control, not the reverse), but that doubles the motion on an anchor the key does move.

### Followers (discussed 2026-11-13; proposed, not built)
Bones that follow a face control: the lower teeth and tongue following the jaw, and later controls following controls, DEF/ORG bones following face controls. Fills the "bone location in, bone moves out" cell of the Emotes table.

**The case:** Kendra's mouth opens with `Mouth.Open`, driven by a chin control that only translates (down; also left/right). The lower teeth and tongue must follow, but they swing around a hinge at the back of the throat, not the chin. The old rig did this with an MCH at the tongue base with Transformation constraints (move and rotate) from the jaw control, parent of the teeth and tongue. The upper teeth likely want the same (the anime mouth opens up a little).

**Decided (user):**
- **A tool,** not a one-off: there will be others like it.
- **Follow the control bone,** not the shape key value. (Rejected: drivers reading the key's value. It ties a follower to one key and isn't general.)
- **The user creates the hinge bone and the parenting** (teeth and tongue root under it). The tool only captures the transform. The followers share the hinge as parent, so they move together exactly; nobody poses teeth and tongue separately.
- **A way to hide the hinge in the MCH collection,** since it isn't a true control.
- **Can't assume** the teeth and tongue are separate meshes or part of the face mesh.
- **Discoverability matters:** the worry is that this becomes an invisible tool people never think to use, even if documented.

**Rejected along the way:** the tool creating the hinge at the 3D cursor (it still had to be posed); solving the pivot from the followers' pose (needs both posed by hand, and the solve is fragile at jaw angles of 10–15°); posing the followers together around the cursor.

**Proposed:**
- **Capture:** the corrective gesture with a location input. Pose the control at a side's extreme, pose the follower (the hinge), select the follower with the control active, Add Follower. Adds a Transformation constraint on the follower: from the control's side (0 to extent, local location) to the captured location/rotation, `ADD` mix, then clears the follower's pose. The control stays posed. Another side (chin sideways) is another capture, stacked on the same follower like correctives stack.
- **Range from the extent:** the constraint's "from" end is driven by the side's `SK ±A` property, so changing Extent keeps followers matched. Reads a bone property, not the Key, so no cycle. Extrapolate on, so Range Max overshoot carries through; the control's own limit caps it.
- **Panel:** a Followers section in the control's bone view, under Connections and Extent/Range/Curve, always shown for a connected control even when empty: a UIList (follower, side, ✕) and an Add Follower button whose tooltip explains the gesture. This is the answer to discoverability: the question "what else moves when this moves?" sits where the user just connected the key. General, not jaw-specific.
- **Move to MCH:** a separate button (not automatic, so the hinge can stay visible while tuning), using `ensure_bone_collection(get_preferences().mch_collection_name, hidden=True)` as correctives do.
- **Reuse `CorrectiveSetup`** (`operators/corrective_bones.py`) where it fits: capture, `add_transform`, mirroring, read-back. Correctives read rotation through a reader MCH; a face control's local location is read directly, so no reader.
- **Symmetrize** mirrors followers by the corrective rules.
- **Checks:** same as correctives (no DEF bones, no assembly mechanism bones).

**Known gaps:**
- **Easing:** Transformation constraints are linear. If `Mouth.Open` has Ease In, the teeth drift from the mouth mid-motion and line up only at 0 and 1. Ship linear and see if it's noticeable; a driver-built follow could apply the key's curve.
- **Two sides on one hinge** are each exact at their extreme; combined poses add the two rotations, fine at small angles.
- **ORG followers in an assembly:** reparenting must also update the assembly's saved parent (`org_state.parent`), or regenerating undoes it. Now the user's job (they do the parenting); worth a check or a note.

**Open:** where the follower's side shows on the follower itself ("Follows jaw −Z"); whether Move to MCH also clears `use_deform`; Data Viewer checks for followers.

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
5. **Pin to Mesh.** Select an existing control in pose mode, run it, and it makes the anchor group and VIS bone and sets the widget override (decided 2026-11-11, replaces the creator).
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
- Registration: the `modules` tuple in `rigtools/__init__.py` (line 53); shape key modules go in the `modules` tuple in `rigtools/panels/shape_keys/__init__.py` (line 3).
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
