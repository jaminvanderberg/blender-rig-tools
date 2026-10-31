# Bone style edits: keep hand edits across reconfigure

## Status (2026-10-31)
**Done and tested in Blender.** Not committed yet: everything after `de30e6c`.

What's left:
- **Parked:** the side-suffix refactor (in `TODO.md`).

How we work: the user builds, or Claude makes one change at a time with its diff and assumptions listed, and the user reviews before the next. No new files, features or renames without describing them first, and no edits until the user says go.

## Context
This comes from the TODO item "preserve hand-edited widgets/shape settings across reconfigure". Bone styles are stored per bone in `BoneRef.style_json` (see `plans/bone_colors.md`). A reconfigure deletes the assembly and rebuilds it, so without this, any style a user changed by hand was lost.

Style is the one kind of assembly data users are expected to edit, with Blender's own tools (the Custom Shape panel, Copy to Selected, the Bone Widget add-on).

## Decisions
- **It's an assembly config.** `BoneStyleConfig` follows the pattern in `config_registry.py`: `snapshot()` reads the live pose bones before the delete, `prepare_rebuild` carries the result in `prior_configs`, and `apply_tool` lays it over the rebuilt bones.
- **`style_json` always holds the assembly default.** Hand edits aren't stored. The live pose bone is the diff, and the snapshot only exists for one rebuild.
- **Everything in the Custom Shape panel is kept, plus the pose bone color**, including settings no style sets (Wireframe, Scale to Bone Length).
- **A hand edit wins over the rebuild**, including a different widget. Reset is how users get out of that.
- **Bones that no longer exist are dropped silently.** Reconfigure can be undone.
- **Renaming is out of scope.** Renaming bones already means delete, rename, recreate.
- **Widgets are shared.** Each rig has one widget per widget class, not one per bone. This removed per-bone widget ownership, fingerprints on bones, keep/rename logic, and Make Unique.
- **Widgets are never deleted** by assemblies. Clear Unused Widgets in the data viewer removes leftovers.
- **Widget types are named for their shape, not their purpose.** `CHEST` became `WAVY` and `ROOT` became `COMPASS`, so a type's default class can't collide with a special class. The bones that care about purpose get a class: Chest, Hips, Root, Properties.
- **Change Widget only changes the selected bones**, never the other side. Select both to change both. Reset to Default then undoes exactly what Change did.
- **Changing a special-class bone never touches its widget.** It gets the class's own widget for the new shape (`{class}-{Shape}`, for example `WGT-Sarah-FK-Hand-Circle`), so it doesn't share with generic bones, and the original keeps any hand edits. Changing back to the original type uses the original widget again. Swapping the mesh inside the shared widget was rejected because it destroys edits.
- **Restoring an edited mesh can keep it.** Reset Widget Mesh moves the edited mesh to a `WGT-EDITED-` copy instead of deleting it (on by default). A second copy gets Blender's `.001`; that's fine.
- **The Bone Style panel works on any bone, on any armature.** On other bones, the reset buttons and Reset to Default go back to Blender's defaults (`style_defaults` with no `bone_ref`), including no widget. Naming a widget sets only the widget prefix, so changing a widget doesn't turn an armature into a RigTools rig.
- **No migration.** Only Sarah has shared widgets so far.

## Core design

### Shared widgets (`utils/widget.py`)
- **Name:** `WGT-{prefix}-{class}` (`generate_widget_name(widget_class, context)` in `naming.py`). The prefix comes from `get_widget_prefix(armature_object)` in `armature_settings.py`, which sets it from the object's name the first time without initializing the other settings. The class is used as-is: no tag or side stripping.
- **Class:** `BoneStyle.widget_class`, optional. Without one, the default class is the widget type `.title()`d, except `FK` and `IK` (`DEFAULT_WIDGET_CLASSES`). Called a class, not a role, because bones already have roles (fk/ik/tweak/control/mch).
- **Who sets classes:** the torso tool (Torso, Hips, Chest, Neck, Head); IK templates through `tip_widget_class`, `fk_end_widget_class` and `ik_widget_class` (arm: FK-Hand, IK-Hand; leg: Toe, FK-Foot, IK-Foot); root widgets (Root, Properties). The IK classes pass through `IKAssemblyOptions` and hidden properties on the IK setup operator, and reconfigure restores them from the saved options. Options and properties use `""` for none; `ik_assembly` converts to `None` before the tools, because `BoneStyle` treats `None` as "no change".
- **A class has one shape:** the first build to create it decides which.
- **Custom properties on the widget object:**
  - `rigtools_widget` (`STANDARD_WIDGET_KEY`): the name it was created with. Lookup is by name first, then by scanning for the tag, so a renamed widget is still found and another rig's widget never matches.
  - `rigtools_widget_mesh` (`STANDARD_WIDGET_MESH_KEY`): a SHA-1 of the rounded vertices and edges, written when RigTools creates or restores the widget. `is_widget_mesh_edited` compares it with the current mesh. A widget without a hash counts as edited.
  - `rigtools_widget_type` (`STANDARD_WIDGET_TYPE_KEY`): the widget type, written by `get_standard_widget` (which also fills it in on older widgets). It's how the panel knows the live shape after a Change, and what `restore_widget_mesh` rebuilds.
  - `rigtools_widget_copy` (`STANDARD_WIDGET_COPY_KEY`), on kept copies only: the shared widget's name. Copies aren't standard widgets, but `unused_standard_widgets` includes them when no bone uses them.
- **Mirroring:** in `apply_tool`, a style with a widget class on an R-side assembly gets its X scale negated before it's applied and recorded, so L and R draw as mirror images and `style_diff` sees no edit. Only classed widgets: default-class shapes are symmetric.
- **Scale and slide axes:** `UNIFORM_SCALE_WIDGETS` (Sphere, Wavy, Compass, Gear) scale on all three axes; everything else scales X and Z and keeps Y, the bone's length. `Z_SLIDE_WIDGET_CLASSES` (Torso, Chest, Hips) are on bones that point forward, so their widgets slide on Z; everything else slides on Y.
- **Helpers:** `find_standard_widget` (never creates; safe while drawing), `get_standard_widget` (creates on first use), `restore_standard_widget` / `restore_widget_mesh(wgt, keep_copy)` (fresh mesh from the creator), `standard_widget_type`, `unused_standard_widgets`, `remove_widget`. Creators are looked up with `_widget_creator(widget_type)`.

### The diff (`assemblies/configs/bone_styles.py`)
- **`style_defaults(context, bone_ref)`** returns each kept setting as the assembly built it: custom shape settings (the style's value, or Blender's default from `CUSTOM_SHAPE_PROPS`), `custom_shape_transform` (bone name), `custom_shape` (the expected shared widget's name), and `color` (stored palette, left out when unknown).
- **`style_diff(context, pose_bone, bone_ref)`** compares the live bone with `style_defaults`. Anything but the expected shared widget is a hand edit to the shape.
- **`reset_style(context, pose_bone, bone_ref, props)`** sets the given properties back to `style_defaults`.
- **`BoneRef.palette`** records the palette the style's color resolved to, so a preference change that hasn't been reapplied doesn't make every bone look hand-colored.

### Reconfigure
`BoneStyleConfig.snapshot()` returns `{bone name: BoneStyleDiff}`. After each bone's style is applied in `apply_tool`, its `BoneStyleDiff` is applied on top. A shape is carried by object name; a name that no longer exists is skipped.

## UI (`panels/bone_style/bone_style_panel.py`)
- **Bone Style sidebar panel** (`RIG_PT_bone_style`, n-Panel > Rig Tools, Pose mode, closed by default since it's a finishing tool):
  - **Widget:** a dropdown labeled with the live widget's type (`_widget_label`), which runs Change Widget. **Reset Widget Mesh** appears centered under it when the live widget's mesh is edited.
  - **Slide / Translation:** one number by default (`PoseBone.rigtools_style_slide`); clicking the label shows X/Y/Z.
  - **Rotation:** always X/Y/Z.
  - **Scale:** one number relative to the assembly's scale (`PoseBone.rigtools_style_scale`), so it starts at 1.0; clicking the label shows X/Y/Z.
  - **Wire Width, Color.**
  - Each row ends in a reset button when that setting is edited on the active bone; it runs Reset with `only=<option>`, no dialog, on the selected bones.
  - Slide and Scale are get/set properties that write straight through to the real vectors, so undo, Edited and the reset buttons work unchanged. The expand toggles are on the window manager: per session, not saved, not undone.
- **Change Widget** (`RIG_OT_change_widget`): a menu of `STANDARD_WIDGET_TYPES` plus None. On the selected bones only: a special-class bone gets `{class}-{Shape}` (or its own class for its original type), any other bone the type's default class.
- **Reset Widget Mesh** (`RIG_OT_reset_widget_mesh`): works on the active bone's live widget, so it covers changed widgets and non-assembly bones. Dialog shows how many bones use the widget, plus **Keep a copy of the edited mesh** (on by default, remembered).
- **Custom Shape panel** (appended to `BONE_PT_display_custom_shape`):
  - **Shared Widget:** which bones use it, or "N bones" past `NAMED_BONES_MAX`.
  - **Edited:** the checkbox names of everything edited on the active bone, including Widget Mesh.
  - **Reset to Default** button.
- **Pose mode right-click:** Reset Style to Default.
- **3D View header:** a red warning while a shared widget is in Edit Mode.
- **Reset to Default** (`RIG_OT_reset_bone_style`):
  - **Checkboxes:** Widget, Widget Mesh, Color, Translation, Rotation, Scale, Wire Width, Override Transform, Display (Wireframe and Scale to Bone Length). All on by default; Blender remembers the last choice. Keep a copy shows when Widget Mesh is edited.
  - **Dialog every time, even for one edit.** The Properties editor has no redo panel. It shows only the checkboxes with something edited on the selected bones.
  - **Greyed out by `poll`** when nothing on the selected bones is edited. Checks every selected bone (`styled_bone_refs` dict, stops at the first edit).
  - **Widget Mesh** restores each shared widget once, and only if its hash doesn't match. The report names the widgets restored and copies kept. A user's own object is unassigned, never deleted.
  - **`RESET_OPTIONS`** maps each checkbox to its label and the settings it resets. It's the one table behind the checkboxes, "Edited:" and the dialog.
- **Data viewer, Widgets subpanel** (`data_viewer/panel.py`): count of unused widgets, and **Clear Unused Widgets** (`RIG_OT_clear_unused_widgets`) with a Delete dialog listing them (up to `LISTED_WIDGETS_MAX`). It only deletes tagged RigTools widgets and kept copies that no bone on any rig uses. It's not a Check Data fix, because fixes promise never to delete objects.
- **Not doing:** a ✓ "edits kept" signal row (replaced by Edited + Reset), a right-click per-field reset (the panel's reset buttons cover it), Make Unique, Copy Widget to Selected (Change Widget already applies to every selected bone), Wireframe / Bone Length / Override Transform / Widget Mesh rows in the sidebar panel (still in Bone Properties and Reset to Default).

## Learned
- **RNA defaults aren't reliable.** `PoseBone.bl_rna.properties[...].default` doesn't match a new bone's values, so Blender defaults are hardcoded in `CUSTOM_SHAPE_PROPS`.
- **`show_wire` lives on `Bone`**, not `PoseBone` (`BONE_PROPS`).
- **`SplineIK` registered bones twice**; the duplicate `extend()` calls are removed. `MechanismBones.add` still doesn't check for duplicates.
- **An operator's own properties aren't in `cls.bl_rna.properties`.** Reading checkbox labels from there raised a KeyError that hid the whole panel section. Errors in appended draw functions only show in the system console.
- **A misspelled property option (`option=` for `options=`)** stops Blender registering every property after it.
- **Blender loads the installed copy** in `AppData\...\addons\rigtools`. Rebuild before testing. Background tests must put the repo first on `sys.path`, drop the addons folders, and add a `preferences.addons` entry for `rigtools`, or they test the installed copy or fail on preferences.
- **In Blender 5.2, selection is `PoseBone.select`**, not `Bone.select`.
- **Deleting assemblies doesn't delete widgets**, so pre-existing widgets get reused by name. Widgets made before the mesh hash have none and show as edited until restored or deleted.
- **The side is stored as the raw bone suffix**, so checks parse it (`"R" in side.upper()`). See `TODO.md`.

## Testing
After a rebuild, nothing should print:
```python
from rigtools.assemblies.configs.bone_styles import style_diff
for a in C.object.data.rigtools_assemblies:
    for ref in a.mechanism_bones:
        pb = C.object.pose.bones.get(ref.name)
        d = style_diff(C, pb, ref) if pb else None
        if d:
            print(a.name, ref.name, d)
```
Then: change a bone's wire width, color and scale, and check that "Edited" lists them and Reset clears them. Edit a shared widget's mesh, check that "Widget Mesh" appears on every bone using it, and that Reset restores it once, keeping a `WGT-EDITED-` copy. Change Hand.L to Box and check Hand.R keeps its widget.

## Notes
- Blender has two bone colors, Bone and Pose Bone. RigTools sets the Pose Bone color; changing the Bone color does nothing in Pose Mode. Worth a line in the docs.
- Reapply Bone Colors goes through every armature, so `context.object` isn't always the rig. It reads settings directly on purpose.

## Open question
- Silent or a summary on reconfigure? The leaning is silent. One option is a single INFO line, such as "Kept hand edits on 12 bones; 2 no longer exist."
