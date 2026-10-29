# Workflow
<figure markdown="span">
    ![Finished rig](image/workflow_finished_rig.png){ width="360" }
    <figcaption>A finished rig in Pose mode, with the Rig UI and Rig Properties panels open.</figcaption>
</figure>


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

8. Set up the Rig UI<br>

    **n-Panel > Item > Rig UI**
    { .where }

    Arrange the collection buttons, and hide the collections animators don't need, like MCH and ORG.
    See *[Rig UI](rig_ui.md)*.<br>

9. [Optional] Check the rig's data<br>

    **Properties > Armature > RigTools > Check Data**
    { .where }

    Run Check Data to find anything RigTools remembers that's no longer on the rig, such as renamed bones or deleted collections.
    See *[Data Viewer](data_viewer.md)*.<br>

10. Hand the rig off to animators<br>

    **n-Panel > RigTools > Tools > Embed Animator UI**
    { .where }

    Embed the Rig UI script in the file so animators see the Rig UI panels without installing RigTools.
    Or have animators install the **RigTools UI** add-on instead.
    See *[Sharing with Animators](rigui/animators.md)*.<br>

## Related

- [Inverse Kinematics Assemblies](ik_assemblies.md)
- [Forward Kinematics Assemblies](fk_assemblies.md)
- [Twist Bones](twist_bones.md)
- [ORG & DEF](org_def.md)
- [Rig UI](rig_ui.md)
- [Data Viewer](data_viewer.md)
- [Sharing with Animators](rigui/animators.md)

