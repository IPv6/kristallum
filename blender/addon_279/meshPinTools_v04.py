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
	"name": "Mesh Pin Tools",
	"author": "IPv6",
	"version": (1, 1, 2),
	"blender": (2, 7, 9),
	"location": "View3D > T-panel > WPL",
	"description" : "",
	"warning"	 : "",
	"wiki_url"	: "",
	"tracker_url" : "",
	"category"	: "WPL"
}

kRaycastEpsilon = 0.01
kRaycastEpsilonCCL = 0.0001
kWPLPinmapUV = "_pinmap"

######################### ######################### #########################
######################### ######################### #########################
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
				bvh_collide = BVHTree.FromBMesh(bm_collide, epsilon = kRaycastEpsilonCCL)
				bm_collide.free()
				bvh2collides.append(bvh_collide)
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

def getVertsPropagationsDst_v02(bm, propDst, initialVertsIdx, initialVertsCo, refPoints):
	propagation_stages = []
	allWalkedVerts = []
	vertsFromIdx = {}
	vertsAddWeight = {}
	if propDst > 0.0 and refPoints>0:
		kd = mathutils.kdtree.KDTree(len(initialVertsIdx))
		for i, vIdx in enumerate(initialVertsIdx):
			allWalkedVerts.append(vIdx)
			v1 = bm.verts[vIdx]
			v1_co = v1.co
			if initialVertsCo is not None and vIdx in initialVertsCo:
				v1_co = initialVertsCo[vIdx]
			kd.insert(v1_co, vIdx)
		kd.balance()
		stage_verts = []
		for vert in bm.verts:
			if vert.hide == 0 and vert.index not in allWalkedVerts:
				kdres = kd.find_n(vert.co, refPoints*3)
				for kditm in kdres:
					f_co = kditm[0]
					f_idx = kditm[1]
					f_dst = kditm[2]
					if f_dst < propDst:
						if f_idx not in allWalkedVerts:
							continue
						if vert.index not in vertsFromIdx:
							vertsAddWeight[vert.index] = 1.0
							vertsFromIdx[vert.index] = []
						if len(vertsFromIdx[vert.index]) >= refPoints:
							continue
						vertsFromIdx[vert.index].append(f_idx)
						if vert.index not in allWalkedVerts:
							allWalkedVerts.append(vert.index)
						if vert.index not in stage_verts:
							stage_verts.append(vert.index)
						vertsAddWeight[vert.index] = min(vertsAddWeight[vert.index], 1.0-f_dst/propDst)
		propagation_stages.append(stage_verts)
	return (propagation_stages, vertsAddWeight, allWalkedVerts, vertsFromIdx)

def getVertsPropagations_v02(bm, smoothingLoops, initialVertsIdx):
	propagation_stages = []
	allWalkedVerts = []
	vertsFromIdx = {}
	#vertsFromRootIdx = {}
	vertsAddWeight = {}
	checked_verts = copy.copy(initialVertsIdx)
	if smoothingLoops > 0.0:
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
	#vertsFromRootIdx = {}
	#def check_vIdxFroms(vIdx,vprts):
	#	if vIdx not in vertsFromIdx:
	#		return
	#	vIdxfrom = vertsFromIdx[vIdx]
	#	if vIdx not in vertsFromRootIdx:
	#		vertsFromRootIdx[vIdx] = []
	#	vprts.append(vertsFromRootIdx[vIdx])
	#	for fIdx in vIdxfrom:
	#		if fIdx in initialVertsIdx:
	#			for pr in vprts:
	#				if fIdx not in pr:
	#					pr.append(fIdx)
	#	for fIdx in vIdxfrom:
	#		if fIdx not in initialVertsIdx:
	#			check_vIdxFroms(fIdx,vprts)
	#for vIdx in vertsFromIdx:
	#	check_vIdxFroms(vIdx,[])
	return (propagation_stages, vertsAddWeight, allWalkedVerts, vertsFromIdx)

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


def getBmPinmap(active_obj, bm, vfilter):
	active_mesh = active_obj.data
	uv_layer_holdr = active_mesh.uv_textures.get(kWPLPinmapUV)
	if uv_layer_holdr is None:
		return (None,None,None,None)
	verts_snap_map = {}
	verts_snap_nrm_map = {}
	verts_se_map = {}
	verts_odx_map = {}
	verts_odx_map_inv = {}
	pinmap = active_obj[kWPLPinmapUV]
	bm.verts.ensure_lookup_table()
	bm.verts.index_update()
	bm.faces.ensure_lookup_table()
	bm.faces.index_update()
	uv_layer_holdr = bm.loops.layers.uv.get(kWPLPinmapUV)
	if uv_layer_holdr is not None:
		for face in bm.faces:
			for vert, loop in zip(face.verts, face.loops):
				if vert.index in verts_snap_map:
					continue
				if vfilter is not None and abs(vert.co[0]) > 0.00001 and math.copysign(1,vert.co[0]) != math.copysign(1,vfilter[0]):
					continue
				if loop[uv_layer_holdr].uv[1] < 0.9: # safety measure
					continue
				storeIdxI = int(loop[uv_layer_holdr].uv[0])
				if storeIdxI > 0:
					storeIdx = str(storeIdxI-1)
					if storeIdx in pinmap:
						idxpin = pinmap[storeIdx]
						storeIdxI = int(storeIdx)
						verts_snap_map[vert.index] = Vector(idxpin["co"])
						verts_snap_nrm_map[vert.index] = Vector(idxpin["no"])
						verts_se_map[vert.index] = idxpin["se"]
						verts_odx_map[vert.index] = storeIdxI
						if storeIdxI not in verts_odx_map_inv:
							verts_odx_map_inv[storeIdxI] = []
						verts_odx_map_inv[storeIdxI].append(vert.index)
						verts_odx_map_inv[storeIdxI].sort(key=lambda vidx: verts_snap_map[vidx][0], reverse=False)
		missingVerts = 0
		for vert in bm.verts:
			if vert.index not in verts_odx_map:
				verts_snap_map[vert.index] = vert.co
				verts_snap_nrm_map[vert.index] = vert.normal
				verts_se_map[vert.index] = 0
				verts_odx_map[vert.index] = 0
				missingVerts = missingVerts+1
		if missingVerts>0:
			print("- getBmPinmap missing verts:",missingVerts)
	return (verts_snap_map,verts_snap_nrm_map,verts_se_map,verts_odx_map,verts_odx_map_inv)

def setBmPinmap(active_obj):
	active_mesh = active_obj.data
	select_and_change_mode(active_obj, 'EDIT')
	uv_layer_holdr = active_mesh.uv_textures.get(kWPLPinmapUV)
	if uv_layer_holdr is not None:
		active_mesh.uv_textures.remove(uv_layer_holdr)
	active_mesh.uv_textures.new(kWPLPinmapUV)
	bm = bmesh.from_edit_mesh(active_mesh)
	bm.verts.ensure_lookup_table()
	bm.faces.ensure_lookup_table()
	bm.verts.index_update()
	uv_layer_holdr = bm.loops.layers.uv.get(kWPLPinmapUV)
	if uv_layer_holdr is None:
		print("Can`t create pinmap")
		return 0
	pinmap = {}
	for face in bm.faces:
		for vert, loop in zip(face.verts, face.loops):
			storeIdx = vert.index
			loop[uv_layer_holdr].uv = (storeIdx+1, 1)
			isSelect = 0
			if vert.select:
				isSelect = 1
			isHide = 0
			if vert.hide>0:
				isHide = 1
			#pinmap[storeIdx] = [vert.co.copy(),vert.normal.copy(),isSelect,isHide]
			pinmap[str(storeIdx)] = {"co": (vert.co[0],vert.co[1],vert.co[2]), "no": (vert.normal[0],vert.normal[1],vert.normal[2]), "se": isSelect, "hi": isHide}
	active_obj[kWPLPinmapUV] = pinmap
	bmesh.update_edit_mesh(active_mesh, True)
	select_and_change_mode(active_obj, 'OBJECT')
	return len(pinmap)
######################### ######################### #########################
######################### ######################### #########################
class wplsmthdef_snap(bpy.types.Operator):
	bl_idname = "mesh.wplsmthdef_snap"
	bl_label = "Pin mesh state"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(self, context):
		p = context.object and context.object.data and context.object.type == 'MESH'
		return p

	def execute(self, context):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		if setBmPinmap(active_obj) == 0:
			self.report({'ERROR'}, "Can`t create pinmap")
			return {'CANCELLED'}
		self.report({'INFO'}, "Mesh state remembered")
		return {'FINISHED'}

class wplsmthdef_snapdel(bpy.types.Operator):
	bl_idname = "mesh.wplsmthdef_snapdel"
	bl_label = "Clear mesh state"
	bl_options = {'REGISTER', 'UNDO'}

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
		select_and_change_mode(active_obj, 'OBJECT')
		uv_layer_holdr = active_mesh.uv_textures.get(kWPLPinmapUV)
		if uv_layer_holdr is not None:
			active_mesh.uv_textures.remove(uv_layer_holdr)
		del active_obj[kWPLPinmapUV]
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
		p = context.object and context.object.data and context.object.type == 'MESH'
		return p

	def execute(self, context):
		active_obj = context.scene.objects.active
		if active_obj is None or active_obj.data is None:
			self.report({'ERROR'}, "No active object")
			return {'CANCELLED'}
		active_mesh = active_obj.data
		if (active_obj[kWPLPinmapUV] is None or active_mesh.uv_textures.get(kWPLPinmapUV) is None):
			self.report({'ERROR'}, "Object not snapped, snap mesh first")
			return {'CANCELLED'}
		selverts = get_selected_vertsIdx(active_mesh)
		if not self.opt_onlyContactVerts and len(selverts) == 0:
			selverts = [e.index for e in active_mesh.vertices]
		if len(selverts) == 0:
			self.report({'ERROR'}, "No verts selected")
			return {'CANCELLED'}

		bvh2collides = get_sceneColldersBVH(active_obj,False)
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
		verts_se_map = {}
		(verts_snap_map,verts_snap_nrm_map,verts_se_map,_,_) = getBmPinmap(active_obj, bm, None)
		verts_now_map = {}
		for vert in bm.verts:
			verts_now_map[vert.index] = vert.co
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

	opt_influence = FloatProperty(
			name="Influence",
			min=-10.0, max=10.0,
			default=1.0,
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
		if (active_obj[kWPLPinmapUV] is None or active_mesh.uv_textures.get(kWPLPinmapUV) is None):
			self.report({'ERROR'}, "Object not snapped, snap mesh first")
			return {'CANCELLED'}
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
		verts_snap_map = {}
		verts_snap_nrm_map = {}
		verts_se_map = {}
		(verts_snap_map,verts_snap_nrm_map,verts_se_map,_,_) = getBmPinmap(active_obj, bm, None)
		for vIdx in selverts:
			s_v = bm.verts[vIdx]
			s_v.co = s_v.co.lerp(verts_snap_map[vIdx],self.opt_influence)
		bm.normal_update()
		bmesh.update_edit_mesh(active_mesh, True)
		return {'FINISHED'}

class wplsmthdef_propagate(bpy.types.Operator):
	bl_idname = "mesh.wplsmthdef_propagate"
	bl_label = "Smooth around selection"
	bl_options = {'REGISTER', 'UNDO'}

	opt_smoothingLoops = IntProperty(
			name="Loops/Points",
			min=0, max=100,
			default=3,
	)
	opt_smoothingDist = FloatProperty(
			name="Points distance",
			min=0.0, max=100,
			default=0.0,
	)
	opt_influence = FloatProperty(
			name="Influence",
			min=-100, max=100,
			default=1.0,
	)
	opt_falloff = FloatProperty(
			name="Falloff",
			min=0.001, max=10,
			default=1.0,
	)
	opt_normalFac = FloatProperty(
			name="Align to Normal",
			description="Align to Normal",
			min=0.0, max=1.0,
			default=0.0,
	)
	#opt_clampOffset = BoolProperty(
	#		name="Clamp to plane",
	#		default=False,
	#)

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
		if (active_obj[kWPLPinmapUV] is None or active_mesh.uv_textures.get(kWPLPinmapUV) is None):
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
		verts_se_map = {}
		(verts_snap_map,verts_snap_nrm_map,verts_se_map,_,_) = getBmPinmap(active_obj, bm, None)
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
		if self.opt_smoothingDist > 0:
			(propagationSteps, vertsWeight, allWalkedVerts, vertsFromIdx) = getVertsPropagationsDst_v02(bm, self.opt_smoothingDist, selverts, verts_snap_map, self.opt_smoothingLoops)
		else:
			(propagationSteps, vertsWeight, allWalkedVerts, vertsFromIdx) = getVertsPropagations_v02(bm, self.opt_smoothingLoops, selverts)
		print("propagationSteps",len(propagationSteps),"allWalkedVerts",len(allWalkedVerts),"vertsFromIdx",len(vertsFromIdx),"vertsWeight",len(vertsWeight))
		verts_shifts = {}
		for v_idx in allWalkedVerts:
			if (v_idx not in verts_shifts) and (v_idx in verts_snap_map):
				v = bm.verts[v_idx]
				verts_shifts[v_idx] = mathutils.Vector(v.co - verts_snap_map[v_idx])
		new_positions = {}
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
					total_shift = self.opt_normalFac*sn_shift + (1.0-self.opt_normalFac)*s_shift
					vertWeight = 1.0
					if vIdx in vertsWeight and abs(vertsWeight[vIdx])>0.0 and self.opt_falloff > 0.0:
						vertWeight = pow(vertsWeight[vIdx], self.opt_falloff)
					#print("shifting vert", vIdx, vertWeight, s_v.index, s_v.co, verts_snap_map[vIdx])
					total_shift = total_shift*vertWeight*self.opt_influence
					#fromR_vIdxes = vertsFromRootIdx[vIdx]
					#if self.opt_clampOffset and len(fromR_vIdxes)>0:
					#	r_v = bm.verts[fromR_vIdxes[0]]
					#	root_v_shift = verts_snap_nrm_map[r_v.index]
					#	if root_v_shift.length >= kRaycastEpsilonCCL:
					#		intrp = mathutils.geometry.intersect_line_plane(s_v.co, s_v.co+total_shift, r_v.co, root_v_shift)
					#		if intrp is not None:
					#			intrp = intrp-s_v.co
					#			if intrp.length < total_shift.length:
					#				total_shift = intrp
					s_v_co2 = s_v.co+total_shift
					new_positions[vIdx] = s_v_co2
		# updating positions as post-step
		for s_idx in new_positions:
			s_v = bm.verts[s_idx]
			#print("New position vert",s_v.co,new_positions[s_idx],(s_v.co-new_positions[s_idx]).length)
			s_v.co = new_positions[s_idx]
		bm.normal_update()
		bmesh.update_edit_mesh(active_mesh, True)
		return {'FINISHED'}

class wplsmthdef_transfer(bpy.types.Operator):
	bl_idname = "mesh.wplsmthdef_transfer"
	bl_label = "Clone topology"
	bl_options = {'REGISTER', 'UNDO'}
	opt_scale = FloatVectorProperty(
		name	 = "Transfer scale",
		size	 = 3,
		min=-1.0, max=1.0,
		default	 = (-1.0,1.0,1.0)
	)
	opt_cloneLoops = IntProperty(
			name="Loops",
			min=0, max=1000,
			default=10,
	)
	opt_falloff = FloatProperty(
			name="Falloff",
			min=0.0, max=10.0,
			default=0.0,
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
		select_and_change_mode(active_obj, 'EDIT')
		bm = bmesh.from_edit_mesh(active_mesh)
		selvertsIdx = get_bmhistory_vertsIdx(bm)
		if len(selvertsIdx) < 2:
			self.report({'ERROR'}, "Verts History error: Pick source, then target.")
			return {'CANCELLED'}
		verts_snap_map = {}
		verts_snap_nrm_map = {}
		if (active_mesh.uv_textures.get(kWPLPinmapUV) is not None and WPL_G.pinobj == active_obj.name):
			print("Found pinned state, using for reference")
			verts_se_map = {}
			(verts_snap_map,verts_snap_nrm_map,verts_se_map,_,_) = getBmPinmap(active_obj, bm, None)
		else:
			for vert in bm.verts:
				verts_snap_map[vert.index] = vert.co
				verts_snap_nrm_map[vert.index] = vert.normal
		transfScale = Vector(self.opt_scale)
		refp_origin_v = bm.verts[selvertsIdx[1]]
		refp_target_v = bm.verts[selvertsIdx[0]]
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
				infl = 1.0
				if self.opt_falloff > 0.0:
					infl = 1.0-float(transferStep+1)/float(self.opt_cloneLoops)
					infl = pow(infl,self.opt_falloff)
				vSrcOffsScaled = Vector((vSrcOffs[0]*transfScale[0],vSrcOffs[1]*transfScale[1],vSrcOffs[2]*transfScale[2]))
				vTrg.co = vTrg.co.lerp(refp_target+vSrcOffsScaled, infl)
				transferred.append(vSrc.index)
				transferred.append(vTrg.index)
				if transferStep < self.opt_cloneLoops:
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

class wplsmthdef_surfshrw( bpy.types.Operator ):
	bl_idname = "mesh.wplsmthdef_surfshrw"
	bl_label = "Shrinkwrap to pinned"
	bl_options = {'REGISTER', 'UNDO'}

	opt_shrinkwMethod = EnumProperty(
		name="Detection method", default="NEAR",
		items=(("NEAR", "Near surface", ""), ("PROJECT", "Negative proj", ""))
	)
	opt_prefDistance = FloatProperty(
		name		= "Keep on distance",
		default	 = 0.0,
		min		 = -100.0,
		max		 = 100.0
	)
	opt_influence = FloatProperty(
		name		= "Influence",
		default	 = 1.0,
		min		 = 0,
		max		 = 1
	)
	opt_vertsType = EnumProperty(
		name="Apply to verts", default="ALL",
		items=(("ALL", "All", ""), ("ABOVE", "Above surface", ""), ("UNDER", "Under surface", ""))
	)
	opt_smoothingLoops = IntProperty(
		name		= "Smooth shrinkwrap",
		default	 = 0,
		min		 = 0,
		max		 = 100
	)
	opt_falloff = FloatProperty(
		name		= "Smoothing falloff",
		min		 = 0.001,
		max		 = 10.0,
		default	 = 1.0
	)
	opt_extendBounds = FloatProperty(
		name="Extend Bounds",
		min		= 0.0,
		max		= 100.0,
		default = 0.5,
	)
	@classmethod
	def poll(self, context):
		p = context.object and context.object.data and context.object.type == 'MESH'
		return p

	def execute( self, context ):
		active_obj = context.scene.objects.active
		if active_obj is None or active_obj.data is None:
			self.report({'ERROR'}, "No active object")
			return {'CANCELLED'}
		active_mesh = active_obj.data
		if (active_obj[kWPLPinmapUV] is None or active_mesh.uv_textures.get(kWPLPinmapUV) is None):
			self.report({'ERROR'}, "Object not snapped, snap mesh first")
			return {'CANCELLED'}
		selvertsAll = get_selected_vertsIdx(active_mesh)
		if len(selvertsAll) == 0:
			self.report({'ERROR'}, "No verts selected")
			return {'FINISHED'}

		bpy.ops.object.mode_set( mode = 'EDIT' )
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.verts.index_update()
		bm.faces.ensure_lookup_table()
		bm.faces.index_update()

		verts_snap_map = {}
		verts_snap_nrm_map = {}
		verts_se_map = {}
		(verts_snap_map,verts_snap_nrm_map,verts_se_map,_,_) = getBmPinmap(active_obj, bm, None)
		bufMapFaces = []
		for face in bm.faces:
			if face.index not in bufMapFaces:
				for v in face.verts:
					if verts_se_map[v.index] > 0 and face.index not in bufMapFaces:
						bufMapFaces.append(face.index)
		if len(bufMapFaces) == 0:
			self.report({'ERROR'}, "No surface faces found, pin mesh with selected faces first")
			return {'CANCELLED'}
		bm2 = bmesh.new()
		bm2vmap = {}
		bm2conv = []
		for fIdx in bufMapFaces:
			f = bm.faces[fIdx]
			f_v_set = []
			f_center_co = Vector((0,0,0))
			f_center_cnt = 0.0
			for vert in f.verts:
				v_co = verts_snap_map[vert.index]
				f_center_co = f_center_co+v_co
				f_center_cnt = f_center_cnt+1.0
				if vert.index not in bm2vmap:
					v_cc = bm2.verts.new(v_co)
					bm2vmap[vert.index] = v_cc
				f_v_set.append(bm2vmap[vert.index])
			f_center_co = f_center_co/f_center_cnt
			f_cc = bm2.faces.new(f_v_set)
			if self.opt_extendBounds > 0.0:
				for e in f.edges:
					if e.is_boundary:
						v1_co = verts_snap_map[e.verts[0].index]
						v2_co = verts_snap_map[e.verts[1].index]
						vm_co = 0.5*(v1_co+v2_co)
						v1_cc = bm2.verts.new(v1_co)
						v2_cc = bm2.verts.new(v2_co)
						v1a_cc = bm2.verts.new(f_center_co+self.opt_extendBounds*(vm_co-f_center_co))
						#v2a_cc = bm2.verts.new(f_center_co+self.opt_extendBounds*(v2_co-f_center_co))
						bm2conv.append(v1_cc)
						bm2conv.append(v2_cc)
						bm2conv.append(v1a_cc)
						#bm2conv.append(v2a_cc)
		if len(bm2conv)>0:
			res = bmesh.ops.convex_hull(bm2, input=bm2conv)
			bm2.verts.ensure_lookup_table()
			bm2.verts.index_update()
			bm2.faces.ensure_lookup_table()
			bm2.faces.index_update()
		bm2.normal_update()
		bm2bvh = BVHTree.FromBMesh(bm2, epsilon = kRaycastEpsilonCCL)
		bm2.free()

		vertsWeight = None
		if self.opt_smoothingLoops > 0:
			(propagationSteps, vertsWeight, allWalkedVerts, vertsFromIdx) = getVertsPropagations_v02(bm, self.opt_smoothingLoops, selvertsAll) #, verts_snap_map
			selvertsAll = allWalkedVerts
		vnormls = {}
		for vIdx in selvertsAll:
			v = bm.verts[vIdx]
			vnormls[vIdx] = v.normal
		okCnt = 0
		for vIdx in selvertsAll:
			v = bm.verts[vIdx]
			if self.opt_shrinkwMethod == 'NEAR':
				n_loc, n_normal, n_index, n_distance = bm2bvh.find_nearest(v.co)
			else: # PROJECT
				n_loc, n_normal, n_index, n_distance = bm2bvh.ray_cast(v.co, -1*vnormls[vIdx], 999)
			if n_loc is not None:
				n_normorg = n_normal
				dotFac = (v.co-n_loc).dot(n_normal)
				if self.opt_vertsType == 'ABOVE':
					if dotFac <= 0:
						continue
				if self.opt_vertsType == 'UNDER':
					if dotFac <= 0:
						continue
				if abs(self.opt_prefDistance)>0.00001:
					n_loc = n_loc+n_normal*self.opt_prefDistance
				infl = self.opt_influence
				if vertsWeight is not None and v.index in vertsWeight and self.opt_falloff > 0.0:
					vertWeight = pow(vertsWeight[v.index], self.opt_falloff)
					infl = infl*vertWeight
				v.co = v.co.lerp(n_loc,infl)
				okCnt = okCnt+1
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		bm.normal_update()
		bmesh.update_edit_mesh(active_mesh, True)
		self.report({'INFO'}, "Done, "+str(okCnt)+" verts moved")
		return {'FINISHED'}

class wplsmthdef_surfedgerest(bpy.types.Operator):
	bl_idname = "mesh.wplsmthdef_surfedgerest"
	bl_label = "Restore edge-net"
	bl_options = {'REGISTER', 'UNDO'}

	opt_iterations = IntProperty(
			name="Iterations",
			min=1, max=100,
			default=10,
	)
	opt_loops = IntProperty(
			name="Step loops",
			min=1, max=100,
			default=10,
	)
	opt_falloff = FloatProperty(
			name="Loops falloff",
			min=0.0, max=10.0,
			default=0.0,
	)
	opt_stepInfluence = FloatProperty(
			name="Step Influence",
			min=-10.0, max=10.0,
			default=0.3,
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
		if (active_obj[kWPLPinmapUV] is None or active_mesh.uv_textures.get(kWPLPinmapUV) is None):
			self.report({'ERROR'}, "Object not snapped, snap mesh first")
			return {'CANCELLED'}
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
		verts_snap_map = {}
		verts_snap_nrm_map = {}
		verts_se_map = {}
		(verts_snap_map,verts_snap_nrm_map,verts_se_map,_,_) = getBmPinmap(active_obj, bm, None)
		okCnt = 0
		for itr in range(self.opt_iterations):
			print ("- iteration",itr, okCnt)
			walkedVerts = []
			stepVerts = selverts.copy()
			for step in range(self.opt_loops):
				print ("-- step",step, len(stepVerts), okCnt)
				if len(stepVerts) == 0:
					break
				nextStepVerts = []
				step_cos = {}
				for vIdx in stepVerts:
					v = bm.verts[vIdx]
					for e in v.link_edges:
						v2 = e.other_vert(v)
						if v2.index in walkedVerts or v2.index in stepVerts:
							continue
						if v2.hide > 0:
							walkedVerts.append(v2.index)
							continue
						ori_len = (verts_snap_map[v2.index] - verts_snap_map[v.index]).length
						cur_len = (v2.co-v.co).length
						#step_len = cur_len+(ori_len-cur_len)*self.opt_edgemix_len
						step_len = ori_len
						v2_newco = v.co+(v2.co-v.co).normalized()*step_len
						if v2 not in step_cos:
							step_cos[v2] = []
						step_cos[v2].append(v2_newco)
						if v2.index not in nextStepVerts:
							nextStepVerts.append(v2.index)
				infl = 1.0
				if self.opt_falloff > 0.0:
					infl = pow(1.0-float(step+1)/float(self.opt_loops),self.opt_falloff)
				for v2 in step_cos:
					v2co = Vector((0,0,0))
					v2cnt = 0.0
					for co in step_cos[v2]:
						v2co = v2co+co
						v2cnt = v2cnt+1.0
					if v2cnt > 0:
						v2co = v2co/v2cnt
						v2.co = v2.co.lerp(v2co, self.opt_stepInfluence*infl)
						okCnt = okCnt+1
				walkedVerts.extend(stepVerts)
				stepVerts = nextStepVerts
		bm.normal_update()
		bmesh.update_edit_mesh(active_mesh, True)
		self.report({'INFO'}, "Done, "+str(okCnt)+" verts moved")
		return {'FINISHED'}

class wplsmthdef_surfalign( bpy.types.Operator ):
	bl_idname = "mesh.wplsmthdef_surfalign"
	bl_label = "Align selection to pinned"
	bl_options = {'REGISTER', 'UNDO'}

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
		min		 = 0.0,
		max		 = 1.0
	)

	@classmethod
	def poll(self, context):
		p = context.object and context.object.data and context.object.type == 'MESH'
		return p

	def execute( self, context ):
		active_obj = context.scene.objects.active
		if active_obj is None or active_obj.data is None:
			self.report({'ERROR'}, "No active object")
			return {'CANCELLED'}
		active_mesh = active_obj.data
		if (active_obj[kWPLPinmapUV] is None or active_mesh.uv_textures.get(kWPLPinmapUV) is None):
			self.report({'ERROR'}, "Object not snapped, snap mesh first")
			return {'CANCELLED'}
		selfacesAll = get_selected_facesIdx(active_mesh)
		if len(selfacesAll) == 0:
			self.report({'ERROR'}, "No faces selected, select faces and vert")
			return {'FINISHED'}

		bpy.ops.object.mode_set( mode = 'EDIT' )
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.verts.index_update()
		bm.faces.ensure_lookup_table()
		bm.faces.index_update()
		histVertsIdx = []
		histFacesIdx = []
		if bpy.context.tool_settings.mesh_select_mode[2] == True:
			histFacesIdx = get_bmhistory_faceIdx(bm)
		else:
			histVertsIdx = get_bmhistory_vertsIdx(bm)
		if len(histVertsIdx)+len(histFacesIdx) == 0:
			self.report({'ERROR'}, "No verts in history, select at least 1 vert manually")
			return {'FINISHED'}

		verts_snap_map = {}
		verts_snap_nrm_map = {}
		verts_se_map = {}
		(verts_snap_map,verts_snap_nrm_map,verts_se_map,_,_) = getBmPinmap(active_obj, bm, None)

		bufMapFaces = []
		for face in bm.faces:
			if face.index not in bufMapFaces:
				for v in face.verts:
					if verts_se_map[v.index] > 0 and face.index not in bufMapFaces:
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
		bm2.free()
		glob_center = None
		glob_matRot = None
		glob_shift = None
		if len(histFacesIdx)>0:
			face0 = bm.faces[histFacesIdx[0]]
			glob_center = face0.calc_center_median()
			glob_normal = -1*face0.normal
			if self.opt_invertNormals:
				glob_normal = -1*glob_normal
		else:
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
class WPLPinningTools_Panel(bpy.types.Panel):
	bl_label = "Mesh Pinning"
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
			prow1 = col.row()
			prow1.operator("mesh.wplsmthdef_snap", text="Pin state")
			prow1.operator("mesh.wplsmthdef_snapdel", text="Clear")
			col.operator("mesh.wplsmthdef_propagate", text="Smooth around selection")
			col.operator("mesh.wplsmthdef_restore", text="Restore selection")
			col.operator("mesh.wplsmthdef_restcolln")

			col.separator()
			col.separator()
			ss1 = col.operator("mesh.wplsmthdef_surfshrw")
			ss1.opt_shrinkwMethod = 'NEAR'
			ss1.opt_vertsType = 'ALL'
			ss1.opt_prefDistance = 0.0
			prow2 = col.row()
			ss2 = prow2.operator("mesh.wplsmthdef_surfshrw", text="Land over")
			ss1.opt_shrinkwMethod = 'PROJECT'
			ss2.opt_vertsType = 'ABOVE'
			ss2.opt_prefDistance = 0.0
			ss2 = prow2.operator("mesh.wplsmthdef_surfshrw", text="Pull under")
			ss1.opt_shrinkwMethod = 'NEAR'
			ss2.opt_vertsType = 'ABOVE'
			ss2.opt_prefDistance = -0.001
			col.operator("mesh.wplsmthdef_surfedgerest")
			col.operator("mesh.wplsmthdef_surfalign")
			col.separator()
			col.operator("mesh.wplsmthdef_transfer")

def register():
	bpy.utils.register_module(__name__)

def unregister():
	bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
	register()
