import bpy
import bmesh
import math
import mathutils
from mathutils import Vector
from random import random, seed
from mathutils.bvhtree import BVHTree
from bpy_extras import view3d_utils
from bpy_extras.object_utils import world_to_camera_view

from bpy.props import (StringProperty,
						BoolProperty,
						IntProperty,
						FloatProperty,
						FloatVectorProperty,
						EnumProperty,
						PointerProperty,
						)
from bpy.types import (Panel,
						Operator,
						AddonPreferences,
						PropertyGroup,
						)

bl_info = {
	"name": "WPL Mesh Helpers",
	"author": "IPv6",
	"version": (1, 0),
	"blender": (2, 78, 0),
	"location": "View3D > T-panel > WPL",
	"description" : "",
	"warning"	 : "",
	"wiki_url"	: "",
	"tracker_url" : "",
	"category"	: ""
	}

WPL_PROJM = [
	('TO_CAMERA', "To camera", "", 1),
	('USE_NORMALS', "Use Normals", "", 2),
]

kRaycastEpsilon = 0.01
kRaycastDeadzone = 0.0001

def force_visible_object(obj):
	if obj:
		if obj.hide == True:
			obj.hide = False
		for n in range(len(obj.layers)):
			obj.layers[n] = False
		current_layer_index = bpy.context.scene.active_layer
		obj.layers[current_layer_index] = True

def select_and_change_mode(obj,obj_mode,hidden=False):
	if obj:
		obj.select = True
		bpy.context.scene.objects.active = obj
		force_visible_object(obj)
		try:
			m = bpy.context.mode
			if bpy.context.mode!='OBJECT':
				bpy.ops.object.mode_set(mode='OBJECT')
			bpy.context.scene.update()
			bpy.ops.object.mode_set(mode=obj_mode)
			#print("Mode switched to ", obj_mode)
		except:
			pass
		obj.hide = hidden
	return m

def camera_pos(region_3d):
	""" Return position, rotation data about a given view for the first space attached to it """
	#https://stackoverflow.com/questions/9028398/change-viewport-angle-in-blender-using-python
	def camera_position(matrix):
		""" From 4x4 matrix, calculate camera location """
		t = (matrix[0][3], matrix[1][3], matrix[2][3])
		r = (
		  (matrix[0][0], matrix[0][1], matrix[0][2]),
		  (matrix[1][0], matrix[1][1], matrix[1][2]),
		  (matrix[2][0], matrix[2][1], matrix[2][2])
		)
		rp = (
		  (-r[0][0], -r[1][0], -r[2][0]),
		  (-r[0][1], -r[1][1], -r[2][1]),
		  (-r[0][2], -r[1][2], -r[2][2])
		)
		output = mathutils.Vector((
		  rp[0][0] * t[0] + rp[0][1] * t[1] + rp[0][2] * t[2],
		  rp[1][0] * t[0] + rp[1][1] * t[1] + rp[1][2] * t[2],
		  rp[2][0] * t[0] + rp[2][1] * t[1] + rp[2][2] * t[2],
		))
		return output
	#look_at = region_3d.view_location
	matrix = region_3d.view_matrix
	#rotation = region_3d.view_rotation
	camera_pos = camera_position(matrix)
	return camera_pos

def get_selected_facesIdx(active_mesh):
	# find selected faces
	bpy.ops.object.mode_set(mode='OBJECT')
	faces = [f.index for f in active_mesh.polygons if f.select]
	# print("selected faces: ", faces)
	return faces

def get_selected_edgesIdx(active_mesh):
	# find selected faces
	bpy.ops.object.mode_set(mode='OBJECT')
	selectedEdgesIdx = [e.index for e in active_mesh.edges if e.select]
	return selectedEdgesIdx

def get_selected_vertsIdx(active_mesh):
	# find selected faces
	bpy.ops.object.mode_set(mode='OBJECT')
	selectedVertsIdx = [e.index for e in active_mesh.vertices if e.select]
	return selectedVertsIdx

# def add_connected_bmverts(v,verts_list,selvertsIdx):
	# v.tag = True
	# if (selvertsIdx is not None) and (v.index not in selvertsIdx):
		# return
	# if v not in verts_list:
		# verts_list.append(v)
	# for edge in v.link_edges:
		# ov = edge.other_vert(v)
		# if (ov is not None) and not ov.tag:
			# ov.tag = True
			# if (selvertsIdx is not None) and (ov.index not in selvertsIdx):
				# return
			# if ov not in verts_list:
				# verts_list.append(ov)
			# add_connected_bmverts(ov,verts_list,selvertsIdx)

def cutLongEdges(active_mesh, seledgesIdx, context, opt_edgelen ):
	bpy.ops.object.mode_set( mode = 'EDIT' )
	bm = bmesh.from_edit_mesh( active_mesh )
	while( True ):
		long_edges = [ e for e in bm.edges if e.calc_length() >= opt_edgelen and e.index in seledgesIdx ]
		if not long_edges:
			break
		result = bmesh.ops.subdivide_edges(
			bm,
			edges=long_edges,
			cuts=1
			#use_single_edge=True,
			#use_grid_fill=True
		)
		splitgeom = result['geom_split']
		#for face in filter(lambda e: isinstance(e, bmesh.types.BMFace), splitgeom):
		#	if face not in out_faces:
		#		out_faces.append(face)
		out_verts = []
		out_faces = []
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		for vert in filter(lambda e: isinstance(e, bmesh.types.BMVert), splitgeom):
			if vert not in out_verts:
				out_verts.append(vert)
		for f in bm.faces:
			for v in f.verts:
				if v in out_verts:
					out_faces.append(f)
					break
		bmesh.ops.triangulate( bm, faces=out_faces )

	# update, while in edit mode
	# thanks to ideasman42 for making this clear
	# http://blender.stackexchange.com/questions/414/
	bmesh.update_edit_mesh( active_mesh )
	# bpy.context.scene.update()

class WPLsubdiv_long_edges( bpy.types.Operator ):
	bl_idname = "mesh.wplsubdiv_long_edges"
	bl_label = "Subdiv Long Edges"
	bl_options = {'REGISTER', 'UNDO'}
	opt_edgelen = bpy.props.FloatProperty(
		name		= "Edge Length",
		description = "Max len for subdiv/Min len for dissolve",
		default	 = 0.5,
		min		 = 0.001,
		max		 = 999
		)

	@classmethod
	def poll( cls, context ):
		return ( context.object is not None  and
				context.object.type == 'MESH' )

	def execute( self, context ):
		active_object = context.scene.objects.active
		active_mesh = active_object.data
		seledgesIdx = get_selected_edgesIdx(active_mesh)
		if len(seledgesIdx) == 0:
			self.report({'ERROR'}, "No faces selected, select some faces first")
			return {'FINISHED'}
		cutLongEdges(active_mesh, seledgesIdx, context, self.opt_edgelen )
		return {'FINISHED'}
		
class WPLrefill_select( bpy.types.Operator ):
	bl_idname = "mesh.wplrefill_select"
	bl_label = "Refill selection"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll( cls, context ):
		return ( context.object is not None  and
				context.object.type == 'MESH' )

	def execute( self, context ):
		active_object = context.scene.objects.active
		active_mesh = active_object.data
		selvertsAll = get_selected_vertsIdx(active_mesh)
		bpy.ops.object.mode_set( mode = 'EDIT' )
		bpy.ops.mesh.region_to_loop()
		selvertsBnd = get_selected_vertsIdx(active_mesh)
		selvertsInner = list(filter(lambda plt: plt not in selvertsBnd, selvertsAll))
		if len(selvertsInner) == 0:
			self.report({'ERROR'}, "No inner vertices found")
			#print("All: ",selvertsAll," outer:", selvertsBnd)
			return {'CANCELLED'}
		bpy.ops.object.mode_set( mode = 'EDIT' )
		bm = bmesh.from_edit_mesh(active_mesh)
		verts_select = [f for f in bm.verts if f.index in selvertsInner]
		bmesh.ops.delete(bm, geom=verts_select, context=1)
		bmesh.update_edit_mesh(active_mesh)
		bpy.ops.mesh.fill()
		return {'FINISHED'}

class WPLproj_bubble( bpy.types.Operator ):
	bl_idname = "mesh.wplproj_bubble"
	bl_label = "Bubble verts into direction"
	bl_options = {'REGISTER', 'UNDO'}

	opt_flatnMeth = EnumProperty(
		items = WPL_PROJM,
		name="Method",
		description="Method",
		default='TO_CAMERA',
	)
	opt_flatnFac = bpy.props.FloatProperty(
		name		= "Influence",
		description = "Influence",
		default	 = 1.0,
		min		 = -100,
		max		 = 100
		)
	opt_maxDist = bpy.props.FloatProperty(
		name		= "Max distance",
		description = "Max distance",
		default	 = 100.0,
		min		 = 0.001,
		max		 = 100
		)

	@classmethod
	def poll( cls, context ):
		return ( context.object is not None  and
				context.object.type == 'MESH' )

	def execute( self, context ):
		active_object = context.scene.objects.active
		active_mesh = active_object.data
		if not bpy.context.space_data.region_3d.is_perspective:
			self.report({'ERROR'}, "Can`t work in ORTHO mode")
			return {'CANCELLED'}
		cameraOrigin_g = camera_pos(bpy.context.space_data.region_3d)
		selvertsAll = get_selected_vertsIdx(active_mesh)
		if len(selvertsAll) == 0:
			self.report({'ERROR'}, "No selected vertices found")
			return {'CANCELLED'}
		#unselvertsAll = [e.index for e in active_mesh.vertices if e.index not in selvertsAll]
		bpy.ops.object.mode_set( mode = 'EDIT' )
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		
		bm2 = bm.copy()
		bm2.verts.ensure_lookup_table()
		bm2.faces.ensure_lookup_table()
		bm2.verts.index_update()
		v2r = []
		for selvIdx in selvertsAll:
			v2r.append(bm2.verts[selvIdx])
		for v2r_v in v2r:
			bm2.verts.remove(v2r_v)
			bm2.verts.ensure_lookup_table()
			bm2.faces.ensure_lookup_table()
			bm2.verts.index_update()
		bm2_tree = BVHTree.FromBMesh(bm2, epsilon = kRaycastEpsilon)
		bm2.free()
		# tracing to new geometry
		matrix_world_inv = active_object.matrix_world.inverted()
		cameraOrigin = matrix_world_inv * cameraOrigin_g
		inner_verts = [ (vIdx, bm.verts[vIdx].co, bm.verts[vIdx].normal) for vIdx in selvertsAll ]
		opt_flatnFac = self.opt_flatnFac
		opt_normdir = 1
		if opt_flatnFac < 0 and self.opt_flatnMeth == 'USE_NORMALS':
			opt_flatnFac = abs(opt_flatnFac)
			opt_normdir = -1
		for w_v in inner_verts:
			hit = None
			if self.opt_flatnMeth == 'TO_CAMERA':
				direction = w_v[1] - cameraOrigin
				direction.normalize()
				hit, normal, index, distance = bm2_tree.ray_cast(cameraOrigin, direction)
			else:
				origin = w_v[1]
				direction = w_v[2]
				direction.normalize()
				hit, normal, index, distance = bm2_tree.ray_cast(origin+kRaycastDeadzone*direction*opt_normdir, direction*opt_normdir)
			if (hit is not None) and ((w_v[1]-hit).length <= self.opt_maxDist):
				# lerping position
				vco_shift = hit - w_v[1]
				vco = w_v[1]+vco_shift*opt_flatnFac
				bm.verts[w_v[0]].co = vco
		bmesh.update_edit_mesh(active_mesh, True)
		return {'FINISHED'}

class WPLproj_flatten( bpy.types.Operator ):
	bl_idname = "mesh.wplproj_flatten"
	bl_label = "Flatten to convex hull"
	bl_options = {'REGISTER', 'UNDO'}

	opt_flatnMeth = EnumProperty(
		items = WPL_PROJM,
		name="Method",
		description="Method",
		default='TO_CAMERA',
	)
	opt_flatnFac = bpy.props.FloatProperty(
		name		= "Influence",
		description = "Influence",
		default	 = 1.0,
		min		 = -100,
		max		 = 100
		)

	@classmethod
	def poll( cls, context ):
		return ( context.object is not None  and
				context.object.type == 'MESH' )

	def execute( self, context ):
		active_object = context.scene.objects.active
		active_mesh = active_object.data
		if not bpy.context.space_data.region_3d.is_perspective:
			self.report({'ERROR'}, "Can`t work in ORTHO mode")
			return {'CANCELLED'}
		cameraOrigin_g = camera_pos(bpy.context.space_data.region_3d)
		selvertsAll = get_selected_vertsIdx(active_mesh)
		bpy.ops.object.mode_set( mode = 'EDIT' )
		bpy.ops.mesh.region_to_loop()
		selvertsBnd = get_selected_vertsIdx(active_mesh)
		selvertsInner = list(filter(lambda plt: plt not in selvertsBnd, selvertsAll))
		if len(selvertsInner) == 0:
			self.report({'ERROR'}, "No inner vertices found")
			#print("All: ",selvertsAll," outer:", selvertsBnd)
			return {'CANCELLED'}
		bm2 = bmesh.new()
		chull_verts = [ active_mesh.vertices[vIdx].co for vIdx in selvertsBnd ]
		for v in chull_verts:
			bm2.verts.new(v)
		bmesh.ops.convex_hull(bm2, input=bm2.verts)
		bm2_tree = BVHTree.FromBMesh(bm2, epsilon = kRaycastEpsilon)
		bm2.free()
		#obj_tmp = bpy.data.objects.new(name=me_tmp.name, object_data=me_tmp)
		#scene.objects.link(obj_tmp)
		#scene.update()
		# tracing to new geometry
		matrix_world_inv = active_object.matrix_world.inverted()
		cameraOrigin = matrix_world_inv * cameraOrigin_g
		inner_verts = [ (vIdx, active_mesh.vertices[vIdx].co, active_mesh.vertices[vIdx].normal) for vIdx in selvertsInner ]
		for w_v in inner_verts:
			hit = None
			if self.opt_flatnMeth == 'TO_CAMERA':
				direction = w_v[1] - cameraOrigin
				direction.normalize()
				hit, normal, index, distance = bm2_tree.ray_cast(cameraOrigin, direction)
			else:
				origin = w_v[1]
				direction = w_v[2]
				direction.normalize()
				hit, normal, index, distance = bm2_tree.ray_cast(origin+kRaycastDeadzone*direction, direction)
			if hit is not None:
				# lerping position
				vco_shift = hit - w_v[1]
				vco = w_v[1]+vco_shift*self.opt_flatnFac
				active_mesh.vertices[w_v[0]].co = vco
		bpy.ops.object.mode_set( mode = 'EDIT' )
		return {'FINISHED'}

class WPLbridge_cirkpunch( bpy.types.Operator ):
	bl_idname = "mesh.wplbridge_cirkpunch"
	bl_label = "Break face with star pattern"
	bl_options = {'REGISTER', 'UNDO'}

	opt_iters = bpy.props.IntProperty(
		name		= "Iterations",
		description = "Iterations",
		default	 = 1,
		min		 = 1,
		max		 = 100
		)

	@classmethod
	def poll( cls, context ):
		return ( context.object is not None  and
				context.object.type == 'MESH' )

	def execute( self, context ):
		active_object = context.scene.objects.active
		active_mesh = active_object.data
		selfaceAll = get_selected_facesIdx(active_mesh)
		if len(selfaceAll) == 0:
			self.report({'ERROR'}, "No selected faces found")
			return {'CANCELLED'}

		bpy.ops.object.mode_set( mode = 'EDIT' )
		bm = bmesh.from_edit_mesh( active_mesh )
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		iters = self.opt_iters
		facemap= {}
		edgmap = []
		for selfi in selfaceAll:
			face = bm.faces[selfi]
			facemap[selfi] = (face, face.calc_center_median())
			for edg in face.edges:
				if edg not in edgmap:
					edgmap.append(edg)
		for edg in edgmap:
			bm.verts.ensure_lookup_table()
			bm.faces.ensure_lookup_table()
			bm.verts.index_update()
			result = bmesh.ops.subdivide_edges(
				bm,
				edges=[edg],
				cuts=self.opt_iters
			)
		for selfi in selfaceAll:
			bm.verts.ensure_lookup_table()
			bm.faces.ensure_lookup_table()
			bm.verts.index_update()
			face = facemap[selfi][0]
			cenpos = facemap[selfi][1]
			facesnew = bmesh.ops.extrude_discrete_faces(bm, faces = [face], use_select_history = False)
			other_verts = [v for v in facesnew["faces"][0].verts]
			for v in other_verts:
				v.co = cenpos
			bmesh.ops.remove_doubles(bm, verts=other_verts, dist=0.01)

		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		bmesh.update_edit_mesh( active_mesh )
		return {'FINISHED'}

# class WPLbridge_mesh_islands( bpy.types.Operator ):
# 	# Operator get all selected faces, extracts bounds and then make faces BETWEEN mesh-selection islands, basing on distance between vertices
# 	bl_idname = "mesh.wplbridge_mesh_islands"
# 	bl_label = "Bridge edges of selected islands"
# 	bl_options = {'REGISTER', 'UNDO'}
# 	opt_flatnFac = bpy.props.FloatProperty(
# 		name		= "Minimal distance",
# 		description = "Distance to merge",
# 		default	 = 0.3,
# 		min		 = 0,
# 		max		 = 100
# 		)
#
# 	@classmethod
# 	def poll( cls, context ):
# 		return ( context.object is not None  and
# 				context.object.type == 'MESH' )
#
# 	def execute( self, context ):
# 		active_object = context.scene.objects.active
# 		active_mesh = active_object.data
# 		selvertsAll = get_selected_vertsIdx(active_mesh)
# 		bpy.ops.object.mode_set( mode = 'EDIT' )
# 		bpy.ops.mesh.region_to_loop()
# 		selvertsBnd = get_selected_vertsIdx(active_mesh)
# 		seledgesBnd = get_selected_edgesIdx(active_mesh)
# 		if len(seledgesBnd) == 0:
# 			self.report({'ERROR'}, "No bounds found")
# 			#print("All: ",selvertsAll," outer:", selvertsBnd)
# 			return {'CANCELLED'}
# 		bpy.ops.object.mode_set( mode = 'EDIT' )
# 		bm = bmesh.from_edit_mesh(active_mesh)
# 		bm.verts.ensure_lookup_table()
# 		bm.faces.ensure_lookup_table()
# 		bm.verts.index_update()
# 		islandVerts = {}
# 		islandNum = 1
# 		for v in bm.verts:
# 			if v.tag == False:
# 				meshlist = []
# 				add_connected_bmverts(v,meshlist,selvertsAll)
# 				for vv in meshlist:
# 					islandVerts[vv.index] = islandNum
# 				islandNum = islandNum+1
# 		if islandNum < 3:
# 			self.report({'ERROR'}, "No islands found, need at least 2 islands")
# 			#print("All: ",selvertsAll," outer:", selvertsBnd)
# 			return {'CANCELLED'}
# 		#nearest vertices for each boundary vertice
# 		for v in bm.verts:
# 			v.tag = False
# 		islandVertsUsed = {}
# 		for isl1 in range(1,islandNum):
# 			for isl2 in range(1,islandNum):
# 				if isl1 != isl2:
# 					hull_edges = []
# 					for bndIdx1 in selvertsBnd:
# 						if islandVerts[bndIdx1] == isl1 and bndIdx1 not in islandVertsUsed:
# 							bndV1 = bm.verts[bndIdx1]
# 							bndNearest = None
# 							bndNearestDist = 99999
# 							for bndIdx2 in selvertsBnd:
# 								if islandVerts[bndIdx2] == isl2:#!!! and bndIdx2 not in islandVertsUsed:
# 									bndV2 = bm.verts[bndIdx2]
# 									dst = (bndV2.co-bndV1.co).length
# 									if dst < self.opt_flatnFac and dst < bndNearestDist:
# 										bndNearestDist = dst
# 										bndNearest = bndV2
# 							if bndNearest is not None:
# 								# selecting edges
# 								islandVertsUsed[bndIdx1]=bndIdx2
# 								islandVertsUsed[bndIdx2]=bndIdx1
# 								verts2join = []
# 								verts2join.append(bndV1)
# 								verts2join.append(bndNearest)
# 								crtres = bmesh.ops.contextual_create(bm, geom=verts2join)
# 								hull_edges.extend(crtres["edges"])
# 								hull_edges.extend(bndV1.link_edges)
# 								hull_edges.extend(bndNearest.link_edges)
# 					hull_edges_pack = list(set(hull_edges))
# 					if len(hull_edges_pack)>2:
# 						bmesh.ops.holes_fill(bm, edges=hull_edges_pack,sides=4)
# 						#bmesh.ops.edgeloop_fill(bm, edges=hull_edges)
# 						#bmesh.ops.bridge_loops(bm, edges=hull_edges)
# 						#bmesh.ops.contextual_create(bm, geom=(edg1,edg2))
# 		bmesh.update_edit_mesh(active_mesh)
# 		bm.free()
# 		return {'FINISHED'}

class WPLuv_flatten( bpy.types.Operator ):
	bl_idname = "mesh.wpluv_flatten"
	bl_label = "Flatten toward active UVMap"
	bl_options = {'REGISTER', 'UNDO'}
	opt_flatnFac = bpy.props.FloatProperty(
		name		= "Flatness",
		description = "Flatness applied",
		default	 = 1.0,
		min		 = -100,
		max		 = 100
		)

	@classmethod
	def poll( cls, context ):
		return ( context.object is not None  and
				context.object.type == 'MESH' )

	def execute( self, context ):
		active_object = context.scene.objects.active
		active_mesh = active_object.data
		active_uvmap = active_mesh.uv_textures.active
		selvertsAll = get_selected_vertsIdx(active_mesh)
		if len(selvertsAll) == 0:
			self.report({'ERROR'}, "No inner vertices found")
			#print("All: ",selvertsAll," outer:", selvertsBnd)
			return {'CANCELLED'}
		if active_uvmap is None:
			self.report({'ERROR'}, "No active UVMap found, unwrap mesh first")
			#print("All: ",selvertsAll," outer:", selvertsBnd)
			return {'CANCELLED'}

		bpy.ops.object.mode_set( mode = 'EDIT' )
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		uv_layer = bm.loops.layers.uv.verify()
		bm.faces.layers.tex.verify()  # currently blender needs both layers.
		# sorting vertex list on Z coord
		selvertsAll = sorted(selvertsAll, key=lambda plt: (-active_mesh.vertices[plt].co[2]))
		anchor_vertIdx = selvertsAll[0]
		anchor_p1 = mathutils.Vector((1,0,0))
		anchor_p2 = mathutils.Vector((0,1,0))
		for elem in reversed(bm.select_history):
			if isinstance(elem, bmesh.types.BMFace):
				anchor_vertIdx = elem.verts[0].index
				facen = elem.normal
				if facen.dot(mathutils.Vector((0,0,1))) > 0.99:
					anchor_p1 = facen.cross(mathutils.Vector((1,0,0)))
				else:
					anchor_p1 = facen.cross(mathutils.Vector((0,0,1)))
				anchor_p2 = facen.cross(anchor_p1)
				tmp = anchor_p2
				anchor_p2 = anchor_p1
				anchor_p1 = -tmp
				break
			if isinstance(elem, bmesh.types.BMVert):
				anchor_vertIdx = elem.index
				break
		first_co = active_mesh.vertices[anchor_vertIdx].co
		first_uv = mathutils.Vector((0,0))
		#searching for first_co_uv
		for face in bm.faces:
			for loop in face.loops:
				vert = loop.vert
				if vert.index == anchor_vertIdx:
					first_uv = loop[uv_layer].uv
		for face in bm.faces:
			for loop in face.loops:
				vert = loop.vert
				if (vert.index in selvertsAll):
					rel_uv = loop[uv_layer].uv - first_uv
					new_co = first_co+anchor_p1*rel_uv[0]+anchor_p2*rel_uv[1]
					vert.co = vert.co.lerp(new_co,self.opt_flatnFac)
					selvertsAll.remove(vert.index) #to avoid double-effect when vert in several loops
		#bm.to_mesh(active_mesh)
		bmesh.update_edit_mesh(active_mesh)
		return {'FINISHED'}

class WPLSculptFeatures_Panel(bpy.types.Panel):
	bl_label = "Sculpt helpers"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_category = 'WPL'

	def draw_header(self, context):
		layout = self.layout
		layout.label(text="")

	def draw(self, context):
		layout = self.layout
		col = layout.column()

		col.separator()
		col.label("Bubbling")
		col.operator("mesh.wplproj_flatten", text="Projected flatten (Camera)").opt_flatnMeth = 'TO_CAMERA'
		col.operator("mesh.wplproj_flatten", text="Projected flatten (Normals)").opt_flatnMeth = 'USE_NORMALS'
		col.separator()
		col.operator("mesh.wplproj_bubble", text="Bubble verts (Camera)").opt_flatnMeth = 'TO_CAMERA'
		col.operator("mesh.wplproj_bubble", text="Bubble verts (Normals)").opt_flatnMeth = 'USE_NORMALS'
		col.operator("mesh.wpluv_flatten", text="UV-flatten")

		col.separator()
		col.label("Subdivide")
		col.operator("mesh.wplrefill_select", text="ReFill selected")
		col.operator("mesh.wplbridge_cirkpunch", text="Star break faces")
		col.operator("mesh.wplsubdiv_long_edges", text="Cut Long Edges")
		#col.operator("mesh.wplbridge_mesh_islands", text="Bridge islands")

def register():
	print("WPLSculptFeatures_Panel registered")
	bpy.utils.register_module(__name__)

def unregister():
	bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
	register()
