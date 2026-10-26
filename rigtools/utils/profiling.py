import cProfile
import pstats
from contextlib import contextmanager

# Developer switch: when True, wrapped code prints a cProfile report to the system console
PROFILING_ENABLED = False

@contextmanager
def profile(limit=25):
	if not PROFILING_ENABLED:
		yield
		return

	profiler = cProfile.Profile()
	profiler.enable()
	try:
		yield
	finally:
		profiler.disable()
		pstats.Stats(profiler).sort_stats('cumulative').print_stats(limit)
