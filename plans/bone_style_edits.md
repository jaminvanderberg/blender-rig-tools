# Bone style edits: keep hand edits across reconfigure

## Status (2026-10-30)
**Done and tested in Blender**, except Clear Unused Widgets (tested in background Blender only). Not committed yet: everything after `417b4a3`.

What's left:
- **Change Widget**, a swap tool (dropdown of widget types). Nearly free: `style_diff` already keeps a different shared widget as a hand edit, and Reset brings the default back.
- **Small cleanups:** `BoneStyleDiff.bone_name` is never read; `human_skeleton.py` imports `apply_widget` without using it.
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
- **No migration.** Only Sarah has shared widgets so far.

## Core design

### Shared widgets (`utils/widget.py`)
- **Name:** `WGT-{prefix}-{class}` (`generate_widget_name(widget_class, context)` in `naming.py`). The prefix is `widget_prefix` in armature settings, set at initialize from the rig object's name. The class is used as-is: no tag or side stripping.
- **Class:** `BoneStyle.widget_class`, optional. Without one, the default class is the widget type `.title()`d, except `FK` and `IK` (`DEFAULT_WIDGET_CLASSES`). Called a class, not a role, because bones already have roles (fk/ik/tweak/control/mch).
- **Who sets classes:** the torso tool (Torso, Hips, Chest, Neck, Head); IK templates through `tip_widget_class`, `fk_end_widget_class` and `ik_widget_class` (arm: FK-Hand, IK-Hand; leg: Toe, FK-Foot, IK-Foot). These pass through `IKAssemblyOptions` and hidden properties on the IK setup operator, and reconfigure restores them from the saved options. Options and properties use `""` for none; `ik_assembly` converts to `None` before the tools, because `BoneStyle` treats `None` as "no change".
- **A class has one shape:** the first build to create it decides which.
- **Tag:** custom property `rigtools_widget` (`STANDARD_WIDGET_KEY`) holds the name the widget was created with. Lookup is by name first, then by scanning for the tag, so a renamed widget is still found and another rig's widget never matches.
- **Mesh hash:** custom property `rigtools_widget_mesh` (`STANDARD_WIDGET_MESH_KEY`), a SHA-1 of the rounded vertices and edges, written when RigTools creates or restores the widget. `is_widget_mesh_edited` compares it with the current mesh. A widget without a hash counts as edited, so it can still be restored. It's on the widget, not the bones, because the widget is shared.
- **Mirroring:** in `apply_tool`, a style with a widget class on an R-side assembly gets its X scale negated before it's applied and recorded, so L and R draw as mirror images and `style_diff` sees no edit. Only classed widgets: default-class shapes are symmetric.
- **Helpers:** `find_standard_widget` (never creates; safe while drawing), `get_standard_widget` (creates on first use), `restore_standard_widget` (fresh mesh from the creator), `unused_standard_widgets`, `remove_widget`. Creators are looked up with `_widget_creator(widget_type)`.

### The diff (`assemblies/configs/bone_styles.py`)
- **`style_defaults(context, bone_ref)`** returns each kept setting as the assembly built it: custom shape settings (the style's value, or Blender's default from `CUSTOM_SHAPE_PROPS`), `custom_shape_transform` (bone name), `custom_shape` (the expected shared widget's name), and `color` (stored palette, left out when unknown).
- **`style_diff(context, pose_bone, bone_ref)`** compares the live bone with `style_defaults`. Anything but the expected shared widget is a hand edit to the shape.
- **`reset_style(context, pose_bone, bone_ref, props)`** sets the given properties back to `style_defaults`.
- **`BoneRef.palette`** records the palette the style's color resolved to, so a preference change that hasn't been reapplied doesn't make every bone look hand-colored.

### Reconfigure
`BoneStyleConfig.snapshot()` returns `{bone name: BoneStyleDiff}`. After each bone's style is applied in `apply_tool`, its `BoneStyleDiff` is applied on top. A shape is carried by object name; a name that no longer exists is skipped.

## UI (`operators/widgets.py`)
- **Custom Shape panel** (appended to `BONE_PT_display_custom_shape`):
  - **Shared Widget:** which bones use it, or "N bones" past `NAMED_BONES_MAX`.
  - **Edited:** the checkbox names of everything edited on the active bone, including Widget Mesh.
  - **Reset to Default** button.
- **Pose mode right-click:** Reset Style to Default.
- **3D View header:** a red warning while a shared widget is in Edit Mode.
- **Reset to Default** (`RIG_OT_reset_bone_style`):
  - **Checkboxes:** Widget, Widget Mesh, Color, Translation, Rotation, Scale, Wire Width, Override Transform, Display (Wireframe and Scale to Bone Length). All on by default; Blender remembers the last choice.
  - **Dialog every time, even for one edit.** The Properties editor has no redo panel. It shows only the checkboxes with something edited on the selected bones.
  - **Greyed out by `poll`** when nothing on the selected bones is edited. Checks every selected bone (`styled_bone_refs` dict, stops at the first edit).
  - **Widget Mesh** restores each shared widget once, and only if its hash doesn't match. The report names the widgets restored. A user's own object is unassigned, never deleted.
  - **`RESET_OPTIONS`** maps each checkbox to its label and the settings it resets. It's the one table behind the checkboxes, "Edited:" and the dialog.
- **Data viewer, Widgets subpanel** (`data_viewer/panel.py`): count of unused widgets, and **Clear Unused Widgets** (`RIG_OT_clear_unused_widgets`) with a Delete dialog listing them (up to `LISTED_WIDGETS_MAX`). It only deletes tagged RigTools widgets that no bone on any rig uses. It's not a Check Data fix, because fixes promise never to delete objects.
- **Not doing:** a ✓ "edits kept" signal row (replaced by Edited + Reset), a right-click per-field reset (the dialog covers it), Make Unique.

## Learned
- **RNA defaults aren't reliable.** `PoseBone.bl_rna.properties[...].default` doesn't match a new bone's values, so Blender defaults are hardcoded in `CUSTOM_SHAPE_PROPS`.
- **`show_wire` lives on `Bone`**, not `PoseBone` (`BONE_PROPS`).
- **`SplineIK` registered bones twice**; the duplicate `extend()` calls are removed. `MechanismBones.add` still doesn't check for duplicates.
- **An operator's own properties aren't in `cls.bl_rna.properties`.** Reading checkbox labels from there raised a KeyError that hid the whole panel section. Errors in appended draw functions only show in the system console.
- **A misspelled property option (`option=` for `options=`)** stops Blender registering every property after it.
- **Blender loads the installed copy** in `AppData\...\addons\rigtools`. Rebuild before testing. Background tests must put the repo first on `sys.path` and drop the addons folders, or they test the installed copy.
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
Then: change a bone's wire width, color and scale, and check that "Edited" lists them and Reset clears them. Edit a shared widget's mesh, check that "Widget Mesh" appears on every bone using it, and that Reset restores it once.

## Notes
- Blender has two bone colors, Bone and Pose Bone. RigTools sets the Pose Bone color; changing the Bone color does nothing in Pose Mode. Worth a line in the docs.
- Reapply Bone Colors goes through every armature, so `context.object` isn't always the rig. It reads settings directly on purpose.

## Open question
- Silent or a summary on reconfigure? The leaning is silent. One option is a single INFO line, such as "Kept hand edits on 12 bones; 2 no longer exist."
