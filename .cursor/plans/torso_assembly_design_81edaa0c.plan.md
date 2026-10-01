---
name: Torso Assembly Design
overview: Document the torso build as an ordered sequence of steps (the procedure you went through), so it can be referenced while implementing and later split into tools. Final hierarchy is secondary.
todos:
  - id: write-torso-doc
    content: Write docs/torso.md as a step-by-step build procedure with tool-boundary notes per step
    status: pending
  - id: write-params-section
    content: Add partition/params/flexibility notes (below waist, neck bones, chest=last before neck, hardcoded twists/follow)
    status: pending
  - id: link-docs
    content: Link torso doc from assemblies.md and mkdocs.yml
    status: pending
isProject: false
---

# Torso Assembly Design Doc

## Goal

Document **how the torso was built**, step by step — not only the finished hierarchy. The procedure is the useful artifact: it is what you will re-run in code, and it is the natural cut list for tools. No implementation in this pass.

## Deliverable

Add [`docs/torso.md`](docs/torso.md); link from [`docs/assemblies.md`](docs/assemblies.md) and [`mkdocs.yml`](mkdocs.yml).

Tone: internal build log / design reference. Each step should say **what you create**, **where it sits**, **what you parent/constrain**, and **why**. Optional short “possible tool” note per step or group of steps. End with a compact final hierarchy appendix for orientation only.

Also include the **parameter / flexibility notes** section below (partition counts, chest = last before neck, hardcoded chest/neck twists + neck rot follow, animal mindset). Working notes welcome — this doc is for thinking while building.

---

## Doc shape: procedure first

Lead with prerequisites (6-role ORG chain + chest twists for tweak density), then numbered build steps in the order you described. Do not lead with a finished tree.

### Prerequisites (brief)

- Selection follows **FK roles**, chain order: `hips → spine1 → spine2 → chest → neck → head` (exactly 6).
- Chest twist ORGs exist for tweak density; they are not extra FKs.
- Standard `FKTweakChain` is probably not enough; expect custom / composed tools.

### Build steps (core of the doc)

Capture each of these as its own section with enough detail to reimplement:

1. **Torso controller** — near center of gravity, aim +Y world.
2. **Tweaks along the chain** — including chest: twists drive mid tweaks, **one** chest FK only (tweak in the middle, single FK). Note neck might get the same treatment later vs rotation falloff / single control.
3. **Offset FKs for spine1 and hips** — treat as upside-down: FK at the bone’s **tail**, same orientation as the source bone; hips rotate from the tail.
4. **Lower-chain parenting (inverted)**
   - hips FK → hips.tweak + spine1.tweak
   - spine1 FK → spine2.tweak (same idea as normal tweak parenting, FK moved)
   - spine1 FK → hips FK (opposite of a normal FK chain)
   - both spine FKs → children of **torso** (highest point both directions, at this stage)
5. **Chest mid-tweak exception** — parent middle chest tweak to **ORG chest**, not the FK, so it can follow when the head moves.
6. **Spine2 midpoint MCH** — MCH authored on one of FK spine1 / FK spine2, parented to the other, Copy Transforms from its home bone at **0.5** so the tweak stays between them when either FK moves. Reparent **spine2.tweak** onto that MCH.
7. **Dual masters (hips + chest)** — rest at the spine2-tweak / mid-spine point. Reparent: torso1 (spine1 FK) under hips master; torso2 (spine2 FK) under chest master.
8. **Rotation follow (chest / hips)** — `MCH-spine.02.FK` child of **torso** (not the master). Half-influence Copy Transforms so the bend is shared (torso2 half / chest half; mirror down the hips). Mark as needs live re-check.
9. **Torso → root**.
10. **Neck rotation isolation** — copy scale off (or inherit scale from root like the arm; note preference to match arm if proven).
11. **Head rotation isolation** — same scale policy.

After the steps: short **open questions** (neck falloff, half-influence follow, whether midpoint/dual-master generalizes to “FK every N bones” / tails — probably not).

Then a **final hierarchy appendix** (one mermaid + bullet tree) so the end state is still findable without being the main content.

### Tool-boundary annotations

In the doc, tag steps that look like reusable tools vs torso-only glue, for example:

| Step group | Likely split |
|------------|----------------|
| Torso COG control | small dedicated create (or shared “place control at avg”) |
| Tweaks + collapsed chest FK | custom torso tweak pass (not limb `TwistBones`, not stock `FKTweakChain`) |
| Offset / inverted FK | possibly a general “FK at tail / reverse parent” helper |
| Midpoint half-CT MCH | candidate shared tool (also interesting for other chains) |
| Dual masters + reparent spine FKs | torso-specific |
| Half-influence follow from torso MCH | torso-specific (test first) |
| Rot isolation neck/head | reuse existing rotation isolation tool |

The doc should not pretend these tools exist yet — only mark the seams.

---

## Design decisions (still recorded in the doc, short section)

- **New assembly type** for the orchestrator; compose tools underneath.
- **Fixed 6 FK roles** by selection order; hard-error otherwise. No “bones below waist” knobs until a second character needs them.
- **Twists = tweak density only**; do not run limb twist falloff tool for chest.
- Tail / every-N-bones reuse: mentioned as a thought, not a v1 goal.

---

## ADD: Parameter / flexibility notes (from later discussion)

Capture this in the same doc as a working “how we define the chain” section. Do not replace the build-step narrative — add alongside it.

### What we are leaning on for now

Expose only:

- **Bones below waist** (default 2) — from the hips end of the selection
- **Neck bones** (default 1) — count before the tip

Derived:

- **Head** = always last bone of the chain (do not expose a head count)
- **Above-waist / ribcage span** = whatever is left in the middle
- **Chest bone** = last bone before the neck span (for twist host / naming). A bit weird, but good enough for now.

Twists are **hard-limited to chest + neck** only (no mid-spine twist rows). For now also **hardcode** chest twist count, neck twist count, and neck rotation-follow rather than putting them in the redo panel — try something and revisit.

Absolute bone indexes (“5th bone”) are a bad template language; end-anchored counts are better because extra mid-spine bones lengthen the middle (cat vs Sarah) without moving neck. Bone names are useful as **resolved preview** in the UI, not as the stored template definition.

### Animal / Rigify check-in (mindset, not a second assembly)

- Weak FK-only animal spines are not a target; Simple FK covers that.
- Rigify-style cat is the same mechanism as the human torso: torso + hips/chest masters, up/down from a waist, optional collapsed neck. Flexibility = same roles, different partition counts / waist placement — not `torso_human` vs `torso_animal`.
- Do not build an animal path now; keep the mental model as waist + up side + down side so Sarah’s two mid bones are one instance of that shape.

### Masters / cosmetics (notes to keep)

- Prefer auto master behavior: if a side only has one FK, merge master into that FK (hips/chest widget) instead of separate master checkboxes.
- Tweaks on/off default on; FK shape Circle; masters hard-coded Pringles-like shape; torso box; add a **master** control color (orange default).

### Still open while building

- Twists: create subdivisions vs consume existing twist ORGs (decide when implementing chest/neck collapse).
- Half-influence rotation-follow wiring needs live testing.
- Neck falloff / single-control behavior: play later.
- Whether midpoint half-CT generalizes beyond this spine: probably not.

---

## Out of scope for this pass

- Python assembly / operators
- Scene or resource changes
- Implementing the tool splits (documentation of seams only)
