# Corrective bones

## Next steps (start here)
Feature complete and documented. Built across several "WIP corrective bones" commits.

Built:
- **Create** (`RIG_OT_create_corrective_bone`, `operators/corrective_bones.py`): validation, reader MCH, capture, Transformation constraints, pose cleared. Mirror on by default. Tested on Sarah's arm and shoulders.
- **Delete** and **Mirror** (`RIG_OT_delete_corrective`, `RIG_OT_mirror_corrective`). Tested.
- **Entry points:** Tools panel ("Pose Tools:" section, pose mode only), Pose > Constraints menu, Shift+Alt+C (Pose keymap).
- **Panel:** corrective box at the top of the Assembly panel (`draw_correctives` in `panels/assembly/corrective_subpanel.py`).
- **Assembly validation:** `create_assembly_data` now rejects other assemblies' mechanism bones (`find_assemblies` in place of `check_assembly_use`) and DEF bones by name.
- **Data viewer:** Correctives sub-panel; the orphan MCH check ignores MCHs a corrective reads.
- **Docs:** `docs/correctives.md`, plus `data_viewer.md`, `assemblies.md`, `workflow.md` (new step 8) and the nav. Docs built and checked.

**Resume here:** nothing left. Possible follow-ups: recapture (see Decisions), Swing + Twist rotation mode, an "Include mirror" toggle for slider edits.

How we'll work: the user builds this. Claude explains, reviews and helps on request.

## Context
From the TODO item "Corrective bones?". A corrective bone (or shape key) should react to how one bone is posed relative to its parent, e.g. a shoulder corrective driven by the upper arm.

**The problem:** in a tweak chain, ORG bones are parented to their own tweak (`ORG-forearm` → `tweak-forearm` → `FK-forearm`). The tweak moves with the bone, so the ORG bone has almost no local transform: only the small Stretch To delta. Reading the ORG directly gives nothing useful.

**The core mechanism:** a hidden reader MCH bone, a *sibling* of the target ORG, parented to the target's ORG parent, with Copy Transforms (world) from the target. Its local transform is "target relative to its parent". **The corrective reads the MCH, not the ORG.**

Without assemblies:
```
ORG-arm
├── ORG-forearm          (unchanged)
└── MCH-CORR-forearm     (Copy Transforms from ORG-forearm, world space)
```
With the arm assembly built, ORG-arm moves under tweak-arm and ORG-forearm moves under tweak-forearm. The MCH stays under ORG-arm. Nothing about the assembly or the chain changes. ORG-arm doesn't move when the elbow bends, so the MCH's local rotation is the elbow bend.

## Decisions
- **Always create the MCH**, even when the target already has a Copy Transforms (e.g. ORG-shoulder from FK). A "use it directly" check would only reflect today's assembly; swapping FK-only for a tweak chain later would silently break it. One MCH per target, shared by every corrective on that target. Named from `BONE["corrective"]` (`MCH-CORR-{name}`).
- **MCH parent:** if the target ORG is in an assembly, use its stored rest parent (`find_org_state(...).parent`); otherwise its current direct parent. If an assembly is built afterwards, it never touches the MCH, so it stays correct.
- **MCH is not connected and lives in the hidden MCH collection.** Chain detection (`find_chains_from_selection`) only walks selected children and Select Connected (`find_connected_chains`) skips unconnected or hidden bones, so the MCH never ends up in an assembly selection. The MCH collection assignment is inline in the operator, not shared with `add_bone`; MCH collections have changed twice and centralizing doesn't solve for the next change.
- **Chain ends:** if the MCH's parent is the *last* ORG of a chain, the terminal reparent rule moves it to the term tweak along with the target (e.g. toe under term-foot). That's acceptable: the MCH and the target share a parent, so it still measures the target relative to what it actually follows. Delete moves both back. Only foot tweak stretch is missed; not expected to matter.
- **Target validation:** ORG bones only, to prevent accidents rather than to be exhaustive.
  - Reject any bone in an assembly's `mechanism_bones` (`find_assemblies(..., include_org_states=False)`).
  - Reject DEF bones by name (`does_match_def_name`, using the `def_template` preference). A DEF target would technically work, since DEF follows ORG with Copy Transforms, but using ORG bones keeps things consistent.
  - The error tells the user to use the ORG bone.
- **The corrective is an ORG bone too.** The Transformation constraints go on `ORG-corrective`; `DEF-corrective` follows it with the usual Copy Transforms. Constraints put on a DEF bone directly would be overridden if Generate ORG Bones later added its Copy Transforms. Convention: always work on ORG bones; a DEF bone should have an ORG.
- **Corrective validation:**
  - Reject DEF bones by name, same as the target.
  - Reject any constraint that isn't a Transformation constraint: it's being controlled by another bone, which would interfere. Existing Transformation constraints are fine: that's another corrective stacking on the same bone, possibly from a different target (e.g. a shoulder blade driven by both shoulder and arm).
- **No stored records.** The constraints already hold everything: a corrective is a Transformation constraint whose subtarget starts with the `MCH-CORR-` prefix, and the MCH's Copy Transforms gives the target. Helpers in `rig_data/correctives.py` (`corrective_constraints`, `find_correctives`, `corrective_target`, `correction_end`). The prefix match is reliable enough; a false match only adds an extra row in the panel or data viewer.
- **No recapture.** Adding rotation to a location corrective is just running Create again (only the new output type is captured, since the existing constraint supplies the rest). Fine adjustment is the sliders. Revisit if re-posing to a different extreme after slider edits becomes a real need; level 1 (target angle only) is ~15 lines.
- **Assembly blocking:** done. `create_assembly_data` uses `find_assemblies` (ORG bones and mechanism bones) and rejects DEF bones by name, so assemblies can't be built on another assembly's created bones. Covers the TODO "Disallow working on DEF?". Tested with the usual templates; nothing legitimate is blocked.
- **Generate ORG Bones is safe:** it skips existing ORG bones and never deletes any (`generate_org_bones.py`).

## Create
1. The user poses the target bone to its extreme, ideally on one axis.
2. The user poses the corrective bone (location and/or rotation).
3. The user selects the target ORG, then the corrective bone last (active).
4. Operator (`CorrectiveSetup` per side, two mode switches total):
   - validates both sides, and captures the corrective's pose (`matrix_basis`, so existing correctives aren't included) before changing anything;
   - edit mode: finds or creates each side's MCH;
   - pose mode: adds the MCH's Copy Transforms, reads the source MCH's local rotation (`view_layer.update()` + `convert_space(..., to_space='LOCAL')`) and picks the largest axis. If the target is at rest, removes MCHs created this run and cancels;
   - adds one Transformation constraint per output type actually used (location, rotation). From range is ordered (min < max); a negative reading puts the correction at min. Mix mode Add, so correctives stack. Values go through `clean()` to avoid `-0`;
   - clears the corrective bone's pose.

## Panel
Top of the Assembly panel, only when the active bone is selected and has correctives. One box per constraint:
- the target name, mirror button, delete button;
- **From**: only the end of the range that holds the correction (`correction_end`);
- **Move/Rotate X Y Z**: the to values at that end;
- No Influence slider (tried, removed). Built-in property drag speed can't be changed from Python; Shift while dragging is the fine control.

**Delete** removes the constraint, and the MCH if no other corrective reads it.

## Mirroring
Blender's X-flip rule, assuming symmetric rest rolls (Symmetrize):
- location: negate X
- rotation: negate Y and Z
- input reading: kept for X, negated for Y and Z

Applies to both from and to values (`mirror_from`).
- **On create:** the redo panel's Mirror (default on). A missing mirror (center bone, or no opposite bones) is an INFO note, not an error. A mirror that exists but fails validation is an error.
- **Mirror button:** rebuilds a setup from the constraint (`from_constraint`), then replaces the opposite constraint with the same MCH *and* output type, so mirroring twice doesn't stack. Influence is copied.
- Later, maybe: an "Include mirror" toggle so slider edits apply to both sides.

## Open questions
- ~~**Reading the captured value**~~ Solved: `context.view_layer.update()`, then `obj.convert_space(pose_bone=mch, matrix=mch.matrix, from_space='POSE', to_space='LOCAL')`. That includes constraints; `matrix_basis` doesn't.
- ~~**Record storage**~~ Decided: none (see Decisions).
- ~~**Which axis/sign**~~ Decided: largest absolute value; the sign picks which end of the ordered range holds the correction.
- **Rotation mode:** uses `'AUTO'` (Euler), matching `to_euler()` in the reading. Swing + Twist might avoid Euler flips near 90° (shoulder raises). If tried, change the reading and `from_rotation_mode` together.
- **Reversed ranges:** unverified whether Blender handles from min > max; the ordered range sidesteps it.
