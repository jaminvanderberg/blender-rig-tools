class ReparentRules:
	def __init__(self):
		self._items = []

	def __iter__(self):
		return iter(self._items)

	def add(self, from_bone, to_bone):
		self._items.append((from_bone, to_bone))

def apply_reparent_rule(armature_data, from_bone, to_bone, *, forward: bool):
	edit_bones = armature_data.edit_bones
	src = to_bone if forward else from_bone
	dst = from_bone if forward else to_bone

	src_bone = edit_bones[src]
	dst_bone = edit_bones[dst]

	moved = []
	for child in list(src_bone.children):
		child.use_connect = False
		child.parent = dst_bone
		print(f"  reparent {child.name} -> {dst_bone.name}")
		moved.append(child.name)

	old, new = (to_bone, from_bone) if forward else (from_bone, to_bone)
	for assembly in armature_data.rigtools_assemblies:
		for state in list(assembly.org_states) + list(assembly.twist_states):
			if state.name in moved and state.parent == old:
				state.parent = new
