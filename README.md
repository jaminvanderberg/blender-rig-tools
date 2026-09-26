# Rig Tools

Blender 4.0+ addon for armature setup and chain building.

**Install:** Preferences → Add-ons → Install → select `rigtools.zip` (or the `rigtools` folder).  
**UI:** View3D → Sidebar → **Rig Tools** (armature selected).

---

## Contents

- [Introduction](#introduction)
- [Preferences](#preferences)
- [Armature Settings](#armature-settings)
- [Rename Chain(s)](#rename-chains)
- [Create FK/Tweak Chain](#create-fktweak-chain)
- [Create FK/IK Switch](#create-fkik-switch)
- [Create MCH Bones](#create-mch-bones)
- [Create Rotation Isolation](#create-rotation-isolation)
- [Find Dependents](#find-dependents)
- [Generate ORG Bones](#generate-org-bones)
- [Select Bones by Name](#select-bones-by-name)
- [Batch Rename Bones](#batch-rename-bones)
- [Weight Paint Proxy](#weight-paint-proxy)


---

<!-- Copy this block for each new tool:

### Tool Name

**Where:** N-panel → Rig Tools (Edit / Pose)  
**Requires:** …

One-line summary of what it does.

1. Step
2. Step

**Output:** bones / constraints / props it adds  
**Notes:** gotchas, limitations

-->

## Introduction

This is set of tools for advanced rig manipulation in Blender.
If you want an easy rigging setup in Blender, Rigify is a much better fit.
This is my attempt at overcoming some of the rigidity of Rigify, turning the rig-building
into more of a interactive process rather than the setup-and-click mentality of Rigify.
This methodology doesn't leave the rig in an uneditable state, and makes it easier
to go back and make changes to the rig.

I found myself locked out of a rig that I had "finalized" a month before.  When I joined
the face rig (shapekey-based) to the Rigify rig, it caused several problems with Rigify's RigUI.
I was able to solve these will some effort.  But then later, when I decided to add a skirt to 
the outfit, I was locked out of using Rigify's tools to create it. 
I knew that creating a second Rigify rig and joining it would only cause more problems with the rig UI,
and I wasn't sure if I'd be able to add these new bones to the rig UI.
I found myself wishing I could setup the Rigify chains in a more ala carte fashion.
This add-on has been my slow push towards that goal.

This is a series of tools designed to speed up repetitive tasks while creating rigs.
The design philosphophy is to not attempt to cover every possible contingency while creating a rig,
but rather to provide powerful, flexible tools for the tasks that are repetitive or complex.

Many of the tools operate on chains of bones.  A chain is a series of bones where one is parented to
another.  All of these tools expect linear chains; that is, each bone can only have one child. These
tools work on the selected bones only, so you can get around this limitation by selecting only one child per parent.
The tools do not require these children to be connected.

Tools that operate on bone chains:
- [Rename Chain(s)](#rename-chains)
- [Create FK/Tweak Chain](#create-fktweak-chain)
- [Create FK/IK Switch](#create-fkik-switch)
- [Weight Paint Proxy](#weight-paint-proxy)

These tools can operate on more than one chain at a time.  Rename chain has a special naming operation for multiple
chains, and the chain creation tools will just make multiple chains with the same parameters.

## Preferences

**Where:** Preferences → Add-ons → Rig Tools  
**Requires:** —

Naming templates, bone colors, selection buttons, import/export.

- Selection buttons / columns
- Strip tags & separators
- Naming templates (DEF, ORG, FK, IK, etc.)
- Import / Export preferences (JSON)

## Generate ORG Bones

**Where:** N-panel → Rig Tools (Object / Edit / Pose)  
**Requires:** Armature with DEF bones

This tool will create ORG bones for all the DEF bones in the rig, selection, or view.
Calling them 'ORG' bones is a Rigify convention that Blender follows as well,
and I've chosen to follow it as well. Although you can change the name of the bones
if you want.

The purpose is to have a set of bones that control the DEF bone, and these ORG bones
will be the target of all the rigs mechanisms.  Typically, the ORG bone will control
the DEF bone via a Copy Transforms constraint.  I've included an option to parent them instead,
but I'm not sure how useful that is.

This tool was designed to be safe to run over and over again.  It won't make multiple
constraints and it won't create duplicate bone.  It will scan to see if the bone and constraint
exist, and create any that don't.  So you can run this over and over again for the whole rig,
and it shouldn't cause any issues as long as you follow the naming convention.

The new bones can be added to a bone collection, if specified.  If the bone already exists,
it will not be moved into this bone collection.

**Output:**  Generates ORG bones matching the name of a corresponding DEF bone, if they don't exist already

## Select Bones by Name

**Where:** N-panel → Rig Tools (and optionally Item tab)  
**Requires:** Armature in Pose or Edit mode

Useful for selecting bones that match a naming convention.  
Check out the (#preferences), where you can customize this list or add your own.

Note that the search is case insensitive and looks for the exact string specified.
So it would be possible for "IK" to match on "spike", which is why a separator was added to be more specific.
It's possible that "DEF" could match with "default", or "ORG" could match with "organic" or "organism", so be aware
and adjust the preferences as necessary.

There is an additional search box that can be used for custom search strings.

**Output:** —  Adds bones to the current selection
**Notes:** Button labels/terms come from addon Preferences.

## Batch Rename Bones

**Where:** N-panel → Rig Tools (Edit / Pose); shortcut `Ctrl+F2`  
**Requires:** Selected bones

This is a replacement for the default batch rename tool that's customized for bones.
It will automatically strip numbers from the end of bone names, if the option is selected.

**Output:** —  Renames selected bones based on find/replace, add prefix/suffix, and strip numbers

## Rename Chain(s)

**Where:** N-panel → Rig Tools (Edit / Pose)  
**Requires:** Selected bone chain(s)

Tool used to rename bones along a chain, or multiple chains.
A useful tool for renaming long chains or many chains with the same name (such as hair or a dress).

For bones along a single chain, they will be numbered in order.
Use the "{bone}" placeholder in the name template, which will be replaced
with the number (or letter) on each bone in the chain.

For bones along multiple chains, the bones in each individual chain will be renamed as above, using the "{bone}" placeholder.
Additionally, a "{chain}" placeholder may be used to a number or letter that describe the chain.
To choose the order for the chains, select an ordering mode.  The default is "Angular" around the Z axis.
That is, it will search in a circle around the Z axis and use that to pick the order.  
This is the default because it's useful for hair and dresses, where the chains usually go around in a circle.
You can pick a starting angle and flip the direction.  A preview of the chosen number/letter should show up in the 3d viewport.
You can also select the "Linear" option to evaluate chain order linearly along the selected axis.

**Output:** —  Renames selected bones based on a template

## Create MCH Bones

**Where:** N-panel → Rig Tools (Edit / Pose)
**Requires:** Selected bones

Quick tool for creating mechanism bone.  
The mechanism bone will be named based on the template provided.
The mechanism bone will the take existing parent from the selected bone, 
and the mechanism bone will become the new parent of the selected bone.

The tool works on multiple bones.  It will create a MCH bone for each bone in the selection.

**Output:**  Generates one or more MCH bones that are parents of the selected bone(s)

## Create Rotation Isolation

**Where:** N-panel → Rig Tools (Edit / Pose)  
**Requires:** Selected bone

Create a rotation isolation mechanism driven by a custom property.

1. …

**Creates:**  
**Notes:**

## Create FK/Tweak Chain

**Where:** N-panel → Rig Tools (Edit / Pose)  
**Requires:** Linear bone chain (one child per parent; connection optional)

Creates an FK/Tweak chain from an existing bone chain.

1. Select chain
2. Run **Create FK Tweak Chain**

**Creates:**  
**Notes:** Chains must be linear (one child per parent), but don't need to be connected.

## Create FK/IK Switch

**Where:** N-panel → Rig Tools (Edit / Pose)  
**Requires:** Selected bone chain(s)

Create an FK/IK switch for the selected bone chains.

1. …

**Creates:**  
**Notes:**

## Find Dependents

**Where:** …  
**Requires:** Active bone

List bones that depend on the active bone (children, constraints, drivers).

1. …

**Creates:** —  
**Notes:**

## Armature Settings

**Where:** …  
**Requires:** Armature

Per-armature settings used by the tools (e.g. root bone).

1. …

**Creates:**  
**Notes:**



**Notes:**


## Weight Paint Proxy

**Where:** N-panel → Rig Tools (Edit / Pose)  
**Requires:** Selected chain(s)

Tool to assist creating a simplified mesh that can be the target of a Data Transfer modifier.
Provides additional tools for spreading the weights across the mesh.
Principal use case for this tool is skirts, cloth, etc.

**Stitch Chain** - If enabled, it will create faces between chains based on the settings provided.
If "Stitch chain" isn't used, the mesh will contain edges only and will need to be stitched manually.

**Ordering Mode** - This option defines how the chains are ordered.  The default is "Angular" around the Z axis.
The "Angular" will search in a circle around the centroid of the selected chain heads, 
in the plane perpendicular to the chosen axis.
This is the most useful when chains go around in a circle (like a skirt).
You can pick a starting angle and flip the direction.  A preview of the chosen number/letter should show up in the 3d viewport.
You can also select the "Linear" option to evaluate chain order linearly along the selected axis.

**Close Loop** - This option will close the edges between the last chain and the first chain, creating a full loop.

**Chain Align** - Option only appears if the chains are not all the same length.
The tool will need to create a triangle fan for any additional vertices.
The "Chain Align" parameter controls whether the triangle occur at the start or the end of the chains.
This will also control how the weights are distributed.

**Seed Weights** - This option will fill the new mesh with vertex group weights for the respective bones. 
If "Spread weights" isn't used, this will set all weights to 1.0.

**Spread Weights** - if used, the tool will distribute the weights around the mesh based on additional settings.

**Spread Along Chain** - controls how much weight is distributed up/down along each chain. (Higher = softer/more weight bleed)

**Spread Across Chain** - controls how much weight is distributed left/right between chains.

**Iterations** - You can use this setting to control how many times the spread is run,
this will typically lead to smoother weights.

**Lock Root Rows** - will prevent weight distribution down the chain for the first n bones in each chain.
Skirts and other cloth will typically want at least 1 locked row to prevent bones further down the chain
from affecting where the cloth is attached.

The purpose of this tool isn't to create a perfect proxy that will work flawlessly without
any additional weight painting.  The purpose of this tool is to accelerate the building
of a proxy and give a solid baseline for additional manual weight painting.

**Output:** Creates a new mesh with armature modifier and weights based on settings.
**Notes:** Switches to weight paint mode with the new mesh and armature selected.