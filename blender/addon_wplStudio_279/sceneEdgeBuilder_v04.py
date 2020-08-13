# problems:
# - mess on sharp angles for flat surfaces

import math
import copy
import mathutils
import numpy as np
import time

import bpy
from bpy.props import *
import bpy.types
import bmesh
from mathutils import Vector, Matrix
from mathutils import kdtree
from mathutils.bvhtree import BVHTree


bl_info = {
	"name": "Scene Edge builder",
	"author": "IPv6",
	"version": (1, 2, 14),
	"blender": (2, 7, 9),
	"location": "View3D > T-panel > WPL",
	"description" : "",
	"warning"	 : "",
	"wiki_url"	: "",
	"tracker_url" : "",
	"category"	: "WPL"
	}

kWPLSystemLayer = 19
kWPLEdgeMaxVerts2check = 100000
kWPLDefaultEdgeProfile = (0.001,0.001,0.2)
kWPLEdgeBevelSize = 100.0/90000.0
kWPLEdgeAutoScale = {"_charb": 0.7, "_head": 0.8}
kWPLEdgeColVC = "DecorC"
kWPLEdgeSkipVC = "Detail"
# kWPLEdgeMapUV = "EdgeFeats"
kWPLEdgeMatName = "fg_marksEdges"
kWPLEdgesObjPostfix = "_edge"
kWPLHideMaskVGroup = "_hidegeom"
kWPLEdgesMainCam = "zzz_MainCamera"
kWPLEdgeOrthOffset = 10
kWPLEdgeSeamtiling = 0.05
kWPLNoEdgeObjects = "sys_,zzz_"
kWPLRaycastEpsilonCCL = 0.0001
kWPLFrameBindPostfix = "_##"

######################### ######################### #########################
######################### ######################### #########################
def moveObjectOnLayer(c_object, layId):
	def layers(l):
		all = [False]*20
		all[l]=True
		return all
	c_object.layers = layers(layId)

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

def get_isLocalView():
	is_local_view = sum(bpy.context.space_data.layers[:]) == 0 #if hairCurve.layers_local_view[0]:
	return is_local_view

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
		curveDist = 0
		for i,p in enumerate(poly):
			if pprev is not None:
				curveDist = curveDist+(p.co-pprev.co).length
			pprev = p
			curve_fac = 0.5
			if curveDistTotal > 0:
				#curve_fac = float(i) / (curveLength-1)
				curve_fac = curveDist / curveDistTotal
			if curve_fac<mid_fac:
				RadTotal = radiusAtStart+(1.0-radiusAtStart)*(curve_fac/mid_fac)
			else:
				RadTotal = radiusAtEnd+(1.0-radiusAtEnd)*(1.0-(curve_fac-mid_fac)/mid_fac)
			RadTotal = max(0.00001,RadTotal)
			RadTotal = pow(RadTotal,radiusPow)
			p.radius = RadTotal*baseRadius

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
	# find selected edges
	bpy.ops.object.mode_set(mode='OBJECT')
	selectedEdgesIdx = [e.index for e in active_mesh.edges if e.select]
	return selectedEdgesIdx
def get_selected_vertsIdx(active_mesh):
	# find selected faces
	bpy.ops.object.mode_set(mode='OBJECT')
	selectedVertsIdx = [e.index for e in active_mesh.vertices if e.select]
	return selectedVertsIdx
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

def get_vertgroup_by_name(obj,group_name):
	if group_name in obj.vertex_groups:
		return obj.vertex_groups[group_name]
	return None
def get_vertwg_by_name(obj,group_name):
	mask_vIdx = {}
	mask_group = get_vertgroup_by_name(obj, group_name)
	if mask_group is not None:
		for v in obj.data.vertices: #loop over all verts
			for n in v.groups: #loop over all groups with each vert
				if n.group == mask_group.index: #check if the group val is the same as the index value of the required vertex group
					mask_vIdx[v.index] = n.weight
	return mask_vIdx

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

def getBMeshVertLoops_v01(v, verts_set_out, max_loops):
	if (v in verts_set_out):
		return
	if v.hide:
		return
	verts_set_out.add(v)
	#for edge in v.link_edges:
	#	ov = edge.other_vert(v)
	#	if (ov is None) or (ov in verts_set_out):
	#		continue
	#	if max_loops > 0:
	#		getBMeshVertLoops_v01(ov, verts_set_out, max_loops-1)
	for f in v.link_faces:
		for ov in f.verts:
			if (ov is None) or (ov in verts_set_out):
				continue
			if max_loops > 0:
				getBMeshVertLoops_v01(ov, verts_set_out, max_loops-1)

def getBMeshVCMap(active_bmesh, vcname):
	vccols = {}
	color_map = None
	try:
		color_map = active_bmesh.loops.layers.color.get(vcname)
	except:
		pass
	if color_map is not None:
		for face in active_bmesh.faces:
			for loop in face.loops:
				ivdx = loop.vert.index
				color = loop[color_map]
				newc = [color[0],color[1],color[2]]
				if (ivdx in vccols):
					prevc = vccols[ivdx]
					newc[0] = max(newc[0],prevc[0])
					newc[1] = max(newc[1],prevc[1])
					newc[2] = max(newc[2],prevc[2])
				vccols[ivdx] = newc
	#print("getBMeshVCMap",vccols)
	return vccols

# https://blender.stackexchange.com/questions/16472/how-can-i-get-the-cameras-projection-matrix
def project_3d_point(camera, p):
	# Get the two components to calculate M
	#render = bpy.context.scene.render
	modelview_matrix = camera.matrix_world.inverted()
	projection_matrix = camera.calc_matrix_camera(
		10000, #render.resolution_x,
		10000, #render.resolution_y,
		1, #render.pixel_aspect_x,
		1, #render.pixel_aspect_y,
	)
	# Compute P’ = M * P
	p1 = projection_matrix * modelview_matrix * Vector((p.x, p.y, p.z, 1))
	# Normalize in: x’’ = x’ / w’, y’’ = y’ / w’
	p2 = Vector(((p1.x/p1.w, p1.y/p1.w)))
	return p2

def getEdgeVertsForObject(context, active_obj, active_bmesh, params):
	vertRaycShift = params["vertRaycShift"]
	vertMaxZdiff = params["vertMaxZdiff"]
	vertMaxLdiff = params["vertMaxLdiff"]
	vertRejoin = params["vertRejoin"]
	vertBounds2Edge = params["vertBounds2Edge"]
	vertSepmesh2Edge = params["vertSepmesh2Edge"]
	optmMaxInNoDot = params["optmMaxInNoDot"]
	optmEdgeTunnlDot = params["optmEdgeTunnlDot"]
	optmNormSmtDot = params["optmNormSmtDot"]
	optmNormOpdDot = params["optmNormOpdDot"]
	optmCurveFlowDot = params["optmCurveFlowDot"]
	camera_obj = params["camera_obj"]
	camera_gLoc = camera_obj.location
	#camera_gDir = Vector((0.0, 0.0, 1.0)) * camera_obj.matrix_world.to_3x3()
	camera_gDir = camera_obj.matrix_world.to_3x3() * Vector((0.0, 0.0, 1.0))
	camera_gDir = camera_gDir.normalized()
	camera_gOrtho = False
	if camera_obj.data.type == 'ORTHO':
		camera_gOrtho = True
	print("Camera",camera_obj.name,"loc:",camera_gLoc,"z:",camera_gDir,"ortho:",camera_gOrtho)
	if vertMaxLdiff<1:
		vertMaxLdiff = 1
	vertTstLdiff = 1
	vertRejLdiff = 1

	active_bmesh.transform(active_obj.matrix_world)
	active_bmesh.normal_update() # updates normals to global space!!!
	#bmesh.ops.recalc_face_normals(active_bmesh, faces=active_bmesh.faces) # No! break some carefully manual-swapped normals
	#matrix_world_inv = active_obj.matrix_world.inverted()
	camera_lCo = camera_gLoc # since bmesh in global space now
	cameraOrigirDir_l = camera_gDir.normalized()
	active_bmesh.verts.ensure_lookup_table()
	active_bmesh.edges.ensure_lookup_table()
	active_bmesh.faces.ensure_lookup_table()
	active_bmesh.verts.index_update()
	active_bmesh.edges.index_update()
	active_bmesh.faces.index_update()
	#dumpBMesh(None,active_bmesh,"EDGEOBJ")

	vert_cnt = len(active_bmesh.verts)
	if vert_cnt > kWPLEdgeMaxVerts2check:
		print("- Too many verts, break object first. Verts count="+str(vert_cnt))
		return None

	edgeVerts = []
	verts2CamDst = {}
	verts2CamDot = {}
	verts2CamDir = {}
	vertsEdgeType = {}
	vertsEdgeOpenDir = {}
	curves_all = []
	zUp = Vector((0,0,1))
	if (cameraOrigirDir_l-zUp).length < 0.01:
		zUp = Vector((1,0,0))
	perp1 = cameraOrigirDir_l.cross(zUp)
	perp2 = cameraOrigirDir_l.cross(perp1)
	bmesh_bvh0 = BVHTree.FromBMesh(active_bmesh, epsilon=0.0) #0.0!!!

	# creating BVHTrees
	shiftBVH = []
	shiftDirs = [(0,0,0),perp1*vertRaycShift,perp2*vertRaycShift,-1*perp1*vertRaycShift,-1*perp2*vertRaycShift]
	shiftDirs.extend([(perp1+perp2)*vertRaycShift,(perp1-perp2)*vertRaycShift,(-1*perp1+perp2)*vertRaycShift,(-1*perp1-perp2)*vertRaycShift])
	for sdir in shiftDirs:
		shiftBVH.append((bmesh_bvh0, Vector(sdir)))

	# getting raw contour verts
	print("- Gathering verts, initial count="+str(vert_cnt))
	millisA1 = int(round(time.time() * 1000))
	allowedNearFaceIdxMap = {}
	allowedNearVertMap = {}
	allowedNearVertAvglenMap = {}
	def edgeViewIniMeasure(v):
		return -1*v.co[2]
	def getVertLinkedVerts(v):
		linkverts = []
		for vf in v.link_faces:
			for sv in vf.verts:
				if sv != v and (sv not in linkverts):
					linkverts.append(sv)
		return linkverts
	def getVertNearedVert(v, nearLoops):
		if nearLoops in allowedNearVertMap:
			anvm = allowedNearVertMap[nearLoops]
		else:
			anvm = {}
			allowedNearVertMap[nearLoops] = anvm
		if v in anvm:
			return anvm[v]
		allowedNearVerts = set()
		getBMeshVertLoops_v01(v, allowedNearVerts, nearLoops)
		anvm[v] = allowedNearVerts
		return allowedNearVerts
	def getVertNearedFaceIdx(v, nearLoops):
		if nearLoops in allowedNearFaceIdxMap:
			anfim = allowedNearFaceIdxMap[nearLoops]
		else:
			anfim = {}
			allowedNearFaceIdxMap[nearLoops] = anfim
		if v in anfim:
			return anfim[v]
		allowedNearFaceIdx = set()
		allowedNearVerts = getVertNearedVert(v, nearLoops)
		for ld_v in allowedNearVerts:
			for ld_f in ld_v.link_faces:
				allowedNearFaceIdx.add(ld_f.index)
		anfim[v] = allowedNearFaceIdx
		return allowedNearFaceIdx
	def getVertNearedVertAvgLen(v, nearLoops):
		if nearLoops in allowedNearVertAvglenMap:
			anvm = allowedNearVertAvglenMap[nearLoops]
		else:
			anvm = {}
			allowedNearVertAvglenMap[nearLoops] = anvm
		if v in anvm:
			return anvm[v]
		allowedNearVerts = getVertNearedVert(v,nearLoops)
		sumlen = 0.0
		cntlen = 0.0
		for vv in allowedNearVerts:
			if vv.index == v.index:
				continue
			sumlen = sumlen+(vv.co-v.co).length
			cntlen = cntlen+1.0
		avglen = sumlen/cntlen
		anvm[v] = avglen
		return avglen
	def getCamRayOpts(v):
		if camera_gOrtho:
			bmesh_orig = v.co + cameraOrigirDir_l*kWPLEdgeOrthOffset
			bmesh_dir = -1*cameraOrigirDir_l
		else:
			bmesh_orig = camera_lCo
			bmesh_dir = (v.co - camera_lCo).normalized()
		return(bmesh_orig,bmesh_dir)
	dots_seams = {}
	dots_bnds = {}
	allVertsCnd = []
	allVertsIsSeam = {}
	walkedVerts = set()
	hideIgnoredVerts = 0
	#deczIgnoredVerts = 0
	for v in active_bmesh.verts:
		if v.hide:
			hideIgnoredVerts = hideIgnoredVerts+1
			walkedVerts.add(v)
			continue
		allVertsIsSeam[v] = 0
		if vertBounds2Edge and v.is_boundary:
			allVertsIsSeam[v] = 2
			dots_bnds[v.index] = {"co_g": copy.copy(v.co)}
		for ve in v.link_edges:
			if ve.seam:
				#allVertsIsSeam[v] = 1
				dots_seams[v.index] = {"co_g": copy.copy(v.co)}
				break
		if camera_gOrtho:
			direction = cameraOrigirDir_l
			v_cam_proj = v.co-(direction.dot(v.co-camera_lCo)*direction)
			verts2CamDst[v] = (v_cam_proj-v.co).length
		else:
			direction = (camera_lCo-v.co).normalized()
			verts2CamDst[v] = (camera_lCo-v.co).length
		v2cd = direction.dot(v.normal)
		verts2CamDot[v] = v2cd
		verts2CamDir[v] = direction
		if allVertsIsSeam[v] == 0 and v2cd < optmMaxInNoDot:
			walkedVerts.add(v)
			continue
		v_closest = v
		if (v_closest is not None) and (v_closest not in allVertsCnd):
			allVertsCnd.append(v_closest)

	edge_col = {}
	colVC = active_bmesh.loops.layers.color.get(kWPLEdgeColVC)
	if colVC is not None:
		for face in active_bmesh.faces:
			for vert, loop in zip(face.verts, face.loops):
				if vert not in allVertsCnd:
					continue
				fcl = Vector((loop[colVC][0],loop[colVC][1],loop[colVC][2],loop[colVC][3]))
				if vert.index not in edge_col:
					edge_col[vert.index] = fcl
				elif fcl.length < edge_col[vert.index].length:
					edge_col[vert.index] = fcl
	if len(active_obj.data.vertices) == len(active_bmesh.verts):
		hidegeomIdx = get_vertwg_by_name(active_obj, kWPLHideMaskVGroup)
		for vIdx in hidegeomIdx:
			vWei = hidegeomIdx[vIdx]
			if vWei > 0.98:
				v = active_bmesh.verts[vIdx]
				hideIgnoredVerts = hideIgnoredVerts+1
				walkedVerts.add(v)
	else:
		print("- hidegeom check skipped: bmesh verts count differ")
	# edge_skip = {}
	# skipVC = active_bmesh.loops.layers.color.get(kWPLEdgeSkipVC)
	# if skipVC is not None:
	# 	for face in active_bmesh.faces:
	# 		for vert, loop in zip(face.verts, face.loops):
	# 			if vert not in allVertsCnd:
	# 				continue
	# 			fcl = Vector((loop[skipVC][0],loop[skipVC][1],loop[skipVC][2],loop[skipVC][3]))
	# 			if vert.index not in edge_skip:
	# 				edge_skip[vert.index] = fcl
	# 			elif fcl.length < edge_skip[vert.index].length:
	# 				edge_skip[vert.index] = fcl

	# removing definitely inner verts
	if True:
		bmesh_bvh = shiftBVH[0][0]
		allVertsCnd2 = []
		for v in allVertsCnd:
			# and blocking edge_skip > 0 (not only edge-verts!)
			# if v.index in edge_skip and (max(max(edge_skip[v.index][0],edge_skip[v.index][1]),edge_skip[v.index][2])) > 0.51:
			# 	deczIgnoredVerts = deczIgnoredVerts+1
			# 	walkedVerts.add(v) #not only edge-verts!
			# 	continue
			isAnyHitGotNearFace = False
			bmesh_cro = getCamRayOpts(v)
			bmesh_orig = bmesh_cro[0]
			bmesh_dir = bmesh_cro[1]
			for i in range(1,len(shiftBVH)):
				bmesh_bvh = shiftBVH[i][0]
				bmesh_sht = shiftBVH[i][1]
				hit, normal, findex, distance = bmesh_bvh.ray_cast(bmesh_orig+bmesh_sht, bmesh_dir)
				#if v.select:
				#	print("debug:",v,hit, normal, findex, distance)
				if hit is not None:
					allowedNearFaceIdx = getVertNearedFaceIdx(v, vertTstLdiff)
					if len(allowedNearFaceIdx)>0 and (findex in allowedNearFaceIdx):
						isAnyHitGotNearFace = True
						break
			if isAnyHitGotNearFace:
				allVertsCnd2.append(v)
		allVertsCnd = allVertsCnd2
		allVertsCnd = sorted(allVertsCnd,key=lambda v:verts2CamDst[v], reverse=False)
	if hideIgnoredVerts>0:
		print("- Ignored verts: Hide count="+str(hideIgnoredVerts))
	# if deczIgnoredVerts>0:
	# 	print("- Ignored verts: Antiintersect count="+str(deczIgnoredVerts))
	_testForAllDots = 0 #1
	if _testForAllDots != 0:
		for i,v in enumerate(allVertsCnd):
			#curves_all.append([v,allVertsCnd[(i+1)%len(allVertsCnd)],allVertsCnd[(i+2)%len(allVertsCnd)]])
			curves_all.append([v,v.co+v.normal*0.01])
		print("- Test all-dots curves:", len(allVertsCnd))
		return {"curves":curves_all, "debug": 1}

	print("- Detecting edge verts, filtered count="+str(len(allVertsCnd)))
	maxRootFirst = -1
	nonEdgeVerts = []
	for av in allVertsCnd:
		if maxRootFirst == 0:
			print("--- stopping, rootfirsts limit")
			break
		#print("-- Starting rootfirst",abs(maxRootFirst))
		maxRootFirst = maxRootFirst-1
		if av in walkedVerts:
			continue
		# first point
		walklist = [av]
		while (len(walklist)>0):
			v = walklist.pop(0)
			walkedVerts.add(v)
			if v not in verts2CamDst:
				print("- WARNING: vert not in verts2CamDst",v)
				continue
			distance0 = verts2CamDst[v]
			isAnyEdge = 0
			isEdge = False
			if isEdge == False:
				if allVertsIsSeam[v] > 0:
					isEdge = True
					isAnyEdge = isAnyEdge+1
					vertsEdgeType[v] = 1.1
					if allVertsIsSeam[v] == 2:
						vertsEdgeType[v] = 4.1
					vertsEdgeOpenDir[v] = v.normal
			if isEdge == False:
				bmesh_cro = getCamRayOpts(v)
				bmesh_orig = bmesh_cro[0]
				bmesh_dir = bmesh_cro[1]
				for i in range(1,len(shiftBVH)):
					isEdge = False
					if isEdge == False:
						bmesh_bvh = shiftBVH[i][0]
						bmesh_sht = shiftBVH[i][1]
						hit, normal, findex, distance = bmesh_bvh.ray_cast(bmesh_orig+bmesh_sht, bmesh_dir)
						if hit is None:
							#if v.select:
							#	print("debug: No hit ",v)
							isEdge = True
							vertsEdgeType[v] = 2.2 #4.2 separate type not ok...
						elif distance>distance0:
							#if v.select:
							#	print("debug:",v, hit, normal, findex, distance>distance0, (hit - v.co).length, vertMaxZdiff)
							if isEdge == False:
								#print("Testing diff",hit, v.co, vertMaxZdiff, (hit - v.co).length)
								if (hit - v.co).length >= vertMaxZdiff:
								#if abs(distance-distance0) >= vertMaxZdiff:
									isEdge = True
									vertsEdgeType[v] = 2.1
							if isEdge == False and vertSepmesh2Edge == True:
								allowedNearFaceIdx = getVertNearedFaceIdx(v, vertMaxLdiff)
								if len(allowedNearFaceIdx)>0 and (findex not in allowedNearFaceIdx):
									isEdge = True
									vertsEdgeType[v] = 3.1
					if isEdge == True:
						isAnyEdge = isAnyEdge+1
						if bmesh_sht is not None:
							if v not in vertsEdgeOpenDir:
								vertsEdgeOpenDir[v] = Vector((0,0,0))
							vertsEdgeOpenDir[v] = vertsEdgeOpenDir[v] + bmesh_sht.normalized()
			if isAnyEdge > 0:
				if (v not in edgeVerts):
					edgeVerts.append(v)
					# blocking all verts on sight
					cro = getCamRayOpts(v)
					cro_dir = cro[1]
					vnv = getVertNearedVert(v, vertMaxLdiff)
					for sv in vnv:
						svv = (sv.co - v.co).normalized()
						if abs(svv.dot(cro_dir)) > optmEdgeTunnlDot:
							walkedVerts.add(sv)
			if isAnyEdge == 0:
				nonEdgeVerts.append(v)
				linkv = getVertLinkedVerts(v)
				for sv in linkv:
					if (sv not in walklist) and (sv not in walkedVerts):
						walklist.append(sv)
	edgeVerts = sorted(edgeVerts,key=lambda v:edgeViewIniMeasure(v), reverse=False)
	millisA2 = int(round(time.time() * 1000))
	print("-- Edge verts="+str(len(edgeVerts))+"; ms="+str(millisA2-millisA1))
	if len(dots_seams) == 0:
		dots_seams = dots_bnds
	dots_edges = {}
	for v_g in edgeVerts:
		if v_g.index in dots_seams:
			continue
		dots_edges[v_g.index] = {"co_g": copy.copy(v_g.co)} #, "normal_g": copy.copy(v_g.normal).normalized()
	_testForEdgeDots = 0 #-1
	if _testForEdgeDots != 0:
		for i,v in enumerate(edgeVerts):
			if _testForEdgeDots < 0 or (v in vertsEdgeType and vertsEdgeType[v] == _testForEdgeDots):
				#curves_all.append([v,edgeVerts[(i+1)%len(edgeVerts)],edgeVerts[(i+2)%len(edgeVerts)]])
				curves_all.append([v,v.co+v.normal*0.01])
		print("- Test edge-dots curves:", len(curves_all),"; dots type:",_testForEdgeDots)
		return {"curves":curves_all, "debug": 1}
	_testForNonEdgeDots = 0 #1
	if _testForNonEdgeDots != 0:
		for i,v in enumerate(nonEdgeVerts):
			curves_all.append([v,v.co+v.normal*0.01])
		print("- Test non-edge-dots curves:", len(curves_all))
		return {"curves":curves_all, "debug": 1}

	# building curves
	print("- Building curves...")
	millisC1 = int(round(time.time() * 1000))
	walkedCurvs = set()
	while True:
		v_curve = []
		vertsPossibBlocked = set()
		isVadded = False
		#isLastTrackedTo = None
		initial_v = None
		initial_v_min_possibl = 0
		for vi in edgeVerts:
			if vi in walkedCurvs:
				continue
			possibl_vn = 0
			vnv = getVertNearedVert(vi, vertMaxLdiff)
			for vn in vnv:
				if vn in walkedCurvs or vn.index == vi.index:
					continue
				possibl_vn = possibl_vn+1
			if initial_v is None:
				initial_v = vi
				initial_v_min_possibl = possibl_vn
			if initial_v_min_possibl < possibl_vn:
				initial_v = vi
				initial_v_min_possibl = possibl_vn
			if initial_v_min_possibl == 1:
				break
		if initial_v is not None:
			isVadded = True
			v_curve.append(initial_v)
			walkedCurvs.add(initial_v)
		while isVadded == True:
			isVadded = False
			curve_first = v_curve[0]
			curve_last = v_curve[-1]
			#curve_last_2d = project_3d_point(camera_obj,curve_last.co)
			#curve_last_flow2d = None
			#if len(v_curve) > 1:
			#	curve_last2 = v_curve[-2]
			#	curve_last2_2d = project_3d_point(camera_obj,curve_last2.co)
			#	curve_last_flow2d = (curve_last_2d - curve_last2_2d).normalized()
			curve_last_prob = []
			nearVerts = getVertNearedVert(curve_last, vertTstLdiff)
			for v in nearVerts:
				if v not in edgeVerts:
					continue
				if v in walkedCurvs or v.index == curve_last.index:
					continue
				if (v in vertsEdgeType) and (curve_last in vertsEdgeType) and int(vertsEdgeType[v]) != int(vertsEdgeType[curve_last]):
					continue
				if (v.index in edge_col) and (curve_last.index in edge_col) and (edge_col[v.index]-edge_col[curve_last.index]).length > 0.01:
					continue
				if optmNormSmtDot > -1.0:
					if curve_last is not None:
						dotFac = v.normal.dot(curve_last.normal)
						if dotFac < optmNormSmtDot:
							continue
				curvOpenedgFac = 10
				if optmNormOpdDot > -1.0:
					if (v in vertsEdgeOpenDir) and (curve_last in vertsEdgeOpenDir):
						v_oe = vertsEdgeOpenDir[v].normalized()
						cl_oe = vertsEdgeOpenDir[curve_last].normalized()
						dotFac = v_oe.dot(cl_oe)
						curvOpenedgFac = dotFac
						if dotFac < optmNormOpdDot:
							continue
				#if optmCurveFlowDot > -1.0:
				#	if curve_last_flow2d is not None:
				#		curve_test_flow2d = (project_3d_point(camera_obj,v.co)-curve_last_2d).normalized()
				#		dotFac = curve_test_flow2d.dot(curve_last_flow2d)
				#		if dotFac < optmCurveFlowDot:
				#			continue
				v_last_dir = (v.co-curve_last.co).normalized()
				curveLinearity = -1
				curveLinearityOk = True
				for i in range(1,len(v_curve)):
					curv_preb_dir = (v_curve[i].co-v_curve[i-1].co).normalized()
					dotFac = curv_preb_dir.dot(v_last_dir)
					curveLinearity = max(dotFac,curveLinearity)
					if optmCurveFlowDot > -1.0 and dotFac<optmCurveFlowDot:
						curveLinearityOk = False
						break
				if curveLinearityOk == False:
					continue
				vOptimFac = 0.0
				avgl = getVertNearedVertAvgLen(v, vertTstLdiff)
				if avgl == 0.0:
					continue
				vOptimFac = vOptimFac+(v.co-curve_last.co).length/avgl # normalized step len. less is better!
				vOptimFac = vOptimFac - curveLinearity # to avoid curve skew to beginning. better when all points stay on same line
				cam3dViewdotFac = abs(v_last_dir.dot(verts2CamDir[v]))
				vOptimFac = vOptimFac+max(1.0-curvOpenedgFac,cam3dViewdotFac) # to avoid sharp endings, pointing to camera (on the same edge sides)
				curve_last_prob.append((v, vOptimFac)) #, (v.co-curve_last.co).length
			v2 = None
			if len(curve_last_prob) > 0:
				curve_last_prob = sorted(curve_last_prob, key=lambda v:v[1], reverse = False)
				v2 = curve_last_prob[0][0] # smallest v[1] value
				isVadded = True
				v_curve.append(v2)
				walkedCurvs.add(v2)
		curve_len = len(v_curve)
		if curve_len == 0:
			break
		curves_all.append(v_curve)
	millisC2 = int(round(time.time() * 1000))
	print("-- Curves created="+str(len(curves_all))+"; ms="+str(millisC2-millisC1))
	rejoined = 0
	if True:
		print("- Rejoinin curves... max:",vertRejoin)
		curveRejoinLenFac = 0
		millisC1 = int(round(time.time() * 1000))
		for i in range(vertRejoin):
			updatedCurves = 0
			j = 0
			for j, pc in enumerate(curves_all):
				if len(pc) <= curveRejoinLenFac:
					continue
				fwd_tries = []
				for k,pa in enumerate(curves_all):
					if len(pa) <= curveRejoinLenFac:
						continue
					if j == k:
						continue
					if pc[0] in getVertNearedVert(pa[0], vertRejLdiff):
						#dd2d = (project_3d_point(camera_obj,pa[0].co)-project_3d_point(camera_obj,pc[0].co)).length #(pa[0].co-pc[0].co).length
						dd2d = verts2CamDst[pa[0]]-verts2CamDst[pc[0]]
						fwd_tries.append((0, dd2d, pa, pc))
					if pc[0] in getVertNearedVert(pa[-1], vertRejLdiff):
						#dd2d = (project_3d_point(camera_obj,pa[-1].co)-project_3d_point(camera_obj,pc[0].co)).length #(pa[-1].co-pc[0].co).length
						dd2d = verts2CamDst[pa[-1]]-verts2CamDst[pc[0]]
						fwd_tries.append((1, dd2d, pa, pc))
					if pc[-1] in getVertNearedVert(pa[0], vertRejLdiff):
						#dd2d = (project_3d_point(camera_obj,pa[0].co)-project_3d_point(camera_obj,pc[-1].co)).length #(pa[0].co-pc[-1].co).length
						dd2d = verts2CamDst[pa[0]]-verts2CamDst[pc[-1]]
						fwd_tries.append((2, dd2d, pa, pc))
					if pc[-1] in getVertNearedVert(pa[-1], vertRejLdiff):
						#dd2d = (project_3d_point(camera_obj,pa[-1].co)-project_3d_point(camera_obj,pc[-1].co)).length #(pa[-1].co-pc[-1].co).length
						dd2d = verts2CamDst[pa[-1]]-verts2CamDst[pc[-1]]
						fwd_tries.append((3, dd2d, pa, pc))
				if len(fwd_tries)>0:
					fwd_tries = sorted(fwd_tries,key=lambda ft:ft[1], reverse=True)
					#print("fwd_tries",[f[1] for f in fwd_tries])
					pa = fwd_tries[0][2]
					pc = fwd_tries[0][3]
					if fwd_tries[0][0] == 0:
						for v in pc:
							pa.insert(0, v)
					if fwd_tries[0][0] == 1:
						pa.extend(pc)
					if fwd_tries[0][0] == 2:
						for v in reversed(pc):
							pa.insert(0, v)
					if fwd_tries[0][0] == 3:
						pa.extend(reversed(pc))
					curves_all[j] = []
					rejoined = rejoined+1
					updatedCurves = updatedCurves+1
			print("- iter:", j, "updated:",updatedCurves)
			if updatedCurves ==0:
				break
	millisC2 = int(round(time.time() * 1000))
	_testForEdgeStart = 0 #1
	if _testForEdgeStart != 0:
		curves_all_cc = copy.copy(curves_all)
		for i,curv in enumerate(curves_all_cc):
			v = curv[0]
			dopcurva = [v]
			for k in range(i):
				dopcurva.append(v.co+Vector((0.0,0.0,0.003))*(1.0+k))
			curves_all.append(dopcurva)
	# vert_curves
	print("-- Curves rejoined="+str(rejoined)+"; ms="+str(millisC2-millisC1))
	return {"curves":curves_all,"colors":edge_col, "dotsEdges": dots_edges, "dotsSeams": dots_seams}

######################### ######################### #########################
######################### ######################### #########################
# class wplbevel_build(bpy.types.Operator):
# 	bl_idname = "object.wplbevel_build"
# 	bl_label = "Bevel from edge"
# 	bl_options = {'REGISTER', 'UNDO'}
# 	@classmethod
# 	def poll( cls, context ):
# 		p = context.object and context.object and context.object.type == 'CURVE'
# 		return p

# 	def execute( self, context ):
# 		wplEdgeBuildProps = context.scene.wplEdgeBuildProps
# 		active_obj = context.scene.objects.active
# 		bevel_name = active_obj.name
# 		bevel_name = bevel_name.replace(wplEdgeBuildProps.opt_edgePostfix2,'')
# 		bevel_name = bevel_name+wplEdgeBuildProps.opt_bevlPostfix2

# 		obj_bevel_old = context.scene.objects.get(bevel_name)
# 		if obj_bevel_old is not None:
# 			bpy.data.objects.remove(obj_bevel_old, True)

# 		obj_bevel = active_obj.copy()
# 		bpy.context.scene.objects.link(obj_bevel)
# 		obj_bevel.data = obj_bevel.data.copy()
# 		obj_bevel.name = bevel_name
# 		obj_bevel.data.name = bevel_name+"_curve"
# 		makeObjectNoShadow(obj_bevel,True,False)
# 		#c_object.hide = True
# 		for polyline in obj_bevel.data.splines:
# 			for point in polyline.points:
# 				point.radius = point.radius*wplEdgeBuildProps.opt_bevlRadiusMul

# 		curveMat = None
# 		if len(wplEdgeBuildProps.opt_bevlMat)>0:
# 			curveMat = bpy.data.materials.get(wplEdgeBuildProps.opt_bevlMat)
# 			if curveMat is not None:
# 				if len(obj_bevel.data.materials) == 0:
# 					obj_bevel.data.materials.append(curveMat)
# 				else:
# 					obj_bevel.data.materials[0] = curveMat
# 		select_and_change_mode(obj_bevel,'OBJECT')
# 		return {'FINISHED'}

class wpledge_build(bpy.types.Operator):
	bl_idname = "object.wpledge_build"
	bl_label = "Generate edges"
	bl_options = {'REGISTER', 'UNDO'}
	# dot->cos(). cos(0) == 1!!!
	opt_detectsEps = bpy.props.FloatVectorProperty(
		name		= "Detection (z-diff, I.vN-skip, I.e-skip2)",
		size = 3,
		default	 = (0.001*100000, -0.5, 0.9)
	)
	opt_detectsBounds = bpy.props.BoolProperty(
		name		= "Bounds as edges",
		default	 = True,
	)
	opt_detectsSepMesh = bpy.props.BoolProperty(
		name		= "Break mesh apart",
		default	 = True,
	)
	opt_curveBuil2Eps = bpy.props.FloatVectorProperty(
		# 0: Minimal curve len, lower curves get radius penalty
		# 1: Normals dot max limit (to avoid cross-edge jumps)
		name		= "Optimizations (cvN.vN-skip, cNE.vNE-skip, cN.pN-skip)",
		size = 3,
		default	 = (0.1, 0.1, -0.3),
	)
	opt_widthProfile = bpy.props.FloatVectorProperty(
		name		= "Width profile (start, end, pow)",
		size = 3,
		default	 = kWPLDefaultEdgeProfile,
	)
	@classmethod
	def poll( cls, context ):
		return True

	def execute( self, context ):
		#if not bpy.context.space_data.region_3d.is_perspective:
		#	self.report({'ERROR'}, "Can`t work in ORTHO mode")
		#	return {'CANCELLED'}
		active_obj = context.scene.objects.active
		if active_obj is None:
			return {'CANCELLED'}
		if get_isLocalView():
			self.report({'ERROR'}, "Can`t work in Local view")
			return {'CANCELLED'}
		sel_all_ini = [active_obj.name] #[o.name for o in bpy.context.selected_objects]
		if len(sel_all_ini) == 0:
			self.report({'ERROR'}, "No objects selected")
			return {'CANCELLED'}
		print("- active object:",active_obj.name)
		wplEdgeBuildProps = context.scene.wplEdgeBuildProps
		if len(kWPLNoEdgeObjects)>0:
			skipNameParts = [x.strip().lower() for x in kWPLNoEdgeObjects.split(",")]
		else:
			skipNameParts = []
		sel_all = []
		for i, sel_obj_name in enumerate(sel_all_ini):
			for snp in skipNameParts:
				if sel_obj_name.lower().find(snp) >= 0:
					sel_obj_name = ""
					break
			sel_obj = context.scene.objects.get(sel_obj_name)
			if sel_obj is None or sel_obj.cycles_visibility.camera == False:
				continue
			if wplEdgeBuildProps.opt_edgePostfix2 in sel_obj.name:
				continue
			if abs(sel_obj.scale[0]-1.0)+abs(sel_obj.scale[1]-1.0)+abs(sel_obj.scale[2]-1.0) > 0.001:
				self.report({'ERROR'}, "Scale not applied: "+sel_obj_name)
				return {'CANCELLED'}
			sel_all.append(sel_obj_name)
		if len(sel_all) == 0:
			return {'FINISHED'}
		camObj = context.scene.objects.get(kWPLEdgesMainCam)
		if camObj is None:
			self.report({'ERROR'}, "Camera not found: "+kWPLEdgesMainCam)
			return {'CANCELLED'}
		camera_gCo = camObj.matrix_world.to_translation() #camObj.location
		camera_gOrtho = False
		if camObj.data.type == 'ORTHO':
			camera_gOrtho = True
		changed_edgemeshed = 0
		curveMat = None
		for mat in bpy.data.materials:
			if kWPLEdgeMatName in mat.name:
				curveMat = mat
				break
		for i, sel_obj_name in enumerate(sel_all):
			sel_obj = context.scene.objects.get(sel_obj_name)
			sel_obj_modstate = {}
			toggleModifs(sel_obj,['MASK'],False,sel_obj_modstate)
			toggleModifs(sel_obj,['ARRAY'],False,sel_obj_modstate) #kWPLShapeKeyAntiIntr __dblr
			toggleModifs(sel_obj,['SOLIDIFY'],False,sel_obj_modstate) #kWPLShapeKeyAntiIntr _sldf
			 # Enabling SUBSURF, equalizing ss levels. or we get bad stuff on render
			ssmds = toggleModifs(sel_obj,['SUBSURF'],True,None)
			for md in ssmds:
				md.render_levels = md.levels #wplEdgeBuildProps.opt_meshSource
			sel_mesh = None
			try:
				sel_mesh = sel_obj.to_mesh(context.scene, True, 'PREVIEW') #wplEdgeBuildProps.opt_meshSource
			except:
				pass
			if sel_mesh is None:
				continue
			print("Preparing object "+sel_obj_name+"...")
			# subdPreparation = wplEdgeBuildProps.opt_edgePrep2[0]
			edger_params = {}
			edger_params["camera_obj"] = camObj
			edger_params["vertRaycShift"] = kWPLRaycastEpsilonCCL #self.opt_detectsEps[0]/100000.0
			edger_params["vertMaxZdiff"] = self.opt_detectsEps[0]/100000.0
			edger_params["vertMaxLdiff"] = wplEdgeBuildProps.opt_edgePrep2[1]
			edger_params["vertRejoin"] = wplEdgeBuildProps.opt_edgePrep2[2]
			edger_params["vertBounds2Edge"] = False
			if self.opt_detectsBounds:
				edger_params["vertBounds2Edge"] = True
			edger_params["vertSepmesh2Edge"] = False
			if self.opt_detectsSepMesh:
				edger_params["vertSepmesh2Edge"] = True
			edger_params["optmMaxInNoDot"] = self.opt_detectsEps[1]
			edger_params["optmEdgeTunnlDot"] = self.opt_detectsEps[2]
			edger_params["optmNormSmtDot"] = self.opt_curveBuil2Eps[0]
			edger_params["optmNormOpdDot"] = self.opt_curveBuil2Eps[1]
			edger_params["optmCurveFlowDot"] = self.opt_curveBuil2Eps[2] # better to split curves on abrupt rotations
			opt_curvePostpEps = (4, 0, 0) #bpy.props.IntVectorProperty name = "Postprocessing (min-pts, post-subdiv, post-smooth)"
			postCurveSubdiv = opt_curvePostpEps[1]
			postCurveSmooth = opt_curvePostpEps[2]
			if sel_obj.type == 'CURVE':
				postCurveSmooth = 0
				postCurveSubdiv = 0
				edger_params["optmMaxInNoDot"] = -0.99
				edger_params["optmCurveFlowDot"] = 0.5
				edger_params["optmNormSmtDot"] = 0.3
				edger_params["optmNormOpdDot"] = 0.7
				edger_params["vertBounds2Edge"] = False
			# if subdPreparation < 0:
				# target_cellsize = 3.0
				# maxdim = max(max(sel_obj.dimensions[0],sel_obj.dimensions[1]),sel_obj.dimensions[2])
				# remesh_scale = maxdim/target_cellsize
				# opt_remeshLevel = abs(subdPreparation)
				# if opt_remeshLevel<10:
					# remesh_scale = remesh_scale*pow(2,10-opt_remeshLevel)
				# remesh_scale = min(remesh_scale,0.99)
				# if remesh_scale > 0.001:
					# print("- Remeshing, level: "+str(opt_remeshLevel)+"/"+str(remesh_scale))
					# selModifiers = sel_obj.modifiers
					# remesh_modifier = selModifiers.new('WPLTMPREMESH', 'REMESH')
					# remesh_modifier.mode = 'SMOOTH'
					# remesh_modifier.scale = remesh_scale
					# remesh_modifier.use_remove_disconnected = False
					# remesh_modifier.octree_depth = opt_remeshLevel
					# bpy.data.meshes.remove(sel_mesh)
					# sel_mesh = sel_obj.to_mesh(context.scene, True, wplEdgeBuildProps.opt_meshSource)
					# selModifiers.remove(remesh_modifier)
			sel_bmesh = bmesh.new()
			sel_bmesh.from_mesh(sel_mesh)
			bpy.data.meshes.remove(sel_mesh)
			# if subdPreparation>0:
				# bmesh.ops.subdivide_edges(sel_bmesh, edges=sel_bmesh.edges[:], cuts=subdPreparation, use_grid_fill=True, use_single_edge=True)
			toggleModifs(sel_obj,['MASK'],None,sel_obj_modstate)
			toggleModifs(sel_obj,['ARRAY'],None,sel_obj_modstate)
			toggleModifs(sel_obj,['SOLIDIFY'],None,sel_obj_modstate)
			if sel_bmesh is None:
				continue
			edgeRadFac = 1.0
			for name_pr in kWPLEdgeAutoScale:
				if name_pr in sel_obj_name:
					edgeRadFac = edgeRadFac*kWPLEdgeAutoScale[name_pr]
			print("- edge radius", edgeRadFac)
			print("- edger_params:", edger_params)
			edgeDB = getEdgeVertsForObject(context, sel_obj, sel_bmesh, edger_params)
			if edgeDB is None:
				print("- Curves generation skipped...")
				continue
			vert_curves = edgeDB["curves"]
			vertEdges_posnrm = edgeDB["dotsEdges"]
			vertSeams_posnrm = edgeDB["dotsSeams"]
			vert_cols = None
			if "colors" in edgeDB:
				vert_cols = edgeDB["colors"] #edge_col
			curves_skipped = 0
			curves_added = 0
			matrix_world_inv = sel_obj.matrix_world.inverted()
			edgeObjName = sel_obj_name + wplEdgeBuildProps.opt_edgePostfix2 + kWPLFrameBindPostfix + str(bpy.context.scene.frame_current)
			curveDataName = edgeObjName+'_curve'
			curveData = bpy.data.curves.new(curveDataName, type='CURVE')
			curveData.dimensions = '3D'
			curveData.fill_mode = 'FULL'
			curveData.bevel_depth = kWPLEdgeBevelSize
			curveData.bevel_resolution = 2
			curveData.use_fill_caps = True
			curveData.show_normal_face = False
			curveData.use_auto_texspace = True
			curveData.use_uv_as_generated = True
			curveData.splines.clear()
			for curve in vert_curves:
				if len(curve) < opt_curvePostpEps[0] and not ("debug" in edgeDB):
					if len(curve) > 0:
						curves_skipped = curves_skipped+1
					continue
				curves_added = curves_added+1
				polyline = curveData.splines.new('NURBS')
				curveLength = float(len(curve))
				curveDist = 0
				v_g_prev_co = None
				for i,v_g in enumerate(curve):
					if isinstance(v_g, bmesh.types.BMVert):
						v_g_co = v_g.co
					else:
						v_g_co = v_g
					if len(polyline.points) <= i:
						polyline.points.add(1)
					v_co_l = matrix_world_inv * v_g_co
					polyline.points[i].co = (v_co_l[0], v_co_l[1], v_co_l[2], 1)
					if v_g_prev_co is not None:
						curveDist = curveDist+(Vector(v_g_co)-Vector(v_g_prev_co)).length
					v_g_prev_co = v_g_co
				baseRadius = 1.0
				# initializing scale
				for i,v_g in enumerate(curve):
					polyline.points[i].radius = baseRadius*edgeRadFac
				# detecting maximum per curve
				rbaseRadiusMax = 0
				for i,v_g in enumerate(curve):
					if polyline.points[i].radius > rbaseRadiusMax:
						rbaseRadiusMax = polyline.points[i].radius
				curve_rescaleRadius(polyline.points, self.opt_widthProfile, 0.5, rbaseRadiusMax)
				polyline.use_endpoint_u = True
				polyline.order_u = 2 # if>2 -> sharp-angles will require edge fixes
				polyline.resolution_u = 10
			if len(curveData.splines) == 0:
				continue
			edgeObj = context.scene.objects.get(edgeObjName)
			if edgeObj is not None:
				bpy.data.objects.remove(edgeObj, True)
			edgeObj = bpy.data.objects.new(edgeObjName, curveData)
			print("- curve mat:", curveMat)
			if curveMat is not None:
				edgeObj.data.materials.append(curveMat)
			context.scene.objects.link(edgeObj)
			edgeCol = wplEdgeBuildProps.opt_edgeColOvr
			edgeCol = Vector((edgeCol[0],edgeCol[1],edgeCol[2]))
			if vert_cols is not None and (edgeCol[0]+edgeCol[1]+edgeCol[2]<0.01):
				# autodetecting from object vert_cols #C8F5FF
				edgeCol = Vector((1,1,1))
				for vIdx in vert_cols:
					vc = vert_cols[vIdx]
					if vc.length > 0.01 and vc.length < edgeCol.length:
						edgeCol = vc
			if edgeCol[0]+edgeCol[1]+edgeCol[2] >= 0.01:
				edgeObj[kWPLEdgeColVC] = Vector((edgeCol[0],edgeCol[1],edgeCol[2],1))
			makeObjectNoShadow(edgeObj, False, False)
			edgeObj.parent = sel_obj.parent
			edgeObj.matrix_world = sel_obj.matrix_world
			attachEdgeToSourceObject(edgeObj, sel_obj, True, True, 0) # Subdiv can`t subdivide POINTS, only final mesh...
			#subdModf = edgeObj.modifiers.get('WPL_EdgeSubd')
			#if subdModf is not None:
			#	subdModf.show_viewport = False
			antiscale = 1.0/max(edgeObj.scale[0],edgeObj.scale[1],edgeObj.scale[2])
			curveData.bevel_depth = curveData.bevel_depth*antiscale
			if postCurveSmooth>0 or postCurveSubdiv>0:
				select_and_change_mode(edgeObj,'EDIT')
				bpy.ops.curve.select_all(action = 'SELECT')
				if postCurveSubdiv>0:
					for i in range(int(postCurveSubdiv)):
						bpy.ops.curve.subdivide()
				if postCurveSmooth>0:
					for i in range(int(postCurveSmooth)):
						bpy.ops.curve.smooth()
				select_and_change_mode(edgeObj,'OBJECT')
			sel_bmesh.free()
			changed_edgemeshed = changed_edgemeshed+1
			print("- Made "+str(curves_added)+" curves, skipped="+str(curves_skipped))
			print(str(changed_edgemeshed)+" of "+str(len(sel_all))+" done.\n")
			select_and_change_mode(edgeObj,'OBJECT')
		self.report({'INFO'}, "Updated "+str(changed_edgemeshed)+" edges of "+str(len(sel_all)))
		return {'FINISHED'}

########## ############ ########## ############ ########## ############
########## ############ ########## ############ ########## ############
class WPLEdgeBuildSettings(bpy.types.PropertyGroup):
	#opt_edgeMat = StringProperty(
	#	name="Edge material",
	#	default = ""
	#	)
	opt_edgePostfix2 = StringProperty(
		name		= "Edge curve postfix",
		default	 = kWPLEdgesObjPostfix,
	)
	opt_edgePrep2 = IntVectorProperty(
		name		= "???/Loops/Rejoin",
		size = 3,
		default	 = (0, 5, 500),
	)
	#opt_meshSource = EnumProperty(
	#	name="Source", default="PREVIEW",
	#	items=(("PREVIEW", "Preview", ""), ("RENDER", "Render", ""))
	#)
	opt_edgeColOvr = FloatVectorProperty(
		name="Edge base Color",
		subtype='COLOR_GAMMA',
		min=0.0, max=1.0,
		default = (0.0,0.0,0.0)
		)

	opt_bevlMat = StringProperty(
		name="Bevel material",
		default = ""
		)
	# opt_bevlPostfix2 = StringProperty(
	# 	name		= "Bevel curve postfix",
	# 	default	 = kWPLBevelObjPostfix,
	# )
	# opt_bevlRadiusMul = FloatProperty(
	# 	name		= "Radius factor",
	# 	min = 1.0, max = 100.0,
	# 	default	 = 3.0,
	# )

class WPLEdgeBuilder_Panel(bpy.types.Panel):
	bl_label = "Scene edger"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_category = 'WPL'

	def draw_header(self, context):
		layout = self.layout
		layout.label(text="")

	def draw(self, context):
		wplEdgeBuildProps = context.scene.wplEdgeBuildProps
		col = self.layout.column()

		box1 = col.box()
		box1.prop(wplEdgeBuildProps, "opt_edgePostfix2")
		#box1.prop(wplEdgeBuildProps, "opt_meshSource")
		box1.separator()
		r3 = box1.row()
		r3.prop(wplEdgeBuildProps, "opt_edgePrep2")
		box1.prop(wplEdgeBuildProps, "opt_edgeColOvr")
		#box1.prop_search(wplEdgeBuildProps, "opt_edgeMat", bpy.data, "materials")
		box1.separator()
		box1.operator("object.wpledge_build", text="Build edges for selection", icon="PARTICLE_POINT")

def register():
	bpy.utils.register_module(__name__)
	bpy.types.Scene.wplEdgeBuildProps = PointerProperty(type=WPLEdgeBuildSettings)

def unregister():
	bpy.utils.unregister_module(__name__)
	del bpy.types.Scene.wplEdgeBuildProps
	bpy.utils.unregister_class(WPLEdgeBuildSettings)

if __name__ == "__main__":
	register()
