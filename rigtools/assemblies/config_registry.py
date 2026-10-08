from rigtools.assemblies.configs.skirt_ride import SkirtRideConfig


CONFIGS = {
	SkirtRideConfig.id: SkirtRideConfig,
}

def iterate_configs(assembly):
	for config in CONFIGS.values():
		if config.present(assembly):
			yield config