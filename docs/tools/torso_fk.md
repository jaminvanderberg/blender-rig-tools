# Torso FK

!!! info
    This is AI-generated documentation that has not yet been human reviewed.

Builds the torso control stack: torso/hips/chest masters, spine/neck FK, and head control from a single linear ORG chain.

## Overview

The default torso configuration includes two bones for the lower torso, usually "ORG-hips" and "ORG-spine.01" or similar.  These bones will be controlled by the **hips** controller. This default configuration also includes two bones for the upper torso, usually "ORG-spine.02" and "ORG-chest" or similar. The ORG-chest bone has 2 **twist bones** enabled by default (see below). These bones will be controlled by the **chest** controller. Lastly, the default configuration includes a single neck bone with 2 twist bones ("ORG-neck", usually), and a single head bone ("ORG-head", usually).  This is a total of 6 main bones: ORG-hips, ORG-spine.01, ORG-spine.02, ORG-chest, ORG-neck, and ORG head, and 4 twist bones: 2 for the chest and 2 for the neck.

This configuration can be modified to fit different torso types.  It uses two parameters to tell determine which bones belong to which section of the torso: **"Lower torso bone count"** and **"Neck bone count"**.  It will always assume a head bone count of 1.  So any remaining bones will belong to the chest.  This should allow a decent amount of flexibility if you want to reconfigure the torso.  All lower torso bones will be controlled by the **hips** controller, and all upper torso bones will be controlled by the **chest** controller.  Adding additional neck bones will add additional FK controllers for the neck. This is usually not desired unless there is a really long neck.  Use twist bones instead if you only want one neck FK controller.

The torso uses [twist bones](tools/twist_bones.md) in a manner similar to the [IK assemblies](../ik_assemblies.md), but slightly different.  The chest twist bones aren't technically twist bones.  They are used primarily as a way to add an additional tweak bone without adding another FK controller.  The chest twist bones do not twist; in that way they are somewhat like the shin.  But there is not way to add twist capabilities to the chest, unlike the shin.  The neck twist bones do twist, following the head will fall-off.  This is an optional setting that can be disabled, but is usually desireable.  If neck falloff is disabled, the neck twist bones will behave like the chest: adding an additional tweak bone without adding an FK controller.  Twist bones are technically not required to have neck rotation fall-off from the head.  All that is required is more than 1 neck bone.  As stated above, though, this adds an additional FK controller for the neck, and is usually not desirable.  If there is only one neck bone and no twist bones, neck fall-off cannot operate.

## Parameters

-  

## Related

- [FK Assemblies](../fk_assemblies.md#torso)
- [Twist Bones](../twist_bones.md)
- [IK Parent Switching](ik_parent.md)
