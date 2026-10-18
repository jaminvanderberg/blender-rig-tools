from rigtools.assemblies.delete_assembly import delete_assembly
from rigtools.assemblies.assembly_data import find_assembly
from rigtools.assemblies.config_registry import snapshot_configs

def prepare_rebuild(context, assembly_uid):
	prior_configs = {}
	if assembly_uid:
		old = find_assembly(context.object, assembly_uid)
		if old: prior_configs = snapshot_configs(context, old)
		delete_assembly(context, assembly_uid)
	return prior_configs