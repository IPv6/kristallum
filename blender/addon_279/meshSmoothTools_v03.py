import math
import copy
import random
import mathutils
import numpy as np
import bisect

import bpy
from bpy.props import *
import bpy.types
import bmesh
from mathutils import Vector, Matrix
from bpy_extras import view3d_utils
from mathutils import kdtree
from mathutils.bvhtree import BVHTree

bl_info = {
	"name": "WPL Smooth Deforming",
	"author": "IPv6",
	"version": (1, 0, 0),
	"blender": (2, 7, 9),
	"location": "View3D > T-panel > WPL",
	"description" : "",
	"warning"	 : "",
	"wiki_url"	: "",
	"tracker_url" : "",
	"category"	: ""
}

kRaycastEpsilon = 0.01
kRaycastEpsilonCCL = 0.0001
kWPLRefitStoreKey = "kWPLRefitStoreKey"
kWPLSelBufferUVMap = "_tmpMeshSel_"

kWPLSmoothHolderUVMap1 = "_tmpMeshPinstate1"
kWPLSmoothHolderUVMap2 = "_tmpMeshPinstate2"
kWPLSmoothHolderUVMap3 = "_tmpMeshPinstate3"
kWPLSmoothHolderUVMap4 = "_tmpMeshPinstate4"
class WPL_G:
	store = {}

######################### ######################### #########################
######################### ######################### #########################
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

def get_bmselectedVertsIdxWeighted(bm,loops):
	weights = {}
	selectedVertsIdx = [v.index for v in bm.verts if v.select]
	for vIdx in selectedVertsIdx:
		weights[vIdx] = 1.0
	# if loops < 0.0:
	# 	-# verts distance
	# 	kd = mathutils.kdtree.KDTree(len(selectedVertsIdx))
	# 	for i, vIdx in enumerate(selectedVertsIdx):
	# 		v1 = bm.verts[vIdx]
	# 		kd.insert(v1.co, vIdx)
	# 	kd.balance()
	# 	maxDist = abs(loops)
	# 	for vert in bm.verts:
	# 		if vert.index not in weights:
	# 			# distance
	# 			f_co,f_idx,f_dst = kd.find(vert.co)
	# 			if f_dst is not None and f_dst<maxDist:
	# 				weights[vert.index] = 1.0-f_dst/maxDist
	if loops >= 1.0:
		bound_vertsIdx = []
		bound_verts_cnt = {}
		for vIdx in selectedVertsIdx:
			bound_verts_cnt[vIdx] = 0
		selfld_next = copy.copy(selectedVertsIdx)
		for i in range(int(loops)):
			selfld = selfld_next
			selfld_next = []
			bound_step_vertsIdx = []
			for vIdx in selfld:
				vertex = bm.verts[vIdx]
				isNonSelLink = False
				for e in vertex.link_edges:
					other_vrt = e.other_vert(vertex)
					if not(other_vrt.index in selectedVertsIdx) or other_vrt.index in bound_vertsIdx:
						isNonSelLink = True
						break
				if isNonSelLink or vertex.is_boundary:
					bound_step_vertsIdx.append(vertex.index)
					#vertex.select = False
				else:
					selfld_next.append(vIdx)
			for vIdx in bound_step_vertsIdx:
				bound_vertsIdx.append(vIdx)
			for vIdx in bound_vertsIdx:
				bound_verts_cnt[vIdx] = bound_verts_cnt[vIdx]+1
		for vIdx in selectedVertsIdx:
			loopwei = float(bound_verts_cnt[vIdx])/float(loops+1.0)
			weights[vIdx] = float(weights[vIdx])*loopwei
	return (selectedVertsIdx,weights)
def get_bmhistory_vertsIdx(active_bmesh):
	active_bmesh.verts.ensure_lookup_table()
	active_bmesh.verts.index_update()
	selectedVertsIdx = []
	for elem in active_bmesh.select_history:
		if isinstance(elem, bmesh.types.BMVert) and elem.select and elem.hide == 0:
			selectedVertsIdx.append(elem.index)
	return selectedVertsIdx

def get_sceneColldersBVH(forObj):
	matrix_world = forObj.matrix_world
	matrix_world_inv = matrix_world.inverted()
	objs2checkAll = [obj for obj in bpy.data.objects]
	bvh2collides = []
	for obj in objs2checkAll:
		if obj.name == forObj.name:
			continue
		if obj.hide == True:
			continue
		for md in obj.modifiers:
			if md.type == 'COLLISION':
				bm_collide = bmesh.new()
				bm_collide.from_object(obj, bpy.context.scene)
				bm_collide.transform(obj.matrix_world)
				bm_collide.transform(matrix_world_inv)
				bm_collide.verts.ensure_lookup_table()
				bm_collide.faces.ensure_lookup_table()
				bm_collide.verts.index_update()
				bvh_collide = BVHTree.FromBMesh(bm_collide, epsilon = kRaycastEpsilonCCL)
				bm_collide.free()
				bvh2collides.append(bvh_collide)
				break
	return bvh2collides

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

def get_active_context_cursor(context):
	scene = context.scene
	space = context.space_data
	cursor = (space if space and space.type == 'VIEW_3D' else scene).cursor_location
	return cursor

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
#
# 	for shootDir in vDirs:
# 		(result, loc_g, normal, index, object, matrix) = bpy.context.scene.ray_cast(vFrom+vDir*kRaycastEpsilon, shootDir)
# 		#print("fuzzySceneRayCast", vFrom, shootDir, result, loc_g)
# 		if result and (objs2ignore is None or object.name not in objs2ignore):
# 			gCount = gCount+1.0
# 			gResult = gResult+loc_g
# 			gResultNormal = gResultNormal+normal
#
# 	if gCount>0:
# 		return (gResult/gCount,gResultNormal/gCount)
# 	return (None, None)

def addConnectedBmVerts_v02(iniDepth, bm, v, verts_list, selverts):
	if iniDepth == 0:
		for temp in bm.verts:
			temp.tag = False
	v.tag = True
	if (selverts is not None) and (v.index not in selverts):
		return
	if v not in verts_list:
		verts_list.append(v)
	if iniDepth < 100:
		for edge in v.link_edges:
			ov = edge.other_vert(v)
			if (ov is None) or ov.tag:
				continue
			addConnectedBmVerts_v02(iniDepth+1, bm, ov, verts_list, selverts)

def getBmEdgesAsStrands_v02(bm, vertsIdx, edgesIdx, opt_flowDirP, opt_edgeStep):
	# looking for bounding verts
	bndVerts = []
	opt_flowDir = Vector(opt_flowDirP)
	opt_flowDir = opt_flowDir.normalized()
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
			bndVerts.append((vIdx, edgeDirs[0],edgeLens/(edgeLensC+0.001)))
	if len(bndVerts)<2 or len(bndVerts)%2 == 1:
		return (None, None, None)
	bndVerts.sort(key=lambda ia: ia[1], reverse=False)
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
			points_co.append(v.co)
			canContinue = False
			for e in v.link_edges:
				if e.index in edgesIdx:
					vIdx = e.other_vert(v).index
					if vIdx not in checked_verts:
						canContinue = True
						break
	#print("strands_points", strands_points, strands_vidx)
	if(opt_edgeStep > 1):
		# repacking
		strands_points2 = []
		strands_vidx2 = []
		for i,points_co in enumerate(strands_points):
			points_co2 = []
			points_idx2 = []
			strands_points2.append(points_co2)
			strands_vidx2.append(points_idx2)
			lastIdxList = None
			for j in range(len(points_co)):
				if j == 0 or (j%opt_edgeStep) == 0 or j == len(points_co)-1:
					if j < len(points_co)-1:
						lastIdxList = strands_vidx[i][j]
					else:
						lastIdxList.append(strands_vidx[i][j][0])
					points_co2.append(points_co[j])
					points_idx2.append(lastIdxList)
				else:
					lastIdxList.append(strands_vidx[i][j][0])
		#print("strands_points2", strands_points2, strands_vidx2)
		strands_points = strands_points2
		strands_vidx = strands_vidx2
	return (strands_points, strands_radius, strands_vidx)

def strandsPoints2globalCurveset(active_obj, bm, strands_points, strands_vidx):
	matrix_world = active_obj.matrix_world
	matrix_world_inv = active_obj.matrix_world.inverted()
	matrix_world_norm = matrix_world_inv.transposed().to_3x3()
	g_curveset = []
	for i, strand_curve in enumerate(strands_points):
		if len(strand_curve) < 2: # we can have single vertices in list too
			continue
		g_curve = []
		for j, co in enumerate(strand_curve):
			vIdx = strands_vidx[i][j][0]
			v = bm.verts[vIdx]
			v_co_g = matrix_world*co
			flow_g = Vector((0,0,0))
			if j<len(strand_curve)-1:
				flow_g = matrix_world*strand_curve[j+1] - v_co_g
			else:
				flow_g = v_co_g-matrix_world*strand_curve[j-1] # last one point in prev direction
				#break #last one is SKIPPED
			g_curve.append((v_co_g, matrix_world_norm*v.normal, flow_g))
		g_curveset.append(g_curve)
	return g_curveset

def customAxisMatrix(v_origin, a, b):
	#https://blender.stackexchange.com/questions/30808/how-do-i-construct-a-transformation-matrix-from-3-vertices
	#def make_matrix(v_origin, v2, v3):
	#a = v2-v_origin
	#b = v3-v_origin
	c = a.cross(b)
	if c.magnitude>0:
		c = c.normalized()
	else:
		raise BaseException("A B C are colinear")
	b2 = c.cross(a).normalized()
	a2 = a.normalized()
	m = Matrix([a2, b2, c]).transposed()
	s = a.magnitude
	m = Matrix.Translation(v_origin) * Matrix.Scale(s,4) * m.to_4x4()
	return m

def getF3cValue(indexCur,indexMax,index50,F3c):
	value = 0.0
	if indexCur<index50:
		value = F3c[0]+(F3c[1]-F3c[0])*(float(indexCur)/max(0.001,index50))
	else:
		value = F3c[1]+(F3c[2]-F3c[1])*(float(indexCur-index50)/max(0.001,indexMax-index50))
	return value

def getVertsPropagations_v02(bm, smoothingLoops, smoothingDist, initialVertsIdx, initialVertsCo):
	propagation_stages = []
	allWalkedVerts = []
	vertsFromIdx = {}
	vertsAddWeight = {}
	checked_verts = copy.copy(initialVertsIdx)
	if smoothingDist > 0:
		kd = mathutils.kdtree.KDTree(len(initialVertsIdx))
		for i, vIdx in enumerate(initialVertsIdx):
			allWalkedVerts.append(vIdx)
			v1 = bm.verts[vIdx]
			v1_co = v1.co
			if vIdx in initialVertsCo:
				v1_co = initialVertsCo[vIdx]
			kd.insert(v1_co, vIdx)
		kd.balance()
		maxDist = abs(smoothingDist)
		stage_verts = []
		for vert in bm.verts:
			if vert.hide == 0 and vert.index not in vertsAddWeight and vert.index not in allWalkedVerts:
				# distance
				f_co,f_idx,f_dst = kd.find(vert.co)
				#f_list = kd.find_n(vert.co,2)
				#if len(f_list)>0:
				#	for f_co,f_idx,f_dst in f_list:
				if f_dst<maxDist:
					if vert.index not in vertsFromIdx:
						vertsFromIdx[vert.index] = []
					vertsFromIdx[vert.index].append(f_idx)
					allWalkedVerts.append(vert.index)
					stage_verts.append(vert.index)
					vertsAddWeight[vert.index] = 1.0-f_dst/maxDist
		propagation_stages.append(stage_verts)
	elif smoothingLoops > 0:
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
	return (propagation_stages, allWalkedVerts, vertsFromIdx, vertsAddWeight)

def updateVertWeight(vg, vIdx, newval, compareOp):
	vg_wmod = 'REPLACE'
	vg_newval = newval
	vg_oldval = 0
	try:
		vg_oldval = vg.weight(idx)
		if compareOp is not None:
			vg_newval = compareOp(vg_oldval,vg_newval)
	except Exception as e:
		vg_wmod = 'ADD'
		vg_newval = newval
	vg.add([vIdx], vg_newval, vg_wmod)
	return vg_oldval

h_cnt = 1
h_pool = "QWERTYUIOPLKJHGFDSAZXCVBNM"
def random_string(length):
	global h_pool
	return ''.join(random.choice(h_pool) for i in range(length))

def getUniqueHash():
	global h_cnt
	h_cnt = h_cnt+1
	return "_"+random_string(2)+str(h_cnt)

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
######################### ######################### #########################
######################### ######################### #########################
class wplsmthdef_snap(bpy.types.Operator):
	bl_idname = "mesh.wplsmthdef_snap"
	bl_label = "Pin mesh state"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(self, context):
		# Check if we have a mesh object active and are in vertex paint mode
		p = context.object and context.object.data and context.object.type == 'MESH'
		return p

	def execute(self, context):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		select_and_change_mode(active_obj, 'EDIT')
		uv_layer_holdr1 = active_mesh.uv_textures.get(kWPLSmoothHolderUVMap1)
		if uv_layer_holdr1 is None:
			active_mesh.uv_textures.new(kWPLSmoothHolderUVMap1)
		uv_layer_holdr2 = active_mesh.uv_textures.get(kWPLSmoothHolderUVMap2)
		if uv_layer_holdr2 is None:
			active_mesh.uv_textures.new(kWPLSmoothHolderUVMap2)
		uv_layer_holdr3 = active_mesh.uv_textures.get(kWPLSmoothHolderUVMap3)
		if uv_layer_holdr3 is None:
			active_mesh.uv_textures.new(kWPLSmoothHolderUVMap3)
		uv_layer_holdr4 = active_mesh.uv_textures.get(kWPLSmoothHolderUVMap4)
		if uv_layer_holdr4 is None:
			active_mesh.uv_textures.new(kWPLSmoothHolderUVMap4)
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		uv_layer_holdr1 = bm.loops.layers.uv.get(kWPLSmoothHolderUVMap1)
		uv_layer_holdr2 = bm.loops.layers.uv.get(kWPLSmoothHolderUVMap2)
		uv_layer_holdr3 = bm.loops.layers.uv.get(kWPLSmoothHolderUVMap3)
		uv_layer_holdr4 = bm.loops.layers.uv.get(kWPLSmoothHolderUVMap4)
		for face in bm.faces:
			for vert, loop in zip(face.verts, face.loops):
				loop[uv_layer_holdr1].uv = (vert.co[0],vert.co[1])
				loop[uv_layer_holdr2].uv = (vert.co[2],vert.normal[0])
				loop[uv_layer_holdr3].uv = (vert.normal[1],vert.normal[2])
				isSelect = 0
				if vert.select:
					isSelect = 1
				isHide = 0
				if vert.hide>0:
					isHide = 1
				loop[uv_layer_holdr4].uv = (isSelect,isHide)
		self.report({'INFO'}, "Mesh state remembered")
		return {'FINISHED'}

class wplsmthdef_snapdel(bpy.types.Operator):
	bl_idname = "mesh.wplsmthdef_snapdel"
	bl_label = "Clear mesh state"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(self, context):
		# Check if we have a mesh object active and are in vertex paint mode
		p = context.object and context.object.data and context.object.type == 'MESH'
		return p

	def execute(self, context):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		select_and_change_mode(active_obj, 'OBJECT')
		uv_layer_holdr1 = active_mesh.uv_textures.get(kWPLSmoothHolderUVMap1)
		if uv_layer_holdr1 is not None:
			active_mesh.uv_textures.remove(uv_layer_holdr1)
		uv_layer_holdr2 = active_mesh.uv_textures.get(kWPLSmoothHolderUVMap2)
		if uv_layer_holdr2 is not None:
			active_mesh.uv_textures.remove(uv_layer_holdr2)
		uv_layer_holdr3 = active_mesh.uv_textures.get(kWPLSmoothHolderUVMap3)
		if uv_layer_holdr3 is not None:
			active_mesh.uv_textures.remove(uv_layer_holdr3)
		uv_layer_holdr4 = active_mesh.uv_textures.get(kWPLSmoothHolderUVMap4)
		if uv_layer_holdr4 is not None:
			active_mesh.uv_textures.remove(uv_layer_holdr4)
		self.report({'INFO'}, "Mesh state cleared")
		return {'FINISHED'}

class wplsmthdef_restcolln(bpy.types.Operator):
	bl_idname = "mesh.wplsmthdef_restcolln"
	bl_label = "Revert to 1st collision"
	bl_options = {'REGISTER', 'UNDO'}
	opt_intplSteps = IntProperty(
			name="Interpolation steps",
			min=1, max=1000,
			default=100,
	)
	opt_onlyContactVerts = BoolProperty(
		name="Contact zone only",
		default=False
	)
	@classmethod
	def poll(self, context):
		# Check if we have a mesh object active and are in vertex paint mode
		p = context.object and context.object.data and context.object.type == 'MESH'
		return p

	def execute(self, context):
		active_obj = context.scene.objects.active
		if active_obj is None or active_obj.data is None:
			self.report({'ERROR'}, "No active object")
			return {'CANCELLED'}
		active_mesh = active_obj.data
		if (active_mesh.uv_textures.get(kWPLSmoothHolderUVMap1) is None) or (active_mesh.uv_textures.get(kWPLSmoothHolderUVMap2) is None):
			self.report({'ERROR'}, "Object not snapped, snap mesh first")
			return {'CANCELLED'}
		selverts = get_selected_vertsIdx(active_mesh)
		if not self.opt_onlyContactVerts and len(selverts) == 0:
			selverts = [e.index for e in active_mesh.vertices]
		if len(selverts) == 0:
			self.report({'ERROR'}, "No verts selected")
			return {'CANCELLED'}

		bvh2collides = get_sceneColldersBVH(active_obj)
		if len(bvh2collides) == 0:
			self.report({'ERROR'}, "Colliders not found: Need objects with collision modifier")
			return {'CANCELLED'}

		select_and_change_mode(active_obj, 'EDIT')
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		verts_snap_map = {}
		verts_snap_nrm_map = {}
		verts_now_map = {}
		uv_layer_holdr1 = bm.loops.layers.uv.get(kWPLSmoothHolderUVMap1)
		uv_layer_holdr2 = bm.loops.layers.uv.get(kWPLSmoothHolderUVMap2)
		uv_layer_holdr3 = bm.loops.layers.uv.get(kWPLSmoothHolderUVMap3)
		for face in bm.faces:
			for vert, loop in zip(face.verts, face.loops):
				verts_now_map[vert.index] = vert.co
				verts_snap_map[vert.index] = mathutils.Vector((loop[uv_layer_holdr1].uv[0], loop[uv_layer_holdr1].uv[1], loop[uv_layer_holdr2].uv[0]))
				verts_snap_nrm_map[vert.index] = mathutils.Vector((loop[uv_layer_holdr2].uv[1], loop[uv_layer_holdr3].uv[0], loop[uv_layer_holdr3].uv[1]))
		inptpl_at = 0.0
		inptpl_at_last_ok = 0.0
		last_contactVerts = []
		for i in range(1, self.opt_intplSteps+1):
			inptpl_at = float(i)/float(self.opt_intplSteps)
			collisions = 0
			for vIdx in selverts:
				step_co = verts_snap_map[vIdx].lerp(verts_now_map[vIdx],inptpl_at)
				step_vec = step_co-verts_now_map[vIdx]
				if step_vec.length > kRaycastEpsilonCCL:
					#print("-- step:",i,[vIdx,step_co,step_vec])
					for bvh_collide in bvh2collides:
						location, normal, index, distance = bvh_collide.ray_cast(step_co, step_vec.normalized(), step_vec.length)
						if location is not None and distance<step_vec.length:
							collisions = collisions+1
							last_contactVerts.append(vIdx)
			if collisions > 0:
				#inptpl_at_last_ok = inptpl_at # test
				print("- step:",i," of ",self.opt_intplSteps,"; collisions:",collisions)
				break
			last_contactVerts = []
			inptpl_at_last_ok = inptpl_at
		verts2update = selverts
		if self.opt_onlyContactVerts:
			verts2update = last_contactVerts
			if self.opt_onlyContactVerts:
				bpy.ops.mesh.select_all(action = 'DESELECT')
				bpy.ops.mesh.select_mode(type='VERT')
				for vIdx in selverts:
					if vIdx not in last_contactVerts:
						v = bm.verts[vIdx]
						v.select = True
				bpy.context.scene.objects.active = bpy.context.scene.objects.active
		for vIdx in verts2update:
			v = bm.verts[vIdx]
			v.co = verts_snap_map[vIdx].lerp(verts_now_map[vIdx],inptpl_at_last_ok)
		bm.normal_update()
		bmesh.update_edit_mesh(active_mesh, True)
		#select_and_change_mode(active_obj, 'OBJECT')
		#if self.opt_onlyContactVerts and len(last_contactVerts) > 0:
		#	for vIdx in last_contactVerts:
		#		v = active_mesh.vertices[vIdx]
		#		v.select = False
		#bpy.context.scene.update()
		#select_and_change_mode(active_obj, 'EDIT')
		self.report({'INFO'}, "Done at: "+str(inptpl_at_last_ok)+" (intersects: "+str(len(last_contactVerts))+", cob: "+str(len(bvh2collides))+")")
		return {'FINISHED'}

class wplsmthdef_restore(bpy.types.Operator):
	bl_idname = "mesh.wplsmthdef_restore"
	bl_label = "Restore selected"
	bl_options = {'REGISTER', 'UNDO'}

	opt_smoothingDist = FloatProperty(
			name="Smoothing Loops",
			min=0.0, max=1000.0,
			default=0.0,
	)
	opt_sloppiness = FloatProperty(
			name="Sloppiness",
			description="Sloppiness",
			min=-10.0, max=10.0,
			default=1.0,
	)
	opt_influence = FloatProperty(
			name="Influence",
			description="Influence",
			min=-10.0, max=10.0,
			default=1.0,
	)
	opt_inverse = BoolProperty(
		name="Inverse influence",
		description="Inverse influence",
		default=False
	)

	@classmethod
	def poll(self, context):
		# Check if we have a mesh object active and are in vertex paint mode
		p = context.object and context.object.data and context.object.type == 'MESH'
		return p

	def execute(self, context):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		if (active_mesh.uv_textures.get(kWPLSmoothHolderUVMap1) is None) or (active_mesh.uv_textures.get(kWPLSmoothHolderUVMap2) is None):
			self.report({'ERROR'}, "Object not snapped, snap mesh first")
			return {'CANCELLED'}
		select_and_change_mode(active_obj, 'EDIT')
		bpy.ops.mesh.select_mode(type='VERT')
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.verts.index_update()
		(selverts,weight) = get_bmselectedVertsIdxWeighted(bm,self.opt_smoothingDist)
		if len(selverts) == 0:
			self.report({'ERROR'}, "No moved/selected verts found")
			return {'CANCELLED'}
		bm.faces.ensure_lookup_table()
		verts_snap_map = {}
		verts_snap_nrm_map = {}
		uv_layer_holdr1 = bm.loops.layers.uv.get(kWPLSmoothHolderUVMap1)
		uv_layer_holdr2 = bm.loops.layers.uv.get(kWPLSmoothHolderUVMap2)
		uv_layer_holdr3 = bm.loops.layers.uv.get(kWPLSmoothHolderUVMap3)
		for face in bm.faces:
			for vert, loop in zip(face.verts, face.loops):
				verts_snap_map[vert.index] = mathutils.Vector((loop[uv_layer_holdr1].uv[0], loop[uv_layer_holdr1].uv[1], loop[uv_layer_holdr2].uv[0]))
				verts_snap_nrm_map[vert.index] = mathutils.Vector((loop[uv_layer_holdr2].uv[1], loop[uv_layer_holdr3].uv[0], loop[uv_layer_holdr3].uv[1]))
		for vIdx in selverts:
			inf = 0
			if abs(weight[vIdx]) > 0.0:
				inf = pow(weight[vIdx],self.opt_sloppiness)*self.opt_influence
			s_v = bm.verts[vIdx]
			if self.opt_inverse == True:
				s_v.co = verts_snap_map[vIdx].lerp(s_v.co,inf)
			else:
				s_v.co = s_v.co.lerp(verts_snap_map[vIdx],inf)
		bm.normal_update()
		bmesh.update_edit_mesh(active_mesh, True)
		return {'FINISHED'}

class wplsmthdef_propagate(bpy.types.Operator):
	bl_idname = "mesh.wplsmthdef_propagate"
	bl_label = "Smooth around selection"
	bl_options = {'REGISTER', 'UNDO'}

	opt_smoothingDist = FloatVectorProperty(
			name="Loops/Distance/Sloppiness",
			min=-1000, max=1000,
			size=3,
			default=(3.0, 0.0, 1.0),
	)
	NormalFac = FloatProperty(
			name="Align to Normal",
			description="Align to Normal",
			min=0.0, max=1.0,
			default=0.0,
	)
	#CollisionDist = FloatProperty(
	#		name="Collision Distance",
	#		description="Collision Distance",
	#		min=0.0, max=100.0,
	#		default=0.0,
	#)
	#CollisionFuzz = FloatProperty(
	#		name="Collision Fuzziness",
	#		description="Collision Fuzziness",
	#		min=-100.0, max=100.0,
	#		default=0.1,
	#)

	@classmethod
	def poll(self, context):
		# Check if we have a mesh object active and are in vertex paint mode
		p = context.object and context.object.data and context.object.type == 'MESH'
		return p

	def execute(self, context):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		#if WPLSMTHDEF_G.mesh_name != active_obj.name:
		if (active_mesh.uv_textures.get(kWPLSmoothHolderUVMap1) is None) or (active_mesh.uv_textures.get(kWPLSmoothHolderUVMap2) is None):
			self.report({'ERROR'}, "Object not snapped, snap mesh first")
			return {'CANCELLED'}
		selverts = get_selected_vertsIdx(active_mesh)
		select_and_change_mode(active_obj, 'EDIT')

		matrix_world = active_obj.matrix_world
		matrix_world_inv = active_obj.matrix_world.inverted()
		matrix_world_nrml = matrix_world_inv.transposed().to_3x3()
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		verts_snap_map = {}
		verts_snap_nrm_map = {}
		uv_layer_holdr1 = bm.loops.layers.uv.get(kWPLSmoothHolderUVMap1)
		uv_layer_holdr2 = bm.loops.layers.uv.get(kWPLSmoothHolderUVMap2)
		uv_layer_holdr3 = bm.loops.layers.uv.get(kWPLSmoothHolderUVMap3)
		for face in bm.faces:
			for vert, loop in zip(face.verts, face.loops):
				verts_snap_map[vert.index] = mathutils.Vector((loop[uv_layer_holdr1].uv[0], loop[uv_layer_holdr1].uv[1], loop[uv_layer_holdr2].uv[0]))
				verts_snap_nrm_map[vert.index] = mathutils.Vector((loop[uv_layer_holdr2].uv[1], loop[uv_layer_holdr3].uv[0], loop[uv_layer_holdr3].uv[1]))
		if len(selverts) == 0:
			selverts = []
			for v in bm.verts:
				if verts_snap_map[v.index] is not None:
					if (v.co-verts_snap_map[v.index]).length > kRaycastEpsilon:
						# vert moved
						selverts.append(v.index)
		if len(selverts) == 0:
			self.report({'ERROR'}, "No moved/selected verts found")
			return {'CANCELLED'}

		(propagationSteps, allWalkedVerts, vertsFromIdx, vertsWeight) = getVertsPropagations_v02(bm, self.opt_smoothingDist[0], self.opt_smoothingDist[1], selverts, verts_snap_map)
		verts_shifts = {}
		for v_idx in allWalkedVerts:
			if (v_idx not in verts_shifts) and (v_idx in verts_snap_map):
				v = bm.verts[v_idx]
				verts_shifts[v_idx] = mathutils.Vector(v.co - verts_snap_map[v_idx])
		new_positions = {}
		#collFuzziness = self.CollisionFuzz
		#collIgnore = [active_obj.name]
		#if collFuzziness<0:
		#	collFuzziness = -1*collfuzz
		#	collIgnore = None
		for stage_verts in propagationSteps:
			for vIdx in stage_verts:
				if vIdx not in verts_snap_nrm_map or vIdx not in verts_snap_map:
					continue
				avg_shift = mathutils.Vector((0,0,0))
				avg_count = 0.0
				from_vIdxes = vertsFromIdx[vIdx]
				for froms_idx in from_vIdxes:
					avg_shift = avg_shift+verts_shifts[froms_idx]
					avg_count = avg_count+1.0
				#print("Vert avg shift", vIdx, avg_shift, avg_count, from_vIdxes)
				if avg_count>0:
					s_shift = mathutils.Vector(avg_shift)/avg_count
					verts_shifts[vIdx] = s_shift
					s_v = bm.verts[vIdx]
					s_v_n = verts_snap_nrm_map[vIdx]
					sn_shift = s_v_n*s_shift.length*math.copysign(1.0,s_v.normal.dot(s_shift))
					total_shift = self.NormalFac*sn_shift + (1.0-self.NormalFac)*s_shift
					vertWeight = 1.0
					if vIdx in vertsWeight:
						vertWeight = pow(vertsWeight[vIdx], self.opt_smoothingDist[2])
					#print("shifting vert", vIdx, vertWeight, s_v.index, s_v.co, verts_snap_map[vIdx])
					s_v_co2 = s_v.co+total_shift*vertWeight
					#if(self.CollisionDist > 0.0):
					#	s_dir_g = (matrix_world_nrml*s_shift.normalized())
					#	s_v_g = matrix_world*s_v.co
					#	min_okdst = (s_shift*vertWeight).length
					#	loc_g, normal = fuzzySceneRayCast_v02(s_v_g, s_dir_g, collFuzziness, 3, collIgnore)
					#	if loc_g is not None:
					#		loc_l = matrix_world_inv * loc_g
					#		hit_dst = (loc_l-s_v.co).length-self.CollisionDist
					#		if hit_dst < min_okdst:
					#			if hit_dst > 0:
					#				s_v_co2 = s_v.co+hit_dst*s_shift.normalized()
					#			else:
					#				s_v_co2 = s_v.co
					new_positions[vIdx] = s_v_co2
		# updating positions as post-step
		for s_idx in new_positions:
			s_v = bm.verts[s_idx]
			#print("New position vert",s_v.co,new_positions[s_idx],(s_v.co-new_positions[s_idx]).length)
			s_v.co = new_positions[s_idx]
		bm.normal_update()
		bmesh.update_edit_mesh(active_mesh, True)
		return {'FINISHED'}

class wpledges_refit_store(bpy.types.Operator):
	bl_idname = "mesh.wpledges_refit_store"
	bl_label = "Refitting: Store target edges"
	bl_options = {'REGISTER', 'UNDO'}

	opt_flowDir = FloatVectorProperty(
		name	 = "Preferred direction",
		size	 = 3,
		min=-1.0, max=1.0,
		default	 = (0.0,0.0,-1.0)
	)

	@classmethod
	def poll(self, context):
		# Check if we have a mesh object active and are in vertex paint mode
		p = context.object and context.object.data and context.object.type == 'MESH'
		return p

	def execute(self, context):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		active_mode = bpy.context.mode
		if active_mode == 'EDIT_MESH':
			active_mode = 'EDIT'
		else:
			active_mode = 'OBJECT'
		vertsIdx = get_selected_vertsIdx(active_mesh)
		edgesIdx = get_selected_edgesIdx(active_mesh)
		if len(edgesIdx)<1:
			self.report({'ERROR'}, "No selected edges found, select some edges first")
			return {'CANCELLED'}

		bpy.ops.object.mode_set( mode = 'EDIT' )
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		(strands_points,strands_radius,strands_vidx) = getBmEdgesAsStrands_v02(bm, vertsIdx, edgesIdx, self.opt_flowDir, 1)
		if strands_points is None:
			self.report({'ERROR'}, "Looped edges found, can`t work on looped edges")
			return {'CANCELLED'}

		g_curvetarg = strandsPoints2globalCurveset(active_obj, bm, strands_points, strands_vidx)
		WPL_G.store[kWPLRefitStoreKey] = g_curvetarg
		bpy.ops.object.mode_set(mode=active_mode)
		self.report({'INFO'}, "Done: curves stored="+str(len(g_curvetarg)))
		return {'FINISHED'}

class wpledges_refit_curve(bpy.types.Operator):
	bl_idname = "curve.wpledges_refit_curve"
	bl_label = "Refitting: Align curve to stored edges"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(self, context):
		# Check if we have a mesh object active
		p = context.object and context.object.data and context.object.type == 'CURVE'
		return p
	def execute(self, context):
		g_curvetarg = []
		if kWPLRefitStoreKey in WPL_G.store:
			g_curvetarg = WPL_G.store[kWPLRefitStoreKey]
		if len(g_curvetarg)<1:
			self.report({'ERROR'}, "No stored edges found, store some edges first")
			return {'CANCELLED'}
		active_obj = context.scene.objects.active
		active_obj_mw = active_obj.matrix_world
		active_obj_mwi = active_obj.matrix_world.inverted()
		curveData = active_obj.data
		if len(curveData.splines)<1:
			return {'CANCELLED'}
		curve_target = g_curvetarg[0]

		# rescaling target to have same edge count as source
		len_trg = 0
		t_xp = []
		t_yp_px = []
		t_yp_py = []
		t_yp_pz = []
		for j, curve_pt in enumerate(curve_target):
			t_xp.append(len_trg)
			t_yp_px.append(curve_pt[0][0])
			t_yp_py.append(curve_pt[0][1])
			t_yp_pz.append(curve_pt[0][2])
			len_trg = len_trg+curve_pt[2].length
		# last point
		#t_xp.append(len_trg)
		#curve_pt = curve_target[-1]
		#t_yp_px.append(curve_pt[0][0]+curve_pt[2][0])
		#t_yp_py.append(curve_pt[0][1]+curve_pt[2][1])
		#t_yp_pz.append(curve_pt[0][2]+curve_pt[2][2])

		polyline = curveData.splines[0]
		len_src = 0
		s_xp = []
		for i,pt in enumerate(polyline.points):
			if i>0:
				ptprev = polyline.points[i-1]
				pt_co = Vector((pt.co[0],pt.co[1],pt.co[2]))
				ptprev_co = Vector((ptprev.co[0],ptprev.co[1],ptprev.co[2]))
				ptdiff_g = (active_obj_mw*pt_co)-(active_obj_mw*ptprev_co)
				len_src = len_src+ptdiff_g.length
				s_xp.append(len_src)
			else:
				s_xp.append(0)
		for i,pt in enumerate(polyline.points):
			t_pos = s_xp[i]*(len_trg/len_src)
			t_yp_g = Vector((np.interp(t_pos, t_xp, t_yp_px),np.interp(t_pos, t_xp, t_yp_py),np.interp(t_pos, t_xp, t_yp_pz)))
			t_yp_l = active_obj_mwi*t_yp_g
			pt.co = Vector((t_yp_l[0],t_yp_l[1],t_yp_l[2],pt.co[3]))
		self.report({'INFO'}, "Done")
		return {'FINISHED'}


class wpledges_refit_clone(bpy.types.Operator):
	bl_idname = "mesh.wpledges_refit_clone"
	bl_label = "Refitting: Clone to stored edges"
	bl_options = {'REGISTER', 'UNDO'}

	opt_flowDir = FloatVectorProperty(
		name	 = "Preferred direction",
		size	 = 3,
		min=-1.0, max=1.0,
		default	 = (0.0,0.0,-1.0)
	)
	opt_actType = EnumProperty(
		name="Action Type", default="CLONE",
		items=(("MOVE", "Move", ""), ("CLONE", "Clone", ""))
	)
	opt_fitType = EnumProperty(
		name="Fit Type", default="FULL",
		items=(("NONE", "None", ""), ("DOWN", "Downscale", ""), ("FULL", "Fit always", ""))
	)
	opt_smoothLevel = IntProperty(
		name="Smoothing level",
		min=1, max=1000,
		default=5,
	)
	opt_UOp = StringProperty(
		name	 = "U=",
		default	 = "U"
	)
	opt_VOp = StringProperty(
		name	 = "V=",
		default	 = "V"
	)
	opt_additionlRot = FloatProperty(
		name	 = "Additional rotation",
		min=-1.0, max=1.0,
		default	 = 0.0
	)
	opt_inverseSrcDir = BoolProperty(
		name="Inverse source",
		default=False
	)
	opt_inverseTrgDir = BoolProperty(
		name="Inverse target",
		default=False
	)
	opt_trgInterval = FloatVectorProperty(
		name="Target interval",
		size=2,
		default=(0.0,1.0)
	)

	@classmethod
	def poll(self, context):
		# Check if we have a mesh object active
		p = context.object and context.object.data and (isinstance(context.scene.objects.active, bpy.types.Object))
		return p

	def execute(self, context):
		g_curvetarg = []
		if kWPLRefitStoreKey in WPL_G.store:
			g_curvetarg = WPL_G.store[kWPLRefitStoreKey]
		if len(g_curvetarg)<1:
			self.report({'ERROR'}, "No stored edges found, store some edges first")
			return {'CANCELLED'}
		UopCode = None
		VopCode = None
		try:
			UopCode = compile(self.opt_UOp, "<string>", "eval")
			VopCode = compile(self.opt_VOp, "<string>", "eval")
		except:
			self.report({'ERROR'}, "UV ops: syntax error")
			return {'CANCELLED'}
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		vertsIdx = get_selected_vertsIdx(active_mesh)
		edgesIdx = get_selected_edgesIdx(active_mesh)
		if len(edgesIdx)<1:
			self.report({'ERROR'}, "No selected edges found, select some edges first")
			return {'CANCELLED'}
		bpy.ops.object.mode_set( mode = 'EDIT' )
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		(strands_points,strands_radius,strands_vidx) = getBmEdgesAsStrands_v02(bm, vertsIdx, edgesIdx, self.opt_flowDir, 1)
		if strands_points is None:
			self.report({'ERROR'}, "Looped edges found, can`t work on looped edges")
			return {'CANCELLED'}
		g_curvebase = strandsPoints2globalCurveset(active_obj, bm, strands_points, strands_vidx)
		source_curve = g_curvebase[0]
		if self.opt_inverseSrcDir:
			source_curve = list(reversed(source_curve))
			for j,curve_pt in enumerate(source_curve):
				source_curve[j] = (curve_pt[0],curve_pt[1],-1*curve_pt[2])
		# Selected vertexes define mesh islands
		duplimesh_verts = []
		for vIdx in vertsIdx:
			addConnectedBmVerts_v02(0, bm, bm.verts[vIdx], duplimesh_verts, None)
		# if True:
		# 	bpy.ops.mesh.select_mode(type='VERT')
		# 	for v in duplimesh_verts:
		# 		v.select = True
		# 	bmesh.update_edit_mesh(active_mesh, True)
		# 	return {'FINISHED'}
		# calculating each vertex position regarding original curvebase (source_curve)
		vertexCoordsInEdgeAxis = {}
		for v in duplimesh_verts:
			g_co = active_obj.matrix_world * v.co
			curve_base_dists = []
			for j,curve_pt in enumerate(source_curve):
				pt_matrix = customAxisMatrix(Vector((0,0,0)),curve_pt[1].normalized(),curve_pt[2].normalized()) #curve_pt[0]
				pt_co = pt_matrix.inverted()*(g_co-curve_pt[0])
				#pt2curve_ang = curve_pt[1].dot((g_co-curve_pt[0]).normalized())
				pt2curve_dist = (g_co-curve_pt[0]).length
				curve_base_dists.append([j, pt_co, curve_pt[2], 1, pt2curve_dist])
			curve_base_dists.sort(key=lambda ia: ia[4], reverse=False)
			curve_base_dists = curve_base_dists[:self.opt_smoothLevel]
			max_dists = 0
			min_dists = 0 #999
			for cbd in curve_base_dists:
				if max_dists < cbd[4]:
					max_dists = cbd[4]
				#if min_dists > cbd[4]:
				#	min_dists = cbd[4]
			if max_dists > 0 and abs(max_dists-min_dists) > 0:
				for cbd in curve_base_dists:
					cbd[3] = 1.0-(cbd[4]-min_dists)/(max_dists-min_dists)
			vertexCoordsInEdgeAxis[v.index] = curve_base_dists

		elems2dupe = []
		if self.opt_actType == 'CLONE':
			# duplicating vertices/edges/faces
			for v in duplimesh_verts:
				#if v not in elems2dupe:
				#	elems2dupe.append(v)
				#for e in v.link_edges:
				#	if e not in elems2dupe:
				#		elems2dupe.append(e)
				for f in v.link_faces:
					if f not in elems2dupe:
						elems2dupe.append(f)
		# applying coord matrices into new coord system
		#curve_target = g_curvetarg[0]
		for curve_target in g_curvetarg:
			vertexSourceCoords = vertexCoordsInEdgeAxis
			vertexSourceVerts = duplimesh_verts
			if len(elems2dupe)>0:
				# duplicating vertices/edges/faces
				dupe_info = bmesh.ops.duplicate(bm,geom=elems2dupe)
				dupe_verts = dupe_info["vert_map"]
				vertexSourceCoords = {}
				vertexSourceVerts = []
				for dup_v in dupe_verts:
					new_v = dup_v
					old_v = dupe_verts[new_v]
					if new_v.index in vertexCoordsInEdgeAxis:
						# need swap
						tmp = new_v
						new_v = old_v
						old_v = tmp
					if old_v is not None and old_v.index in vertexCoordsInEdgeAxis:
						vertexSourceVerts.append(new_v)
						vertexSourceCoords[new_v.index] = vertexCoordsInEdgeAxis[old_v.index]
			trgFrom = max(0.0,min(self.opt_trgInterval[0],self.opt_trgInterval[1]))
			trgTo = min(1.0,max(self.opt_trgInterval[0],self.opt_trgInterval[1]))
			if (trgFrom > 0.0 or trgTo<1.0):
				curve_target_resampled = []
				for i,curve_pt in enumerate(curve_target):
					frc = float(i)/float(len(curve_target)-1)
					if frc >= trgFrom and frc <= trgTo:
						curve_target_resampled.append(curve_pt)
				curve_target = curve_target_resampled
			if self.opt_fitType == 'FULL' or (self.opt_fitType == 'DOWN' and len(curve_target) < len(source_curve)):
				# rescaling target to have same edge count as source
				len_trg = 0
				t_xp = []
				t_yp_px = []
				t_yp_py = []
				t_yp_pz = []
				t_yp_nx = []
				t_yp_ny = []
				t_yp_nz = []
				for j, curve_pt in enumerate(curve_target):
					t_xp.append(len_trg)
					t_yp_px.append(curve_pt[0][0])
					t_yp_py.append(curve_pt[0][1])
					t_yp_pz.append(curve_pt[0][2])
					t_yp_nx.append(curve_pt[1][0])
					t_yp_ny.append(curve_pt[1][1])
					t_yp_nz.append(curve_pt[1][2])
					len_trg = len_trg+curve_pt[2].length
				# last point
				t_xp.append(len_trg)
				curve_pt = curve_target[-1]
				t_yp_px.append(curve_pt[0][0]+curve_pt[2][0])
				t_yp_py.append(curve_pt[0][1]+curve_pt[2][1])
				t_yp_pz.append(curve_pt[0][2]+curve_pt[2][2])
				t_yp_nx.append(curve_pt[1][0])
				t_yp_ny.append(curve_pt[1][1])
				t_yp_nz.append(curve_pt[1][2])

				len_src = 0
				s_xp = []
				for j, curve_pt in enumerate(source_curve):
					s_xp.append(len_src)
					len_src = len_src+curve_pt[2].length
				# last point
				s_xp.append(len_src)

				curve_target_resampled = []
				for j, curve_pt in enumerate(source_curve):
					t_pos = s_xp[j]*(len_trg/len_src)
					t_pos2 = s_xp[j+1]*(len_trg/len_src)
					t_yp_p = Vector((np.interp(t_pos, t_xp, t_yp_px),np.interp(t_pos, t_xp, t_yp_py),np.interp(t_pos, t_xp, t_yp_pz)))
					t_yp_p2 = Vector((np.interp(t_pos2, t_xp, t_yp_px),np.interp(t_pos2, t_xp, t_yp_py),np.interp(t_pos2, t_xp, t_yp_pz)))
					t_yp_n = Vector((np.interp(t_pos, t_xp, t_yp_nx),np.interp(t_pos, t_xp, t_yp_ny),np.interp(t_pos, t_xp, t_yp_nz)))
					curve_pt_resampled = (t_yp_p,t_yp_n.normalized(),t_yp_p2-t_yp_p)
					curve_target_resampled.append(curve_pt_resampled)
				curve_target = curve_target_resampled
			if(self.opt_inverseTrgDir):
				curve_target = list(reversed(curve_target))
				for j,curve_pt in enumerate(curve_target):
					curve_target[j] = (curve_pt[0],curve_pt[1],-1*curve_pt[2])
			for v in vertexSourceVerts:
				g_coords_xyz = []
				g_coords_wei = []
				g_coords_wei_sum = 0
				curve_base_dists = vertexSourceCoords[v.index]
				#max_allowed_wei = 1.0
				for i, cbd in enumerate(curve_base_dists):
					curve_target_idx = cbd[0]
					if curve_target_idx<0 or curve_target_idx>=len(curve_target):
						continue
					curve_base_wei = cbd[3] #*max_allowed_wei
					curve_base_xyz = cbd[1]
					curve_base_flo = cbd[2]
					curve_target_pt = curve_target[curve_target_idx]
					curve_target_flo = curve_target_pt[2]
					#if i == 0:
					#	g_co = curve_target_pt[0]
					pt_matrix = customAxisMatrix(Vector((0,0,0)),curve_target_pt[1].normalized(),curve_target_pt[2].normalized())
					flowScale = curve_target_flo.length / curve_base_flo.length
					T1 = float(curve_target_idx)/len(curve_target)
					T05 = getF3cValue(T1,1,0.5,(0,0.5,1))
					U = curve_base_xyz[0]
					V = curve_base_xyz[2]
					curve_base_xyz[0] = eval(UopCode)
					curve_base_xyz[2] = eval(VopCode)
					pt_target_pt_offset = pt_matrix*(flowScale*curve_base_xyz)
					if abs(self.opt_additionlRot) > 0:
						r_mat_s = Matrix.Rotation(self.opt_additionlRot*math.pi, 4, curve_target_flo)
						pt_target_pt_offset = pt_target_pt_offset * r_mat_s
					g_co_pt = curve_target_pt[0]+pt_target_pt_offset
					#g_co = g_co.lerp(g_co_pt, curve_base_wei)
					g_coords_xyz.append(g_co_pt)
					g_coords_wei.append(curve_base_wei)
					g_coords_wei_sum = g_coords_wei_sum+curve_base_wei
					#max_allowed_wei = max_allowed_wei-curve_base_wei
					#if max_allowed_wei <= 0:
					#	break
				if len(g_coords_xyz)>0 and g_coords_wei_sum>0:
					x = np.average([co[0] for co in g_coords_xyz],weights=g_coords_wei)
					y = np.average([co[1] for co in g_coords_xyz],weights=g_coords_wei)
					z = np.average([co[2] for co in g_coords_xyz],weights=g_coords_wei)
					avg_g_co = Vector((x,y,z))
					v.co = active_obj.matrix_world.inverted() * avg_g_co
			if len(elems2dupe) == 0:
				break
		bm.normal_update()
		bmesh.update_edit_mesh(active_mesh, True)
		self.report({'INFO'}, "Done")
		return {'FINISHED'}


class wplsmthdef_transfer(bpy.types.Operator):
	bl_idname = "mesh.wplsmthdef_transfer"
	bl_label = "Simmetrize/Copy topology"
	bl_options = {'REGISTER', 'UNDO'}
	opt_scale = FloatVectorProperty(
		name	 = "Transfer scale",
		size	 = 3,
		min=-1.0, max=1.0,
		default	 = (-1.0,1.0,1.0)
	)
	opt_smoothingLoops = IntProperty(
			name="Smoothing Loops",
			description="Loops",
			min=0, max=1000,
			default=10,
	)
	opt_sloppiness = FloatProperty(
			name="Sloppiness",
			description="Sloppiness",
			min=-10.0, max=100.0,
			default=100.0,
	)

	@classmethod
	def poll(self, context):
		# Check if we have a mesh object active and are in vertex paint mode
		p = context.object and context.object.data and context.object.type == 'MESH'
		return p

	def execute(self, context):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		select_and_change_mode(active_obj, 'EDIT')
		bm = bmesh.from_edit_mesh(active_mesh)
		selvertsIdx = get_bmhistory_vertsIdx(bm)
		if len(selvertsIdx) < 2:
			self.report({'ERROR'}, "Verts History error: Pick source, then target.")
			return {'CANCELLED'}
		verts_snap_map = {}
		verts_snap_nrm_map = {}
		if (active_mesh.uv_textures.get(kWPLSmoothHolderUVMap1) is not None) and (active_mesh.uv_textures.get(kWPLSmoothHolderUVMap2) is not None) and (active_mesh.uv_textures.get(kWPLSmoothHolderUVMap3) is not None):
			print("Found pinned state, using for reference")
			uv_layer_holdr1 = bm.loops.layers.uv.get(kWPLSmoothHolderUVMap1)
			uv_layer_holdr2 = bm.loops.layers.uv.get(kWPLSmoothHolderUVMap2)
			uv_layer_holdr3 = bm.loops.layers.uv.get(kWPLSmoothHolderUVMap3)
			for face in bm.faces:
				for vert, loop in zip(face.verts, face.loops):
					verts_snap_map[vert.index] = mathutils.Vector((loop[uv_layer_holdr1].uv[0], loop[uv_layer_holdr1].uv[1], loop[uv_layer_holdr2].uv[0]))
					verts_snap_nrm_map[vert.index] = mathutils.Vector((loop[uv_layer_holdr2].uv[1], loop[uv_layer_holdr3].uv[0], loop[uv_layer_holdr3].uv[1]))
		else:
			for vert in bm.verts:
				verts_snap_map[vert.index] = vert.co
				verts_snap_nrm_map[vert.index] = vert.normal
		transfScale = Vector(self.opt_scale)
		refp_origin_v = bm.verts[selvertsIdx[0]]
		refp_target_v = bm.verts[selvertsIdx[1]]
		refp_origin = refp_origin_v.co
		refp_target = refp_target_v.co
		transferred = []
		transferMap = [(refp_origin_v,refp_target_v,Vector((0,0,0)))]
		transferStep = 0
		errs1 = 0
		errs2 = 0
		while len(transferMap)>0:
			#print("transferMap", transferMap, "transferStep", transferStep)
			transferMapNext = []
			for tpr in transferMap:
				vSrc = tpr[0]
				vTrg = tpr[1]
				vSrcOffs = tpr[2]
				vSrc_bCo = verts_snap_map[vSrc.index]
				vTrg_bCo = verts_snap_map[vTrg.index]
				# transferring position
				influence = 0.0
				if(self.opt_sloppiness < 100):
					influence = float(transferStep)/float(self.opt_smoothingLoops)
					influence = pow(influence,self.opt_sloppiness)
				vSrcOffsScaled = Vector((vSrcOffs[0]*transfScale[0],vSrcOffs[1]*transfScale[1],vSrcOffs[2]*transfScale[2]))
				vTrg.co = vTrg.co.lerp(refp_target+vSrcOffsScaled,1.0-influence)
				transferred.append(vSrc.index)
				transferred.append(vTrg.index)
				if transferStep < self.opt_smoothingLoops:
					# moving to next
					srcNxt = []
					for eSrc in vSrc.link_edges:
						vSrc2 = eSrc.other_vert(vSrc)
						if vSrc2.index in transferred or vSrc2.hide > 0:
							continue
						vSrc2_bCo = verts_snap_map[vSrc2.index]
						parentDir = (vSrc2_bCo-vSrc_bCo)
						parentDir = parentDir.normalized()
						srcNxt.append((vSrc2, parentDir))
					trgNxt = []
					trgNxtUsed = []
					# Find nearest end point among target endes for each source edge
					for i,vprSrc in enumerate(srcNxt):
						nearestDst = 9999
						nearestVrt = None
						for eTrg in vTrg.link_edges:
							vTrg2 = eTrg.other_vert(vTrg)
							if vTrg2.index in transferred or vTrg2.hide > 0:
								continue
							vTrg2_bCo = verts_snap_map[vTrg2.index]
							parentDir = (vTrg2_bCo-vTrg_bCo)
							parentDir = Vector((parentDir[0]*transfScale[0],parentDir[1]*transfScale[1],parentDir[2]*transfScale[2]))
							parentDir = parentDir.normalized()
							srcELen = (parentDir-vprSrc[1]).length
							if srcELen < nearestDst: # to avoid miscast on 1-unit distance
								if srcELen < 0.99 or len(trgNxt)-len(srcNxt)<2:
									nearestDst = srcELen
									nearestVrt = vTrg2
						# TBD: other matching means
						if (nearestVrt is not None) and (nearestVrt not in trgNxtUsed):
							trgNxtUsed.append(nearestVrt)
							trgNxt.append((nearestVrt, nearestDst))
						else:
							errs1 = errs1+1
					if len(srcNxt) == len(trgNxt) and len(trgNxt)>0:
						#print("srcNxt", srcNxt)
						#print("trgNxt", trgNxt)
						for i,vprSrc in enumerate(srcNxt):
							vprTrg = trgNxt[i]
							vSrcOffs = vprSrc[0].co-refp_origin
							nextstep = (vprSrc[0],vprTrg[0],vSrcOffs)
							transferMapNext.append(nextstep)
					else:
						errs2 = errs2+1
						# easily on mesh bounds -> just skipping
						#self.report({'ERROR'}, "Stopped at topology difference")
						#transferMapNext = []
			transferMap = transferMapNext
			transferStep = transferStep+1
		bm.normal_update()
		bmesh.update_edit_mesh(active_mesh, True)
		self.report({'INFO'}, "Snapped: "+ str(int(len(transferred)/2))+" in "+str(transferStep)+" steps; Skipped:"+str(errs1)+"/"+str(errs2))
		return {'FINISHED'}


class wplsmthdef_surfalign( bpy.types.Operator ):
	bl_idname = "mesh.wplsmthdef_surfalign"
	bl_label = "Align strip to surf"
	bl_options = {'REGISTER', 'UNDO'}

	opt_singleFromAc = BoolProperty(
		name		= "Use last active vert (if any)",
		default	 = True
	)
	opt_invertNormals = BoolProperty(
		name		= "Invert result",
		default	 = False
	)
	opt_prefDistance = FloatProperty(
		name		= "Keep on distance",
		default	 = 0.0,
		min		 = -100.0,
		max		 = 100.0
	)
	opt_influOri = FloatProperty(
		name		= "Orientation Influence",
		default	 = 1.0,
		min		 = 0,
		max		 = 1
	)

	@classmethod
	def poll( cls, context ):
		return ( context.object is not None  and
				context.object.type == 'MESH' )

	def execute( self, context ):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		selfacesAll = get_selected_facesIdx(active_mesh)
		if len(selfacesAll) == 0:
			self.report({'ERROR'}, "No faces selected")
			return {'FINISHED'}

		bpy.ops.object.mode_set( mode = 'EDIT' )
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.verts.index_update()
		bm.faces.ensure_lookup_table()
		bm.faces.index_update()
		histVertsIdx = get_bmhistory_vertsIdx(bm)
		_singleFromAc = self.opt_singleFromAc
		if len(histVertsIdx) == 0 and _singleFromAc == True:
			print("- No verts in history, switching to face align")
			_singleFromAc = False
			#self.report({'ERROR'}, "No verts in history, select at least 1 vert manually")
			#return {'FINISHED'}

		uv_layer_holdr4 = bm.loops.layers.uv.get(kWPLSmoothHolderUVMap4)
		bufMapFaces = []
		for face in bm.faces:
			if face.index not in bufMapFaces:
				for vert, loop in zip(face.verts, face.loops):
					isVertSel = False
					if loop[uv_layer_holdr4].uv[0]>0:
						isVertSel = True
					if isVertSel and face.index not in bufMapFaces:
						if face.index not in selfacesAll:
							bufMapFaces.append(face.index)
		if len(bufMapFaces) == 0:
			self.report({'ERROR'}, "No surface faces found, pin mesh with selected faces first")
			return {'CANCELLED'}

		bm2 = bmesh.new()
		bm2vmap = {}
		for fIdx in bufMapFaces:
			f = bm.faces[fIdx]
			f_v_set = []
			for vert in f.verts:
				if vert.index not in bm2vmap:
					v = bm2.verts.new(vert.co)
					bm2vmap[vert.index] = v
				f_v_set.append(bm2vmap[vert.index])
			#print("-",f_v_set)
			bm2.faces.new(f_v_set)
		bm2.normal_update()
		bm2bvh = BVHTree.FromBMesh(bm2, epsilon = kRaycastEpsilon)
		glob_center = None
		glob_matRot = None
		glob_shift = None
		if _singleFromAc == True:
			vert0 = bm.verts[histVertsIdx[0]]
			glob_center = vert0.co
			glob_normal = -1*vert0.normal
			if self.opt_invertNormals:
				glob_normal = -1*glob_normal
			# average center and
			#temp_center = Vector((0,0,0))
			#temp_nrm = Vector((0,0,0))
			#temp_cnt = 0
			#for fIdx in selfacesAll:
			#	f = bm.faces[fIdx]
			#	temp_center = temp_center+f.calc_center_median()
			#	temp_nrm = temp_nrm+f.normal
			#	temp_cnt = temp_cnt+1
			#if temp_cnt > 0:
			#glob_center = temp_center/temp_cnt
			#glob_normal = (temp_nrm/temp_cnt).normalized()
			n_loc, n_normal, n_index, n_distance = bm2bvh.find_nearest(glob_center)
			if n_normal is not None:
				face_rotQuat = glob_normal.rotation_difference(n_normal)
				glob_matRot = Matrix.Translation(glob_center) * face_rotQuat.to_matrix().to_4x4() * Matrix.Translation(-glob_center)
				if abs(self.opt_prefDistance)>0.0001:
					bestPos = n_loc+n_normal*self.opt_prefDistance
					glob_shift = bestPos-glob_center

		vertsNewCoord = {}
		for fIdx in selfacesAll:
			f = bm.faces[fIdx]
			f_center = glob_center
			if f_center is None:
				f_center = f.calc_center_median()
			f_matRot = glob_matRot
			f_shift = glob_shift
			if f_matRot is None:
				n_loc, n_normal, n_index, n_distance = bm2bvh.find_nearest(f_center)
				#print("Nears",f_center,n_loc, n_normal, n_index, n_distance)
				if n_normal is not None:
					fnrm = f.normal
					if self.opt_invertNormals:
						fnrm = -1*fnrm
					face_rotQuat = fnrm.rotation_difference(n_normal)
					f_matRot = Matrix.Translation(f_center) * face_rotQuat.to_matrix().to_4x4() * Matrix.Translation(-f_center)
					if abs(self.opt_prefDistance)>0.0001:
						bestPos = n_loc+n_normal*self.opt_prefDistance
						f_shift = bestPos-f_center
			if f_matRot is not None and f_center is not None:
				for v in f.verts:
					vIdx = v.index
					if vIdx not in vertsNewCoord:
						vertsNewCoord[vIdx]=[]
					rotpos = f_matRot*v.co
					if f_shift is not None:
						rotpos = rotpos + f_shift
					vertsNewCoord[vIdx].append(rotpos)

		okCnt = 0
		for vIdx in vertsNewCoord:
			if len(vertsNewCoord[vIdx])>0:
				v = bm.verts[vIdx]
				midSum = Vector((0,0,0))
				midCnt = 0
				for vco in vertsNewCoord[vIdx]:
					midCnt = midCnt+1
					midSum = midSum+vco
				v_co2 = v.co.lerp(midSum/midCnt,self.opt_influOri)
				#print("Shift: "+str((v_co2-v.co).length)+"/"+str(v))
				v.co = v_co2
				okCnt = okCnt+1

		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		bm.normal_update()
		bmesh.update_edit_mesh(active_mesh, True)
		self.report({'INFO'}, "Done, "+str(okCnt)+" verts moved")
		return {'FINISHED'}

######################### ######################### #########################
######################### ######################### #########################
class WPLSmoothDeform_Panel1(bpy.types.Panel):
	bl_label = "Smooth Deforming"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_category = 'WPL'

	def draw_header(self, context):
		layout = self.layout
		layout.label(text="")

	def draw(self, context):
		obj = context.scene.objects.active
		layout = self.layout
		col = layout.column()

		if obj is not None:
			col.separator()
			col.label("Mesh smoothing")
			prow = col.row()
			prow.operator("mesh.wplsmthdef_snap", text="Pin state")
			prow.operator("mesh.wplsmthdef_snapdel", text="Clear")
			col.operator("mesh.wplsmthdef_propagate", text="Smooth around selection")
			op1 = col.operator("mesh.wplsmthdef_restore", text="Restore at bounds")
			op1.opt_smoothingDist = 2
			op1.opt_inverse = False
			op2 = col.operator("mesh.wplsmthdef_restore", text="Restore inside")
			op2.opt_smoothingDist = 2
			op2.opt_inverse = True
			col.operator("mesh.wplsmthdef_restcolln", text="Revert to 1st collision")

			col.separator()
			col.separator()
			col.label("Refitting")
			col.operator("mesh.wpledges_refit_store", text="Store target edges")
			if obj.type == 'CURVE' and obj.data.dimensions == '3D':
				col.operator("curve.wpledges_refit_curve", text="Align curve to stored")
			else:
				col.operator("mesh.wpledges_refit_clone", text="Align to stored edge").opt_actType = 'MOVE'
				col.operator("mesh.wpledges_refit_clone", text="Clone to stored edges").opt_actType = 'CLONE'
			col.separator()
			col.separator()
			col.operator("mesh.wplsmthdef_transfer", text="Simmetrize/Copy topology")
			col.operator("mesh.wplsmthdef_surfalign", text="Align to saved selection")

def register():
	print("WPLSmoothDeform_Panel registered")
	bpy.utils.register_module(__name__)

def unregister():
	bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
	register()
