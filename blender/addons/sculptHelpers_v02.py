# Operators:
# - Cut long edges / Subdivide big faces into smaller one
# - Select all visible vertices/Deselect visible/invisible verts. Can give "strange" results in local mode, since raytrace using WHOLE scene ALWAYS!
# - Flatten inner vertices (of selected region) on the virtually-visible convex-hull of region boundaries
# - Bridge edges of selected mesh regions based on min distance between vertices

# Inetresting:
# - UV-flattening https://github.com/the3dadvantage/BlenderSurfaceFollow/blob/master/UVShape.py

import bpy
import bmesh
import math
import mathutils
from mathutils import Vector
from random import random, seed
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

def camera_pos(region_3d):
	""" Return position, rotation data about a given view for the first space attached to it """
	#https://stackoverflow.com/questions/9028398/change-viewport-angle-in-blender-using-python
	#look_at = region_3d.view_location
	matrix = region_3d.view_matrix
	#rotation = region_3d.view_rotation
	camera_pos = camera_position(matrix)
	return camera_pos

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

def add_connected_bmverts(v,verts_list,selvertsIdx):
	v.tag = True
	if (selvertsIdx is not None) and (v.index not in selvertsIdx):
		return
	if v not in verts_list:
		verts_list.append(v)
	for edge in v.link_edges:
		ov = edge.other_vert(v)
		if (ov is not None) and not ov.tag:
			ov.tag = True
			if (selvertsIdx is not None) and (ov.index not in selvertsIdx):
				return
			if ov not in verts_list:
				verts_list.append(ov)
			add_connected_bmverts(ov,verts_list,selvertsIdx)

def visibilitySelect(active_object, active_mesh, context, actionSelectType, fuzz):
	selverts = get_selected_vertsIdx(active_mesh)
	bpy.ops.object.mode_set( mode = 'EDIT' )
	bpy.ops.mesh.select_all(action = 'DESELECT')
	scene = bpy.context.scene
	bm = bmesh.from_edit_mesh( active_mesh )
	bm.verts.ensure_lookup_table()
	bm.faces.ensure_lookup_table()
	bm.verts.index_update()
	cameraOrigin = camera_pos(bpy.context.space_data.region_3d)
	affectedVerts = []
	fuzzlist = [(0,0,0),(fuzz,0,0),(-fuzz,0,0),(0,fuzz,0),(0,-fuzz,0),(0,0,fuzz),(0,0,-fuzz)]
	for face in bm.faces:
		for vert in face.verts:
			for fuzzpic in fuzzlist:
				if vert.index not in affectedVerts:
					# Cast a ray from the "camera" position
					co_world = active_object.matrix_world * vert.co + mathutils.Vector(fuzzpic)
					direction = co_world - cameraOrigin;
					direction.normalize()
					result, location, normal, faceIndex, object, matrix = scene.ray_cast( cameraOrigin, direction )
					#print ("result",result," faceIndex",faceIndex," vert",vert, " verts", bm.faces[faceIndex].verts)
					if result and object.name == active_object.name:
						facevrt = [ e.index for e in bm.faces[faceIndex].verts]
						#print ("vert.index",vert.index," facevrt",facevrt)
						if vert.index in facevrt:
							affectedVerts.append(vert.index)
	#bmesh.update_edit_mesh( active_mesh )
	bpy.ops.object.mode_set(mode='OBJECT')
	if actionSelectType == 0:
		for vertIdx in affectedVerts:
			active_mesh.vertices[vertIdx].select = True
	elif actionSelectType == 1:
		for vertIdx in selverts:
			if vertIdx in affectedVerts:
				active_mesh.vertices[vertIdx].select = True
	elif actionSelectType == 2:
		for vertIdx in selverts:
			if vertIdx not in affectedVerts:
				active_mesh.vertices[vertIdx].select = True
	bpy.ops.object.mode_set(mode='EDIT')
	#context.tool_settings.mesh_select_mode = (True, False, False)
	bpy.ops.mesh.select_mode(type="VERT")


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

class WPL_subdiv_long_edges( bpy.types.Operator ):
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
		#wplScultSets = context.scene.wplScultSets  #wplScultSets.opt_edgelen
		active_object = context.scene.objects.active
		active_mesh = active_object.data
		seledgesIdx = get_selected_edgesIdx(active_mesh)
		if len(seledgesIdx) == 0:
			self.report({'ERROR'}, "No faces selected, select some faces first")
			return {'FINISHED'}
		cutLongEdges(active_mesh, seledgesIdx, context, self.opt_edgelen )
		return {'FINISHED'}

class WPL_selvisible( bpy.types.Operator ):
	bl_idname = "mesh.wplvert_selvisible"
	bl_label = "Select visible verts"
	bl_options = {'REGISTER', 'UNDO'}
	opt_rayFuzz = bpy.props.FloatProperty(
		name		= "Fuzziness",
		default	 = 0.05
	)
	@classmethod
	def poll( cls, context ):
		return ( context.object is not None  and
				context.object.type == 'MESH' )

	def execute( self, context ):
		active_object = context.scene.objects.active
		active_mesh = active_object.data
		visibilitySelect(active_object, active_mesh, context, 0, self.opt_rayFuzz )
		return {'FINISHED'}

class WPL_deselvisible( bpy.types.Operator ):
	bl_idname = "mesh.wplvert_deselunvisible"
	bl_label = "Deselect invisible verts"
	bl_options = {'REGISTER', 'UNDO'}
	opt_rayFuzz = bpy.props.FloatProperty(
		name		= "Fuzziness",
		default	 = 0.05
	)
	@classmethod
	def poll( cls, context ):
		return ( context.object is not None  and
				context.object.type == 'MESH' )

	def execute( self, context ):
		active_object = context.scene.objects.active
		active_mesh = active_object.data
		visibilitySelect(active_object, active_mesh, context, 1, self.opt_rayFuzz )
		return {'FINISHED'}

class WPL_deselunvisible( bpy.types.Operator ):
	bl_idname = "mesh.wplvert_deselvisible"
	bl_label = "Deselect visible verts"
	bl_options = {'REGISTER', 'UNDO'}
	opt_rayFuzz = bpy.props.FloatProperty(
		name		= "Fuzziness",
		default	 = 0.05
	)
	@classmethod
	def poll( cls, context ):
		return ( context.object is not None  and
				context.object.type == 'MESH' )

	def execute( self, context ):
		active_object = context.scene.objects.active
		active_mesh = active_object.data
		visibilitySelect(active_object, active_mesh, context, 2, self.opt_rayFuzz )
		return {'FINISHED'}

class WPL_refill_select( bpy.types.Operator ):
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

class WPL_proj_flatten( bpy.types.Operator ):
	bl_idname = "mesh.wplproj_flatten"
	bl_label = "Flatten toward camera"
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
		cameraOrigin = camera_pos(bpy.context.space_data.region_3d)
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
		chull_verts = [ active_object.matrix_world * active_mesh.vertices[vIdx].co for vIdx in selvertsBnd ]
		for v in chull_verts:
			bm2.verts.new(v)
		bmesh.ops.convex_hull(bm2, input=bm2.verts)

		# hack from https://blender.stackexchange.com/questions/9073/how-to-check-if-two-meshes-intersect-in-python
		scene = bpy.context.scene
		me_tmp = bpy.data.meshes.new(name="~temp~")
		bm2.to_mesh(me_tmp)
		bm2.free()
		obj_tmp = bpy.data.objects.new(name=me_tmp.name, object_data=me_tmp)
		scene.objects.link(obj_tmp)
		scene.update()
		# tracing to new geometry
		matrix_world_inv = active_object.matrix_world.inverted()
		inner_verts = [ (vIdx,active_object.matrix_world * active_mesh.vertices[vIdx].co) for vIdx in selvertsInner ]
		for w_v in inner_verts:
			#print("w_v",w_v," cameraOrigin",cameraOrigin)
			direction = w_v[1] - cameraOrigin
			direction.normalize()
			result, location, normal, faceIndex, object, matrix = scene.ray_cast( cameraOrigin, direction )
			# projecting each vertex to nearest
			if result:
				# lerping position
				vco_shift = location - w_v[1]
				vco = w_v[1]+vco_shift*self.opt_flatnFac
				active_mesh.vertices[w_v[0]].co = matrix_world_inv * vco

		scene.objects.unlink(obj_tmp)
		bpy.data.objects.remove(obj_tmp)
		bpy.data.meshes.remove(me_tmp)
		scene.update()

		bpy.ops.object.mode_set( mode = 'EDIT' )
		return {'FINISHED'}


class WPL_bridge_mesh_islands( bpy.types.Operator ):
	# Operator get all selected faces, extracts bounds and then make faces BETWEEN mesh-selection islands, basing on distance between vertices
	bl_idname = "mesh.wplbridge_mesh_islands"
	bl_label = "Bridge edges of selected islands"
	bl_options = {'REGISTER', 'UNDO'}
	opt_flatnFac = bpy.props.FloatProperty(
		name		= "Minimal distance",
		description = "Distance to merge",
		default	 = 0.3,
		min		 = 0,
		max		 = 100
		)

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
		seledgesBnd = get_selected_edgesIdx(active_mesh)
		if len(seledgesBnd) == 0:
			self.report({'ERROR'}, "No bounds found")
			#print("All: ",selvertsAll," outer:", selvertsBnd)
			return {'CANCELLED'}
		bpy.ops.object.mode_set( mode = 'EDIT' )
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		islandVerts = {}
		islandNum = 1
		for v in bm.verts:
			if v.tag == False:
				meshlist = []
				add_connected_bmverts(v,meshlist,selvertsAll)
				for vv in meshlist:
					islandVerts[vv.index] = islandNum
				islandNum = islandNum+1
		if islandNum < 3:
			self.report({'ERROR'}, "No islands found, need at least 2 islands")
			#print("All: ",selvertsAll," outer:", selvertsBnd)
			return {'CANCELLED'}
		#nearest vertices for each boundary vertice
		for v in bm.verts:
			v.tag = False
		islandVertsUsed = {}
		for isl1 in range(1,islandNum):
			for isl2 in range(1,islandNum):
				if isl1 != isl2:
					hull_edges = []
					for bndIdx1 in selvertsBnd:
						if islandVerts[bndIdx1] == isl1 and bndIdx1 not in islandVertsUsed:
							bndV1 = bm.verts[bndIdx1]
							bndNearest = None
							bndNearestDist = 99999
							for bndIdx2 in selvertsBnd:
								if islandVerts[bndIdx2] == isl2:#!!! and bndIdx2 not in islandVertsUsed:
									bndV2 = bm.verts[bndIdx2]
									dst = (bndV2.co-bndV1.co).length
									if dst < self.opt_flatnFac and dst < bndNearestDist:
										bndNearestDist = dst
										bndNearest = bndV2
							if bndNearest is not None:
								# selecting edges
								islandVertsUsed[bndIdx1]=bndIdx2
								islandVertsUsed[bndIdx2]=bndIdx1
								verts2join = []
								verts2join.append(bndV1)
								verts2join.append(bndNearest)
								crtres = bmesh.ops.contextual_create(bm, geom=verts2join)
								hull_edges.extend(crtres["edges"])
								hull_edges.extend(bndV1.link_edges)
								hull_edges.extend(bndNearest.link_edges)
					hull_edges_pack = list(set(hull_edges))
					if len(hull_edges_pack)>2:
						bmesh.ops.holes_fill(bm, edges=hull_edges_pack,sides=4)
						#bmesh.ops.edgeloop_fill(bm, edges=hull_edges)
						#bmesh.ops.bridge_loops(bm, edges=hull_edges)
						#bmesh.ops.contextual_create(bm, geom=(edg1,edg2))
		bmesh.update_edit_mesh(active_mesh)
		bm.free()
		return {'FINISHED'}

class WPL_uv_flatten( bpy.types.Operator ):
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

class WPL_weig_edt( bpy.types.Operator ):
	bl_idname = "mesh.wplweig_edt"
	bl_label = "Change weight value in vertex group on surrent selection"
	bl_options = {'REGISTER', 'UNDO'}
	opt_stepadd = bpy.props.FloatProperty(
		name		= "Value",
		default	 	= 0.33
		)
	opt_stepmul = bpy.props.FloatProperty(
		name		= "Multiplier",
		default	 	= 1.0
		)

	@classmethod
	def poll( cls, context ):
		return ( context.object is not None  and
				context.object.type == 'MESH' )

	def execute( self, context ):
		oldmode = bpy.context.active_object.mode
		active_object = context.scene.objects.active
		active_mesh = active_object.data
		selvertsAll = get_selected_vertsIdx(active_mesh)
		if len(selvertsAll) == 0:
			self.report({'ERROR'}, "No selected vertices found")
			return {'CANCELLED'}
		select_and_change_mode(active_object,"OBJECT")
		vg = active_object.vertex_groups.active #obj.vertex_groups.new("group name")
		if vg is None:
			self.report({'ERROR'}, "No active vertex group found")
			return {'CANCELLED'}
		for idx in selvertsAll:
			wmod = 'REPLACE'
			try:
				oldval = vg.weight(idx)
			except Exception as e:
				wmod = 'ADD'
				oldval = 0
			newval = oldval
			if self.opt_stepmul == 0.0:
				newval = self.opt_stepadd
			else:
				newval = oldval+self.opt_stepmul*self.opt_stepadd
			vg.add([idx], newval, wmod)
		if oldmode != 'EDIT':
			select_and_change_mode(active_object,"EDIT")
		select_and_change_mode(active_object,oldmode)
		#bpy.context.scene.objects.active = bpy.context.scene.objects.active
		bpy.context.scene.update()
		return {'FINISHED'}

class WPLSculptFeatures_Panel(bpy.types.Panel):
	bl_label = "mesh.wplHelpers"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_category = 'WPL'

	def draw_header(self, context):
		layout = self.layout
		layout.label(text="")

	def draw(self, context):
		layout = self.layout
		#wplScultSets = context.scene.wplScultSets

		# display the properties
		col = layout.column()
		col.label("Subdividers")
		col.operator("mesh.wplrefill_select", text="ReFill selected")
		col.operator("mesh.wplsubdiv_long_edges", text="Cut Long Edges")
		col.operator("mesh.wplbridge_mesh_islands", text="Bridge islands")

		col.separator()
		col.label("Selection control")
		col.operator("mesh.wplvert_selvisible", text="Select visible")
		col.operator("mesh.wplvert_deselvisible", text="Deselect visible")
		col.operator("mesh.wplvert_deselunvisible", text="Deselect invisible")

		col.separator()
		col.label("Flattening")
		col.operator("mesh.wplproj_flatten", text="Projected flatten")
		col.operator("mesh.wpluv_flatten", text="UVMap flatten")

		col.separator()
		col.label("Weight control")
		#col.prop(wplScultSets, "weig_stp")
		row1 = col.row()
		row1.operator("mesh.wplweig_edt", text="+").opt_stepmul = 1.0
		row1.operator("mesh.wplweig_edt", text="-").opt_stepmul = -1.0
		row1.operator("mesh.wplweig_edt", text="=").opt_stepmul = 0.0

#class WPLSculptSettings(PropertyGroup):
#	weig_stp = FloatProperty(
#		name = "Weight value",
#		description = "Value to add/substruct",
#		default = 1.0
#	)

def register():
	print("WPLSculptFeatures_Panel registered")
	bpy.utils.register_module(__name__)
	#bpy.types.Scene.wplScultSets = PointerProperty(type=WPLSculptSettings)

def unregister():
	bpy.utils.unregister_module(__name__)
	#del bpy.types.Scene.wplScultSets

if __name__ == "__main__":
	register()
