import math
import copy
import mathutils
import numpy as np
#import bisect

import bpy
from bpy.props import *
import bpy.types
import bmesh
from mathutils import Vector, Matrix, Euler
from bpy_extras import view3d_utils
from mathutils.bvhtree import BVHTree

bl_info = {
	"name": "Mesh Deform Tools",
	"author": "IPv6",
	"version": (1, 4, 1),
	"blender": (2, 7, 9),
	"location": "View3D > T-panel > WPL",
	"description" : "",
	"warning"	 : "",
	"wiki_url"	: "",
	"tracker_url" : "",
	"category"	: "WPL"
}

kWPLRaycastEpsilon = 0.01
kWPLRaycastEpsilonCCL = 0.0001
kWPLMeshDeformMod = "wpl_Meshdefrm"
kWPLSystemEmpty = "zzz_Support"
kWPLSystemLayer = 19
kWPLEdgesMainCam = "zzz_MainCamera"
kWPLHullIncKey = "wpl_helperobjs"
kWPLRefitEdgesStoreKey = "edgerefit"
kWPLRefitVertsStoreKey = "vertrefit"
kWPLFrameBindPostfix = "_##"
kWPLArmaStickman = "zzz_armSkel"

class WPL_G:
	store = {}
######################### ######################### #########################
######################### ######################### #########################
def moveObjectOnLayer(c_object, layId):
	def layers(l):
		all = [False]*20
		all[l]=True
		return all
	c_object.layers = layers(layId)

def getSysEmpty(context,subname):
	emptyname = kWPLSystemEmpty
	if subname is not None and len(subname)>0:
		emptyname = subname
	empty = context.scene.objects.get(emptyname)
	if empty is None:
		empty = bpy.data.objects.new(emptyname, None)
		empty.empty_draw_size = 0.45
		empty.empty_draw_type = 'PLAIN_AXES'
		context.scene.objects.link(empty)
		context.scene.update()
		if subname is not None and len(subname)>0:
			empty.parent = getSysEmpty(context,"")
	return empty

def select_and_change_mode(obj, obj_mode):
	#print("select_and_change_mode",obj_mode)
	m = bpy.context.mode
	if obj_mode == "EDIT_MESH" or  obj_mode == "EDIT_CURVE":
		obj_mode = "EDIT"
	if obj_mode == "PAINT_VERTEX":
		obj_mode = "VERTEX_PAINT"
	if (obj is not None and bpy.context.scene.objects.active != obj) or m != 'OBJECT':
		# stepping out from currently active object mode, or switch may fail
		try:
			bpy.ops.object.mode_set(mode='OBJECT')
		except:
			print("select_and_change_mode: failed to prep mode", bpy.context.scene.objects.active, obj, m)
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

def findChildObjectByName(obj, childName):
	# looking childs
	if len(obj.children)>0:
		for ch in obj.children:
			if childName in ch.name:
				return ch
	# looking in all objects
	for objx in bpy.data.objects:
		if childName in objx.name and obj.name in objx.name:
			return objx
	return None

def view_getActiveRegion():
	reg3d = bpy.context.space_data.region_3d
	if reg3d is not None:
		return reg3d
	for area in bpy.context.screen.areas:
		if area.type == 'VIEW_3D':
			return area.spaces.active.region_3d
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

def get_selected_vertsIdx(active_mesh):
	bpy.ops.object.mode_set(mode='OBJECT')
	selectedVertsIdx = [e.index for e in active_mesh.vertices if e.select]
	return selectedVertsIdx

def get_selected_facesIdx(active_mesh):
	# find selected faces
	bpy.ops.object.mode_set(mode='OBJECT')
	faces = [f.index for f in active_mesh.polygons if f.select]
	# print("selected faces: ", faces)
	return faces

def get_selected_edgesIdx(active_mesh):
	bpy.ops.object.mode_set(mode='OBJECT')
	selectedEdgesIdx = [e.index for e in active_mesh.edges if e.select]
	return selectedEdgesIdx

def get_bmhistory_vertsIdx(active_bmesh):
	active_bmesh.verts.ensure_lookup_table()
	active_bmesh.verts.index_update()
	selectedVertsIdx = []
	for elem in reversed(active_bmesh.select_history):
		if isinstance(elem, bmesh.types.BMVert) and elem.select and elem.hide == 0:
			selectedVertsIdx.append(elem.index)
	return selectedVertsIdx
def get_bmhistory_faceIdx(active_bmesh):
	active_bmesh.faces.ensure_lookup_table()
	active_bmesh.faces.index_update()
	selectedFacesIdx = []
	for elem in reversed(active_bmesh.select_history):
		if isinstance(elem, bmesh.types.BMFace) and elem.select and elem.hide == 0:
			selectedFacesIdx.append(elem.index)
	return selectedFacesIdx
def get_bmhistory_edgesIdx(active_bmesh):
	active_bmesh.edges.ensure_lookup_table()
	active_bmesh.edges.index_update()
	selectedEdgesIdx = []
	for elem in reversed(active_bmesh.select_history):
		if isinstance(elem, bmesh.types.BMEdge) and elem.select and elem.hide == 0:
			selectedEdgesIdx.append(elem.index)
	return selectedEdgesIdx

def get_isLocalView():
	is_local_view = sum(bpy.context.space_data.layers[:]) == 0 #if hairCurve.layers_local_view[0]:
	return is_local_view

# def strands2GlobalFlowset(active_obj, bm, strands_points, strands_vidx, subdiv = 0):
# 	matrix_world = active_obj.matrix_world
# 	matrix_world_inv = active_obj.matrix_world.inverted()
# 	matrix_world_norm = matrix_world_inv.transposed().to_3x3()
# 	g_curveset = []
# 	for i, strand_curve in enumerate(strands_points):
# 		if len(strand_curve) < 2: # we can have single vertices in list too
# 			continue
# 		g_curve = []
# 		for j, co in enumerate(strand_curve):
# 			vIdx = strands_vidx[i][j][0]
# 			v = bm.verts[vIdx]
# 			v_co_g = matrix_world*co
# 			flow_g = Vector((0,0,0))
# 			if j<len(strand_curve)-1:
# 				flow_g = matrix_world*strand_curve[j+1] - v_co_g
# 			else:
# 				flow_g = v_co_g-matrix_world*strand_curve[j-1] # last one point in prev direction. extending direction "past the end"
# 			g_curve.append((v_co_g, matrix_world_norm*v.normal, flow_g))
# 		if subdiv>0:
# 			# subdividing curve
# 			for sdn in range(0, subdiv):
# 				g_curve_new = []
# 				for i, pt in enumerate(g_curve):
# 					g_curve_new.append( (pt[0], pt[1], pt[2]*0.5) )
# 					if i+1 < len(g_curve):
# 						pt_next = g_curve[i+1]
# 						g_curve_new.append( ((pt[0]+pt_next[0])*0.5, ((pt[1]+pt_next[1])*0.5).normalized(), pt[2]*0.5) )
# 				g_curve = g_curve_new
# 		g_curveset.append(g_curve)
# 	return g_curveset

def getBmEdgesAsStrands_v04(bm, vertsIdx, edgesIdx, opt_flowDirP, obj_forWrldMat = None):
	bm.verts.ensure_lookup_table()
	bm.verts.index_update()
	bm.edges.ensure_lookup_table()
	bm.edges.index_update()
	# looking for bounding verts
	opt_flowDir = Vector(opt_flowDirP)
	opt_flowDir = opt_flowDir.normalized()
	def calc_boundVerts():
		bndVertsTest = []
		for vIdx in vertsIdx:
			v = bm.verts[vIdx]
			edgeDirs = []
			edgeLens = 0
			edgeLensC = 0
			for e in v.link_edges:
				if e.index in edgesIdx:
					flowfir = (e.other_vert(v).co-v.co).normalized()
					flowdot = flowfir.dot(opt_flowDir)
					flowang = math.acos(flowdot)
					edgeDirs.append(flowang)
				else:
					edgeLens = edgeLens+e.calc_length()
					edgeLensC = edgeLensC+1
			if len(edgeDirs) == 1:
				bndVertsTest.append((vIdx, edgeDirs[0], edgeLens/(edgeLensC+0.001)))
		bndVertsTest.sort(key=lambda ia: ia[1], reverse=False)
		return bndVertsTest
	bndVerts = calc_boundVerts()
	if len(bndVerts)<2 and len(edgesIdx)>1:
		# loops... breaking edgesIdx somewhere - near historyVert or first edge
		dropVertIdx = vertsIdx[0]
		histVerts = get_bmhistory_vertsIdx(bm)
		if len(histVerts) > 0:
			dropVertIdx = histVerts[0] # most recent active vert
		isDropped = False
		for eIdx in edgesIdx:
			e = bm.edges[eIdx]
			if e.verts[0].index == dropVertIdx or e.verts[1].index == dropVertIdx:
				edgesIdx.remove(eIdx)
				isDropped = True
				break
		if isDropped == False:
			edgesIdx.remove(edgesIdx[0])
		bndVerts = calc_boundVerts()
	if len(bndVerts)<2:
		# something wrong
		return (None, None, None)
	strands_points = []
	strands_radius = []
	strands_vidx = []
	checked_verts = []
	#print("bndVerts", bndVerts)
	for ia in bndVerts:
		vIdx = ia[0]
		points_co = None
		points_idx = None
		canContinue = True
		while canContinue == True:
			#print("Checking vIdx", vIdx)
			if vIdx in checked_verts:
				canContinue = False
				continue
			checked_verts.append(vIdx)
			if points_co is None:
				points_co = []
				points_idx = []
				strands_points.append(points_co)
				strands_vidx.append(points_idx)
				strands_radius.append(ia[2])
			v = bm.verts[vIdx]
			points_idx.append([v.index])
			v_co = copy.copy(v.co)
			if obj_forWrldMat is not None:
				v_co = obj_forWrldMat.matrix_world * v_co
			points_co.append(v_co)
			canContinue = False
			for e in v.link_edges:
				if e.index in edgesIdx:
					vIdx = e.other_vert(v).index
					if vIdx not in checked_verts:
						canContinue = True
						break
	return (strands_points, strands_radius, strands_vidx)

def sortBmVertsByConnection_v01(bm, vertsIdx, smartFirst):
	bm.verts.ensure_lookup_table()
	bm.verts.index_update()
	bm.edges.ensure_lookup_table()
	bm.edges.index_update()
	bm.faces.ensure_lookup_table()
	bm.faces.index_update()
	if len(vertsIdx)<3:
		return vertsIdx
	if smartFirst:
		for i in range(1, len(vertsIdx)):
			v = bm.verts[vertsIdx[i]]
			selothors = 0
			for e in v.link_edges:
				if e.other_vert(v).index in vertsIdx:
					selothors = selothors+1
			if selothors == 1:
				t = vertsIdx[0]
				vertsIdx[0] = vertsIdx[i]
				vertsIdx[i] = t
				break
	for i in range(len(vertsIdx)-1):
		v = bm.verts[vertsIdx[i]]
		mindst = 9999
		exhpos = -1
		for j in range(i+1,len(vertsIdx)):
			vo = bm.verts[vertsIdx[j]]
			for f in v.link_faces:
				if vo in f.verts:
					if (vo.co-v.co).length < mindst:
						mindst = (vo.co-v.co).length
						exhpos = j
					break
		if exhpos >= 0:
			t = vertsIdx[i+1]
			vertsIdx[i+1] = vertsIdx[exhpos]
			vertsIdx[exhpos] = t
	return vertsIdx

def getBmAverageEdgeLen(bm, vertsIdx, deflen):
	edgelenSum = 0
	edgelenCnt = 0
	edgelenSumAll = 0
	edgelenCntAll = 0
	for vIdx in vertsIdx:
		v = bm.verts[vIdx]
		for e in v.link_edges:
			edgelenSumAll = edgelenSumAll+e.calc_length()
			edgelenCntAll = edgelenCntAll+1
			if e.other_vert(v).select:
				continue
			edgelenSum = edgelenSum+e.calc_length()
			edgelenCnt = edgelenCnt+1
	edgelenAvg = deflen
	if edgelenCnt>0:
		edgelenAvg = edgelenSum/edgelenCnt
	elif edgelenCntAll>0:
		edgelenAvg = edgelenSumAll/edgelenCntAll
	return edgelenAvg

def getHelperObjId(context):
	if kWPLHullIncKey not in context.scene:
		context.scene[kWPLHullIncKey] = 1
	curId = context.scene[kWPLHullIncKey]
	context.scene[kWPLHullIncKey] = context.scene[kWPLHullIncKey]+1
	return curId

def fuzzyBVHRayCast_v01(bvh, vFrom, vDir, fuzzyVal, fuzzyQual):
	gResult = mathutils.Vector((0,0,0))
	gResultNormal = mathutils.Vector((0,0,0))
	gCount = 0.0
	vDirs = [vDir.normalized()]
	if fuzzyVal > 0.0:
		perpBase = mathutils.Vector((0,0,1))
		if(math.fabs(vDir.dot(perpBase)) > 0.9):
			perpBase = mathutils.Vector((0,1,0))
		perp1 = vDir.cross(perpBase)
		perp2 = vDir.cross(perp1)
		vDirs = [vDir.normalized()]
		for i in range(0,fuzzyQual):
			delim = float(i+1)/float(fuzzyQual)
			slice = [(vDir+delim*perp1*fuzzyVal).normalized(), (vDir-delim*perp1*fuzzyVal).normalized(), (vDir+delim*perp2*fuzzyVal).normalized(), (vDir-delim*perp2*fuzzyVal).normalized()]
			vDirs.extend(slice)

	for shootDir in vDirs:
		loc_g, normal, index, distance = bvh.ray_cast(vFrom+vDir*kWPLRaycastEpsilon, shootDir)
		#print("fuzzySceneRayCast", vFrom, shootDir, result, loc_g)
		if loc_g is not None:
			gCount = gCount+1.0
			gResult = gResult+loc_g
			gResultNormal = gResultNormal+normal

	if gCount>0:
		return (gResult/gCount, gResultNormal/gCount)
	return (None, None)

def customAxisMatrix(v_origin, a, b):
	# https://blender.stackexchange.com/questions/30808/how-do-i-construct-a-transformation-matrix-from-3-vertices
	#def make_matrix(v_origin, v2, v3):
	#a = v2-v_origin
	#b = v3-v_origin
	c = a.cross(b)
	if c.magnitude>0:
		c = c.normalized()
	else:
		#raise BaseException("A B C are colinear")
		return None
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

def getF3cValue(indexCur,indexMax,index50,F3c):
	value = 0.0
	if indexCur<index50:
		value = F3c[0]+(F3c[1]-F3c[0])*(float(indexCur)/max(0.001,index50))
	else:
		value = F3c[1]+(F3c[2]-F3c[1])*(float(indexCur-index50)/max(0.001,indexMax-index50))
	return value
def wpl_slope(v0,v1,v2,mid,pos): # for PY parameters
	return getF3cValue(pos,1.0,mid,(v0,v1,v2))
def wpl_mix(v0,v1,pos): # for PY parameters
	return v0+(v1-v0)*pos

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
def val_vertgroup(vertgroup,idx,newval):
	wmod = 'REPLACE'
	oldval = 0
	try:
		oldval = vertgroup.weight(idx)
	except Exception as e:
		wmod = 'ADD'
	if newval is not None:
		vertgroup.add([idx], newval, wmod)
	return oldval
def copyBMVertColtoFace(bm,frmFace,trgFace,vIdx_vccache):
	if frmFace is None:
		return
	bm.verts.ensure_lookup_table()
	bm.faces.ensure_lookup_table()
	trgFace.smooth = frmFace.smooth
	allvcs = bm.loops.layers.color.keys()
	for llayer_key in allvcs:
		llayer = bm.loops.layers.color[llayer_key]
		cck = llayer_key+str(frmFace.index)
		if cck in vIdx_vccache:
			fcl = vIdx_vccache[cck]
		else:
			fcl = Vector((0,0,0))
			fcl_c = 0
			for loop in frmFace.loops:
				fcl = fcl+Vector((loop[llayer][0],loop[llayer][1],loop[llayer][2]))
				fcl_c = fcl_c+1
			if fcl_c>0:
				fcl = fcl/fcl_c
			vIdx_vccache[cck] = fcl
		for loop in trgFace.loops:
			loop[llayer] = (fcl[0],fcl[1],fcl[2],1)

def get_active_context_cursor(context):
	scene = context.scene
	space = context.space_data
	v3ds = (space if space and space.type == 'VIEW_3D' else scene)
	if v3ds is None:
		return None
	cursor = v3ds.cursor_location
	return cursor

def makeObjectNoShadow(c_object, andWire, andNoRender):
	c_object.cycles_visibility.camera = True
	c_object.cycles_visibility.diffuse = False
	c_object.cycles_visibility.glossy = False
	c_object.cycles_visibility.transmission = False
	c_object.cycles_visibility.scatter = False
	c_object.cycles_visibility.shadow = False
	if andWire is not None and andWire == True:
		c_object.draw_type = 'WIRE'
	if andNoRender is not None:
		c_object.hide_render = andNoRender
		c_object.cycles_visibility.camera = not andNoRender

def attachEdgeToSourceObject(edgeObj, sel_obj, asChild, withShrinkw, withSubd):
	if len(edgeObj.data.materials) == 0 and len(sel_obj.data.materials)>0:
		edgeObj.data.materials.append(sel_obj.data.materials[0])
	if asChild:
		edgeObj.parent = sel_obj
		edgeObj.matrix_local = Matrix.Identity(4)
	else:
		edgeObj.parent = sel_obj.parent
		edgeObj.matrix_world = sel_obj.matrix_world
	if withSubd > 0:
		edgeModifiers = edgeObj.modifiers
		if (edgeModifiers.get('WPL_EdgeSubd') is None) and (sel_obj.type != 'CURVE'):
			subdiv_modifier = edgeModifiers.new(name = "WPL_EdgeSubd", type = 'SUBSURF')
			subdiv_modifier.levels = withSubd
			subdiv_modifier.render_levels = withSubd
	if withShrinkw:
		edgeModifiers = edgeObj.modifiers
		if (edgeModifiers.get('WPL_Edge2src') is None) and (sel_obj.type != 'CURVE'):
			shrinkwrap_modifier = edgeModifiers.new(name = "WPL_Edge2src", type = 'SHRINKWRAP')
			shrinkwrap_modifier.offset = 0.0
			shrinkwrap_modifier.target = sel_obj
			shrinkwrap_modifier.use_keep_above_surface = True
			shrinkwrap_modifier.use_apply_on_spline = True
			shrinkwrap_modifier.wrap_method = 'NEAREST_SURFACEPOINT'

def modfSendBackByType(c_object,modType):
	modname = None
	bpy.context.scene.objects.active = c_object
	for md in c_object.modifiers:
		if md.type == modType: #'SUBSURF'
			modname = md.name
			break
	if modname is not None:
		while c_object.modifiers[-1].name != modname:
			#modifier_move_up
			bpy.ops.object.modifier_move_down(modifier=modname)

def modfGetByType(c_object, modType, modName = None):
	for md in c_object.modifiers:
		isNameOk = True
		isTypeOk = True
		if modType is not None and md.type != modType:
			isTypeOk = False
		if modName is not None and (modName not in md.name):
			isNameOk = False
		if isNameOk and isTypeOk:
			return md
	return None

def curve_rescaleRadius(poly, radF3c, mid_fac, baseRadius):
	radiusAtStart = radF3c[0]
	radiusAtEnd = radF3c[1]
	radiusPow = radF3c[2]
	curveLength = float(len(poly))
	if curveLength>1:
		mid_fac = min(0.99,max(0.01,mid_fac))
		curveDistTotal = 0
		pprev = None
		for i,p in enumerate(poly):
			if pprev is not None:
				curveDistTotal = curveDistTotal+(p.co-pprev.co).length
			pprev = p
		pprev = None
		curveDist = 0;
		for i,p in enumerate(poly):
			if pprev is not None:
				curveDist = curveDist+(p.co-pprev.co).length
			pprev = p
			#curve_fac = float(i) / (curveLength-1)
			curve_fac = curveDist / curveDistTotal
			if curve_fac<mid_fac:
				RadTotal = radiusAtStart+(1.0-radiusAtStart)*(curve_fac/mid_fac)
			else:
				RadTotal = radiusAtEnd+(1.0-radiusAtEnd)*(1.0-(curve_fac-mid_fac)/mid_fac)
			RadTotal = max(0.00001,RadTotal)
			RadTotal = pow(RadTotal,radiusPow)
			p.radius = RadTotal*baseRadius

######################### ######################### #########################
######################### ######################### #########################
class wpldeform_extrskin(bpy.types.Operator):
	bl_idname = "object.wpldeform_extrskin"
	bl_label = "Extract skinned edges"
	bl_options = {'REGISTER', 'UNDO'}

	opt_skinSize = bpy.props.FloatProperty(
		name		= "Skinning size",
		default	 = 0.015,
		min		 = 0.001,
		max		 = 1.0
		)
	opt_postShrwSize = bpy.props.FloatProperty(
		name		= "Post-shrinkwrap distance",
		default	 = 0.003,
		min		 = 0.0,
		max		 = 1.0
		)

	@classmethod
	def poll( cls, context ):
		p = context.object and context.object and context.object.type == 'MESH'
		return p

	def execute( self, context ):
		active_obj = context.scene.objects.active
		if active_obj is None:
			self.report({'ERROR'}, "No object selected")
			return {'CANCELLED'}
		if get_isLocalView():
			self.report({'ERROR'}, "Can`t work in Local view")
			return {'CANCELLED'}
		active_mesh = active_obj.data
		edgesIdx = get_selected_edgesIdx(active_mesh)
		if len(edgesIdx) == 0:
			self.report({'ERROR'}, "No selected edges found")
			return {'FINISHED'}
		objsBefore = [obj for obj in bpy.data.objects]
		bpy.ops.object.mode_set( mode = 'EDIT' )
		bpy.ops.mesh.select_mode(type='EDGE')
		bpy.ops.mesh.separate(type='SELECTED')
		objsAfter = [obj for obj in bpy.data.objects]
		if len(objsAfter) == len(objsBefore):
			self.report({'ERROR'}, "Nothing extracted, ignoring")
			return {'CANCELLED'}
		edgeObj = None
		for obj in objsAfter:
			if obj not in objsBefore:
				edgeObj = obj
				break
		if edgeObj is None:
			self.report({'ERROR'}, "Extraction not found, ignoring")
			return {'CANCELLED'}
		edgeObj.select = False
		edgeObj.name = active_obj.name + "_skin"
		attachEdgeToSourceObject(edgeObj, active_obj, True, True, 0)
		skin_modf = edgeObj.modifiers.new(name = 'edge_skin', type = 'SKIN')
		bpy.ops.object.mode_set( mode = 'OBJECT' )
		isRootSet = False
		vSkinData = edgeObj.data.skin_vertices[0].data
		for vIdx,vS in enumerate(vSkinData):
			vS.radius = (self.opt_skinSize, self.opt_skinSize)
			vS.use_loose = False
			#v = edgeObj.vertices(vIdx)
			if isRootSet == False:
				isRootSet = True
				vS.use_root = True
		edgeObj.modifiers.new("Subsurf", 'SUBSURF')
		if self.opt_postShrwSize > 0:
			shrinkwrap_modifier2 = edgeObj.modifiers.new(name = "WPL_Edge2src2", type = 'SHRINKWRAP')
			shrinkwrap_modifier2.offset = self.opt_postShrwSize
			shrinkwrap_modifier2.target = active_obj
			shrinkwrap_modifier2.use_keep_above_surface = False
			shrinkwrap_modifier2.use_apply_on_spline = False
			shrinkwrap_modifier2.wrap_method = 'NEAREST_SURFACEPOINT'
		self.report({'INFO'}, "Skinned detail extracted")
		return {'FINISHED'}

class wpldeform_2curve(bpy.types.Operator):
	bl_idname = "object.wpldeform_2curve"
	bl_label = "Add detail Curve"
	bl_options = {'REGISTER', 'UNDO'}
	opt_sourceMeth = EnumProperty(
		items = [
			('VHIST', "Vert history", "", 1),
			('SELC', "Selection", "", 2)
		],
		name="Source",
		default='SELC',
	)
	opt_targetTune = EnumProperty(
		items = [
			('DETAIL', "Detail object", "", 1),
			('DEFORM', "Curve deform object", "", 2)
		],
		name="Source",
		default='DETAIL',
	)
	opt_widthProfile = bpy.props.FloatVectorProperty(
		name = "Width profile (start, end, pow)",
		size = 4,
		#default = (0.01, 0.01, 0.8, 1.0),
		default	 = (1.0, 1.0, 1.0, 0.2),
	)
	opt_subdLenRel = bpy.props.FloatProperty(
		name		= "Subdiv target (Edge-relative)",
		subtype		= 'PERCENTAGE',
		default	 = 200,
		min		 = 0.0,
		max		 = 1000.0
		)
	opt_shrw2src = BoolProperty(
		name ="Shrinkwrap",
		default=True
	)
	opt_shadelessObj = BoolProperty(
		name ="Shadeless",
		default=True
	)

	@classmethod
	def poll( cls, context ):
		p = context.object and context.object and context.object.type == 'MESH'
		return p

	def execute( self, context ):
		active_obj = context.scene.objects.active
		if active_obj is None:
			self.report({'ERROR'}, "No object selected")
			return {'CANCELLED'}
		if get_isLocalView():
			self.report({'ERROR'}, "Can`t work in Local view")
			return {'CANCELLED'}
		if abs(active_obj.scale[0]-1.0)+abs(active_obj.scale[1]-1.0)+abs(active_obj.scale[2]-1.0) > 0.001:
			self.report({'ERROR'}, "Scale not applied: "+active_obj.name)
			return {'CANCELLED'}
		oldmode = select_and_change_mode(active_obj,'EDIT')
		active_mesh = active_obj.data
		vertsIdx = []
		bm = None
		bm_co = None
		#try:
		bm_co = bmesh.new()
		bm_co.from_object(active_obj, context.scene, deform=True, render=False, cage=True, face_normals=True)
		bm_co.verts.ensure_lookup_table()
		bm_co.faces.ensure_lookup_table()
		bm_co.verts.index_update()
		bm = bmesh.from_edit_mesh( active_mesh )
		if self.opt_sourceMeth == 'VHIST':
			vertsIdx = get_bmhistory_vertsIdx(bm)
		else:
			vertsIdx = [v.index for v in bm.verts if v.select]
			# sorting according to nearness
			vertsIdx = sortBmVertsByConnection_v01(bm, vertsIdx, True)
		#except:
		#	pass
		if len(vertsIdx) <= 1:
			self.report({'ERROR'}, "No history verts found, select something first")
			return {'FINISHED'}
		antiscale = 1.0/max(active_obj.scale[0],active_obj.scale[1],active_obj.scale[1])*self.opt_widthProfile[3]
		sel_obj_name = active_obj.name
		needUpdateBevelDepth = False
		postf = "_curve"
		if self.opt_targetTune == 'DEFORM':
			postf = "_defrm"
		edgeObjName = sel_obj_name + postf
		curveDataName = edgeObjName + postf
		if self.opt_targetTune == 'DETAIL':
			curveData = bpy.data.curves.get(curveDataName)
		else:
			curveData = None
		if curveData is None:
			curveData = bpy.data.curves.new(curveDataName, type='CURVE')
			curveData.dimensions = '3D'
			curveData.fill_mode = 'FULL'
			needUpdateBevelDepth = True
			curveData.bevel_depth = 1*antiscale
			curveData.bevel_resolution = 2
			curveData.use_fill_caps = True
			curveData.show_normal_face = False
			curveData.use_auto_texspace = True
			curveData.use_uv_as_generated = True
			print("- creating curve data",curveData.name)
		polyline = curveData.splines.new('NURBS')
		curveLength = float(len(vertsIdx))
		edgesMaxLen = 0.0
		vertsCo = []
		for i,v_idx in enumerate(vertsIdx):
			v = bm_co.verts[v_idx]
			vertsCo.append(v.co)
			for e in v.link_edges:
				edgesMaxLen = max(edgesMaxLen,e.calc_length())
		subdlen = edgesMaxLen*(self.opt_subdLenRel*0.01)
		if subdlen>0.0:
			needContinue = True
			while needContinue:
				needContinue = False
				for i,v_co_l in enumerate(vertsCo):
					if i>0 and (v_co_l-vertsCo[i-1]).length > subdlen:
						v_co_l2 = (v_co_l+vertsCo[i-1])*0.5
						vertsCo.insert(i,v_co_l2)
						needContinue = True
						break
		for i,v_co_l in enumerate(vertsCo):
			if len(polyline.points) <= i:
				polyline.points.add(1)
			polyline.points[i].co = (v_co_l[0], v_co_l[1], v_co_l[2], 1)
		if self.opt_targetTune == 'DETAIL':
			curve_rescaleRadius(polyline.points, self.opt_widthProfile, 0.5, 1.0)
		polyline.use_endpoint_u = True
		polyline.order_u = 4
		polyline.resolution_u = 10
		if needUpdateBevelDepth and edgesMaxLen>0.0:
			curveData.bevel_depth = edgesMaxLen*0.3*antiscale
		if self.opt_targetTune == 'DETAIL':
			edgeObj = context.scene.objects.get(edgeObjName)
		else:
			edgeObj = None
		if edgeObj is None:
			edgeObj = bpy.data.objects.new(edgeObjName, curveData)
			edgeObj.parent = active_obj.parent
			edgeObj.matrix_world = active_obj.matrix_world
			context.scene.objects.link(edgeObj)
		if self.opt_shadelessObj:
			makeObjectNoShadow(edgeObj, True, False)
		attachEdgeToSourceObject(edgeObj, active_obj, False, self.opt_shrw2src, 0)
		if self.opt_targetTune == 'DEFORM':
			select_and_change_mode(edgeObj,'OBJECT')
			bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
			edgeObj.parent = getSysEmpty(context,"")
			# adding empty cube
			curveData.bevel_depth = 0.0
			bpy.ops.mesh.primitive_cube_add(radius = edgesMaxLen*0.3*antiscale)
			defl_cube = bpy.context.active_object
			defl_cube.name = edgeObjName + "_step"
			defl_cube.parent = active_obj.parent
			defl_cube.matrix_world = active_obj.matrix_world
			array_modf = defl_cube.modifiers.new(name = 'curve_len', type = 'ARRAY')
			array_modf.count = 3
			array_modf.show_in_editmode = True
			array_modf.show_on_cage = True
			curve_modf = defl_cube.modifiers.new(name = 'curve_defm', type = 'CURVE')
			curve_modf.object = edgeObj
			curve_modf.show_in_editmode = True
			curve_modf.show_on_cage = True
		select_and_change_mode(active_obj,oldmode)
		self.report({'INFO'}, "Added "+str(curveLength)+" points")
		return {'FINISHED'}

class wpldeform_bind(bpy.types.Operator):
	bl_idname = "mesh.wpldeform_bind"
	bl_label = "Multi-bind mesh/lat deform"
	bl_options = {'REGISTER', 'UNDO'}

	opt_makeWireInvis = BoolProperty(
		name="Surf: Wireframe & No-Render",
		default=True,
	)

	@classmethod
	def poll(self, context):
		if len(bpy.context.selected_objects)>0:
			return True
		return False

	def execute(self, context):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		#sel_all = [o.name for o in bpy.context.selected_objects]
		sel_all = []
		for sel_obj in bpy.context.selected_objects:
			if sel_obj.type == 'EMPTY' or sel_obj.type == 'ARMATURE' or sel_obj.data is None:
				continue
			#if sel_obj.data.shape_keys is not None and len(sel_obj.data.shape_keys.key_blocks):
			#	self.report({'ERROR'}, "Some objects has shapekeys: "+sel_obj.name)
			#	return {'CANCELLED'}
			sel_all.append(sel_obj.name)
		select_and_change_mode(active_obj,"OBJECT")
		if len(sel_all) == 0:
			self.report({'ERROR'}, "No objects selected")
			return {'CANCELLED'}
		deformToolsOpts = context.scene.deformToolsOpts
		cage_object = None
		try:
			cage_object = context.scene.objects[deformToolsOpts.bind_targ]
		except:
			pass
		if cage_object is None:
			self.report({'ERROR'}, "No proper cage found, choose mesh/lattice object first")
			return {'CANCELLED'}
		for md in cage_object.modifiers:
			self.report({'ERROR'}, "Cage has modifier: "+md.type)
			return {'CANCELLED'}
		if self.opt_makeWireInvis:
			makeObjectNoShadow(cage_object, True, True)
		modname = kWPLMeshDeformMod
		ok = 0
		error = 0
		maxSize = 0
		if cage_object.type == 'EMPTY':
			select_and_change_mode(cage_object,"OBJECT")
			maxSize = 2.0*max(max(cage_object.scale[0], cage_object.scale[1]), cage_object.scale[2])
			bpy.ops.view3d.snap_cursor_to_active()
		for i, sel_obj_name in enumerate(sel_all):
			if sel_obj_name == cage_object.name:
				continue
			sel_obj = context.scene.objects[sel_obj_name]
			print("Handling object "+str(i+1)+" of "+str(len(sel_all)), sel_obj.name)
			prevModifier = sel_obj.modifiers.get(modname)
			select_and_change_mode(sel_obj,"OBJECT")
			if sel_obj.type == 'MESH' or sel_obj.type == 'CURVE':
				if cage_object.type == 'LATTICE':
					if prevModifier is not None:
						sel_obj.modifiers.remove(prevModifier)
					meshdef_modifier = sel_obj.modifiers.new(name = modname, type = 'LATTICE')
					meshdef_modifier.object = cage_object
					meshdef_modifier.show_in_editmode = True
					meshdef_modifier.show_on_cage = True
					if sel_obj.type == 'CURVE':
						meshdef_modifier.use_apply_on_spline = True
					modfSendBackByType(sel_obj, 'SHRINKWRAP')
					modfSendBackByType(sel_obj, 'SUBSURF')
					ok = ok+1
				if cage_object.type == 'MESH':
					if prevModifier is not None:
						sel_obj.modifiers.remove(prevModifier)
					meshdef_modifier = sel_obj.modifiers.new(name = modname, type = 'MESH_DEFORM')
					meshdef_modifier.object = cage_object
					meshdef_modifier.precision = 5
					meshdef_modifier.use_dynamic_bind = True
					meshdef_modifier.show_in_editmode = True
					meshdef_modifier.show_on_cage = True
					if sel_obj.type == 'CURVE':
						meshdef_modifier.use_apply_on_spline = True
					modfSendBackByType(sel_obj, 'SOLIDIFY')
					modfSendBackByType(sel_obj, 'SUBSURF') #before binding!
					bpy.ops.object.meshdeform_bind(modifier=modname)
					ok = ok+1
				if cage_object.type == 'EMPTY':
					hookdef_modifier = sel_obj.modifiers.new(name = modname, type = 'HOOK')
					modname = hookdef_modifier.name #can be many
					hookdef_modifier.object = cage_object
					hookdef_modifier.falloff_radius = maxSize
					hookdef_modifier.falloff_type = 'SMOOTH'
					#hookdef_modifier.use_falloff_uniform = True
					hookdef_modifier.show_in_editmode = True
					hookdef_modifier.show_on_cage = True
					if sel_obj.type == 'CURVE':
						hookdef_modifier.use_apply_on_spline = True
					modfSendBackByType(sel_obj, 'SOLIDIFY')
					modfSendBackByType(sel_obj, 'SUBSURF') #before binding!
					select_and_change_mode(sel_obj,"EDIT")
					if sel_obj.type == 'CURVE':
						bpy.ops.curve.select_all(action='SELECT')
					else:
						bpy.ops.mesh.select_all(action='SELECT')
					bpy.ops.object.hook_assign(modifier=modname)
					bpy.ops.object.hook_reset(modifier=modname)
					bpy.ops.object.hook_recenter(modifier=modname)
					if sel_obj.type == 'CURVE':
						bpy.ops.curve.select_all(action='DESELECT')
					else:
						bpy.ops.mesh.select_all(action='DESELECT')
					select_and_change_mode(sel_obj,"OBJECT")
					ok = ok+1
		self.report({'INFO'}, "Done: count="+str(ok)+"/"+str(len(sel_all)))
		select_and_change_mode(active_obj,"OBJECT")
		return {'FINISHED'}

class wpldeform_objlattc(bpy.types.Operator):
	bl_idname = "object.wpldeform_objlattc"
	bl_label = "Add Lattice for object"
	bl_options = {'REGISTER', 'UNDO'}

	opt_orientation = EnumProperty(
		name="Orientation", default="OBJECT",
		items=(("OBJECT", "Object", ""), ("CAMERA", "Look2Cam", ""))
	)
	opt_origin = EnumProperty(
		name="Origin", default="OBJECT",
		items=(("OBJECT", "Object", ""), ("CURSOR", "3D-Cursor", ""))
	)
	opt_dimensions = IntVectorProperty(
		name = "Dimensions",
		size= 3,
		default = (2,5,5)
	)

	@classmethod
	def poll(self, context):
		p = context.object
		return p

	def execute(self, context):
		if context.scene.objects.active is None:
			self.report({'ERROR'}, "No objects selected")
			return {'FINISHED'}
		active_obj = context.scene.objects.active
		latname = active_obj.name+"_lattice"
		lattice_data = bpy.data.lattices.new(name=latname)
		lattice_object = bpy.data.objects.new(name=latname, object_data=lattice_data)
		#lattice_data.interpolation_type_u = self.interpolation_type
		#lattice_data.interpolation_type_v = self.interpolation_type
		#lattice_data.interpolation_type_w = self.interpolation_type
		lattice_data.points_u = int(self.opt_dimensions[0])
		lattice_data.points_v = int(self.opt_dimensions[1])
		lattice_data.points_w = int(self.opt_dimensions[2])
		#lattice_data.use_outside = True
		lattice_object.show_x_ray = True
		context.scene.objects.link(object=lattice_object)
		lattice_object.parent = active_obj.parent
		#lattice_object.rotation_euler = active_obj.rotation_euler
		#lattice_object.location = active_obj.location
		lattice_object.matrix_local = active_obj.matrix_local
		lattice_object.dimensions = active_obj.dimensions
		if self.opt_orientation == 'CAMERA':
			camera_obj = context.scene.objects.get(kWPLEdgesMainCam)
			if camera_obj is not None:
				followCon = lattice_object.constraints.new('TRACK_TO')
				#followCon.track_axis = 'TRACK_NEGATIVE_Y'
				followCon.track_axis = 'TRACK_X'
				followCon.target = camera_obj
		if self.opt_origin == 'CURSOR':
			c_co = get_active_context_cursor(context)
			lattice_object.location = lattice_object.matrix_world.inverted()*c_co
		deformToolsOpts = context.scene.deformToolsOpts
		deformToolsOpts.bind_targ = lattice_object.name
		#context.scene.objects.active = lattice_object
		return {'FINISHED'}

# class wpldeform_combmesh(bpy.types.Operator):
# 	bl_idname = "object.wpldeform_combmesh"
# 	bl_label = "Add joined mesh"
# 	bl_options = {'REGISTER', 'UNDO'}

# 	opt_allowMirror = BoolProperty(
# 		name="Allow mirror",
# 		default = False,
# 	)
	
# 	def execute(self, context):
# 		active_obj = context.scene.objects.active
# 		objs2checkNames = [o.name for o in bpy.context.selected_objects]
# 		if active_obj is None or len(objs2checkNames) < 1 or active_obj.data is None:
# 			self.report({'ERROR'}, "No objects selected")
# 			return {'CANCELLED'}
# 		for sel_obj_name in objs2checkNames:
# 			sel_obj = context.scene.objects.get(sel_obj_name)
# 			if self.opt_allowMirror == False and modfGetByType(sel_obj,'MIRROR'):
# 				self.report({'ERROR'}, "Some object has MIRROR:"+sel_obj.name)
# 				return {'FINISHED'}
# 		kWPLConvHullObj = "_joined_"
# 		isSingleBodyMode = False
# 		if len(objs2checkNames) == 1 and bpy.context.mode == 'OBJECT':
# 			isSingleBodyMode = True
# 		hullNameBase = kWPLConvHullObj + active_obj.name + kWPLFrameBindPostfix + str(bpy.context.scene.frame_current)
# 		if isSingleBodyMode == False:
# 			hullName = hullNameBase + "_collider"
# 		else:
# 			hullName = hullNameBase
# 		hullOld = context.scene.objects.get(hullName)
# 		if hullOld is not None:
# 			bpy.data.objects.remove(hullOld, True)
# 		if isSingleBodyMode: # special case for single item (finalized body)
# 			sel_obj = context.scene.objects.get(objs2checkNames[0])
# 			select_and_change_mode(sel_obj, 'OBJECT' )
# 			bpy.ops.object.duplicate(linked=False, mode='TRANSLATION')
# 			bpy.ops.object.wplbind_applytransf() # WPL, finalize all
# 			bm2_obj = bpy.context.selected_objects[0] # new object
# 			bm2_obj.name = hullName
# 			setBmPinmap(bm2_obj, kWPLPinmapUV+"_ini")
# 			setBmPinmap(active_obj, kWPLPinmapUV+"_ini", True)
# 			self.report({'INFO'}, "Done (single object)")
# 			return {'FINISHED'}
# 		bm2 = bmesh.new()
# 		for sel_obj_name in objs2checkNames:
# 			sel_obj = context.scene.objects.get(sel_obj_name)
# 			print("Grabbing ",sel_obj)
# 			select_and_change_mode(sel_obj, 'OBJECT' )
# 			sel_mesh = None
# 			try:
# 				sel_mesh = sel_obj.to_mesh(context.scene, True, 'PREVIEW')
# 				sel_mesh.transform(sel_obj.matrix_world)
# 			except:
# 				pass
# 			if sel_mesh is None:
# 				print("No mesh for ",sel_obj)
# 				continue
# 			bm2.from_mesh(sel_mesh)
# 			bpy.data.meshes.remove(sel_mesh)
# 		bm2m = bpy.data.meshes.new(hullNameBase + "_mesh")
# 		bm2_obj = bpy.data.objects.new(hullName, bm2m)
# 		bpy.context.scene.objects.link(bm2_obj)
# 		bm2.to_mesh(bm2m)
# 		select_and_change_mode(bm2_obj, 'OBJECT' )
# 		bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
# 		moveObjectOnLayer(bm2_obj,kWPLSystemLayer)
# 		bpy.context.scene.update()
# 		setBmPinmap(bm2_obj, kWPLPinmapUV+"_ini")
# 		for sel_obj_name in objs2checkNames:
# 			sel_obj = context.scene.objects.get(sel_obj_name)
# 			setBmPinmap(sel_obj, kWPLPinmapUV+"_ini", True)
# 		self.report({'INFO'}, "Done")
# 		return {'FINISHED'}

class wpldeform_extrhull(bpy.types.Operator):
	bl_idname = "object.wpldeform_extrhull"
	bl_label = "Extract convex (v-sel)"
	bl_options = {'REGISTER', 'UNDO'}

	opt_targetObjName = StringProperty(
		name="Convex Name",
		default = "zzz_hull",
	)
	opt_makeWireInvis = BoolProperty(
		name="Sys & Wireframe & No-Render",
		default = True,
	)

	@classmethod
	def poll(self, context):
		return ( context.object is not None)

	def execute(self, context):
		active_obj = context.scene.objects.active
		if active_obj is None:
			return {"CANCELLED"}
		if get_isLocalView():
			self.report({'ERROR'}, "Can`t work in Local view")
			return {'CANCELLED'}
		active_mesh = active_obj.data
		selverts = []
		select_and_change_mode(active_obj, 'EDIT' )
		bm = bmesh.from_edit_mesh(active_mesh)
		for bm_v in bm.verts:
			if bm_v.select:
				selverts.append(active_obj.matrix_world * copy.copy(bm_v.co))
		select_and_change_mode(active_obj, 'OBJECT' )
		hullObj = context.scene.objects.get(self.opt_targetObjName)
		if hullObj is None:
			bm2m = bpy.data.meshes.new(self.opt_targetObjName + "_mesh")
			bm2_obj = bpy.data.objects.new(self.opt_targetObjName, bm2m)
			bpy.context.scene.objects.link(bm2_obj)
		hullObj = context.scene.objects.get(self.opt_targetObjName)
		select_and_change_mode(hullObj, 'EDIT' )
		bm2 = bmesh.from_edit_mesh(hullObj.data)
		hullv = []
		for co_g in selverts:
			co_l = hullObj.matrix_world.inverted() * co_g
			bm2v = bm2.verts.new(co_l)
			hullv.append(bm2v)
		bm2.verts.ensure_lookup_table()
		bm2.verts.index_update()
		result = bmesh.ops.convex_hull(bm2, input=hullv)
		if "geom_unused" in result and len(result["geom_unused"])>0:
			for v in result["geom_unused"]:
				bm2.verts.remove(v)
		select_and_change_mode(hullObj, 'OBJECT' )
# 		hullParent = active_obj.parent
# 		if self.opt_makeWireInvis:
# 			kWPLConvHullObj = "sys_hull_"
# 			hullParent = getSysEmpty(context,"")
		bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
		moveObjectOnLayer(hullObj,kWPLSystemLayer)
		bpy.context.scene.update()
		if self.opt_makeWireInvis:
			makeObjectNoShadow(hullObj, True, True)
		self.report({'INFO'}, "Done")
		return {'FINISHED'}

# class wpldeform_convhull(bpy.types.Operator):
# 	bl_idname = "object.wpldeform_convhull"
# 	bl_label = "Add convex hull (v-sel)"
# 	bl_options = {'REGISTER', 'UNDO'}

# 	opt_makeWireInvis = BoolProperty(
# 		name="Sys & Wireframe & No-Render",
# 		default = True,
# 	)
# 	opt_combineAll = BoolProperty(
# 		name="Combine all verts",
# 		default = True,
# 	)
# 	opt_addDisplace = FloatProperty(
# 		name="Displace",
# 		min = -100, max = 100,
# 		default = 0.0,
# 	)
# 	opt_addRemesh = IntProperty(
# 		name="Remesh",
# 		min = 0, max = 12,
# 		default = 0,
# 	)

# 	@classmethod
# 	def poll(self, context):
# 		return ( context.object is not None)

# 	def execute(self, context):
# 		active_obj = context.scene.objects.active
# 		active_mesh = active_obj.data
# 		meshes_verts = []
# 		needToSetObjectMode = True
# 		hullHsh = 0.0
# 		if bpy.context.mode != 'OBJECT':
# 			needToSetObjectMode = False
# 			sel_mesh = None
# 			try:
# 				bpy.ops.mesh.select_mode(type='VERT')
# 				select_and_change_mode(active_obj, 'OBJECT' )
# 				sel_mesh = active_obj.to_mesh(context.scene, True, 'PREVIEW')
# 				if sel_mesh is None:
# 					self.report({'ERROR'}, "No mesh")
# 					return {'CANCELLED'}
# 				if self.opt_combineAll == True:
# 					mesh_verts = []
# 					for v in sel_mesh.vertices:
# 						if v.select:
# 							hullHsh = hullHsh+v.co[0]+v.co[1]+v.co[2]
# 							mesh_verts.append(active_obj.matrix_world*v.co)
# 					if len(mesh_verts) >= 3:
# 						meshes_verts.append(mesh_verts)
# 				else:
# 					bm = bmesh.new()
# 					bm.from_mesh(sel_mesh)
# 					bm.verts.ensure_lookup_table()
# 					bm.verts.index_update()
# 					selverts = []
# 					for bm_v in bm.verts:
# 						if bm_v.select:
# 							selverts.append(bm_v.index)
# 					allVertsIslandsed = splitBmVertsByLinks_v02(bm, selverts, True)
# 					for meshlist in allVertsIslandsed:
# 						if len(meshlist)>0:
# 							mesh_verts = []
# 							for bm_v2Idx in meshlist:
# 								bm_v2 = bm.verts[bm_v2Idx]
# 								hullHsh = hullHsh+bm_v2.co[0]+bm_v2.co[1]+bm_v2.co[2]
# 								mesh_verts.append(active_obj.matrix_world*bm_v2.co)
# 							if len(mesh_verts) >= 3:
# 								meshes_verts.append(mesh_verts)
# 				select_and_change_mode(active_obj, 'EDIT' )
# 			except Exception as e:
# 				print("Exception e",e)
# 				pass
# 			if sel_mesh is not None:
# 				bpy.data.meshes.remove(sel_mesh)
# 		else:
# 			objs2checkNames = [o.name for o in bpy.context.selected_objects]
# 			if len(objs2checkNames) < 1:
# 				self.report({'ERROR'}, "No objects selected")
# 				return {'CANCELLED'}
# 			mesh_verts = []
# 			for sel_obj_name in objs2checkNames:
# 				sel_obj = context.scene.objects.get(sel_obj_name)
# 				print("Grabbing ",sel_obj)
# 				select_and_change_mode(sel_obj, 'OBJECT' )
# 				if sel_obj.type == 'CURVE':
# 					mesh_verts = []
# 					initialCount = len(sel_obj.data.splines)
# 					for i in range(initialCount):
# 						polylineI = sel_obj.data.splines[i]
# 						points = getPolylinePoint(polylineI)
# 						for p in points:
# 							mesh_verts.append(sel_obj.matrix_world*Vector((p.co[0], p.co[1], p.co[2])))
# 							if modfGetByType(sel_obj,'MIRROR'):
# 								mesh_verts.append(sel_obj.matrix_world*Vector((-1*p.co[0], p.co[1], p.co[2])))
# 					meshes_verts.append(mesh_verts)
# 				else:
# 					sel_mesh = None
# 					try:
# 						sel_mesh = sel_obj.to_mesh(context.scene, True, 'PREVIEW')
# 					except:
# 						pass
# 					if sel_mesh is None:
# 						print("No mesh for ",sel_obj)
# 						continue
# 					if self.opt_combineAll == False:
# 						mesh_verts = []
# 					for v in sel_mesh.vertices:
# 						if v.hide:
# 							continue
# 						mesh_verts.append(sel_obj.matrix_world*v.co)
# 					if self.opt_combineAll == False:
# 						if len(mesh_verts) >= 3:
# 							meshes_verts.append(mesh_verts)
# 					bpy.data.meshes.remove(sel_mesh)
# 					if self.opt_combineAll == True:
# 						if len(mesh_verts) >= 3:
# 							meshes_verts.append(mesh_verts)
# 		if len(meshes_verts) == 0:
# 			self.report({'ERROR'}, "Select more verts")
# 			return {'FINISHED'}
# 		bm2 = bmesh.new()
# 		for mesh_verts in meshes_verts:
# 			hullv = []
# 			for co in mesh_verts:
# 				bm2v = bm2.verts.new(co)
# 				hullv.append(bm2v)
# 			bm2.verts.ensure_lookup_table()
# 			bm2.verts.index_update()
# 			print("Adding convex: ",len(hullv))
# 			result = bmesh.ops.convex_hull(bm2, input=hullv)
# 			if "geom_unused" in result and len(result["geom_unused"])>0:
# 				for v in result["geom_unused"]:
# 					bm2.verts.remove(v)
# 		hullHsh_str = str(int(hullHsh*10000)%10000)
# 		kWPLConvHullObj = "hull_"
# 		hullParent = active_obj.parent
# 		if self.opt_makeWireInvis:
# 			kWPLConvHullObj = "sys_hull_"
# 			hullParent = getSysEmpty(context,"")
# 		hullName = kWPLConvHullObj + active_obj.name + hullHsh_str + "_collider"
# 		hullOld = context.scene.objects.get(hullName)
# 		if hullOld is not None:
# 			bpy.data.objects.remove(hullOld, True)
# 		bm2m = bpy.data.meshes.new(kWPLConvHullObj + active_obj.name+"_mesh")
# 		bm2ob = bpy.data.objects.new(hullName, bm2m)
# 		bpy.context.scene.objects.link(bm2ob)
# 		bm2.to_mesh(bm2m)
# 		modifiers = bm2ob.modifiers
# 		if abs(self.opt_addDisplace) > 0.0001:
# 			displ_modifier = modifiers.new('WPLTMPDISPL', type = 'DISPLACE')
# 			displ_modifier.direction = 'NORMAL'
# 			displ_modifier.mid_level = 0.0
# 			displ_modifier.strength = self.opt_addDisplace
# 		if self.opt_addRemesh > 0:
# 			remesh_modifier = modifiers.new('WPLTMPREMESH', 'REMESH')
# 			remesh_modifier.mode = 'SMOOTH'
# 			remesh_modifier.scale = 0.99
# 			remesh_modifier.use_remove_disconnected = False
# 			remesh_modifier.octree_depth = self.opt_addRemesh
# 		if self.opt_makeWireInvis:
# 			bm2ob.parent = hullParent
# 			makeObjectNoShadow(bm2ob, True, True)
# 		else:
# 			bm2ob.parent = hullParent
# 			bm2ob.matrix_parent_inverse = hullParent.matrix_world.inverted()
# 		if needToSetObjectMode:
# 			select_and_change_mode(bm2ob, 'OBJECT' )
# 			bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
# 		moveObjectOnLayer(bm2ob,kWPLSystemLayer)
# 		self.report({'INFO'}, "Done")
# 		return {'FINISHED'}

class wpldeform_smart_extrude(bpy.types.Operator):
	bl_idname = "mesh.wpldeform_smart_extrude"
	bl_label = "Grow edge"
	bl_options = {'REGISTER', 'UNDO'}

	opt_stepDst = FloatProperty(
			name = "Step",
			default = 0.01
	)
	opt_shrwPositive = FloatProperty (
		name = "Collisions: Positive check",
		default = 0.0
	)
	opt_shrwNegative = FloatProperty (
		name = "Collisions: Negative check",
		default = 0.0
	)

	@classmethod
	def poll( cls, context ):
		return ( context.object is not None  and
				context.object.type == 'MESH' )
	def execute( self, context ):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		vertsIdx = get_selected_vertsIdx(active_mesh)
		edgesIdx = get_selected_edgesIdx(active_mesh)
		if len(edgesIdx) == 0:
			self.report({'ERROR'}, "No selected edges found")
			return {'FINISHED'}
		bpy.ops.object.mode_set( mode = 'EDIT' )
		bpy.ops.mesh.select_mode(type='VERT')
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.verts.index_update()
		bm.edges.ensure_lookup_table()
		bm.edges.index_update()
		bm.faces.ensure_lookup_table()
		bm.faces.index_update()
		edgelenAvg = getBmAverageEdgeLen(bm, vertsIdx, 1.0)
		bmduplisCache = {}
		vIdx_vccache = {}
		def getBmVertDupli(bm_v, v_dir):
			key = bm_v.index*10000 #+int(v_dir.dot(Vector((0,0,1)))*2)*1000+int(v_dir.dot(Vector((0,1,0)))*2)*100+int(v_dir.dot(Vector((1,0,0)))*2)*10
			if key in bmduplisCache:
				return bmduplisCache[key]
			v_dups = bmesh.ops.duplicate(bm, geom = [bm_v])
			vd = v_dups["geom"][0]
			bmduplisCache[key] = vd
			return vd
		bvh_self = BVHTree.FromBMesh(bm, epsilon = kWPLRaycastEpsilonCCL)
		newFaces = []
		edges2extent = []
		for eIdx in edgesIdx:
			e = bm.edges[eIdx]
			mface = None
			mdir0 = None
			mdir1 = None
			if len(e.link_faces) > 0:
				mface = e.link_faces[0]
				mdir = (e.verts[0].co+e.verts[1].co)*0.5-mface.calc_center_median()
			if mface is None:
				continue
			edst = mface.calc_perimeter()/len(mface.edges)
			edges2extent.append((e.verts[0], e.verts[1], mface, mdir))
		onCnt = 0
		vertAvgs = {}
		vertAvgsC = {}
		verts2sel = []
		for e_dat in edges2extent:
			e_v1 = e_dat[0]
			e_v2 = e_dat[1]
			srcf = e_dat[2]
			mdir = e_dat[3]
			mdir = mdir.normalized()
			mdst = self.opt_stepDst
			vd1 = getBmVertDupli(e_v1, mdir)
			vd2 = getBmVertDupli(e_v2, mdir)
			vd1.co = e_v1.co+mdir*mdst
			vd2.co = e_v2.co+mdir*mdst
			stepVerts = [vd1,vd2]
			fnrm = -1*srcf.normal
			e_axis = (e_v1.co-e_v2.co).normalized()
			e_nrm = e_axis.cross(mdir).normalized()
			if e_nrm.cross(fnrm).dot(e_axis) < 0:
				e_nrm = -1*e_nrm
			for vd in stepVerts:
				doNeg = True
				if self.opt_shrwPositive > 0.0:
					# bubbling if below the surface
					fuzzyhit = fuzzyBVHRayCast_v01(bvh_self, vd.co, e_nrm, self.opt_stepDst*0.05, 4)
					hit_co = fuzzyhit[0]
					if hit_co is not None and (hit_co-vd.co).length < self.opt_shrwPositive*self.opt_stepDst:
						hit2d = (hit_co-vd.co).normalized()
						vd.co = vd.co + mdir.cross(hit2d).cross(mdir)*mdst
						doNeg = False
				if doNeg and self.opt_shrwNegative > 0.0:
					# bubbling if below the surface
					fuzzyhit = fuzzyBVHRayCast_v01(bvh_self, vd.co, -1 * e_nrm, self.opt_stepDst*0.05, 4)
					hit_co = fuzzyhit[0]
					if hit_co is not None and (hit_co-vd.co).length < self.opt_shrwNegative*self.opt_stepDst:
						hit2d = (hit_co-vd.co).normalized()
						vd.co = vd.co + mdir.cross(hit2d).cross(mdir)*mdst
				if vd not in vertAvgs:
					vertAvgs[vd] = Vector((0,0,0))
					vertAvgsC[vd] = 0
				vertAvgs[vd] = vertAvgs[vd]+vd.co
				vertAvgsC[vd] = vertAvgsC[vd]+1.0
			f = bm.faces.new([vd1,vd2,e_v2,e_v1])
			verts2sel.append(vd1.index)
			verts2sel.append(vd2.index)
			verts2sel.append(e_v2.index)
			verts2sel.append(e_v1.index)
			f.select = False
			copyBMVertColtoFace(bm,srcf,f,vIdx_vccache)
			newFaces.append(f)
			for v in vertAvgs:
				if vertAvgsC[v]>1:
					onCnt = onCnt+1
					v.co = vertAvgs[v]/vertAvgsC[v]
					pass
		for v in bm.verts:
			v.select = False
			if v.index in verts2sel and v.index not in vertsIdx:
				v.select = True
		bmesh.ops.recalc_face_normals(bm, faces=newFaces)
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		bm.normal_update()
		bmesh.update_edit_mesh(active_mesh, True)
		bpy.ops.object.mode_set( mode = 'OBJECT' )
		bpy.ops.object.mode_set( mode = 'EDIT' )
		self.report({'INFO'}, "Verts moved: "+str(onCnt))
		return {'FINISHED'}

kWPDefaultStripifyWVal = "avgE*0.9"
kWPDefaultStripifyHVal = "avgE*0.5"
kWPDefaultStripifyXYCVal = "(0.0, 0.0, 0.5, 0.0)"
class wpldeform_stripify_edge(bpy.types.Operator):
	bl_idname = "mesh.wpldeform_stripify_edge"
	bl_label = "Stripify edges"
	bl_options = {'REGISTER', 'UNDO'}
	opt_action = EnumProperty(
		items = [
			('EDGESEL', "Selected edges", "", 1),
			('VERTHIST', "Vert history", "", 2),
			('INDIVELEM', "Individual", "", 3),
		],
		name="Action",
		default='VERTHIST',
	)
	EvalW = StringProperty(
			name = "Width=",
			default = kWPDefaultStripifyWVal
	)
	EvalH = StringProperty(
			name = "Height=",
			default = kWPDefaultStripifyHVal
	)
	EvalXYC = StringProperty(
			name = "(U,V,CC,R)=",
			default = kWPDefaultStripifyXYCVal
	)
	opt_FlowNorml = EnumProperty(
		items = [
			('AUTO', "Auto", "", 1),
			('LOCALZ', "Local Z", "", 2),
			('LOCALX', "Local X", "", 3),
			('LOCALY', "Local Y", "", 4),
		],
		name="Flow normal",
		default='AUTO',
	)
	opt_TurnScale = FloatProperty(
		name="Scale on turns",
		default=1.0 #1.4
	)
	opt_Solidify = BoolProperty(
		name="Solidify stripe",
		default=True
	)
	opt_selectNew = BoolProperty(
		name="Select added geom",
		default=True
	)

	@classmethod
	def poll( cls, context ):
		return ( context.object is not None  and
				context.object.type == 'MESH' )
	def execute( self, context ):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		vertsIdx = get_selected_vertsIdx(active_mesh)
		edgesIdx = get_selected_edgesIdx(active_mesh)
		facesIdx = get_selected_facesIdx(active_mesh)
		bpy.ops.object.mode_set( mode = 'EDIT' )
		if bpy.context.tool_settings.mesh_select_mode[2] == True: # 'FACE' selection
			selmode = 2
		elif bpy.context.tool_settings.mesh_select_mode[1] == True: # 'EDGE' selection
			selmode = 1
		else:
			selmode = 0
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.verts.index_update()
		bm.edges.ensure_lookup_table()
		bm.edges.index_update()
		bm.faces.ensure_lookup_table()
		bm.faces.index_update()
		refDir = Vector((0,0,1))
		edgelenAvg = getBmAverageEdgeLen(bm, vertsIdx, 1.0)

		strands_points = None
		strands_vidx = None
		strands_notcachables = []
		strands_vnrmreplace = {}
		if self.opt_action == 'INDIVELEM':
			strands_points = []
			strands_vidx = []
			if len(facesIdx) > 0 and selmode == 2:
				for fIdx in facesIdx:
					f = bm.faces[fIdx]
					flowDir = f.normal
					vIdx = f.verts[0].index
					v_co = f.calc_center_median()
					sideDir = (v_co-f.verts[0].co).normalized()
					strands_vnrmreplace[vIdx] = (sideDir.cross(flowDir)).cross(flowDir)
					strands_points.append([v_co - flowDir*edgelenAvg*0.5, v_co + flowDir*edgelenAvg*0.5])
					strands_vidx.append([[vIdx],[vIdx]])
					strands_notcachables.append(vIdx)
			if len(edgesIdx) > 0 and selmode == 1:
				for eIdx in edgesIdx:
					e = bm.edges[eIdx]
					flowDir = (e.verts[0].co-e.verts[1].co).normalized()
					vIdx = e.verts[0].index
					v_co =  (e.verts[0].co+e.verts[1].co)*0.5
					sideDir = (v_co-e.link_faces[0].calc_center_median()).normalized()
					strands_vnrmreplace[vIdx] = (sideDir.cross(flowDir)).cross(flowDir)
					strands_points.append([v_co - flowDir*edgelenAvg*0.5, v_co + flowDir*edgelenAvg*0.5])
					strands_vidx.append([[vIdx],[vIdx]])
					strands_notcachables.append(vIdx)
			if len(vertsIdx) > 0 and selmode == 0:
				for vIdx in vertsIdx:
					v = bm.verts[vIdx]
					flowDir = v.normal
					sideDir = refDir
					sideDirAng = -999
					for e in v.link_edges:
						edr = (v.co-e.other_vert(v).co).normalized()
						edrd = abs(edr.dot(refDir))
						if edrd > sideDirAng:
							sideDirAng = edrd
							sideDir = edr
					# if len(facesIdx) > 0 and selmode == 2:
					# 	closestDst = 999
					# 	for fIdx in facesIdx:
					# 		f = bm.faces[fIdx]
					# 		f_dst = (v.co-f.calc_center_median()).length
					# 		if f_dst<closestDst:
					# 			closestDst = f_dst
					# 			flowDir = f.normal
					strands_vnrmreplace[vIdx] = (sideDir.cross(flowDir)).cross(flowDir)
					strands_points.append([v.co - flowDir*edgelenAvg*0.5, v.co + flowDir*edgelenAvg*0.5])
					strands_vidx.append([[vIdx],[vIdx]])
					strands_notcachables.append(vIdx)
		if self.opt_action == 'VERTHIST':
			histVertsIdx = get_bmhistory_vertsIdx(bm)
			if len(histVertsIdx) > 0:
				strands_points_line = []
				strands_vidx_line = []
				for vIdx in reversed(histVertsIdx):
					v = bm.verts[vIdx]
					strands_points_line.append(v.co)
					strands_vidx_line.append([v.index])
				strands_points=[strands_points_line]
				strands_vidx=[strands_vidx_line]
		if self.opt_action == 'EDGESEL':
			if len(edgesIdx) > 0:
				(strands_points,strands_radius,strands_vidx) = getBmEdgesAsStrands_v04(bm, vertsIdx, edgesIdx, refDir, None)
		#print("strands_points",strands_points,strands_vidx)
		if strands_points is None or len(strands_points) == 0:
			self.report({'ERROR'}, "Nothing to do, check selection (no looped, etc)")
			return {'CANCELLED'}
		if self.opt_selectNew:
			#bpy.ops.object.select_all(action='DESELECT')
			bpy.ops.mesh.select_mode(type='VERT')
			for v in bm.verts:
				v.select = False
		if len(self.EvalW) == 0:
			self.EvalW = kWPDefaultStripifyWVal
		if len(self.EvalH) == 0:
			self.EvalH = kWPDefaultStripifyHVal
		if len(self.EvalXYC) == 0:
			self.EvalXYC = kWPDefaultStripifyXYCVal
		EvalW_py = None
		EvalH_py = None
		EvalXYC_py = None
		try:
			EvalW_py = compile(self.EvalW, "<string>", "eval")
			EvalH_py = compile(self.EvalH, "<string>", "eval")
			EvalXYC_py = compile(self.EvalXYC, "<string>", "eval")
		except:
			self.report({'ERROR'}, "Eval compilation: syntax error")
			return {'CANCELLED'}
		vIdx_cache = {}
		vIdx_vccache = {}
		def getVertsForStrokePoint(bm, vIdx, flowDir, flowDirNext, posFac, posOvl):
			if vIdx in vIdx_cache:
				return vIdx_cache[vIdx]
			bm.verts.ensure_lookup_table()
			bm.verts.index_update()
			bm_v = bm.verts[vIdx]
			if posOvl is not None:
				s3d = posOvl
			else:
				s3d = bm_v.co
			if vIdx in strands_vnrmreplace:
				cen_nrm = strands_vnrmreplace[vIdx]
			else:
				cen_nrm = bm_v.normal
			I = posFac
			avgE = edgelenAvg
			l_width = eval(EvalW_py)
			h_offset = eval(EvalH_py)
			uvc_offset = eval(EvalXYC_py)

			u_offset = float(uvc_offset[0])
			v_offset = float(uvc_offset[1])
			cc_offset = float(uvc_offset[2])
			r_angl_s = math.pi * float(uvc_offset[3])
			if self.opt_FlowNorml == 'LOCALZ':
				cen_nrm = Vector((0,0,1))
			if self.opt_FlowNorml == 'LOCALX':
				cen_nrm = Vector((1,0,0))
			if self.opt_FlowNorml == 'LOCALY':
				cen_nrm = Vector((0,1,0))
			cen_flow = flowDir.normalized() #s3d-bm.verts[prevIdx].co
			if flowDirNext is not None:
				flowDir = flowDir.normalized()
				flowDirNext = flowDirNext.normalized()
				cen_flow = ((flowDir+flowDirNext)*0.5).normalized()
				fld = 1.0-abs(flowDir.dot(flowDirNext))
				if fld > 0.0:
					l_width = (1.0-fld)*l_width+(fld)*(l_width*self.opt_TurnScale)
			cen_perp = cen_nrm.cross(cen_flow)
			cen_edge_vec = Matrix.Rotation(r_angl_s, 4, cen_flow) * cen_nrm
			cen_side_vec = (Matrix.Rotation(r_angl_s, 4, cen_flow) * cen_perp) * l_width
			s3d = s3d+(u_offset*l_width)*cen_perp.normalized()+(v_offset*l_width)*cen_nrm.normalized()
			cen_p = s3d + cen_edge_vec*h_offset
			v1_p = (cen_p + cen_side_vec*cc_offset)
			v2_p = (cen_p - cen_side_vec*(1.0-cc_offset))
			v1_dups = bmesh.ops.duplicate(bm, geom = [bm_v])
			v1 = v1_dups["geom"][0]
			v1.co = v1_p
			v2_dups = bmesh.ops.duplicate(bm, geom = [bm_v])
			v2 = v2_dups["geom"][0]
			v2.co = v2_p
			vIdx_cacheval = None
			if self.opt_Solidify:
				cen_p2 = s3d-cen_edge_vec*h_offset
				v3_p = (cen_p2 + cen_side_vec*cc_offset)
				v4_p = (cen_p2 - cen_side_vec*(1.0-cc_offset))
				#v3 = bm.verts.new(v3_p)
				v3_dups = bmesh.ops.duplicate(bm, geom = [bm_v])
				v3 = v3_dups["geom"][0]
				v3.co = v3_p
				#v4 = bm.verts.new(v4_p)
				v4_dups = bmesh.ops.duplicate(bm, geom = [bm_v])
				v4 = v4_dups["geom"][0]
				v4.co = v4_p
				vIdx_cacheval = (v1,v2,v4,v3)
			else:
				vIdx_cacheval = (v1,v2)
			#print("New points",vIdx,vIdx_cacheval,cen_p,cen_nrm,cen_perp)
			if vIdx not in strands_notcachables:
				vIdx_cache[vIdx] = vIdx_cacheval
			return vIdx_cacheval
		okCnt = 0
		for i, strand_curve in enumerate(strands_points):
			if len(strand_curve) < 2:
				print("Bad curve",strand_curve)
				continue
			vIdx_prv = 0
			flowDir = Vector((0,0,0))
			las_num = float(len(strand_curve))
			#print("- handling",i,"of",len(strands_points),"points:",len(strand_curve))
			bm_vf = None
			for j, co in enumerate(strand_curve):
				bm.verts.ensure_lookup_table()
				bm.faces.ensure_lookup_table()
				vIdx_now = strands_vidx[i][j][0]
				if vIdx_now>0:
					bm_v = bm.verts[vIdx_now]
					if len(bm_v.link_faces)>0:
						bm_vf = bm_v.link_faces[0]
				if j > 0:
					coLast = strand_curve[j-1]
					coThis = strand_curve[j]
					flowDir = coThis-coLast
					flowDirNext = None
					if j < len(strand_curve)-1:
						coNext = strand_curve[j+1]
						flowDirNext = coNext-coThis
					##########################################
					v_prev = getVertsForStrokePoint(bm, vIdx_prv, flowDir, flowDirNext, float(j-1)/las_num, coLast)
					v_this = getVertsForStrokePoint(bm, vIdx_now, flowDir, flowDirNext, float(j)/(las_num-1), coThis)
					f1 = bm.faces.new([v_prev[0],v_prev[1],v_this[1],v_this[0]])
					copyBMVertColtoFace(bm,bm_vf,f1,vIdx_vccache)
					if self.opt_Solidify:
						f2 = bm.faces.new([v_prev[1],v_prev[2],v_this[2],v_this[1]])
						f3 = bm.faces.new([v_prev[2],v_prev[3],v_this[3],v_this[2]])
						f4 = bm.faces.new([v_prev[3],v_prev[0],v_this[0],v_this[3]])
						copyBMVertColtoFace(bm,bm_vf,f2,vIdx_vccache)
						copyBMVertColtoFace(bm,bm_vf,f3,vIdx_vccache)
						copyBMVertColtoFace(bm,bm_vf,f4,vIdx_vccache)
					if self.opt_selectNew:
						v_prev[0].select = True
						v_prev[1].select = True
						v_this[0].select = True
						v_this[1].select = True
						if len(v_prev) == 4:
							v_prev[2].select = True
							v_prev[3].select = True
						if len(v_this) == 4:
							v_this[2].select = True
							v_this[3].select = True
					##########################################
					okCnt = okCnt+1
				vIdx_prv = vIdx_now
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		bm.normal_update()
		bmesh.update_edit_mesh(active_mesh, True)
		if okCnt == 0:
			self.report({'INFO'}, "Nothing added, no edges/histVerts")
		else:
			self.report({'INFO'}, "Faces added: "+str(okCnt))
		return {'FINISHED'}

class wpldeform_cutflow(bpy.types.Operator):
	bl_idname = "mesh.wpldeform_cutflow"
	bl_label = "Add CutPlane for object"
	bl_options = {'REGISTER', 'UNDO'}

	opt_action = EnumProperty(
		name="Action", default="STARTCUT",
		items=(("STARTCUT", "Start", ""), 
			("FINISHDELINS", "Finish: Del inside", ""),
			("FINISHDELOUT", "Finish: Del outside", ""),
			("FINISHDUPLI", "Finish: Duplicate", ""),
			("FINISHSEL", "Finish: Select", ""),
			("FINISHCANCEL", "Cancel cut", "")
		))

	@classmethod
	def poll(self, context):
		return True

	def execute(self, context):
		# adding cutplane2camera
		camera_obj = context.scene.objects.get(kWPLEdgesMainCam)
		if camera_obj is None:
			self.report({'ERROR'}, "Camera not found: "+kWPLEdgesMainCam)
			return {'CANCELLED'}
		cutp_obj = findChildObjectByName(camera_obj, kWPLEdgesMainCam+"_cutplane")
		if self.opt_action == "FINISHCANCEL":
			if "camcut_objects" in WPL_G.store:
				del WPL_G.store["camcut_objects"]
			if cutp_obj is not None:
				cutp_obj.hide = True
			select_and_change_mode(camera_obj, 'OBJECT')
			self.report({'INFO'}, "Cancelled")
		sel_all = [o.name for o in bpy.context.selected_objects]
		if len(sel_all) == 0:
			self.report({'ERROR'}, "No objects selected")
			return {'FINISHED'}
		needBack2LV = False
		if cutp_obj is None:
			if get_isLocalView():
				bpy.ops.view3d.localview()
				needBack2LV = True
			select_and_change_mode(camera_obj, 'OBJECT')
			bpy.ops.mesh.primitive_plane_add(radius=0.1, view_align=False, enter_editmode=False, location=Vector((0,0,-0.5)))
			cutp_obj = context.scene.objects.active
			cutp_obj.name = kWPLEdgesMainCam+"_cutplane"
			cutp_obj.data.name = kWPLEdgesMainCam+"_cutmesh"
			cutp_obj.parent = camera_obj
			makeObjectNoShadow(cutp_obj, True, True)
			cutp_obj.show_all_edges = True
		if cutp_obj is None:
			self.report({'ERROR'}, "Cant create cutplane")
			return {'FINISHED'}
		if self.opt_action == "STARTCUT":
			WPL_G.store["camcut_objects"] = sel_all
			select_and_change_mode(cutp_obj, 'OBJECT')
			if get_isLocalView():
				bpy.ops.view3d.localview()
				needBack2LV = True
			if needBack2LV == True:
				cutp_obj.select = True
				needBack2LV = False
				for obj_name in sel_all:
					obj = context.scene.objects.get(obj_name)
					obj.select = True
				bpy.ops.view3d.localview()
			bpy.ops.view3d.viewnumpad(type='TOP')
			bpy.ops.view3d.viewnumpad(type='CAMERA')
			bpy.context.scene.update()
			cutp_obj.hide = False
			select_and_change_mode(cutp_obj, 'EDIT')
			bpy.ops.mesh.select_mode(type='VERT')
			bpy.ops.mesh.select_all(action='SELECT')
			bpy.ops.mesh.delete(type='VERT')
			bm = bmesh.from_edit_mesh(cutp_obj.data)
			bm.verts.ensure_lookup_table()
			bm.verts.index_update()
			newv = bm.verts.new(Vector((0,0,0)))
			newv.select = True
			bmesh.update_edit_mesh(cutp_obj.data, True)
			self.report({'INFO'}, "Cutplane initialized")
		elif "camcut_objects" in WPL_G.store:
			# deletes
			sel_objs = WPL_G.store["camcut_objects"]
			del WPL_G.store["camcut_objects"]
			for obj_name in sel_objs:
				select_and_change_mode(cutp_obj, 'OBJECT')
				obj = context.scene.objects.get(obj_name)
				if kWPLEdgesMainCam in obj_name or obj.type != 'MESH':
					continue
				bpy.ops.object.select_all(action='DESELECT')
				cutp_obj.select = True
				obj.select = True
				bpy.context.scene.objects.active = obj
				bpy.context.scene.update()
				# NO!!! select_and_change_mode(obj, 'EDIT')
				bpy.ops.object.mode_set( mode = 'EDIT' )
				bpy.ops.mesh.select_all(action='DESELECT')
				bpy.ops.mesh.select_mode(type='EDGE')
				bpy.ops.mesh.knife_project(cut_through  = True)
				if self.opt_action == "FINISHSEL":
					pass
				if self.opt_action == "FINISHDUPLI":
					bpy.ops.mesh.duplicate()
				if self.opt_action == "FINISHDELINS":
					bpy.ops.mesh.split()
					bpy.ops.mesh.delete(type='VERT')
				if self.opt_action == "FINISHDELOUT":
					bpy.ops.mesh.split()
					bpy.ops.mesh.select_more()
					bpy.ops.mesh.select_all(action='INVERT')
					bpy.ops.mesh.delete(type='VERT')
				bpy.ops.mesh.select_mode(type='VERT')
			cutp_obj.hide = True
			self.report({'INFO'}, "Done")
		return {'FINISHED'}

class wpldeform_fill_simple(bpy.types.Operator):
	bl_idname = "mesh.wpldeform_fill_simple"
	bl_label = "Refill simple"
	bl_options = {'REGISTER', 'UNDO'}

	opt_flatnMeth = EnumProperty(
		items = [
			('FILL', "Usual fill", "", 1),
			('CENTR', "Bounds center", "", 2),
			('WFRAM', "Wireframe", "", 3),
		],
		name="Method",
		default='CENTR',
	)

	opt_postCuts = IntProperty(
		name		= "Post-Cuts",
		default	 = 0,
		min		 = 0,
		max		 = 100
		)

	@classmethod
	def poll( cls, context ):
		return ( context.object is not None  and
				context.object.type == 'MESH' )

	def execute( self, context ):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		selvertsAll = get_selected_vertsIdx(active_mesh)
		selfaceAll = get_selected_facesIdx(active_mesh)
		bpy.ops.object.mode_set( mode = 'EDIT' )
		if len(selfaceAll) == 0:
			bpy.ops.mesh.loop_to_region()
			selvertsAll = get_selected_vertsIdx(active_mesh)
			bpy.ops.object.mode_set( mode = 'EDIT' )
		bpy.ops.mesh.region_to_loop()
		selvertsBnd = get_selected_vertsIdx(active_mesh)
		# vertices in selection that are NOT on bound loops
		selvertsInner = list(filter(lambda plt: plt not in selvertsBnd, selvertsAll))
		bpy.ops.object.mode_set( mode = 'EDIT' )
		bpy.ops.mesh.select_mode(type='VERT')
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.edges.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		if self.opt_flatnMeth == 'WFRAM':
			bpy.ops.mesh.select_all(action = 'DESELECT')
			bpy.ops.mesh.select_mode(type='EDGE')
			len_min = 999.0
			len_sum = 0.0
			len_cnt = 0.0
			for e in bm.edges:
				if e.verts[0].index in selvertsBnd and e.verts[1].index in selvertsBnd:
					e.select = True
					len_e = e.calc_length()
					len_cnt = len_cnt+1.0
					len_sum = len_sum+len_e
					if len_e < len_min:
						len_min = len_e
			if len_cnt > 0:
				bmesh.update_edit_mesh(active_mesh)
				bpy.ops.mesh.duplicate()
				bpy.ops.mesh.edge_face_add()
				len_frac = 0.2
				bpy.ops.mesh.wireframe(use_replace=True, use_even_offset=True, use_relative_offset=True, thickness= len_sum/len_cnt*len_frac + (1.0-len_frac)*len_min)
				if self.opt_postCuts>0:
					bpy.ops.mesh.subdivide(number_cuts=self.opt_postCuts)
			return {'FINISHED'}
		if len(selvertsInner)>0:
			verts_select = [f for f in bm.verts if f.index in selvertsInner]
			bmesh.ops.delete(bm, geom=verts_select, context=1) #DEL_VERTS
		elif len(selfaceAll)>0:
			faces2del = []
			for fIdx in selfaceAll:
				faces2del.append(bm.faces[fIdx])
			bmesh.ops.delete(bm, geom=faces2del, context=5) #DEL_FACES
		bmesh.update_edit_mesh(active_mesh)
		if self.opt_flatnMeth == 'CENTR':
			if self.opt_postCuts>0:
				for i in range(self.opt_postCuts):
					bpy.ops.mesh.extrude_edges_move()
					scale = 1.0/(1+(self.opt_postCuts-i))
					bpy.ops.transform.resize(value = Vector((scale,scale,scale)))
			bpy.ops.mesh.extrude_edges_move() #bpy.ops.mesh.extrude_vertices_move()
			bpy.ops.mesh.merge(type='CENTER')
		else:
			bpy.ops.mesh.fill()
			if self.opt_postCuts>0:
				bpy.ops.mesh.subdivide(number_cuts=self.opt_postCuts)
		bpy.ops.mesh.faces_shade_smooth()
		return {'FINISHED'}

######################### ######################### #########################
######################### ######################### #########################
class WPLDeformToolsSettings(bpy.types.PropertyGroup):
	bind_targ = StringProperty(
		name="Deformer",
		description="Object deformer",
		default = ""
	)

class WPLDeformTools_Panel1(bpy.types.Panel):
	bl_label = "Mesh Deform"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_category = 'WPL'

	def draw_header(self, context):
		layout = self.layout
		layout.label(text="")

	def draw(self, context):
		obj = context.scene.objects.active
		deformToolsOpts = context.scene.deformToolsOpts
		layout = self.layout
		col = layout.column()
		box2 = col.box()
		box2.label("Edit actions")
		if "camcut_objects" not in WPL_G.store:
			box2.operator("mesh.wpldeform_cutflow", text='Start Camera Cut').opt_action = 'STARTCUT'
		else:
			box2.operator("mesh.wpldeform_cutflow", text='Finish cut: del inside').opt_action = 'FINISHDELINS'
			box2.operator("mesh.wpldeform_cutflow", text='Finish cut: del outside').opt_action = 'FINISHDELOUT'
			box2.operator("mesh.wpldeform_cutflow", text='Finish cut: duplicate').opt_action = 'FINISHDUPLI'
			box2.operator("mesh.wpldeform_cutflow", text='Finish cut: select').opt_action = 'FINISHSEL'
			box2.operator("mesh.wpldeform_cutflow", text='Cancel cut').opt_action = 'FINISHCANCEL'

		box2.separator()
		op = box2.operator("mesh.wpldeform_stripify_edge", text='Stripify fold')
		op.opt_action = 'VERTHIST'
		op.EvalW = "avgE*wpl_slope(0.1, 0.5, 1.0, 0.5, I)"
		op.EvalH = "avgE*0.5*wpl_slope(0.3, 0.6, 1.0, 0.5, I)"
		op.EvalXYC = "(0.0, 0.0, 0.5, 0.25)"
		op = box2.operator("mesh.wpldeform_stripify_edge", text='Stripify edges')
		op.opt_action = 'EDGESEL'
		op.EvalW = kWPDefaultStripifyWVal
		op.EvalH = kWPDefaultStripifyHVal
		op.EvalXYC = kWPDefaultStripifyXYCVal
		op = box2.operator("mesh.wpldeform_stripify_edge", text='Cubify')
		op.opt_action = 'INDIVELEM'
		op.EvalW = kWPDefaultStripifyHVal
		op.EvalH = kWPDefaultStripifyHVal
		op.EvalXYC = kWPDefaultStripifyXYCVal
		box2.operator("mesh.wpldeform_smart_extrude")
		box2.operator("mesh.wpldeform_fill_simple", text='Refill simple').opt_flatnMeth = 'CENTR'
		box2.operator("mesh.wpldeform_fill_simple", text='Add Wireframe').opt_flatnMeth = 'WFRAM'
		col.separator()
		box3 = col.box()
		addc2 = box3.operator("object.wpldeform_2curve", text = 'Add Deform curve+cube (selected)')
		addc2.opt_targetTune = 'DEFORM'
		addc2.opt_sourceMeth = 'SELC'
		#box3.operator("object.wpldeform_convhull")
		#box3.operator("object.wpldeform_combmesh")
		box3.separator()
		addc1 = box3.operator("object.wpldeform_2curve", text = 'Add Detail curve (v-hist)')
		addc1.opt_targetTune = 'DETAIL'
		addc1.opt_sourceMeth = 'VHIST'
		addc3 = box3.operator("object.wpldeform_2curve", text = 'Add Detail curve (selected)')
		addc3.opt_targetTune = 'DETAIL'
		addc3.opt_sourceMeth = 'SELC'
		box3.operator("object.wpldeform_extrskin")
		box3.operator("object.wpldeform_extrhull")
		col.separator()
		box1 = col.box()
		box1.prop_search(deformToolsOpts, "bind_targ", context.scene, "objects",icon="SNAP_NORMAL")
		box1.operator("mesh.wpldeform_bind", text="Selection: Multi-bind mesh/lat deform")
		box1.separator()
		box1.operator("object.wpldeform_objlattc")
		col.separator()

def register():
	bpy.utils.register_module(__name__)
	bpy.types.Scene.deformToolsOpts = PointerProperty(type=WPLDeformToolsSettings)

def unregister():
	bpy.utils.unregister_module(__name__)
	bpy.utils.unregister_class(WPLDeformToolsSettings)


if __name__ == "__main__":
	register()
