class ChainBranchingError(Exception):
	"""Creates FK/Tweak chain from an existing bone chain."""
	pass

def find_chains_from_selection(context):
	selected_bones = set(context.selected_editable_bones)
	if not selected_bones:
		return []
	
	heads = [
		bone for bone in selected_bones
		if bone.parent is None or bone.parent not in selected_bones
	]
	chains = []
	
	def walk_chain(current_bone, current_chain):
		current_chain.append(current_bone.name)
		selected_children = [c for c in current_bone.children if c in selected_bones]
		
		if len(selected_children) > 1:
			raise ChainBranchingError(
				f"Branching detected at bone '{current_bone.name}'. All bones must have only one selected child."
			)
		elif len(selected_children) == 0:
			chains.append(current_chain)
			return

		walk_chain(selected_children[0], current_chain)
		
	for head in heads:
		walk_chain(head, [])
		
	return chains