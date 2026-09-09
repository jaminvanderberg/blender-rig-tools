import json
import bpy
from bpy_extras.io_utils import ExportHelper, ImportHelper
from bpy.types import Operator
from bpy.props import StringProperty
from rigtools.preferences import get_preferences


class RIG_OT_export_preferences(Operator, ExportHelper):
    bl_idname = "rig.export_preferences"
    bl_label = "Export Preferences"
    bl_description = "Export Rig Tools preferences to a JSON file"

    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})
    filepath: StringProperty(default="rigtools_preferences.json", subtype='FILE_PATH')

    def execute(self, context):
        prefs = get_preferences(context)

        data = {}
        for prop in prefs.rna_type.properties:
            if not prop.is_readonly and prop.identifier != 'rna_type':
                data[prop.identifier] = getattr(prefs, prop.identifier)

        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

        self.report({'INFO'}, f"Exported {len(data)} settings to {self.filepath}")
        return {'FINISHED'}


class RIG_OT_import_preferences(Operator, ImportHelper):
    bl_idname = "rig.import_preferences"
    bl_label = "Import Preferences"
    bl_description = "Import Rig Tools preferences from a JSON file"

    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})
    filepath: StringProperty(subtype='FILE_PATH')

    def execute(self, context):
        prefs = get_preferences(context)

        with open(self.filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        valid_props = {
            prop.identifier for prop in prefs.rna_type.properties
            if not prop.is_readonly and prop.identifier != 'rna_type'
        }

        applied_count = 0
        for key, value in data.items():
            if key in valid_props:
                setattr(prefs, key, value)
                applied_count += 1

        self.report({'INFO'}, f"Imported {applied_count} settings from {self.filepath}")
        return {'FINISHED'}


classes = (
    RIG_OT_export_preferences,
    RIG_OT_import_preferences,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
