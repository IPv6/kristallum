import bpy
from bpy.props import *
import bmesh
import math
import mathutils
import random
import time
import copy
import numpy as np

from mathutils import Vector, Matrix, Euler
from mathutils.bvhtree import BVHTree
from bpy_extras import view3d_utils
from bpy_extras.object_utils import world_to_camera_view

bl_info = {
	"name": "Mesh Sculpt Tools",
	"author": "IPv6",
	"version": (1, 4, 6),
	"blender": (2, 7, 9),
	"location": "View3D > T-panel > WPL",
	"description" : "",
	"warning"	 : "",
	"wiki_url"	: "",
	"tracker_url" : "",
	"category"	: "WPL"
	}

kWPLRaycastEpsilon = 0.000001
kWPLRaycastEpsilonCCL = 0.0001
kWPLConvexPrecision = 10000.0

kArmMeshPartHide_Body_MB = 'clavicle,spine,pelvis,breast,!upperarm_L:0.12,!upperarm_R:0.12,!thigh_twist_L:0.5,!thigh_twist_R:0.5,!head:0.5'
kArmMeshPartHide_ArmL_MB = 'lowerarm_L,upperarm_L,!clavicle:0.12'
kArmMeshPartHide_ArmR_MB = 'lowerarm_R,upperarm_R,!clavicle:0.12'
kArmMeshPartHide_LegL_MB = 'thigh_L,calf_L,calf_twist_L'
kArmMeshPartHide_LegR_MB = 'thigh_R,calf_R,calf_twist_R'
kArmMeshPartHide_Hands_MB = 'hand,pinky,ring,middle,index,thumb,!lowerarm_L:0.005,!lowerarm_R:0.005'

kArmMeshPartHide_Body_MLOW = 'bn_shoulder,bn_spine,bn_pelvis,bn_breast,!bn_thigh:0.5,!bn_upperarm:0.5'
kArmMeshPartHide_ArmL_MLOW = 'bn_upperarm01.L:0.6,bn_upperarm02.L:0.6,bn_forearm01.L:0.6,bn_forearm02.L:0.6,!bn_shoulder.L:0.1,!bn_spine:0.1'
kArmMeshPartHide_ArmR_MLOW = 'bn_upperarm01.R:0.6,bn_upperarm02.R:0.6,bn_forearm01.R:0.6,bn_forearm02.R:0.6,!bn_shoulder.R:0.1,!bn_spine:0.1'
kArmMeshPartHide_LegL_MLOW = 'bn_thigh01.L,bn_thigh02.L,bn_shin01.L,bn_shin02.L,!bn_spine:0.2,!bn_pelvis:0.3'
kArmMeshPartHide_LegR_MLOW = 'bn_thigh01.R,bn_thigh02.R,bn_shin01.R,bn_shin02.R,!bn_spine:0.2,!bn_pelvis:0.3'
kArmMeshPartHide_Hands_MLOW = 'hand,pinky,ring,middle,index,thumb,!bn_forearm:0.5'

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

# def get_bmverts_byCo(active_bmesh,co,dist,onlySelected):
	# active_bmesh.verts.ensure_lookup_table()
	# active_bmesh.verts.index_update()
	# res = []
	# for v in active_bmesh.verts:
		# if onlySelected and v.select == False:
			# continue
		# if (v.co-co).length < dist:
			# res.append(v)
	# return res

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
	active_bmesh.edges.ensure_lookup_table()
	active_bmesh.edges.index_update()
	histVertsIdx = []
	histFacesIdx = []
	histEdgesIdx = []
	if bpy.context.tool_settings.mesh_select_mode[2] == True: # 'FACE' selection
		histFacesIdx = get_bmhistory_faceIdx(active_bmesh)
	elif bpy.context.tool_settings.mesh_select_mode[1] == True: # 'EDGE' selection
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

def getBmVertGeodesicDistmap_v05(bme, step_vIdx, maxloops, maxdist, ignoreEdges, ignoreHidden, limitWalk2verts):
	# counting propagations
	vertDistMap = {}
	vertOriginMap = {}
	vertStepMap = {}
	for vIdx in step_vIdx:
		vertOriginMap[vIdx] = vIdx
	for curStep in range(maxloops):
		for vIdx in step_vIdx:
			if vIdx not in vertStepMap:
				vertStepMap[vIdx] = curStep+1
			if vIdx not in vertDistMap:
				vertDistMap[vIdx] = 0.0
		nextStepIdx = {}
		for vIdx in step_vIdx:
			v = bme.verts[vIdx]
			nearVers = []
			if ignoreEdges:
				# across faces
				for f in v.link_faces:
					for fv in f.verts:
						nearVers.append(fv)
			else:
				# across edges
				for e in v.link_edges:
					nearVers.append(e.other_vert(v))
			for fv in nearVers:
				if ignoreHidden == True and fv.hide != 0:
					continue
				if (limitWalk2verts is not None) and (fv.index not in limitWalk2verts):
					continue
				if fv.index not in vertStepMap:
					fv_dist = vertDistMap[vIdx]+(fv.co-v.co).length
					if fv.index not in vertDistMap:
						vertDistMap[fv.index] = fv_dist
						vertOriginMap[fv.index] = vertOriginMap[vIdx]
						if (maxdist is None) or (fv_dist <= maxdist):
							nextStepIdx[fv.index] = vIdx
					elif vertDistMap[fv.index] > fv_dist:
						vertDistMap[fv.index] = fv_dist
						vertOriginMap[fv.index] = vertOriginMap[vIdx]
						if (maxdist is None) or (fv_dist <= maxdist):
							nextStepIdx[fv.index] = vIdx
		# print("- step",curStep+1,len(step_vIdx),len(nextStepIdx))
		step_vIdx = []
		for vIdxNext in nextStepIdx:
			step_vIdx.append(vIdxNext)
		if len(step_vIdx) == 0:
			#print("- walk stopped at", curStep)
			break
	return vertDistMap, vertOriginMap, vertStepMap

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

def getBmVertsKdtree(obj, bm, ignoreIdx):
	research_tree = mathutils.kdtree.KDTree(len(bm.verts))
	for vert in bm.verts:
		if ignoreIdx is not None and vert.index in ignoreIdx:
			continue
		if obj is not None:
			research_tree.insert(obj.matrix_world*vert.co, vert.index)
		else:
			research_tree.insert(vert.co, vert.index)
	research_tree.balance()
	return research_tree
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

def coToKey(co_vec):
	key = str(int(co_vec[0]*kWPLConvexPrecision))+"_"+str(int(co_vec[1]*kWPLConvexPrecision))+"_"+str(int(co_vec[2]*kWPLConvexPrecision))
	return key

def view_getActiveRegion():
	reg3d = bpy.context.space_data.region_3d
	if reg3d is not None:
		return reg3d
	for area in bpy.context.screen.areas:
		if area.type == 'VIEW_3D':
			return area.spaces.active.region_3d

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

def bm_selectVertEdgesFaces(bm, verts2sel):
	bm.verts.ensure_lookup_table()
	bm.verts.index_update()
	bm.edges.ensure_lookup_table()
	bm.edges.index_update()
	bm.faces.ensure_lookup_table()
	bm.faces.index_update()
	for vIdx in verts2sel:
		v = bm.verts[vIdx]
		v.select = True
	for edge in bm.edges:
		if edge.verts[0].select and edge.verts[1].select:
			edge.select = True
	for face in bm.faces:
		e_sels = 0
		for e in face.edges:
			if e.select:
				e_sels = e_sels+1
		if e_sels == len(face.edges):
			face.select = True
	return
########### ############ ########### ############ ########### ############ ########### ############
########### ############ ########### ############ ########### ############ ########### ############
class wplsculpt_egeoout(bpy.types.Operator):
	bl_idname = "mesh.wplsculpt_egeoout"
	bl_label = "Geodesic outline"
	bl_options = {'REGISTER', 'UNDO'}

	opt_geoDistAbs = FloatProperty(
		name		= "Absolute Distance",
		default	 = 0.0,
		min		 = 0,
		max		 = 999
	)
	opt_geoDistRel = FloatProperty(
		name		= "Relative Distance (avg edge len)",
		subtype		= 'PERCENTAGE',
		default	 = 150,
		min		 = 0,
		max		 = 999
	)
	opt_postSelect = bpy.props.EnumProperty(
		name="Post selection", default="BOUNDS",
		items=(("BOUNDS", "Bounds", ""), ("ALL", "All", ""))
		)

	@classmethod
	def poll( cls, context ):
		return ( context.object is not None  and
				context.object.type == 'MESH' )

	def execute( self, context ):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data

		vertsIdx = get_selected_vertsIdx(active_mesh)
		if len(vertsIdx)<1:
			self.report({'ERROR'}, "No selected verts found, select some verts first")
			return {'FINISHED'} # or all changes get lost!!!

		bpy.ops.object.mode_set(mode='EDIT')
		bpy.ops.mesh.select_mode(type='VERT')
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.verts.index_update()
		bm.edges.ensure_lookup_table()
		bm.edges.index_update()
		bm.faces.ensure_lookup_table()
		bm.faces.index_update()
		avglenSum = 0.0
		avglenCnt = 0.0
		for vIdx in vertsIdx:
			v = bm.verts[vIdx]
			for e in v.link_edges:
				avglenSum = avglenSum+e.calc_length()
				avglenCnt = avglenCnt+1.0
		outlineDist = self.opt_geoDistAbs
		if avglenCnt>0 and self.opt_geoDistRel>0:
			outlineDist = outlineDist+self.opt_geoDistRel*0.01*avglenSum/avglenCnt
		vertDistMap, _, _ = getBmVertGeodesicDistmap_v05(bm, vertsIdx, 100, outlineDist, True, True, None)
		vertIn =[]
		for vIdx in vertDistMap:
			v = bm.verts[vIdx]
			v.select = False
			vertIn.append(v)
		joinvertsRaw = []
		joinedgesRaw = []
		for v in vertIn:
			edges = [e for e in v.link_edges]
			for e in edges:
				vo = e.other_vert(v)
				#if vo.index in vertUsed:
				#	continue
				if vo.index in vertDistMap:
					if abs(vertDistMap[v.index]-outlineDist)<0.00001:
						if v.index not in joinvertsRaw:
							joinvertsRaw.append(v.index)
					elif abs(vertDistMap[vo.index]-outlineDist)<0.00001:
						if vo.index not in joinvertsRaw:
							joinvertsRaw.append(vo.index)
					elif vertDistMap[v.index] > outlineDist and vertDistMap[vo.index] < outlineDist:
						prc = (outlineDist-vertDistMap[vo.index])/(vertDistMap[v.index]-vertDistMap[vo.index])
						newv_co = vo.co+prc*(v.co-vo.co)
						joinedgesRaw.append((e,newv_co))
			if self.opt_postSelect == 'ALL':
				if vertDistMap[v.index] < outlineDist:
					v.select = True
		for bsc in joinedgesRaw:
			e = bsc[0]
			newv_co = bsc[1]
			geom = bmesh.ops.bisect_edges(bm, edges = [e], cuts = 1)
			new_bmverts = [ele for ele in geom['geom_split'] if isinstance(ele, bmesh.types.BMVert)]
			if len(new_bmverts) == 1:
				newv = new_bmverts[0]
				newv.co = newv_co
				if newv.index not in joinvertsRaw:
					joinvertsRaw.append(newv.index)
		if len(joinvertsRaw) >= 2:
			# resorting by distance and same-faceness
			joinvertsRaw = sortBmVertsByConnection_v01(bm, joinvertsRaw, False)
			joinvertsSrt = []
			for vIdx in joinvertsRaw:
				v = bm.verts[vIdx]
				v.select = True
				joinvertsSrt.append(v)
			bmesh.ops.connect_verts(bm, verts = joinvertsSrt, faces_exclude = [], check_degenerate = True)
		bm.normal_update()
		bmesh.update_edit_mesh(active_mesh, True)
		self.report({'INFO'}, "Done, "+str(len(joinvertsRaw))+" verts added")
		return {'FINISHED'}

class wplsculpt_ebisect(bpy.types.Operator):
	bl_idname = "mesh.wplsculpt_ebisect"
	bl_label = "Bisect with edge"
	bl_options = {'REGISTER', 'UNDO'}


	opt_ovlNormalDir = FloatVectorProperty(
		name	 = "Plane normal override",
		size	 = 3,
		min=-1.0, max=1.0,
		default	 = (0.0,0.0,0.0)
	)

	@classmethod
	def poll( cls, context ):
		return ( context.object is not None  and
				context.object.type == 'MESH' )
	def execute( self, context ):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		facesIdx = get_selected_facesIdx(active_mesh)
		edgesIdx = get_selected_edgesIdx(active_mesh)
		bpy.ops.object.mode_set( mode = 'EDIT' )
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.edges.ensure_lookup_table()
		bm.edges.index_update()
		histEdgesIdx = get_bmhistory_edgesIdx(bm)
		if len(histEdgesIdx) == 0:
			self.report({'ERROR'}, "No active edge found, select edge first")
			return {'CANCELLED'}
		bisectEdgeMain = bm.edges[histEdgesIdx[0]]
		oporV = bisectEdgeMain.verts[0]
		secdV = bisectEdgeMain.verts[1]
		if len(facesIdx) == 0:
			bpy.ops.mesh.select_mode(type="FACE")
			for f in oporV.link_faces:
				f.select = True
			for f in secdV.link_faces:
				f.select = True
		bm.faces.ensure_lookup_table()
		bm.faces.index_update()
		bisectFaces = [f for f in bm.faces if f.select]
		if len(bisectFaces) == 0:
			self.report({'ERROR'}, "No faces found, select faces first")
			return {'CANCELLED'}
		bisectEdges = []
		bisectEdges.append((oporV,secdV))
		# adding edges with verts without selected faces
		for eIdx in edgesIdx:
			e = bm.edges[eIdx]
			isPossibleBse = True
			for bse in bisectEdges:
				if bse[0] == e.verts[0] or bse[0] == e.verts[1] or bse[1] == e.verts[0] or bse[1] == e.verts[1]:
					isPossibleBse = False
					break
			vfcsc = 0
			for f in e.verts[0].link_faces:
				if f.select:
					vfcsc = vfcsc+1
					break
			for f in e.verts[1].link_faces:
				if f.select:
					vfcsc = vfcsc+1
					break
			if vfcsc > 1 or isPossibleBse == False:
				continue
			bisectEdges.append((e.verts[0],e.verts[1]))
		for bse in bisectEdges:
			oporV = bse[0]
			secdV = bse[1]
			reperNrm = oporV.normal
			if abs(self.opt_ovlNormalDir[0])+abs(self.opt_ovlNormalDir[1])+abs(self.opt_ovlNormalDir[2])>0.00001:
				reperNrm = Vector((self.opt_ovlNormalDir[0],self.opt_ovlNormalDir[1],self.opt_ovlNormalDir[2])).normalized()
			bisectNrm = (oporV.co-secdV.co).normalized().cross(reperNrm)
			geom_in_v = []
			geom_in_e = []
			geom_in_f = []
			for f in bisectFaces:
				geom_in_v.extend(f.verts)
				geom_in_e.extend(f.edges)
				geom_in_f.append(f)
			print("Bisecting",len(geom_in_v),len(geom_in_e),len(geom_in_f))
			#geom_in = bm.verts[:]+bm.edges[:]+bm.faces[:]
			geom_in = set(geom_in_v[:]+geom_in_e[:]+geom_in_f[:])
			res = bmesh.ops.bisect_plane(bm, geom=list(geom_in), dist=kWPLRaycastEpsilonCCL, plane_co=oporV.co, plane_no=bisectNrm, use_snap_center=False, clear_outer=False, clear_inner=False)
			bpy.ops.mesh.select_mode(type="FACE")
			for elem in res["geom"]:
				if isinstance(elem, bmesh.types.BMFace):
					elem.select = True
					if elem not in bisectFaces:
						bisectFaces.append(elem)
		bm.normal_update()
		bm.faces.ensure_lookup_table()
		bm.faces.index_update()
		bm.verts.ensure_lookup_table()
		bm.verts.index_update()
		bm.edges.ensure_lookup_table()
		bm.edges.index_update()
		bmesh.update_edit_mesh(active_mesh, True)
		bpy.ops.mesh.select_mode(type="EDGE")
		return {'FINISHED'}

class wplsculpt_edge_verts(bpy.types.Operator):
	bl_idname = "mesh.wplsculpt_edge_verts"
	bl_label = "Distribute verts"
	bl_options = {'REGISTER', 'UNDO'}

	opt_influence = FloatProperty(
		name		= "Influence",
		default	 = 1.0,
		min		 = 0,
		max		 = 1
	)
	opt_lerpLinear = FloatProperty(
		name		= "Straighten",
		default	 = 0.0,
		min		 = 0,
		max		 = 1
	)

	opt_smoothArn = FloatVectorProperty(
		name     = "Smooth around",
		size = 2,
		default	 = (0.0, 1.0),
	)
	opt_enforceVCnt = IntProperty(
		name     = "Minimum vert count",
		default	 = 0,
		min		 = -1,
		max		 = 1000
	)
	opt_flowDir = FloatVectorProperty(
		name	 = "Preferred direction",
		size	 = 3,
		min=-1.0, max=1.0,
		default	 = (0.0,0.0,-1.0)
	)
	
	@classmethod
	def poll( cls, context ):
		return ( context.object is not None  and
				context.object.type == 'MESH' )


	def resetOpts(self):
		self.opt_influence = 1
		self.opt_lerpLinear = 0
		self.opt_enforceVCnt = 0
		self.opt_smoothArn = (0.0, 1.0)
		return
		
	def execute( self, context ):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data

		vertsIdx = get_selected_vertsIdx(active_mesh)
		edgesIdx = get_selected_edgesIdx(active_mesh)
		if len(edgesIdx)<1:
			self.resetOpts()
			bpy.ops.object.mode_set( mode = 'EDIT' )
			self.report({'ERROR'}, "No selected edges found, select some edges first")
			return {'FINISHED'} # or all changes get lost!!!

		bpy.ops.object.mode_set( mode = 'EDIT' )
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.verts.index_update()
		bm.edges.ensure_lookup_table()
		bm.edges.index_update()
		(strands_points,strands_radius,strands_vidx) = getBmEdgesAsStrands_v04(bm, vertsIdx, edgesIdx, self.opt_flowDir, None)
		if strands_points is None:
			self.report({'ERROR'}, "No edges found")
			return {'FINISHED'} # or all changes get lost!!!
		enforceVertCount = self.opt_enforceVCnt
		if enforceVertCount < 0:
			for i in range(len(strands_points)):
				vidx = strands_vidx[i]
				enforceVertCount = max(enforceVertCount,len(vidx))
		for i in range(len(strands_points)):
			vidx = strands_vidx[i]
			len_trg = 0
			t_xp = []
			t_yp_px = []
			t_yp_py = []
			t_yp_pz = []
			t_pos_len = {}
			curve_pt_last = None
			for j, vIds in enumerate(vidx):
				bm.verts.ensure_lookup_table()
				bm.verts.index_update()
				bm.edges.ensure_lookup_table()
				bm.edges.index_update()
				curve_pt = bm.verts[vIds[0]]
				t_yp_px.append(curve_pt.co[0])
				t_yp_py.append(curve_pt.co[1])
				t_yp_pz.append(curve_pt.co[2])
				if curve_pt_last is not None:
					len_trg = len_trg+(curve_pt_last.co-curve_pt.co).length
				t_xp.append(len_trg)
				t_pos_len[vIds[0]] = len_trg
				curve_pt_last = curve_pt
			if self.opt_lerpLinear > 0.0:
				dots = len(t_yp_px)
				if dots > 1:
					for j in range(dots):
						if j == 0 or j == dots-1:
							continue
						px = t_yp_px[0]+(t_yp_px[-1] - t_yp_px[0])*(float(j)/float(dots))
						t_yp_px[j] = t_yp_px[j]+(px - t_yp_px[j])*self.opt_lerpLinear
						py = t_yp_py[0]+(t_yp_py[-1] - t_yp_py[0])*(float(j)/float(dots))
						t_yp_py[j] = t_yp_py[j]+(py - t_yp_py[j])*self.opt_lerpLinear
						pz = t_yp_pz[0]+(t_yp_pz[-1] - t_yp_pz[0])*(float(j)/float(dots))
						t_yp_pz[j] = t_yp_pz[j]+(pz - t_yp_pz[j])*self.opt_lerpLinear
						xp = t_xp[0]+(t_xp[-1] - t_xp[0])*(float(j)/float(dots))
						t_xp[j] = t_xp[j]+(xp - t_xp[j])*self.opt_lerpLinear
			if len_trg > 0.00001:
				if enforceVertCount > 0 and len(vidx) != enforceVertCount:
					t_pos_len = {} # not compatible yet
					maxAttempts = 100
					while maxAttempts > 0 and len(vidx) < enforceVertCount:
						maxAttempts = maxAttempts-1
						bm.verts.ensure_lookup_table()
						bm.verts.index_update()
						bm.edges.ensure_lookup_table()
						bm.edges.index_update()
						j_rand = random.randint(0,len(vidx)-1)
						rnd_vIds = vidx[j_rand]
						curve_pt1 = bm.verts[rnd_vIds[0]]
						# random edge with vert in same line
						rnd_edge = None
						rnd_edge_dir = 0
						for e in curve_pt1.link_edges:
							for j, vIds in enumerate(vidx):
								curve_pt2 = bm.verts[vIds[0]]
								if e.other_vert(curve_pt1) == curve_pt2:
									rnd_edge = e
									rnd_edge_dir = -1
									if j >= j_rand:
										rnd_edge_dir = 1
									break
							if rnd_edge_dir != 0:
								break
						if rnd_edge is not None and rnd_edge_dir != 0:
							result = bmesh.ops.subdivide_edges(bm, edges=[rnd_edge], cuts=1)
							result_verts = [e for e in result["geom_split"] if isinstance(e, bmesh.types.BMVert)]
							if len(result_verts) > 0:
								new_vert = result_verts[0]
								new_vert.select = True
								new_vidx_item = [new_vert.index]
								if rnd_edge_dir > 0:
									vidx.insert(j_rand+1,new_vidx_item) # next to j_rand
								else:
									vidx.insert(j_rand,new_vidx_item) # before j_rand
				if self.opt_smoothArn[0] > 0:
					bpy.ops.mesh.wplverts_pinsnap(opt_pinId = "pin_straight") # WPL, pin mesh
				bm = bmesh.from_edit_mesh(active_mesh)
				for j, vIds in enumerate(vidx):
					bm.verts.ensure_lookup_table()
					bm.verts.index_update()
					bm.edges.ensure_lookup_table()
					bm.edges.index_update()
					curve_pt = bm.verts[vIds[0]]
					t_pos = float(j)/float(len(vidx)-1)*len_trg
					if vIds[0] in t_pos_len:
						t_pos_ini = t_pos_len[vIds[0]]
						t_pos = t_pos_ini*(1.0-self.opt_influence)+t_pos*self.opt_influence
					new_co = Vector((np.interp(t_pos, t_xp, t_yp_px),np.interp(t_pos, t_xp, t_yp_py),np.interp(t_pos, t_xp, t_yp_pz)))
					curve_pt.co = new_co #curve_pt.co.lerp(new_co,self.opt_influence)
				if self.opt_smoothArn[0] > 0:
					bpy.ops.mesh.wplverts_pinpropagt(opt_mode='KEEPACTIV', opt_smoothLoops=self.opt_smoothArn[0], opt_smoothPow=self.opt_smoothArn[1], opt_pinId = "pin_straight") # WPL, pin mesh
				bm = bmesh.from_edit_mesh(active_mesh)
				bm.normal_update()
				bmesh.update_edit_mesh(active_mesh, True)
		return {'FINISHED'}

# class wplsculpt_edge_len(bpy.types.Operator):
# 	bl_idname = "mesh.wplsculpt_edge_len"
# 	bl_label = "Equalize edges"
# 	bl_options = {'REGISTER', 'UNDO'}

# 	opt_preselectRings = BoolProperty(
# 		name="Preselect rings",
# 		default=True
# 	)
# 	opt_mixOrient = FloatProperty(
# 		name="Cast orientation",
# 		min = 0.0, max= 1.0,
# 		default=0.0
# 	)
# 	opt_lengthAdd = FloatProperty(
# 		name="Add space",
# 		default=0.0
# 	)
# 	opt_reperPoint = FloatProperty(
# 		name="Reper point",
# 		default=0.5
# 	)

# 	@classmethod
# 	def poll( cls, context ):
# 		return ( context.object is not None  and
# 				context.object.type == 'MESH' )
# 	def execute( self, context ):
# 		active_obj = context.scene.objects.active
# 		active_mesh = active_obj.data
# 		edgesIdx = get_selected_edgesIdx(active_mesh)
# 		if len(edgesIdx) == 0:
# 			self.report({'ERROR'}, "No edges found, select edge first")
# 			return {'CANCELLED'}
# 		reflenEdgeIdx = -1
# 		if len(edgesIdx) == 1:
# 			reflenEdgeIdx = edgesIdx[0]
# 		bpy.ops.object.mode_set( mode = 'EDIT' )
# 		bpy.ops.mesh.select_mode(type="EDGE")
# 		if len(edgesIdx) == 1 or self.opt_preselectRings:
# 			bpy.ops.mesh.loop_multi_select(ring=True)
# 			edgesIdx = get_selected_edgesIdx(active_mesh)
# 			bpy.ops.object.mode_set(mode = 'EDIT')
# 		bm = bmesh.from_edit_mesh(active_mesh)
# 		bm.edges.ensure_lookup_table()
# 		bm.edges.index_update()
# 		reflen = 0
# 		refdir = None
# 		if reflenEdgeIdx >= 0:
# 			e = bm.edges[reflenEdgeIdx]
# 			reflen = e.calc_length()
# 			refdir = (e.verts[1].co-e.verts[0].co).normalized()
# 		else:
# 			refdir = Vector((0,0,0))
# 			refdir_c = 0
# 			for idx in edgesIdx:
# 				e = bm.edges[idx]
# 				reflen = reflen+e.calc_length()
# 				refdir = refdir+(e.verts[1].co-e.verts[0].co).normalized()
# 				refdir_c = refdir_c+1
# 			reflen = reflen/float(len(edgesIdx))
# 			refdir = refdir/refdir_c
# 		reflen = abs(reflen+self.opt_lengthAdd)
# 		if reflen<0.000001:
# 			self.report({'ERROR'}, "Zero edge len not supported")
# 			return {'CANCELLED'}
# 		alV = Vector((0,0,1))
# 		for idx in edgesIdx:
# 			e = bm.edges[idx]
# 			v1 = e.verts[0]
# 			v2 = e.verts[1]
# 			if abs(v1.co*alV - v2.co*alV) < reflen*0.1:
# 				alV = Vector((1,1,0))
# 		for idx in edgesIdx:
# 			e = bm.edges[idx]
# 			v1 = e.verts[0]
# 			v2 = e.verts[1]
# 			if v1.co*alV > v2.co*alV:
# 				v1 = e.verts[1]
# 				v2 = e.verts[0]
# 			center = v1.co*self.opt_reperPoint+v2.co*(1.0-self.opt_reperPoint)
# 			dir1 = (v1.co-center).normalized()
# 			dir2 = (v2.co-center).normalized()
# 			if self.opt_mixOrient > 0.0:
# 				dirz = 1.0
# 				if dir1.dot(refdir)<dir2.dot(refdir):
# 					dirz = -1.0
# 				dir1 = dir1.lerp(dirz*refdir,self.opt_mixOrient).normalized()
# 				dir2 = dir2.lerp(-1*dirz*refdir,self.opt_mixOrient).normalized()
# 			v1.co = center+dir1*(reflen*(1.0-self.opt_reperPoint))
# 			v2.co = center+dir2*(reflen*self.opt_reperPoint)
# 		bm.normal_update()
# 		bmesh.update_edit_mesh(active_mesh, True)
# 		return {'FINISHED'}

class wplsculpt_doosabin_smooth(bpy.types.Operator):
	bl_idname = "mesh.wplsculpt_doosabin_smooth"
	bl_label = "Doo-Sabin smooth"
	bl_options = {'REGISTER', 'UNDO'}

	opt_SmoothAmount = FloatProperty(
		name="Smooth Amount",
		min=-10, max=10,
		default=0.5
	)
	opt_IterationAmount = IntProperty(
		name="Iterations",
		min=1, max=1000,
		default=1, step=1
	)
	opt_PreserveVolS = FloatProperty(
		name="Keep Surface",
		default=0.0, min=-10, max=10
	)
	opt_PreserveVolN = FloatProperty(
		name="Keep Normal",
		default=0.0, min=-10, max=10
	)
	opt_FreezeBoundary = BoolProperty(
		name="Freeze boundary", default=True
	)
	opt_FreezeSeams = BoolProperty(
		name="Freeze seams", default=True
	)
	# opt_MedianPush = FloatProperty(
		# name="Normal Push",
		# min=-10, max=10,
		# default=0.0
	# )

	def resetOpts(self):
		#self.opt_MedianPush = 0
		self.opt_PreserveVolN = 0
		self.opt_PreserveVolS = 0
		self.opt_FreezeBoundary = True
		self.opt_FreezeSeams = True
		return

	def ds_smooth_mesh(self, bm, selverts, factor, preserveVol, freeze_boundary, freeze_seams):
		def calc_median(*args):
			return sum(args, Vector()) / len(args)
		selected_vertices = [v for v in bm.verts if v.index in selverts]
		face_points = [None] * len(bm.faces)
		bound_verts = []
		seam_verts = []
		for vertex in selected_vertices:
			isNonSelLink = False
			for e in vertex.link_edges:
				if e.seam:
					seam_verts.append(vertex)
			for f in vertex.link_faces:
				if f.hide:
					isNonSelLink = True
					break
				for fv in f.verts:
					if not(fv in selected_vertices) or fv.hide:
						isNonSelLink = True
						break
			if isNonSelLink or vertex.is_boundary:
				bound_verts.append(vertex)
			for face in vertex.link_faces:
				face_points[face.index] = face.calc_center_median()
				#if self.opt_MedianPush != 0.0:
				#	face_points[face.index] = face_points[face.index]+face.normal*self.opt_MedianPush
		#Compute the "edge midpoints" of all edges connected to the selected vertices, indexed by their BMesh indexes.
		edge_midpoints = [None] * len(bm.edges)
		for vertex in selected_vertices:
			for edge in vertex.link_edges:
				if edge_midpoints[edge.index] == None:
					edge_midpoints[edge.index] = calc_median(edge.verts[0].co, edge.verts[1].co)
		#Go through each vertex and compute their smoothed position.
		total_sum = Vector()
		for vertex in selected_vertices:
			if freeze_boundary and vertex in bound_verts:
				continue
			if freeze_seams and vertex in seam_verts:
				continue
			total_sum.zero()
			for face in vertex.link_faces:
				total_sum += face_points[face.index]
			for edge in vertex.link_edges:
				total_sum += edge_midpoints[edge.index]
			ent_cnt = (len(vertex.link_faces) + len(vertex.link_edges))
			if ent_cnt == 0:
				continue
			new_co = total_sum / ent_cnt
			old_co = vertex.co.copy()
			vertex.co = vertex.co + factor*(new_co - vertex.co)
			if abs(preserveVol) > 0.001:
				diff = vertex.co - old_co
				projectedDiff_on_normal = vertex.normal * vertex.normal.dot(diff)  # u(u dot v)  - projection of v on u
				vertex.co -= projectedDiff_on_normal * preserveVol
		return

	@classmethod
	def poll( cls, context ):
		return ( context.object is not None  and
				context.object.type == 'MESH' )

	def execute( self, context ):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		selvertsAll = get_selected_vertsIdx(active_mesh)
		if len(selvertsAll)<3:
			self.resetOpts()
			bpy.ops.object.mode_set( mode = 'EDIT' )
			self.report({'ERROR'}, "At least 3 verts needed")
			return {'FINISHED'}
		bpy.ops.object.mode_set( mode = 'EDIT' )
		bm = bmesh.from_edit_mesh(active_mesh)
		oldselectmode = bm.select_mode
		bm.faces.ensure_lookup_table()
		bm.faces.index_update()
		bm.verts.ensure_lookup_table()
		bm.verts.index_update()
		bvh_orig = None
		if abs(self.opt_PreserveVolS) > 0.001:
			# creating BVH only from selected faces
			bm2 = bmesh.new()
			bm2vmap = {}
			bm2conv = []
			for f in bm.faces:
				if f.select == False:
					continue
				f_v_set = []
				for v in f.verts:
					v_co = v.co
					vert_index = coToKey(v_co)
					if vert_index not in bm2vmap:
						v_cc = bm2.verts.new(v_co)
						bm2vmap[vert_index] = v_cc
					else:
						v_cc = bm2vmap[vert_index]
					if v_cc not in f_v_set:
						f_v_set.append(v_cc)
				if len(f_v_set) >= 3:
					f_cc = bm2.faces.new(f_v_set)
			bvh_orig = BVHTree.FromBMesh(bm2, epsilon = 0)
		okCnt = len(selvertsAll)
		for i in range(self.opt_IterationAmount):
			self.ds_smooth_mesh(bm, selvertsAll, self.opt_SmoothAmount, self.opt_PreserveVolN, self.opt_FreezeBoundary, self.opt_FreezeSeams)
			#bpy.ops.mesh.vertices_smooth()
			if bvh_orig is not None:
				for vIdx in selvertsAll:
					v = bm.verts[vIdx]
					# first project
					n_loc, n_normal, n_index, n_distance = bvh_orig.ray_cast(v.co, v.normal)
					if n_loc is None:
						# if nothing then shrinkwrap
						n_loc, n_normal, n_index, n_distance = bvh_orig.find_nearest(v.co)
					if n_loc is not None:
						v.co = v.co.lerp(n_loc, self.opt_PreserveVolS)
			bm.normal_update()
		bm_selectVertEdgesFaces(bm, selvertsAll)
		bmesh.update_edit_mesh(active_mesh, True)
		if oldselectmode is not None and list(oldselectmode)[0] != 'VERT':
			bpy.ops.mesh.select_mode(type=list(oldselectmode)[0])
		self.report({'INFO'}, "Done, "+str(okCnt)+" verts moved")
		return {'FINISHED'}

class wplsculpt_flt_toconvex(bpy.types.Operator):
	bl_idname = "mesh.wplsculpt_flt_toconvex"
	bl_label = "Wrap to convex"
	bl_options = {'REGISTER', 'UNDO'}

	opt_influence = FloatProperty(
		name		= "Influence",
		default	 = 1.0,
		min = -10.0,
		max = 10.0
	)
	opt_postSmooth = IntProperty(
		name		= "Post-smooth",
		default	 = 3,
		min		 = 0,
		max		 = 1000
	)

	opt_normCast = FloatProperty(
		name		= "Recast with Normal",
		default		= 0.0
	)
	opt_cursCast = FloatProperty(
		name		= "Recast with 3D Cursor",
		default		= 0.0
	)

	opt_halfConvex = BoolProperty(
		name="Use convex half", default=True
	)

	opt_FreezeBoundary = BoolProperty(
		name="Freeze boundary", default=True
	)
	opt_FreezeSeams = BoolProperty(
		name="Freeze Seams", default=True
	)
	opt_convexMode = bpy.props.EnumProperty(
		name="Convex mode", default="ALL",
		items=(("ALL", "All verts", ""), ("BOUNDS", "Bound verts", ""), ("USEPINNED", "Pinned", ""), ("PINCONVEX", "Pin active", ""), ("PINCONVEX_XMIRR", "Pin active+X Mirror", ""))
	)

	def resetOpts(self):
		self.opt_influence = 1
		self.opt_postSmooth = 3
		self.opt_normCast= 0.0
		self.opt_cursCast = 0.0
		self.opt_FreezeBoundary = True
		self.opt_FreezeSeams = True
		return

	@classmethod
	def poll( cls, context ):
		return ( context.object is not None and
				context.object.type == 'MESH' )

	def execute( self, context ):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		selvertsAll = get_selected_vertsIdx(active_mesh)
		if len(selvertsAll) == 0:
			self.resetOpts()
			bpy.ops.object.mode_set( mode = 'EDIT' )
			self.report({'ERROR'}, "At least 3 verts needed")
			return {'FINISHED'}

		bpy.ops.object.mode_set( mode = 'EDIT' )
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.verts.index_update()
		oldselectmode = bm.select_mode
		bvh_orig = BVHTree.FromBMesh(bm, epsilon = 0)
		okCnt = 0

		bound_verts = []
		seam_verts = []
		for vIdx in selvertsAll:
			v = bm.verts[vIdx]
			isNonSelLink = False
			for e in v.link_edges:
				if e.seam:
					seam_verts.append(vIdx)
				if not(e.other_vert(v).index in selvertsAll):
					isNonSelLink = True
					break
			if isNonSelLink or v.is_boundary:
				bound_verts.append(vIdx)
		originalPos = {}
		originalNrm = {}
		originalPosKey = {}
		originalNrmAvg = Vector((0,0,0))
		originalNrmAvgC = 0.0
		originalNrmAvgA = Vector((0,0,0))
		originalNrmAvgAC = 0.0
		for vIdx in selvertsAll:
			v = bm.verts[vIdx]
			originalPos[vIdx] = Vector((v.co[0],v.co[1],v.co[2]))
			originalNrm[vIdx] = Vector((v.normal[0],v.normal[1],v.normal[2]))
			originalNrmAvgA = originalNrmAvgA+v.normal
			originalNrmAvgAC = originalNrmAvgAC+1.0
			if vIdx in bound_verts:
				originalNrmAvg = originalNrmAvg+v.normal
				originalNrmAvgC = originalNrmAvgC+1.0
		if originalNrmAvgC>0:
			originalNrmAvg = originalNrmAvg/originalNrmAvgC
		else: # convexes, etc, no bounds
			originalNrmAvg = originalNrmAvgA/originalNrmAvgAC
		originalNrmAvg = originalNrmAvg.normalized()
		bm2 = bmesh.new()
		hullv = []
		if self.opt_convexMode == 'PINCONVEX' or self.opt_convexMode == 'PINCONVEX_XMIRR':
			last_used_co = []
			for vIdx in selvertsAll:
				v = bm.verts[vIdx]
				v_co = copy.copy(v.co)
				last_used_co.append(v_co)
				if self.opt_convexMode == 'PINCONVEX_XMIRR':
					v_co_xm = Vector((-1*v_co[0], v_co[1], v_co[2]))
					last_used_co.append(v_co_xm)
			WPL_G.store["convex_last_used"] = last_used_co
			self.report({'INFO'}, "Pinned "+str(len(last_used_co))+" verts")
			return {'FINISHED'}
		hullc_c = Vector((0,0,0))
		if self.opt_convexMode == 'USEPINNED':
			if "convex_last_used" in WPL_G.store:
				lastVerts = WPL_G.store["convex_last_used"]
				for v_co in lastVerts:
					bm2v = bm2.verts.new(v_co)
					hullc_c = hullc_c+v_co
					hullv.append(bm2v)
		else:
			for vIdx in selvertsAll:
				bm2.verts.ensure_lookup_table()
				v = bm.verts[vIdx]
				if self.opt_convexMode == 'BOUNDS':
					isSelects = False
					isNonselects = False
					for e in v.link_edges:
						if e.other_vert(v).index in selvertsAll:
							isSelects = True
						else:
							isNonselects = True
					if self.opt_FreezeBoundary and v.is_boundary:
						isNonselects = True
					if self.opt_FreezeSeams and vIdx in seam_verts:
						isNonselects = True
					if isSelects == True and isNonselects == False:
						# nonbound
						continue
				bm2v = bm2.verts.new(v.co)
				hullc_c = hullc_c+v.co
				hullv.append(bm2v)
		if len(hullv) < 3:
			self.resetOpts()
			self.report({'ERROR'}, "At least 3 verts needed")
			return {'FINISHED'}
		hullc_c = hullc_c/len(hullv)
		if abs(self.opt_cursCast) > 0.001:
			cur_co = active_obj.matrix_world.inverted() * get_active_context_cursor(context)
			if cur_co is not None:
				# ignoring real normal and use direction from cursor to vertex
				print(" - rewriting normals")
				for vIdx in originalPos:
					reintNrm = (originalPos[vIdx]-cur_co).normalized()
					originalNrm[vIdx] = originalNrm[vIdx].lerp(reintNrm, self.opt_cursCast).normalized()
		print(" - convex verts", len(hullv))
		bm2.verts.ensure_lookup_table()
		bm2.verts.index_update()
		bmesh.ops.convex_hull(bm2, input=hullv)
		bm2.faces.ensure_lookup_table()
		bm2.faces.index_update()
		if self.opt_halfConvex:
			faces2del = []
			for hull_face in bm2.faces:
				# v1: checking if hull face is inside (bad for non-strict-closed meshes)
				#fc = hull_face.calc_center_median()
				#n_loc, n_normal, n_index, n_distance = bvh_orig.ray_cast(fc+hull_face.normal*0.0001, hull_face.normal)
				#if n_loc is not None:
				#	# is hit from inside?
				#	if (n_loc-fc).normalized().dot(n_normal)<0:
				#		n_loc = None
				#	if n_loc is not None and hull_face not in faces2del:
				#		faces2del.append(hull_face)
				# v2: checking is face normal opposite to average verts normal (good after fairing)
				if hull_face.normal.dot(originalNrmAvg)<= 0.0:
					faces2del.append(hull_face)
			if len(faces2del)>0:
				bmesh.ops.delete(bm2, geom=faces2del, context=5) #DEL_FACES
		bvh_hull = BVHTree.FromBMesh(bm2, epsilon = kWPLRaycastEpsilonCCL)
		bm2.free()
		newPos = {}
		for i in range(self.opt_postSmooth+1):
			if i>0:
				bpy.ops.mesh.vertices_smooth()
			for vIdx in selvertsAll:
				v = bm.verts[vIdx]
				n_loc1 = v.co
				n_loc2 = None
				n_loc3 = None
				n_loc4 = None
				if abs(self.opt_normCast)+abs(self.opt_cursCast) > 0.00001:
					n_loc1_nrm = originalNrm[vIdx]
					castDir = 1.0
					if abs(self.opt_normCast) > 0.0001:
						castDir = math.copysign(1.0, self.opt_normCast)
					n_loc2, n_normal2, n_index2, n_distance2 = bvh_hull.ray_cast(v.co, n_loc1_nrm * castDir)
					if n_loc2 is not None:
						n_loc1 = n_loc1.lerp(n_loc2, abs(self.opt_normCast)+abs(self.opt_cursCast))
				n_loc4, n_normal4, n_index4, n_distance4 = bvh_hull.find_nearest(n_loc1)
				if n_loc4 is None:
					continue
				newPos[vIdx] = n_loc4
			for vIdx in selvertsAll:
				v = bm.verts[vIdx]
				if vIdx in newPos:
					v.co = newPos[vIdx]
		bm.normal_update()
		for vIdx in selvertsAll:
			v = bm.verts[vIdx]
			needFrees = False
			if self.opt_FreezeBoundary and vIdx in bound_verts:
				needFrees = True
			if self.opt_FreezeSeams and vIdx in seam_verts:
				needFrees = True
			if needFrees:
				v.co = originalPos[vIdx]
			elif vIdx in newPos:
				v.co = originalPos[vIdx].lerp(newPos[vIdx], self.opt_influence)
				okCnt = okCnt+1
			originalPosKey[coToKey(v.co)] = 1
		bm.verts.ensure_lookup_table()
		bm.verts.index_update()
		bm.faces.ensure_lookup_table()
		bm.normal_update()
		bmesh.update_edit_mesh(active_mesh, True)
		bpy.ops.mesh.delete_loose()
		# reselecting by position (delete_loose kills indexes)
		bpy.ops.mesh.select_all(action='DESELECT')
		bpy.ops.mesh.select_mode(type='VERT')
		bm = bmesh.from_edit_mesh(active_mesh)
		verts2sel = []
		for v in bm.verts:
			if coToKey(v.co) in originalPosKey:
				verts2sel.append(v.index)
		bm_selectVertEdgesFaces(bm, verts2sel)
		bmesh.update_edit_mesh(active_mesh, True)
		if oldselectmode is not None and list(oldselectmode)[0] != 'VERT':
			bpy.ops.mesh.select_mode(type=list(oldselectmode)[0])
		self.report({'INFO'}, "Done, "+str(okCnt)+" verts moved")
		return {'FINISHED'}

class wplsculpt_fill_smartjoin(bpy.types.Operator):
	bl_idname = "mesh.wplsculpt_fill_smartjoin"
	bl_label = "History join"
	bl_options = {'REGISTER', 'UNDO'}
	
	opt_preSubdiv = IntProperty(
		name		= "Pre-subdiv blob",
		default	 = 1,
		min		 = 0,
		max		 = 1000
	)
	opt_preTriang = BoolProperty(
		name="Pre-triangulate blob", default=True
	)
	opt_postSelIntrs = BoolProperty(
		name="Post-select intersection", default=False
	)
	opt_postSelBlob = BoolProperty(
		name="Post-select blob", default=True
	)
	
	@classmethod
	def poll( cls, context ):
		return ( context.object is not None  and
				context.object.type == 'MESH' )

	def execute( self, context ):
		active_obj = context.scene.objects.active
		if active_obj.data.shape_keys is not None:
			self.report({'ERROR'}, "Shapekeys detected. Can`t continue.")
			return {'CANCELLED'}
		active_mesh = active_obj.data
		bpy.ops.object.mode_set( mode = 'EDIT' )
		bpy.ops.mesh.select_mode(type='VERT')
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.verts.index_update()
		for v in bm.verts:
			if v.hide:
				self.report({'ERROR'}, "Hidden verts detected. Can`t continue.")
				return {'CANCELLED'}
		histVertsIdx = get_bmhistory_vertsIdx(bm)
		if len(histVertsIdx) < 2:
			self.report({'ERROR'}, "Two hist-verts needed")
			return {'CANCELLED'}
		histV2_idx = histVertsIdx[-1] # convex, choosen first
		histV2_co = copy.copy(bm.verts[histV2_idx].co)
		histV1s_idx = []
		histV1s_co = []
		for idx in histVertsIdx[:-1]: # base verts, choosen last
			histV1s_idx.append(idx)
			histV1s_co.append(copy.copy(bm.verts[idx].co))
		bpy.ops.mesh.select_linked(delimit=set())
		bpy.ops.mesh.hide(unselected=True)
		bpy.ops.mesh.select_all(action='DESELECT')
		bpy.ops.object.mode_set( mode = 'OBJECT' )
		active_mesh.vertices[histV2_idx].select = True
		bpy.ops.object.mode_set( mode = 'EDIT' )
		bpy.ops.mesh.select_linked(delimit=set())
		if self.opt_preTriang:
			bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')
		if self.opt_preSubdiv > 0:
			bpy.ops.mesh.subdivide(number_cuts=self.opt_preSubdiv, smoothness=0)
		bpy.ops.object.mode_set( mode = 'OBJECT' )
		blobPnts = []
		for vert in active_mesh.vertices:
			if vert.select:
				blobPnts.append(copy.copy(vert.co))
		bpy.ops.object.mode_set( mode = 'EDIT' )
		bpy.ops.mesh.intersect(separate_mode='CUT', threshold=0.0)
		bpy.ops.object.mode_set( mode = 'OBJECT' )
		intrsPnts = []
		for vert in active_mesh.vertices:
			if vert.select:
				intrsPnts.append(copy.copy(vert.co))
		bpy.ops.object.mode_set( mode = 'EDIT' )
		bpy.ops.mesh.hide(unselected=False)
		bpy.ops.mesh.select_all(action='DESELECT')
		bpy.ops.object.mode_set( mode = 'OBJECT' )
		for vert in active_mesh.vertices:
			for histV1_co in histV1s_co:
				if (vert.co-histV1_co).length < 0.000001:
					vert.select = True
			if (vert.co-histV2_co).length < 0.000001:
				vert.select = True
		bpy.ops.object.mode_set( mode = 'EDIT' )
		bpy.ops.mesh.select_linked(delimit=set())
		bpy.ops.mesh.hide(unselected=False)
		bpy.ops.mesh.select_all(action='SELECT')
		bpy.ops.mesh.delete(type='VERT')
		bpy.ops.mesh.reveal()
		bpy.ops.mesh.remove_doubles()
		bpy.ops.mesh.select_all(action='DESELECT')
		bpy.ops.object.mode_set( mode = 'OBJECT' )
		if self.opt_postSelIntrs:
			for vert in active_mesh.vertices:
				for v_co in intrsPnts:
					if (vert.co-v_co).length < 0.000001:
						vert.select = True
		if self.opt_postSelBlob:
			for vert in active_mesh.vertices:
				for v_co in blobPnts:
					if (vert.co-v_co).length < 0.000001:
						vert.select = True
		bpy.ops.object.mode_set( mode = 'EDIT' )
		#bm = bmesh.from_edit_mesh(active_mesh)
		#bm.verts.ensure_lookup_table()
		#bm.verts.index_update()
		return {'FINISHED'}
	
class wplsculpt_weldinto(bpy.types.Operator):
	bl_idname = "mesh.wplsculpt_weldinto"
	bl_label = "Weld verts into selection"
	bl_options = {'REGISTER', 'UNDO'}

	opt_distanceAbs = FloatProperty(
		name		= "Absolute distance",
		default	 = 0.001,
		min		 = 0.00001,
		max		 = 100
		)
	opt_distanceRel = FloatProperty(
		name		= "Edge-relative distance",
		subtype		= 'PERCENTAGE',
		default	 = 20,
		min		 = 0.0,
		max		 = 100.0
		)
	opt_rmdDistanceAbs = FloatProperty(
		name		= "Pre-remove doubles distance",
		default	 = -1.0,
		min		 = -1.0,
		max		 = 100
		)
	opt_rmdMiddles = BoolProperty(
		name		= "Post-remove middle verts",
		default	 = True
		)

	@classmethod
	def poll( cls, context ):
		return ( context.object is not None  and
				context.object.type == 'MESH' )

	def execute( self, context ):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		if abs(self.opt_rmdDistanceAbs) > 0.0001:
			dst = self.opt_rmdDistanceAbs
			selvertsAll = get_selected_vertsIdx(active_mesh)
			if len(selvertsAll) == 0:
				self.report({'ERROR'}, "No selected verts found")
				return {'CANCELLED'}
			bpy.ops.object.mode_set( mode = 'EDIT' )
			if dst < 0:
				bm = bmesh.from_edit_mesh( active_mesh )
				bm.verts.ensure_lookup_table()
				bm.verts.index_update()
				edgelenAvg = getBmAverageEdgeLen(bm, selvertsAll, 0.0)
				dst = edgelenAvg*abs(dst)
			bpy.ops.mesh.remove_doubles(threshold = dst)
		selvertsAll = get_selected_vertsIdx(active_mesh)
		if len(selvertsAll) == 0:
			self.report({'ERROR'}, "No selected verts found")
			return {'CANCELLED'}

		bpy.ops.object.mode_set( mode = 'EDIT' )
		bm = bmesh.from_edit_mesh( active_mesh )
		bm.verts.ensure_lookup_table()
		bm.verts.index_update()
		edgelenAvg = getBmAverageEdgeLen(bm, selvertsAll, 0.0)
		checkDst = max(self.opt_distanceAbs, edgelenAvg*(self.opt_distanceRel/100.0))
		bmtree = getBmVertsKdtree(None, bm, selvertsAll)
		weldmap = {}
		welddist = {}
		#dissolv = []
		for vIdx in selvertsAll:
			v = bm.verts[vIdx]
			nearest_verts = bmtree.find_range(v.co, checkDst)
			for nearest_body_vert_data in nearest_verts:
				near_vert_idx = nearest_body_vert_data[1]
				near_vert_dist = nearest_body_vert_data[2]
				if near_vert_idx not in welddist or near_vert_dist < welddist[near_vert_idx]:
					near_v = bm.verts[near_vert_idx]
					if near_v.hide > 0:
						continue
					welddist[near_vert_idx] = near_vert_dist
					weldmap[near_v] = v
		bmesh.ops.weld_verts(bm, targetmap = weldmap)
		bmesh.update_edit_mesh(active_mesh)
		if self.opt_rmdMiddles:
			selvertsAll = get_selected_vertsIdx(active_mesh)
			bpy.ops.object.mode_set( mode = 'EDIT' )
			bm = bmesh.from_edit_mesh( active_mesh )
			bm.verts.ensure_lookup_table()
			bm.verts.index_update()
			verts2dslv = []
			for vIdx in selvertsAll:
				v = bm.verts[vIdx]
				if len(v.link_edges) < 3:
					verts2dslv.append(v)
			bmesh.ops.dissolve_verts(bm, verts = verts2dslv)
			bmesh.update_edit_mesh(active_mesh)
		self.report({'INFO'}, "Verts merged: "+str(len(weldmap)))
		return {'FINISHED'}

class wplsculpt_ar_vhide(bpy.types.Operator):
	bl_idname = "object.wplsculpt_ar_vhide"
	bl_label = "Hide verts"
	bl_options = {'REGISTER', 'UNDO'}
	opt_bones2use = StringProperty(
		name = "Names",
		default = ""
	)
	@classmethod
	def poll( cls, context ):
		p = (isinstance(context.scene.objects.active, bpy.types.Object))
		return p

	def execute( self, context ):
		active_obj = context.scene.objects.active
		if active_obj is None or active_obj.type != 'MESH':
			return {'FINISHED'}
		active_mesh = active_obj.data
		oldmode = select_and_change_mode(active_obj,'EDIT')
		bpy.ops.mesh.select_mode(type='VERT')
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.verts.index_update()
		if len(self.opt_bones2use) == 0:
			bpy.ops.mesh.reveal()
			for v in bm.verts:
				v.select = False
			bmesh.update_edit_mesh(active_mesh, True)
			select_and_change_mode(active_obj,oldmode)
			self.report({'INFO'}, "Verts unhidden")
			return {'FINISHED'}
		for v in bm.verts:
			v.select = False
		bnpref = [x.strip() for x in self.opt_bones2use.split(",")]
		for pref_item in bnpref:
			bnLimit = 0.001
			pref = pref_item
			if ":" in pref:
				pref_item_sl = pref_item.split(":")
				pref = pref_item_sl[0]
				bnLimit = float(pref_item_sl[1])
			for vg in active_obj.vertex_groups:
				isVgNeeded = 0
				prefVg = None
				if pref in vg.name:
					isVgNeeded = 1
					prefVg = vg
				if ("!" in pref) and (pref in "!"+vg.name):
					isVgNeeded = -1
					prefVg = vg
				if isVgNeeded != 0 and prefVg is not None:
					allVgVertsCo, allVgVertsIdx, allVgVertsW = get_vertgroup_verts(active_obj, prefVg, bnLimit)
					print("- ",pref_item, isVgNeeded, prefVg.name, bnLimit, "->",len(allVgVertsIdx))
					for vgv_idx in allVgVertsIdx:
						v = bm.verts[vgv_idx]
						if isVgNeeded>0:
							v.select = True
						if isVgNeeded<0:
							v.select = False
						# all side verts also
						for e in v.link_edges:
							v2 = e.other_vert(v)
							if isVgNeeded>0:
								v2.select = True
							if isVgNeeded<0:
								v2.select = False
		okCnt = 0
		for v in bm.verts:
			if v.select:
				okCnt = okCnt+1
		bmesh.update_edit_mesh(active_mesh, True)
		bpy.ops.mesh.hide(unselected=False)
		select_and_change_mode(active_obj,oldmode)
		self.report({'INFO'}, "Verts hidden: "+str(okCnt))
		return {'FINISHED'}

########### ################ ############### ############## ##############
class WPLSculptTools_Panel1(bpy.types.Panel):
	bl_label = "Mesh Sculpt"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_category = 'WPL'

	def draw_header(self, context):
		layout = self.layout
		layout.label(text="")

	def draw(self, context):
		active_obj = context.scene.objects.active
		
		layout = self.layout
		col = layout.column()
		col.operator("mesh.wplsculpt_doosabin_smooth")
		col.separator()
		op1 = col.operator("mesh.wplsculpt_flt_toconvex")
		op1.opt_convexMode = 'ALL'

		row1 = col.row()
		op2 = row1.operator("mesh.wplsculpt_flt_toconvex", text="Flatten to bounds")
		op2.opt_convexMode = 'BOUNDS'
		op5 = row1.operator("mesh.wplsculpt_edge_verts", text="Straighten")
		op5.opt_lerpLinear = 1.0
		op5.opt_smoothArn = (3, 1.0)
		row2 = col.row()
		op3 = row2.operator("mesh.wplsculpt_flt_toconvex", text="Pin convex")
		op3.opt_convexMode = 'PINCONVEX'
		op4 = row2.operator("mesh.wplsculpt_flt_toconvex", text="Wrap to pinned")
		op4.opt_convexMode = 'USEPINNED'
		col.separator()
		#col.operator("mesh.wplsculpt_edge_len")
		row3 = col.row()
		op6 = row3.operator("mesh.wplsculpt_edge_verts", text="Distribute")
		op6.opt_lerpLinear = 0.0
		op6.opt_smoothArn = (0.0, 1.0)
		op7 = row3.operator("mesh.wplsculpt_edge_verts", text="Linearize")
		op7.opt_lerpLinear = 1.0
		op7.opt_smoothArn = (0.0, 1.0)
		col.operator("mesh.wplsculpt_weldinto")
		col.operator("mesh.wplsculpt_egeoout")
		col.separator()
		col.operator("mesh.wplsculpt_fill_smartjoin")
		col.operator("mesh.wplsculpt_ebisect")
		col.separator()
		
		if active_obj is not None and active_obj.type == 'MESH':
			box4 = col.box()
			box4.label(text="Mesh masking")
			box4.operator("object.wplsculpt_ar_vhide", text="- Body").opt_bones2use = select_by_arm(active_obj, kArmMeshPartHide_Body_MB, kArmMeshPartHide_Body_MLOW, "")
			row1 = box4.row()
			row1.operator("object.wplsculpt_ar_vhide", text="-L Arm").opt_bones2use = select_by_arm(active_obj, kArmMeshPartHide_ArmL_MB, kArmMeshPartHide_ArmL_MLOW, "")
			row1.operator("object.wplsculpt_ar_vhide", text="-R Arm").opt_bones2use = select_by_arm(active_obj, kArmMeshPartHide_ArmR_MB, kArmMeshPartHide_ArmR_MLOW, "")
			row2 = box4.row()
			row2.operator("object.wplsculpt_ar_vhide", text="-L Leg").opt_bones2use = select_by_arm(active_obj, kArmMeshPartHide_LegL_MB, kArmMeshPartHide_LegL_MLOW, "")
			row2.operator("object.wplsculpt_ar_vhide", text="-R Leg").opt_bones2use = select_by_arm(active_obj, kArmMeshPartHide_LegR_MB, kArmMeshPartHide_LegR_MLOW, "")
			box4.operator("object.wplsculpt_ar_vhide", text="- Hands").opt_bones2use = select_by_arm(active_obj, kArmMeshPartHide_Hands_MB, kArmMeshPartHide_Hands_MLOW, "")
			box4.operator("object.wplsculpt_ar_vhide", text="Unhide all").opt_bones2use = ''

def register():
	bpy.utils.register_module(__name__)

def unregister():
	bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
	register()
