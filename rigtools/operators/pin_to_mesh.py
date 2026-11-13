import bpy
from bpy.props import EnumProperty
from mathutils.bvhtree import BVHTree
from mathutils.geometry import area_tri
from rigtools.preferences import get_preferences
from rigtools.rig_ui.rig_ui import get_related_meshes
from rigtools.utils.bone import duplicate_bone
from rigtools.utils.bone_collection import ensure_bone_collection
from rigtools.utils.naming import name_bone

PIN_CONSTRAINT_NAME = "Pin to Mesh"

def calc_barycentric_weights(point, a, b, c):
	"""How much point leans toward each corner of triangle abc: three weights summing to 1.
	A corner's weight is the area of the triangle the point makes with the other two corners,
	out of the whole triangle's area."""
	total = area_tri(a, b, c)
	if total < 1e-12:
		# A collapsed triangle has no area to divide by: lean fully on the nearest corner
		corners = (a, b, c)
		nearest = min(range(3), key=lambda i: (point - corners[i]).length)
		return tuple(1.0 if i == nearest else 0.0 for i in range(3))
	return (
		area_tri(point, b, c) / total,
		area_tri(a, point, c) / total,
		area_tri(a, b, point) / total
	)

def find_closest_anchor(mesh_obj, world_point):
	"""Finds the triangle on the mesh closest to the given world-space point.
	Returns (world distance, {vertex index: weight}) for the triangle's vertices, or None if
	the mesh has no faces. Uses the mesh's own data at rest, so the indices match its vertex groups."""
	mesh = mesh_obj.data
	mesh.calc_loop_triangles()
	triangles = [tuple(tri.vertices) for tri in mesh.loop_triangles]
	positions = [v.co for v in mesh.vertices]
	tree = BVHTree.FromPolygons(positions, triangles)

	local_point = mesh_obj.matrix_world.inverted() @ world_point
	closest, _normal, triangle_index, _distance = tree.find_nearest(local_point)
	if triangle_index is None:
		return None

	corners = triangles[triangle_index]
	corner_positions = [mesh.vertices[i].co for i in corners]
	weights = calc_barycentric_weights(closest, *corner_positions)
	# find_nearest's own distance is in this mesh's space; scale would skew comparisons
	distance = (mesh_obj.matrix_world @ closest - world_point).length
	return distance, {index: weight for index, weight in zip(corners, weights) if weight > 1e-6}

def sort_meshes_by_distance(meshes, world_point):
	"""[(distance, mesh_obj, weights)], sorted nearest first."""
	hits = []
	for mesh_obj in meshes:
		hit = find_closest_anchor(mesh_obj, world_point)
		if hit is not None:
			distance, weights = hit
			hits.append((distance, mesh_obj, weights))
	hits.sort(key=lambda h: h[0])
	return hits

def get_pinnable_meshes(armature_obj, view_layer):
	"""Returns a list of mesh objects that can be pinned to by the given armature."""
	return [m for m in get_related_meshes(armature_obj, view_layer) if m.visible_get()]

def bone_rest_head(armature_obj, bone_name):
	"""The bone's head at rest, in world space. Rest, not posed: the mesh is searched at rest
	too, and pinning a posed control shouldn't move its anchor"""
	return armature_obj.matrix_world @ armature_obj.data.bones[bone_name].head_local

# Blender keeps only pointers into these strings: if the list is freed, the labels turn to garbage
_mesh_items_cache = []

def mesh_items(self, context):
	global _mesh_items_cache
	items = []
	armature_obj = context.object
	if armature_obj and armature_obj.type == 'ARMATURE':
		items += [(m.name, m.name, "") for m in get_pinnable_meshes(armature_obj, context.view_layer)]
	# An enum can't be empty
	_mesh_items_cache = items or [('NONE', "No visible mesh", "")]
	return _mesh_items_cache

def fill_anchor_group(mesh_obj, anchor_name, vertex_weights):
	"""Creates the anchor vertex group and fills it with the given weights.
	Overwrites existing vertex group if it exists. Returns the vertex group."""
	group = mesh_obj.vertex_groups.get(anchor_name)
	if group is None:
		group = mesh_obj.vertex_groups.new(name=anchor_name)
	else:
		group.remove([v.index for v in mesh_obj.data.vertices])

	for index, weight in vertex_weights.items():
		group.add([index], weight, 'REPLACE')
	return group

def create_vis_bone(armature_obj, control_name, vis_name):
	"""Adds the VIS bone in edit mode: a copy of the control (same length, roll and parent,
	so the widget keeps its size and turns with the head), non-deforming, in the hidden MCH
	collection. Leaves the armature in pose mode. Bone references from before are invalid after"""
	armature_data = armature_obj.data
	bpy.ops.object.mode_set(mode='EDIT')
	edit_bones = armature_data.edit_bones
	vis_bone = duplicate_bone(armature_data, edit_bones[control_name], vis_name, 1.0)
	vis_bone.use_deform = False
	for coll in list(vis_bone.collections):
		coll.unassign(vis_bone)
	mch_coll = ensure_bone_collection(armature_data, get_preferences().mch_collection_name, hidden=True)
	if mch_coll:
		mch_coll.assign(vis_bone)
	bpy.ops.object.mode_set(mode='POSE')

def pin_constraint(vis, mesh_obj, anchor_name):
	"""The VIS bone's Copy Location to the anchor group, added or retargeted on a re-pin"""
	constraint = vis.constraints.get(PIN_CONSTRAINT_NAME)
	if constraint is None:
		constraint = vis.constraints.new('COPY_LOCATION')
		constraint.name = PIN_CONSTRAINT_NAME
	constraint.target = mesh_obj
	constraint.subtarget = anchor_name
	return constraint

def find_pin(pose_bone):
	"""The VIS bone pinning this control, or None"""
	vis = pose_bone.custom_shape_transform
	if vis is not None and PIN_CONSTRAINT_NAME in vis.constraints:
		return vis
	return None

class RIG_OT_pin_to_mesh(bpy.types.Operator):
	"""Draw this control's widget on the mesh surface: a VIS bone follows the mesh, and the
	control's widget is drawn at it. The control itself stays at rest"""
	bl_idname = "rig.pin_to_mesh"
	bl_label = "Pin to Mesh"
	bl_options = {'REGISTER', 'UNDO'}

	mesh: EnumProperty(
		name="Mesh",
		items=mesh_items,
		options={'SKIP_SAVE'},
		description="The mesh object for the pin to follow"
	)

	vertex_selection: EnumProperty(
		name="Vertex Selection",
		items=[
			('NEAREST', "Nearest", "Pin to the nearest point on the mesh"),
			('EDIT_SELECTION', "Edit Selection", "Pin to the vertices last selected in edit mode"),
		],
		default='NEAREST',
		description="How to select the vertices to pin to"
	)

	@classmethod
	def poll(cls, context):
		return (context.mode == 'POSE'
			and context.active_pose_bone is not None)

	def invoke(self, context, event):
		# Only on the click, not on redo: the redo panel then shows the mesh it picked
		armature_obj = context.object
		head = bone_rest_head(armature_obj, context.active_pose_bone.name)
		meshes = sort_meshes_by_distance(get_pinnable_meshes(armature_obj, context.view_layer), head)
		if not meshes:
			self.report({'ERROR'}, "No visible meshes connected to this armature")
			return {'CANCELLED'}
		self.mesh = meshes[0][1].name
		return self.execute(context)

	def execute(self, context):
		armature_obj = context.object
		if not armature_obj or armature_obj.type != 'ARMATURE':
			self.report({'ERROR'}, "Select an armature object")
			return {'CANCELLED'}

		pose_bone = context.active_pose_bone
		if not pose_bone:
			self.report({'ERROR'}, "No active pose bone selected")
			return {'CANCELLED'}
		# pose_bone is invalid after a mode switch: keep names
		control_name = pose_bone.name
		vis_name = name_bone("vis", control_name)
		anchor_name = name_bone("anchor", control_name)

		if PIN_CONSTRAINT_NAME in pose_bone.constraints:
			self.report({'ERROR'}, f"'{control_name}' is a VIS bone: select the control it pins")
			return {'CANCELLED'}
		# Nothing may depend on a VIS bone: a child of it is a real cycle, and the follow breaks
		if pose_bone.parent and pose_bone.parent.name == vis_name:
			self.report({'ERROR'}, f"'{control_name}' is parented to '{vis_name}': that's a dependency cycle")
			return {'CANCELLED'}

		mesh_obj = bpy.data.objects.get(self.mesh)
		if not mesh_obj or mesh_obj.type != 'MESH':
			self.report({'ERROR'}, f"Mesh object '{self.mesh}' not found")
			return {'CANCELLED'}

		if self.vertex_selection == 'EDIT_SELECTION':
			weights = {v.index: 1.0 for v in mesh_obj.data.vertices if v.select}
			if not weights:
				self.report({'ERROR'}, f"No vertices selected on '{mesh_obj.name}': select them in edit mode first")
				return {'CANCELLED'}
		else:
			hit = find_closest_anchor(mesh_obj, bone_rest_head(armature_obj, control_name))
			if hit is None:
				self.report({'ERROR'}, f"'{mesh_obj.name}' has no faces to pin to")
				return {'CANCELLED'}
			weights = hit[1]

		# An armature modifier treats a group named like a bone as that bone's: a cycle
		if anchor_name in armature_obj.data.bones:
			self.report({'ERROR'}, f"A bone is named '{anchor_name}': the anchor group can't share it.")
			return {'CANCELLED'}

		fill_anchor_group(mesh_obj, anchor_name, weights)

		if vis_name not in armature_obj.data.bones: # re-pinning reuses it
			create_vis_bone(armature_obj, control_name, vis_name)

		vis = armature_obj.pose.bones[vis_name]
		control = armature_obj.pose.bones[control_name]
		pin_constraint(vis, mesh_obj, anchor_name)
		control.custom_shape_transform = vis

		self.report({'INFO'}, f"Pinned '{control_name}' to '{mesh_obj.name}'")
		return {'FINISHED'}

class RIG_OT_unpin_from_mesh(bpy.types.Operator):
	"""Stop drawing this control's widget on the mesh: removes its VIS bone and anchor group"""
	bl_idname = "rig.unpin_from_mesh"
	bl_label = "Unpin from Mesh"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(cls, context):
		return (context.mode == 'POSE' and context.active_pose_bone is not None
			and find_pin(context.active_pose_bone) is not None)

	def execute(self, context):
		armature_obj = context.object
		control = context.active_pose_bone
		control_name = control.name
		vis = find_pin(control)
		vis_name = vis.name
		constraint = vis.constraints[PIN_CONSTRAINT_NAME]
		mesh_obj, anchor_name = constraint.target, constraint.subtarget

		control.custom_shape_transform = None
		if mesh_obj is not None and anchor_name in mesh_obj.vertex_groups:
			mesh_obj.vertex_groups.remove(mesh_obj.vertex_groups[anchor_name])

		# Removing a bone needs edit mode; control and vis are invalid after this
		bpy.ops.object.mode_set(mode='EDIT')
		edit_bones = armature_obj.data.edit_bones
		edit_bones.remove(edit_bones[vis_name])
		bpy.ops.object.mode_set(mode='POSE')

		self.report({'INFO'}, f"Unpinned '{control_name}'")
		return {'FINISHED'}

classes = (
	RIG_OT_pin_to_mesh,
	RIG_OT_unpin_from_mesh,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
