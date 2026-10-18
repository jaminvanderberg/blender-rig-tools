class ReparentRules:
	def __init__(self):
		self._items = []

	def __iter__(self):
		return iter(self._items)

	def add(self, from_bone, to_bone):
		self._items.append((from_bone, to_bone))