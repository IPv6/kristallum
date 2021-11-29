import math
import copy
import mathutils
import time
from mathutils import kdtree
from bpy_extras import view3d_utils
import numpy as np
import datetime

import bpy
from bpy.props import *
import bpy.types
import bmesh
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

bl_info = {
	"name": "Prop Bind Tools",
	"author": "IPv6",
	"version": (1, 4, 14),
	"blender": (2, 7, 9),
	"location": "View3D > T-panel > WPL",
	"warning": "",
	"wiki_url": "",
	"tracker_url": "",
	"category": "WPL"}

kWPLRaycastEpsilon = 0.0001
kWPLRaycastDeadzone = 0.0
kWPLConvexPrecision = 10000.0
kWPLUVPrecision = 100000.0
kWPLHullIncKey = "wpl_helperobjs"
#kWPLPinmapUV = "_pinmap"
#kWPLBindmapUV = "_bindmap"
kWPLBindmapOCP = "wpl_bindmap_o2"
kWPLBindmapCCP = "wpl_bindmap_c2"
kWPLEdgeFlowUV = "Edges"
kWPLEdgesMainCam = "zzz_MainCamera"
kWPLSystemEmpty = "zzz_Support"
kWPLFrameBindPostfix = "_##"
kWPLFinShapekeyPrefix = "Finalize"

#kWPLShapeKeyAntiIntr = 'wpl_antiIntersect'
#kWPLAntiIntrInfluenceVC = 'AntiIntersect'
#kWPLShapeKeyDiffBake = 'wpl_diffBake'
#kWPLDisplmapUV = "DisplaceMap"

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

def getHelperObjId(context):
	if kWPLHullIncKey not in context.scene:
		context.scene[kWPLHullIncKey] = 1
	curId = context.scene[kWPLHullIncKey]
	context.scene[kWPLHullIncKey] = context.scene[kWPLHullIncKey]+1
	return curId

def get_isLocalView():
	is_local_view = sum(bpy.context.space_data.layers[:]) == 0 #if hairCurve.layers_local_view[0]:
	return is_local_view

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

def uvToKey(uv_vec):
	key = str(int(uv_vec[0]*kWPLUVPrecision))+"_"+str(int(uv_vec[1]*kWPLUVPrecision))
	return key
def coToKey(co_vec):
	key = str(int(co_vec[0]*kWPLConvexPrecision))+"_"+str(int(co_vec[1]*kWPLConvexPrecision))+"_"+str(int(co_vec[2]*kWPLConvexPrecision))
	return key
def idxToKey(co_idx):
	key = str(int(co_idx*kWPLConvexPrecision))
	return key

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
def toggleModifs(c_object, modfTypes, onOff, prepstate):
	foundMds = []
	for md in c_object.modifiers:
		if md.type in modfTypes:
			foundMds.append(md)
			if onOff is None and prepstate is None:
				# just counting!
				continue
			if onOff == False:
				print("- disabling", md.name,md.type)
				if prepstate is not None:
					prepstate[md] = (md.show_in_editmode,md.show_on_cage,md.show_viewport,md.show_render)
				md.show_in_editmode = False
				md.show_on_cage = False
				md.show_viewport = False
				md.show_render = False
			if onOff == True:
				print("- enabling", md.name, md.type)
				if prepstate is not None:
					prepstate[md] = (md.show_in_editmode,md.show_on_cage,md.show_viewport,md.show_render)
				md.show_in_editmode = True
				md.show_on_cage = True
				md.show_viewport = True
				md.show_render = True
			if (onOff is None) and (prepstate is not None):
				if md in prepstate:
					print("- restoring", md.name, md.type, prepstate[md])
					md.show_in_editmode = prepstate[md][0]
					md.show_on_cage = prepstate[md][1]
					md.show_viewport = prepstate[md][2]
					md.show_render = prepstate[md][3]
	return foundMds

# def modfVertDisplace(c_object, displBasename, offsetMap_l):
# 	#bpy.ops.object.mode_set( mode = 'OBJECT' )
# 	# uv unwrap: lightmap pack +1024 size +0.2 margin
# 	if c_object is None or c_object.type != 'MESH':
# 		return -1
# 	if c_object.data.uv_layers.get(kWPLDisplmapUV) is None:
# 		return -2
# 	dispImgW = kWPLDisplmapRes
# 	dispImgH = kWPLDisplmapRes
# 	dispImgMidLvl = 0.5
# 	dispImgScaleLvl = 10.0
# 	dispUV = c_object.data.uv_layers.get(kWPLDisplmapUV).data
# 	dispUVTex = c_object.data.uv_textures.get(kWPLDisplmapUV)
# 	dispImage = bpy.data.images.get(displBasename)
# 	if dispImage is None:
# 		dispImage = bpy.data.images.new(name = displBasename, width=dispImgW, height=dispImgH, alpha=True)
# 		pixels = list(dispImage.pixels)
# 		for i in range(0, len(pixels), 4):
# 			pixels[i+0] = dispImgMidLvl #randint(0,100)/100.0
# 			pixels[i+1] = dispImgMidLvl
# 			pixels[i+2] = dispImgMidLvl
# 			pixels[i+3] = 1.0
# 		dispImage.pixels[:] = pixels
# 	dispTex = bpy.data.textures.get(displBasename)
# 	if dispTex is None:
# 		dispTex = bpy.data.textures.new(displBasename, type = 'IMAGE')
# 		dispTex.image = dispImage
# 	dispModf = c_object.modifiers.get(displBasename)
# 	if dispModf is None:
# 		dispModf = c_object.modifiers.new(name = displBasename, type = 'DISPLACE')
# 		dispModf.strength = 1/dispImgScaleLvl
# 		dispModf.mid_level = (round(255*dispImgMidLvl)/255)
# 		dispModf.texture = dispTex
# 		dispModf.direction = 'RGB_TO_XYZ'
# 		dispModf.texture_coords = 'UV'
# 		dispModf.uv_layer = dispUVTex.name
# 		dispModf.space = 'LOCAL'
# 		dispModf.show_render = True
# 		dispModf.show_in_editmode = True
# 		dispModf.show_on_cage = True
# 	ok = 0
# 	used_vIdx = []
# 	used_pixels = {}
# 	pixels = list(dispImage.pixels)
# 	def incPixel(pic_x,pic_y,incval):
# 		if pic_x < 0 or pic_x >= dispImgW:
# 			return
# 		if pic_y < 0 or pic_y >= dispImgH:
# 			return
# 		refp = 4*(pic_x+dispImgW*pic_y)
# 		refp_str = str(pic_x)+":"+str(pic_y)
# 		if refp_str not in used_pixels:
# 			used_pixels[refp_str] = 0
# 		used_pixels[refp_str] = used_pixels[refp_str]+1
# 		pixels[refp+0] = pixels[refp+0]+incval[0]
# 		pixels[refp+1] = pixels[refp+1]+incval[1]
# 		pixels[refp+2] = pixels[refp+2]+incval[2]
# 	for poly in c_object.data.polygons:
# 		for loop_index in range(poly.loop_start, poly.loop_start + poly.loop_total):
# 			ivdx = c_object.data.loops[loop_index].vertex_index
# 			if (ivdx in offsetMap_l) and (ivdx not in used_vIdx):
# 				ok = ok+1
# 				used_vIdx.append(ivdx)
# 				vertOffset = offsetMap_l[ivdx]*dispImgScaleLvl
# 				pixel_x = round(dispImgW * dispUV[loop_index].uv[0])
# 				pixel_y = round(dispImgH * dispUV[loop_index].uv[1])
# 				incPixel(pixel_x,pixel_y,vertOffset)
# 				incPixel(pixel_x-1,pixel_y,vertOffset)
# 				incPixel(pixel_x-1,pixel_y-1,vertOffset)
# 				incPixel(pixel_x,pixel_y-1,vertOffset)
# 	if ok>0:
# 		dispImage.pixels[:] = pixels
# 		dispImage.update()
# 		dispImage.pack(as_png = True)
# 	overlaps = 0 # check pixel overlap
# 	for refp_str in used_pixels:
# 		if used_pixels[refp_str]>1:
# 			overlaps = overlaps+1
# 	if overlaps == 0:
# 		print("- Displace map: no overlaps")
# 	else:
# 		print("- Warning: Displace map: overlaps",overlaps)
# 	return ok

# def getBmPinmap(active_obj, bm = None, uvmapName = None):
# 	verts_dat,verts_odx_map_inv = getBmPinmapX(active_obj, bm, uvmapName)
# 	if verts_dat is None:
# 		return (None,None,None,None,None)
# 	verts_snap_map = {}
# 	verts_snap_nrm_map = {}
# 	verts_se_map = {}
# 	verts_odx_map = {}
# 	for idx in verts_dat:
# 		verts_snap_map[idx] = verts_dat[idx]["co"]
# 		verts_snap_nrm_map[idx] = verts_dat[idx]["no"]
# 		verts_se_map[idx] = verts_dat[idx]["se"]
# 		verts_odx_map[idx] = verts_dat[idx]["idx"]
# 	return (verts_snap_map,verts_snap_nrm_map,verts_se_map,verts_odx_map,verts_odx_map_inv)

# def getBmPinmapX(active_obj, bm, uvmapName = None):
# 	if uvmapName is None:
# 		uvmapName = kWPLPinmapUV
# 	active_mesh = active_obj.data
# 	uv_layer_holdr = active_mesh.uv_textures.get(uvmapName)
# 	if uv_layer_holdr is None:
# 		return (None,None)
# 	print("- getBmPinmap:", active_obj.name, uvmapName, len(active_mesh.vertices))
# 	verts_dat = {}
# 	verts_odx_map_inv = {}
# 	missingVerts = 0
# 	pinmap = active_obj[uvmapName]
# 	bm.verts.ensure_lookup_table()
# 	bm.verts.index_update()
# 	bm.faces.ensure_lookup_table()
# 	bm.faces.index_update()
# 	uv_layer_holdr = bm.loops.layers.uv.get(uvmapName)
# 	for face in bm.faces:
# 		for vert, loop in zip(face.verts, face.loops):
# 			if vert.index in verts_dat:
# 				continue
# 			#if vfilter is not None and abs(vert.co[0]) > 0.00001 and math.copysign(1,vert.co[0]) != math.copysign(1,vfilter[0]):
# 			#	continue
# 			if loop[uv_layer_holdr].uv[1] < 0.9: # safety measure
# 				continue
# 			storeIdxI = int(loop[uv_layer_holdr].uv[0])
# 			if storeIdxI > 0:
# 				storeIdx = str(storeIdxI-1)
# 				if storeIdx in pinmap:
# 					idxpin = pinmap[storeIdx]
# 					storeIdxI = int(storeIdx)
# 					if vert.index not in verts_dat:
# 						verts_dat[vert.index] = {}
# 					verts_dat[vert.index]["co"] = Vector(idxpin["co"])
# 					verts_dat[vert.index]["no"] = Vector(idxpin["no"])
# 					verts_dat[vert.index]["co_g"] = Vector(idxpin["co_g"])
# 					verts_dat[vert.index]["no_g"] = Vector(idxpin["no_g"])
# 					verts_dat[vert.index]["se"] = idxpin["se"]
# 					verts_dat[vert.index]["hi"] = idxpin["hi"]
# 					verts_dat[vert.index]["idx"] = storeIdxI
# 					if storeIdxI not in verts_odx_map_inv:
# 						verts_odx_map_inv[storeIdxI] = []
# 					verts_odx_map_inv[storeIdxI].append(vert.index)
# 					#verts_odx_map_inv[storeIdxI].sort(key=lambda vidx: verts_dat[vidx]["co"][0], reverse=False)
# 					verts_odx_map_inv[storeIdxI].sort(key=lambda vidx: vidx, reverse=False)
# 	for vert in bm.verts:
# 		if vert.index not in verts_dat:
# 			verts_dat[vert.index] = {}
# 			verts_dat[vert.index]["co"] = vert.co
# 			verts_dat[vert.index]["no"] = vert.normal
# 			verts_dat[vert.index]["co_g"] = active_obj.matrix_world*vert.co
# 			verts_dat[vert.index]["no_g"] = active_obj.matrix_world.inverted().transposed().to_3x3() * vert.normal
# 			verts_dat[vert.index]["se"] = 0
# 			verts_dat[vert.index]["hi"] = 0
# 			verts_dat[vert.index]["idx"] = 0
# 			missingVerts = missingVerts+1
# 	if missingVerts>0:
# 		print("- getBmPinmap: ", active_obj.name, uvmapName, "missing verts:", missingVerts, len(bm.verts), len(verts_dat))
# 	return (verts_dat, verts_odx_map_inv)

# def setBmPinmap(active_obj, uvmapName = None, useDeformed = False, justUpdate = True):
# 	if active_obj.type != 'MESH':
# 		return 0
# 	if uvmapName is None:
# 		uvmapName = kWPLPinmapUV
# 	active_mesh = active_obj.data
# 	select_and_change_mode(active_obj, 'EDIT')
# 	uv_layer_holdr = active_mesh.uv_textures.get(uvmapName)
# 	if justUpdate == False and uv_layer_holdr is not None:
# 		active_mesh.uv_textures.remove(uv_layer_holdr)
# 		uv_layer_holdr = None
# 	if uv_layer_holdr is None:
# 		justUpdate = False
# 		active_mesh.uv_textures.new(uvmapName)
# 	bm_deformed = None
# 	if useDeformed:
# 		bm_deformed = bmesh.new()
# 		bm_deformed.from_object(active_obj, bpy.context.scene, deform=True, render=False, cage=False, face_normals=False)
# 		bm_deformed.verts.ensure_lookup_table()
# 		bm_deformed.verts.index_update()
# 	bm = bmesh.from_edit_mesh(active_mesh)
# 	bm.verts.ensure_lookup_table()
# 	bm.verts.index_update()
# 	bm.faces.ensure_lookup_table()
# 	uv_layer_holdr = bm.loops.layers.uv.get(uvmapName)
# 	if uv_layer_holdr is None:
# 		print("Can`t create pinmap")
# 		return 0
# 	pinmap = {}
# 	for face in bm.faces:
# 		for vert, loop in zip(face.verts, face.loops):
# 			storeIdx = vert.index
# 			storeKey = str(storeIdx)
# 			if storeKey in pinmap:
# 				continue
# 			loop[uv_layer_holdr].uv = (storeIdx+1, 1)
# 			isSelect = 0
# 			if vert.select:
# 				isSelect = 1
# 			isHide = 0
# 			if vert.hide>0:
# 				isHide = 1
# 			#pinmap[storeIdx] = [vert.co.copy(),vert.normal.copy(),isSelect,isHide]
# 			vert_co = vert.co
# 			vert_no = vert.normal
# 			if bm_deformed is not None:
# 				vert_co_g = active_obj.matrix_world * bm_deformed.verts[vert.index].co
# 				vert_no_g = active_obj.matrix_world.inverted().transposed().to_3x3() * bm_deformed.verts[vert.index].normal
# 			else:
# 				vert_co_g = active_obj.matrix_world * vert_co
# 				vert_no_g = active_obj.matrix_world.inverted().transposed().to_3x3() * vert_no
# 			pinmap[storeKey] = {"co": (vert_co[0],vert_co[1],vert_co[2]), "no": (vert_no[0],vert_no[1],vert_no[2]), "co_g": (vert_co_g[0],vert_co_g[1],vert_co_g[2]), "no_g": (vert_no_g[0],vert_no_g[1],vert_no_g[2]), "se": isSelect, "hi": isHide}
# 	print("- setBmPinmap", active_obj.name, uvmapName, len(pinmap), len(bm.verts))
# 	if justUpdate == False:
# 		bmesh.update_edit_mesh(active_mesh, True)
# 	select_and_change_mode(active_obj, 'OBJECT')
# 	active_obj[uvmapName] = pinmap
# 	return len(pinmap)

def setBmPinmapFastUV(cage_obj, cage_bm, pinId, uvId):
	uv_layer_holdr = cage_bm.loops.layers.uv.get(uvId)
	if uv_layer_holdr is None:
		return None
	cage_bm.verts.ensure_lookup_table()
	cage_bm.verts.index_update()
	pins_v = {}
	vertKeys = {}
	for face in cage_bm.faces:
		for vert, loop in zip(face.verts, face.loops):
			luv = loop[uv_layer_holdr].uv
			luv_kk = uvToKey(luv)
			vertKeys[vert.index] = luv_kk
			vertKeys[luv_kk] = vert.index
	for vert in cage_bm.verts:
		pindat = {}
		isSelect = 0
		if vert.select:
			isSelect = 1
		isHide = 0
		if vert.hide>0:
			isHide = 1
		vert_no = copy.copy(vert.normal)
		vert_no_g = cage_obj.matrix_world.inverted().transposed().to_3x3() * vert_no
		vert_co = copy.copy(vert.co)
		vert_co_g = cage_obj.matrix_world * vert_co
		pindat["co"] = vert_co
		pindat["co_g"] = vert_co_g
		pindat["no"] = vert_no
		pindat["no_g"] = vert_no_g
		pindat["se"] = isSelect
		pindat["hi"] = isHide
		#pins_v[vert.index] = pindat
		pins_v[vertKeys[vert.index]] = pindat
		# if vert.select:
		# 	print("- selected", vert.index, vert.co, pindat)
	WPL_G.store[pinId] = pins_v
	return pins_v

def getBmPinmapFastUV(cage_obj, cage_bm, pinId, uvId):
	if pinId not in WPL_G.store:
		return None
	uv_layer_holdr = cage_bm.loops.layers.uv.get(uvId)
	if uv_layer_holdr is None:
		return None
	vertKeys = {}
	for face in cage_bm.faces:
		for vert, loop in zip(face.verts, face.loops):
			luv = loop[uv_layer_holdr].uv
			luv_kk = uvToKey(luv)
			vertKeys[vert.index] = luv_kk
			vertKeys[luv_kk] = vert.index
	pins_v = WPL_G.store[pinId]
	verts_dat = {}
	cage_bm.verts.ensure_lookup_table()
	cage_bm.verts.index_update()
	cage_bm.faces.ensure_lookup_table()
	cage_bm.faces.index_update()
	unkVerts = 0
	knoVerts = 0
	knoVertsDiff = 0
	for vert in cage_bm.verts:
		verts_dat[vert.index] = {}
		v_kk = vertKeys[vert.index]
		if v_kk not in pins_v:
			unkVerts = unkVerts+1
			vert_no = copy.copy(vert.normal)
			vert_no_g = cage_obj.matrix_world.inverted().transposed().to_3x3() * vert_no
			vert_co = copy.copy(vert.co)
			vert_co_g = cage_obj.matrix_world * vert_co
			verts_dat[vert.index]["co"] = vert_co
			verts_dat[vert.index]["co_g"] = vert_co_g
			verts_dat[vert.index]["no"] = vert_no
			verts_dat[vert.index]["no_g"] = vert_no_g
			verts_dat[vert.index]["se"] = 0
			verts_dat[vert.index]["hi"] = 0
			verts_dat[vert.index]["idx"] = 0
		else:
			idxpin = pins_v[v_kk]
			knoVerts = knoVerts+1
			knoVertsDiff = (Vector(idxpin["co"])-vert.co).length
			verts_dat[vert.index]["co"] = Vector(idxpin["co"])
			verts_dat[vert.index]["co_g"] = Vector(idxpin["co_g"])
			verts_dat[vert.index]["no"] = Vector(idxpin["no"])
			verts_dat[vert.index]["no_g"] = Vector(idxpin["no_g"])
			verts_dat[vert.index]["se"] = idxpin["se"]
			verts_dat[vert.index]["hi"] = idxpin["hi"]
			verts_dat[vert.index]["idx"] = vert.index
			# if vert.select:
			# 	print("- selected", vert.index, vert.co, verts_dat[vert.index])
		# if storeIdxI not in verts_odx_map_inv:
		# 	verts_odx_map_inv[v_kk] = []
		# verts_odx_map_inv[v_kk].append(vert.index)
		# verts_odx_map_inv[v_kk].sort(key=lambda vidx: vidx, reverse=False)
	#print("- pins_v", pins_v)
	print("- getBmPinmapFastUV: verts:", knoVerts, "diff:", knoVertsDiff, "unknown:", unkVerts)
	return verts_dat

def dumpBMesh(active_obj, bm2test, testname):
	bm2test_mesh = bpy.data.meshes.new(testname)
	bm2test_ob = bpy.data.objects.new(testname, bm2test_mesh)
	if active_obj is not None:
		bm2test_ob.matrix_world = active_obj.matrix_world
	bpy.context.scene.objects.link(bm2test_ob)
	bm2test.to_mesh(bm2test_mesh)
	return bm2test_ob
	
def customAxisMatrix(v_origin, a, b):
	#https://blender.stackexchange.com/questions/30808/how-do-i-construct-a-transformation-matrix-from-3-vertices
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

def getPolylinePoint(polyline):
	if polyline.type == 'NURBS' or polyline.type == 'POLY':
		points = polyline.points
	else:
		points = polyline.bezier_points
	return points
def getPolylineSelPoint(polyline):
	points = getPolylinePoint(polyline)
	if polyline.type == 'NURBS' or polyline.type == 'POLY':
		points = [point for point in points if point.select]
	else:# bezier
		points = [point for point in points if point.select_control_point]
	return points
def curveXMirror(Curve,onlySelected):
	select_and_change_mode(Curve,'EDIT')
	initialCount = len(Curve.data.splines)
	for i in range(initialCount):
		polylineI = Curve.data.splines[i]
		points = getPolylinePoint(polylineI)
		if onlySelected:
			points = getPolylineSelPoint(polylineI)
		if len(points)>1:
			polylineC = Curve.data.splines.new('NURBS')
			for j in range(len(points)):
				pointI = points[j]
				if len(polylineC.points) <= j:
					polylineC.points.add(1)
				polylineC.points[j].co = (-1.0*pointI.co[0], pointI.co[1], pointI.co[2], 1)
				polylineC.points[j].radius = pointI.radius
				polylineC.points[j].tilt = pointI.tilt
			polylineC.use_endpoint_u = polylineI.use_endpoint_u
			polylineC.use_bezier_u = polylineI.use_bezier_u
			polylineC.use_cyclic_u = polylineI.use_cyclic_u
			polylineC.resolution_u = polylineI.resolution_u
			polylineC.use_smooth = polylineI.use_smooth
			polylineC.order_u = polylineI.order_u
	return

#############################################################################################
#############################################################################################

# class wplbind_datatransf(bpy.types.Operator):
	# bl_idname = "object.wplbind_datatransf"
	# bl_label = "Mass-transfer data"
	# bl_options = {'REGISTER', 'UNDO'}

	# opt_tranfType = bpy.props.EnumProperty(
		# name="Data type", default="WEI",
		# items=(("WEI", "Weights", ""), ("VC", "Vertex colors", ""))
	# )
	# opt_makeSingleUser = bpy.props.BoolProperty(
		# name		= "Make single user",
		# default	 = True
	# )

	# @classmethod
	# def poll( cls, context ):
		# p = (isinstance(context.scene.objects.active, bpy.types.Object))
		# return p

	# def execute( self, context ):
		# wpl_propToolOpts = context.scene.wpl_propToolOpts
		# if wpl_propToolOpts.mdf_srcbody not in bpy.data.objects.keys():
			# self.report({'INFO'}, 'No source to get weight')
			# return {"CANCELLED"}
		# active_obj = bpy.data.objects[wpl_propToolOpts.mdf_srcbody]
		# if active_obj.type != 'MESH':
			# self.report({'INFO'}, 'Source is not a mesh')
			# return {"CANCELLED"}
		# sel_all = [o.name for o in bpy.context.selected_objects]
		# if len(sel_all) == 0:
			# self.report({'ERROR'}, "No objects selected")
			# return {'CANCELLED'}
		# ok = 0
		# select_and_change_mode(active_obj,"OBJECT")
		# for i, sel_obj_name in enumerate(sel_all):
			# sel_obj = context.scene.objects[sel_obj_name]
			# if sel_obj.name == active_obj.name:
				# continue
			# if sel_obj.type != 'MESH':
				# continue
			# needReset_R_vgs = False
			# for md in sel_obj.modifiers:
				# if md.type == 'MIRROR':
					# if self.opt_tranfType == "WEI":
						# needReset_R_vgs = True
						# break
					# else:
						# self.report({'ERROR'}, "Error: Object with MIRROR modifer.")
						# return {'CANCELLED'}
			# select_and_change_mode(sel_obj,"OBJECT")
			# print("Handling object "+str(i+1)+" of "+str(len(sel_all)), sel_obj.name)
			# if sel_obj.data.users > 1:
				# if self.opt_makeSingleUser:
					# bpy.ops.object.make_single_user(object=False, obdata=True)
				# else:
					# self.report({'ERROR'}, "Multi-user object, can`t apply modifier")
					# return {'CANCELLED'}
			# modname = "sys_dataTransfer"
			# bpy.ops.object.modifier_remove(modifier=modname)
			# modifiers = sel_obj.modifiers
			# dt_modifier = modifiers.new(name = modname, type = 'DATA_TRANSFER')
			# if dt_modifier is not None:
				# if self.opt_tranfType == "WEI":
					# dt_modifier.use_vert_data = True
					# dt_modifier.data_types_verts = {'VGROUP_WEIGHTS'}
					# dt_modifier.vert_mapping = 'POLYINTERP_NEAREST' #POLY_NEAREST
					# dt_modifier.layers_vgroup_select_src = 'ALL'
					# dt_modifier.layers_vgroup_select_dst = 'NAME'
				# if self.opt_tranfType == "VC":
					# dt_modifier.use_loop_data = True
					# dt_modifier.data_types_loops = {'VCOL'}
					# dt_modifier.loop_mapping = 'POLYINTERP_NEAREST'
					# dt_modifier.layers_vcol_select_src = 'ALL'
					# dt_modifier.layers_vcol_select_dst = 'NAME'
				# dt_modifier.object = active_obj
				# while sel_obj.modifiers[0].name != modname:
					# bpy.ops.object.modifier_move_up(modifier=modname)
				# bpy.ops.object.datalayout_transfer(modifier=modname)
				# bpy.ops.object.modifier_apply(apply_as='DATA', modifier=modname)
				# if needReset_R_vgs:
					# names = [group.name for group in sel_obj.vertex_groups if "_L" in group.name]
					# for group_name in names:
						# vertgroup = sel_obj.vertex_groups[group_name]
						# sel_obj.vertex_groups.remove(vertgroup)
						# sel_obj.vertex_groups.new(name=group_name)
				# ok = ok+1
		# select_and_change_mode(active_obj,"OBJECT")
		# self.report({'INFO'}, "Transferred to "+str(ok)+" objects")
		# return {'FINISHED'}

# class wplbind_cpymodifs(bpy.types.Operator):
	# bl_idname = "object.wplbind_cpymodifs"
	# bl_label = "Copy modifiers"
	# bl_options = {'REGISTER', 'UNDO'}

	# @classmethod
	# def poll( cls, context ):
		# p = (isinstance(context.scene.objects.active, bpy.types.Object))
		# return p

	# def execute( self, context ):
		# wpl_propToolOpts = context.scene.wpl_propToolOpts
		# if wpl_propToolOpts.mdf_srcbody not in bpy.data.objects.keys():
			# self.report({'INFO'}, 'No source')
			# return {"CANCELLED"}
		# active_obj = bpy.data.objects[wpl_propToolOpts.mdf_srcbody]
		# sel_all = [o.name for o in bpy.context.selected_objects]
		# if len(sel_all) == 0:
			# self.report({'ERROR'}, "No objects selected")
			# return {'CANCELLED'}
		# ok = 0
		# select_and_change_mode(active_obj,"OBJECT")
		# mod_params = None
		# for md in active_obj.modifiers:
			# if md.type == 'ARMATURE':
				# mod_params = {}
				# mod_params["name"] = md.name
				# mod_params["type"] = md.type
				# mod_params["settings_list"] = ["vertex_group","use","object","show"]
				# mod_params["settings"] = {}
				# copyBpyStructFields(md, mod_params["settings"], mod_params["settings_list"],None)
				# break
		# if mod_params is None:
			# self.report({'ERROR'}, "No modifier found on source")
			# return {'CANCELLED'}
		# for i, sel_obj_name in enumerate(sel_all):
			# sel_obj = context.scene.objects[sel_obj_name]
			# if sel_obj.name == active_obj.name:
				# continue
			# if sel_obj.type != 'MESH':
				# continue
			# new_modifier = None
			# for md in sel_obj.modifiers:
				# if md.name == mod_params["name"] and md.type == mod_params["type"]:
					# new_modifier = md
					# break
			# if new_modifier is None:
				# new_modifier = sel_obj.modifiers.new(mod_params["name"], mod_params["type"])
			# if mod_params["type"] == 'ARMATURE':
				# copyBpyStructFields(mod_params["settings"], new_modifier, mod_params["settings_list"], None)
				# modfSendBackByType(sel_obj, 'SUBSURF')
			# ok = ok+1
		# self.report({'INFO'}, "Transferred to "+str(ok)+" objects")
		# return {'FINISHED'}

# class wplbind_bind2surf_o(bpy.types.Operator):
# 	bl_idname = "object.wplbind_bind2surf_o"
# 	bl_label = "Bind object 2 surface"
# 	bl_options = {'REGISTER', 'UNDO'}

# 	def invoke(self, context, event):
# 		if bpy.context.mode != 'OBJECT':
# 			self.opt_onlySelection = True
# 		elif bpy.context.mode == 'OBJECT':
# 			self.opt_onlySelection = False
# 		return self.execute(context)

# 	def execute(self, context):
# 		wpl_propToolOpts = context.scene.wpl_propToolOpts
# 		cage_object = None
# 		try:
# 			cage_object = context.scene.objects[wpl_propToolOpts.mdf_srcbody]
# 		except:
# 			pass
# 		if cage_object is None or cage_object.type != 'MESH':
# 			self.report({'ERROR'}, "No proper cage found")
# 			return {'CANCELLED'}
# 		#if modfGetByType(cage_object,'MIRROR'):
# 		#	self.report({'INFO'}, 'Cage has Mirror modifier')
# 		#	return {"CANCELLED"}
# 		cage_mesh = cage_object.data
# 		sel_all = []
# 		for sel_obj in bpy.context.selected_objects:
# 			sel_obj_name = sel_obj.name
# 			sel_all.append(sel_obj_name)
# 		if setBmPinmap(cage_object, kWPLBindmapUV) == 0:
# 			self.report({'ERROR'}, "Can`t create pinmap")
# 			return {'CANCELLED'}
# 		okCnt = 0
# 		bm = bmesh.new()
# 		bm.from_mesh(cage_mesh)
# 		bm.verts.ensure_lookup_table()
# 		bm.faces.ensure_lookup_table()
# 		bm.verts.index_update()
# 		cage_tree = mathutils.kdtree.KDTree(len(bm.verts))
# 		for v in bm.verts:
# 			cage_tree.insert(cage_object.matrix_world*v.co, v.index)
# 		cage_tree.balance()
# 		for i, sel_obj_name in enumerate(sel_all):
# 			sel_obj = context.scene.objects[sel_obj_name]
# 			pt_co0 = sel_obj.matrix_world*Vector((0,0,0))
# 			pt_coX = sel_obj.matrix_world*Vector((1,0,0))
# 			pt_coY = sel_obj.matrix_world*Vector((0,1,0))
# 			pt_coZ = sel_obj.matrix_world*Vector((0,0,1))
# 			nearpts = cage_tree.find_n(pt_co0, 3)
# 			if nearpts is not None:
# 				nearpts.sort(key=lambda np: np[2], reverse=False)
# 				idx1 = nearpts[0][1]
# 				idx2 = nearpts[1][1]
# 				idx3 = nearpts[2][1]
# 				gp1 = nearpts[0][0]
# 				gp2 = nearpts[1][0]
# 				gp3 = nearpts[2][0]
# 				bind_item = [[idx1, idx2, idx3], [pt_co0[0], pt_co0[1], pt_co0[2]], [pt_coX[0], pt_coX[1], pt_coX[2]], [pt_coY[0], pt_coY[1], pt_coY[2]], [pt_coZ[0], pt_coZ[1], pt_coZ[2]], [gp1[0], gp1[1], gp1[2]], [gp2[0], gp2[1], gp2[2]], [gp3[0], gp3[1], gp3[2]]]
# 				sel_obj[kWPLBindmapOCP] = bind_item
# 				okCnt = okCnt+1
				
# 		bm.to_mesh(cage_mesh)
# 		self.report({'INFO'}, "Done, objects="+str(okCnt))
# 		return {'FINISHED'}


# class wplbind_align2surf_o(bpy.types.Operator):
# 	bl_idname = "object.wplbind_align2surf_o"
# 	bl_label = "Align object 2 binding"
# 	bl_options = {'REGISTER', 'UNDO'}

# 	def execute(self, context):
# 		wpl_propToolOpts = context.scene.wpl_propToolOpts
# 		cage_object = None
# 		try:
# 			cage_object = context.scene.objects[wpl_propToolOpts.mdf_srcbody]
# 		except:
# 			pass
# 		if cage_object is None or cage_object.type != 'MESH':
# 			self.report({'ERROR'}, "No proper cage found")
# 			return {'CANCELLED'}
# 		cage_mesh = cage_object.data
# 		sel_all = []
# 		for sel_obj in bpy.context.selected_objects:
# 			if kWPLBindmapOCP not in sel_obj:
# 				continue
# 			sel_obj_name = sel_obj.name
# 			sel_all.append(sel_obj_name)

# 		okCnt = 0
# 		subsurf = modfGetByType(cage_object,'SUBSURF')
# 		if subsurf is not None:
# 			print("- disabling subsurf on the cage")
# 			subsurf.show_viewport = False
# 		bm = bmesh.new()
# 		bm.from_object(cage_object, bpy.context.scene, deform=True, render=False, cage=False, face_normals=False)
# 		bm.verts.ensure_lookup_table()
# 		bm.faces.ensure_lookup_table()
# 		bm.verts.index_update()
# 		(verts_snap_map,verts_snap_nrm_map,verts_se_map,_,verts_odx_map_inv) = getBmPinmap(cage_object, bm, kWPLBindmapUV)
# 		if verts_snap_map is None:
# 			self.report({'ERROR'}, "Cage not pinned")
# 			return {'CANCELLED'}
# 		for i, sel_obj_name in enumerate(sel_all):
# 			sel_obj = context.scene.objects[sel_obj_name]
# 			bind_inf = sel_obj[kWPLBindmapOCP]
# 			print("- Applying for",sel_obj_name)
# 			if len(bind_inf) > 0:
# 				rep_idxs = bind_inf[0]
# 				pn_pos0_g = Vector((bind_inf[1][0], bind_inf[1][1], bind_inf[1][2]))
# 				pn_posX_g = Vector((bind_inf[2][0], bind_inf[2][1], bind_inf[2][2]))
# 				pn_posY_g = Vector((bind_inf[3][0], bind_inf[3][1], bind_inf[3][2]))
# 				pn_posZ_g = Vector((bind_inf[4][0], bind_inf[4][1], bind_inf[4][2]))
# 				rep1_pos_g = Vector((bind_inf[5][0], bind_inf[5][1], bind_inf[5][2]))
# 				rep2_pos_g = Vector((bind_inf[6][0], bind_inf[6][1], bind_inf[6][2]))
# 				rep3_pos_g = Vector((bind_inf[7][0], bind_inf[7][1], bind_inf[7][2]))
# 				odx1_idx = rep_idxs[0]
# 				odx2_idx = rep_idxs[1]
# 				odx3_idx = rep_idxs[2]
# 				if odx1_idx not in verts_odx_map_inv or odx2_idx not in verts_odx_map_inv or odx3_idx not in verts_odx_map_inv:
# 					continue
# 				vert1 = bm.verts[verts_odx_map_inv[odx1_idx][0]]
# 				v1_co = cage_object.matrix_world*vert1.co
# 				vert2 = bm.verts[verts_odx_map_inv[odx2_idx][0]]
# 				v2_co = cage_object.matrix_world*vert2.co
# 				vert3 = bm.verts[verts_odx_map_inv[odx3_idx][0]]
# 				v3_co = cage_object.matrix_world*vert3.co
# 				pn_trl0 = mathutils.geometry.barycentric_transform(pn_pos0_g,rep1_pos_g,rep2_pos_g,rep3_pos_g,v1_co,v2_co,v3_co)
# 				pn_trlZ = mathutils.geometry.barycentric_transform(pn_posZ_g,rep1_pos_g,rep2_pos_g,rep3_pos_g,v1_co,v2_co,v3_co)
# 				#v_co = cage_object.matrix_world*vert.co # global position
# 				#v_nm = (cage_object.matrix_world.inverted().transposed().to_3x3() * vert.normal).normalized() # global normal
# 				v_nm = (pn_trlZ-pn_trl0).normalized()
# 				sel_rot_quat = v_nm.to_track_quat('Z', 'Y')
# 				aLoc, aRot, aSca = sel_obj.matrix_world.decompose()
# 				aLocM = mathutils.Matrix.Translation(pn_trl0)
# 				aRotM = sel_rot_quat.to_matrix().to_4x4()
# 				aScaM = Matrix().Scale(aSca[0], 4, Vector((1,0,0)))
# 				aScaM *= Matrix().Scale(aSca[1], 4, Vector((0,1,0)))
# 				aScaM *= Matrix().Scale(aSca[2], 4, Vector((0,0,1)))
# 				sel_obj.matrix_world = aLocM * aRotM * aScaM
# 				sel_obj.rotation_mode = 'XYZ'
# 				okCnt = okCnt+1
# 		self.report({'INFO'}, "Done, objects="+str(okCnt))
# 		return {'FINISHED'}

# class wplbind_bind2surf_c(bpy.types.Operator):
# 	bl_idname = "object.wplbind_bind2surf_c"
# 	bl_label = "Bind curve 2 surface"
# 	bl_options = {'REGISTER', 'UNDO'}

# 	opt_onlySelection = BoolProperty(
# 		name="Only Selected",
# 		default=True
# 	)

# 	def invoke(self, context, event):
# 		if bpy.context.mode != 'OBJECT':
# 			self.opt_onlySelection = True
# 		elif bpy.context.mode == 'OBJECT':
# 			self.opt_onlySelection = False
# 		return self.execute(context)

# 	def execute(self, context):
# 		wpl_propToolOpts = context.scene.wpl_propToolOpts
# 		cage_object = None
# 		try:
# 			cage_object = context.scene.objects[wpl_propToolOpts.mdf_srcbody]
# 		except:
# 			pass
# 		if cage_object is None or cage_object.type != 'MESH':
# 			self.report({'ERROR'}, "No proper cage found")
# 			return {'CANCELLED'}
# 		#if modfGetByType(cage_object,'MIRROR'):
# 		#	self.report({'INFO'}, 'Cage has Mirror modifier')
# 		#	return {"CANCELLED"}
# 		cage_mesh = cage_object.data
# 		sel_all = []
# 		for sel_obj in bpy.context.selected_objects:
# 			if sel_obj.type != 'CURVE':
# 				continue
# 			#if modfGetByType(sel_obj,'MIRROR'):
# 			#	self.report({'INFO'}, 'Curve has Mirror modifier')
# 			#	return {"CANCELLED"}
# 			sel_obj_name = sel_obj.name
# 			sel_all.append(sel_obj_name)
# 		if setBmPinmap(cage_object, kWPLBindmapUV) == 0:
# 			self.report({'ERROR'}, "Can`t create pinmap")
# 			return {'CANCELLED'}
# 		okCnt = 0
# 		bm = bmesh.new()
# 		bm.from_mesh(cage_mesh)
# 		bm.verts.ensure_lookup_table()
# 		bm.faces.ensure_lookup_table()
# 		bm.verts.index_update()
# 		cage_tree = mathutils.kdtree.KDTree(len(bm.verts))
# 		for v in bm.verts:
# 			cage_tree.insert(cage_object.matrix_world*v.co, v.index)
# 		cage_tree.balance()
# 		for i, sel_obj_name in enumerate(sel_all):
# 			sel_obj = context.scene.objects[sel_obj_name]
# 			curveData = sel_obj.data
# 			bind_list = []
# 			for i, polyline in enumerate(curveData.splines):
# 				if polyline.type == 'NURBS' or polyline.type == 'POLY':
# 					for j, pt in enumerate(polyline.points):
# 						if self.opt_onlySelection and not pt.select:
# 							continue
# 						if pt.hide > 0:
# 							continue
# 						pt_co = sel_obj.matrix_world*Vector((pt.co[0],pt.co[1],pt.co[2]))
# 						nearpts = cage_tree.find_n(pt_co, 3)
# 						if nearpts is not None and len(nearpts) == 3:
# 							nearpts.sort(key=lambda np: np[2], reverse=False)
# 							idx1 = nearpts[0][1]
# 							idx2 = nearpts[1][1]
# 							idx3 = nearpts[2][1]
# 							gp1 = nearpts[0][0]
# 							gp2 = nearpts[1][0]
# 							gp3 = nearpts[2][0]
# 							bind_item = [[i, j], [idx1, idx2, idx3], [pt_co[0], pt_co[1], pt_co[2]], [gp1[0], gp1[1], gp1[2]], [gp2[0], gp2[1], gp2[2]], [gp3[0], gp3[1], gp3[2]]]
# 							bind_list.append(bind_item)
# 							okCnt = okCnt+1
# 			sel_obj[kWPLBindmapCCP] = bind_list
# 		bm.to_mesh(cage_mesh)
# 		self.report({'INFO'}, "Done, points="+str(okCnt))
# 		return {'FINISHED'}

# class wplbind_align2surf_c(bpy.types.Operator):
# 	bl_idname = "object.wplbind_align2surf_c"
# 	bl_label = "Align curve 2 binding"
# 	bl_options = {'REGISTER', 'UNDO'}

# 	opt_useNearest = BoolProperty(
# 		name	= "Snap2nearest",
# 		default	= False
# 	)

# 	def execute(self, context):
# 		wpl_propToolOpts = context.scene.wpl_propToolOpts
# 		cage_object = None
# 		try:
# 			cage_object = context.scene.objects[wpl_propToolOpts.mdf_srcbody]
# 		except:
# 			pass
# 		if cage_object is None or cage_object.type != 'MESH':
# 			self.report({'ERROR'}, "No proper cage found")
# 			return {'CANCELLED'}
# 		cage_mesh = cage_object.data
# 		sel_all = []
# 		for sel_obj in bpy.context.selected_objects:
# 			if sel_obj.type != 'CURVE':
# 				continue
# 			if kWPLBindmapCCP not in sel_obj:
# 				continue
# 			sel_obj_name = sel_obj.name
# 			sel_all.append(sel_obj_name)

# 		okCnt = 0
# 		subsurf = modfGetByType(cage_object,'SUBSURF')
# 		if subsurf is not None:
# 			print("- disabling subsurf on the cage")
# 			subsurf.show_viewport = False
# 		bm = bmesh.new()
# 		bm.from_object(cage_object, bpy.context.scene, deform=True, render=False, cage=False, face_normals=False)
# 		bm.verts.ensure_lookup_table()
# 		bm.faces.ensure_lookup_table()
# 		bm.verts.index_update()
# 		(verts_snap_map,verts_snap_nrm_map,verts_se_map,_,verts_odx_map_inv) = getBmPinmap(cage_object, bm, kWPLBindmapUV)
# 		if verts_snap_map is None:
# 			self.report({'ERROR'}, "Cage not pinned")
# 			return {'CANCELLED'}
# 		for i, sel_obj_name in enumerate(sel_all):
# 			sel_obj = context.scene.objects[sel_obj_name]
# 			curveData = sel_obj.data
# 			print("- Applying for",sel_obj_name)
# 			bind_list = sel_obj[kWPLBindmapCCP]
# 			for i, polyline in enumerate(curveData.splines):
# 				if polyline.type == 'NURBS' or polyline.type == 'POLY':
# 					for j, pt in enumerate(polyline.points):
# 						for bind_inf in bind_list:
# 							spl_pn = bind_inf[0]
# 							if spl_pn[0] != i or spl_pn[1] != j:
# 								continue
# 							rep_idxs = bind_inf[1]
# 							pn_pos_g = Vector((bind_inf[2][0], bind_inf[2][1], bind_inf[2][2]))
# 							rep1_pos_g = Vector((bind_inf[3][0], bind_inf[3][1], bind_inf[3][2]))
# 							rep2_pos_g = Vector((bind_inf[4][0], bind_inf[4][1], bind_inf[4][2]))
# 							rep3_pos_g = Vector((bind_inf[5][0], bind_inf[5][1], bind_inf[5][2]))
# 							odx1_idx = rep_idxs[0]
# 							odx2_idx = rep_idxs[1]
# 							odx3_idx = rep_idxs[2]
# 							if odx1_idx not in verts_odx_map_inv or odx2_idx not in verts_odx_map_inv or odx3_idx not in verts_odx_map_inv:
# 								continue
# 							vert1 = bm.verts[verts_odx_map_inv[odx1_idx][0]]
# 							v1_co = cage_object.matrix_world*vert1.co
# 							vert2 = bm.verts[verts_odx_map_inv[odx2_idx][0]]
# 							v2_co = cage_object.matrix_world*vert2.co
# 							vert3 = bm.verts[verts_odx_map_inv[odx3_idx][0]]
# 							v3_co = cage_object.matrix_world*vert3.co
# 							if self.opt_useNearest:
# 								pn_trl = v1_co
# 								pn_trl_local = sel_obj.matrix_world.inverted() * pn_trl
# 							else:
# 								pn_trl = mathutils.geometry.barycentric_transform(pn_pos_g,rep1_pos_g,rep2_pos_g,rep3_pos_g,v1_co,v2_co,v3_co)
# 								pn_trl_local = sel_obj.matrix_world.inverted() * pn_trl
# 							pt.co = (pn_trl_local[0], pn_trl_local[1], pn_trl_local[2], 1)
# 							okCnt = okCnt+1
# 		self.report({'INFO'}, "Done, points="+str(okCnt))
# 		return {'FINISHED'}
		
class wplbind_bind2surf_m(bpy.types.Operator):
	bl_idname = "object.wplbind_bind2surf_m"
	bl_label = "Bind mesh 2 surface"
	bl_options = {'REGISTER', 'UNDO'}

	opt_pinId = StringProperty(
		name		= "Pin ID",
		default	 	= "fastpin_uv"
	)
	opt_uvName = StringProperty(
		name = "Cage UV",
		default = kWPLEdgeFlowUV
	)

	def execute(self, context):
		wpl_propToolOpts = context.scene.wpl_propToolOpts
		cage_object = None
		try:
			cage_object = context.scene.objects[wpl_propToolOpts.mdf_srcbody]
		except:
			pass
		if cage_object is None or cage_object.type != 'MESH':
			self.report({'ERROR'}, "No proper cage found")
			return {'CANCELLED'}
		if modfGetByType(cage_object,'MIRROR'):
			self.report({'INFO'}, 'Cage has Mirror modifier')
			return {"CANCELLED"}
		active_obj = context.scene.objects.active
		sel_all = []
		for sel_obj in bpy.context.selected_objects:
			if sel_obj.type != 'MESH' or sel_obj.name == cage_object.name:
				continue
			if modfGetByType(sel_obj,'MIRROR'):
				self.report({'INFO'}, 'Bind mesh has Mirror modifier')
				return {"CANCELLED"}
			sel_all.append(sel_obj.name)
		select_and_change_mode(cage_object, 'EDIT')
		bm_cage = bmesh.from_edit_mesh(cage_object.data)
		pins_v = setBmPinmapFastUV(cage_object, bm_cage, self.opt_pinId, self.opt_uvName)
		select_and_change_mode(cage_object, 'OBJECT')
		if pins_v is None:
			self.report({'INFO'}, 'Cage does not have UV or duplicates found')
			return {"CANCELLED"}
		self.report({'INFO'}, "Done")
		return {'FINISHED'}

class wplbind_align2surf_m(bpy.types.Operator):
	bl_idname = "object.wplbind_align2surf_m"
	bl_label = "Align mesh 2 binding"
	bl_options = {'REGISTER', 'UNDO'}

	opt_wightsPow = FloatProperty(
		name="Weights pow",
		default=2.0,
	)
	opt_nearVerts = IntProperty(
			name="Base verts count",
			min=2, max=100,
			default = 15,
	)
	opt_pinId = StringProperty(
		name		= "Pin ID",
		default	 	= "fastpin_uv"
	)
	opt_uvName = StringProperty(
		name = "Cage UV",
		default = kWPLEdgeFlowUV
	)

	def execute(self, context):
		wpl_propToolOpts = context.scene.wpl_propToolOpts
		cage_object = None
		try:
			cage_object = context.scene.objects[wpl_propToolOpts.mdf_srcbody]
		except:
			pass
		if cage_object is None or cage_object.type != 'MESH':
			self.report({'ERROR'}, "No proper cage found")
			return {'CANCELLED'}
		cage_mesh = cage_object.data
		sel_all = []
		for sel_obj in bpy.context.selected_objects:
			if sel_obj.type != 'MESH' or sel_obj.name == cage_object.name:
				continue
			sel_all.append(sel_obj.name)
		if len(sel_all) == 0:
			self.report({'INFO'}, "Dry run")
			return {'FINISHED'}
		okCnt = 0
		allCnt = 0
		m_subsurf = modfGetByType(cage_object,'SUBSURF')
		if m_subsurf is not None:
			print("- disabling subsurf on the cage")
			m_subsurf.show_viewport = False
		select_and_change_mode(cage_object, 'EDIT')
		bm_cage = bmesh.from_edit_mesh(cage_object.data)
		cage_verts_dt = getBmPinmapFastUV(cage_object, bm_cage, self.opt_pinId, self.opt_uvName)
		if cage_verts_dt is None:
			select_and_change_mode(cage_object, 'OBJECT')
			self.report({'ERROR'}, "Cage not pinned")
			return {'CANCELLED'}
		cage_mw_inv = cage_object.matrix_world.inverted()
		cage_mw_nrml = cage_mw_inv.transposed().to_3x3()
		cage_tree_orig = mathutils.kdtree.KDTree(len(bm_cage.verts))
		cage_vert_nrm = {}
		for cage_v_idx in cage_verts_dt.keys():
			if bm_cage.verts[cage_v_idx].hide:
				continue
			cage_tree_orig.insert(cage_verts_dt[cage_v_idx]["co_g"], cage_v_idx)
			cage_vert_nrm[cage_v_idx] = copy.copy(cage_verts_dt[cage_v_idx]["no_g"])
		cage_vert_co = {}
		cage_vert_no = {}
		for cv in bm_cage.verts:
			cage_vert_co[cv.index] = copy.copy(cv.co)
			cage_vert_no[cv.index] = copy.copy(cv.normal)
		cage_tree_orig.balance()
		select_and_change_mode(cage_object, 'OBJECT')
		for i, sel_obj_name in enumerate(sel_all):
			sel_obj = context.scene.objects[sel_obj_name]
			m_bevel = modfGetByType(sel_obj,'BEVEL')
			if m_bevel is not None:
				print("- disabling bevel on the mesh")
				m_bevel.show_viewport = False
			select_and_change_mode(sel_obj, 'OBJECT')
			meshData = sel_obj.data
			print("- Applying for", sel_obj_name, "allverts=", len(meshData.vertices))
			bind_list = {}
			for pt in meshData.vertices:
				pt_co_g = sel_obj.matrix_world * pt.co #sel_verts_dt[pt.index]["co_g"]
				nearpts = cage_tree_orig.find_n(pt_co_g, self.opt_nearVerts)
				if nearpts is not None and len(nearpts) > 1:
					nearpts.sort(key=lambda np: np[2], reverse=False)
					dist_min = nearpts[0][2]
					dist_max = nearpts[-1][2]
					cage_mw_zv = (nearpts[1][0]-nearpts[0][0]).normalized()
					bind_item = [[pt.index, nearpts[1][1], nearpts[0][1]]]
					for nearpt in nearpts:
						gp_idx1 = nearpt[1]
						v_cage_nrm = cage_vert_nrm[gp_idx1]
						gp1 = nearpt[0]
						gp1_n1 = v_cage_nrm.normalized()
						gp1_n2 = gp1_n1.cross(cage_mw_zv).normalized()
						gp_sm1 = customAxisMatrix(Vector((0,0,0)),gp1_n1,gp1_n2)
						if gp_sm1 is None:
							print("- can`t bind to vert (CAM=null)", gp_idx1)
							continue
						pt_co_cm = gp_sm1.inverted()*(pt_co_g - gp1)
						pt_co_cm_dist = (pt_co_g-gp1).length
						pt_co_cm_wei = 1.0 - (pt_co_cm_dist-dist_min)/(dist_max-dist_min)
						bind_item.append([gp_idx1, pt_co_cm[0], pt_co_cm[1], pt_co_cm[2], pt_co_cm_wei])
					bind_list[pt.index] = bind_item
			vertCo = {}
			for pt in meshData.vertices:
				allCnt = allCnt+1
				if pt.index not in bind_list:
					continue
				bind_inf = bind_list[pt.index]
				spl_pn = bind_inf[0]
				if spl_pn[0] != pt.index:
					continue
				cage_mw_zv_p1 = spl_pn[1]
				cage_mw_zv_p2 = spl_pn[2]
				if cage_mw_zv_p1 not in cage_verts_dt or cage_mw_zv_p2 not in cage_verts_dt: #cage_verts_inv
					print("- unknown vert found (cageMw)", cage_mw_zv_p1, cage_mw_zv_p2)
					continue
				cage_mw_zv_p1_now = cage_mw_zv_p1 #cage_verts_inv[cage_mw_zv_p1]
				cage_mw_zv_v1_now_co = cage_vert_co[cage_mw_zv_p1_now]
				cage_mw_zv_p2_now = cage_mw_zv_p2 #cage_verts_inv[cage_mw_zv_p2]
				cage_mw_zv_v2_now_co = cage_vert_co[cage_mw_zv_p2_now]
				cage_mw_zv = (cage_object.matrix_world*cage_mw_zv_v1_now_co-cage_object.matrix_world*cage_mw_zv_v2_now_co).normalized()
				l_coords_xyz = []
				l_coords_wei = []
				l_coords_wei_sum = 0
				for bind_inf_v in bind_inf[1:]:
					odx1_idx = bind_inf_v[0]
					if odx1_idx not in cage_verts_dt: #cage_verts_inv
						print("- unknown vert found (odx)",odx1_idx)
						continue
					gp_idx1 = odx1_idx #cage_verts_inv[odx1_idx]
					vert1_co = cage_vert_co[gp_idx1]
					gp_idx1_no = cage_vert_no[gp_idx1]
					gp1 = cage_object.matrix_world*vert1_co
					gp1_n1 = (cage_mw_nrml * gp_idx1_no).normalized()
					gp1_n2 = gp1_n1.cross(cage_mw_zv).normalized()
					gp_sm1 = customAxisMatrix(Vector((0,0,0)),gp1_n1,gp1_n2)
					pt_co_cm = Vector((bind_inf_v[1], bind_inf_v[2], bind_inf_v[3]))
					pn_trl = gp1 + (gp_sm1 * pt_co_cm)
					pn_trl_local = sel_obj.matrix_world.inverted() * pn_trl
					l_coords_wei_sum = l_coords_wei_sum+bind_inf_v[4]
					l_coords_xyz.append(pn_trl_local)
					l_coords_wei.append(pow(bind_inf_v[4],self.opt_wightsPow))
				#if pt.select:
				#	print("-",gp1,pt_co_cm,pn_trl_local,(pn_trl_local-pt.co).length)
				if len(l_coords_xyz)>0 and l_coords_wei_sum > 0.0:
					x = np.average([co[0] for co in l_coords_xyz],weights=l_coords_wei)
					y = np.average([co[1] for co in l_coords_xyz],weights=l_coords_wei)
					z = np.average([co[2] for co in l_coords_xyz],weights=l_coords_wei)
					vertCo[pt.index] = Vector((x,y,z)) #pt_locals/pt_locals_cnt
			for vIdx in vertCo:
				okCnt = okCnt+1
				v = meshData.vertices[vIdx]
				v.co = vertCo[vIdx]
		self.report({'INFO'}, "Done, points="+str(okCnt)+"/"+str(allCnt))
		return {'FINISHED'}

class wplbind_applytransf(bpy.types.Operator):
	# Also used in joined mesh duplication
	bl_idname = "object.wplbind_applytransf"
	bl_label = "Finalize objects"
	bl_options = {'REGISTER', 'UNDO'}

	opt_applyMirror = bpy.props.BoolProperty(
		name		= "Apply mirror (if any)",
		default	 = True
		)
	opt_applyArmat = bpy.props.BoolProperty(
		name		= "Apply armature (if any)",
		default	 = True
		)
	opt_applyHooks = bpy.props.BoolProperty(
		name		= "Apply hooks (if any)",
		default	 = True
		)
	opt_applyShrinks = bpy.props.BoolProperty(
		name		= "Apply shrinks (if any)",
		default	 = True
		)
	opt_applyConstrs = bpy.props.BoolProperty(
		name		= "Remove constraints (if any)",
		default	 = False
		)

	@classmethod
	def poll( cls, context ):
		return ( context.object is not None)

	def execute( self, context ):
		sel_all = [o.name for o in bpy.context.selected_objects]
		if len(sel_all) == 0:
			self.report({'ERROR'}, "No objects selected")
			return {'CANCELLED'}
		changesCount = 0
		for i, sel_obj_name in enumerate(sel_all):
			active_obj = context.scene.objects.get(sel_obj_name)
			if active_obj.type == 'MESH' and active_obj.data.shape_keys is not None and len(active_obj.data.shape_keys.key_blocks)>0:
				#self.report({'ERROR'}, "Some objects has shapekeys: "+active_obj.name)
				#return {'CANCELLED'}
				for shkn in range(0,len(active_obj.data.shape_keys.key_blocks)):
					active_obj.active_shape_key_index = 0
					sk = active_obj.data.shape_keys.key_blocks[active_obj.active_shape_key_index]
					active_obj.shape_key_remove(sk)
		for i, sel_obj_name in enumerate(sel_all):
			active_obj = context.scene.objects.get(sel_obj_name)
			if active_obj.type == 'ARMATURE':
				continue
			if active_obj.library is not None or active_obj.hide_select:
				continue
			print("Finalizing",active_obj.name)
			if active_obj.type == 'MESH':
				active_obj.data.use_mirror_x = False
				active_obj.data.use_mirror_topology = False
			select_and_change_mode(active_obj,"OBJECT")
			if self.opt_applyConstrs == True and len(active_obj.constraints)>0:
				bpy.ops.object.visual_transform_apply()
				for c in active_obj.constraints:
					if kWPLFrameBindPostfix in c.name:
						continue # This constraint is needed
					active_obj.constraints.remove(c)
			#try:
			applMods = []
			remvMods = []
			changeOrigin = True
			mirrorMd = None
			for md in active_obj.modifiers:
				if md.show_viewport == False and md.show_render == False:
					continue
				if self.opt_applyMirror == True and md.type == 'MIRROR':
					mirrorMd = md
				if self.opt_applyHooks == True and md.type == 'HOOK':
					applMods.append(md.name)
				if self.opt_applyHooks == True and md.type == 'MESH_DEFORM':
					applMods.append(md.name)
				if self.opt_applyHooks == True and md.type == 'LATTICE':
					applMods.append(md.name)
				if self.opt_applyHooks == True and md.type == 'SURFACE_DEFORM' and active_obj.type == 'MESH':
					applMods.append(md.name)
				if self.opt_applyMirror == True and md.type == 'MIRROR' and active_obj.type == 'MESH':
					applMods.append(md.name)
				if self.opt_applyArmat == True and md.type == 'CORRECTIVE_SMOOTH' and active_obj.type == 'MESH':
					applMods.append(md.name)
				if self.opt_applyArmat == True and md.type == 'ARMATURE':
					applMods.append(md.name)
				if self.opt_applyArmat == True and md.type == 'SKIN':
					applMods.append(md.name)
				if self.opt_applyShrinks == True and (md.type == 'SHRINKWRAP' or md.type == 'SMOOTH' or md.type == 'DISPLACE' or md.type == 'SIMPLE_DEFORM'):
					applMods.append(md.name)
			for mdname in applMods:
				print("- Applying",mdname)
				md = active_obj.modifiers.get(mdname)
				bpy.ops.object.modifier_apply(apply_as='DATA', modifier=mdname)
			if mirrorMd is not None and active_obj.type == 'CURVE':
				print("- Manual mirror")
				remvMods.append(mirrorMd)
				curveXMirror(active_obj,False)
				select_and_change_mode(active_obj,"OBJECT")
			for md in remvMods:
				active_obj.modifiers.remove(md)
			changesCount = changesCount+1
		self.report({'INFO'}, "Objects updated: "+str(changesCount)+" of "+str(len(sel_all)))
		return {'FINISHED'}

class wplbind_apply2shk(bpy.types.Operator):
	bl_idname = "object.wplbind_apply2shk"
	bl_label = "Finalize to Shapekey"
	bl_options = {'REGISTER', 'UNDO'}

	opt_pinId = StringProperty(
		name		= "Pin ID",
		default	 	= "fastpin_uv"
	)
	opt_uvName = StringProperty(
		name = "Cage UV",
		default = kWPLEdgeFlowUV
	)
	# opt_addExtraMaps = bpy.props.BoolProperty(
	# 	name		= "Generate extra maps",
	# 	default	 = True
	# )

	@classmethod
	def poll( cls, context ):
		return ( context.object is not None and
				context.object.type == 'MESH')

	def execute( self, context ):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		if modfGetByType(active_obj,'MIRROR'):
			self.report({'ERROR'}, "Object has MIRROR:")
			return {'FINISHED'}
		if active_obj.data.users > 1:
			# shapekeys are per mesh data
			bpy.ops.object.make_single_user(object=False, obdata=True)
		# if self.opt_addExtraMaps:
		# 	bpy.ops.object.wpluvvg_unwrap_edges(opt_tranfType='DST_PRJ') # WPL
		# 	bpy.ops.object.wpluvvg_unwrap_bonenrm() # WPL
		obj_modstate = {}
		toggleModifs(active_obj,['MASK','ARRAY','SOLIDIFY','SUBSURF','BEVEL'],False,obj_modstate)
		# select_and_change_mode(active_obj, 'EDIT')
		# bm_cage = bmesh.from_edit_mesh(active_mesh)
		# pins_v = setBmPinmapFastUV(active_obj, bm_cage, self.opt_pinId, self.opt_uvName)
		# select_and_change_mode(active_obj, 'OBJECT')
		# if pins_v is None:
		# 	self.report({'INFO'}, 'Cage does not have UV or duplicates found')
		# 	return {"CANCELLED"}
		bm_deformed = bmesh.new()
		bm_deformed.from_object(active_obj, context.scene, deform=True, render=False, cage=False, face_normals=True)
		bm_deformed.verts.ensure_lookup_table()
		bm_deformed.verts.index_update()
		# cage_verts_dt = getBmPinmapFastUV(active_obj, bm_deformed, self.opt_pinId, self.opt_uvName)
		if active_obj.data.shape_keys is None or len(active_obj.data.shape_keys.key_blocks) == 0:
			sk_basis = active_obj.shape_key_add('Basis', from_mix=False)
			sk_basis.interpolation = 'KEY_LINEAR'
			active_obj.data.shape_keys.use_relative = True
		active_obj.active_shape_key_index = len(active_obj.data.shape_keys.key_blocks)
		sk = active_obj.shape_key_add(kWPLFinShapekeyPrefix + kWPLFrameBindPostfix + str(bpy.context.scene.frame_current), from_mix=False)
		sk.interpolation = 'KEY_LINEAR'
		for poly in active_mesh.polygons:
			for loop_index in range(poly.loop_start, poly.loop_start + poly.loop_total):
				vi = active_mesh.loops[loop_index].vertex_index
				sk.data[vi].co = copy.copy(bm_deformed.verts[vi].co)
		# disabling modfs+enabling shapekey
		for md in active_obj.modifiers:
			md.show_render = False
			md.show_viewport = False
		sk.value = 1.0 # activate
		toggleModifs(active_obj,['MASK','ARRAY','SOLIDIFY','SUBSURF','BEVEL'],None,obj_modstate)
		return {'FINISHED'}

# class wplbind_smoothv(bpy.types.Operator):
	# bl_idname = "mesh.wplbind_smoothv"
	# bl_label = "modf: Smooth selection"
	# bl_options = {'REGISTER', 'UNDO'}

	# opt_preDisplace = FloatProperty(
			# name="Predisplace",
			# min=0.0, max=1,
			# default=0.05,
	# )
	# opt_smoothXY = bpy.props.BoolProperty(
		# name		= "Smooth XY only",
		# default	 = False
	# )

	# @classmethod
	# def poll( cls, context ):
		# return ( context.object is not None  and
				# context.object.type == 'MESH'  and
				# bpy.context.mode == 'EDIT_MESH')
	# def execute( self, context ):
		# active_obj = context.scene.objects.active
		# active_mesh = active_obj.data
		# vertsIdx = get_selected_vertsIdx(active_mesh)
		# if len(vertsIdx) == 0:
			# self.report({'ERROR'}, "No selected verts found")
			# return {'FINISHED'}
		# vg_name = 'wpl_smooth'+ str(getHelperObjId(context))
		# select_and_change_mode(active_obj, 'OBJECT')
		# group_c = active_obj.vertex_groups.new(name = vg_name)
		# group_c.add(vertsIdx, 1.0, 'ADD')
		# if abs(self.opt_preDisplace) > 0.0001:
			# displ_modifier = active_obj.modifiers.new(name = vg_name+'_displ', type = 'DISPLACE')
			# displ_modifier.vertex_group = group_c.name
			# displ_modifier.strength = self.opt_preDisplace
			# displ_modifier.show_render = True
			# displ_modifier.show_in_editmode = True
			# displ_modifier.show_on_cage = True
		# if self.opt_smoothXY:
			# smooth_modifier = active_obj.modifiers.new(name = vg_name, type = 'SMOOTH')
			# smooth_modifier.use_z = False
		# else:
			# smooth_modifier = active_obj.modifiers.new(name = vg_name, type = 'CORRECTIVE_SMOOTH')
			# smooth_modifier.smooth_type = 'LENGTH_WEIGHTED'
			# smooth_modifier.use_only_smooth = True
		# smooth_modifier.vertex_group = group_c.name
		# smooth_modifier.iterations = 50
		# smooth_modifier.show_render = True
		# smooth_modifier.show_in_editmode = True
		# smooth_modifier.show_on_cage = True
		# self.report({'INFO'}, "Verts smoothed: "+str(len(vertsIdx)))
		# return {'FINISHED'}

######### ############ ################# ############
class WPLPropToolSettings(bpy.types.PropertyGroup):
	mdf_srcbody = StringProperty(
		name="Body",
		default = ""
	)

class WPLPropTools_Panel1(bpy.types.Panel):
	bl_label = "Prop: Binding"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_category = 'WPL'

	def draw(self, context):
		layout = self.layout
		wpl_propToolOpts = context.scene.wpl_propToolOpts
		active_obj = context.scene.objects.active
		col = layout.column()

		box1 = col.box()
		finMirr = box1.operator("object.wplbind_applytransf", text="Finalize Mirror")
		finMirr.opt_applyConstrs = False
		finMirr.opt_applyMirror = True
		finMirr.opt_applyArmat = False
		finMirr.opt_applyHooks = False
		finMirr.opt_applyShrinks = False
		#finMirr.opt_addExtraMaps = False
		finAll = box1.operator("object.wplbind_applytransf", text="Finalize ALL")
		finAll.opt_applyConstrs = False
		finAll.opt_applyMirror = True
		finAll.opt_applyArmat = True
		finAll.opt_applyHooks = True
		finAll.opt_applyShrinks = True
		#finAll.opt_addExtraMaps = True
		finAll = box1.operator("object.wplbind_apply2shk", text="Finalize To Shapekey")
		box1.separator()
		box1.operator("object.wpluvvg_islandsmid") # WPL
		box1.operator("object.wpluvvg_unwrap_edges", text = "Generate Edges UV").opt_tranfType='DST_PRJ' # WPL
		box1.operator("object.wpluvvg_unwrap_bonenrm", text="Generate Bone normals") # WPL
		col.separator()
		box2 = col.box()
		box2.prop_search(wpl_propToolOpts, "mdf_srcbody", context.scene, "objects", icon="SNAP_NORMAL")
		box2.separator()
		#box2.operator("object.wplbind_bind2surf_o", text="Object: Bind to deformer")
		#box2.operator("object.wplbind_align2surf_o", text="Object: Restore binding")
		# if active_obj is not None and active_obj.type == 'CURVE':
		# 	box2.separator()
		# 	box2.operator("object.wplbind_bind2surf_c", text="Curve: Bind to deformer")
		# 	box2.operator("object.wplbind_align2surf_c", text="Curve: Restore binding")
		if active_obj is not None and (active_obj.type == 'MESH' or active_obj.type == 'EMPTY'):
			box2.separator()
			box2.operator("object.wplbind_bind2surf_m", text="Mesh: Bind to deformer")
			box2.operator("object.wplbind_align2surf_m", text="Mesh: Restore binding")

		#col.separator()
		#box1 = col.box()
		#box1.prop_search(wpl_propToolOpts, "mdf_srcbody", context.scene, "objects", icon="SNAP_NORMAL")
		#box1.operator("object.wplbind_cpymodifs")
		#box1.separator()
		#box1.operator("object.wplbind_datatransf", text="Transfer w-groups to selection").opt_tranfType = 'WEI'


def register():
	bpy.utils.register_module(__name__)
	bpy.types.Scene.wpl_propToolOpts = PointerProperty(type=WPLPropToolSettings)

def unregister():
	bpy.utils.unregister_module(__name__)
	del bpy.types.Scene.wpl_propToolOpts
	bpy.utils.unregister_class(WPLPropToolSettings)

if __name__ == "__main__":
	register()
