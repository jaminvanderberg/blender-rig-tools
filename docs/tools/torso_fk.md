# Torso FK

Builds the torso control stack: torso/hips/chest masters, spine/neck FK, and head control from a single linear ORG chain.

## Overview

The default torso configuration includes two bones for the lower torso, usually "ORG-hips" and "ORG-spine.01" or similar.  These bones will be controlled by the **hips** controller. This default configuration also includes two bones for the upper torso, usually "ORG-spine.02" and "ORG-chest" or similar. The ORG-chest bone has 2 **twist bones** enabled by default (see below). These bones will be controlled by the **chest** controller. Lastly, the default configuration includes a single neck bone with 2 twist bones ("ORG-neck", usually), and a single head bone ("ORG-head", usually).  This is a total of 6 main bones: ORG-hips, ORG-spine.01, ORG-spine.02, ORG-chest, ORG-neck, and ORG-head, and 4 twist bones: 2 for the chest and 2 for the neck.

!!! screenshot "Image placeholder"
    `image/torso_sections.png` — Labeled side view of the default torso chain, with each section bracketed: **hips** controller (hips, spine.01), **chest** controller (spine.02, chest + 2 twist bones), **neck** (+ 2 twist bones), and **head**.

This configuration can be modified to fit different torso types.  It uses two parameters to determine which bones belong to which section of the torso: **"Lower torso bone count"** and **"Neck bone count"**.  It will always assume a head bone count of 1.  So any remaining bones will belong to the chest.  This should allow a decent amount of flexibility if you want to reconfigure the torso.  All lower torso bones will be controlled by the **hips** controller, and all upper torso bones will be controlled by the **chest** controller.  Adding additional neck bones will add additional FK controllers for the neck. This is usually not desired unless there is a really long neck.  Use twist bones instead if you only want one neck FK controller.

The torso uses [twist bones](twist_bones.md) in a manner similar to the [IK assemblies](../ik_assemblies.md), but slightly different.  The chest twist bones aren't technically twist bones.  They are used primarily as a way to add an additional tweak bone without adding another FK controller.  The chest twist bones do not twist; in that way they are somewhat like the shin.  But there is no way to add twist capabilities to the chest, unlike the shin.  The neck twist bones do twist, following the head with fall-off.  This is an optional setting that can be disabled, but is usually desirable.  If neck falloff is disabled, the neck twist bones will behave like the chest: adding an additional tweak bone without adding an FK controller.  Twist bones are technically not required to have neck rotation fall-off from the head.  All that is required is more than 1 neck bone.  As stated above, though, this adds an additional FK controller for the neck, and is usually not desirable.  If there is only one neck bone and no twist bones, neck fall-off cannot operate.

!!! screenshot "Image placeholder"
    `image/torso_controls.png` — The finished torso in Pose mode, showing the torso box, the hips and chest widgets, the spine FK circles, and the neck and head controls.

## Parameters

- Lower Torso Bone Count: the number of bones at the start of the chain that belong to the lower torso, controlled by the **hips** controller.  Default: 2.
- Neck Bone Count: the number of neck bones between the chest and the head.  Each neck bone gets its own FK controller.  Default: 1.
- Use Twist Bones: use twist bones on the neck and chest.  See *[twist bones](twist_bones.md)*.  Default: on.
    - Neck Twist Bone Count: the number of twist bones on each neck bone.  Default: 2.
    - Chest Twist Bone Count: the number of twist bones on the chest.  Default: 2.
- Add Neck Rotation Isolation: add *[rotation isolation](rotation_isolation.md)* to the neck.  Default: on.
    - Neck Inherit Scale From Root: the neck takes its scale from the root bone instead of the chest.  Default: on.
- Add Head Rotation Isolation: add *[rotation isolation](rotation_isolation.md)* to the head.  Default: on.
    - Head Inherit Scale From Root: the head takes its scale from the root bone instead of the neck.  Default: on.
- Neck Falloff: how the head's rotation fades down the neck.  Set to None to disable neck fall-off.  See *[falloff](twist_bones.md#falloff)*.  Default: Root.

## Related

- [FK Assemblies](../fk_assemblies.md#torso)
- [Twist Bones](../twist_bones.md)
- [IK Parent Switching](ik_parent.md)
