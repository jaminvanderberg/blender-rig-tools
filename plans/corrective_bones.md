# Corrective bones

## Next steps (start here)
`RIG_OT_create_corrective_bone` (`operators/corrective_bones.py`) works end to end, including mirroring. Per-side logic lives in `CorrectiveSetup` (validate, edit_mode, pose_mode, capture, apply, mirror_from). Mirror defaults to on; a missing mirror is a note, not an error. Validation and capture happen before any changes; MCHs created this run are removed if the target is at rest.

**Resume here:**
1. Storage for corrective records (per constraint).
2. Panel for the active corrective bone (sliders, recapture, delete, mirror button).

How we'll work: the user builds this. Claude explains, reviews and helps on request.

## Context
From the TODO item "Corrective bones?". A corrective bone (or shape key) should react to how one bone is posed relative to its parent, e.g. a shoulder corrective driven by the upper arm.

**The problem:** in a tweak chain, ORG bones are parented to their own tweak (`ORG-forearm` → `tweak-forearm` → `FK-forearm`). The tweak moves with the bone, so the ORG bone has almost no local transform: only the small Stretch To delta. Reading the ORG directly gives nothing useful.

**The core mechanism:** a hidden reader MCH bone, a *sibling* of the target ORG, parented to the target's ORG parent, with Copy Transforms (world) from the target. Its local transform is "target relative to its parent". **The corrective reads the MCH, not the ORG.**

Without assemblies:
```
ORG-arm
├── ORG-forearm                (unchanged)
└── MCH-corrective-forearm     (Copy Transforms from ORG-forearm, world space)
```
With the arm assembly built, ORG-arm moves under tweak-arm and ORG-forearm moves under tweak-forearm. The MCH stays under ORG-arm. Nothing about the assembly or the chain changes. ORG-arm doesn't move when the elbow bends, so the MCH's local rotation is the elbow bend.

## Decisions
- **Always create the MCH**, even when the target already has a Copy Transforms (e.g. ORG-shoulder from FK). A "use it directly" check would only reflect today's assembly; swapping FK-only for a tweak chain later would silently break it. One MCH per target, shared by every corrective on that target.
- **MCH parent:** if the target ORG is in an assembly, use its stored rest parent (`org_states[...].parent`); otherwise its current direct parent. If an assembly is built afterwards, it never touches the MCH, so it stays correct.
- **MCH is not connected and lives in a hidden MCH collection.** Chain detection (`find_chains_from_selection`) only walks selected children and Select Connected (`find_connected_chains`) skips unconnected or hidden bones, so the MCH never ends up in an assembly selection.
- **Chain ends:** if the MCH's parent is the *last* ORG of a chain, the terminal reparent rule moves it to the term tweak along with the target (e.g. toe under term-foot). That's acceptable: the MCH and the target share a parent, so it still measures the target relative to what it actually follows. Delete moves both back. Only foot tweak stretch is missed; not expected to matter.
- **Target validation:** ORG bones only, to prevent accidents rather than to be exhaustive.
  - Reject any bone in an assembly's `mechanism_bones` (anything an assembly would delete).
  - Reject DEF bones by name (`def_template`, via `bone_name_matches`). A DEF target would technically work, since DEF follows ORG with Copy Transforms, but using ORG bones keeps things consistent.
  - The error tells the user to use the ORG bone.
- **The corrective is an ORG bone too.** The Transformation constraints go on `ORG-corrective`; `DEF-corrective` follows it with the usual Copy Transforms. Constraints put on a DEF bone directly would be overridden if Generate ORG Bones later added its Copy Transforms. Convention: always work on ORG bones; a DEF bone should have an ORG.
- **Corrective validation:**
  - Reject DEF bones by name, same as the target.
  - Reject any constraint that isn't a Transformation constraint: it's being controlled by another bone, which would interfere. Existing Transformation constraints are fine: that's another corrective stacking on the same bone, possibly from a different target (e.g. a bicep driven by both shoulder and elbow). So records are per constraint, not per bone.
- **Assembly blocking (optional):** `check_assembly_use` only checks `org_states`, so assemblies can currently be built on another assembly's mechanism bones. Adding `mechanism_bones` names there (like `find_assemblies`) is a one-line fix. Not yet decided.
- **Generate ORG Bones is safe:** it skips existing ORG bones and never deletes any (`generate_org_bones.py`).

## Workflow
1. The user poses the target bone to its extreme, ideally on one axis.
2. The user poses the corrective bone however they like (location and/or rotation).
3. The user selects the target ORG, then the corrective bone last (active), like Ctrl+Shift+C.
4. Operator:
   - validates both bones;
   - finds or creates the target's MCH;
   - reads the MCH's local rotation and picks the largest axis as the input;
   - for each output type the corrective actually uses (location, rotation, scale), adds one Transformation constraint: from 0 to the captured value on that axis, to 0 to the corrective's current values. Mix mode is additive, so several correctives on one bone stack (e.g. shoulder raise + shoulder forward);
   - clears the corrective bone's pose transforms so they aren't applied twice.

## Storage
A corrective record, not an assembly. Rough fields:
- corrective bone name
- target ORG name
- MCH name
- constraint names on the corrective bone

Correctives are separate from assemblies, so deleting or rebuilding the target's assembly doesn't affect them. Where the records live (a new collection property on the armature data, next to `rigtools_assemblies`) is still to be decided.

## Panel
Shown when the active bone has a corrective record. Probably near the assembly panel, since that's where the user would look.
- Per constraint: from min/max (input) and to min/max (output) as sliders.
- **Recapture:** re-reads the current pose and updates the constraints. It *adds* a constraint for a newly used output type (e.g. rotation added after creating with location only), so you're never stuck with the first type. Fallback if that's too much: "Add location / Add rotation" buttons.
- Delete: removes the constraints, and removes the MCH if no other corrective uses it.

## Mirroring
One shared function: flip the corrective and target names (`flip_side_name`), find or create the opposite MCH, and copy the Transformation constraints with mirrored values. Blender's X-flip rule, assuming symmetric rest rolls (Symmetrize):
- location: negate X
- rotation: negate Y and Z
- scale: unchanged

This applies to both from and to values. If the opposite corrective bone doesn't exist, report an error; the user makes it.
- Redo panel "Mirror" checkbox: creates both sides at once.
- Panel "Mirror Corrective" button: needed after slider edits, since the redo panel is gone by then.
- Later: an "Include mirror" toggle so slider edits and recapture apply to both sides (like `include_mirror` in `find_similar_assemblies`).

## Open questions
- ~~**Reading the captured value**~~ Solved: `context.view_layer.update()`, then `obj.convert_space(pose_bone=mch, matrix=mch.matrix, from_space='POSE', to_space='LOCAL')`. That includes constraints; `matrix_basis` doesn't.
- **Rotation mode:** the Transformation constraint's source rotation mode. Swing + Twist should avoid Euler flips near 90° (shoulder raises). Euler is the fallback.
- **Which axis/sign** for the input when the pose isn't on a single axis: largest absolute value, keeping the sign for from max.
- **Record storage location** (see Storage).
