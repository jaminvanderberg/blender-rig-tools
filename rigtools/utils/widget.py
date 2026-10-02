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
		verts.append((math.cos(angle) * 0.5, 0.5, math.sin(angle) * 0.5))
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

def create_box_widget(widget_name, collection, size_x=0.85, size_y=1.0, size_z=0.4):
	hx, hz = size_x * 0.5, size_z * 0.5
	verts = [
		(-hx, 0, -hz),
		( hx, 0, -hz),
		( hx, size_y, -hz),
		(-hx, size_y, -hz),
		(-hx, 0,  hz),
		( hx, 0,  hz),
		( hx, size_y,  hz),
		(-hx, size_y,  hz),
	]
	edges = [
		(0, 1), (1, 2), (2, 3), (3, 0),
		(4, 5), (5, 6), (6, 7), (7, 4),
		(0, 4), (1, 5), (2, 6), (3, 7),
	]
	mesh = bpy.data.meshes.new(widget_name)
	mesh.from_pydata(verts, edges, [])
	mesh.update()
	wgt = bpy.data.objects.new(widget_name, mesh)
	collection.objects.link(wgt)
	return wgt

def create_rectangle_widget(widget_name, collection, width = 0.15, height = 0.90):
	verts = [
		(0.0, (1.0 - height)/2, -width/2),
		(0.0, (1.0 - height)/2, width/2),
		(0.0, (1.0 + height)/2, width/2),
		(0.0, (1.0 + height)/2, -width/2),
	]
	edges = [(0, 1), (1, 2), (2, 3), (3, 0)]
	mesh = bpy.data.meshes.new(widget_name)
	mesh.from_pydata(verts, edges, [])
	mesh.update()
	wgt = bpy.data.objects.new(widget_name, mesh)
	collection.objects.link(wgt)
	return wgt

def create_fk_shape_widget(widget_name, collection, radius = 0.25):
	verts = [(0.0, 0.0, 0.0), (0.0, 1.0, 0.0)]
	edges = [(0, 1)]

	segments = 16
	
	for i in range(segments):
		angle = (2 * math.pi * i) / segments
		verts.append((math.cos(angle) * radius, 0.5, math.sin(angle) * radius))
		edges.append((i + 2, (i + 1) % segments + 2))	

	mesh = bpy.data.meshes.new(widget_name)
	mesh.from_pydata(verts, edges, [])
	mesh.update()
	wgt = bpy.data.objects.new(widget_name, mesh)
	collection.objects.link(wgt)
	return wgt

fk_widget_types = [
	('CIRCLE', 'Circle', 'Create a circle widget'),
	('RECTANGLE', 'Rectangle', 'Create a rectangle widget'),
	('FK', 'FK Shape', 'Create a FK widget'),
	('BOX', 'Box', 'Create a box widget'),
	('NONE', 'None', 'No widget'),
]

def create_fk_widget(widget_type, widget_name, collection):
	match widget_type:
		case 'CIRCLE':
			return create_circle_widget(widget_name, collection)
		case 'RECTANGLE':
			return create_rectangle_widget(widget_name, collection)
		case 'FK':
			return create_fk_shape_widget(widget_name, collection)
		case 'BOX':
			return create_box_widget(widget_name, collection)
		case _:
			return None

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


def create_chest_widget(widget_name, collection):
	verts = [
        (0.000000, -0.745914, -0.118223),
        (-0.195090, -0.731528, -0.100247),
        (-0.382683, -0.688923, -0.043049),
        (-0.555570, -0.619737, 0.060735),
        (-0.707107, -0.526628, 0.181042),
        (-0.831470, -0.413175, 0.298476),
        (-0.923880, -0.283737, 0.392751),
        (-0.980785, -0.143288, 0.461894),
        (-1.000000, 0.002773, 0.488856),
        (-0.980785, 0.148835, 0.461894),
        (-0.923880, 0.289284, 0.392751),
        (-0.831470, 0.418722, 0.298476),
        (-0.707107, 0.532175, 0.181043),
        (-0.555570, 0.625284, 0.060735),
        (-0.382683, 0.694470, -0.043049),
        (-0.195090, 0.737075, -0.100247),
        (0.000000, 0.751461, -0.118223),
        (0.195090, 0.737075, -0.100247),
        (0.382683, 0.694470, -0.043049),
        (0.555570, 0.625284, 0.060735),
        (0.707107, 0.532175, 0.181043),
        (0.831470, 0.418722, 0.298476),
        (0.923880, 0.289284, 0.392751),
        (0.980785, 0.148835, 0.461894),
        (1.000000, 0.002773, 0.488856),
        (0.980785, -0.143288, 0.461894),
        (0.923880, -0.283737, 0.392751),
        (0.831470, -0.413175, 0.298476),
        (0.707107, -0.526628, 0.181042),
        (0.555570, -0.619737, 0.060735),
        (0.382683, -0.688923, -0.043049),
        (0.195090, -0.731528, -0.100247),
	]
	edges = [
        (1, 0),
        (2, 1),
        (3, 2),
        (4, 3),
        (5, 4),
        (6, 5),
        (7, 6),
        (8, 7),
        (9, 8),
        (10, 9),
        (11, 10),
        (12, 11),
        (13, 12),
        (14, 13),
        (15, 14),
        (16, 15),
        (17, 16),
        (18, 17),
        (19, 18),
        (20, 19),
        (21, 20),
        (22, 21),
        (23, 22),
        (24, 23),
        (25, 24),
        (26, 25),
        (27, 26),
        (28, 27),
        (29, 28),
        (30, 29),
        (31, 30),
        (0, 31),
	]
	mesh = bpy.data.meshes.new(widget_name)
	mesh.from_pydata(verts, edges, [])
	mesh.update()
	wgt = bpy.data.objects.new(widget_name, mesh)
	collection.objects.link(wgt)
	return wgt	

"""
import bpy

obj = bpy.context.object
mesh = obj.data

# Apply object scale/rotation into verts so the dump matches what you see
mesh.transform(obj.matrix_world)
obj.matrix_world.identity()
mesh.update()

print("verts = [")
for v in mesh.vertices:
    print(f"\t({v.co.x:.6f}, {v.co.y:.6f}, {v.co.z:.6f}),")
print("]")

print("edges = [")
for e in mesh.edges:
    print(f"\t({e.vertices[0]}, {e.vertices[1]}),")
print("]")
"""