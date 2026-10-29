import bpy
from rigtools.assemblies.configs.bone_styles import BoneStyleConfig
from rigtools.assemblies.delete_assembly import delete_assemblies
from rigtools.assemblies.assembly_data import find_assembly
from rigtools.assemblies.config_registry import snapshot_configs

def prepare_rebuild(context, assembly_uids):
	prior_configs = {
		uid: snapshot_configs(context, find_assembly(context.object, uid))
		for uid in assembly_uids
	}
	delete_assemblies(context, assembly_uids)
	return prior_configs