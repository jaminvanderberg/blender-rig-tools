import bpy
import re
from rigtools.preferences import get_separators

def get_base_name(bone_name) -> tuple[str, str]:
    symmetry_pattern = r'(\.[LR]|\_[LR])(\.\d+)?$'
    match = re.search(symmetry_pattern, bone_name, re.IGNORECASE)
    
    if match:
        base_name = bone_name[:match.start()]
        extension = match.group(0)
    else:
        base_name = bone_name
        extension = ""

    return base_name, extension

def bone_name_matches(bone_name, prefix, suffix):
    base_name, extension = get_base_name(bone_name)
    if len(base_name) <= len(prefix) + len(suffix):
        return False
    return base_name.startswith(prefix) and base_name.endswith(suffix)

def generate_bone_name(org_name, template, strip_name=True):
    name = org_name
    base_name, extension = get_base_name(name)    

    if strip_name:
        prefixes = ["ORG-", "DEF-", "MCH-", "CTRL-", "ctrl-", "org-", "def-", "mch-",
                    "ORG_", "DEF_", "MCH_", "CTRL_", "ctrl_", "org_", "def_", "mch_",
                    "ORG.", "DEF.", "MCH.", "CTRL.", "ctrl.", "org.", "def.", "mch."]
        for p in prefixes:
            if base_name.startswith(p):
                base_name = base_name[len(p):]

        suffixes = ["-ORG", "-DEF", "-MCH", "-CTRL", "-ctrl", "-org", "-def", "-mch",
                    "_ORG", "_DEF", "_MCH", "_CTRL", "_ctrl", "_org", "_def", "_mch",
                    ".ORG", ".DEF", ".MCH", ".CTRL", ".ctrl", ".org", ".def", ".mch"]
        for s in suffixes:
            if base_name.endswith(s):
                base_name = base_name[:-len(s)]
        
    if "{name}" not in template:
        # Gentle fallback behavior for when {name} is missing.
        # If it starts with a separator, assume the used just mean a suffix
        separators = tuple(get_separators())
        if template.startswith(separators):
            template = f"{{name}}{template}"
        else:
            # Otherwise, we just assume it's a prefix.
            # empty string template will just return the same bone name,
            # which is probably fine
            template = f"{template}{{name}}"
            
    formatted_base = template.format(name=base_name)
    
    return f"{formatted_base}{extension}"

def duplicate_bone(armature_data, bone, name, scale, copy_collections=True):
    new_bone = armature_data.edit_bones.new(name)

    direction = (bone.tail - bone.head).normalized()
    
    new_bone.head = bone.head
    new_bone.tail = bone.head + (direction * bone.length * scale)

    new_bone.parent = bone.parent
    # intentionally not copying connected status

    connected = bone.use_connect
    # we need to disconnect the bone so that the roll calculates properly
    bone.use_connect = False
    
    new_bone.roll = bone.roll

    bone.use_connect = connected

    if copy_collections:
        for coll in bone.collections:
            coll.assign(new_bone)

    return new_bone
            
def is_bone_visible(bone):
    if bone.hide:
        return False
    
    data_bone = getattr(bone, "bone", bone)
    
    if hasattr(data_bone, "collections"):
        if not data_bone.collections:
            return True
        return any(coll.is_visible for coll in data_bone.collections)
    
    armature = data_bone.id_data if hasattr(data_bone, "id_data") else None
    if armature and hasattr(armature, "layers"):
        return any(b_layer and a_layer for b_layer, a_layer in zip(data_bone.layers, armature.layers))
    
    return True


def is_collection_visible(collection, armature_data):
    if collection:
        return collection.is_visible_effectively
    return not armature_data.collections.is_solo_active