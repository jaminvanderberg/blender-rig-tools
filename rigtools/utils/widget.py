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