import cython
import math
import numpy as np
import numpy.ma as ma
from numpy import linalg as LA
import os,time
from pprint import pprint
from pxr import Usd, UsdGeom
from mathutils import Matrix,Vector,Euler
os.system('cls')
then = time.time()

#### USD functions ####
def read_path(file_path):
    """Create needed paths for the USD to get
    
    
    """
    
    path = os.path.splitext(file_path)
    base = os.path.basename(file_path)
    file_name = os.path.splitext(base)[0]

    blocklib_path = path[0]+'\\'+file_name+'_materials\\BlockLibrary.usda'
    world_name = os.path.basename(os.path.dirname(file_path))

    paths = {
        "file_path": file_path,
        "directory_filepath": path[0],
        "blocklib_filepath": blocklib_path,
        "file_name": file_name,
        "world_name": world_name,
    }

    return paths

def read_usd(paths):
    """Read the stage creation"""

    world_name = paths.get("world_name")
    world_str = str(world_name).replace(' ','_')
    usd_worldpath = '/'+world_str+'/VoxelMap'
    usd_blockpath = usd_worldpath+'/BlockLib'

    stage_ref = Usd.Stage.Open(paths.get("file_path"))
    block_ref = stage_ref.GetPrimAtPath(usd_blockpath+'/Blocks')
    voxel_ref = stage_ref.GetPrimAtPath(usd_worldpath)
    chunk_ref = voxel_ref.GetChildren()

    stage_dict = {
        "stage": stage_ref,
        "blocklib" :  block_ref,
        "chunk": chunk_ref,
        "voxelmap": voxel_ref,
        "world_path": usd_worldpath,
        "block_path": usd_blockpath,
    }
    return stage_dict

def read_chunk(usd_paths):
    """Reading though the chunks of the usd file
    'path' : reference path of blocks in the chunks
    'chunks' : chunks
    'points' : point postions 
    'indicies': block indicies to use for instancing
    """
    stage = usd_paths.get("stage")
    chunks = usd_paths.get("chunk")
    world_path = usd_paths.get("world_path")
    
    chunk_dict = {
        "chunks": [],
        "path" : [],
        "points" : [],
        "indices": []
    }

    for ch in chunks:
        chunk_name = str(ch).split(str(world_path))[1].split('>')[0]
        if 'Chunk' in chunk_name:            
            chunk_ref = stage.GetPrimAtPath(world_path + chunk_name)
            pos = chunk_ref.GetAttribute('positions').Get()
            id = chunk_ref.GetAttribute('protoIndices').Get()
            rel = chunk_ref.GetRelationship('prototypes')
            blocks_path = rel.GetTargets()
            
            chunk_dict['path'].append(blocks_path)
            chunk_dict['chunks'].append(chunk_name)
            chunk_dict['points'].append(pos) 
            chunk_dict['indices'].append(id)
            
    return chunk_dict

def read_block(usd_paths,chunks):
    """Read through the blocks of the chunks
    'path' : reference mesh path
    'block' : block name in number form
    'name': block real name
    'id' : the Minecraft block id
    'sub_id': the sub nbt id of that block 
    'instance' : object name block use for instancing 
    """
    stage = usd_paths.get("stage")
    usd_block_path = usd_paths.get("block_path")
    block_path = chunks.get("path")
    block_dict = {
        "block": [],
        "name" : [],
        "id": [],
        "sub_id": [],
        "path" : [],
        "instance": [],
        "grouped": []
    }

    for blocks in block_path:
        _full_name = []
        _name = []
        _id = []
        _sub_id = []
        _mesh = []
        _instance = []
        _group = []
        for block in blocks:  
            block_name = str(block).split(usd_block_path+'/Blocks')[1]  
            block_ref = stage.GetPrimAtPath(block)
            child_mesh = block_ref.GetChildren()
            name = block_ref.GetAttribute('typeName').Get()
            # blocks['name'].append(name)
            _full_name.append(block_name)
            _name.append(name)
            id = block_name.split("/Block_")[1].split('_')
            _id.append(int(id[0]))
            _sub_id.append(int(id[1]))
            _mesh.append(child_mesh)
            if len(child_mesh) >= 2: # instance pick 
                tmp_instance = [1,block_name]
#                tmp_group = 1
            else:
                tmp_instance = [0,block_name]
#                tmp_group = 0
#            _group.append(tmp_group)
            _instance.append(tmp_instance)
        # print(full_name)
        block_dict['block'].append(_full_name)
        block_dict['name'].append(_name)
        block_dict['id'].append(_id)
        block_dict['sub_id'].append(_sub_id)
        block_dict['path'].append(_mesh)
        block_dict['instance'].append(_instance)
#       block_dict['grouped'].append(_group)

    # print(block_dict.get("block_name"))
    return block_dict

def read_mesh(usd_paths,blocks):
    """ Read the block mesh
    'block' : a list meshes of blocks, some blocks can have multiple meshes
    'mesh' : a list of meshes used
    'material': a list of materials used
    'texture': a list of textures used and its path
    'instance': a list of name for referencing instance ['Block_1_0', 'stone']
    """
    stage = usd_paths.get("stage")
    usd_block_path = usd_paths.get("block_path")
    usd_blocklib_path = usd_paths.get("blocklib")

    _material = []
    _block = []
    _texture = []
    _mesh = []
    _instance = {}
    for blocks in usd_blocklib_path.GetChildren():
        meshes = blocks.GetChildren()
        for mesh in meshes:
            child_name = str(mesh).split(str(usd_block_path))[1].split('>')[0]
            child_path = str(usd_block_path)+child_name
            child_material = stage.GetPrimAtPath(child_path)
            # print(child_material)
            mat_rel = child_material.GetRelationship('material:binding')
            mat = mat_rel.GetTargets()   
            if not mat in _material and not mat == []:
                material = str(mat).split('Looks')
                material_path = usd_block_path+'/Blocks'+'/Looks'+material[1][:-3]
                material_ref = stage.GetPrimAtPath(material_path+'/diffuse_texture')
                diffuse = material_ref.GetProperty('inputs:file').Get()

                _material.append(mat)
                _texture.append(diffuse)
            if not 'Looks' in str(mesh):
                _mesh.append(mesh)
                mesh_inst = str(mesh).split('/Blocks')[1]
                block_inst = mesh_inst.split('/')
                _instance[block_inst[1]] = block_inst[2].strip('>)')
        _block.append(meshes)
        
    mesh_dict = {
        "block": _block,
        "mesh": _mesh,
        "material": _material,
        "texture": _texture,
        "instance": _instance,
    }
    return mesh_dict

#### Blender functions start here ####
def create_pts(paths,chunks,blocks):
    """Create points with attributes"""
    file_name = paths.get("file_name")  # file name
    ch = chunks.get("chunks")       # chunks
    points = chunks.get("points")       # points position
    indicies = chunks.get("indices")    # instance index
    id =  blocks.get("id")              # block index
    sub_id =  blocks.get("sub_id")      # block nbt index
    
    object_mesh = []
    for ic,chunk in enumerate(ch):
        mesh_name  = file_name+ ' - '+ 'PT_' +chunk.split('/')[1]
        if not bool(D.meshes.get(mesh_name)):
            mesh = D.meshes.new(mesh_name)  # add the new 
        else:
            mesh = D.meshes[mesh_name]
            D.meshes.remove(mesh,do_unlink=True) 
            mesh = D.meshes.new(mesh_name)
#        mesh.vertices.add(num_vertices)
#        mesh.vertices.foreach_set("co", vertices)
        
        bm = bmesh.new()   
        bm.to_mesh(mesh)   
#        
#        ins_index = bm.verts.layers.int.new("instance_index")
#        blo_index = bm.verts.layers.int.new("block_index")
#        nbt_index = bm.verts.layers.int.new("nbt_index")
#        print(id)
        
        a = np.array(points[ic])
        a[:,[1, 2]] = a[:,[2, 1]] #swaping Y and Z 
        e = a
        y = np.concatenate([np.array(i) for i in a])
        
    
        num_vertices = y.shape[0] // 3    
        
        mesh.vertices.add(num_vertices)
        mesh.vertices.foreach_set("co", y)
        
        
        
#        result = np.diff(a, axis = 1)
#        for ix,ex in enumerate(a):
#            for iy,ey in enumerate(a):
#                print(np.abs(np.diff(ex,ey],axis=1))) == 1)
#        print([e for e,i in enumerate(a)])
#        print(np.any(np.abs(np.diff([,v2],axis=1))) == 1)
#        print(indicies[ic])
        
#        print(id[ic])
        
        ins = indicies[ic]
        blo = [id[ic][i] for i in ins]
        sub = [sub_id[ic][i] for i in ins]
        ins_index = mesh.vertex_layers_int.new(name="instance_index")
        blo_index = mesh.vertex_layers_int.new(name="block_index")
        nbt_index = mesh.vertex_layers_int.new(name="nbt_index")
        ins_index.data.foreach_set("value", ins)
        blo_index.data.foreach_set("value", blo)
        nbt_index.data.foreach_set("value", sub)

        vertices = np.zeros(len(mesh.vertices) * 3,dtype=np.int32)
        mesh.vertices.foreach_get("co", vertices)
        vertices = vertices.reshape(-1,3)

        bm = bmesh.new()   
        bm.from_mesh(mesh)   
        min = Vector(tuple(np.min(vertices,0).tolist()))
        cloc =  min
        verts = sorted(bm.verts, key=lambda v: (v.co - cloc).length)

        for i, v in enumerate(verts):
            v.index = i
        bm.verts.sort()
        
        for v1 in vertices:
            for v2 in vertices:
                diff = sum(abs(a-b) for a,b in zip(v1,v2))
                try:
                    if diff == 1:
                        e = bm.edges.new([v1, v2])
                except:
                    pass
                    
        bm.to_mesh(mesh)
        bm.free()  
#        edges =np.zeros((len(mesh.edges)*2), dtype=np.int32)
        edges = np.array([
            0,1,
            0,2,
            0,3,
            1,4,
            1,6,
            1,8
        ], dtype=np.int32)
#        edges = np.random.randint(int(len(mesh.vertices)),size=2000)
#        h = np.any(np.abs(np.diff([v1,v2],axis=1))) == 1
#        r = np.random.randint(64, size=(1000, 3))
        
#        print(vertices)
#        h = np.diff(vertices, axis = 0)
#        v = vertices[::-1]

#        v = vertices
#        np.random.shuffle(v)

#        verts = np.concatenate((vertices,vertices))
#        z = v1[(v1>0)&(v2>0)] - v2[(v1>0)&(v2>0)]
#        c = z.reshape(-1,2)
#        print(verts)
        
#        z = np.linalg.norm(vertices-v,axis=-1)
#        z = np.abs(vertices[:,None] - v).sum(-1)
#        print(z, len(z))            
#        z = np.sum(np.abs(vertices[:,None]-v[:]),axis=-1)==1
        
#        print(z)
#        z = h.sum(axis=1) == 1
#        sum
#        x = np.argwhere(np.isin(vertices,r)).ravel()
#        pprint(z.tolist())
#        x = x.astype(int)
#        print(x)
        
#        num_edges = x.shape[0] // 2  
#        mesh.edges.add(num_edges)
#        mesh.edges.foreach_set("vertices", x)
        
        mesh.update()
        mesh.validate()
        
#        for i1,v1 in enumerate(a):
#            p = bm.verts.new([v1[0],v1[2],v1[1]])
#            bm.verts.ensure_lookup_table()
#            index = indicies[ic]
#            bm.verts[i1][ins_index] = index[i1]
#            bm.verts[i1][blo_index] = id[ic][index[i1]]
#            bm.verts[i1][nbt_index] = sub_id[ic][index[i1]]
#            for i2,v2 in  enumerate(a):
##                diff = abs(v1[0] - v2[0]) + abs(v1[1] - v2[1]) + abs(v1[2] - v2[2]) 
#                if np.any(np.abs(np.diff([v1,v2],axis=1))) == 1 and not np.any(v1 == v2):
#                    e = bm.edges.new([p, p[i2]])
#            for v2 in bm.verts:
#                diff = abs(v1.co[0] - v2.co[0]) + abs(v1.co[1] - v2.co[1]) + abs(v1.co[2] - v2.co[2])
#                if diff == 1 and not v1 == v2:
#                    e = bm.edges.new([v1, v2])

#        vertices = np.array([
#        1, 2, 0,
#        8, 0, 0,
#        5, 4, 0.9,
#        -2, 2, 0.2,
#        3, 9, 10,
#        2, -1, -1,
#        -5, -2, -1,
#        5, -5, -1,
#        2, -5, -1
#        ], dtype=np.float32)

#        edges = np.array([
#        0, 1,
#        0, 2,
#        0, 3,
#        1, 4,
#        1, 6,
#        1, 8,
#        1, 2,
#        0, 3,
#        3, 4,
#        2, 4,
#        3, 6,
#        1, 7,
#        6, 0
#        ], dtype=np.int32)

#        x = np.array([
#        2,
#        8,
#        5,
#        -2,
#        3,
#        2,
#        -5,
#        5,
#        2,
#        ], dtype=np.int32)


#        num_edges = edges.shape[0] // 2

#        mesh = bpy.data.meshes.new(name='created mesh')

#        mesh.vertices.add(num_vertices)
#        mesh.vertices.foreach_set("co", vertices)

#        a = mesh.vertex_layers_int.new(name="a")
#        #b = range(0,len(mesh.vertices))
#        try:
#        a.data.foreach_set("value", x)
#        except:
#        print('fail2')

#        mesh.edges.add(num_edges)
#        mesh.edges.foreach_set("vertices", edges)

#        mesh.update()
#        mesh.validate()

#        obj = bpy.data.objects.new('created object', mesh)
        
#        bm.to_mesh(mesh)
#        bm.free()
        object_mesh.append(mesh)
        
    return object_mesh

def create_collection(name,parent = None):
    #Create collection, if exist get it.
    if not bool(D.collections.get(name)):
        collection =  D.collections.new(name)
        if parent != None:
            parent.children.link(collection)
        else:
            C.scene.collection.children.link(collection)
    else:
        collection = D.collections[name]
    return collection

def moveto_collection(objects,collection):
    # Unlink objects in all collection, link it to new one 
    for obj in objects:
        for col in obj.users_collection:
            col.objects.unlink(obj) 
        collection.objects.link(obj)

def create_usd_collection(paths):
    """ Create collection to store usd and fix merged blocks
    Example: Grass Block is Block_2_0 need to merge all meshes
    dirt,grass_block_side,grass_block_top into one """
    # Create the USD collections
    collections = []
    file_name = paths.get("file_name")
    world_name = paths.get("world_name")
    
    usd_col = create_collection(file_name + " USD Collection")
    pt_col = create_collection(file_name + " USD Points",usd_col)
    block_col = create_collection(file_name + " USD BlockLib",usd_col)
    
    collections.append([usd_col,pt_col,block_col])
    
    if not bool(D.objects.get(file_name +' Blocks')):
        bpy.ops.wm.usd_import(filepath=filePath,import_usd_preview=True)
        
        objs = C.selected_objects
        moveto_collection(objs,block_col)
    
        #Fix all the block merge and apply 
        block_objs = block_col.objects['Blocks'].children_recursive
        rot = Matrix.Rotation(math.radians(90),4,'X')
        loc = Matrix.Translation((-0.5,-0.5,-0.5))
        
        path = ['Looks','Blocks','VoxelMap',world_name.replace(' ','_')]

        if D.objects[path[2]]:
            for child in D.objects[path[2]].children_recursive:
                D.objects.remove(child,do_unlink=True)
            D.objects.remove(D.objects[path[2]],do_unlink=True)
        for obj in D.objects:
            if obj.name in path and not 'Block' in obj.name:
                for child in obj.children_recursive:
                    child.name = file_name + ' '+ child.name
                obj.name =  file_name + ' '+obj.name
                     
        if bool(D.objects.get('Blocks')):
            obj = D.objects['Blocks']  
            obj.name =  file_name + ' '+obj.name
    

        new_i = 0
        row = 0
        column = 0
        for i,obj in enumerate(block_objs):
        
            pre_loc = Matrix.Translation((row,-2,column))
            try:
                if obj.type != 'MESH' and 'Block' in obj.name:
                    merge_mesh = D.meshes.new(obj.name + '_merge')
                    merge_obj = D.objects.new(merge_mesh.name, merge_mesh)
                    merge_obj.parent = obj.parent
                    merge_obj.location = obj.location
                    col = obj.users_collection[0]
                    col.objects.link(merge_obj)
                    
                    bpy.ops.object.select_all(action='DESELECT')
                    bpy.context.view_layer.objects.active = merge_obj
                    merge_obj.select_set(True)
                    for children_mesh in obj.children:
                        children_mesh.select_set(True)
                    
                    D.objects.remove(obj,do_unlink=True)                
                    bpy.ops.object.join()
                    
                    ma = rot @ loc
                    me = merge_obj.data
                    me.transform(ma)
                    
                    merge_obj.matrix_world = pre_loc
                elif obj.type == 'MESH':
                    
                    ma = rot @ loc
                    me = obj.data
                    me.transform(ma)
                    
                    obj.matrix_world = pre_loc
            except: # Except broken cause by previous merge RNA blocks
                new_i-=1
                pass
            new_i+=1
            row = new_i % 16
            column = math.floor(new_i / 16)

            
            
        
        fix_material(D.materials)
    return collections

def create_asset():
    """Create node group assets """
    if not bool(D.node_groups.get("Post_Surface")):
        surface = D.node_groups.new('Post_Surface','GeometryNodeTree')
        surface.inputs.new(type='NodeSocketGeometry',name='Geometry')
        surface.outputs.new(type='NodeSocketGeometry',name='Geometry')

    if not bool(D.objects.get('Empty')):
        mesh = D.meshes.new('EmptyMesh')
        D.objects.new('Empty',mesh)    

    if not bool(D.node_groups.get("Process")):
        process = D.node_groups.new('Process','GeometryNodeTree')
        process.inputs.new(type='NodeSocketGeometry',name='Geometry')
        process.outputs.new(type='NodeSocketGeometry',name='Instances')
        process.outputs.new(type='NodeSocketGeometry',name='Geometry')
        out_process= process.nodes.new('NodeGroupOutput')

        out_process.location = (800,0)

        in_process = process.nodes.new('NodeGroupInput')

        instanceNode = process.nodes.new('GeometryNodeInstanceOnPoints')
        instanceNode.inputs[3].default_value = True
        instanceNode.location = (300,0)
        instanceNode.mute = True

        rerouteNode = process.nodes.new('NodeReroute')
        rerouteNode.location = (280,-25)

        process.links.new(rerouteNode.inputs[0],in_process.outputs[0])
        process.links.new(out_process.inputs[1],rerouteNode.outputs[0])
        process.links.new(instanceNode.inputs[0],rerouteNode.outputs[0])
        process.links.new(instanceNode.inputs[2],in_process.outputs[1])
        process.links.new(out_process.inputs[0],instanceNode.outputs[0])
        process.links.new(instanceNode.inputs[4],in_process.outputs[2])

        process.inputs.new(type='NodeSocketInt',name='Block Index')
        process.inputs.new(type='NodeSocketInt',name='Nbt Index')
        
    else:
        process = D.node_groups["Process"]
    return process
broke = []
def create_nodegroup(chunks,blocks,meshes):
    """ Create a node group for instancing on the object"""
    chunks = chunks.get("chunks")
    block_instances = blocks.get("instance")
    mesh_instances = meshes.get("instance")
    
    node_groups = []
    for ic,chunk in enumerate(chunks):
        nodegroup_name = chunk.split('/')[1]
        if not bool(D.node_groups.get(nodegroup_name)):
            instance = D.node_groups.new(chunk.split('/')[1],'GeometryNodeTree')
            out_instance = instance.nodes.new('NodeGroupOutput')
            in_instance = instance.nodes.new('NodeGroupInput')
            instance.inputs.new(type='NodeSocketGeometry',name='Geometry')
            
            out_instance.location = (800,0)
            join_block = instance.nodes.new('GeometryNodeJoinGeometry')
            join_block.name='Join Block Instances'
            join_block.location = (-200,-200)
            frame_block = instance.nodes.new('NodeFrame')
            frame_block.name = chunk.split('/')[1]+'_Blocks'
            frame_block.label = frame_block.name
            join_block.parent = frame_block
            i = 0                
            
        else:
            instance = D.node_groups[nodegroup_name]
            join_block = instance.nodes['Join Block Instances']
            frame_block = instance.nodes[nodegroup_name+'_Blocks']

        for node in instance.nodes:
            if node.type == 'OBJECT_INFO':
                instance.nodes.remove(node)


        i = 0
#        print(block_instances)
        for block in reversed(block_instances[ic]):
            if block[0] == 0:
                name = mesh_instances[block[1].strip('/')]   
            else:
                name = block[1].strip('/') + "_merge"
            try:
                inst = D.objects[name]
            except:
                try:
                    inst = D.objects[name+'.001']
                except:
                    inst = D.objects['Empty']
                    broke.append(name)
                                
            block_node = instance.nodes.new('GeometryNodeObjectInfo')
            block_node.name = inst.name
            block_node.label = inst.name
            block_node.hide = True
            block_node.location = (-500,-500+i)
            block_node.inputs[1].default_value = True
            block_node.parent = frame_block
            instance.links.new(join_block.inputs[0],block_node.outputs[3])
            i+=50
            if inst.type == 'MESH':
                block_node.inputs[0].default_value = inst
        
        if not bool(instance.nodes.get("Process")):
            process_group = instance.nodes.new("GeometryNodeGroup")
            process_group.name = "Process"
            process_group.node_tree = process
            process_group.location =  (300,0)
        
            instance.links.new(out_instance.inputs[0],process_group.outputs[0])
            instance.links.new(process_group.inputs[1],join_block.outputs[0])
            
            instance.links.new(process_group.inputs[0],in_instance.outputs[0])
            instance.links.new(process_group.inputs[2],in_instance.outputs[1])
            instance.links.new(process_group.inputs[3],in_instance.outputs[2])
            instance.links.new(process_group.inputs[4],in_instance.outputs[3])
        node_groups.append(instance)
    return node_groups

def create_object(meshes,collection):
    """Create the object and apply the point instancing node group"""
    for im,mesh in enumerate(meshes):
        object_name  = mesh.name
        if not bool(D.objects.get(mesh.name)):
            obj = D.objects.new(mesh.name, mesh)
            collection.objects.link(obj)
            # d = Matrix.Rotation(math.radians(90),4,'X')
            # obj.matrix_world = d
        else:
            obj = D.objects[object_name]
            
        if not bool(obj.modifiers.get("Point Instancer")):
            mod = obj.modifiers.new('Point Instancer','NODES')
            
            mod.node_group = node_groups[im]
            mod["Input_2_use_attribute"] = True 
            mod["Input_2_attribute_name"] = "instance_index"
            mod["Input_3_use_attribute"] = True 
            mod["Input_3_attribute_name"] = "block_index"
            mod["Input_4_use_attribute"] = True 
            mod["Input_4_attribute_name"] = "nbt_index"
        else:
            pass

def lprint(list):
    for l in list:
        print(l)

def fix_material(materials):
    for mat in materials:
        try:
            img = mat.node_tree.nodes["Image Texture"]
            img.interpolation = 'Closest'
        except:
            pass

def clean_mesh(meshes):
    for mesh in meshes:
        D.meshes.remove(mesh,do_unlink=True)

def clean_mat(materials):
    for material in materials:
        D.materials.remove(material,do_unlink=True)   

def clean_image(images):
    for img in images:
        D.images.remove(img,do_unlink=True)   

def clean_obj(objs):
    for obj in objs:
        D.objects.remove(obj,do_unlink=True) 
        
def clean_ng(ngs):
    for ng in ngs:
        D.node_groups.remove(ng,do_unlink=True) 

filePath = 'D:\\Forge modding\\ModDev\\run\\saves\\modd 4\\mood.usda'

paths = read_path(filePath)
usd_paths = read_usd(paths)
chunks = read_chunk(usd_paths)
blocks = read_block(usd_paths,chunks)
meshes = read_mesh(usd_paths,blocks)
#print(meshes.get("instance"))
## adjacent function check if 2 points position is different only 1 axis
def adjacent_point():
    # ch = chunks.get("chunks")
    pt = chunks.get("points")
    # for ic,c in enumerate(ch[0][0]):
    a =np.array(pt[0])
    for v1 in a:
        for v2 in a:
            if np.any(np.abs(np.diff([v1,v2],axis=1))) == 1:
        
        # if diff == 1 and not (v1 == v2):
        #     print([str(v1),str(v2)],[i1,i2])
                print(v1,v2)

#adjacent_point()

blender = False
try:
    import bpy
    blender = True
except:
    pass

if blender:
    import bmesh
    D = bpy.data
    C = bpy.context
    process = create_asset()
    collections = create_usd_collection(paths)
    node_groups = create_nodegroup(chunks,blocks,meshes)

    point_collection = collections[0][1]
    object_mesh = create_pts(paths,chunks,blocks)
    create_object(object_mesh,point_collection)
#    print(broke)

now = time.time() #Time after it finished
print("It took: ", now-then, " seconds")