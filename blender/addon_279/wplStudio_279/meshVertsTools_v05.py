import math
import copy
import mathutils
import random
import time
from mathutils import kdtree
from bpy_extras import view3d_utils
import numpy as np
import datetime

import bpy
from bpy.props import *
import bpy.types
import bmesh
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree

bl_info = {
	"name": "Mesh Verts Tools",
	"author": "IPv6",
	"version": (1, 4, 6),
	"blender": (2, 7, 9),
	"location": "View3D > T-panel > WPL",
	"warning": "",
	"wiki_url": "",
	"tracker_url": "",
	"category": "WPL"}

kWPLRaycastEpsilon = 0.0001
kWPLRaycastDeadzone = 0.0
kWPLRaycastEpsilonCCL = 0.0001
kWPLSaveSelVGroup = "_sel"
kWPLHullIncKey = "wpl_helperobjs"
kWPLEdgesMainCam = "zzz_MainCamera"
kWPLTempOrien = "_TEMP"

kArmAlignBns_MB = 'neck, clavicle, pelvis, spine, upperarm_R+upperarm_twist_R, upperarm_L+upperarm_twist_L, lowerarm_R+lowerarm_twist_R, lowerarm_L+lowerarm_twist_L, thigh_R+thigh_twist_R, thigh_L+thigh_twist_L, calf_R+calf_twist_R, calf_L+calf_twist_L, foot, thumb01, thumb02, thumb03, pinky00, ring00, middle00, index00, pinky01, ring01, middle01, index01, pinky02, ring02, middle02, index02, pinky03, ring03, middle03, index03'
kArmAlignBns_MLOW = 'bn_shoulder, bn_upperarm, bn_forearm, bn_spine, bn_thigh, bn_shin, bn_foot, bn_toe, bn_hand, thumb01, thumb02, thumb03, pinky00, ring00, middle00, index00, pinky01, ring01, middle01, index01, pinky02, ring02, middle02, index02, pinky03, ring03, middle03, index03'

class WPL_G:
	store = {}
########### ############ ########### ############ ########### ############ ########### ############
########### ############ ########### ############ ########### ############ ########### ############
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
def get_selected_edgesIdx(active_mesh):
	# find selected faces
	bpy.ops.object.mode_set(mode='OBJECT')
	selectedEdgesIdx = [e.index for e in active_mesh.edges if e.select]
	return selectedEdgesIdx

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
def get_vertgroup_verts(obj, vertgroup, limit):
	def get_weights(ob, vgroup):
		group_index = vgroup.index
		for i, v in enumerate(ob.data.vertices):
			for g in v.groups:
				if g.group == group_index:
					yield (v, g.weight)
					break
	vertsCo = []
	vertsIdx = []
	vertsW = []
	for v, w in get_weights(obj, vertgroup):
		if w >= limit:
			vertsCo.append( v.co.copy() )
			vertsIdx.append(v.index)
			vertsW.append(w)
	return vertsCo,vertsIdx,vertsW

def getHelperObjId(context):
	if kWPLHullIncKey not in context.scene:
		context.scene[kWPLHullIncKey] = 1
	curId = context.scene[kWPLHullIncKey]
	context.scene[kWPLHullIncKey] = context.scene[kWPLHullIncKey]+1
	return curId

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
def get_bmhistory_refCo(active_bmesh):
	active_bmesh.verts.ensure_lookup_table()
	active_bmesh.verts.index_update()
	active_bmesh.edges.ensure_lookup_table()
	active_bmesh.edges.index_update()
	histVertsIdx = []
	histFacesIdx = []
	histEdgesIdx = []
	if bpy.context.tool_settings.mesh_select_mode[2] == True:
		histFacesIdx = get_bmhistory_faceIdx(active_bmesh)
	elif bpy.context.tool_settings.mesh_select_mode[1] == True:
		histEdgesIdx = get_bmhistory_edgesIdx(active_bmesh)
	else:
		histVertsIdx = get_bmhistory_vertsIdx(active_bmesh)
	if len(histFacesIdx)+len(histVertsIdx)+len(histEdgesIdx) == 0:
		return None
	fltCenter = Vector((0,0,0))
	fltNormal = Vector((0,0,0))
	fltAxe = None
	if len(histFacesIdx)>0:
		f = active_bmesh.faces[histFacesIdx[0]]
		fltCenter = f.calc_center_median()
		fltNormal = f.normal
	elif len(histEdgesIdx)>0:
		e = active_bmesh.edges[histEdgesIdx[0]]
		fltCenter = (e.verts[0].co+e.verts[1].co)*0.5
		fltNormal = (e.verts[0].normal+e.verts[1].normal)*0.5
		fltAxe = (e.verts[0].co-e.verts[1].co).normalized()
	else:
		v = active_bmesh.verts[histVertsIdx[0]]
		fltCenter = v.co
		fltNormal = v.normal
	return (fltCenter,fltNormal,fltAxe)

def get_bmedge_segmented(active_bmesh, edgIdxList, opt_angleprc):
	active_bmesh.verts.ensure_lookup_table()
	active_bmesh.verts.index_update()
	active_bmesh.edges.ensure_lookup_table()
	active_bmesh.edges.index_update()
	segments = []
	def findEdgeChain(eIdx):
		for chn in segments:
			if (chn is not None) and (eIdx in chn):
				return chn
		return None
	def findEdgeNextFromVert(e1, e1v):
		edgeAngls = []
		for e2 in e1v.link_edges:
			if e2 == e1:
				continue
			if e2.index not in edgIdxList:
				continue
			# if edges share same face - not a chain.
			if not set(e1.link_faces).isdisjoint(set(e2.link_faces)):
				continue
			vec1 = (e1v.co-e1.other_vert(e1v).co).normalized()
			vec2 = (e2.other_vert(e1v).co-e1v.co).normalized()
			flowdot = vec2.dot(vec1)
			flowang = math.acos(max(min(flowdot,1.0),-1.0))
			edgeAngls.append( (e2, flowang, math.degrees(flowang)) )
		edgeAngls = sorted(edgeAngls, key=lambda pr: pr[1], reverse=False)
		if len(edgeAngls) > 0:
			edgNext = edgeAngls[0][0]
			if edgeAngls[0][1] < opt_angleprc or len(edgeAngls) == 1:
				#print("? edgeAngls", edgeAngls)
				return edgNext
		return None
	allPossibleConnections = {}
	for eIdx in edgIdxList:
		segments.append([eIdx])
		ed = active_bmesh.edges[eIdx]
		edNext1 = findEdgeNextFromVert(ed, ed.verts[0])
		edNext2 = findEdgeNextFromVert(ed, ed.verts[1])
		if edNext1 is not None:
			edNext1A = findEdgeNextFromVert(edNext1, edNext1.verts[0])
			edNext1B = findEdgeNextFromVert(edNext1, edNext1.verts[1])
			if (edNext1A is not None and edNext1A == ed) or (edNext1B is not None and edNext1B == ed):
				conn_key = str(min(eIdx, edNext1.index))+"_"+str(max(eIdx, edNext1.index))
				if conn_key not in allPossibleConnections:
					allPossibleConnections[conn_key] = [ed.index, edNext1.index]
		if edNext2 is not None:
			edNext2A = findEdgeNextFromVert(edNext2, edNext2.verts[0])
			edNext2B = findEdgeNextFromVert(edNext2, edNext2.verts[1])
			if (edNext2A is not None and edNext2A == ed) or (edNext2B is not None and edNext2B == ed):
				conn_key = str(min(eIdx, edNext2.index))+"_"+str(max(eIdx, edNext2.index))
				if conn_key not in allPossibleConnections:
					allPossibleConnections[conn_key] = [ed.index, edNext2.index]
	print("Segmenting edges, cnt:", len(edgIdxList),"allConns:", len(allPossibleConnections))
	for conn_key in allPossibleConnections:
		merge_pair = allPossibleConnections[conn_key]
		chn1 = findEdgeChain(merge_pair[0])
		chn2 = findEdgeChain(merge_pair[1])
		if (chn1 is not None) and (chn2 is not None) and chn1 != chn2:
			for eccIdx in chn2:
				chn1.append(eccIdx)
			del chn2[:]
	segments_noEmpty = []
	segments = sorted(segments, key=lambda pr: len(pr), reverse=True)
	segments_byLen = {}
	for chn in segments:
		if chn is not None and len(chn) > 0:
			if len(chn) not in segments_byLen:
				segments_byLen[len(chn)] = 0
			segments_byLen[len(chn)] = segments_byLen[len(chn)]+1
			segments_noEmpty.append(chn)
	print("- found segments:", segments_byLen)
	return segments_noEmpty

def view_getActiveRegion():
	reg3d = bpy.context.space_data.region_3d
	if reg3d is not None:
		return reg3d
	for area in bpy.context.screen.areas:
		if area.type == 'VIEW_3D':
			return area.spaces.active.region_3d
def view_point3dToPoint2d(worldcoords, region):
	if region is None:
		region = bpy.context.space_data.region_3d
	out = view3d_utils.location_3d_to_region_2d(bpy.context.region, region, worldcoords)
	return out
def get_active_context_cursor(context):
	scene = context.scene
	space = context.space_data
	v3ds = (space if space and space.type == 'VIEW_3D' else scene)
	if v3ds is None:
		return None
	cursor = v3ds.cursor_location
	return cursor
def get_active_context_orient(context):
	scene = context.scene
	space = context.space_data
	v3ds = (space if space and space.type == 'VIEW_3D' else scene)
	if v3ds is None or v3ds.current_orientation is None:
		return None
	cu_matrix = v3ds.current_orientation.matrix.copy()
	return cu_matrix

def get_related_arma(obj):
	if obj is None:
		return None
	if obj.type == 'ARMATURE':
		return obj
	for md in obj.modifiers:
		if md.type == 'ARMATURE':
			return md.object
	# parent chain
	obj_tt = obj
	while obj_tt is not None:
		if obj_tt.data is not None and isinstance(obj_tt.data, bpy.types.Armature):
			return obj_tt
		obj_tt = obj_tt.parent
	return None

def select_by_arm(obj, opt_mb, opt_mlow, opt_unk):
	armatr = get_related_arma(obj)
	if armatr is None:
		return opt_unk
	rootbnames = [b.name.lower() for b in armatr.data.bones if not b.parent]
	if "bn_spine01" in rootbnames:
		return opt_mlow
	if "root" in rootbnames:
		return opt_mb
	return opt_unk

def getBmVertShortestPath_v01(bme, v1idx, v2idx, maxloops):
	path = []
	vertOriginMap = {}
	vertStepMap = {}
	step_vIdx = [v1idx]
	for curStep in range(maxloops):
		for vIdx in step_vIdx:
			if vIdx not in vertStepMap:
				vertStepMap[vIdx] = curStep+1
		nextStepIdx = {}
		nextStepDists = {}
		for vIdx in step_vIdx:
			v = bme.verts[vIdx]
			#for f in v.link_faces:
			for e in v.link_edges:
				#for fv in f.verts:
				fv = e.other_vert(v)
				if fv.hide != 0:
					continue
				if fv.index not in vertStepMap:
					edgelen = (fv.co - v.co).length
					if fv.index not in nextStepDists or edgelen < nextStepDists[fv.index]:
						nextStepDists[fv.index] = edgelen
						nextStepIdx[fv.index] = vIdx
						vertOriginMap[fv.index] = vIdx
					#nextStepIdx[fv.index] = vIdx
					#if fv.index not in vertOriginMap:
					#	vertOriginMap[fv.index] = [vIdx]
					#else:
					#	vertOriginMap[fv.index].append(vIdx)
		step_vIdx = []
		for vIdxNext in nextStepIdx:
			step_vIdx.append(vIdxNext)
		if v2idx in step_vIdx:
			# found path!!!
			step_vIdx = []
			vIdxNext = v2idx
			path.append(vIdxNext)
			while vIdxNext in vertOriginMap:
				vIdxPrev = vertOriginMap[vIdxNext]
				if vIdxPrev not in path:
					path.append(vIdxPrev)
				if vIdxPrev == vIdxNext:
					break
				vIdxNext = vIdxPrev
		if len(step_vIdx) == 0:
			break
	return path
	
def get_sceneColldersBVH(forObj, allowSelf):
	matrix_world_inv = None
	if forObj is not None:
		matrix_world = forObj.matrix_world
		matrix_world_inv = matrix_world.inverted()
	objs2checkAll = [obj for obj in bpy.data.objects]
	bvh2collides = []
	for obj in objs2checkAll:
		if allowSelf == False and forObj is not None and obj.name == forObj.name:
			continue
		if obj.hide == True:
			continue
		isColl = False
		if "_collider" in obj.name:
			isColl = True
		for md in obj.modifiers:
			if md.type == 'COLLISION':
				isColl = True
				break
		if isColl:
			print("- Collider found:",obj.name)
			bm_collide = None
			if obj.type != 'MESH':
				sel_mesh = None
				try:
					sel_mesh = obj.to_mesh(bpy.context.scene, True, 'PREVIEW')
				except:
					pass
				if sel_mesh is not None:
					bm_collide = bmesh.new()
					bm_collide.from_mesh(sel_mesh)
					bpy.data.meshes.remove(sel_mesh)
			else:
				bm_collide = bmesh.new()
				bm_collide.from_object(obj, bpy.context.scene)
			if bm_collide is not None:
				hiddenFaces = []
				for bm2f in bm_collide.faces:
					if bm2f.hide and bm2f not in hiddenFaces:
						hiddenFaces.append(bm2f)
				if len(hiddenFaces)>0:
					bmesh.ops.delete(bm_collide,geom=hiddenFaces,context=5)
				bm_collide.transform(obj.matrix_world)
				if matrix_world_inv is not None:
					bm_collide.transform(matrix_world_inv)
				bmesh.ops.recalc_face_normals(bm_collide, faces=bm_collide.faces) #??? strange results!!!
				bm_collide.verts.ensure_lookup_table()
				bm_collide.faces.ensure_lookup_table()
				bm_collide.verts.index_update()
				bvh_collide = BVHTree.FromBMesh(bm_collide, epsilon = kWPLRaycastEpsilonCCL)
				bm_collide.free()
				bvh2collides.append(bvh_collide)
	return bvh2collides

# def fuzzySceneRayCast_v02(vFrom, vDir, fuzzyVal, fuzzyQual, objs2ignore):
# 	gResult = mathutils.Vector((0,0,0))
# 	gResultNormal = mathutils.Vector((0,0,0))
# 	gCount = 0.0;
# 	vDirs = [vDir.normalized()]
# 	if fuzzyVal > 0.0:
# 		perpBase = mathutils.Vector((0,0,1))
# 		if(math.fabs(vDir.dot(perpBase)) > 0.9):
# 			perpBase = mathutils.Vector((0,1,0))
# 		perp1 = vDir.cross(perpBase)
# 		perp2 = vDir.cross(perp1)
# 		vDirs = [vDir.normalized()]
# 		for i in range(0,fuzzyQual):
# 			delim = float(i+1)/float(fuzzyQual)
# 			slice = [(vDir+delim*perp1*fuzzyVal).normalized(), (vDir-delim*perp1*fuzzyVal).normalized(), (vDir+delim*perp2*fuzzyVal).normalized(), (vDir-delim*perp2*fuzzyVal).normalized()]
# 			vDirs.extend(slice)

# 	for shootDir in vDirs:
# 		(result, loc_g, normal, index, object, matrix) = bpy.context.scene.ray_cast(vFrom+vDir*kWPLRaycastEpsilon, shootDir)
# 		#print("fuzzySceneRayCast", vFrom, shootDir, result, loc_g)
# 		if result and (objs2ignore is None or object.name not in objs2ignore):
# 			gCount = gCount+1.0
# 			gResult = gResult+loc_g
# 			gResultNormal = gResultNormal+normal

# 	if gCount>0:
# 		return (gResult/gCount,gResultNormal/gCount)
# 	return (None, None)

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
		return (gResult/gCount,gResultNormal/gCount)
	return (None, None)

def setBmPinmapFastIdx(active_obj, bm, pinId):
	bm.verts.ensure_lookup_table()
	bm.verts.index_update()
	bm.faces.ensure_lookup_table()
	bm.faces.index_update()
	pins_f = []
	pins_v = {}
	for vert in bm.verts:
		pindat = {}
		isSelect = 0
		if vert.select:
			isSelect = 1
		isHide = 0
		if vert.hide>0:
			isHide = 1
		pindat["co"] = copy.copy(vert.co)
		vert_co_g = active_obj.matrix_world * vert.co
		pindat["co_g"] = vert_co_g
		pindat["se"] = isSelect
		pindat["hi"] = isHide
		pins_v[vert.index] = pindat
	for f in bm.faces:
		if not f.select:
			continue
		if f.hide:
			continue
		faceverts = []
		for vert in f.verts:
			v_co_g = active_obj.matrix_world * vert.co
			faceverts.append(v_co_g)
		pins_f.append(faceverts)
	WPL_G.store[pinId] = pins_v
	WPL_G.store[pinId+"_selfaces"] = pins_f

def getBmPinmapFastIdx(active_obj, bm, pinId):
	if pinId not in WPL_G.store:
		return None, None
	pins_v = WPL_G.store[pinId]
	verts_dat = {}
	faces_dat = []
	if pinId+"_selfaces" in WPL_G.store:
		faces_dat = WPL_G.store[pinId+"_selfaces"]
	bm.verts.ensure_lookup_table()
	bm.verts.index_update()
	bm.faces.ensure_lookup_table()
	bm.faces.index_update()
	for vert in bm.verts:
		verts_dat[vert.index] = {}
		if vert.index not in pins_v:
			verts_dat[vert.index]["co"] = Vector(vert.co)
			verts_dat[vert.index]["co_g"] = active_obj.matrix_world * vert.co
			verts_dat[vert.index]["se"] = 0
			verts_dat[vert.index]["hi"] = 0
			verts_dat[vert.index]["idx"] = 0
		else:
			idxpin = pins_v[vert.index]
			verts_dat[vert.index]["co"] = Vector(idxpin["co"])
			verts_dat[vert.index]["co_g"] = Vector(idxpin["co_g"])
			verts_dat[vert.index]["se"] = idxpin["se"]
			verts_dat[vert.index]["hi"] = idxpin["hi"]
			verts_dat[vert.index]["idx"] = vert.index
	return verts_dat, faces_dat

kWPLConvexPrecision = 10000.0
def coToKey(co_vec):
	key = str(int(co_vec[0]*kWPLConvexPrecision))+"_"+str(int(co_vec[1]*kWPLConvexPrecision))+"_"+str(int(co_vec[2]*kWPLConvexPrecision))
	return key

def getVertsPropagations_v02(bm, smoothingLoops, initialVertsIdx):
	propagation_stages = []
	allWalkedVerts = []
	vertsFromIdx = {}
	#vertsFromRootIdx = {}
	vertsAddWeight = {}
	checked_verts = copy.copy(initialVertsIdx)
	for stage in range(1,int(smoothingLoops)+1):
		stage_verts = []
		checked_verts_cc = copy.copy(checked_verts)
		for v_idx in checked_verts_cc:
			v = bm.verts[v_idx]
			allWalkedVerts.append(v_idx)
			for edg in v.link_edges:
				v2 = edg.other_vert(v)
				if v2.hide == 0 and v2.index not in checked_verts_cc:
					if v2.index not in checked_verts:
						checked_verts.append(v2.index)
					if(v2.index not in stage_verts):
						vertsAddWeight[v2.index] = 1.0-(1.0+len(propagation_stages))/(1.0+smoothingLoops)
						stage_verts.append(v2.index)
						vertsFromIdx[v2.index] = []
					if v_idx not in vertsFromIdx[v2.index]:
						vertsFromIdx[v2.index].append(v_idx)
		if len(stage_verts) == 0:
			break
		propagation_stages.append(stage_verts)
	return (propagation_stages, vertsAddWeight, allWalkedVerts, vertsFromIdx)
#############################################################################################
#############################################################################################

# class wplverts_bubble_simple(bpy.types.Operator):
# 	bl_idname = "mesh.wplverts_bubble_simple"
# 	bl_label = "Bubble verts into direction"
# 	bl_options = {'REGISTER', 'UNDO'}

# 	opt_flatnMeth = EnumProperty(
# 		items = [
# 			('MESH_NORMALS', "Mesh, Normals", "", 1),
# 			('MESH_CAMERA', "Mesh, Camera", "", 2),
# 			('SCENE_NORMALS', "Scene, Normals", "", 3),
# 			('SCENE_CAMERA', "Scene, Camera", "", 4),
# 		],
# 		name="Method",
# 		description="Method",
# 		default='SCENE_NORMALS',
# 	)
# 	opt_ignoreHidden = BoolProperty(
# 			name="Ignore hidden",
# 			default=True,
# 	)
# 	opt_heightAbv = bpy.props.FloatProperty(
# 		name		= "Additional elevation",
# 		default	 = 0.0,
# 		min		 = -10,
# 		max		 = 10
# 	)
# 	opt_maxDist = bpy.props.FloatProperty(
# 		name		= "Max distance",
# 		default	 = 0.1,
# 		min		 = 0.00001,
# 		max		 = 100
# 		)

# 	opt_fuzzrcFac = bpy.props.FloatProperty(
# 		name		= "Fuzzy bubbling",
# 		default	 = 0.0,
# 		min		 = 0,
# 		max		 = 10
# 	)
# 	opt_influence = bpy.props.FloatProperty(
# 		name		= "Influence",
# 		default	 = 1.0,
# 		min		 = 0,
# 		max		 = 100
# 	)
# 	opt_inverseDir = BoolProperty(
# 			name="Inverse direction",
# 			default=False,
# 	)

# 	@classmethod
# 	def poll( cls, context ):
# 		return ( context.object is not None  and
# 				context.object.type == 'MESH' )

# 	def execute( self, context ):
# 		active_obj = context.scene.objects.active
# 		active_mesh = active_obj.data
# 		selvertsAll = get_selected_vertsIdx(active_mesh)
# 		if len(selvertsAll) == 0:
# 			self.report({'ERROR'}, "No selected vertices found")
# 			return {'CANCELLED'}
# 		camObj = context.scene.objects.get(kWPLEdgesMainCam)
# 		if camObj is None:
# 			self.report({'ERROR'}, "Camera not found: "+kWPLEdgesMainCam)
# 			return {'CANCELLED'}
# 		camera_gCo = camObj.matrix_world.to_translation() #camObj.location
# 		matrix_world_inv = active_obj.matrix_world.inverted()
# 		matrix_world_norm = matrix_world_inv.transposed().to_3x3()
# 		camera_lCo = matrix_world_inv * camera_gCo
# 		camera_gOrtho = False
# 		if camObj.data.type == 'ORTHO':
# 			camera_gOrtho = True
# 		bpy.ops.object.mode_set( mode = 'EDIT' )
# 		bm = bmesh.from_edit_mesh(active_mesh)
# 		bm.verts.ensure_lookup_table()
# 		bm.faces.ensure_lookup_table()
# 		bm.verts.index_update()
# 		bm2 = bm.copy()
# 		bm2.verts.ensure_lookup_table()
# 		bm2.faces.ensure_lookup_table()
# 		bm2.verts.index_update()
# 		v2rf = []
# 		for selvIdx in selvertsAll:
# 			selv = bm2.verts[selvIdx]
# 			for f in selv.link_faces:
# 				if f not in v2rf:
# 					v2rf.append(f)
# 		if self.opt_ignoreHidden: # deleting hidden faces
# 			for bm2f in bm2.faces:
# 				if bm2f.hide and bm2f not in v2rf:
# 					v2rf.append(bm2f)
# 		if len(v2rf) > 0: # https://blender.stackexchange.com/questions/1541/how-can-i-delete-mesh-parts-with-python
# 			bmesh.ops.delete(bm2,geom=v2rf,context=5)
# 		bm2_tree = BVHTree.FromBMesh(bm2, epsilon = kWPLRaycastEpsilon)
# 		bm2.free()
# 		collIgnore = [active_obj.name] # tracing to new geometry
# 		inner_verts = [ (vIdx, bm.verts[vIdx].co, bm.verts[vIdx].normal) for vIdx in selvertsAll if bm.verts[vIdx].hide == False]
# 		opt_normdir = 1.0
# 		if self.opt_inverseDir:
# 			opt_normdir = -1.0
# 		changesList = {}
# 		for w_v in inner_verts:
# 			hit = None
# 			w_v_i = w_v[0]
# 			w_v_co = w_v[1]
# 			w_v_n = w_v[2] # if defaultNormal is not None:#w_v_n = w_v_n.lerp(defaultNormal,self.opt_actvNormFac)
# 			if self.opt_flatnMeth == 'MESH_NORMALS':
# 				direction = w_v_n
# 				origin = w_v_co
# 				hit, hit_normal = fuzzyBVHRayCast_v01(bm2_tree, origin, opt_normdir*direction, self.opt_fuzzrcFac, 10)
# 				if hit is not None and (hit-origin).normalized().dot(hit_normal) < 0:
# 					hit = None
# 			if self.opt_flatnMeth == 'MESH_CAMERA':
# 				direction = (camera_lCo-w_v_co).normalized()
# 				origin = w_v_co
# 				hit, hit_normal = fuzzyBVHRayCast_v01(bm2_tree, origin, opt_normdir*direction, self.opt_fuzzrcFac, 10)
# 			if self.opt_flatnMeth == 'SCENE_NORMALS':
# 				direction = matrix_world_norm * w_v_n
# 				origin = active_obj.matrix_world * w_v_co
# 				hit_g, hit_normal = fuzzySceneRayCast_v02(origin, opt_normdir*direction, self.opt_fuzzrcFac, 10, collIgnore)
# 				if hit_g is not None and (hit_g-origin).normalized().dot(hit_normal) < 0:
# 					hit_g = None
# 				if hit_g is not None:
# 					hit = matrix_world_inv*hit_g
# 			if self.opt_flatnMeth == 'SCENE_CAMERA':
# 				direction = ( (matrix_world_norm * camera_lCo) - (matrix_world_norm * w_v_co)).normalized()
# 				origin = active_obj.matrix_world * w_v_co
# 				hit_g, hit_normal = fuzzySceneRayCast_v02(origin, opt_normdir*direction, self.opt_fuzzrcFac, 10, collIgnore)
# 				if hit_g is not None:
# 					hit = matrix_world_inv*hit_g
# 			if (hit is not None) and ((w_v_co-hit).length <= self.opt_maxDist):# lerping position
# 				vco_shift = hit - w_v_co
# 				vco = w_v_co + vco_shift*self.opt_influence
# 				vco = vco+self.opt_heightAbv*hit_normal
# 				changesList[w_v_i] = vco
# 		bpy.ops.mesh.select_mode(type='VERT')
# 		bpy.ops.mesh.select_all(action = 'DESELECT')
# 		for vIdx in changesList:
# 			v = bm.verts[vIdx]
# 			v.co = changesList[vIdx]
# 			v.select = True
# 		bmesh.update_edit_mesh(active_mesh, True)
# 		self.report({'INFO'}, "Moved: "+str(len(changesList)))
# 		return {'FINISHED'}

# class wplverts_bubble_colld(bpy.types.Operator):
# 	bl_idname = "mesh.wplverts_bubble_colld"
# 	bl_label = "Shrinkwrap to colliders"
# 	bl_options = {'REGISTER', 'UNDO'}

# 	opt_maxDistn = FloatProperty(
# 			name="Detection distance",
# 			min=0.00001, max=1000.0,
# 			default=0.05,
# 	)
# 	opt_distnPositive = BoolProperty(
# 			name="Positive direction",
# 			default=True,
# 	)
# 	opt_distnNegative = BoolProperty(
# 			name="Negative direction",
# 			default=True,
# 	)
# 	opt_withElevation = FloatProperty(
# 			name="Additional elevation",
# 			min=0.0, max=1000.0,
# 			default=0.0
# 	)
# 	opt_withSmoothing = FloatProperty(
# 			name="Additional smoothing",
# 			min=0.0, max=1.0,
# 			default=0.0
# 	)
# 	opt_influence = FloatProperty(
# 			name="Influence",
# 			min=0.0, max=1000.0,
# 			default=1.0,
# 	)
# 	opt_recastNormal = BoolProperty(
# 			name="With Normal recast",
# 			default=False,
# 	)

# 	@classmethod
# 	def poll( cls, context ):
# 		return ( context.object is not None  and
# 				context.object.type == 'MESH' )

# 	def execute( self, context ):
# 		active_obj = context.scene.objects.active
# 		active_mesh = active_obj.data
# 		selvertsAll = get_selected_vertsIdx(active_mesh)
# 		if len(selvertsAll) == 0:
# 			self.report({'ERROR'}, "No selected vertices found")
# 			return {'CANCELLED'}
# 		bvh2collides = get_sceneColldersBVH(active_obj,False)
# 		if len(bvh2collides) == 0:
# 			self.report({'ERROR'}, "Colliders not found: Need objects with collision modifier")
# 			return {'CANCELLED'}
# 		if self.opt_withSmoothing > 0.0:
# 			select_and_change_mode(active_obj,'EDIT')
# 			bpy.ops.mesh.vertices_smooth(factor=self.opt_withSmoothing)
# 		select_and_change_mode(active_obj,'OBJECT')
# 		print("- Moving vertices...")
# 		changesCount = 0
# 		changesIdx = []
# 		for vIdx in selvertsAll:
# 			for bvh_collide in bvh2collides:
# 				vert = active_mesh.vertices[vIdx]
# 				near_location, near_normal, near_index, near_distance = bvh_collide.find_nearest(vert.co, self.opt_maxDistn)
# 				if near_location is not None:
# 					rc_location = near_location
# 					if self.opt_recastNormal:
# 						rc_location, rc_normal, rc_index, rc_distance = bvh_collide.ray_cast(vert.co, near_normal, self.opt_maxDistn)
# 						if rc_location is None and self.opt_distnNegative == True:
# 							rc_location, rc_normal, rc_index, rc_distance = bvh_collide.ray_cast(vert.co, -1*near_normal, self.opt_maxDistn)
# 					if rc_location is not None and self.opt_distnPositive == False and (rc_location-vert.co).normalized().dot(vert.normal) > 0:
# 						rc_location = None
# 					if rc_location is not None and self.opt_distnNegative == False and (rc_location-vert.co).normalized().dot(vert.normal) < 0:
# 						rc_location = None
# 					if rc_location is not None:
# 						changesCount = changesCount+1
# 						changesIdx.append(vIdx)
# 						newCo = rc_location+self.opt_withElevation*near_normal
# 						vert.co = vert.co.lerp(newCo,self.opt_influence)
# 		select_and_change_mode(active_obj,'EDIT')
# 		bpy.ops.mesh.select_mode(type='VERT')
# 		bpy.ops.mesh.select_all(action = 'DESELECT')
# 		bm = bmesh.from_edit_mesh(active_mesh)
# 		bm.verts.ensure_lookup_table()
# 		for vIdx in changesIdx:
# 			bm_vert = bm.verts[vIdx]
# 			bm_vert.select = True
# 		bmesh.update_edit_mesh(active_mesh)
# 		self.report({'INFO'}, "Moved: "+str(changesCount))
# 		return {'FINISHED'}


class wplverts_pinsurfshrw(bpy.types.Operator):
	bl_idname = "mesh.wplverts_pinsurfshrw"
	bl_label = "Shrinkwrap to pinned"
	bl_options = {'REGISTER', 'UNDO'}

	opt_influence = FloatProperty(
		name		= "Influence",
		default	 = 1.0,
		min		 = 0,
		max		 = 1
	)
	opt_shrinkwMethod = EnumProperty(
		name="Detection method", default="NEAR",
		items=(("NEAR", "Near surface", ""), 
			("NEGPROJ", "Negative proj", ""),
			("CAMPROJ", "Project from camera", ""))
	)
	opt_vertsType = EnumProperty(
		name="Apply to verts", default="ALL",
		items=(("ALL", "All", ""), ("ABOVE", "Above surface", ""), ("UNDER", "Under surface", ""))
	)
	opt_makeConvex = BoolProperty(
		name="Shrinkwrap to convex", default=False
	)
	opt_dopFeats = FloatVectorProperty(
		name = "Softcast/Displace/???",
		size = 3,
		default	 = (0.5, 0.0, 0.0)
	)
	opt_pinId = StringProperty(
		name		= "Pin ID",
		default	 	= "fastpin1"
	)
	
	@classmethod
	def poll(self, context):
		p = context.object and context.object.data and context.object.type == 'MESH'
		return p

	def execute( self, context ):
		camObj = context.scene.objects.get(kWPLEdgesMainCam)
		if camObj is None:
			self.report({'ERROR'}, "Camera not found: "+kWPLEdgesMainCam)
			return {'CANCELLED'}
		active_obj = context.scene.objects.active
		if active_obj is None or active_obj.data is None:
			self.report({'ERROR'}, "No active object")
			return {'CANCELLED'}
		active_mesh = active_obj.data
		selvertsAll = get_selected_vertsIdx(active_mesh)
		if len(selvertsAll) == 0:
			self.report({'ERROR'}, "No verts selected")
			return {'FINISHED'}
		camera_gCo = camObj.matrix_world.to_translation()
		camera_gDir = camObj.matrix_world.to_3x3()*Vector((0.0, 0.0, 1.0))
		matrix_world_inv = active_obj.matrix_world.inverted()
		matrix_world_norm = matrix_world_inv.transposed().to_3x3()
		camera_lCo = matrix_world_inv * camera_gCo
		camera_lDir = matrix_world_norm.inverted() * camera_gDir
		camera_gOrtho = False
		if camObj.data.type == 'ORTHO':
			camera_gOrtho = True
		bpy.ops.object.mode_set( mode = 'EDIT' )
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.verts.index_update()
		bm.faces.ensure_lookup_table()
		bm.faces.index_update()
		bm2bvh = None

		#print("self.opt_pinId0", self.opt_pinId, self.opt_dopFeats)
		verts_snap_map, faces_snap_map = getBmPinmapFastIdx(active_obj, bm, self.opt_pinId)
		if faces_snap_map is not None:
			bm2 = bmesh.new()
			bm2vmap = {}
			bm2conv = []
			for f_vg in faces_snap_map:
				f_v_set = []
				f_v_set_ko = []
				for v_co_g in f_vg:
					v_co = matrix_world_inv * v_co_g
					vert_index = coToKey(v_co)
					if vert_index not in bm2vmap:
						v_cc = bm2.verts.new(v_co)
						bm2vmap[vert_index] = v_cc
					else:
						v_cc = bm2vmap[vert_index]
					#v_cc = bm2.verts.new(v_co)
					if v_cc not in f_v_set:
						f_v_set.append(v_cc)
						f_v_set_ko.append(vert_index)
				if len(f_v_set) >= 3:
					f_v_set_ko = sorted(f_v_set_ko)
					f_v_set_ko = ",".join(f_v_set_ko)
					if f_v_set_ko not in bm2vmap:
						bm2vmap[f_v_set_ko] = f_v_set
						f_cc = bm2.faces.new(f_v_set)
				if self.opt_makeConvex:
					for v_cc in f_v_set:
						if v_cc not in bm2conv:
							bm2conv.append(v_cc)
			if len(bm2conv)>0:
				res = bmesh.ops.convex_hull(bm2, input=bm2conv)
				bm2.verts.ensure_lookup_table()
				bm2.verts.index_update()
				bm2.faces.ensure_lookup_table()
				bm2.faces.index_update()
			bm2.normal_update()
			bm2bvh = BVHTree.FromBMesh(bm2, epsilon = kWPLRaycastEpsilonCCL)
			bm2.free()
		# if verts_snap_map is not None:
		# 	bufMapFaces = []
		# 	for face in bm.faces:
		# 		if face.index not in bufMapFaces:
		# 			for v in face.verts:
		# 				if verts_snap_map[v.index]["se"] > 0 and face.index not in bufMapFaces:
		# 					bufMapFaces.append(face.index)
		# 	bm2 = bmesh.new()
		# 	bm2vmap = {}
		# 	bm2conv = []
		# 	for fIdx in bufMapFaces:
		# 		f = bm.faces[fIdx]
		# 		f_v_set = []
		# 		for vert in f.verts:
		# 			v_co = verts_snap_map[vert.index]["co"]
		# 			if vert.index not in bm2vmap:
		# 				v_cc = bm2.verts.new(v_co)
		# 				bm2vmap[vert.index] = v_cc
		# 			f_v_set.append(bm2vmap[vert.index])
		# 		f_cc = bm2.faces.new(f_v_set)
		# 		if self.opt_makeConvex:
		# 			for v_cc in f_v_set:
		# 				if v_cc not in bm2conv:
		# 					bm2conv.append(v_cc)
		# 	if len(bm2conv)>0:
		# 		res = bmesh.ops.convex_hull(bm2, input=bm2conv)
		# 		bm2.verts.ensure_lookup_table()
		# 		bm2.verts.index_update()
		# 		bm2.faces.ensure_lookup_table()
		# 		bm2.faces.index_update()
		# 	bm2.normal_update()
		# 	bm2bvh = BVHTree.FromBMesh(bm2, epsilon = kWPLRaycastEpsilonCCL)
		# 	bm2.free()
		if bm2bvh is None:
			self.report({'ERROR'}, "No surface faces found, pin mesh with selected faces first")
			return {'CANCELLED'}

		vertsWeight = None
		vnormls = {}
		for vIdx in selvertsAll:
			v = bm.verts[vIdx]
			vnormls[vIdx] = v.normal
		okCnt = 0
		for vIdx in selvertsAll:
			v = bm.verts[vIdx]
			if self.opt_shrinkwMethod == 'NEAR':
				n_loc, n_normal, n_index, n_distance = bm2bvh.find_nearest(v.co)
			elif self.opt_shrinkwMethod == 'CAMPROJ':
				if camera_gOrtho:
					proj_dir = -1 * camera_lDir
				else:
					proj_dir = -1 * (camera_lCo - v.co).normalized()
				n_loc, n_normal = fuzzyBVHRayCast_v01(bm2bvh, v.co, proj_dir, self.opt_dopFeats[0], 4)
				if n_loc is not None:
					# recalcing, since "soft" can slide vertex, which is not needed on practice
					n_loc = v.co + proj_dir*(n_loc-v.co).length
				#n_loc, n_normal, n_index, n_distance = bm2bvh.ray_cast(v.co, proj_dir, 999)
			else: # NEGPROJ
				proj_dir = -1*vnormls[vIdx]
				n_loc, n_normal = fuzzyBVHRayCast_v01(bm2bvh, v.co, proj_dir, self.opt_dopFeats[0], 4)
				#n_loc, n_normal, n_index, n_distance = bm2bvh.ray_cast(v.co, proj_dir, 999)
			if n_loc is not None:
				n_normorg = n_normal
				dotFac = (v.co-n_loc).dot(n_normal)
				if self.opt_vertsType == 'ABOVE':
					if dotFac <= 0:
						continue
				if self.opt_vertsType == 'UNDER':
					if dotFac > 0:
						continue
				if abs(self.opt_dopFeats[1])>0.00001:
					n_loc = n_loc+n_normal*self.opt_dopFeats[1]
				infl = self.opt_influence
				v.co = v.co.lerp(n_loc,infl)
				okCnt = okCnt+1
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		bm.normal_update()
		bmesh.update_edit_mesh(active_mesh, True)
		self.report({'INFO'}, "Done, "+str(okCnt)+" verts moved")
		return {'FINISHED'}
		
class wplverts_loadsel(bpy.types.Operator):
	bl_idname = "mesh.wplverts_loadsel"
	bl_label = "Load selection"
	bl_options = {'REGISTER', 'UNDO'}

	opt_vgname = StringProperty(
		name		= "Group name",
		default	 	= ""
	)
	opt_deselVg = BoolProperty(
		name="Deselect, not select",
		default=False,
	)
	opt_deselCurrent = BoolProperty(
		name="Deselect current",
		default=True,
	)

	@classmethod
	def poll( cls, context ):
		return ( context.object is not None and
				context.object.type == 'MESH' )

	def execute( self, context ):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		if "!" in self.opt_vgname:
			remove_vertgroup(active_obj,self.opt_vgname[1:])
			return {'FINISHED'}
		select_and_change_mode(active_obj,"EDIT")
		mask_group = get_vertgroup_by_name(active_obj, self.opt_vgname)
		if mask_group is not None:
			#active_obj.vertex_groups.active = mask_group.index
			bpy.ops.object.vertex_group_set_active(group = mask_group.name)
			if self.opt_deselCurrent:
				bpy.ops.mesh.select_all( action = 'DESELECT' )
			if self.opt_deselVg:
				bpy.ops.object.vertex_group_deselect()
			else:
				bpy.ops.object.vertex_group_select()
			self.report({'INFO'}, "Loaded "+self.opt_vgname)
		return {'FINISHED'}

class wplverts_dirdesel(bpy.types.Operator):
	bl_idname = "mesh.wplverts_dirdesel"
	bl_label = "Deselect by direction"
	bl_options = {'REGISTER', 'UNDO'}
	
	opt_direction = FloatVectorProperty(
		name	 = "Direction",
		size	 = 3,
		default	 = (0.0,0.0,1.0)
	)
	opt_maxdiff = FloatProperty(
		name	 = "Max angle",
		min = 0, max = 180,
		default	 = 25
	)
	opt_inversion = BoolProperty(
		name="Treat direction as plane normal",
		default=False,
	)

	@classmethod
	def poll( cls, context ):
		return ( context.object is not None and
				context.object.type == 'MESH' )

	def execute( self, context ):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		seledgAll = get_selected_edgesIdx(active_mesh)
		selfaceAll = get_selected_facesIdx(active_mesh)
		if len(seledgAll)+len(selfaceAll) == 0:
			self.report({'ERROR'}, "No selected edges/faces found")
			return {'FINISHED'}
		select_and_change_mode(active_obj,"EDIT")
		bm = bmesh.from_edit_mesh( active_mesh )
		bm.edges.ensure_lookup_table()
		bm.edges.index_update()
		bm.faces.ensure_lookup_table()
		bm.faces.index_update()
		maindd = Vector((self.opt_direction[0],self.opt_direction[1],self.opt_direction[2])).normalized()
		if len(selfaceAll) > 0 and bpy.context.tool_settings.mesh_select_mode[2] == True: # 'FACE' selection
			deselFaces = []
			for fIdx in selfaceAll:
				f = bm.faces[fIdx]
				dir = f.normal.normalized()
				difang = math.acos(max(-1.0,min(1.0,abs(dir.dot(maindd)))))
				if self.opt_inversion == False and difang < math.radians(self.opt_maxdiff):
					deselFaces.append(fIdx)
				if self.opt_inversion == True and abs(math.radians(90)-difang) < math.radians(self.opt_maxdiff):
					deselFaces.append(fIdx)
			bpy.ops.mesh.select_all(action = 'DESELECT')
			bpy.ops.mesh.select_mode(type='FACE')
			for fIdx in selfaceAll:
				if fIdx not in deselFaces:
					f = bm.faces[fIdx]
					f.select = True
			self.report({'INFO'}, "Deselected: "+str(len(deselFaces))+" faces")
		else:
			deselEdges = []
			for eIdx in seledgAll:
				e = bm.edges[eIdx]
				dir = (e.verts[0].co-e.verts[1].co).normalized()
				difang = math.acos(max(-1.0,min(1.0,abs(dir.dot(maindd)))))
				if self.opt_inversion == False and difang < math.radians(self.opt_maxdiff):
					deselEdges.append(eIdx)
				if self.opt_inversion == True and abs(math.radians(90)-difang) < math.radians(self.opt_maxdiff):
					deselEdges.append(eIdx)
			bpy.ops.mesh.select_all(action = 'DESELECT')
			bpy.ops.mesh.select_mode(type='EDGE')
			for eIdx in seledgAll:
				if eIdx not in deselEdges:
					e = bm.edges[eIdx]
					e.select = True
			self.report({'INFO'}, "Deselected: "+str(len(deselEdges))+" edges")
		bmesh.update_edit_mesh(active_mesh)
		return {'FINISHED'}

class wplverts_chaindesel(bpy.types.Operator):
	bl_idname = "mesh.wplverts_chaindesel"
	bl_label = "Deselect short chains"
	bl_options = {'REGISTER', 'UNDO'}
	
	opt_chainlen = IntProperty(
		name	 = "Chain len threshold",
		default	 = 3
	)
	opt_angleprc = FloatProperty(
		name	 = "Max step angle",
		default	 = 360.0
	)
	opt_inversion = BoolProperty(
		name="Deselect bigger",
		default=False,
	)

	@classmethod
	def poll( cls, context ):
		return ( context.object is not None and
				context.object.type == 'MESH' )

	def execute( self, context ):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		seledgAll = get_selected_edgesIdx(active_mesh)
		if len(seledgAll) == 0:
			self.report({'ERROR'}, "No selected edges found")
			return {'FINISHED'}
		select_and_change_mode(active_obj,"EDIT")
		bm = bmesh.from_edit_mesh( active_mesh )
		bm.edges.ensure_lookup_table()
		bm.edges.index_update()
		edgeChains = get_bmedge_segmented(bm, seledgAll, math.radians(self.opt_angleprc))
		deselEdges = []
		for eIdx in seledgAll:
			e_chain = None
			for chn in edgeChains:
				if eIdx in chn:
					e_chain = chn
					break
			if (e_chain is not None) and self.opt_inversion == False and len(e_chain) <= self.opt_chainlen:
				deselEdges.append(eIdx)
			if (e_chain is not None) and self.opt_inversion == True and len(e_chain) >= self.opt_chainlen:
				deselEdges.append(eIdx)
		bpy.ops.mesh.select_all(action = 'DESELECT')
		bpy.ops.mesh.select_mode(type='EDGE')
		for eIdx in seledgAll:
			if eIdx not in deselEdges:
				e = bm.edges[eIdx]
				e.select = True
		# DBG
		# bpy.ops.mesh.select_all(action = 'DESELECT')
		# if self.opt_chainlen < len(edgeChains):
		# 	for eIdx in edgeChains[self.opt_chainlen]:
		# 		e = bm.edges[eIdx]
		# 		e.select = True
		bmesh.update_edit_mesh(active_mesh)
		self.report({'INFO'}, "Deselected: "+str(len(deselEdges))+" edges")
		return {'FINISHED'}

class wplverts_savesel(bpy.types.Operator):
	bl_idname = "mesh.wplverts_savesel"
	bl_label = "Save selection"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll( cls, context ):
		return ( context.object is not None and
				context.object.type == 'MESH' )

	def execute( self, context ):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		oldmode = select_and_change_mode(active_obj,"OBJECT")
		selvertsAll = get_selected_vertsIdx(active_mesh)
		if len(selvertsAll) == 0:
			self.report({'ERROR'}, "No selected vertices found")
			return {'FINISHED'}
		nextNumber = 1
		while get_vertgroup_by_name(active_obj, kWPLSaveSelVGroup+str(nextNumber)) is not None:
			nextNumber = nextNumber+1
		selVGName = kWPLSaveSelVGroup+str(nextNumber)
		mask_group = getornew_vertgroup(active_obj, selVGName)
		ok = 0
		for idx in selvertsAll:
			wmod = 'REPLACE'
			try:
				oldval = mask_group.weight(idx)
			except Exception as e:
				oldval = 0
				wmod = 'ADD'
			mask_group.add([idx], 1.0, wmod)
			ok = ok+1
		select_and_change_mode(active_obj,oldmode)
		active_mesh.update()
		self.report({'INFO'}, selVGName+": "+str(ok)+" verts")
		return {'FINISHED'}


class wplverts_selfill(bpy.types.Operator):
	bl_idname = "mesh.wplverts_selfill"
	bl_label = "Fill-Select"
	bl_options = {'REGISTER', 'UNDO'}

	opt_iterations = IntProperty(
		name	 = "Fill iterations",
		default	 = 10
	)

	opt_fillAcrossFaces = BoolProperty(
		name="Go across faces",
		default=True,
	)

	opt_aggressiveStop = BoolProperty(
		name="Aggressive barriers",
		default=True,
	)

	@classmethod
	def poll( cls, context ):
		return ( context.object is not None  and
				context.object.type == 'MESH' )

	def execute( self, context ):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		selvertsAll = get_selected_vertsIdx(active_mesh)
		if len(selvertsAll) < 2:
			self.report({'ERROR'}, "No selected verts found")
			return {'CANCELLED'}
		bpy.ops.object.mode_set( mode = 'EDIT' )
		bpy.ops.mesh.select_mode(type='VERT')
		bm = bmesh.from_edit_mesh( active_mesh )
		bm.verts.ensure_lookup_table()
		bm.verts.index_update()
		bm.edges.ensure_lookup_table()
		bm.edges.index_update()
		histVertsIdx = get_bmhistory_vertsIdx(bm)
		if len(histVertsIdx) == 0:
			self.report({'ERROR'}, "No active vert found")
			return {'CANCELLED'}
		v = bm.verts[histVertsIdx[0]]
		seedVerts = [v.index]
		blockVerts = [vIdx for vIdx in selvertsAll if vIdx != v.index]
		visitedVerts = []
		okCnt = 0
		for iter in range(0, self.opt_iterations):
			seedVertsCpy = copy.copy(seedVerts)
			for vIdx in seedVertsCpy:
				if (vIdx in blockVerts) or (vIdx in visitedVerts):
					continue
				v = bm.verts[vIdx]
				v.select = True
				visitedVerts.append(vIdx)
				sideVerts = []
				sideVertsEdges = [e.other_vert(v) for e in v.link_edges]
				if self.opt_fillAcrossFaces:
					for f in v.link_faces:
						for v2 in f.verts:
							if v2.index != v.index and v2.index not in sideVerts:
								sideVerts.append(v2)
				else:
					sideVerts = sideVertsEdges
				for v2 in sideVerts:
					if v2.index in visitedVerts:
						continue
					if v2.index in blockVerts:
						if self.opt_aggressiveStop and v2 in sideVertsEdges:
							# blocking all neared to this one
							# only for "real edges" verts!
							for e2 in v2.link_edges:
								v2a = e2.other_vert(v2)
								if v2a.index not in visitedVerts:
									if v2a.index not in blockVerts:
										blockVerts.append(v2a.index)
						continue
					okCnt = okCnt+1
					if v2.index not in seedVerts:
						seedVerts.append(v2.index)
		okCnt = okCnt+1
		bmesh.update_edit_mesh(active_mesh)
		self.report({'INFO'}, "Verts selected: "+str(okCnt))
		return {'FINISHED'}

class wplverts_pinsnap(bpy.types.Operator):
	bl_idname = "mesh.wplverts_pinsnap"
	bl_label = "Pin mesh state"
	bl_options = {'REGISTER', 'UNDO'}

	opt_pinId = StringProperty(
		name		= "Pin ID",
		default	 	= "fastpin1"
	)

	@classmethod
	def poll(self, context):
		p = context.object and context.object.data and context.object.type == 'MESH'
		return p

	def execute(self, context):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		select_and_change_mode(active_obj, 'EDIT')
		bpy.ops.mesh.select_mode(type='VERT')
		bm = bmesh.from_edit_mesh(active_mesh)
		if setBmPinmapFastIdx(active_obj, bm, self.opt_pinId) == 0:
			self.report({'ERROR'}, "Can`t create pinmap")
			return {'CANCELLED'}
		self.report({'INFO'}, "Mesh state remembered")
		return {'FINISHED'}

class wplverts_pinrestore(bpy.types.Operator):
	bl_idname = "mesh.wplverts_pinrestore"
	bl_label = "Restore selected"
	bl_options = {'REGISTER', 'UNDO'}

	opt_mode = EnumProperty(
		items = [
			('DIRECT', "As Is", "", 1),
			('CAMERA', "Camera view", "", 2)
		],
		name="Mode",
		default='DIRECT',
	)

	opt_influence = FloatProperty(
			name="Influence",
			min=-10.0, max=10.0,
			default=1.0,
	)

	opt_pinId = StringProperty(
		name		= "Pin ID",
		default	 	= "fastpin1"
	)

	@classmethod
	def poll(self, context):
		p = context.object and context.object.data and context.object.type == 'MESH'
		return p

	def execute(self, context):
		active_obj = context.scene.objects.active
		if active_obj is None or active_obj.data is None:
			self.report({'ERROR'}, "No active object")
			return {'CANCELLED'}
		camObj = context.scene.objects.get(kWPLEdgesMainCam)
		if camObj is None:
			self.report({'ERROR'}, "Camera not found: "+kWPLEdgesMainCam)
			return {'CANCELLED'}
		camera_gCo = camObj.matrix_world.to_translation()
		matrix_world_inv = active_obj.matrix_world.inverted()
		camera_lCo = matrix_world_inv * camera_gCo
		camera_gOrtho = False
		if camObj.data.type == 'ORTHO':
			camera_gOrtho = True
		active_mesh = active_obj.data
		select_and_change_mode(active_obj, 'EDIT')
		bpy.ops.mesh.select_mode(type='VERT')
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.verts.index_update()
		bm.faces.ensure_lookup_table()
		selverts = [v.index for v in bm.verts if v.select]
		if len(selverts) == 0:
			self.report({'ERROR'}, "No moved/selected verts found")
			return {'CANCELLED'}
		verts_snap_map, faces_snap_map = getBmPinmapFastIdx(active_obj, bm, self.opt_pinId)
		if verts_snap_map is None:
			self.report({'ERROR'}, "Mesh not pinned")
			return {'CANCELLED'}
		for vIdx in selverts:
			s_v = bm.verts[vIdx]
			s_v_co_init = verts_snap_map[vIdx]["co"]
			if self.opt_mode == 'CAMERA':
				incoming = s_v_co_init-camera_lCo
				intrRes = mathutils.geometry.intersect_point_line(s_v.co, camera_lCo, camera_lCo+10.0*incoming)
				s_v_co_init = intrRes[0]
			s_v.co = s_v.co.lerp(s_v_co_init,self.opt_influence)
		bm.normal_update()
		bmesh.update_edit_mesh(active_mesh, True)
		return {'FINISHED'}

class wplverts_pinpropagt(bpy.types.Operator):
	bl_idname = "mesh.wplverts_pinpropagt"
	bl_label = "Smooth around"
	bl_options = {'REGISTER', 'UNDO'}

	opt_mode = EnumProperty(
		items = [
			('KEEPACTIV', "Active selection", "", 1),
			('ENFORPINS', "Reset initial", "", 2)
		],
		name="Movement source",
		default='KEEPACTIV',
	)

	opt_influence = FloatProperty(
			name="Influence",
			min=-100, max=100,
			default=1.0,
	)
	opt_smoothLoops = IntProperty(
			name="Smoothing loops",
			min=0, max=100,
			default=5,
	)
	opt_smoothPow = FloatProperty(
			name="Smoothing pow",
			min=0.001, max=10,
			default=1.0,
	)

	opt_pinId = StringProperty(
		name		= "Pin ID",
		default	 	= "fastpin1"
	)

	@classmethod
	def poll(self, context):
		p = context.object and context.object.data and context.object.type == 'MESH'
		return p

	def execute(self, context):
		active_obj = context.scene.objects.active
		if active_obj is None or active_obj.data is None:
			self.report({'ERROR'}, "No active object")
			return {'CANCELLED'}
		active_mesh = active_obj.data
		selverts = get_selected_vertsIdx(active_mesh)
		select_and_change_mode(active_obj, 'EDIT')

		matrix_world = active_obj.matrix_world
		matrix_world_inv = active_obj.matrix_world.inverted()
		matrix_world_nrml = matrix_world_inv.transposed().to_3x3()
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		verts_shifts = {}
		verts_snap_map, faces_snap_map = getBmPinmapFastIdx(active_obj, bm, self.opt_pinId)
		if verts_snap_map is None:
			self.report({'ERROR'}, "Mesh not pinned")
			return {'CANCELLED'}
		useCurrentVposAsRef = False
		if self.opt_mode == 'ENFORPINS':
			selverts = []
			useCurrentVposAsRef = True
			# resetting initial selection
			for v in bm.verts:
				if verts_snap_map[v.index]["se"] > 0:
					selverts.append(v.index)
					v_co2 = v.co.lerp(verts_snap_map[v.index]["co"], self.opt_influence)
					verts_shifts[v.index] = Vector(v_co2 - v.co)
					v.co = v_co2
		if len(selverts) == 0:
			selverts = []
			for v in bm.verts:
				if verts_snap_map[v.index] is not None:
					if (v.co-verts_snap_map[v.index]["co"]).length > kWPLRaycastEpsilon:
						# vert moved
						selverts.append(v.index)
		if len(selverts) == 0:
			self.report({'ERROR'}, "No moved/selected verts found")
			return {'CANCELLED'}
		(propagationSteps, vertsWeight, allWalkedVerts, vertsFromIdx) = getVertsPropagations_v02(bm, self.opt_smoothLoops, selverts)
		for v_idx in allWalkedVerts:
			if (v_idx not in verts_shifts) and (v_idx in verts_snap_map):
				v = bm.verts[v_idx]
				verts_shifts[v_idx] = Vector(v.co - verts_snap_map[v_idx]["co"])
		new_positions = {}
		for stage_verts in propagationSteps:
			for vIdx in stage_verts:
				if vIdx not in verts_snap_map:
					continue
				avg_shift = mathutils.Vector((0,0,0))
				avg_count = 0.0
				from_vIdxes = vertsFromIdx[vIdx]
				for froms_idx in from_vIdxes:
					avg_shift = avg_shift + verts_shifts[froms_idx]
					avg_count = avg_count + 1.0
				#print("Vert avg shift", vIdx, avg_shift, avg_count, from_vIdxes)
				if avg_count>0:
					s_shift = mathutils.Vector(avg_shift)/avg_count
					verts_shifts[vIdx] = s_shift
					if useCurrentVposAsRef:
						s_v_co = bm.verts[vIdx].co
					else:
						s_v_co = verts_snap_map[vIdx]["co"]
					total_shift = s_shift
					vertWeight = 1.0
					if self.opt_smoothPow > 0.0:
						if vIdx in vertsWeight and abs(vertsWeight[vIdx])>0.0:
							vertWeight = pow(vertsWeight[vIdx], self.opt_smoothPow)
						else:
							print("- opt_smoothPow: vert not found", vIdx, len(vertsWeight))
					total_shift = total_shift*vertWeight*self.opt_influence
					s_v_co2 = s_v_co+total_shift
					new_positions[vIdx] = s_v_co2
		# updating positions as post-step
		for s_idx in new_positions:
			if self.opt_mode == 'KEEPACTIV' and s_idx in selverts:
				continue
			s_v = bm.verts[s_idx]
			s_v.co = new_positions[s_idx]
		bm.normal_update()
		bmesh.update_edit_mesh(active_mesh, True)
		self.report({'INFO'}, "Smoothed "+str(len(new_positions))+" verts")
		return {'FINISHED'}

class wplverts_getori_coll(bpy.types.Operator):
	bl_idname = "mesh.wplverts_getori_coll"
	bl_label = "Grab orientation from colliders"
	bl_options = {'REGISTER', 'UNDO'}

	opt_pivot2cursor = BoolProperty(
		name="Change pivot to cursor",
		default=True,
	)
	@classmethod
	def poll(cls, context):
		return context.active_object is not None

	def execute(self, context):
		bpy.ops.view3d.snap_cursor_to_active()
		if "wplverts_getori" not in WPL_G.store:
			WPL_G.store["wplverts_getori"] = ""
		cur_co = get_active_context_cursor(context)
		cur_no = None
		bvh2collides = get_sceneColldersBVH(None,False)
		if len(bvh2collides) == 0:
			self.report({'ERROR'}, "Colliders not found: Need objects with collision modifier")
			return {'CANCELLED'}
		dist = 999
		for bvh_collide in bvh2collides:
			location, normal, index, distance = bvh_collide.find_nearest(cur_co, 999)
			if location is not None and distance < dist:
				# moving 3D cursor to position
				print("Collider pos", location, normal)
				dist = distance
				cur_no = normal
				cur_co = location
		if cur_no is not None:
			bpy.context.scene.cursor_location = cur_co
			bpy.ops.transform.create_orientation(name=kWPLTempOrien, use=True, overwrite=True)
			orientation = bpy.context.scene.orientations.get(kWPLTempOrien)
			nrm_rot = cur_no.rotation_difference(mathutils.Vector((0,0,1)))
			co_pos = Matrix.Translation(cur_co).to_3x3()
			co_pos.rotate(nrm_rot.to_matrix())
			orientation.matrix = co_pos
		bpy.context.space_data.show_manipulator = True
		if self.opt_pivot2cursor:
			bpy.context.space_data.pivot_point = 'CURSOR'
		else:
			bpy.context.space_data.pivot_point = 'MEDIAN_POINT'
		WPL_G.store["wplverts_getori"] = "COLLD"
		return {'FINISHED'}

class wplverts_getori_bone(bpy.types.Operator):
	bl_idname = "mesh.wplverts_getori_bone"
	bl_label = "Grab orientation from bone"
	bl_options = {'REGISTER', 'UNDO'}

	opt_bones2useIni = StringProperty(
		name="Bones",
		default = ""
	)
	opt_pivot2cursor = BoolProperty(
		name="Change pivot to cursor",
		default=True,
	)
	@classmethod
	def poll(cls, context):
		return context.active_object is not None

	def execute(self, context):
		active_obj = context.scene.objects.active
		opt_bones2use = self.opt_bones2useIni
		if len(opt_bones2use) == 0:
			opt_bones2use = select_by_arm(active_obj, kArmAlignBns_MB, kArmAlignBns_MLOW, "")
		armatr = get_related_arma(active_obj)
		if armatr is None:
			self.report({'ERROR'}, "Need related Armature")
			return {'CANCELLED'}
		if active_obj is None or active_obj.type != 'MESH':
			return {'FINISHED'}
		active_mesh = active_obj.data
		bpy.ops.object.mode_set( mode = 'EDIT' )
		bpy.ops.mesh.select_mode(type='VERT')
		bm = bmesh.from_edit_mesh( active_mesh )
		bm.verts.ensure_lookup_table()
		bm.verts.index_update()
		bm.edges.ensure_lookup_table()
		bm.edges.index_update()
		histVertsIdx = get_bmhistory_vertsIdx(bm)
		if len(histVertsIdx) == 0:
			self.report({'ERROR'}, "No active vert found")
			return {'CANCELLED'}
		active_v = bm.verts[histVertsIdx[0]]
		#bpy.ops.view3d.snap_cursor_to_active()
		if "wplverts_getori" not in WPL_G.store:
			WPL_G.store["wplverts_getori"] = ""
		cur_co = None
		cur_no = None
		cur_tan = None
		# looking for bone with highest weight from allowed
		bnpref = [x.strip() for x in opt_bones2use.split(",")]
		refbone_maxw = 0.0
		refbone_maxn = None
		refbone_remap = {}
		for pref_item in bnpref:
			pref = pref_item
			pref2 = "*"
			if "+" in pref:
				pref_item_sl = pref_item.split("+")
				pref = pref_item_sl[0]
				pref2 = pref_item_sl[1]
				refbone_remap[pref2] = pref
			for vg in active_obj.vertex_groups:
				if (pref in vg.name) or (pref2 in vg.name):
					allVgVertsCo, allVgVertsIdx, allVgVertsW = get_vertgroup_verts(active_obj, vg, 0.01)
					if active_v.index in allVgVertsIdx:
						v_at = allVgVertsIdx.index(active_v.index) # ..find
						v_w = allVgVertsW[v_at]
						if v_w > refbone_maxw:
							print("- relbone", vg.name, v_w)
							refbone_maxw = v_w
							refbone_maxn = vg.name
		if refbone_maxn is not None:
			# getting bone line, projecting vertex
			if refbone_maxn in refbone_remap:
				refbone_maxn = refbone_remap[refbone_maxn]
			print("- final:", refbone_maxn)
			pbone = armatr.pose.bones[refbone_maxn]
			pbone.rotation_mode = 'QUATERNION'
			headInBoneSpace = Vector( (0, 0, 0) )
			tailInBoneSpace = Vector( (0, pbone.length, 0) )
			phead = active_obj.matrix_world.inverted() * (armatr.matrix_world * (pbone.matrix*headInBoneSpace)) # pbone.head
			ptail = active_obj.matrix_world.inverted() * (armatr.matrix_world * (pbone.matrix*tailInBoneSpace)) # pbone.tail
			intrRes = mathutils.geometry.intersect_point_line(active_v.co, phead, ptail)
			proj_co = intrRes[0]
			cur_co = active_obj.matrix_world * proj_co
			cur_no = (active_obj.matrix_world * (active_v.co-proj_co)).normalized()
			cur_tan = (active_obj.matrix_world * (ptail-phead)).normalized()
			# print(" -> ", active_v.co, (active_v.co-proj_co), (ptail-phead), cur_no.dot(cur_tan))
			if cur_no.dot(cur_tan) > 0.99:
				cur_tan = cur_no.cross(Vector((0,1,0)))
		if cur_no is not None and cur_co is not None:
			select_and_change_mode(active_obj,"EDIT")
			bpy.context.space_data.cursor_location = cur_co
			bpy.ops.transform.create_orientation(name=kWPLTempOrien, use=True, overwrite=True)
			orientation = bpy.context.scene.orientations.get(kWPLTempOrien)
			# rotation matrix from 2 vectors
			aRot = Matrix.Identity(3)
			aRot[0] = cur_tan.normalized()               # x
			aRot[1] = cur_no.normalized().cross(cur_tan).normalized() # y
			aRot[2] = cur_no.normalized()               # z
			aRot = aRot.transposed()
			aRotM = aRot.to_4x4()
			# z = Quaternion()
			# aRot = z.rotation_difference(cur_no.to_track_quat())
			# aRotM = aRot.to_matrix().to_4x4()
			aLocM = mathutils.Matrix.Translation(cur_co)
			combined = aLocM * aRotM
			orientation.matrix = combined.to_3x3()

		bpy.context.space_data.show_manipulator = True
		if self.opt_pivot2cursor:
			bpy.context.space_data.pivot_point = 'CURSOR'
		else:
			bpy.context.space_data.pivot_point = 'MEDIAN_POINT'
		WPL_G.store["wplverts_getori"] = "BONE"
		select_and_change_mode(active_obj,"EDIT")
		return {'FINISHED'}


class wplverts_getori(bpy.types.Operator):
	bl_idname = "mesh.wplverts_getori"
	bl_label = "Grab orientation"
	bl_options = {'REGISTER', 'UNDO'}

	opt_mode = EnumProperty(
		items = [
			('ACTIVE', "Active elem", "", 1),
			('CAMERA',  "Camera", "", 2),
			('UNGRAB', "Ungrab", "", 3)
		],
		name="Orientation mode",
		default='ACTIVE',
	)
	opt_pivot2cursor = BoolProperty(
			name="Change pivot to cursor",
			default=True,
	)

	@classmethod
	def poll(cls, context):
		return context.active_object is not None

	def execute(self, context):
		bpy.ops.view3d.snap_cursor_to_active()
		camObj = context.scene.objects.get(kWPLEdgesMainCam)
		if camObj is None:
			self.report({'ERROR'}, "Camera not found: "+kWPLEdgesMainCam)
			return {'CANCELLED'}
		if "wplverts_getori" not in WPL_G.store:
			WPL_G.store["wplverts_getori"] = ""
		cur_co = get_active_context_cursor(context)
		cur_no = None
		cur_co_key = self.opt_mode #coToKey(cur_co)
		if self.opt_mode == 'UNGRAB':
			WPL_G.store["wplverts_getori"] = ""
			bpy.context.space_data.transform_orientation = 'LOCAL'
			bpy.context.space_data.pivot_point = 'MEDIAN_POINT'
			return {'FINISHED'}
		if self.opt_mode == 'ACTIVE':
			bpy.ops.transform.create_orientation(name=kWPLTempOrien, use=True, overwrite=True)
		if self.opt_mode == 'CAMERA':
			bpy.ops.transform.create_orientation(name=kWPLTempOrien, use=True, overwrite=True)
			orientation = bpy.context.scene.orientations.get(kWPLTempOrien)
			aLoc, aRot, aSca = camObj.matrix_world.decompose()
			aLocM = mathutils.Matrix.Translation(cur_co)
			aRotM = aRot.to_matrix().to_4x4()
			aScaM = Matrix().Scale(aSca[0], 4, Vector((1,0,0)))
			aScaM *= Matrix().Scale(aSca[1], 4, Vector((0,1,0)))
			aScaM *= Matrix().Scale(aSca[2], 4, Vector((0,0,1)))
			combined = aLocM * aRotM * aScaM
			orientation.matrix = combined.to_3x3()
		bpy.context.space_data.show_manipulator = True
		if self.opt_pivot2cursor:
			bpy.context.space_data.pivot_point = 'CURSOR'
		else:
			bpy.context.space_data.pivot_point = 'MEDIAN_POINT'
		WPL_G.store["wplverts_getori"] = cur_co_key
		return {'FINISHED'}

class wplverts_orialign(bpy.types.Operator):
	bl_idname = "mesh.wplverts_orialign"
	bl_label = "Align to orientation"
	bl_options = {'REGISTER', 'UNDO'}

	opt_mode = EnumProperty(
		items = [
			('ORI', "Orientation", "", 1),
			('CUR', "3D Cursor", "", 2)
		],
		name="Orientation mode",
		default='ORI',
	)
	opt_moveOffset = bpy.props.FloatVectorProperty(
		name		= "Move Offset",
		size = 3,
		default	 = (0.0,0.0,0.0),
	)
	opt_influence = bpy.props.FloatProperty(
		name		= "Influence",
		default	 = 1.0,
		min		 = 0,
		max		 = 100
	)

	@classmethod
	def poll(cls, context):
		return context.active_object is not None

	def invoke(self, context, event):
		# if bpy.context.mode != 'OBJECT':
		# 	self.opt_rotOffset = (180,0,0)
		# elif bpy.context.mode == 'OBJECT':
		# 	self.opt_rotOffset = (0,0,0)
		return self.execute(context)

	def execute(self, context):
		active_obj = context.scene.objects.active
		if active_obj is None:
			return {'FINISHED'}
		matrix_world = active_obj.matrix_world
		matrix_world_inv = active_obj.matrix_world.inverted()
		matrix_world_nrml = matrix_world_inv.transposed().to_3x3()
		orient_co = get_active_context_cursor(context)
		orient_rot = None
		if self.opt_mode == 'ORI':
			orient_rot = get_active_context_orient(context)
			if orient_co is None or orient_rot is None:
				self.report({'ERROR'}, "No proper context/Invalid orientation")
				return {'FINISHED'}
		if bpy.context.mode == 'OBJECT' or active_obj.type != 'MESH':
			new_co_g = orient_co
			if orient_rot is not None:
				new_co_g = new_co_g+self.opt_moveOffset[0]*(orient_rot*Vector((1,0,0)))
				new_co_g = new_co_g+self.opt_moveOffset[1]*(orient_rot*Vector((0,1,0)))
				new_co_g = new_co_g+self.opt_moveOffset[2]*(orient_rot*Vector((0,0,1)))
			aLoc, aRot, aSca = matrix_world.decompose()
			aLocM = mathutils.Matrix.Translation(aLoc.lerp(new_co_g,self.opt_influence))
			#aRotM = aRot.to_matrix().to_4x4()
			aRotM = mathutils.Matrix.Identity(4)
			if orient_rot is not None:
				aRotM = orient_rot.to_quaternion().to_matrix().to_4x4()
			aScaM = Matrix().Scale(aSca[0], 4, Vector((1,0,0)))
			aScaM *= Matrix().Scale(aSca[1], 4, Vector((0,1,0)))
			aScaM *= Matrix().Scale(aSca[2], 4, Vector((0,0,1)))
			matrix_world = aLocM * aRotM * aScaM
			active_obj.matrix_world = matrix_world
			return {'FINISHED'}
		active_mesh = active_obj.data
		selvertsAll = get_selected_vertsIdx(active_mesh)
		if len(selvertsAll) == 0:
			self.report({'ERROR'}, "No selected verts found")
			return {'FINISHED'}
		# getting reference position
		select_and_change_mode(active_obj,'EDIT')
		bm = bmesh.from_edit_mesh(active_mesh)
		fltCenter = None
		fltNormal = None
		fltrefs = get_bmhistory_refCo(bm)
		if fltrefs is not None:
			fltCenter = fltrefs[0]
			fltNormal = fltrefs[1]
		else:
			fltCenter = Vector((0,0,0))
			for vIdx in selvertsAll:
				v = bm.verts[vIdx]
				fltCenter = fltCenter + v.co
			fltCenter = fltCenter/float(len(selvertsAll))
		#ori_nrm = (orient_rot * Vector((0,0,1)))
		diff_p = matrix_world_inv*orient_co-fltCenter
		for vIdx in selvertsAll:
			v = bm.verts[vIdx]
			new_co = v.co
			new_co = new_co+diff_p
			if orient_rot is not None:
				new_co = new_co+self.opt_moveOffset[0]*(orient_rot*Vector((1,0,0)))
				new_co = new_co+self.opt_moveOffset[1]*(orient_rot*Vector((0,1,0)))
				new_co = new_co+self.opt_moveOffset[2]*(orient_rot*Vector((0,0,1)))
			v.co = v.co.lerp(new_co,self.opt_influence)
		bm.normal_update()
		bmesh.update_edit_mesh(active_mesh, True)
		self.report({'INFO'}, "Done, "+str(len(selvertsAll))+" verts moved")
		return {'FINISHED'}


######### ############ ################# ############

class WPLVertTools_Panel2(bpy.types.Panel):
	bl_label = "Mesh Verts"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_category = 'WPL'

	def draw(self, context):
		layout = self.layout
		active_obj = context.scene.objects.active
		col = layout.column()
		box1 = col.box()
		if active_obj is not None:
			if "wplverts_getori" in WPL_G.store and len(WPL_G.store["wplverts_getori"]) > 0:
				box1.operator("mesh.wplverts_getori", text = "UNGRAB orientation").opt_mode='UNGRAB'
			else:
				op1 = box1.operator("mesh.wplverts_getori", text = "GRAB active")
				op1.opt_mode = 'ACTIVE'
				op1.opt_pivot2cursor = True
			op4 = box1.operator("mesh.wplverts_getori", text="GRAB 2camera")
			op4.opt_mode = 'CAMERA'
			op4.opt_pivot2cursor = False
			pro1a = box1.row()
			pro1a.operator("mesh.wplverts_getori_bone", text="2bone")
			pro1a.operator("mesh.wplverts_getori_coll", text="2collider")
			box1.operator("mesh.wplverts_orialign", text="Align to orientation").opt_mode = 'ORI'
			box1.operator("mesh.wplverts_orialign", text="Move to 3D cursor").opt_mode = 'CUR'
		if active_obj is not None and active_obj.data is not None:
			box1.separator()
			box1.operator("mesh.wplverts_savesel", text="Save selection")
			nextNumber = 1
			selGrps = []
			for vg in active_obj.vertex_groups:
				if kWPLSaveSelVGroup in vg.name:
					selGrps.append(vg.name)
			selGrps = sorted(selGrps)
			for vg_name in selGrps:
				row = box1.row()
				op1 = row.operator("mesh.wplverts_loadsel", text=vg_name)
				op1.opt_deselCurrent = True
				op1.opt_deselVg = False
				op1.opt_vgname = vg_name
				op2 = row.operator("mesh.wplverts_loadsel", text="Deselect")
				op2.opt_deselCurrent = False
				op2.opt_deselVg = True
				op2.opt_vgname = vg_name
				op3 = row.operator("mesh.wplverts_loadsel", text="Rem")
				op3.opt_vgname = "!"+vg_name
			col.separator()
			box1 = col.box()
			box1.operator("mesh.wplverts_selfill")
			opr1 = box1.row()
			opr1.operator("mesh.wplverts_chaindesel", text="Desel short").opt_inversion = False
			opr1.operator("mesh.wplverts_chaindesel", text="Desel long").opt_inversion = True
			opr2 = box1.row()
			op1 = opr2.operator("mesh.wplverts_dirdesel", text="Desel vertical")
			op1.opt_direction = (0,0,1)
			op1.opt_inversion = False
			op2 = opr2.operator("mesh.wplverts_dirdesel", text="Desel horizontal")
			op2.opt_direction = (0,0,1)
			op2.opt_inversion = True
			col.separator()
			box1 = col.box()
			opr3 = box1.row()
			opr3.operator("mesh.wplverts_pinsnap", text="S1: Pin").opt_pinId = "fastpin1"
			opr3.operator("mesh.wplverts_pinsnap", text="S2: Pin").opt_pinId = "fastpin2"
			box1.operator("mesh.wplverts_pinrestore", text="S1: Sel restore").opt_mode = 'DIRECT'
			box1.operator("mesh.wplverts_pinrestore", text="S1: Snap sel2cam").opt_mode = 'CAMERA'
			box1.separator()
			box1.operator("mesh.wplverts_pinpropagt", text="S1: Smooth selection").opt_mode = 'KEEPACTIV'
			box1.operator("mesh.wplverts_pinpropagt", text="S1: Enforce pinned").opt_mode = 'ENFORPINS'
			box1.separator()
			opr4 = box1.row()
			ss1 = opr4.operator("mesh.wplverts_pinsurfshrw", text="S1: Shrinkwrap")
			ss1.opt_shrinkwMethod = 'NEAR'
			ss1.opt_vertsType = 'ALL'
			ss1.opt_pinId = "fastpin1"
			ss2 = opr4.operator("mesh.wplverts_pinsurfshrw", text="S1: Project")
			ss2.opt_shrinkwMethod = 'CAMPROJ'
			ss2.opt_vertsType = 'ALL'
			ss2.opt_pinId = "fastpin1"
			box1.separator()
			opr3 = box1.row()
			ss1 = opr3.operator("mesh.wplverts_pinsurfshrw", text="S2: Shrinkwrap")
			ss1.opt_shrinkwMethod = 'NEAR'
			ss1.opt_vertsType = 'ALL'
			ss1.opt_pinId = "fastpin2"
			ss2 = opr3.operator("mesh.wplverts_pinsurfshrw", text="S2: Project")
			ss2.opt_shrinkwMethod = 'CAMPROJ'
			ss2.opt_vertsType = 'ALL'
			ss2.opt_pinId = "fastpin2"
			#ss2 = prow2.operator("mesh.wplverts_pinsurfshrw", text="Pull under")
			#ss1.opt_shrinkwMethod = 'NEAR'
			#ss2.opt_vertsType = 'ABOVE'
			#ss2.opt_prefDistance = -0.001
			# box1.separator()
			# box1.operator("mesh.wplverts_bubble_simple", text="Bubble verts (Same mesh, Normals)").opt_flatnMeth = 'MESH_NORMALS'
			# box1.operator("mesh.wplverts_bubble_simple", text="Bubble verts (Same mesh, Camera)").opt_flatnMeth = 'MESH_CAMERA'
			# box1.operator("mesh.wplverts_bubble_simple", text="Bubble verts (Scene, Normals)").opt_flatnMeth = 'SCENE_NORMALS'
			# box1.operator("mesh.wplverts_bubble_simple", text="Bubble verts (Scene, Camera)").opt_flatnMeth = 'SCENE_CAMERA'
			# box1.operator("mesh.wplverts_bubble_colld", text="Shrinkwrap to Colliders")

def register():
	bpy.utils.register_module(__name__)

def unregister():
	bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
	register()
