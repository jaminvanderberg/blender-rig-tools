# Twist Bones

!!! info 
    This is AI-generated documentation that has not yet been human reviewed.

Twist bones distribute rotational twist along a limb or torso segment so deformation
doesn't collapse into a single bone's roll. In RigTools they live on the **ORG / deform**
side of the rig — not as primary animator controls.

Assemblies (especially Arm IK, Leg IK, and Torso FK) create or reuse twist chains,
drive them from control bones with a falloff, and hang **tweak** controls on the
subdivisions. You can also author twist chains yourself and tell RigTools which
ORG bone they belong to.

!!! tip "Start here"
    Twist setup is almost always driven by an [assembly](assemblies.md) template.
    Read Assemblies first if you haven't.

!!! note "Not spline twist"
    Spline IK has its own "twist controllers" on the spline. That is a separate feature.
    This page covers limb/torso twist deform bones and the twist parent map.

## Concepts

### What they are for

| Layer | Role |
| --- | --- |
| Twist bones | Subdivided bones along a segment (usually named like `ORG-upper_arm.1.L`). Used for skinning / ORG→DEF. |
| Segment ORG | The bone the twists "belong to" (upper arm, thigh, neck, etc.). |
| Controls (FK / IK / switch) | Animator-facing bones that **drive** twist via Copy Rotation falloff. |
| Tweaks | Fine controls created on the twist subdivisions. |
| Isolators | Mechanism bones that absorb unwanted twist at the start of some segments (e.g. upper arm) or at the neck. |

### Twist parent map

Identity of a twist bone is **not** inferred from naming alone.
RigTools stores a map on the armature:

- Each twist bone points at the deform/ORG bone it belongs to ("Twist Parent").
- A set of twists for one parent must form a **single linear chain** (parenting root → tip).

You can view and edit Twist Parent on the active bone under **Bone Properties → Rig Tools**,
or use **Set / Clear Twist Parent** from the armature Parent menu
(`Ctrl+Shift+P` / `Ctrl+Alt+P` by default).

!!! note
    *Generate ORG Bones* copies twist-parent links from DEF → ORG, so authored DEF twist
    chains survive ORG generation.

### Persistence

When you delete or reconfigure an assembly:

- Twist **constraints** are removed and twist **parenting** is restored to the pre-assembly state.
- The twist **bones themselves are kept**.
- Bone collections are also kept (see [Assemblies](assemblies.md)).

That means regenerating an arm with the same twist count reuses existing twist bones
instead of creating duplicates.

!!! warning "Count mismatch"
    If twist bones already exist for a segment but the count doesn't match what the
    assembly asks for, generation fails with an error. Clear or fix the chain first
    if you intentionally change the count.

!!! warning "DEF gap"
    Auto-created twists are ORG bones only — matching DEF bones are not generated yet.
    Prefer authoring DEF twists and using Generate ORG Bones, or link DEFs yourself afterward.

## In assemblies

### Arm and Leg IK

When **Use Twist Bones** is enabled (default on Arm / Leg templates):

1. RigTools looks up existing twists for each configured segment.
2. If none exist, it subdivides the segment ORG into the requested count and registers them.
3. It builds tweak controls on those subdivisions and wires Copy Rotation falloff from the
   appropriate control bones.

**Segment source** controls what drives the falloff:

| Source | Meaning | Typical use |
| --- | --- | --- |
| Self | Twist from that segment's own control | Upper arm, thigh |
| Child | Twist from the child segment's control | Forearm from hand |
| None | Deform / tweaks only — no Copy Rotation falloff | Shin |

**Falloff** presets (`Linear`, `Smooth`, `Round`, `Root`, `Sharp`) shape how much influence
each twist bone gets along the chain. Influence is stronger toward the tip of the twist chain
by default.

Default templates:

| Template | Segments | Count |
| --- | --- | --- |
| Arm | Arm → Self / Root · Forearm → Child / Linear | 4 |
| Leg | Thigh → Self / Sharp · Shin → None | 4 |

The redo panel exposes twist enable, count, and the segment list (name, bone index, source, falloff).

### Torso FK

Torso does not use the same tool class, but the same map and create/reuse rules:

- Optional **neck** and **chest** twist counts (enabled when Use Twist Bones is on).
- Neck falloff can drive the neck/head FK chain across twist subdivisions.
- A neck isolator may be created when rotation isolation is on and the neck has multiple pieces.

## Manual workflow

Useful when you want a custom twist layout before generating an assembly:

1. Create the twist bones (subdivide / duplicate as you like).
2. Parent them into one linear chain per segment.
3. **Set Twist Parent** on those bones to the segment ORG (or DEF, then Generate ORG Bones).
4. Run the assembly with a matching twist count — RigTools will reuse your chain.

## Related

- [Assemblies](assemblies.md)
- Inverse Kinematics Assemblies (Arm / Leg twist options)
- Forward Kinematics Assemblies (Torso twist options)
