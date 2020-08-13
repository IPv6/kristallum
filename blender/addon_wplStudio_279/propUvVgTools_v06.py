import math
import copy
import mathutils
import numpy as np
import time
import random

import bpy
from bpy.props import *
import bpy.types
import bmesh
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

bl_info = {
	"name": "Prop UV/VG Tools",
	"author": "IPv6",
	"version": (1, 3, 8),
	"blender": (2, 7, 9),
	"location": "View3D > T-panel > WPL",
	"description" : "",
	"warning"	 : "",
	"wiki_url"	: "",
	"tracker_url" : "",
	"category"	: "WPL"
	}


kWPLRaycastEpsilon = 0.0001
kWPLRaycastDeadzone = 0.0
kWPLUVPrecision = 100000.0
kWPLPalIslUVPostfix = "_pal"
kWPLIslandsVC = "Islands"
kWPLEdgeFlowUV = "Edges"
kWPLEBoneFlowUV = "Bone"
kWPLEdgesMainCam = "zzz_MainCamera"
#kWPLDisplmapRes = 512

kArmBakeIgnoreBns_MB = 'struct,twist,breast,hand,index,clavicle'
kArmBakeIgnoreBns_MLOW = 'breast,hand,shoulder'

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

def strToTokens(sustrParts):
	if sustrParts is None or len(sustrParts) == 0:
		return []
	sustrParts = sustrParts.replace(";",",")
	sustrParts = sustrParts.replace("+",",")
	sustrParts = sustrParts.replace("|",",")
	stringTokens = [x.strip().lower() for x in sustrParts.split(",")]
	return stringTokens
	
def isTokenInStr(toks, nme, defl = True):
	if toks is None or len(toks) == 0 or nme is None or len(nme) == 0:
		return defl
	nmeLower = nme.lower()
	toksList = [x.strip().lower() for x in toks.split(",")]
	for tok in toksList:
		if tok in nmeLower:
			return True
	return False

def get_selected_facesIdx(active_mesh):
	# find selected faces
	bpy.ops.object.mode_set(mode='OBJECT')
	faces = [f.index for f in active_mesh.polygons if f.select]
	# print("selected faces: ", faces)
	return faces

def get_selected_edgesIdx(active_mesh):
	# find selected edges
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
def getVertWeightMap(active_obj, vgname):
	weights = {}
	vgroup = active_obj.vertex_groups.get(vgname)
	if vgroup is not None:
		for index, vert in enumerate(active_obj.data.vertices):
			for group in vert.groups:
				if group.group == vgroup.index:
					weights[index] = group.weight
	return weights

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

def getBmVertRegularDistmap_v01(bme, step_vIdx, limitWalk2verts, vertsPerIslands):
	dots_tree_all = mathutils.kdtree.KDTree(len(step_vIdx))
	for vIdx in step_vIdx:
		v = bme.verts[vIdx]
		dots_tree_all.insert(v.co, vIdx)
	dots_tree_all.balance()
	dots_tree_cache = {}
	vertDistMap = {}
	vertProjMap = {}
	for v in bme.verts:
		if limitWalk2verts is not None and v.index not in limitWalk2verts:
			continue
		dots_tree_cur = dots_tree_all
		if vertsPerIslands is not None:
			vertIslId = -1
			for idx, isl in enumerate(vertsPerIslands):
				if v.index in isl:
					vertIslId = idx
					break
			if vertIslId >= 0:
				if vertIslId not in dots_tree_cache:
					dots_tree_cache[vertIslId] = "???"
					dots_tree_tmp_cnt = 0
					dots_tree_tmp = mathutils.kdtree.KDTree(len(step_vIdx))
					for vIdx in step_vIdx:
						if vIdx not in vertsPerIslands[vertIslId]:
							continue
						v = bme.verts[vIdx]
						dots_tree_tmp.insert(v.co, vIdx)
						dots_tree_tmp_cnt = dots_tree_tmp_cnt+1
					dots_tree_tmp.balance()
					if dots_tree_tmp_cnt > 0:
						dots_tree_cache[vertIslId] = dots_tree_tmp
				if vertIslId in dots_tree_cache:
					if dots_tree_cache[vertIslId] != "???":
						dots_tree_cur = dots_tree_cache[vertIslId]
		v_co_g = v.co
		nearptsEdges = dots_tree_cur.find_n(v_co_g,5)
		if len(nearptsEdges) > 0:
			nearptsEdges.sort(key=lambda itm: itm[2], reverse=False)
			distEdges_min = nearptsEdges[0][2]
			distEdges_max = nearptsEdges[-1][2]
			if abs(distEdges_max-distEdges_min) < 0.0001:
				continue
			nearEdges_v_n_v = []
			nearEdges_wei = []
			for near in nearptsEdges:
				n_co_g = near[0]
				n_idx = near[1]
				n_dist = near[2]
				v_n_v = (n_co_g-v_co_g).length
				v_n_wei = pow((v_n_v - distEdges_min)/(distEdges_max - distEdges_min),2)
				nearEdges_v_n_v.append(v_n_v)
				nearEdges_wei.append(v_n_wei)
			v_n_v = np.average(nearEdges_v_n_v,weights=nearEdges_wei)
			vertDistMap[v.index] = v_n_v
		nearptsSeams = dots_tree_cur.find_n(v.co,2)
		if len(nearptsSeams) > 0:
			nearptsSeams.sort(key=lambda itm: itm[2], reverse=False)
			n1_co_g = nearptsSeams[0][0]
			dst = (n1_co_g-v_co_g).length
			if len(nearptsSeams)>1:
				n2_co_g = nearptsSeams[-1][0]
				n_co_g, dst_perc = mathutils.geometry.intersect_point_line(v_co_g,n1_co_g,n2_co_g)
				dst2 = (n_co_g-v_co_g).length
				if not math.isnan(dst2):
					dst = dst2
				vertProjMap[v.index] = dst
	return vertDistMap, vertProjMap

def splitBmVertsByLinks_v02(bm, selverts, onlySel):
	totalIslands = []
	verts2walk = []
	usedverts = []
	if onlySel:
		for v in bm.verts:
			if v.index not in selverts:
				usedverts.append(v.index)
	if selverts is None:
		selverts = []
		for v in bm.verts:
			selverts.append(v.index)
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

def getActiveBrush(context):
	if context.area.type == 'VIEW_3D' and context.vertex_paint_object:
		brush = context.tool_settings.vertex_paint.brush
	elif context.area.type == 'VIEW_3D' and context.image_paint_object:
		brush = context.tool_settings.image_paint.brush
	elif context.area.type == 'IMAGE_EDITOR' and  context.space_data.mode == 'PAINT':
		brush = context.tool_settings.image_paint.brush
	else :
		brush = None
	return brush

def setActiveBrushColor(context, newcol):
	uvvgtoolsOpts = context.scene.uvvgtoolsOpts
	uvvgtoolsOpts.bake_vc_col = (newcol[0],newcol[1],newcol[2])
	try:
		wplEdgeBuildProps = context.scene.wplEdgeBuildProps
		wplEdgeBuildProps.opt_edgeCol = uvvgtoolsOpts.bake_vc_col
	except:
		pass
	br = getActiveBrush(context)
	if br:
		br.color = mathutils.Vector((newcol[0],newcol[1],newcol[2]))

def get_isLocalView():
	is_local_view = sum(bpy.context.space_data.layers[:]) == 0 #if hairCurve.layers_local_view[0]:
	return is_local_view

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

########### ############ ########### ############ ########### ############ ########### ############
########### ############ ########### ############ ########### ############ ########### ############
class wpluvvg_unwrap_bonenrm(bpy.types.Operator):
	bl_idname = "object.wpluvvg_unwrap_bonenrm"
	bl_label = "UV: Add bonenormals"
	bl_options = {'REGISTER', 'UNDO'}

	opt_uvPrefx = StringProperty(
		name = "Name base",
		default = kWPLEBoneFlowUV
	)
	opt_bones2skip = StringProperty(
		name = "UV: bones to ignore",
		default = ""
	)

	@classmethod
	def poll(self, context):
		# Check if we have a mesh object active
		return True

	def execute(self, context):
		if get_isLocalView():
			self.report({'ERROR'}, "Can`t work in Local view")
			return {'CANCELLED'}
		active_obj0 = context.scene.objects.active
		opt_skipBones = self.opt_bones2skip
		if len(opt_skipBones) == 0:
			opt_skipBones = select_by_arm(active_obj0, kArmBakeIgnoreBns_MB, kArmBakeIgnoreBns_MLOW, "") 
		selobj_all = [o for o in bpy.context.selected_objects]
		if len(selobj_all) == 0:
			# just nothing
			return {'FINISHED'}
		camera_obj = context.scene.objects.get(kWPLEdgesMainCam)
		if camera_obj is None:
			self.report({'ERROR'}, "Camera not found: "+kWPLEdgesMainCam)
			return {'CANCELLED'}
		camera_gCo = camera_obj.matrix_world.to_translation() #camera_obj.location
		camera_gDir = camera_obj.matrix_world.to_3x3()*Vector((0.0, 0.0, 1.0))
		camera_gOrtho = False
		if camera_obj.data.type == 'ORTHO':
			camera_gOrtho = True
		bone_parlens_cache = {}
		def get_bone_parlen(armatr, bn_name):
			if bn_name in bone_parlens_cache:
				return bone_parlens_cache[bn_name]
			pblen = 0
			pb = armatr.pose.bones[bn_name]
			if pb.parent is not None:
				arm_mw = armatr.matrix_world
				pb1 = armatr.pose.bones[pb.parent.name]
				pb1_head_g = arm_mw*pb1.head
				pb1_tail_g = arm_mw*pb1.tail
				pblen = pblen+(pb1_head_g-pb1_tail_g).length
				if pb.parent.parent is not None:
					pblen = pblen + get_bone_parlen(armatr, pb.parent.parent.name)
			bone_parlens_cache[bn_name] = pblen
			return pblen
				
		vertsOk = 0
		vertsNotOk = 0
		isArmatr0Hide = False
		armatr = get_related_arma(active_obj0)
		if armatr is not None:
			isArmatr0Hide = armatr.hide
		for active_obj in selobj_all:
			armatr = get_related_arma(active_obj)
			if armatr is None or active_obj.type != 'MESH':
				continue
			print("- updating bone normals for", active_obj.name)
			active_mesh = active_obj.data
			select_and_change_mode(armatr,"POSE")
			boneNames = armatr.pose.bones.keys()
			bpy.ops.pose.visual_transform_apply()
			arm_mw = armatr.matrix_world
			ao_mw = active_obj.matrix_world
			ao_mw_nrm_g = active_obj.matrix_world.inverted().transposed().to_3x3()
			#matrix_world_inv = active_obj.matrix_world.inverted()
			verts_new_datal = {}
			actbonesOk = []
			virtVGs = [] # bone parenting
			nexrPare = active_obj.parent
			while nexrPare is not None:
				if nexrPare.constraints is not None:
					for constr in nexrPare.constraints:
						if constr.type == 'COPY_TRANSFORMS':
							if len(constr.subtarget) > 0:
								virtVGs.append(constr.subtarget)
				if len(nexrPare.parent_bone) > 0:
					virtVGs.append(nexrPare.parent_bone)
				nexrPare = nexrPare.parent
			#print(" - virtVGs", virtVGs)
			for bn_name in boneNames:
				if (bn_name in active_obj.vertex_groups) or (bn_name in virtVGs):
					pb = armatr.pose.bones[bn_name]
					# mw = armatr.convert_space(pose_bone=pb, # ??? not working
					# 	matrix=pb.matrix, 
					# 	from_space='POSE', 
					# 	to_space='WORLD')
					head_g = arm_mw*pb.head
					tail_g = arm_mw*pb.tail
					camDir = camera_gDir
					if camera_gOrtho == False:
						pb_center = tail_g #(head_g-tail_g)*0.5
						if (head_g-camera_gCo).length < (tail_g-camera_gCo).length:
							pb_center = head_g
						camDir = (pb_center-camera_gCo).normalized()
					perp1 = (head_g-tail_g).cross(camDir)
					perp2 = (head_g-tail_g).cross(perp1)
					perp2 = perp2.normalized()
					if perp2.dot(camDir) < 0:
						perp2 = -1*perp2
					pb_rot = perp2.rotation_difference(camDir)
					pb_rot_mat = pb_rot.to_matrix().to_4x4()
					bone_verts = []
					bone_verts_gen = []
					if (bn_name in virtVGs):
						for v in active_obj.data.vertices:
							bone_verts_gen.append( (v, 1.0) )
					else:
						allVgVertsCo, allVgVertsIdx, allVgVertsW = get_vertgroup_verts(active_obj, active_obj.vertex_groups[bn_name], 0.001)
						for i, vIdx in enumerate(allVgVertsIdx):
							bone_verts_gen.append( (active_obj.data.vertices[vIdx], allVgVertsW[i]) )
					avg_bn_dst = 0.0
					avg_bn_dst_cnt = 0.0
					for item in bone_verts_gen:
						bone_verts.append(item)
						v = item[0]
						v_co_g = ao_mw * v.co
						v2bn_projpair = mathutils.geometry.intersect_point_line(v_co_g, head_g, tail_g)
						avg_bn_dst = avg_bn_dst+v2bn_projpair[1]
						avg_bn_dst_cnt = avg_bn_dst_cnt+1.0
					if avg_bn_dst_cnt < 1.0:
						continue
					bone_scale = 1.0
					if isTokenInStr(opt_skipBones, bn_name, False):
						#print(" - skip:", bn_name, opt_skipBones)
						bone_scale = 0.0000001
					else:
						actbonesOk.append(bn_name)
					avg_bn_dst = avg_bn_dst/avg_bn_dst_cnt
					#print(" - used:", pb.name, len(bone_verts), avg_bn_dst)
					for item in bone_verts:
						v = item[0]
						v_wei = item[1]
						v_nrm_g = ao_mw_nrm_g * v.normal
						v_nrm_g2 = pb_rot_mat * v_nrm_g
						v_co_g = ao_mw * v.co
						v2bn_projpair = mathutils.geometry.intersect_point_line(v_co_g, head_g, tail_g)
						#print("- v2bn_projpair", v2bn_projpair)
						buv_wei = v_wei * bone_scale
						v2bn_u = get_bone_parlen(armatr, bn_name) + (v2bn_projpair[0]-head_g).length * math.copysign(1.0,v2bn_projpair[1])
						v2bn_v_axis = -1*pb.z_axis #pb.x_axis
						v2bn_v_dot = v2bn_v_axis.dot( (v.co - ao_mw.inverted() * v2bn_projpair[0]).normalized() )
						v2bn_v = math.acos(max(min(v2bn_v_dot,1.0),-1.0))
						if v.index not in verts_new_datal:
							verts_new_datal[v.index] = []
						verts_new_datal[v.index].append( [ (v_wei, v_nrm_g2), (buv_wei, v2bn_u, v2bn_v) ] )
			print("- bones used", len(actbonesOk), actbonesOk)
			select_and_change_mode(armatr,"OBJECT")
			verts_nrm = {}
			verts_buv = {}
			if len(verts_new_datal) > 0:
				for vIdx, vert_list in verts_new_datal.items():
					nx = np.average([itm[0][1][0] for itm in vert_list],weights=[itm[0][0] for itm in vert_list])
					ny = np.average([itm[0][1][1] for itm in vert_list],weights=[itm[0][0] for itm in vert_list])
					nz = np.average([itm[0][1][2] for itm in vert_list],weights=[itm[0][0] for itm in vert_list])
					uv_u = np.average([itm[1][1] for itm in vert_list],weights=[itm[1][0] for itm in vert_list])
					uv_v = np.average([itm[1][2] for itm in vert_list],weights=[itm[1][0] for itm in vert_list])
					avg_n_co = Vector((nx,ny,nz)).normalized()
					verts_nrm[vIdx] = avg_n_co
					verts_buv[vIdx] = (uv_u, uv_v)
			else:
				# default normal
				for v in active_mesh.vertices:
					v_nrm_g = ao_mw_nrm_g * v.normal
					verts_nrm[v.index] = v_nrm_g
			uv_layer1_nm = self.opt_uvPrefx+"_nrmXY"
			uv_layer1_ob = active_mesh.uv_textures.get(uv_layer1_nm)
			if uv_layer1_ob is None:
				active_mesh.uv_textures.new(uv_layer1_nm)
			uv_layer2_nm = self.opt_uvPrefx+"_nrmZD"
			uv_layer2_ob = active_mesh.uv_textures.get(uv_layer2_nm)
			if uv_layer2_ob is None:
				active_mesh.uv_textures.new(uv_layer2_nm)
			uv_layer3_nm = self.opt_uvPrefx+"_nrmUV"
			uv_layer3_ob = active_mesh.uv_textures.get(uv_layer3_nm)
			if uv_layer3_ob is None:
				active_mesh.uv_textures.new(uv_layer3_nm)
			select_and_change_mode(active_obj,"EDIT")
			bm = bmesh.from_edit_mesh(active_mesh)
			bm.verts.ensure_lookup_table()
			bm.faces.ensure_lookup_table()
			bm.verts.index_update()
			for vert in bm.verts:
				vert.select = False
			# distance from camera to island closest vert
			#camera_lCo = matrix_world_inv * camera_gCo
			islandPerVert = {}
			distPerIsland = {}
			islandId = 0.0
			selVertsIslandsed = splitBmVertsByLinks_v02(bm, None, False)
			for meshlist in selVertsIslandsed:
				if len(meshlist)>0:
					islandId = islandId+1.0
					for vidx in meshlist:
						islandPerVert[vidx] = islandId
					if islandId not in distPerIsland:
						distPerIsland[islandId] = 0.0
					v_co_g = active_obj.matrix_world*v.co # we need depth in GLOBAL coords, not local
					zdepth = (camera_gCo-v_co_g).length
					if zdepth < distPerIsland[islandId] or distPerIsland[islandId] < 0.01:
						distPerIsland[islandId] = zdepth
			print("- z-depths:", distPerIsland)
			uv_layer1_ob = bm.loops.layers.uv.get(uv_layer1_nm)
			uv_layer2_ob = bm.loops.layers.uv.get(uv_layer2_nm)
			uv_layer3_ob = bm.loops.layers.uv.get(uv_layer3_nm)
			for face in bm.faces:
				for loop in face.loops:
					vert = loop.vert
					if (vert.index not in verts_nrm):
						#print("- bonevert NOT FOUND", vert.index)
						vert.select = True
						# trying to get average from nears
						avg_sum = Vector((0,0,0))
						avg_cnt = 0
						for e in vert.link_edges:
							vert2 = e.other_vert(vert)
							if vert2.index in verts_nrm:
								avg_sum = avg_sum+verts_nrm[vert2.index]
								avg_cnt = avg_cnt+1
						if avg_cnt>0:
							verts_nrm[vert.index] = avg_sum/avg_cnt
						else:
							vertsNotOk = vertsNotOk+1
							v_nrm_g = ao_mw_nrm_g * vert.normal
							verts_nrm[vert.index] = v_nrm_g
						verts_buv[vert.index] = (0.0, 0.0)
					if (vert.index in verts_nrm):
						new_n = verts_nrm[vert.index]
						new_buv = (0.0, 0.0)
						if vert.index in verts_buv:
							new_buv = verts_buv[vert.index]
						vdepth = 0.0
						if vert.index in islandPerVert:
							islandId = islandPerVert[vert.index]
							vdepth = distPerIsland[islandId]
						loop[uv_layer1_ob].uv = (new_n[0], new_n[1])
						loop[uv_layer2_ob].uv = (new_n[2], vdepth)
						loop[uv_layer3_ob].uv = (new_buv[0], new_buv[1])
						vertsOk = vertsOk+1
			bmesh.update_edit_mesh(active_mesh)
			select_and_change_mode(active_obj,"OBJECT")
			print("- done, verts: ", len(verts_nrm))
		if active_obj0 is not None:
			if isArmatr0Hide:
				armatr = get_related_arma(active_obj0)
				armatr.hide = True
			select_and_change_mode(active_obj0,"OBJECT")
		if armatr is not None:
			self.report({'INFO'}, "Bone normals: arma "+ armatr.name+", objs:"+str(len(selobj_all))+", verts "+str(vertsOk)+", problemVerts "+str(vertsNotOk))
		context.scene.update()
		return {'FINISHED'}

class wpluvvg_unwrap_edges(bpy.types.Operator):
	bl_idname = "object.wpluvvg_unwrap_edges"
	bl_label = "UV: Unwrap from edges"
	bl_options = {'REGISTER', 'UNDO'}

	opt_tranfType = bpy.props.EnumProperty(
		name="Unwrap type", default="GRD",
		items=(("GRD", "Grid", ""), ("DST_AVG", "DistanceAVG", ""), ("DST_PRJ", "DistancePRJ", ""))
	)
	opt_uvPrefx = StringProperty(
		name = "UV Name",
		default = kWPLEdgeFlowUV
	)
	# opt_onlySelection = BoolProperty(
	# 	name="Only Selected",
	# 	default=False
	# )
	vgSeedU = StringProperty(
		name = "U-Seed (vg posfix)",
		default = "_sel1"
	)
	vgSeedV = StringProperty(
		name = "V-Seed (vg posfix)",
		default = "_sel2"
	)
	opt_minValue = FloatProperty(
		name="Min. value",
		min=0.0001, max=999.0,
		default=0.0001
	)

	@classmethod
	def poll(self, context):
		# Check if we have a mesh object active
		p = context.object and context.object.data and (isinstance(context.scene.objects.active, bpy.types.Object) and isinstance(context.scene.objects.active.data, bpy.types.Mesh))
		return p

	def execute(self, context):
		active_obj = context.scene.objects.active
		if active_obj is None or active_obj.type != 'MESH':
			# just nothing
			return {'FINISHED'}
		#if active_obj is None or modfGetByType(active_obj,'MIRROR'):
		#	self.report({'INFO'}, 'Object not ready (has Mirror)')
		#	return {"CANCELLED"}
		bakemap_pref = self.opt_uvPrefx
		active_mesh = active_obj.data
		uv_layer_ob = active_mesh.uv_textures.get(bakemap_pref)
		if uv_layer_ob is None:
			active_mesh.uv_textures.new(bakemap_pref)
		bpy.ops.object.mode_set( mode = 'EDIT' )
		bm = bmesh.from_edit_mesh( active_mesh )
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		vmapU = None
		vmapUvg = get_vertgroup_by_name(active_obj, bakemap_pref+self.vgSeedU)
		if vmapUvg is None:
			vmapUvg = get_vertgroup_by_name(active_obj, self.vgSeedU)
		if vmapUvg is not None:
			vmapU = getVertWeightMap(active_obj, vmapUvg.name)
			print("- using",vmapUvg.name,len(vmapU))
		vmapV = None
		vmapVvg = get_vertgroup_by_name(active_obj, bakemap_pref+self.vgSeedV)
		if vmapVvg is None:
			vmapVvg = get_vertgroup_by_name(active_obj, self.vgSeedV)
		if vmapVvg is not None:
			vmapV = getVertWeightMap(active_obj, vmapVvg.name)
			print("- using",vmapVvg.name,len(vmapV))
		#selverts = []
		bndverts = []
		seamverts = []
		shrverts = []
		stepU_vIdx = []
		stepV_vIdx = []
		for v in bm.verts:
			#if v.select:
			#	selverts.append(v.index)
			if v.is_boundary:
				bndverts.append(v.index)
			for e in v.link_edges:
				if e.seam and (v.index not in seamverts):
					seamverts.append(v.index)
				if e.calc_face_angle(999) > 1.5 and (v.index not in shrverts):
					shrverts.append(v.index)
			if vmapU is not None:
				if v.index in vmapU and vmapU[v.index] > 0:
					stepU_vIdx.append(v.index)
			if vmapV is not None:
				if v.index in vmapV and vmapV[v.index] > 0:
					stepV_vIdx.append(v.index)
		if len(stepU_vIdx) == 0:
			stepU_vIdx = bndverts
		if len(stepV_vIdx) == 0:
			stepV_vIdx = seamverts
		if len(stepV_vIdx) == 0:
			stepV_vIdx = shrverts
		# DEBUG
		# for vIdx in stepV_vIdx:
		# 	v = bm.verts[vIdx]
		# 	v.select = True
		if len(stepU_vIdx) == 0 and len(stepV_vIdx) > 0:
			stepU_vIdx = stepV_vIdx
		if len(stepU_vIdx) == 0 or len(stepV_vIdx) == 0:
			self.report({'ERROR'}, "No seed verts (bounds+seams) found")
			return {'FINISHED'}
		print("seedU",len(stepU_vIdx),"seedV",len(stepV_vIdx))
		walkLimit = None
		#if self.opt_onlySelection:
		#	walkLimit = selverts
		vertDistMapU = None
		vertDistMapV = None
		if self.opt_tranfType == 'GRD':
			vertDistMapU, _, _ = getBmVertGeodesicDistmap_v05(bm, stepU_vIdx, 100, None, True, False, walkLimit)
			vertDistMapV, _, _ = getBmVertGeodesicDistmap_v05(bm, stepV_vIdx, 100, None, True, False, walkLimit)
		else:
			vertsPerIslands = splitBmVertsByLinks_v02(bm, None, False)
			vertDistMapU, vertProjMapU = getBmVertRegularDistmap_v01(bm, stepU_vIdx, walkLimit, vertsPerIslands)
			vertDistMapV, vertProjMapV = getBmVertRegularDistmap_v01(bm, stepV_vIdx, walkLimit, vertsPerIslands)
			if self.opt_tranfType == 'DST_PRJ':
				vertDistMapU = vertProjMapU
				vertDistMapV = vertProjMapV
		uv_layer_ob = bm.loops.layers.uv.get(bakemap_pref)
		uv_dups_checkmap = {}
		for face in bm.faces:
			for loop in face.loops:
				vert = loop.vert
				vU = 0
				vV = 0
				if (vert.index in vertDistMapU):
					vU = vertDistMapU[vert.index]
				if (vert.index in vertDistMapV):
					vV = vertDistMapV[vert.index]
				loopU = self.opt_minValue+vU
				loopV = self.opt_minValue+vV
				loop[uv_layer_ob].uv = (loopU, loopV)
				kk = str(int(loopU*kWPLUVPrecision))+"_"+str(int(loopV*kWPLUVPrecision))
				if kk not in uv_dups_checkmap:
					uv_dups_checkmap[kk] = []
				if vert.index not in uv_dups_checkmap[kk]:
					uv_dups_checkmap[kk].append(vert.index)
		uv_dups = 0
		for kk in uv_dups_checkmap:
			if len(uv_dups_checkmap[kk]) >= 2:
				uv_dups = uv_dups+1
				#print("- UV duplication found", kk, uv_dups_checkmap[kk])
				for vIdx in uv_dups_checkmap[kk]:
					v = bm.verts[vIdx]
					v.select = True
		bmesh.update_edit_mesh(active_mesh)
		bpy.ops.object.mode_set( mode = 'OBJECT' )
		self.report({'INFO'}, "Vertices baked:" + str(len(vertDistMapU)) + "/" + str(len(vertDistMapV))+", dups:"+str(uv_dups))
		context.scene.update()
		return {'FINISHED'}

# class wpluvvg_normalize_uv(bpy.types.Operator):
# 	bl_idname = "object.wpluvvg_normalize_uv"
# 	bl_label = "UV: Normalize UVs"
# 	bl_options = {'REGISTER', 'UNDO'}

# 	EvalUV = StringProperty(
# 		name = "UV=",
# 		default = "(U, V) #( (U-0.5)*0.045, (V-0.5)*AZX*0.045 )"
# 	)

# 	opt_swapUV = BoolProperty(
# 		name="Swap UV",
# 		default=False,
# 	)

# 	@classmethod
# 	def poll(self, context):
# 		# Check if we have a mesh object active
# 		p = context.object and context.object.data and (isinstance(context.scene.objects.active, bpy.types.Object) and isinstance(context.scene.objects.active.data, bpy.types.Mesh))
# 		return p

# 	def execute(self, context):
# 		uvvgtoolsOpts = context.scene.uvvgtoolsOpts
# 		active_obj = context.scene.objects.active
# 		active_mesh = active_obj.data
# 		oldmode = select_and_change_mode(active_obj,'OBJECT')
# 		selverts = get_selected_vertsIdx(active_mesh)
# 		selfaces = get_selected_facesIdx(active_mesh)
# 		if len(selverts) == 0 or len(selfaces) == 0:
# 			self.report({'ERROR'}, "No verts selected, select some verts first")
# 			return {'FINISHED'}
# 		EvalUV_py = None
# 		try:
# 			EvalUV_py = compile(self.EvalUV, "<string>", "eval")
# 		except:
# 			self.report({'ERROR'}, "Eval compilation: syntax error")
# 			return {'CANCELLED'}
# 		bakemap_pref = uvvgtoolsOpts.bake_uvbase
# 		uv_layer_ob = active_mesh.uv_textures.get(bakemap_pref)
# 		if uv_layer_ob is None:
# 			active_mesh.uv_textures.new(bakemap_pref)

# 		uv_vals = {}
# 		bm = bmesh.new()
# 		bm.from_mesh(active_mesh)
# 		bm.verts.ensure_lookup_table()
# 		bm.faces.ensure_lookup_table()
# 		bm.verts.index_update()
# 		uv_layer_ob = bm.loops.layers.uv.get(bakemap_pref)
# 		xyz_nmin = [9999,9999,9999]
# 		xyz_nmax = [-9999,-9999,-9999]
# 		for face in bm.faces:
# 			if face.index not in selfaces:
# 				continue
# 			for loop in face.loops:
# 				vert = loop.vert
# 				if (vert.index in selverts):
# 					if vert.index not in uv_vals:
# 						uv_vals[vert.index] = [-9999,-9999]
# 					uv_vals[vert.index] = [max(uv_vals[vert.index][0],loop[uv_layer_ob].uv[0]),max(uv_vals[vert.index][1],loop[uv_layer_ob].uv[1])]
# 					xyz_nmin = [min(xyz_nmin[0],vert.co[0]),min(xyz_nmin[1],vert.co[1]),min(xyz_nmin[2],vert.co[2])]
# 					xyz_nmax = [max(xyz_nmax[0],vert.co[0]),max(xyz_nmax[1],vert.co[1]),max(xyz_nmax[2],vert.co[2])]
# 		uv_islanmin = [9999,9999]
# 		uv_islanmax = [-9999,-9999]
# 		nrm0 = 0.0
# 		nrm1 = 1.0
# 		for vIdx in uv_vals:
# 			uv_islanmin[0] = min(uv_vals[vIdx][0],uv_islanmin[0])
# 			uv_islanmin[1] = min(uv_vals[vIdx][1],uv_islanmin[1])
# 			uv_islanmax[0] = max(uv_vals[vIdx][0],uv_islanmax[0])
# 			uv_islanmax[1] = max(uv_vals[vIdx][1],uv_islanmax[1])
# 		if abs(uv_islanmax[0]-uv_islanmin[0])>0.0001 and abs(uv_islanmax[1]-uv_islanmin[1])>0.0001:
# 			for vIdx in uv_vals:
# 				facU = (uv_vals[vIdx][0]-uv_islanmin[0])/(uv_islanmax[0]-uv_islanmin[0])
# 				facV = (uv_vals[vIdx][1]-uv_islanmin[1])/(uv_islanmax[1]-uv_islanmin[1])
# 				uv_vals[vIdx][0] = nrm0+facU*(nrm1-nrm0)
# 				uv_vals[vIdx][1] = nrm0+facV*(nrm1-nrm0)
# 		else:
# 			self.report({'ERROR'}, "Normalize skipped, same dimenstions")
# 			return {'FINISHED'}
# 		if self.opt_swapUV:
# 			for vIdx in uv_vals:
# 				uv_vals[vIdx] = [uv_vals[vIdx][1],uv_vals[vIdx][0]]
# 		#AYX = (xyz_nmax[1]-xyz_nmin[1])/(xyz_nmax[0]-xyz_nmin[0])
# 		#AZX = (xyz_nmax[2]-xyz_nmin[2])/(xyz_nmax[0]-xyz_nmin[0])
# 		#AZY = (xyz_nmax[2]-xyz_nmin[2])/(xyz_nmax[1]-xyz_nmin[1])
# 		for vIdx in uv_vals:
# 			U = uv_vals[vIdx][0]
# 			V = uv_vals[vIdx][1]
# 			newUV = eval(EvalUV_py)
# 			uv_vals[vIdx] = [newUV[0],newUV[1]]
# 		for face in bm.faces:
# 			if face.index not in selfaces:
# 				continue
# 			for loop in face.loops:
# 				vert = loop.vert
# 				if (vert.index in uv_vals):
# 					loop[uv_layer_ob].uv = (uv_vals[vert.index][0],uv_vals[vert.index][1])
# 		bm.to_mesh(active_mesh)
# 		bm.free()
# 		self.report({'INFO'}, "Vertices baked:" + str(len(uv_vals)))
# 		select_and_change_mode(active_obj,oldmode)
# 		context.scene.update()
# 		return {'FINISHED'}

# class wpluvvg_unwrap_uv(bpy.types.Operator):
# 	bl_idname = "object.wpluvvg_unwrap_uv"
# 	bl_label = "UV: basic unwrap"
# 	bl_options = {'REGISTER', 'UNDO'}

# 	opt_unwrType = bpy.props.EnumProperty(
# 		name="Unwrap type", default="BASIC",
# 		items=(("BASIC", "Basic", ""), ("PROJ", "From view", ""))
# 	)

# 	@classmethod
# 	def poll(self, context):
# 		# Check if we have a mesh object active
# 		p = context.object and context.object.data and (isinstance(context.scene.objects.active, bpy.types.Object) and isinstance(context.scene.objects.active.data, bpy.types.Mesh))
# 		return p

# 	def execute(self, context):
# 		uvvgtoolsOpts = context.scene.uvvgtoolsOpts
# 		active_obj = context.scene.objects.active
# 		if active_obj is None or modfGetByType(active_obj,'MIRROR'):
# 			self.report({'INFO'}, 'Object not ready (has Mirror)')
# 			return {"CANCELLED"}
# 		active_mesh = active_obj.data
# 		bakemap_pref = uvvgtoolsOpts.bake_uvbase
# 		uv_layer_ob = active_mesh.uv_textures.get(bakemap_pref)
# 		if uv_layer_ob is None:
# 			active_mesh.uv_textures.new(bakemap_pref)
# 			uv_layer_ob = active_mesh.uv_textures.get(bakemap_pref)
# 		uv_layer_ob.active = True
# 		bpy.ops.object.mode_set(mode='EDIT')
# 		if self.opt_unwrType == 'PROJ':
# 			bpy.ops.uv.project_from_view(camera_bounds=False, correct_aspect=True, scale_to_bounds=False)
# 		if self.opt_unwrType == 'BASIC':
# 			bpy.ops.uv.unwrap()
# 		return {'FINISHED'}

# class wpluvvg_unwrap_islc(bpy.types.Operator):
# 	bl_idname = "object.wpluvvg_unwrap_islc"
# 	bl_label = "Bake island centers"
# 	bl_options = {'REGISTER', 'UNDO'}

# 	opt_uvPrefx = StringProperty(
# 		name = "UV Name",
# 		default = kWPLEdgeFlowUV
# 	)
	
# 	@classmethod
# 	def poll(self, context):
# 		p = context.object and context.object.data and (isinstance(context.scene.objects.active, bpy.types.Object) and isinstance(context.scene.objects.active.data, bpy.types.Mesh))
# 		return p

# 	def execute(self, context):
# 		active_obj = context.scene.objects.active
# 		if active_obj is None:
# 			self.report({'ERROR'}, "No active object found")
# 			return {'CANCELLED'}
# 		active_mesh = active_obj.data

# 		bakemap_pref = self.opt_uvPrefx
# 		bakemap_prefX = bakemap_pref+"_cX"
# 		bakemap_prefY = bakemap_pref+"_cY"
# 		bakemap_prefZ = bakemap_pref+"_cZ"
# 		uv_layer_obX = active_mesh.uv_textures.get(bakemap_prefX)
# 		if uv_layer_obX is None:
# 			active_mesh.uv_textures.new(bakemap_prefX)
# 		uv_layer_obY = active_mesh.uv_textures.get(bakemap_prefY)
# 		if uv_layer_obY is None:
# 			active_mesh.uv_textures.new(bakemap_prefY)
# 		uv_layer_obZ = active_mesh.uv_textures.get(bakemap_prefZ)
# 		if uv_layer_obZ is None:
# 			active_mesh.uv_textures.new(bakemap_prefZ)

# 		selverts = get_selected_vertsIdx(active_mesh)
# 		if len(selverts) == 0:
# 			selverts = None

# 		bm = bmesh.new()
# 		bm.from_mesh(active_mesh)
# 		bm.verts.ensure_lookup_table()
# 		bm.faces.ensure_lookup_table()
# 		bm.verts.index_update()
# 		islandPerVert = {}
# 		islandId = 0
# 		selVertsIslandsed = splitBmVertsByLinks_v02(bm, selverts, False)
# 		for meshlist in selVertsIslandsed:
# 			if len(meshlist)>0:
# 				islandId = islandId+1.0
# 				cnterSum = Vector((0,0,0))
# 				for vidx in meshlist:
# 					v = bm.verts[vidx]
# 					cnterSum = cnterSum+v.co
# 				cnterAvg = cnterSum/len(meshlist)
# 				for vidx in meshlist:
# 					islandPerVert[vidx] = cnterAvg
# 		onCnt = 0
# 		if len(islandPerVert)>0:
# 			uv_layer_obX = bm.loops.layers.uv.get(bakemap_prefX)
# 			uv_layer_obY = bm.loops.layers.uv.get(bakemap_prefY)
# 			uv_layer_obZ = bm.loops.layers.uv.get(bakemap_prefZ)
# 			for face in bm.faces:
# 				for loop in face.loops:
# 					vert = loop.vert
# 					if (vert.index in islandPerVert):
# 						onCnt = onCnt+1
# 						cnterAvg = islandPerVert[vert.index]
# 						cnterOffs = cnterAvg-vert.co
# 						loop[uv_layer_obX].uv = (cnterOffs[0],cnterAvg[0])
# 						loop[uv_layer_obY].uv = (cnterOffs[1],cnterAvg[1])
# 						loop[uv_layer_obZ].uv = (cnterOffs[2],cnterAvg[2])
# 		bm.to_mesh(active_mesh)
# 		bpy.ops.object.mode_set(mode='OBJECT')
# 		context.scene.update()
# 		print("Islands",islandId,"verts",onCnt,"maps",bakemap_prefX,bakemap_prefY,bakemap_prefZ)
# 		self.report({'INFO'}, 'Islands found='+str(islandId))
# 		return {'FINISHED'}


class wpluvvg_copyuv(bpy.types.Operator):
	bl_idname = "mesh.wpluvvg_copyuv"
	bl_label = "Topological Copy/Paste UV"
	bl_options = {'REGISTER', 'UNDO'}
	opt_op = EnumProperty(
		name="Operation", default="COPY",
		items=(('COPY', "COPY", ""), ('PASTE', "PASTE", ""))
	)
	opt_uvName = StringProperty(
		name = "UV Name",
		default = kWPLEdgeFlowUV
	)
	opt_autoOrder = BoolProperty(
		name = "Auto ordering",
		default = True
	)
	@classmethod
	def poll( cls, context ):
		return ( context.object is not None and context.object.type == 'MESH')

	def execute( self, context ):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		def generateVertTopoKeys(bm, histVerts):
			#bpy.ops.mesh.select_all( action = 'DESELECT' ) # DBG
			mapVert2refDstE = {}
			mapVert2refDstF = {}
			for v in bm.verts:
				mapVert2refDstE[v.index] = [0 for i in range(len(histVerts))]
				mapVert2refDstF[v.index] = [0 for i in range(len(histVerts))]
			print("- starting forward pass...")
			for vId in range(0, len(histVerts)):
				refv1 = histVerts[vId]
				step_vIdx = [refv1]
				_, _, distmapE = getBmVertGeodesicDistmap_v05(bm, [refv1], 200, None, False, False, None)
				_, _, distmapF = getBmVertGeodesicDistmap_v05(bm, [refv1], 200, None, True, False, None)
				# print("- distmap", vId, vIdx, len(distmap))
				for vIdx in distmapE:
					dst = distmapE[vIdx]
					mapVert2refDstE[vIdx][vId] = dst
				for vIdx in distmapF:
					dst = distmapF[vIdx]
					mapVert2refDstF[vIdx][vId] = dst
			print("- starting backward pass, total verts: "+str(len(mapVert2refDstE))+"...")
			#_, origmap, _ = getBmVertGeodesicDistmap_v05(bm, histVerts, 200, None, False, False, None)
			mapVertTopoKeys = {}
			mapVertTopoKeysInv = {}
			for vIdx in mapVert2refDstE:
				dstE = mapVert2refDstE[vIdx]
				dstF = mapVert2refDstF[vIdx]
				kk = "t"
				# _, _, distmapRev = getBmVertGeodesicDistmap_v05(bm, [vIdx], 200, None, True, False, None)
				# for hvIdx in histVerts:
				# 	kkDstRev = str(distmapRev[hvIdx])+"/"
				# 	kk = kk+kkDstRev
				for vId, dst in enumerate(dstF):
					kkDst = str(dst)+"/"
					kk = kk+kkDst
				for vId, dst in enumerate(dstE):
					kkDst = "+"+str(dst)
					kk = kk+kkDst
				mapVertTopoKeys[vIdx] = kk
				if kk not in mapVertTopoKeysInv:
					mapVertTopoKeysInv[kk] = []
				mapVertTopoKeysInv[kk].append(vIdx)
			print("- checks done! histVerts", histVerts)
			dupesKeys2 = 0
			for kk in mapVertTopoKeysInv:
				if len(mapVertTopoKeysInv[kk]) >= 2:
					dupesKeys2 = dupesKeys2+1
					for vIdx in mapVertTopoKeysInv[kk]:
						v = bm.verts[vIdx]
						v.select = True
					print("- topology dupesKeys", kk, mapVertTopoKeysInv[kk])
			if dupesKeys2 > 0:
				bmesh.update_edit_mesh(active_mesh, True)
				print("- ERROR: topology dupes:", len(histVerts), dupesKeys2)
			return mapVertTopoKeys
		selverts = get_selected_vertsIdx(active_mesh)
		select_and_change_mode(active_obj, 'EDIT')
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.verts.index_update()
		bm.faces.ensure_lookup_table()
		bm.faces.index_update()
		uv_layer_holdr = bm.loops.layers.uv.get(self.opt_uvName)
		histVerts = get_bmhistory_vertsIdx(bm)
		if self.opt_autoOrder or (len(histVerts) < 3 and len(selverts) >= 3):
			histVerts = []
			selvord = []
			for vIdx in selverts:
				v = bm.verts[vIdx]
				kk = "z"+str(int((v.co[2])*kWPLUVPrecision)).zfill(8)+"_x"+str(int((v.co[0])*kWPLUVPrecision)).zfill(8)+"_y"+str(int((v.co[1])*kWPLUVPrecision)).zfill(8)
				selvord.append((kk, vIdx))
			selvord.sort(key=lambda ia: ia[0], reverse=False)
			print("- auto order", selvord)
			histVerts = [ia[1] for ia in selvord]
		if len(histVerts) < 3:
			self.report({'ERROR'}, "Hist verts needed")
			return {'CANCELLED'}
		if self.opt_op == 'COPY':
			okCnt = 0
			uvmapDict = {}
			mapVertTopoKeys = generateVertTopoKeys(bm, histVerts)
			if uv_layer_holdr is not None:
				for face in bm.faces:
					for vert, loop in zip(face.verts, face.loops):
						if vert.index in mapVertTopoKeys:
							kk = mapVertTopoKeys[vert.index]
							if kk not in uvmapDict:
								uvmapDict[kk] = copy.copy(loop[uv_layer_holdr].uv)
								okCnt = okCnt+1
			WPL_G.store['wpluvvg_copyuv'] = uvmapDict
			self.report({'INFO'}, "Copied "+str(okCnt)+" verts")
		if self.opt_op == 'PASTE':
			if 'wpluvvg_copyuv' not in WPL_G.store:
				self.report({'ERROR'}, "No UV map copy found")
				return {'FINISHED'}
			uvmapDict = WPL_G.store['wpluvvg_copyuv']
			if uv_layer_holdr is None:
				self.report({'ERROR'}, "Target UV map not found")
				return {'FINISHED'}
			okCnt = {}
			mapVertTopoKeys = generateVertTopoKeys(bm, histVerts)
			for face in bm.faces:
				for vert, loop in zip(face.verts, face.loops):
					if vert.index in mapVertTopoKeys:
						kk = mapVertTopoKeys[vert.index]
						if kk in uvmapDict:
							uvmap = uvmapDict[kk]
							loop[uv_layer_holdr].uv = (uvmap[0], uvmap[1])
							okCnt[vert.index] = 1
			bmesh.update_edit_mesh(active_mesh, True)
			select_and_change_mode(active_obj, 'OBJECT')
			self.report({'INFO'}, "Pasted "+str(len(okCnt))+" verts")
		return {'FINISHED'}


# class wpluvvg_bakedepth2vg(bpy.types.Operator):
# 	bl_idname = "mesh.wpluvvg_bakedepth2vg"
# 	bl_label = "Depth to VG"
# 	bl_options = {'REGISTER', 'UNDO'}

# 	opt_vgPrefx = StringProperty(
# 		name = "VG Name",
# 		default = "_depth"
# 	)
	
# 	opt_direction = FloatVectorProperty(
# 		name	 = "Direction",
# 		size	 = 3,
# 		default	 = (0.0,1.0,0.0)
# 	)

# 	@classmethod
# 	def poll( cls, context ):
# 		return ( context.object is not None and
# 				context.object.type == 'MESH' )

# 	def execute( self, context ):
# 		active_obj = context.scene.objects.active
# 		active_mesh = active_obj.data
# 		selvertsAll = get_selected_vertsIdx(active_mesh)
# 		if len(selvertsAll) == 0:
# 			self.report({'ERROR'}, "No selected vertices found")
# 			return {'FINISHED'}
# 		vg = active_obj.vertex_groups.get(self.opt_vgPrefx)
# 		if vg is None:
# 			if len(self.opt_vgPrefx) == 0:
# 				self.report({'ERROR'}, "No active vertex group found")
# 				return {'CANCELLED'}
# 			self.report({'INFO'}, "Vertex group not found, creating new")
# 			vg = active_obj.vertex_groups.new(self.opt_vgPrefx)
# 		active_obj.vertex_groups.active_index = vg.index
# 		select_and_change_mode(active_obj,'EDIT')
# 		bm = bmesh.from_edit_mesh(active_mesh)
# 		bm.verts.ensure_lookup_table()
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
# 		# deleting hidden faces
# 		for bm2f in bm2.faces:
# 			if bm2f.hide and bm2f not in v2rf:
# 				v2rf.append(bm2f)
# 		bmesh.ops.delete(bm2,geom=v2rf,context=5)
# 		bm2_tree = BVHTree.FromBMesh(bm2, epsilon = kWPLRaycastEpsilon)
# 		bm2.free()
# 		vertsDepths = {}
# 		vertsDepthMax = 0
# 		for vIdx in selvertsAll:
# 			w_v_co = bm.verts[vIdx].co
# 			direction = Vector((self.opt_direction[0],self.opt_direction[1],self.opt_direction[2])).normalized()
# 			origin = w_v_co+kWPLRaycastDeadzone*direction
# 			hit, hit_normal = fuzzyBVHRayCast_v01(bm2_tree, origin, direction, 0, 10)
# 			if hit is not None:
# 				depth = (hit-w_v_co).length
# 				vertsDepths[vIdx] = depth
# 				if depth>vertsDepthMax:
# 					vertsDepthMax = depth
# 		select_and_change_mode(active_obj,'OBJECT')
# 		okCnt = 0
# 		if vertsDepthMax>0:
# 			for vIdx in selvertsAll:
# 				wmod = 'REPLACE'
# 				try:
# 					oldval = vg.weight(vIdx)
# 				except Exception as e:
# 					wmod = 'ADD'
# 					oldval = 0
# 				newval = 0.0
# 				if vIdx in vertsDepths:
# 					newval = vertsDepths[vIdx]/vertsDepthMax
# 				vg.add([vIdx], newval, wmod)
# 				okCnt = okCnt+1
# 		self.report({'INFO'}, "Baked "+str(okCnt)+" verts")
# 		return {'FINISHED'}

# class wpluvvg_vgpropagate(bpy.types.Operator):
# 	bl_idname = "mesh.wpluvvg_vgpropagate"
# 	bl_label = "VG: Propagate on selected"
# 	bl_options = {'REGISTER', 'UNDO'}
# 	opt_influence = bpy.props.FloatProperty(
# 		name		= "Influence",
# 		min = 0.0, max = 1.0,
# 		default	 	= 1.0
# 	)
# 	opt_falloff = bpy.props.FloatProperty(
# 		name		= "Falloff",
# 		min = 0.0, max = 10.0,
# 		default	 	= 0.0
# 	)

# 	@classmethod
# 	def poll( cls, context ):
# 		return ( context.object is not None and
# 				context.object.type == 'MESH' )

# 	def execute( self, context ):
# 		active_obj = context.scene.objects.active
# 		active_mesh = active_obj.data
# 		selvertsAll = get_selected_vertsIdx(active_mesh)
# 		if len(selvertsAll) == 0:
# 			self.report({'ERROR'}, "No selected vertices found")
# 			return {'FINISHED'}
# 		select_and_change_mode(active_obj,"EDIT")
# 		bm = bmesh.from_edit_mesh(active_mesh)
# 		bm.verts.ensure_lookup_table()
# 		bm.verts.index_update()
# 		histVertsIdx = get_bmhistory_vertsIdx(bm)
# 		if len(histVertsIdx) == 0:
# 			self.report({'ERROR'}, "No active vertice found")
# 			return {'FINISHED'}
# 		refVertIdx = histVertsIdx[0]
# 		print("Ref vert:",refVertIdx,bm.verts[refVertIdx].co,"selverts",len(selvertsAll))
# 		vertsCo = {}
# 		vertsCo[refVertIdx] = bm.verts[refVertIdx].co
# 		distanceMax = 0.0
# 		for idx in selvertsAll:
# 			vertsCo[idx] = bm.verts[idx].co
# 			dst2ref = (vertsCo[idx]-vertsCo[refVertIdx]).length
# 			distanceMax = max(dst2ref,distanceMax)
# 		select_and_change_mode(active_obj,"OBJECT")
# 		ok = 0
# 		for vg in active_obj.vertex_groups:
# 			try:
# 				valRef = vg.weight(refVertIdx)
# 			except Exception as e:
# 				valRef = 0
# 			for idx in selvertsAll:
# 				if idx == refVertIdx:
# 					continue
# 				wmod = 'REPLACE'
# 				try:
# 					oldval = vg.weight(idx)
# 				except Exception as e:
# 					oldval = 0
# 					wmod = 'ADD'
# 				dst2ref = (vertsCo[idx]-vertsCo[refVertIdx]).length
# 				infl = 1.0
# 				if self.opt_falloff > 0.0:
# 					infl = 1.0-dst2ref/distanceMax
# 					infl = min(1.0,infl)
# 					infl = max(0.0,infl)
# 					infl = pow(infl,self.opt_falloff)
# 				newval = oldval+(valRef-oldval)*self.opt_influence*infl
# 				vg.add([idx], newval, wmod)
# 				ok=ok+1
# 		bpy.context.scene.update()
# 		active_mesh.update()
# 		select_and_change_mode(active_obj,"EDIT")
# 		self.report({'INFO'}, "Propagated on "+str(ok)+" verts")
# 		return {'FINISHED'}

class wpluvvg_vgnext(bpy.types.Operator):
	bl_idname = "mesh.wpluvvg_vgnext"
	bl_label = "Find next layer with selected"
	bl_options = {'REGISTER', 'UNDO'}
	opt_minval = bpy.props.FloatProperty(
		name		= "Minimum Value",
		default	 	= 0.1
	)

	@classmethod
	def poll( cls, context ):
		return ( context.object is not None and
				context.object.type == 'MESH' )

	def execute( self, context ):
		oldmode = context.scene.objects.active.mode
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		wpl_weigToolOpts = context.scene.uvvgtoolsOpts
		selvertsAll = get_selected_vertsIdx(active_mesh)
		if len(selvertsAll) == 0:
			self.report({'ERROR'}, "No selected vertices found")
			return {'CANCELLED'}
		select_and_change_mode(active_obj,"OBJECT")

		vg_firstOk = None
		vg_nextOk = None
		iswmcoFound = False
		for vg in active_obj.vertex_groups:
			if vg.name == wpl_weigToolOpts.wei_gropnm:
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
			wpl_weigToolOpts.wei_gropnm = vg_nextOk.name
			# in EDIT mode!!!
			active_obj.vertex_groups.active_index = vg_nextOk.index
			#bpy.ops.object.vertex_group_select()
		select_and_change_mode(active_obj,oldmode)
		bpy.context.scene.update()
		return {'FINISHED'}

class wpluvvg_smoothall(bpy.types.Operator):
	bl_idname = "mesh.wpluvvg_smoothall"
	bl_label = "Weight: smooth all"
	bl_options = {'REGISTER', 'UNDO'}
	
	opt_onActiveOnly = BoolProperty(
		name="Use active only",
		default=False
	)
	opt_iters = bpy.props.FloatProperty(
		name		= "Iters",
		default	 	= 5
	)

	@classmethod
	def poll( cls, context ):
		return ( context.object is not None and
				context.object.type == 'MESH' )

	def execute( self, context ):
		oldmode = context.scene.objects.active.mode
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		selvertsAll = get_selected_vertsIdx(active_mesh)
		if len(selvertsAll) == 0:
			self.report({'ERROR'}, "No selected vertices found")
			return {'CANCELLED'}
		act_vg = None
		if self.opt_onActiveOnly:
			wpl_weigToolOpts = context.scene.uvvgtoolsOpts
			act_vg = active_obj.vertex_groups.get(wpl_weigToolOpts.wei_gropnm)
			if act_vg is None:
				self.report({'ERROR'}, "No active group")
				return {'CANCELLED'}
		select_and_change_mode(active_obj,"EDIT")
		if act_vg is None:
			bpy.ops.object.vertex_group_smooth(group_select_mode = 'ALL', repeat = self.opt_iters)
		else:
			active_obj.vertex_groups.active_index = act_vg.index
			bpy.ops.object.vertex_group_smooth(group_select_mode = 'ACTIVE', repeat = self.opt_iters)
		bpy.ops.mesh.select_all( action = 'SELECT' )
		select_and_change_mode(active_obj,"OBJECT")
		for vg in active_obj.vertex_groups:
			bpy.ops.object.vertex_group_set_active(group = vg.name)
			bpy.ops.object.vertex_group_normalize()
		select_and_change_mode(active_obj,"EDIT")
		bpy.ops.mesh.select_all( action = 'DESELECT' )
		select_and_change_mode(active_obj,"OBJECT")
		for v in active_mesh.vertices:
			if v.index in selvertsAll:
				v.select = True
		select_and_change_mode(active_obj,oldmode)
		bpy.context.scene.update()
		return {'FINISHED'}

class wpluvvg_vgedt(bpy.types.Operator):
	bl_idname = "mesh.wpluvvg_vgedt"
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
	opt_otherval = bpy.props.FloatProperty(
		name		= "Value for other vg",
		default	 	= -1.0
		)
	opt_extendOnNear = BoolProperty(
		name="With nears (even hidden)",
		default=True
	)
	@classmethod
	def poll( cls, context ):
		return ( context.object is not None and
				context.object.type == 'MESH' )

	def execute( self, context ):
		oldmode = context.scene.objects.active.mode
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		wpl_weigToolOpts = context.scene.uvvgtoolsOpts
		selvertsAll = get_selected_vertsIdx(active_mesh)
		if len(selvertsAll) == 0:
			self.report({'ERROR'}, "No selected vertices found")
			return {'CANCELLED'}
		if self.opt_extendOnNear == True:
			additnlIdx = []
			for e in active_mesh.edges:
				if e.vertices[0] in selvertsAll and e.vertices[1] not in selvertsAll:
					if e.vertices[1] not in additnlIdx:
						additnlIdx.append(e.vertices[1])
				if e.vertices[1] in selvertsAll and e.vertices[0] not in selvertsAll:
					if e.vertices[0] not in additnlIdx:
						additnlIdx.append(e.vertices[0])
			selvertsAll = selvertsAll+additnlIdx
		select_and_change_mode(active_obj,"OBJECT")
		vg = active_obj.vertex_groups.get(wpl_weigToolOpts.wei_gropnm)
		if vg is None:
			if len(wpl_weigToolOpts.wei_gropnm) == 0:
				self.report({'ERROR'}, "No active vertex group found")
				return {'CANCELLED'}
			self.report({'INFO'}, "Vertex group not found, creating new")
			vg = active_obj.vertex_groups.new(wpl_weigToolOpts.wei_gropnm)
			wpl_weigToolOpts.wei_gropnm = vg.name
		active_obj.vertex_groups.active_index = vg.index
		stepval = wpl_weigToolOpts.wei_value
		for idx in selvertsAll:
			wmod = 'REPLACE'
			try:
				oldval = vg.weight(idx)
			except Exception as e:
				wmod = 'ADD'
				oldval = 0
			newval = oldval*self.opt_oldmul+self.opt_stepmul*stepval+self.opt_stepadd
			vg.add([idx], newval, wmod)
		if self.opt_otherval >= 0.0:
			for vg in active_obj.vertex_groups:
				if vg.name == wpl_weigToolOpts.wei_gropnm:
					continue
				for idx in selvertsAll:
					wmod = 'REPLACE'
					try:
						oldval = vg.weight(idx)
					except Exception as e:
						oldval = 0
						wmod = 'ADD'
					vg.add([idx], self.opt_otherval, wmod)
		if oldmode != 'EDIT':
			select_and_change_mode(active_obj,"EDIT")
		select_and_change_mode(active_obj,oldmode)
		#bpy.context.scene.objects.active = bpy.context.scene.objects.active
		bpy.context.scene.update()
		return {'FINISHED'}


class wpluvvg_islandsmid(bpy.types.Operator):
	bl_idname = "object.wpluvvg_islandsmid"
	bl_label = "Generate Islands"
	bl_options = {'REGISTER', 'UNDO'}

	opt_targetVc = StringProperty(
		name="Target VC",
		default = kWPLIslandsVC
	)
	# opt_targetUV = StringProperty(
	# 	name="Target UV",
	# 	default = ""
	# )

	@classmethod
	def poll(self, context):
		p = context.object and context.object.data and (isinstance(context.scene.objects.active, bpy.types.Object) and isinstance(context.scene.objects.active.data, bpy.types.Mesh))
		return p

	def execute(self, context):
		active_obj = context.scene.objects.active
		if active_obj is None:
			self.report({'ERROR'}, "No active object found")
			return {'CANCELLED'}
		active_mesh = active_obj.data
		out_VCName = self.opt_targetVc
		#out_UVName = self.opt_targetUV
		selverts = [e.index for e in active_mesh.vertices] # all, important for curve meshing
		#selverts = get_selected_vertsIdx(active_mesh)
		#if len(selverts) == 0:
		#	selverts = None

		bm = bmesh.new()
		bm.from_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		islandPerVert = {}
		islandId = 0.0
		selVertsIslandsed = splitBmVertsByLinks_v02(bm, selverts, False)
		for meshlist in selVertsIslandsed:
			if len(meshlist)>0:
				islandId = islandId+1.0
				for vidx in meshlist:
					islandPerVert[vidx] = islandId
		bpy.ops.object.mode_set(mode='OBJECT')
		colorsRGB = []
		colorsR = []
		colorsG = []
		colorsB = []
		for islfrac in range(0, int(islandId)+1):
			colorsR.append(0.11+0.77*(islfrac/islandId))
			colorsG.append(0.22+0.88*(islfrac/islandId))
			colorsB.append(0.33+0.99*(islfrac/islandId))
		random.shuffle(colorsR)
		random.shuffle(colorsG)
		random.shuffle(colorsB)
		for islfrac in range(0, int(islandId)+1):
			newcolor = Vector((colorsR[islfrac], colorsG[islfrac], colorsB[islfrac]))
			colorsRGB.append(newcolor)
		if len(out_VCName) > 0:
			palette_mapvc = active_mesh.vertex_colors.get(out_VCName)
			if palette_mapvc is None:
				palette_mapvc = active_mesh.vertex_colors.new(out_VCName)
			if palette_mapvc is not None and len(islandPerVert)>0:
				for poly in active_mesh.polygons:
					ipoly = poly.index
					for idx, lIdx in enumerate(active_mesh.polygons[ipoly].loop_indices):
						ivdx = active_mesh.polygons[ipoly].vertices[idx]
						if (ivdx in islandPerVert):
							islfrac = islandPerVert[ivdx]
							newcolor = colorsRGB[int(islfrac)]
							palette_mapvc.data[lIdx].color = (newcolor[0],newcolor[1],newcolor[2],1.0)
		# if len(out_UVName) > 0:
		# 	palette_mapuv = active_mesh.uv_layers.get(out_UVName)
		# 	if palette_mapuv is not None and len(islandPerVert)>0:
		# 		for poly in active_mesh.polygons:
		# 			ipoly = poly.index
		# 			for idx, lIdx in enumerate(active_mesh.polygons[ipoly].loop_indices):
		# 				ivdx = active_mesh.polygons[ipoly].vertices[idx]
		# 				if (ivdx in islandPerVert):
		# 					islfrac = islandPerVert[ivdx]
		# 					palette_mapuv.data[lIdx].uv = Vector((palette_mapuv.data[lIdx].uv[0],islfrac))
		self.report({'INFO'}, 'Islands found='+str(islandId))
		context.scene.update()
		return {'FINISHED'}
		
######################### ######################### #########################
######################### ######################### #########################

# def onUpdate_bake_uvbase_real(self, context):
# 	uvvgtoolsOpts = context.scene.uvvgtoolsOpts
# 	if len(uvvgtoolsOpts.bake_uvbase_real)>0:
# 		uvvgtoolsOpts.bake_uvbase = uvvgtoolsOpts.bake_uvbase_real
# 		uvvgtoolsOpts.bake_uvbase_real = ""

def onUpdate_wei_gropnm_real(self, context):
	wpl_weigToolOpts = context.scene.uvvgtoolsOpts
	if len(wpl_weigToolOpts.wei_gropnm_real)>0:
		wpl_weigToolOpts.wei_gropnm = wpl_weigToolOpts.wei_gropnm_real
		wpl_weigToolOpts.wei_gropnm_real = ""
	
class WPLUVVGToolsSettings(bpy.types.PropertyGroup):
	# bake_uvbase = StringProperty(
	# 	name="UV",
	# 	default = kWPLEdgeFlowUV
	# )
	# bake_uvbase_real = StringProperty(
	# 	name="",
	# 	default = ""
	# )

	wei_value = FloatProperty(
		name="Val",
		default = 0.1
	)
	wei_gropnm = StringProperty(
		name="VG",
		default = ""
	)
	wei_gropnm_real = StringProperty(
		name="",
		default = "",
		update=onUpdate_wei_gropnm_real
	)

class WPLUVVGTools_Panel(bpy.types.Panel):
	bl_label = "Prop: UV/VG"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_category = 'WPL'

	def draw_header(self, context):
		layout = self.layout
		layout.label(text="")

	def draw(self, context):
		layout = self.layout
		uvvgtoolsOpts = context.scene.uvvgtoolsOpts
		active_obj = context.scene.objects.active
		col = layout.column()
		if active_obj is None or active_obj.data is None or active_obj.type == 'ARMATURE':
			col.label(text="No proper object")
			return
		obj_data = active_obj.data
		col.separator()
		box2 = col.box()
		row0 = box2.row()
		row0.prop(uvvgtoolsOpts, "wei_gropnm")
		row0.prop_search(uvvgtoolsOpts, "wei_gropnm_real", active_obj, "vertex_groups", icon='GROUP_VERTEX', text="")
		box2.separator()
		#box2.operator("mesh.wpluvvg_vgpropagate")
		box2.operator("mesh.wpluvvg_smoothall", text="VG: Smooth on selection").opt_onActiveOnly = False
		box2.separator()
		row1 = box2.row()
		row1.prop(uvvgtoolsOpts, "wei_value")
		op1 = row1.operator("mesh.wpluvvg_vgedt", text="+")
		op1.opt_stepmul = 1.0
		op1.opt_oldmul = 1.0
		op1.opt_stepadd = 0.0
		op1.opt_otherval = -1.0
		op2 = row1.operator("mesh.wpluvvg_vgedt", text="-")
		op2.opt_stepmul = -1.0
		op2.opt_oldmul = 1.0
		op2.opt_stepadd = 0.0
		op2.opt_otherval = -1.0
		row2 = box2.row()
		op5 = row2.operator("mesh.wpluvvg_vgedt", text="*0.5")
		op5.opt_stepmul = 0.0
		op5.opt_oldmul = 0.5
		op5.opt_stepadd = 0.0
		op5.opt_otherval = -1.0
		op5 = row2.operator("mesh.wpluvvg_vgedt", text="*1.5")
		op5.opt_stepmul = 0.0
		op5.opt_oldmul = 1.5
		op5.opt_stepadd = 0.0
		op5.opt_otherval = -1.0
		op6 = row2.operator("mesh.wpluvvg_vgedt", text="*2.0")
		op6.opt_stepmul = 0.0
		op6.opt_oldmul = 2.0
		op6.opt_stepadd = 0.0
		op6.opt_otherval = -1.0
		row3 = box2.row()
		op7 = row3.operator("mesh.wpluvvg_vgedt", text="=0.0")
		op7.opt_stepmul = 0.0
		op7.opt_oldmul = 0.0
		op7.opt_stepadd = 0.0
		op7.opt_otherval = -1.0
		op8 = row3.operator("mesh.wpluvvg_vgedt", text="=0.5")
		op8.opt_stepmul = 0.0
		op8.opt_oldmul = 0.0
		op8.opt_stepadd = 0.5
		op8.opt_otherval = -1.0
		op9 = row3.operator("mesh.wpluvvg_vgedt", text="=1.0")
		op9.opt_stepmul = 0.0
		op9.opt_oldmul = 0.0
		op9.opt_stepadd = 1.0
		op9.opt_otherval = -1.0
		# op10 = box2.operator("mesh.wpluvvg_vgedt", text="Set 1.0 Exclusively")
		# op10.opt_stepmul = 0.0
		# op10.opt_oldmul = 0.0
		# op10.opt_stepadd = 1.0
		# op10.opt_otherval = 0.0
		box2.separator()
		box2.operator("mesh.wpluvvg_smoothall", text="Smooth selection").opt_onActiveOnly = True
		box2.operator("mesh.wpluvvg_vgnext", text="Activate next layer")
		col.separator()
		col.separator()
		box4 = col.box()
		box4.operator("object.wpluvvg_unwrap_edges", text="UV: Edges Grid").opt_tranfType='GRD'
		box4.operator("object.wpluvvg_unwrap_edges", text="UV: Edges DistanceAVG").opt_tranfType='DST_AVG'
		box4.operator("object.wpluvvg_unwrap_edges", text="UV: Edges DistancePRJ").opt_tranfType='DST_PRJ'
		box4.operator("object.wpluvvg_unwrap_bonenrm", text="UV: Bone Normals")
		box4.separator()
		box4.operator("object.wpluvvg_islandsmid", text="VC: Generate Islands")
		#box4.operator("object.wpluvvg_unwrap_islc", text="Bake island centers")
		col.separator()
		# box5 = col.box()
		# row0 = box5.row()
		# row0.prop(uvvgtoolsOpts, "bake_uvbase")
		# row0.prop_search(uvvgtoolsOpts, "bake_uvbase_real", active_obj.data, "uv_layers", icon='GROUP_UVS', text="")
		# box5.separator()
		#row0a = box5.row()
		#row0a.operator("object.wpluvvg_unwrap_uv", text="Basic Unwrap").opt_unwrType = 'BASIC'
		#row0a.operator("object.wpluvvg_unwrap_uv", text="From View").opt_unwrType = 'PROJ'
		#box5.operator("object.wpluvvg_normalize_uv", text="Normalize UVs")
		#col.separator()
		box2 = col.box()
		box2.operator("mesh.wpluvvg_copyuv", text="Topo-Copy UV").opt_op = 'COPY'
		box2.operator("mesh.wpluvvg_copyuv", text="Topo-Paste UV").opt_op = 'PASTE'
		#box2.separator()
		#box2.operator("mesh.wpluvvg_bakedepth2vg")


def register():
	bpy.utils.register_module(__name__)
	bpy.types.Scene.uvvgtoolsOpts = PointerProperty(type=WPLUVVGToolsSettings)

def unregister():
	bpy.utils.unregister_module(__name__)
	del bpy.types.Scene.uvvgtoolsOpts
	bpy.utils.unregister_class(WPLUVVGToolsSettings)

if __name__ == "__main__":
	register()
