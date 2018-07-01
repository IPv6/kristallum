import math
import copy
import mathutils
import time
import random
from mathutils import kdtree
from random import random, seed
import numpy as np
import datetime

import bpy
from bpy.props import *
import bpy.types
import bmesh
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

bl_info = {
	"name": "WPL Garment tools",
	"author": "IPv6",
	"version": (1, 0, 0),
	"blender": (2, 7, 9),
	"location": "View3D > T-panel > WPL",
	"warning": "",
	"wiki_url": "",
	"tracker_url": "",
	"category": ""}

kRaycastEpsilon = 0.0001
kDisplaceDefault = 0.005
kWPLSmoothHolderUVMap4 = "_tmpMeshPinstate4"

########### ############ ########### ############ ########### ############ ########### ############
########### ############ ########### ############ ########### ############ ########### ############
def select_and_change_mode(obj, obj_mode):
	#print("select_and_change_mode",obj_mode)
	m = bpy.context.mode
	if obj_mode == "EDIT_MESH":
		obj_mode = "EDIT"
	if obj_mode == "PAINT_VERTEX":
		obj_mode = "VERTEX_PAINT"
	if (obj is not None and bpy.context.scene.objects.active != obj) or m != 'OBJECT':
		# stepping out from currently active object mode, or switch may fail
		bpy.ops.object.mode_set(mode='OBJECT')
	for objx in bpy.data.objects:
		objx.select = False
	if obj:
		if obj.hide == True:
			obj.hide = False
		obj.select = True
		bpy.context.scene.objects.active = obj
		bpy.context.scene.update()
		bpy.ops.object.mode_set(mode=obj_mode)
	return m

def get_selected_facesIdx(active_mesh):
	# find selected faces
	bpy.ops.object.mode_set(mode='OBJECT')
	faces = [f.index for f in active_mesh.polygons if f.select]
	# print("selected faces: ", faces)
	return faces
def get_selected_vertsIdx(active_mesh):
	bpy.ops.object.mode_set(mode='OBJECT')
	selectedVertsIdx = [e.index for e in active_mesh.vertices if e.select]
	return selectedVertsIdx

def get_vertgroup_by_name(obj,group_name):
	if group_name in obj.vertex_groups:
		return obj.vertex_groups[group_name]
	return None
def remove_vertgroups_all(obj):
	obj.vertex_groups.clear()
def remove_vertgroup(obj, group_name):
	vertgroup = get_vertgroup_by_name(obj, group_name)
	if vertgroup:
		obj.vertex_groups.remove(vertgroup)
def getornew_vertgroup(obj, group_name):
	vertgroup = get_vertgroup_by_name(obj, group_name)
	if vertgroup is None:
		vertgroup = obj.vertex_groups.new(name=group_name)
	return vertgroup
def get_less_vertsMap_v01(obj, set_of_vertsIdx, iterations=1):
	polygons = obj.data.polygons
	vertices = obj.data.vertices
	vert2loopMap = {}
	for vIdx in set_of_vertsIdx:
		vert2loopMap[vIdx] = 1.0
	while iterations != 0:
		verts_to_remove = set()
		for poly in polygons:
			poly_verts_idx = poly.vertices
			for v_idx in poly_verts_idx:
				if v_idx not in set_of_vertsIdx:
					for v_idx in poly_verts_idx:
						verts_to_remove.add(v_idx)
					break
		set_of_vertsIdx.difference_update(verts_to_remove)
		for vIdx in set_of_vertsIdx:
			vert2loopMap[vIdx] = vert2loopMap[vIdx]+1.0
		iterations -= 1
	return vert2loopMap

def getF3cValue(indexCur,indexMax,index50,F3c):
	value = 0.0
	if indexCur<index50:
		value = F3c[0]+(F3c[1]-F3c[0])*(float(indexCur)/max(0.001,index50))
	else:
		value = F3c[1]+(F3c[2]-F3c[1])*(float(indexCur-index50)/max(0.001,indexMax-index50))
	return value

def splitBmVertsByLinks_v02(bm, selverts, onlySel):
	totalIslands = []
	verts2walk = []
	usedverts = []
	if onlySel:
		for v in bm.verts:
			if v.index not in selverts:
				usedverts.append(v.index)
	for rvidx in selverts:
		if rvidx in usedverts:
			continue
		mi = []
		mi.append(rvidx)
		totalIslands.append(mi)
		verts2walk.append(rvidx)
		while len(verts2walk)>0:
			verts2walkNext = []
			for vIdx in verts2walk:
				if vIdx in usedverts:
					continue
				usedverts.append(vIdx)
				if vIdx not in mi:
					mi.append(vIdx)
				v = bm.verts[vIdx]
				for edge in v.link_edges:
					ov = edge.other_vert(v)
					if ov.index in usedverts:
						continue
					verts2walkNext.append(ov.index)
			verts2walk = verts2walkNext
	return totalIslands
def get_bmhistory_vertsIdx(active_bmesh):
	active_bmesh.verts.ensure_lookup_table()
	active_bmesh.verts.index_update()
	selectedVertsIdx = []
	for elem in active_bmesh.select_history:
		if isinstance(elem, bmesh.types.BMVert) and elem.select and elem.hide == 0:
			selectedVertsIdx.append(elem.index)
	return selectedVertsIdx
def get_bmhistory_faceIdx(active_bmesh):
	active_bmesh.faces.ensure_lookup_table()
	active_bmesh.faces.index_update()
	selectedFacesIdx = []
	for elem in active_bmesh.select_history:
		if isinstance(elem, bmesh.types.BMFace) and elem.select and elem.hide == 0:
			selectedFacesIdx.append(elem.index)
	return selectedFacesIdx

def location_to_region(worldcoords):
	out = view3d_utils.location_3d_to_region_2d(bpy.context.region, bpy.context.space_data.region_3d, worldcoords)
	return out

def region_to_location(viewcoords, depthcoords):
	out = view3d_utils.region_2d_to_location_3d(bpy.context.region, bpy.context.space_data.region_3d, viewcoords, depthcoords)
	return out

def get_active_context_cursor(context):
	scene = context.scene
	space = context.space_data
	cursor = (space if space and space.type == 'VIEW_3D' else scene).cursor_location
	return cursor

def projectPointOnPlaneByNormal(pOrig, pTarg, planeNrm):
	vec = pTarg-pOrig
	pTargProjected = pTarg - dot(vec, planeNrm) * planeNrm
	return pTargProjected;

def customAxisMatrix(v_origin, a, b):
	#https://blender.stackexchange.com/questions/30808/how-do-i-construct-a-transformation-matrix-from-3-vertices
	#def make_matrix(v_origin, v2, v3):
	#a = v2-v_origin
	#b = v3-v_origin
	c = a.cross(b)
	if c.magnitude>0:
		c = c.normalized()
	else:
		return None #BaseException("A B C are colinear")
	b2 = c.cross(a).normalized()
	a2 = a.normalized()
	m = Matrix([a2, b2, c]).transposed()
	s = a.magnitude
	m = Matrix.Translation(v_origin) * Matrix.Scale(s,4) * m.to_4x4()
	return m
def recalcPointFromTri2Tri_meth1(src_pt,src_t1,src_t2,src_t3,trg_t1,trg_t2,trg_t3):
	return mathutils.geometry.barycentric_transform(src_pt,src_t1,src_t2,src_t3,trg_t1,trg_t2,trg_t3)
def recalcPointFromTri2Tri_meth2(src_pt,src_t1,src_t2,src_t3,trg_t1,trg_t2,trg_t3):
	src_cntr = (src_t1+src_t2+src_t3)*0.3333
	trg_cntr = (trg_t1+trg_t2+trg_t3)*0.3333
	sm1 = customAxisMatrix(Vector((0,0,0)),(src_t1-src_cntr).normalized(),(src_t2-src_cntr).normalized())
	sm2 = customAxisMatrix(Vector((0,0,0)),(src_t2-src_cntr).normalized(),(src_t3-src_cntr).normalized())
	sm3 = customAxisMatrix(Vector((0,0,0)),(src_t3-src_cntr).normalized(),(src_t1-src_cntr).normalized())
	if sm1 is None or sm2 is None or sm3 is None:
		return None
	tm1 = customAxisMatrix(Vector((0,0,0)),(trg_t1-trg_cntr).normalized(),(trg_t2-trg_cntr).normalized())
	tm2 = customAxisMatrix(Vector((0,0,0)),(trg_t2-trg_cntr).normalized(),(trg_t3-trg_cntr).normalized())
	tm3 = customAxisMatrix(Vector((0,0,0)),(trg_t3-trg_cntr).normalized(),(trg_t1-trg_cntr).normalized())
	if tm1 is None or tm2 is None or tm3 is None:
		return None
	tp1 = trg_cntr+(sm1*(tm1.inverted()*(src_pt-src_cntr)))
	tp2 = trg_cntr+(sm2*(tm2.inverted()*(src_pt-src_cntr)))
	tp3 = trg_cntr+(sm3*(tm3.inverted()*(src_pt-src_cntr)))
	avg_src_pt = (tp1+tp2+tp3)*0.3333
	return avg_src_pt
def recalcPointFromTri2Tri_meth3(src_pt,src_t1,src_t2,src_t3,trg_t1,trg_t2,trg_t3):
	def transfPT(src_pt,p1s,p2s,p3s,p1t,p2t,p3t):
		sm = customAxisMatrix(Vector((0,0,0)),(p2s-p1s).normalized(),(p3s-p1s).normalized())
		tm = customAxisMatrix(Vector((0,0,0)),(p2t-p1t).normalized(),(p3t-p1t).normalized())
		if sm is None or tm is None:
			return None
		return p1t+(sm*(tm.inverted()*(src_pt-p1s)))
	tp1 = transfPT(src_pt,src_t1,src_t2,src_t3,trg_t1,trg_t2,trg_t3)
	tp2 = transfPT(src_pt,src_t2,src_t1,src_t3,trg_t2,trg_t1,trg_t3)
	tp3 = transfPT(src_pt,src_t3,src_t2,src_t1,trg_t3,trg_t2,trg_t1)
	if tp1 is None or tp2 is None or tp3 is None:
		return None
	avg_src_pt = (tp1+tp2+tp3)*0.3333
	return avg_src_pt

def copyBpyStructFields(bpyFrom, bpyTo, fieldsCopy, filedSkip):
	print("copyBpyStructFields", bpyFrom, bpyTo)
	if bpyTo is None:
		return
	if isinstance(bpyFrom,dict):
		bpyFromDirItems = bpyFrom.keys()
	else:
		bpyFromDirItems = dir(bpyFrom)
	for property in bpyFromDirItems:
		#print("copyBpyStructFields",property)
		if "__" in property:
			continue
		inPropChanged = 0
		if filedSkip is not None:
			for fld in filedSkip:
				if fld in property:
					inPropChanged = -1
					break
		if inPropChanged >= 0:
			for fld in fieldsCopy:
				if (fld in property):
					if isinstance(bpyFrom,dict):
						val = bpyFrom[property]
					else:
						val = getattr(bpyFrom,property)
					if val is None or isinstance(val, str) or isinstance(val, int) or isinstance(val, float) or isinstance(val, bool) or isinstance(val, bpy.types.Object):
						#print("- updating field",property,"to",val)
						if isinstance(bpyTo,dict):
							bpyTo[property] = val
						else:
							setattr(bpyTo, property, val)
						inPropChanged = inPropChanged+1
						break
					#else:
					#	print("- skipping by type",type(val))
		if inPropChanged <= 0:
			print("- skipping field",property)

class WPLbake_normalize_uv(bpy.types.Operator):
	bl_idname = "object.wplbake_normalize_uv"
	bl_label = "UV: Normalize UVs"
	bl_options = {'REGISTER', 'UNDO'}

	EvalUV = StringProperty(
		name = "UV=",
		default = "(U, V) #((U-0.5)*0.049, (V-0.5)*0.045)"
	)
	
	opt_swapUV = BoolProperty(
		name="Swap UV",
		default=False,
	)
	
	@classmethod
	def poll(self, context):
		# Check if we have a mesh object active
		p = context.object and context.object.data and (isinstance(context.scene.objects.active, bpy.types.Object) and isinstance(context.scene.objects.active.data, bpy.types.Mesh))
		return p

	def execute(self, context):
		wpl_propToolOpts = context.scene.wpl_propToolOpts
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		selverts = get_selected_vertsIdx(active_mesh)
		selfaces = get_selected_facesIdx(active_mesh)
		if len(selverts) == 0 or len(selfaces) == 0:
			self.report({'ERROR'}, "No verts selected, select some verts first")
			return {'FINISHED'}
		EvalUV_py = None
		try:
			EvalUV_py = compile(self.EvalUV, "<string>", "eval")
		except:
			self.report({'ERROR'}, "Eval compilation: syntax error")
			return {'CANCELLED'}
		bpy.ops.object.mode_set(mode='OBJECT')
		bakemap_pref = wpl_propToolOpts.bake_uvbase
		uv_layer_ob = active_mesh.uv_textures.get(bakemap_pref)
		if uv_layer_ob is None:
			active_mesh.uv_textures.new(bakemap_pref)

		uv_vals = {}
		bm = bmesh.new()
		bm.from_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		uv_layer_ob = bm.loops.layers.uv.get(bakemap_pref)
		for face in bm.faces:
			if face.index not in selfaces:
				continue
			for loop in face.loops:
				vert = loop.vert
				if (vert.index in selverts):
					if vert.index not in uv_vals:
						uv_vals[vert.index] = [-9999,-9999]
					uv_vals[vert.index] = [max(uv_vals[vert.index][0],loop[uv_layer_ob].uv[0]),max(uv_vals[vert.index][1],loop[uv_layer_ob].uv[1])]
		uv_islanmin = [9999,9999]
		uv_islanmax = [-9999,-9999]
		nrm0 = 0.0
		nrm1 = 1.0
		for vIdx in uv_vals:
			uv_islanmin[0] = min(uv_vals[vIdx][0],uv_islanmin[0])
			uv_islanmin[1] = min(uv_vals[vIdx][1],uv_islanmin[1])
			uv_islanmax[0] = max(uv_vals[vIdx][0],uv_islanmax[0])
			uv_islanmax[1] = max(uv_vals[vIdx][1],uv_islanmax[1])
		if abs(uv_islanmax[0]-uv_islanmin[0])>0.0001 and abs(uv_islanmax[1]-uv_islanmin[1])>0.0001:
			for vIdx in uv_vals:
				facU = (uv_vals[vIdx][0]-uv_islanmin[0])/(uv_islanmax[0]-uv_islanmin[0])
				facV = (uv_vals[vIdx][1]-uv_islanmin[1])/(uv_islanmax[1]-uv_islanmin[1])
				uv_vals[vIdx][0] = nrm0+facU*(nrm1-nrm0)
				uv_vals[vIdx][1] = nrm0+facV*(nrm1-nrm0)
		else:
			self.report({'ERROR'}, "Normalize skipped, same dimenstions")
			return {'FINISHED'}
		if self.opt_swapUV:
			for vIdx in uv_vals:
				uv_vals[vIdx] = [uv_vals[vIdx][1],uv_vals[vIdx][0]]
		for vIdx in uv_vals:
			U = uv_vals[vIdx][0]
			V = uv_vals[vIdx][1]
			newUV = eval(EvalUV_py)
			uv_vals[vIdx] = [newUV[0],newUV[1]]
		for face in bm.faces:
			if face.index not in selfaces:
				continue
			for loop in face.loops:
				vert = loop.vert
				if (vert.index in uv_vals):
					loop[uv_layer_ob].uv = (uv_vals[vert.index][0],uv_vals[vert.index][1])
		bm.to_mesh(active_mesh)
		bm.free()
		context.scene.update()
		self.report({'INFO'}, "Vertices baked:" + str(len(uv_vals)))
		bpy.ops.object.mode_set(mode='EDIT')
		return {'FINISHED'}
			
# class WPLbake_mesh_centers(bpy.types.Operator):
	# bl_idname = "object.wplbake_mesh_centers"
	# bl_label = "UV: Bake mesh coords"
	# bl_options = {'REGISTER', 'UNDO'}

	# opt_uvinType = EnumProperty(
		# name="Bake Type", default="AVGN",
		# items=(("AVGN", "Average Normal", ""), ("XZ", "Y as Normal", ""), ("YZ", "X as Normal", ""), ("XY", "Z as Normal", ""), ("ACT", "Active vert", ""))
	# )
	# opt_post01Normalize = BoolProperty(
		# name="Map to (0,1) range",
		# default=False,
	# )
	# opt_offset = FloatVectorProperty(
		# name = "Axis Shift",
		# size = 2,
		# default = (0.0,0.0)
	# )
	# opt_scale = FloatVectorProperty(
		# name = "Axis scale",
		# size = 2,
		# default = (1.0,1.0)
	# )

	# @classmethod
	# def poll(self, context):
		# p = context.object and context.object.data and (isinstance(context.scene.objects.active, bpy.types.Object) and isinstance(context.scene.objects.active.data, bpy.types.Mesh))
		# return p

	# def execute(self, context):
		# wpl_propToolOpts = context.scene.wpl_propToolOpts
		# active_obj = context.scene.objects.active
		# active_mesh = active_obj.data
		# selverts = get_selected_vertsIdx(active_mesh)
		# if len(selverts) == 0:
			# self.report({'ERROR'}, "No verts selected, select some verts first")
			# return {'FINISHED'}
		# bpy.ops.object.mode_set(mode='OBJECT')

		# matrix_world_inv = active_obj.matrix_world.inverted()
		# matrix_world_norm = matrix_world_inv.transposed().to_3x3()
		# bakemap_pref = wpl_propToolOpts.bake_uvbase
		# uv_layer_ob = active_mesh.uv_textures.get(bakemap_pref)
		# if uv_layer_ob is None:
			# active_mesh.uv_textures.new(bakemap_pref)

		# bm = bmesh.new()
		# bm.from_mesh(active_mesh)
		# bm.verts.ensure_lookup_table()
		# bm.faces.ensure_lookup_table()
		# bm.verts.index_update()
		# if bpy.context.tool_settings.mesh_select_mode[2] == True:
			# histFacesIdx = get_bmhistory_faceIdx(bm)
			# histVertsIdx = []
		# else:
			# histVertsIdx = get_bmhistory_vertsIdx(bm)
			# histFacesIdx = []
		# g_activeVertCo = None
		# g_activeVertNrm = None
		# if len(histVertsIdx)>0:
			# g_activeVertCo = active_obj.matrix_world*bm.verts[histVertsIdx[0]].co
			# g_activeVertNrm = matrix_world_norm*bm.verts[histVertsIdx[0]].normal
		# elif len(histFacesIdx)>0:
			# g_activeVertCo = active_obj.matrix_world*bm.faces[histFacesIdx[0]].calc_center_median()
			# g_activeVertNrm = matrix_world_norm*bm.faces[histFacesIdx[0]].normal
		# if g_activeVertCo is None and self.opt_uvinType == 'ACT':
			# self.report({'ERROR'}, "No active vert/face found")
			# return {'FINISHED'}
		# uv_values1 = {}
		# uv_values2 = {}
		# uv_normals = {}
		# uv_islanid = {}
		# uv_projeca = {}
		# islid = 0
		# selVertsIslandsed = splitBmVertsByLinks_v02(bm, selverts, False)
		# for meshlistAll in selVertsIslandsed:
			# meshlist = [vIdx for vIdx in meshlistAll if vIdx in selverts]
			# if len(meshlist) > 0:
				# islid = islid+1
				# medianpoint = mathutils.Vector()
				# mediannormal = mathutils.Vector()
				# medianpointMin = [9999,9999,9999]
				# medianpointMax = [-9999,-9999,-9999]
				# for mvIdx in meshlist:
					# mv = bm.verts[mvIdx]
					# mv_co = active_obj.matrix_world*mv.co
					# medianpoint = medianpoint+mv_co
					# mediannormal = mediannormal+matrix_world_norm*mv.normal
					# medianpointMin[0] = min(medianpointMin[0],mv_co[0])
					# medianpointMin[1] = min(medianpointMin[1],mv_co[1])
					# medianpointMin[2] = min(medianpointMin[2],mv_co[2])
					# medianpointMax[0] = max(medianpointMax[0],mv_co[0])
					# medianpointMax[1] = max(medianpointMax[1],mv_co[1])
					# medianpointMax[2] = max(medianpointMax[2],mv_co[2])
				# medianpoint = medianpoint/len(meshlist)
				# medianpomin = Vector((medianpointMin[0],medianpointMin[1],medianpointMin[2]))
				# medianpomax = Vector((medianpointMax[0],medianpointMax[1],medianpointMax[2]))
				# mediannormal = mediannormal/len(meshlist)
				# mediannormal = mediannormal.normalized()
				# if g_activeVertCo is not None and self.opt_uvinType == 'ACT':
					# medianpoint = g_activeVertCo
					# mediannormal = g_activeVertNrm
				# medianbbvec = (medianpomax-medianpomin).normalized()
				# bbvec_dst = [[(medianbbvec-Vector((0,0,1))).length,Vector((0,0,1))],[(medianbbvec-Vector((0,1,0))).length,Vector((0,1,0))],[(medianbbvec-Vector((1,0,0))).length,Vector((1,0,0))]]
				# bbvec_dst = sorted(bbvec_dst, key=lambda pr: pr[0], reverse=False)
				# ax1 = mediannormal.cross(bbvec_dst[0][1])
				# ax2 = mediannormal.cross(ax1)
				# for mvIdx in meshlist:
					# mv = bm.verts[mvIdx]
					# mv_co = active_obj.matrix_world*mv.co
					# uv_values1[mv.index] = mv_co-medianpoint
					# uv_normals[mv.index] = mediannormal
					# uv_islanid[mv.index] = islid
					# uv_projeca[mv.index] = (ax1,ax2)
		# if len(uv_values1)>0:
			# projNrml = None
			# if self.opt_uvinType == 'XY':
				# projNrml = (Vector((1,0,0)),Vector((0,1,0)))
			# if self.opt_uvinType == 'XZ':
				# projNrml = (Vector((1,0,0)),Vector((0,0,1)))
			# if self.opt_uvinType == 'YZ':
				# projNrml = (Vector((0,1,0)),Vector((0,0,1)))
			# for vIdx in uv_values1:
				# proj = projNrml
				# if proj is None:
					# proj = uv_projeca[vIdx]
				# pt_mat = customAxisMatrix(Vector((0,0,0)),proj[0],proj[1])
				# if pt_mat is None:
					# self.report({'INFO'}, "Colinear axis found, bake skipped")
					# return {'FINISHED'}
				# newCo = pt_mat*uv_values1[vIdx]
				# uv_values2[vIdx] = [newCo[0],-1*newCo[1]]
			# if self.opt_post01Normalize:
				# uv_islanmin = {}
				# uv_islanmax = {}
				# nrm0 = 0.0
				# nrm1 = 1.0
				# for vIdx in uv_values2:
					# islid = uv_islanid[vIdx]
					# if islid not in uv_islanmin:
						# uv_islanmin[islid] = [9999,9999]
						# uv_islanmax[islid] = [-9999,-9999]
					# uv_islanmin[islid][0] = min(uv_values2[vIdx][0],uv_islanmin[islid][0])
					# uv_islanmin[islid][1] = min(uv_values2[vIdx][1],uv_islanmin[islid][1])
					# uv_islanmax[islid][0] = max(uv_values2[vIdx][0],uv_islanmax[islid][0])
					# uv_islanmax[islid][1] = max(uv_values2[vIdx][1],uv_islanmax[islid][1])
				# for vIdx in uv_values2:
					# islid = uv_islanid[vIdx]
					# if abs(uv_islanmax[islid][0]-uv_islanmin[islid][0])>0.0001 and abs(uv_islanmax[islid][1]-uv_islanmin[islid][1])>0.0001:
						# facU = (uv_values2[vIdx][0]-uv_islanmin[islid][0])/(uv_islanmax[islid][0]-uv_islanmin[islid][0])
						# facV = (uv_values2[vIdx][1]-uv_islanmin[islid][1])/(uv_islanmax[islid][1]-uv_islanmin[islid][1])
						# uv_values2[vIdx][0] = nrm0+facU*(nrm1-nrm0)
						# uv_values2[vIdx][1] = nrm0+facV*(nrm1-nrm0)
					# else:
						# print("- warning: normalize skipped, same dimenstions", uv_islanminmax[islid])
			# for vIdx in uv_values2:
				# newCo = Vector((uv_values2[vIdx][0],uv_values2[vIdx][1],0))
				# val_u = self.opt_scale[0]*newCo[0]+self.opt_offset[0]
				# val_v = self.opt_scale[1]*newCo[1]+self.opt_offset[1]
				# uv_values2[vIdx] = [val_u,val_v]
			# uv_layer_ob = bm.loops.layers.uv.get(bakemap_pref)
			# for face in bm.faces:
				# for loop in face.loops:
					# vert = loop.vert
					# if (vert.index in selverts) and (vert.index in uv_values2):
						# loop[uv_layer_ob].uv = (uv_values2[vert.index][0],uv_values2[vert.index][1])
			# bm.to_mesh(active_mesh)
		# bm.free()
		# context.scene.update()
		# self.report({'INFO'}, "Vertices baked:" + str(len(uv_values2)))
		# return {'FINISHED'}

class wplprops_cpymodifs( bpy.types.Operator ):
	bl_idname = "object.wplprops_cpymodifs"
	bl_label = "Copy modifiers"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll( cls, context ):
		p = (isinstance(context.scene.objects.active, bpy.types.Object))
		return p

	def execute( self, context ):
		wpl_propToolOpts = context.scene.wpl_propToolOpts
		if wpl_propToolOpts.mbh_mask_targ not in bpy.data.objects.keys():
			self.report({'INFO'}, 'No source to get weight')
			return {"CANCELLED"}
		active_obj = bpy.data.objects[wpl_propToolOpts.mbh_mask_targ]
		sel_all = [o.name for o in bpy.context.selected_objects]
		if len(sel_all) == 0:
			self.report({'ERROR'}, "No objects selected")
			return {'CANCELLED'}
		ok = 0
		select_and_change_mode(active_obj,"OBJECT")
		mod_params = None
		for md in active_obj.modifiers:
			if md.type == 'ARMATURE':
				mod_params = {}
				mod_params["name"] = md.name
				mod_params["type"] = md.type
				mod_params["settings_list"] = ["vertex_group","use","object","show"]
				mod_params["settings"] = {}
				copyBpyStructFields(md, mod_params["settings"], mod_params["settings_list"],None)
				break
		if mod_params is None:
			self.report({'ERROR'}, "No modifier found on source")
			return {'CANCELLED'}
		for i, sel_obj_name in enumerate(sel_all):
			sel_obj = context.scene.objects[sel_obj_name]
			if sel_obj.name == active_obj.name:
				continue
			new_modifier = None
			for md in sel_obj.modifiers:
				if md.name == mod_params["name"] and md.type == mod_params["type"]:
					new_modifier = md
					break
			if new_modifier is None:
				new_modifier = sel_obj.modifiers.new(mod_params["name"], mod_params["type"])
			if mod_params["type"] == 'ARMATURE':
				copyBpyStructFields(mod_params["settings"], new_modifier, mod_params["settings_list"], None)

			ok = ok+1
		self.report({'INFO'}, "Transferred to "+str(ok)+" objects")
		return {'FINISHED'}

class wplprops_weitransf( bpy.types.Operator ):
	bl_idname = "object.wplprops_weitransf"
	bl_label = "Mass-adapt weights"
	bl_options = {'REGISTER', 'UNDO'}

	opt_smoothDist = FloatProperty(
		name="Smoothing distance",
		default=2.0,
	)

	def kdtree_from_mesh_vertices(self, obj, mesh):
		vertices = mesh.vertices
		research_tree = mathutils.kdtree.KDTree(len(vertices))
		for idx,vert in enumerate(vertices):
			research_tree.insert(obj.matrix_world*vert.co, idx)
		research_tree.balance()
		return research_tree

	def adapt_weights(self, body, proxy):
		#proxy.vertex_groups.clear()
		body_kd_tree = self.kdtree_from_mesh_vertices(body, body.data)
		proxy_vertices = proxy.data.vertices
		body_verts_weights = [[] for v in body.data.vertices]
		for grp in body.vertex_groups:
			for idx, w_data in enumerate(body_verts_weights):
				try:
					w_data.append([grp.name,grp.weight(idx)])
				except:
					pass #TODO: idx in grp.weight
		for p_idx, proxy_vert in enumerate(proxy_vertices):
			proxy_vert_weights = {}
			nearest_body_vert = body_kd_tree.find(proxy.matrix_world*proxy_vert.co)
			min_dist = nearest_body_vert[2]
			nearest_body_verts = body_kd_tree.find_range(proxy.matrix_world*proxy_vert.co,min_dist*self.opt_smoothDist)
			for nearest_body_vert_data in nearest_body_verts:
				body_vert_idx = nearest_body_vert_data[1]
				body_vert_dist = nearest_body_vert_data[2]
				if body_vert_dist != 0:
					magnitude = min_dist/body_vert_dist
				else:
					magnitude = 1
				group_data = body_verts_weights[body_vert_idx]
				for g_data in group_data:
					if len(g_data) > 0:
						group_name = g_data[0]
						vert_weight = g_data[1]
					if group_name in proxy_vert_weights:
						proxy_vert_weights[group_name] += vert_weight*magnitude
					else:
						proxy_vert_weights[group_name] = vert_weight*magnitude
			#Weights normalize
			weights_sum = 0
			for vert_weight in proxy_vert_weights.values():
				weights_sum += vert_weight
			for group_name,vert_weight in proxy_vert_weights.items():
				proxy_vert_weights[group_name] = vert_weight/weights_sum
			for group_name,vert_weight in proxy_vert_weights.items():
					if group_name not in proxy.vertex_groups:
						proxy.vertex_groups.new(name=group_name)
					g = proxy.vertex_groups[group_name]
					g.add([p_idx], vert_weight, 'REPLACE')

	@classmethod
	def poll( cls, context ):
		p = (isinstance(context.scene.objects.active, bpy.types.Object))
		return p

	def execute( self, context ):
		wpl_propToolOpts = context.scene.wpl_propToolOpts
		if wpl_propToolOpts.mbh_mask_targ not in bpy.data.objects.keys():
			self.report({'INFO'}, 'No source to get weight')
			return {"CANCELLED"}
		active_obj = bpy.data.objects[wpl_propToolOpts.mbh_mask_targ]
		if active_obj.type != 'MESH':
			self.report({'INFO'}, 'Source is not a mesh')
			return {"CANCELLED"}
		sel_all = [o.name for o in bpy.context.selected_objects]
		if len(sel_all) == 0:
			self.report({'ERROR'}, "No objects selected")
			return {'CANCELLED'}
		ok = 0
		body_cloned = active_obj.copy()
		body_cloned.data = body_cloned.data.copy()
		bpy.context.scene.objects.link(body_cloned)
		select_and_change_mode(body_cloned,"OBJECT")
		for mod in body_cloned.modifiers:
			bpy.ops.object.modifier_apply(modifier = mod.name)
		for i, sel_obj_name in enumerate(sel_all):
			sel_obj = context.scene.objects[sel_obj_name]
			if sel_obj.name == active_obj.name or sel_obj.name == body_cloned.name:
				continue
			if sel_obj.type != 'MESH':
				continue
			self.adapt_weights(body_cloned,sel_obj)
			ok = ok+1
		select_and_change_mode(active_obj,"OBJECT")
		bpy.data.objects.remove(body_cloned, True)
		self.report({'INFO'}, "Transferred to "+str(ok)+" objects")
		return {'FINISHED'}

class wplprops_datatransf( bpy.types.Operator ):
	bl_idname = "object.wplprops_datatransf"
	bl_label = "Mass-transfer data"
	bl_options = {'REGISTER', 'UNDO'}

	opt_tranfType = bpy.props.EnumProperty(
		name="Data type", default="WEI",
		items=(("WEI", "Weights", ""), ("VC", "Vertex colors", ""))
	)

	@classmethod
	def poll( cls, context ):
		p = (isinstance(context.scene.objects.active, bpy.types.Object))
		return p

	def execute( self, context ):
		wpl_propToolOpts = context.scene.wpl_propToolOpts
		if wpl_propToolOpts.mbh_mask_targ not in bpy.data.objects.keys():
			self.report({'INFO'}, 'No source to get weight')
			return {"CANCELLED"}
		active_obj = bpy.data.objects[wpl_propToolOpts.mbh_mask_targ]
		if active_obj.type != 'MESH':
			self.report({'INFO'}, 'Source is not a mesh')
			return {"CANCELLED"}
		sel_all = [o.name for o in bpy.context.selected_objects]
		if len(sel_all) == 0:
			self.report({'ERROR'}, "No objects selected")
			return {'CANCELLED'}
		ok = 0
		select_and_change_mode(active_obj,"OBJECT")
		for i, sel_obj_name in enumerate(sel_all):
			sel_obj = context.scene.objects[sel_obj_name]
			if sel_obj.name == active_obj.name:
				continue
			if sel_obj.type != 'MESH':
				continue
			needReset_R_vgs = False
			for md in sel_obj.modifiers:
				if md.type == 'MIRROR':
					if self.opt_tranfType == "WEI":
						needReset_R_vgs = True
						break
					else:
						self.report({'ERROR'}, "Error: Object with MIRROR modifer.")
						return {'CANCELLED'}
			select_and_change_mode(sel_obj,"OBJECT")
			print("Handling object "+str(i+1)+" of "+str(len(sel_all)))
			modname = "sys_dataTransfer"
			bpy.ops.object.modifier_remove(modifier=modname)
			modifiers = sel_obj.modifiers
			dt_modifier = modifiers.new(name = modname, type = 'DATA_TRANSFER')
			if dt_modifier is not None:
				if self.opt_tranfType == "WEI":
					dt_modifier.use_vert_data = True
					dt_modifier.data_types_verts = {'VGROUP_WEIGHTS'}
					dt_modifier.vert_mapping = 'POLYINTERP_NEAREST' #POLY_NEAREST
					dt_modifier.layers_vgroup_select_src = 'ALL'
					dt_modifier.layers_vgroup_select_dst = 'NAME'
				if self.opt_tranfType == "VC":
					dt_modifier.use_loop_data = True
					dt_modifier.data_types_loops = {'VCOL'}
					dt_modifier.loop_mapping = 'POLYINTERP_NEAREST'
					dt_modifier.layers_vcol_select_src = 'ALL'
					dt_modifier.layers_vcol_select_dst = 'NAME'
				dt_modifier.object = active_obj
				while sel_obj.modifiers[0].name != modname:
					bpy.ops.object.modifier_move_up(modifier=modname)
				bpy.ops.object.datalayout_transfer(modifier=modname)
				bpy.ops.object.modifier_apply(apply_as='DATA', modifier=modname)
				if needReset_R_vgs:
					names = [group.name for group in sel_obj.vertex_groups if "_L" in group.name]
					for group_name in names:
						vertgroup = sel_obj.vertex_groups[group_name]
						sel_obj.vertex_groups.remove(vertgroup)
						sel_obj.vertex_groups.new(name=group_name)
				ok = ok+1
		select_and_change_mode(active_obj,"OBJECT")
		self.report({'INFO'}, "Transferred to "+str(ok)+" objects")
		return {'FINISHED'}

# class wplprops_maskgarm( bpy.types.Operator ):
# 	bl_idname = "object.wplprops_maskgarm"
# 	bl_label = "Mask from selection"
# 	bl_options = {'REGISTER', 'UNDO'}
# 	opt_displInfluence = FloatProperty(
# 			name="Displace (0 to hide)",
# 			min=-100, max=100,
# 			step=0.005,
# 			default=kDisplaceDefault,
# 	)
# 	opt_preSubdiv = IntProperty(
# 			name="Pre-subdiv garment",
# 			min=0, max=10,
# 			default=1,
# 	)
# 	opt_dist2hide = FloatProperty(
# 			name="Vert distance",
# 			min=0.00001, max=100.0,
# 			step=0.01,
# 			default=0.01,
# 	)
# 	opt_insetLoops = IntProperty(
# 			name="Post-inset edges (loops)",
# 			min=0, max=100,
# 			default=1,
# 	)
#
# 	@classmethod
# 	def poll( cls, context ):
# 		p = (isinstance(context.scene.objects.active, bpy.types.Object))
# 		return p
#
# 	def execute( self, context ):
# 		wpl_propToolOpts = context.scene.wpl_propToolOpts
# 		if wpl_propToolOpts.mbh_mask_targ not in bpy.data.objects.keys():
# 			self.report({'INFO'}, 'Body not found')
# 			return {"CANCELLED"}
# 		sel_all = [o.name for o in bpy.context.selected_objects]
# 		if len(sel_all) == 0:
# 			self.report({'ERROR'}, "No objects selected")
# 			return {'CANCELLED'}
#
# 		active_obj = bpy.data.objects[wpl_propToolOpts.mbh_mask_targ]
# 		if active_obj.type != 'MESH':
# 			self.report({'ERROR'}, "Body must be MESH")
# 			return {'CANCELLED'}
# 		select_and_change_mode(active_obj,"OBJECT")
#
# 		bmFromAct = bmesh.new()
# 		bmFromAct.from_object(active_obj, context.scene, deform=True, render=False, cage=True, face_normals=True)
# 		bmFromAct.transform(active_obj.matrix_world)
# 		bmFromAct.verts.ensure_lookup_table()
# 		bmFromAct.faces.ensure_lookup_table()
# 		bmFromAct.verts.index_update()
# 		bmFromAct.faces.index_update()
# 		vertsSet = []
# 		for i, sel_obj_name in enumerate(sel_all):
# 			sel_obj = context.scene.objects[sel_obj_name]
# 			if sel_obj.name == active_obj.name or sel_obj.type == 'EMPTY':
# 				continue
# 			print("Handling object "+str(i+1)+" of "+str(len(sel_all)))
# 			#main bvh
# 			sel_obj_mesh = sel_obj.to_mesh(context.scene, True, 'PREVIEW')
# 			bmFromSel = bmesh.new()
# 			bmFromSel.from_mesh(sel_obj_mesh)
# 			bpy.data.meshes.remove(sel_obj_mesh)
# 			if self.opt_preSubdiv > 0:
# 				bmesh.ops.subdivide_edges(bmFromSel,edges=bmFromSel.edges[:], cuts=self.opt_preSubdiv, use_grid_fill=True, use_single_edge=True)
# 			bmFromSel.transform(sel_obj.matrix_world)
# 			bvhGlobSel = BVHTree.FromBMesh(bmFromSel, epsilon = kRaycastEpsilon)
# 			modname = "mask_"+sel_obj.name
# 			remove_vertgroup(active_obj,"sys_"+modname)
# 			mask_group = getornew_vertgroup(active_obj,"sys_"+modname)
# 			vert2nearmap = set()
# 			for i, vert in enumerate(bmFromAct.verts):
# 				s_location, s_normal, s_index, s_distance = bvhGlobSel.find_nearest(vert.co, self.opt_dist2hide)
# 				if s_location is not None:
# 					vert2nearmap.add(vert.index)
# 			get_less_vertsMap_v01(active_obj, vert2nearmap, self.opt_insetLoops)
# 			for i, vert in enumerate(bmFromAct.verts):
# 				if vert.index in vert2nearmap:
# 					if vert.index not in vertsSet:
# 						vertsSet.append(vert.index)
# 					mask_group.add([vert.index], 1.0, 'ADD')
# 			bpy.ops.object.modifier_remove(modifier=modname)
# 			modifiers = active_obj.modifiers
# 			if self.opt_displInfluence == 0.0:
# 				mask_modifier = modifiers.new(name = modname, type = 'MASK')
# 				mask_modifier.vertex_group = mask_group.name
# 				mask_modifier.invert_vertex_group = True
# 			else:
# 				mask_modifier = modifiers.new(name = modname, type = 'DISPLACE')
# 				mask_modifier.direction = 'NORMAL'
# 				mask_modifier.mid_level = 0.0
# 				mask_modifier.strength = -1*self.opt_displInfluence
# 				mask_modifier.vertex_group = mask_group.name
# 			bmFromSel.free()
# 		bmFromAct.free()
# 		select_and_change_mode(active_obj,"EDIT")
# 		bpy.ops.mesh.select_mode(type="VERT")
# 		bpy.ops.mesh.select_all(action = 'DESELECT')
# 		bpy.ops.object.mode_set(mode='OBJECT')
# 		active_mesh = active_obj.data
# 		for v in active_mesh.vertices:
# 			if v.index in vertsSet:
# 				active_mesh.vertices[v.index].select = True
# 		return {'FINISHED'}

class wplprops_maskgarm2( bpy.types.Operator ):
	bl_idname = "object.wplprops_maskgarm2"
	bl_label = "Bake distances"
	bl_options = {'REGISTER', 'UNDO'}
	opt_preSubdiv = IntProperty(
			name="Pre-subdiv garment",
			min=0, max=10,
			default=1,
	)
	opt_displaceVal = FloatProperty(
			name="Displace amount",
			min=-10, max=10,
			default=-0.002,
	)
	opt_recreateUVMap = BoolProperty(
		name="Replace all",
		default=True,
	)
	@classmethod
	def poll( cls, context ):
		p = (isinstance(context.scene.objects.active, bpy.types.Object))
		return p

	def execute( self, context ):
		wpl_propToolOpts = context.scene.wpl_propToolOpts
		if wpl_propToolOpts.mbh_mask_targ not in bpy.data.objects.keys():
			self.report({'INFO'}, 'Body not found')
			return {"CANCELLED"}
		sel_all = [o.name for o in bpy.context.selected_objects]
		if len(sel_all) == 0:
			self.report({'ERROR'}, "No objects selected")
			return {'CANCELLED'}

		active_obj = bpy.data.objects[wpl_propToolOpts.mbh_mask_targ]
		if active_obj.type != 'MESH':
			self.report({'ERROR'}, "Body must be MESH")
			return {'CANCELLED'}
		active_mesh = active_obj.data
		bmFromAct = bmesh.new()
		bmFromAct.from_object(active_obj, context.scene, deform=True, render=False, cage=True, face_normals=True)
		bmFromAct.transform(active_obj.matrix_world)
		bmFromAct.verts.ensure_lookup_table()
		bmFromAct.faces.ensure_lookup_table()
		bmFromAct.verts.index_update()
		bmFromAct.faces.index_update()
		vert2nearmap = {}
		for i, sel_obj_name in enumerate(sel_all):
			sel_obj = context.scene.objects[sel_obj_name]
			if sel_obj.name == active_obj.name or sel_obj.type == 'EMPTY':
				continue
			print("Handling object "+str(i+1)+" of "+str(len(sel_all)))
			#main bvh
			sel_obj_mesh = sel_obj.to_mesh(context.scene, True, 'PREVIEW')
			bmFromSel = bmesh.new()
			bmFromSel.from_mesh(sel_obj_mesh)
			bpy.data.meshes.remove(sel_obj_mesh)
			if self.opt_preSubdiv > 0:
				bmesh.ops.subdivide_edges(bmFromSel,edges=bmFromSel.edges[:], cuts=self.opt_preSubdiv, use_grid_fill=True, use_single_edge=True)
			bmFromSel.transform(sel_obj.matrix_world)
			bvhGlobSel = BVHTree.FromBMesh(bmFromSel, epsilon = kRaycastEpsilon)
			for i, vert in enumerate(bmFromAct.verts):
				s_location, s_normal, s_index, s_distance = bvhGlobSel.find_nearest(vert.co, 999)
				if s_location is not None:
					if vert.index not in vert2nearmap or s_distance<vert2nearmap[vert.index]:
						vert2nearmap[vert.index] = s_distance
			bmFromSel.free()
		bmFromAct.free()
		# setting mbh_mask_dist_uv values
		bakemap_pref = wpl_propToolOpts.mbh_mask_dist_uv
		uv_layer_ob = active_mesh.uv_textures.get(bakemap_pref)
		if uv_layer_ob is None:
			active_mesh.uv_textures.new(bakemap_pref)
		bm = bmesh.new()
		bm.from_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		uv_layer_ob = bm.loops.layers.uv.get(bakemap_pref)
		okCnt = 0
		# UV: V MUST be != 0. To check where UV is here or not
		if abs(self.opt_displaceVal) < 0.00001:
			self.opt_displaceVal = 0.00001
		for face in bm.faces:
			for loop in face.loops:
				vert = loop.vert
				if (vert.index in vert2nearmap):
					v_dist = vert2nearmap[vert.index]
					if self.opt_recreateUVMap == False:
						if loop[uv_layer_ob].uv[0] < v_dist:
							continue
					okCnt = okCnt+1
					loop[uv_layer_ob].uv = (v_dist,self.opt_displaceVal)
				else:
					if self.opt_recreateUVMap:
						loop[uv_layer_ob].uv = (999,self.opt_displaceVal)
		bm.to_mesh(active_mesh)
		self.report({'INFO'}, "Done, "+str(okCnt)+" verts baked")
		return {'FINISHED'}

class wplprops_stepphysics( bpy.types.Operator ):
	bl_idname = "object.wplprops_stepphysics"
	bl_label = "Step and Apply physics"
	bl_options = {'REGISTER', 'UNDO'}

	opt_framesToSim = IntProperty(
		name = "Frames",
		default = 10
	)

	@classmethod
	def poll( cls, context ):
		p = (isinstance(context.scene.objects.active, bpy.types.Object))
		return p

	def execute( self, context ):
		active_obj = context.scene.objects.active
		if active_obj is None:
			self.report({'ERROR'}, "No active object found")
			return {'CANCELLED'}
		active_mesh = active_obj.data
		cur_frame = context.scene.frame_current
		end_frame = cur_frame+self.opt_framesToSim
		print("Saving modifiers...")
		phys_mod = None
		phys_mod_params = {}
		for md in active_obj.modifiers:
			if md.type == 'CLOTH':
				phys_mod = md
				phys_mod_params["name"] = phys_mod.name
				phys_mod_params["type"] = phys_mod.type
				phys_mod_params["settings"] = {}
				phys_mod_params["settings_list"] = ["damping","stiffness","friction","density","goal","gravity","mass","quality","rest_shape_key","force","shrink","time_scale","use","group","voxel_cell_size"]
				phys_mod_params["collision_settings"] = {}
				phys_mod_params["collision_settings_list"] = ["collision","distance","self","use","damping","friction","group","repel_force"]
				phys_mod_params["effector_weights"] = {}
				phys_mod_params["effector_weights_list"] = ["all","apply","boid","charge","curve_guide","drag","force","gravity","group","harmonic","lennardjones","magnetic","smokeflow","texture","turbulence","vortex","wind"]
				copyBpyStructFields(phys_mod.settings, phys_mod_params["settings"], phys_mod_params["settings_list"],None) #["effector_weights"]
				copyBpyStructFields(phys_mod.collision_settings, phys_mod_params["collision_settings"], phys_mod_params["collision_settings_list"], None)
				copyBpyStructFields(phys_mod.settings.effector_weights, phys_mod_params["effector_weights"], phys_mod_params["effector_weights_list"], None)
				break
			if md.type == 'SOFT_BODY':
				phys_mod = md
				phys_mod_params["name"] = phys_mod.name
				phys_mod_params["type"] = phys_mod.type
				phys_mod_params["settings"] = {}
				phys_mod_params["settings_list"] = ["aero","aerodynamics_type","ball","bend","choke","collision","damping","error_threshold","friction","fuzzy","goal","gravity","mass","plastic","pull","push","estimate","shear","speed","spring","step","use","vertex"]
				phys_mod_params["effector_weights"] = {}
				phys_mod_params["effector_weights_list"] = ["all","apply","boid","charge","curve_guide","drag","force","gravity","group","harmonic","lennardjones","magnetic","smokeflow","texture","turbulence","vortex","wind"]
				copyBpyStructFields(phys_mod.settings, phys_mod_params["settings"], phys_mod_params["settings_list"], None)
				copyBpyStructFields(phys_mod.settings.effector_weights, phys_mod_params["effector_weights"], phys_mod_params["effector_weights_list"], None)
				break
		if phys_mod is not None:
			print("Baking physics... ","-frames:",(end_frame-cur_frame),"-time:",datetime.datetime.now())
			bpy.context.scene.frame_set(cur_frame)
			phys_mod.point_cache.frame_start = cur_frame
			phys_mod.point_cache.frame_end = end_frame
			bpy.ops.ptcache.bake_all(bake=True)
			print("Baking done!... ","-time:",datetime.datetime.now())
		print("Switching frame...")
		bpy.context.scene.frame_set(end_frame)
		bpy.context.scene.update()
		if phys_mod is not None:
			#if phys_mod.type == 'CLOTH':
			#bpy.ops.object.convert(target='MESH', keep_original=False)
			#if phys_mod.type == 'SOFT_BODY':
			bpy.ops.object.modifier_apply(apply_as='DATA', modifier=phys_mod.name)
		else:
			bpy.ops.object.convert(target='MESH', keep_original=False)
		new_mat = active_obj.matrix_world
		print("Going back...")
		bpy.context.scene.frame_set(cur_frame)
		bpy.context.scene.update()
		print("Restoring modifiers...")
		active_obj.matrix_world = new_mat
		if phys_mod is not None:
			newphys_modifier = active_obj.modifiers.new(phys_mod_params["name"], phys_mod_params["type"])
			if phys_mod_params["type"] == 'CLOTH':
				copyBpyStructFields(phys_mod_params["settings"], newphys_modifier.settings, phys_mod_params["settings_list"], None) #["effector_weights"]
				copyBpyStructFields(phys_mod_params["collision_settings"], newphys_modifier.collision_settings, phys_mod_params["collision_settings_list"], None)
				copyBpyStructFields(phys_mod_params["effector_weights"], newphys_modifier.settings.effector_weights, phys_mod_params["effector_weights_list"], None)
			if phys_mod_params["type"] == 'SOFT_BODY':
				copyBpyStructFields(phys_mod_params["settings"], newphys_modifier.settings, phys_mod_params["settings_list"], None)
				copyBpyStructFields(phys_mod_params["effector_weights"], newphys_modifier.settings.effector_weights, phys_mod_params["effector_weights_list"], None)
			bpy.ops.ptcache.free_bake_all()
		print("Done!")
		return {'FINISHED'}

class WPLweig_edt( bpy.types.Operator ):
	bl_idname = "mesh.wplweig_edt"
	bl_label = "Weight: inc/dec selected"
	bl_options = {'REGISTER', 'UNDO'}
	opt_stepadd = bpy.props.FloatProperty(
		name		= "Additional step",
		default	 	= 0.0
		)
	opt_stepmul = bpy.props.FloatProperty(
		name		= "Step fac",
		default	 	= 1.0
		)
	opt_oldmul = bpy.props.FloatProperty(
		name		= "Mix fac",
		default	 	= 1.0
		)

	@classmethod
	def poll( cls, context ):
		return ( context.object is not None and
				context.object.type == 'MESH' )

	def execute( self, context ):
		oldmode = context.scene.objects.active.mode
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		wpl_propToolOpts = context.scene.wpl_propToolOpts
		selvertsAll = get_selected_vertsIdx(active_mesh)
		if len(selvertsAll) == 0:
			self.report({'ERROR'}, "No selected vertices found")
			return {'CANCELLED'}
		select_and_change_mode(active_obj,"OBJECT")
		vg = active_obj.vertex_groups.get(wpl_propToolOpts.wei_gropnm)
		if vg is None:
			if len(wpl_propToolOpts.wei_gropnm) == 0:
				self.report({'ERROR'}, "No active vertex group found")
				return {'CANCELLED'}
			self.report({'INFO'}, "Vertex group not found, creating new")
			vg = active_obj.vertex_groups.new(wpl_propToolOpts.wei_gropnm)
			wpl_propToolOpts.wei_gropnm = vg.name
		active_obj.vertex_groups.active_index = vg.index
		stepval = wpl_propToolOpts.wei_value
		for idx in selvertsAll:
			wmod = 'REPLACE'
			try:
				oldval = vg.weight(idx)
			except Exception as e:
				wmod = 'ADD'
				oldval = 0
			newval = oldval*self.opt_oldmul+self.opt_stepmul*stepval+self.opt_stepadd
			vg.add([idx], newval, wmod)
		if oldmode != 'EDIT':
			select_and_change_mode(active_obj,"EDIT")
		select_and_change_mode(active_obj,oldmode)
		#bpy.context.scene.objects.active = bpy.context.scene.objects.active
		bpy.context.scene.update()
		return {'FINISHED'}

class WPLlwei_next( bpy.types.Operator ):
	bl_idname = "mesh.wplwei_next"
	bl_label = "Find next layer with selected"
	bl_options = {'REGISTER', 'UNDO'}
	opt_minval = bpy.props.FloatProperty(
		name		= "Minimum Value",
		default	 	= 0.01
		)
	@classmethod
	def poll( cls, context ):
		return ( context.object is not None and
				context.object.type == 'MESH' )

	def execute( self, context ):
		oldmode = context.scene.objects.active.mode
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		wpl_propToolOpts = context.scene.wpl_propToolOpts
		selvertsAll = get_selected_vertsIdx(active_mesh)
		if len(selvertsAll) == 0:
			self.report({'ERROR'}, "No selected vertices found")
			return {'CANCELLED'}
		select_and_change_mode(active_obj,"OBJECT")

		vg_firstOk = None
		vg_nextOk = None
		iswmcoFound = False
		for vg in active_obj.vertex_groups:
			if vg.name == wpl_propToolOpts.wei_gropnm:
				iswmcoFound = True
				continue
			for idx in selvertsAll:
				try:
					oldval = vg.weight(idx)
				except Exception as e:
					oldval = 0
				if oldval>=self.opt_minval:
					# found!!!
					if vg_firstOk is None:
						vg_firstOk = vg
					if iswmcoFound and vg_nextOk is None:
						vg_nextOk = vg
					break
			if vg_nextOk is not None:
				break
		if vg_nextOk is None and vg_firstOk is not None:
			vg_nextOk = vg_firstOk
		if oldmode != 'OBJECT':
			select_and_change_mode(active_obj,"OBJECT")
		if vg_nextOk is not None:
			wpl_propToolOpts.wei_gropnm = vg_nextOk.name
			# in EDIT mode!!!
			active_obj.vertex_groups.active_index = vg_nextOk.index
			#bpy.ops.object.vertex_group_select()
		select_and_change_mode(active_obj,oldmode)
		bpy.context.scene.update()
		return {'FINISHED'}

class wplposing_ar_refitprop( bpy.types.Operator ):
	bl_idname = "object.wplposing_ar_refitprop"
	bl_label = "Clone prop to target"
	bl_options = {'REGISTER', 'UNDO'}

	opt_bnlTests = IntProperty(
		name="Bone segs",
		min = 1, max = 100,
		default = 5,
	)
	opt_rayTests = IntProperty(
		name="Ray-casts per seg",
		min = 1, max = 100,
		default = 6,
	)
	opt_kdDist = FloatProperty(
		name="Affection dist",
		min = 0.0001, max = 100,
		default = 0.1,
	)
	@classmethod
	def poll( cls, context ):
		return ( context.object is not None)

	def execute( self, context ):
		wpl_prclToolOpts = context.scene.wpl_prclToolOpts
		if wpl_prclToolOpts.bdmesh_src not in bpy.data.objects.keys():
			self.report({'INFO'}, 'Body-src not found')
			return {"CANCELLED"}
		if wpl_prclToolOpts.prmesh_src not in bpy.data.objects.keys():
			self.report({'INFO'}, 'Prop-src not found')
			return {"CANCELLED"}
		if wpl_prclToolOpts.bdmesh_trg not in bpy.data.objects.keys():
			self.report({'INFO'}, 'Body-trg not found')
			return {"CANCELLED"}
		body_src = bpy.data.objects.get(wpl_prclToolOpts.bdmesh_src)
		body_trg = bpy.data.objects.get(wpl_prclToolOpts.bdmesh_trg)
		# getting armatures
		body_src_arm = None
		body_trg_arm = None
		for md in body_src.modifiers:
			if md.type == 'MIRROR':
				body_src_arm =None
				break
			if md.type == 'ARMATURE':
				body_src_arm = md.object
		for md in body_trg.modifiers:
			if md.type == 'MIRROR':
				body_src_arm =None
				break
			if md.type == 'ARMATURE':
				body_trg_arm = md.object
		print("armatures",body_src_arm,body_trg_arm)
		if body_src_arm is None or body_trg_arm is None:
			self.report({'INFO'}, 'Armatures not found or body mirrors present')
			return {"CANCELLED"}
		body_src_arm.data.pose_position = 'REST'
		body_trg_arm.data.pose_position = 'REST'
		prop_src = bpy.data.objects.get(wpl_prclToolOpts.prmesh_src)
		# calculating bones to check
		bones_list = []
		boneNames = body_src_arm.pose.bones.keys()
		if len(wpl_prclToolOpts.bdarm_bns)>0:
			boneNameParts = [x.strip().lower() for x in wpl_prclToolOpts.bdarm_bns.split(",")]
			for nm in boneNames:
				if nm not in bones_list:
					skipped = False
					for bnp in boneNameParts:
						if ("!" in bnp):
							bnp_cleared = bnp.replace("!","")
							if bnp_cleared in nm.lower():
								skipped = True
					if skipped == False:
						for bnp in boneNameParts:
							if bnp in nm.lower():
								bones_list.append(nm)
								break
		else:
			bones_list = boneNames
		if len(bones_list) == 0:
			self.report({'INFO'}, 'No reper bones found')
			return {"CANCELLED"}
		print("- bonelist", bones_list)

		# calculating point mappping
		# https://docs.blender.org/api/blender_python_api_2_77_1/bpy.types.PoseBone.html
		kd_src_g = mathutils.kdtree.KDTree(len(body_src.data.vertices))
		kdIndex = 0
		reperPointsMapping = {} # kdIndex = [from,to,boneName,boneName_rayId]
		bmg_src = bmesh.new()
		bmg_src.from_object(body_src, bpy.context.scene)
		bmg_src.transform(body_src.matrix_world)
		bmg_trg = bmesh.new()
		bmg_trg.from_object(body_trg, bpy.context.scene)
		bmg_trg.transform(body_trg.matrix_world)
		# if methodUV:
			#-# uvmap similarities
			# bm_src_uvcache = {}
			# uv_layer_ob = bmg_src.loops.layers.uv.get("UVMap")
			# for face in bmg_src.faces:
				# for loop in face.loops:
					# vert = loop.vert
					# uvk = str(int(loop[uv_layer_ob].uv[0]*10000))+"_"+str(int(loop[uv_layer_ob].uv[1]*10000))
					# bm_src_uvcache[uvk] = Vector((vert.co[0],vert.co[1],vert.co[2]))
			# bm_trg_uvcache = {}
			# uv_layer_ob = bmg_trg.loops.layers.uv.get("UVMap")
			# for face in bmg_trg.faces:
				# for loop in face.loops:
					# vert = loop.vert
					# uvk = str(int(loop[uv_layer_ob].uv[0]*10000))+"_"+str(int(loop[uv_layer_ob].uv[1]*10000))
					# bm_trg_uvcache[uvk] = Vector((vert.co[0],vert.co[1],vert.co[2]))
			# for uvk in bm_trg_uvcache:
				# if uvk in bm_src_uvcache:
					# kdIndex = kdIndex+1
					# pts_location = bm_src_uvcache[uvk]
					# ptt_location = bm_trg_uvcache[uvk]
					# kd_src_g.insert(pts_location, kdIndex)
					# slot = (pts_location,ptt_location,"uv")
					# reperPointsMapping[kdIndex] = slot
			# reperPointsBndMap = None
		# raycasting
		bvh_src = BVHTree.FromBMesh(bmg_src, epsilon = kRaycastEpsilon)
		arm_src_mw = body_src_arm.matrix_world
		arm_src_mwinv = arm_src_mw.inverted()
		arm_src_mwinv_norm = arm_src_mwinv.transposed().to_3x3()

		bvh_trg = BVHTree.FromBMesh(bmg_trg, epsilon = kRaycastEpsilon)
		arm_trg_mw = body_trg_arm.matrix_world
		arm_trg_mwinv = arm_trg_mw.inverted()
		arm_trg_mwinv_norm = arm_trg_mwinv.transposed().to_3x3()

		reperPointsBndMap = {}
		usedFaces = []
		for bn in bones_list:
			reperPointsBndMap[bn] = []
			if bn not in body_src_arm.pose.bones.keys():
				print(" - bone not found (src),",bn)
				continue
			if bn not in body_trg_arm.pose.bones.keys():
				print(" - bone not found (trg),",bn)
				continue
			bnFr = body_src_arm.pose.bones[bn]
			bnTo = body_trg_arm.pose.bones[bn]
			rotstep = 2*math.pi/float(self.opt_rayTests)
			bnt = max(1,self.opt_bnlTests)
			for bi in range(bnt):
				if self.opt_bnlTests == 0:
					bnFr_pt = arm_src_mw*(bnFr.center+bnFr.vector*0.5)
					bnTo_pt = arm_trg_mw*(bnTo.center+bnTo.vector*0.5)
				else:
					bnFr_pt = arm_src_mw*(bnFr.center-bnFr.vector*0.4+bnFr.vector*(0.8*float(bi)/float(self.opt_bnlTests)))
					bnTo_pt = arm_trg_mw*(bnTo.center-bnTo.vector*0.4+bnTo.vector*(0.8*float(bi)/float(self.opt_bnlTests)))
				for i in range(self.opt_rayTests):
					reperKey = bn+str(i)
					bnFrDir = arm_src_mwinv_norm*((Matrix.Rotation(float(i)*rotstep,4,bnFr.y_axis))*bnFr.x_axis)
					bnToDir = arm_trg_mwinv_norm*((Matrix.Rotation(float(i)*rotstep,4,bnTo.y_axis))*bnTo.x_axis)
					#-#bnFrDir = arm_src_mwinv_norm*(Matrix.Rotation(float(i)*rotstep,4,bnFr.vector.normalized())*(Vector((0,0,1)).cross(bnFr.vector.normalized())))
					#-#bnToDir = arm_trg_mwinv_norm*(Matrix.Rotation(float(i)*rotstep,4,bnTo.vector.normalized())*(Vector((0,0,1)).cross(bnTo.vector.normalized())))
					pts_location, pts_normal, pts_index, pts_distance = bvh_src.ray_cast(bnFr_pt, bnFrDir, 999)
					ptt_location, ptt_normal, ptt_index, ptt_distance = bvh_trg.ray_cast(bnTo_pt, bnToDir, 999)
					if pts_location is not None and ptt_location is not None:
						if pts_index not in usedFaces:
							usedFaces.append(pts_index)
							#-#body_src.data.polygons[pts_index].select = True
							#-#body_trg.data.polygons[ptt_index].select = True
							kdIndex = kdIndex+1
							kd_src_g.insert(pts_location, kdIndex)
							slot = (pts_location,ptt_location,bn,reperKey)
							reperPointsMapping[kdIndex] = slot
							reperPointsBndMap[bn].append(slot)
					else:
						print("- raytest: no mapping for",reperKey,pts_location,ptt_location)
		kd_src_g.balance()
		bmg_src.free()
		bmg_trg.free()
		print("- mappings found", len(reperPointsMapping))
		# creating clone
		prop_trg = prop_src.copy()
		prop_trg.data = prop_src.data.copy()
		prop_trg.parent = body_trg.parent # no save location!!!
		prop_trg.matrix_world = body_trg.matrix_world
		bpy.context.scene.objects.link(prop_trg)
		for md in prop_trg.modifiers:
			if md.type == 'ARMATURE':
				md.object = None
		# applying mapping
		select_and_change_mode(prop_trg,"OBJECT")
		bm_src = bmesh.new()
		bm_src.from_mesh(prop_src.data)
		bm_trg = bmesh.new()
		bm_trg.from_mesh(prop_trg.data)
		bm_src.verts.ensure_lookup_table()
		bm_trg.verts.ensure_lookup_table()
		for v_src in bm_src.verts:
			v_trg = bm_trg.verts[v_src.index]
			v_trg_ps_g = []
			v_trg_ws_g = []
			v_src_co_g = prop_src.matrix_world*v_src.co
			nears = kd_src_g.find_range(v_src_co_g,self.opt_kdDist)
			affectedBns = []
			affectedSlots = []
			for kdelem in nears:
				index = kdelem[1]
				indexSlot = reperPointsMapping[index]
				if reperPointsBndMap is not None:
					indexBn = indexSlot[2]
					if indexBn not in affectedBns:
						affectedBns.append(indexBn)
				else:
					affectedSlots.append(indexSlot)
			def applySlots(slt):
				for i in range(len(slt)):
					slot1 = slt[i]
					sp1 = slot1[0]
					tp1 = slot1[1]
					slot2 = slt[(i+1)%len(slt)]
					sp2 = slot2[0]
					tp2 = slot2[1]
					slot3 = slt[(i+2)%len(slt)]
					sp3 = slot3[0]
					tp3 = slot3[1]
					# _meth1 smoother, meth2 better4volume
					tp_g = recalcPointFromTri2Tri_meth1(v_src_co_g,sp1,sp2,sp3,tp1,tp2,tp3)
					if tp_g is not None:
						tg_g_w = ((v_src_co_g-sp1).length+(v_src_co_g-sp2).length+(v_src_co_g-sp3).length)*0.33
						#tg_g_w = max((v_src_co_g-sp1).length,(v_src_co_g-sp2).length,(v_src_co_g-sp3).length)
						v_trg_ps_g.append(tp_g)
						v_trg_ws_g.append(tg_g_w)
					#else:
					#	print("- no mapping for",slot1[2],slot2[2],slot3[2])
			if len(affectedSlots) > 0:
				applySlots(affectedSlots)
			else:
				for bn in affectedBns:
					affectedSlots = reperPointsBndMap[bn]
					applySlots(affectedSlots)
			if len(v_trg_ps_g)>0:
				maxw = max(v_trg_ws_g)
				minw = min(v_trg_ws_g)
				v_trg_ws_g = [1.0-pow((w-minw)/(maxw-minw),2) for w in v_trg_ws_g]
				x = np.average([co[0] for co in v_trg_ps_g],weights=v_trg_ws_g)
				y = np.average([co[1] for co in v_trg_ps_g],weights=v_trg_ws_g)
				z = np.average([co[2] for co in v_trg_ps_g],weights=v_trg_ws_g)
				v_trg.co = prop_trg.matrix_world.inverted()*Vector((x,y,z))

		bm_trg.to_mesh(prop_trg.data)
		return {'FINISHED'}
######### ############ ################# ############
def onUpdate_wei_gropnm_real(self, context):
	wpl_propToolOpts = context.scene.wpl_propToolOpts
	if len(wpl_propToolOpts.wei_gropnm_real)>0:
		wpl_propToolOpts.wei_gropnm = wpl_propToolOpts.wei_gropnm_real
		wpl_propToolOpts.wei_gropnm_real = ""
def onUpdate_bake_uvbase_real(self, context):
	wpl_propToolOpts = context.scene.wpl_propToolOpts
	if len(wpl_propToolOpts.bake_uvbase_real)>0:
		vctoolsOpts.bake_uvbase = vctoolsOpts.bake_uvbase_real
		vctoolsOpts.bake_uvbase_real = ""
class WPLPropToolSettings(bpy.types.PropertyGroup):
	bake_uvbase = StringProperty(
		name="Grid-UV",
		default = "GridXY"
		)
	bake_uvbase_real = StringProperty(
		name="UV",
		default = ""
		)
	mbh_mask_targ = StringProperty(
		name="Body",
		default = ""
	)
	mbh_mask_dist_uv= StringProperty(
		name="Dist-UV",
		default = "Proximity"
		)
	wei_value = FloatProperty(
		name="Val",
		default = 0.1
	)
	wei_gropnm = StringProperty(
		name="V-group",
		default = ""
	)
	wei_gropnm_real = StringProperty(
		name="",
		default = "",
		update=onUpdate_wei_gropnm_real
	)

class WPLPrclToolSettings(bpy.types.PropertyGroup):
	bdmesh_src = StringProperty(
		name="Src: Body",
		default = ""
	)
	prmesh_src = StringProperty(
		name="Src: Prop",
		default = ""
	)
	bdmesh_trg = StringProperty(
		name="Trg: Body",
		default = ""
	)
	bdarm_bns = StringProperty(
		name="Reper bones",
		default = "calf,thigh,pelvis,spine01,upperarm,lowerarm,neck,clavicle,  ,spine02,spine03,breast  ,!twist"#,spine02,spine03,breast
		#default = "lowerarm_L,upperarm_L"
	)

class WPLGarmToolsMask_Panel2(bpy.types.Panel):
	bl_label = "Weight tools"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_category = 'WPL'

	def draw(self, context):
		layout = self.layout
		wpl_propToolOpts = context.scene.wpl_propToolOpts
		active_obj = context.scene.objects.active
		col = layout.column()
		if active_obj is not None and active_obj.data is not None:
			row0 = col.row()
			row0.prop(wpl_propToolOpts, "wei_gropnm")
			row0.prop_search(wpl_propToolOpts, "wei_gropnm_real", active_obj, "vertex_groups", icon='GROUP_VERTEX', text="")
			row1 = col.row()
			row1.prop(wpl_propToolOpts, "wei_value")
			op1 = row1.operator("mesh.wplweig_edt", text="+")
			op1.opt_stepmul = 1.0
			op1.opt_oldmul = 1.0
			op1.opt_stepadd = 0.0
			op2 = row1.operator("mesh.wplweig_edt", text="-")
			op2.opt_stepmul = -1.0
			op2.opt_oldmul = 1.0
			op2.opt_stepadd = 0.0
			#op3 = row1.operator("mesh.wplweig_edt", text="//")
			#op3.opt_stepmul = 0.5
			#op3.opt_oldmul = 0.5
			#op3.opt_stepadd = 0.0
			row2 = col.row()
			op4 = row2.operator("mesh.wplweig_edt", text="*0.33")
			op4.opt_stepmul = 0.0
			op4.opt_oldmul = 0.33
			op4.opt_stepadd = 0.0
			op5 = row2.operator("mesh.wplweig_edt", text="*0.5")
			op5.opt_stepmul = 0.0
			op5.opt_oldmul = 0.5
			op5.opt_stepadd = 0.0
			op6 = row2.operator("mesh.wplweig_edt", text="*2.0")
			op6.opt_stepmul = 0.0
			op6.opt_oldmul = 2.0
			op6.opt_stepadd = 0.0
			row3 = col.row()
			op7 = row3.operator("mesh.wplweig_edt", text="=0.0")
			op7.opt_stepmul = 0.0
			op7.opt_oldmul = 0.0
			op7.opt_stepadd = 0.0
			op8 = row3.operator("mesh.wplweig_edt", text="=0.5")
			op8.opt_stepmul = 0.0
			op8.opt_oldmul = 0.0
			op8.opt_stepadd = 0.5
			op9 = row3.operator("mesh.wplweig_edt", text="=1.0")
			op9.opt_stepmul = 0.0
			op9.opt_oldmul = 0.0
			op9.opt_stepadd = 1.0
			col.separator()
			col.operator("object.vertex_group_smooth", text="Smooth weights")
			col.operator("mesh.wplwei_next", text="Find next layer")

class WPLGarmToolsMask_Panel1(bpy.types.Panel):
	bl_label = "Props tools"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_category = 'WPL'

	def draw(self, context):
		layout = self.layout
		wpl_propToolOpts = context.scene.wpl_propToolOpts
		active_obj = context.scene.objects.active
		col = layout.column()
		col.prop_search(wpl_propToolOpts, "mbh_mask_targ", context.scene, "objects",icon="SNAP_NORMAL")
		col.operator("object.wplprops_datatransf", text="Transfer w-groups to selection").opt_tranfType = 'WEI'
		col.operator("object.wplprops_datatransf", text="Transfer v-colors to selection").opt_tranfType = 'VC'
		col.operator("object.wplprops_cpymodifs", text="Transfer modifs to selection")
		col.operator("object.wplprops_weitransf", text="Adapt weights on selection")
		col.separator()
		#col.operator("object.wplprops_maskgarm", text="Mask by selection").opt_displInfluence = 0.0
		#col.operator("object.wplprops_maskgarm", text="Displace by selection").opt_displInfluence = kDisplaceDefault
		col.label("UV Baking")
		col.prop(wpl_propToolOpts, "mbh_mask_dist_uv")
		col.operator("object.wplprops_maskgarm2", text="Bake distances to selection")
		col.separator()
		col.separator()
		row0 = col.row()
		row0.prop(wpl_propToolOpts, "bake_uvbase")
		row0.prop_search(wpl_propToolOpts, "bake_uvbase_real", active_obj.data, "uv_layers", icon='GROUP_UVS')
		#col.operator("object.wplbake_mesh_centers", text="Bake local space (island centers)")
		col.operator("object.wplbake_normalize_uv", text="Normalize UVs")
		
class WPLGarmToolsMask_Panel2(bpy.types.Panel):
	bl_label = "Props misc"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_category = 'WPL'

	def draw(self, context):
		layout = self.layout
		wpl_propToolOpts = context.scene.wpl_propToolOpts
		col = layout.column()
		col.label("Physics")
		col.operator("object.wplprops_stepphysics", text="Roll bpy-physics")
		col.separator()
		col.separator()

		wpl_prclToolOpts = context.scene.wpl_prclToolOpts
		col.prop_search(wpl_prclToolOpts, "bdmesh_src", context.scene, "objects",icon="SNAP_NORMAL")
		col.prop_search(wpl_prclToolOpts, "prmesh_src", context.scene, "objects",icon="SNAP_NORMAL")
		col.prop_search(wpl_prclToolOpts, "bdmesh_trg", context.scene, "objects",icon="SNAP_NORMAL")
		col.prop(wpl_prclToolOpts, "bdarm_bns")
		col.operator("object.wplposing_ar_refitprop")

def register():
	print("WPLGarmToolsMask_Panel1 register")
	bpy.utils.register_module(__name__)
	bpy.types.Scene.wpl_propToolOpts = PointerProperty(type=WPLPropToolSettings)
	bpy.types.Scene.wpl_prclToolOpts = PointerProperty(type=WPLPrclToolSettings)

def unregister():
	print("WPLGarmToolsMask_Panel1 unregister")
	bpy.utils.unregister_module(__name__)
	del bpy.types.Scene.wpl_propToolOpts
	bpy.utils.unregister_class(WPLPropToolSettings)
	bpy.utils.unregister_class(WPLPrclToolSettings)

if __name__ == "__main__":
	register()
