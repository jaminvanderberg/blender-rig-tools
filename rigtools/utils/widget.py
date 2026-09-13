import bpy
import math
###########################################################################################################
# Widget creation

def get_widget_collection(context, collection_name):
	coll = bpy.data.collections.get(collection_name)
	if not coll:
		coll = bpy.data.collections.new(collection_name)
		context.scene.collection.children.link(coll)
		coll.hide_viewport = True
		coll.hide_render = True
	return coll

def create_sphere_widget(widget_name, collection):    
	verts = []
	edges = []
	segments = 12
	
	for axis in ['XY', 'XZ', 'YZ']:
		start_idx = len(verts)
		for i in range(segments):
			angle = (2 * math.pi * i) / segments
			cos_a = math.cos(angle) * 0.5
			sin_a = math.sin(angle) * 0.5
			
			match axis:
				case 'XY':
					verts.append((cos_a, sin_a, 0.0))
				case 'XZ':
					verts.append((cos_a, 0.0, sin_a))
				case 'YZ':
					verts.append((0.0, cos_a, sin_a))
					
			next_i = (i + 1) % segments
			edges.append((start_idx + i, start_idx + next_i))
			
	mesh = bpy.data.meshes.new(widget_name)
	mesh.from_pydata(verts, edges, [])
	mesh.update()
	
	wgt = bpy.data.objects.new(widget_name, mesh)
	collection.objects.link(wgt)
	
	return wgt

def create_circle_widget(widget_name, collection):
	verts = []
	edges = []
	segments = 16
	
	for i in range(segments):
		angle = (2 * math.pi * i) / segments
		verts.append((math.cos(angle) * 0.5, 0.0, math.sin(angle) * 0.5))
		edges.append((i, (i + 1) % segments))
		
	mesh = bpy.data.meshes.new(widget_name)
	mesh.from_pydata(verts, edges, [])
	mesh.update()
	
	wgt = bpy.data.objects.new(widget_name, mesh)
	collection.objects.link(wgt)
	return wgt

def create_line_widget(widget_name, collection):
	verts = [(0.0, 0.0, 0.0), (0.0, 1.0, 0.0)]
	edges = [(0, 1)]

	mesh = bpy.data.meshes.new(widget_name)
	mesh.from_pydata(verts, edges, [])
	mesh.update()

	wgt = bpy.data.objects.new(widget_name, mesh)
	collection.objects.link(wgt)
	return wgt

def create_twist_widget(widget_name, collection):
	"""Two parallel arc rings with opposing Vs in each gap:  > <  """
	verts = [
		(-0.191342, 0.054932, -0.461940),
		(-0.277785, 0.054932, -0.415735),
		(-0.353553, 0.054932, -0.353553),
		(-0.415735, 0.054932, -0.277785),
		(-0.461940, 0.054932, -0.191342),
		(-0.461940, 0.054932, 0.191342),
		(-0.415735, 0.054932, 0.277785),
		(-0.353553, 0.054932, 0.353553),
		(-0.277785, 0.054932, 0.415735),
		(-0.191342, 0.054932, 0.461940),
		(0.191342, 0.054932, -0.461940),
		(0.277785, 0.054932, -0.415735),
		(0.353553, 0.054932, -0.353553),
		(0.415735, 0.054932, -0.277785),
		(0.461940, 0.054932, -0.191342),
		(0.461940, 0.054932, 0.191342),
		(0.415735, 0.054932, 0.277785),
		(0.353553, 0.054932, 0.353553),
		(0.277785, 0.054932, 0.415735),
		(0.191342, 0.054932, 0.461940),
		(0.191342, -0.054932, -0.461940),
		(0.277785, -0.054932, -0.415735),
		(0.353553, -0.054932, -0.353553),
		(-0.191342, -0.054932, -0.461940),
		(-0.277785, -0.054932, -0.415735),
		(-0.353553, -0.054932, -0.353553),
		(-0.415735, -0.054932, -0.277785),
		(-0.461940, -0.054932, -0.191342),
		(-0.461940, -0.054932, 0.191342),
		(-0.415735, -0.054932, 0.277785),
		(-0.353553, -0.054932, 0.353553),
		(-0.277785, -0.054932, 0.415735),
		(-0.191342, -0.054932, 0.461940),
		(0.415735, -0.054932, -0.277785),
		(0.461940, -0.054932, -0.191342),
		(0.461940, -0.054932, 0.191342),
		(0.415735, -0.054932, 0.277785),
		(0.353553, -0.054932, 0.353553),
		(0.277785, -0.054932, 0.415735),
		(0.191342, -0.054932, 0.461940),
		(0.097545, -0.000000, -0.490393),
		(0.490393, -0.000000, -0.097545),
		(0.490393, 0.000000, 0.097545),
		(0.097545, 0.000000, 0.490393),
		(-0.097545, -0.000000, -0.490393),
		(-0.490393, -0.000000, -0.097545),
		(-0.490393, 0.000000, 0.097545),
		(-0.097545, 0.000000, 0.490393),
	]
	edges = [
		(1, 0),
		(2, 1),
		(3, 2),
		(4, 3),
		(6, 5),
		(7, 6),
		(8, 7),
		(9, 8),
		(11, 10),
		(12, 11),
		(13, 12),
		(14, 13),
		(16, 15),
		(17, 16),
		(18, 17),
		(19, 18),
		(20, 40),
		(21, 20),
		(22, 21),
		(33, 22),
		(23, 44),
		(24, 23),
		(25, 24),
		(26, 25),
		(27, 26),
		(29, 28),
		(30, 29),
		(31, 30),
		(32, 31),
		(28, 46),
		(5, 46),
		(34, 33),
		(36, 35),
		(37, 36),
		(38, 37),
		(39, 38),
		(35, 42),
		(15, 42),
		(10, 40),
		(14, 41),
		(34, 41),
		(19, 43),
		(39, 43),
		(0, 44),
		(4, 45),
		(27, 45),
		(9, 47),
		(32, 47),
	]
	mesh = bpy.data.meshes.new(widget_name)
	mesh.from_pydata(verts, edges, [])
	mesh.update()
	wgt = bpy.data.objects.new(widget_name, mesh)
	collection.objects.link(wgt)
	return wgt
