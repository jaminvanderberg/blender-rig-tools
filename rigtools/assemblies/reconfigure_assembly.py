from rigtools.assemblies.delete_assembly import delete_assembly
from rigtools.assemblies.assembly_data import find_assembly
from rigtools.assemblies.config_registry import snapshot_configs

def reconfigure_assembly(context, assembly_uid, recreate_func):
	stash = {}
	if assembly_uid:
		old = find_assembly(context.object, assembly_uid)
		if old: stash = snapshot_configs(context, old)
		delete_assembly(context, assembly_uid)
	return recreate_func(stash)