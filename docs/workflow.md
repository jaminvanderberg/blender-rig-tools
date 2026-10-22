# Workflow

!!! screenshot "Image placeholder"
    `image/workflow_finished_rig.png` — A finished character rig in Pose mode (torso, arms, legs, fingers, and a skirt or hair assembly), with the Rig UI panel open.  Shows where the workflow ends up.

1. Create the initial rig skeleton:<br>

    **Add > Armature > RigTools Human Skeleton**
    { .where }

    Use this base skeleton, customize it, and fit it to your character, or create the skeleton manually.<br>

2. [Optional] Add twist bones<br>

    **n-Panel > RigTools > Tools > Add Twist Bones**
    { .where }

    Create twist bones on the arm, legs, chest, and neck as desired.
    These can also be created manually.  See *[twist bones](twist_bones.md)* for more information.<br>

3. Weight paint the character<br>

    Weight paint the character as you normally would.  This can be done manually or with standard Blender tools.
    The *[weight paint proxy](operators/weight_paint_proxy.md)* tool might help in some niche cases.<br>

4. Create the ORG bones<br>

    **n-Panel > RigTools > Tools > Generate ORG Bones**
    { .where }

    See *[Generate ORG Bones](operators/generate_org_bones.md)* for more details.
    This tool duplicates every DEF bone and creates a Copy Transforms constraint from the ORG bone to the DEF bone.<br>

5. Create the Torso assembly<br>

    **n-Panel > RigTools > Forward Kinematics > Torso**
    { .where }

    Select the torso bones, neck, and head (excluding twist bones) and create the torso assembly.
    See *[torso assembly](fk_assemblies.md#torso)*<br>

6. Create the Arm and Leg assemblies<br>

    **n-Panel > RigTools > Inverse Kinematics > Arm** and **Leg**
    { .where }

    See *[ik_assemblies](ik_assemblies.md)* for more information

7. Create additional assemblies as desired.

    Add shoulder, palm, and finger assemblies if desired.  Add assemblies for hair, cloth, tails, etc.
    Use "FK only" for short detail chains, or "Simple FK" if you want tweak controls.

## Related

- [Inverse Kinematics Assemblies](ik_assemblies.md)
- [Forward Kinematics Assemblies](fk_assemblies.md)
- [Twist Bones](twist_bones.md)
- [ORG & DEF](org_def.md)
- [Rig UI](rig_ui.md)

