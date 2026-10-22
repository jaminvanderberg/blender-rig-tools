# Rig Tools

Blender 4.0+ addon for armature setup and chain building.

**Install:** Preferences > Add-ons > Install > select `rigtools.zip` 
  
**UI:** View3D > Sidebar > **Rig Tools** (armature selected).

---

## Full Documentation

https://jaminvanderberg.github.io/blender-rig-tools/

## Introduction

RigTools is a rig creation tool for Blender. If you want an easy rigging setup in Blender, Rigify is a much better fit. This is my attempt at overcoming some of the rigidity of Rigify, turning the rig-building into more of a interactive process rather than the setup-and-click mentality of Rigify. This methodology doesn't leave the rig in an uneditable state, and makes it easier to go back and make changes to the rig.

I found myself locked out of a rig that I had "finalized" a month before.  When I joined the face rig (shapekey-based) to the Rigify rig, it caused several problems with Rigify's RigUI. I was able to solve these will some effort.  But then later, when I decided to add a skirt to the outfit, I was locked out of using Rigify's tools to create it. I knew that creating a second Rigify rig and joining it would only cause more problems with the rig UI,
and I wasn't sure if I'd be able to add these new bones to the rig UI. I found myself wishing I could setup the Rigify chains in a more ala carte fashion. This add-on has been my slow push towards that goal.

Version 1 of RigTools is centered around humanoid characters.  While some of the tools might work for animals, machines, or other rig types, these were not the priority for the initial version.  There are plans to add additional capabilities in the future, but this likely won't happen until I need them for my own rigs, or someone else contributes them.

This tool centers around creating "assemblies", which is a set of mechanisms belonging to a limb.
Assemblies can be reconfigured or deleted after creation.  For more information on assemblies, see
*[assemblies](docs/assemblies.md)*
