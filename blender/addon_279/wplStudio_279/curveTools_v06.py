import math
import copy
import mathutils
import numpy as np

import bpy
from bpy.props import *
import bpy.types
import bmesh
from mathutils import Vector, Matrix
from bpy_extras import view3d_utils
from bpy_extras.object_utils import world_to_camera_view
from mathutils.bvhtree import BVHTree


bl_info = {
	"name": "Curve Tools",
	"author": "IPv6",
	"version": (1, 2, 18),
	"blender": (2, 7, 9),
	"location": "View3D > T-panel > WPL",
	"description" : "",
	"warning"	 : "",
	"wiki_url"	: "",
	"tracker_url" : "",
	"category"	: "WPL"
}

kWPLRaycastEpsilonCCL = 0.0001
kWPLCurvePostfix = "_curve"
kWPLCurveBvlPostfix = "_bvl"
kWPLCurveUVCurvlen = "Orco_curvlen"
kWPLCurveUVCurvrad = "Orco_curvrad"
kWPLMeshColVC = "DecorC"
#kWPLCurveHookPostfix = "_hook"
kWPLRaycastEpsilon = 0.0001
kWPLSystemEmpty = "zzz_Support"
kWPLEdgesMainCam = "zzz_MainCamera"

kWPLDefaultEdgeProfile = (0.01,0.01,1.0)

class WPL_G:
	store = {}

######################### ######################### #########################
######################### ######################### #########################
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

def get_selected_vertsIdx(active_mesh):
	bpy.ops.object.mode_set(mode='OBJECT')
	selectedVertsIdx = [e.index for e in active_mesh.vertices if e.select]
	return selectedVertsIdx
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
def gpencil_to_screenpos_v2(context, stroke_subdiv_limit, region, gpidx):
	def check_if_scene_gp_exists(context):
		sceneGP = bpy.context.scene.grease_pencil
		if(sceneGP is not None):
			if(len(sceneGP.layers)>0):
				if(len(sceneGP.layers[-1].active_frame.strokes) > 0):
					return True
		return False
	def check_if_object_gp_exists(context):
		if bpy.context.active_object is None:
			return False
		objectGP = bpy.context.active_object.grease_pencil
		if(objectGP is not None):
			if(len(objectGP.layers)>0):
					if(len(objectGP.layers[-1].active_frame.strokes) > 0):
						return True
		return False
	gp = 0
	sceneGP = bpy.context.scene.grease_pencil
	objectGP = bpy.context.active_object.grease_pencil
	gpLayer = None
	if(check_if_scene_gp_exists(context)):
		gpLayer = sceneGP.layers[-1]
		gp = gpLayer.active_frame
	elif(check_if_object_gp_exists(context)):
		gpLayer = objectGP.layers[-1]
		gp = gpLayer.active_frame
	if(gp == 0 or gpidx >= len(gp.strokes)):
		if gpidx <= 0:
			if "wplcurve_gpen2d" in WPL_G.store:
				return WPL_G.store["wplcurve_gpen2d"], WPL_G.store["wplcurve_gpen3d"], None
		return [],[],gpLayer
	else:
		points_3d = [point.co for point in gp.strokes[gpidx].points if (len(gp.strokes) > 0)]
	if stroke_subdiv_limit>0:# dividing strokes until no lines bigger that stroke_subdiv_limit
		points_3d_up = []
		p3d_prev = None
		for p3d in points_3d:
			if p3d_prev is not None:
				p2len = (Vector(p3d) - Vector(p3d_prev)).length
				if p2len > stroke_subdiv_limit:
					intrmd = p2len/stroke_subdiv_limit
					for i in range(0, intrmd):
						mid3d = Vector(p3d_prev).lerp(Vector(p3d),i/intrmd)
						points_3d_up.append(mid3d)
			points_3d_up.append(p3d)
			p3d_prev = p3d
		points_3d = points_3d_up
	points_3d_vecs = []
	points_2d_vecs = []
	for p3d in points_3d:
		if p3d is not None:
			loc = view_point3dToPoint2d(p3d, region)
			if loc is not None:
				points_2d_vecs.append(Vector(loc))
				points_3d_vecs.append(Vector(p3d))
	if gpidx <= 0:
		WPL_G.store["wplcurve_gpen2d"] = points_2d_vecs
		WPL_G.store["wplcurve_gpen3d"] = points_3d_vecs
	return points_2d_vecs,points_3d_vecs,gpLayer

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

def curve_delPointByIndex(curveSpline, ptIdx):
	bpy.ops.curve.select_all(action='DESELECT')
	if curveSpline is None or ptIdx < 0 or  ptIdx >= len(curveSpline.points):
		print("curve_delPointByIndex skipped", ptIdx, len(curveSpline.points))
		return
	print("curve_delPointByIndex", ptIdx, len(curveSpline.points))
	del_pt = curveSpline.points[ptIdx]
	del_pt.select = True
	bpy.ops.curve.delete(type='VERT')
	return

def curve_getSelectedPolys(curveData, andDesel, ignoreHids):
	selected_poly_all = []
	selected_poly_pnt = []
	selected_polys = []
	for polyline in curveData.splines:
		if polyline.type == 'NURBS' or polyline.type == 'POLY':
			points_sel = [point for point in polyline.points if point.select and (ignoreHids == False or point.hide == 0)]
			if len(points_sel)>0:
				points_all = [point for point in polyline.points if (ignoreHids == False or point.hide == 0)]
				selected_polys.append(polyline)
				selected_poly_all.append(points_all)
				selected_poly_pnt.append(points_sel)
				if andDesel:
					for point in points_sel:
						point.select = False
	return (selected_poly_all,selected_poly_pnt,selected_polys)

def curve_rescaleRadius(poly, radF3c, mid_fac, baseRadius):
	radiusAtStart = radF3c[0]
	radiusAtEnd = radF3c[1]
	radiusPow = radF3c[2]
	if radiusPow < 0.01:
		radiusPow = 1.0
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
			#curve_fac = float(i) / (curveLength-1)
			curve_fac = curveDist / curveDistTotal
			RadTotal = 1.0
			if curve_fac < mid_fac:
				curve_fac1 = (curve_fac/mid_fac)
				curve_fac1 = min(1.0, curve_fac1 * (2.0 - curve_fac1))
				curve_fac2 = pow(curve_fac1, radiusPow)
				RadTotal = radiusAtStart+(RadTotal-radiusAtStart)*curve_fac2
			else:
				curve_fac1 = 1.0-(curve_fac-mid_fac)/(1.0-mid_fac)
				curve_fac1 = min(1.0, curve_fac1 * (2.0 - curve_fac1))
				curve_fac2 = pow(curve_fac1, radiusPow)
				RadTotal = RadTotal+(radiusAtEnd-RadTotal)*(1.0-curve_fac2)
			RadTotal = max(0.00001,RadTotal)
			p.radius = RadTotal*baseRadius

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

#def areas_tuple():
#	res = {}
#	count = 0
#	for area in bpy.context.screen.areas:
#		res[area.type] = count
#		count += 1
#	return res

def materializeBevel(context, subcurveObj, hairCurve):
	scn = context.scene
	if scn.objects.get(subcurveObj.name) is None:
		scn.objects.link(subcurveObj)
		subcurveObj.use_fake_user = False
	empty = getSysEmpty(context,"")
	subcurveObj.parent = empty
	if hairCurve is not None and hairCurve.data.bevel_object == subcurveObj:
		subcurveObj.name = "sys_"+hairCurve.name+kWPLCurveBvlPostfix
		subcurveObj.data.name = "sys_"+hairCurve.name+kWPLCurveBvlPostfix
	makeObjectNoShadow(subcurveObj, True, True)

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

######################### ######################### #########################
######################### ######################### #########################

class wplcurve_2curves(bpy.types.Operator):
	bl_idname = "mesh.wplcurve_2curves"
	bl_label = "Edges to curves"
	bl_options = {'REGISTER', 'UNDO'}

	opt_curveType = EnumProperty(
		name="Curve Type", default="NURBS",
		items=(("NURBS", "Nurbs", ""), ("POLY", "Poly", ""))
	)
	opt_flowDir = FloatVectorProperty(
		name	 = "Preferred direction",
		size	 = 3,
		min=-1.0, max=1.0,
		default	 = (0.0,0.0,-1.0)
	)
	opt_initRadFrac = FloatProperty(
		name	 = "Initial radius (edgelen frac)",
		min=-100.0000, max=100.0,
		default	 = 0.5
	)
	opt_hideSourceObj = BoolProperty(
		name="Hide source from render",
		default=False
	)

	@classmethod
	def poll(self, context):
		p = context.object and context.object.data and (isinstance(context.scene.objects.active, bpy.types.Object) and isinstance(context.scene.objects.active.data, bpy.types.Mesh))
		return p

	def execute(self, context):
		active_obj = context.scene.objects.active
		if active_obj is None:
			self.report({'ERROR'}, "No object selected")
			return {'CANCELLED'}
		if abs(active_obj.scale[0]-1.0)+abs(active_obj.scale[1]-1.0)+abs(active_obj.scale[2]-1.0) > 0.001:
			self.report({'ERROR'}, "Scale not applied: "+active_obj.name)
			return {'CANCELLED'}
		active_mesh = active_obj.data
		select_and_change_mode(active_obj, 'EDIT')

		vertsIdx = get_selected_vertsIdx(active_mesh)
		edgesIdx = get_selected_edgesIdx(active_mesh)
		if len(edgesIdx)<1:
			self.report({'ERROR'}, "No selected edges found, select some edges first")
			return {'FINISHED'} # or all changes get lost!!!
		bpy.ops.object.mode_set( mode = 'EDIT' )
		#bpy.ops.mesh.select_mode(type="FACE")
		#bm = bmesh.from_edit_mesh( active_mesh )
		bm = bmesh.new()
		bm.from_object(active_obj, context.scene, deform=True, render=False, cage=True, face_normals=True)
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		(strands_points,strands_radius,strands_vidx) = getBmEdgesAsStrands_v04(bm, vertsIdx, edgesIdx, self.opt_flowDir, None)
		if strands_points is None:
			self.report({'ERROR'}, "No edges found")
			return {'FINISHED'} # or all changes get lost!!!
		curveData = bpy.data.curves.new(active_obj.name+kWPLCurvePostfix, type='CURVE')
		curveData.dimensions = '3D'
		curveData.twist_mode = 'MINIMUM' #'TANGENT'
		curveData.fill_mode = 'FULL'
		if self.opt_initRadFrac>0:
			curveData.bevel_depth = strands_radius[0]*self.opt_initRadFrac
		else:
			curveData.bevel_depth = abs(self.opt_initRadFrac)
		curveData.bevel_resolution = 2
		curveOB = bpy.data.objects.new(active_obj.name+kWPLCurvePostfix, curveData)
		curveOB.matrix_world = active_obj.matrix_world
		curveOB.parent = active_obj.parent
		bpy.context.scene.objects.link(curveOB)
		if len(curveOB.data.materials) == 0 and len(active_obj.data.materials)>0:
			curveOB.data.materials.append(active_obj.data.materials[0])
		activeName = active_obj.name
		curveName = curveOB.name

		#hookEmptyes = {}
		for i,strand_curve in enumerate(strands_points):
			polyline = curveData.splines.new(self.opt_curveType)
			polyline.points.add(len(strand_curve) - 1)
			for j, co in enumerate(strand_curve):
				polyline.points[j].co = (co[0], co[1], co[2], 1)
			if self.opt_curveType == 'NURBS':
				polyline.order_u = 3 # like bezier thing
				polyline.use_endpoint_u = True
		bpy.ops.object.mode_set( mode = 'OBJECT' )
		active_obj.select = False
		curveOB.select = True
		curveOB.data.show_normal_face = False
		if self.opt_hideSourceObj:
			makeObjectNoShadow(active_obj, True, True)
		# attaching to source
		attachEdgeToSourceObject(curveOB, active_obj, False, True, 0)
		select_and_change_mode(active_obj, 'OBJECT')
		return {'FINISHED'}

class wplcurve_taper_pts(bpy.types.Operator):
	bl_label = "Taper Curve"
	bl_idname = "curve.wplcurve_taper_pts"
	bl_description = "Taper Curve radius over length"
	bl_options = {"REGISTER", "UNDO"}
	opt_Radius = FloatProperty(
		name="Radius",
		default=0,
		min=0, max=100
	)
	opt_widthProfile = bpy.props.FloatVectorProperty(
		name = "Width profile (start, end, pow)",
		size = 3,
		default	 = kWPLDefaultEdgeProfile,
	)
	opt_RadiusMidpoint = FloatProperty(
		name="Midpoint",
		default=0.5,
		min=0, max=1
	)
	opt_onlySelection = BoolProperty(
		name="Only Selected",
		default=True
	)

	def invoke(self, context, event):
		if bpy.context.mode != 'OBJECT':
			self.opt_onlySelection = True
		elif bpy.context.mode == 'OBJECT':
			self.opt_onlySelection = False
		return self.execute(context)

	def execute(self, context):
		# mid_fac = self.opt_RadiusMidpoint
		# radiusAtStart = self.opt_RadiusAtStart
		# radiusAtEnd = self.opt_RadiusAtEnd
		# radiusPow = self.opt_RadiusFalloff
		selectedCurves = [obj for obj in context.selected_objects if obj.type == 'CURVE']
		for Curve in selectedCurves:
			curveData = Curve.data
			for polyline in curveData.splines:  # for strand point
				points = getPolylinePoint(polyline)
				if self.opt_onlySelection:
					points = getPolylineSelPoint(polyline)
				curveLength = float(len(points))
				Radius = self.opt_Radius
				if Radius<=0.0001:
					for point in points:
						Radius = max(Radius,point.radius)
				curve_rescaleRadius(points, self.opt_widthProfile, self.opt_RadiusMidpoint, Radius)
		return {"FINISHED"}

# class wplcurve_smooth_conv(bpy.types.Operator):
# 	bl_idname = "curve.wplcurve_smooth_conv"
# 	bl_label = "Flatten to convex"
# 	bl_options = {'REGISTER', 'UNDO'}

# 	opt_influence = bpy.props.FloatProperty(
# 		name		= "Influence",
# 		default	 = 1.0,
# 		min		 = 0,
# 		max		 = 10
# 	)
# 	opt_protectHead = BoolProperty(
# 		name="Protect Heads",
# 		default=True
# 	)
# 	opt_protectTails = BoolProperty(
# 		name="Protect Tails",
# 		default=False
# 	)
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

# 	def execute( self, context ):
# 		active_obj = context.scene.objects.active
# 		if active_obj is None or active_obj.type != 'CURVE':
# 			self.report({'INFO'}, 'Use operator on curve type object')
# 			return {"CANCELLED"}
# 		curveData = active_obj.data
# 		ptsForces = []
# 		ptsProtect = []
# 		for polyline in curveData.splines:  # for strand point
# 			points = getPolylinePoint(polyline)
# 			pointsAll = points
# 			if self.opt_onlySelection:
# 				points = getPolylineSelPoint(polyline)
# 			for p in points:
# 				if p.hide:
# 					continue
# 				ptsForces.append(p)
# 			if self.opt_protectHead:
# 				ptsProtect.append(pointsAll[0])
# 			if self.opt_protectTails:
# 				ptsProtect.append(pointsAll[-1])
# 		okCnt = 0
# 		bm2 = bmesh.new()
# 		hullv = []
# 		originalPos = {}
# 		for p in ptsForces:
# 			originalPos[p] = Vector((p.co[0],p.co[1],p.co[2]))
# 			bm2v = bm2.verts.new(originalPos[p])
# 			hullv.append(bm2v)
# 		if len(hullv)<3:
# 			self.report({'INFO'}, "No points found")
# 			return {'FINISHED'}
# 		bm2.verts.ensure_lookup_table()
# 		bm2.verts.index_update()
# 		bmesh.ops.convex_hull(bm2, input=hullv)
# 		bvh_hull = BVHTree.FromBMesh(bm2, epsilon = kWPLRaycastEpsilonCCL)
# 		for p in ptsForces:
# 			n_loc, n_normal, n_index, n_distance = bvh_hull.find_nearest(originalPos[p])
# 			if n_loc is None:
# 				continue
# 			n_loc = originalPos[p].lerp(n_loc, self.opt_influence)
# 			p.co = (n_loc[0],n_loc[1],n_loc[2],1)
# 			okCnt = okCnt+1
# 		self.report({'INFO'}, "Done, "+str(okCnt)+" points moved")
# 		return {'FINISHED'}

class wplcurve_straighten_pts(bpy.types.Operator):
	bl_label = "Straighten curve"
	bl_idname = "curve.wplcurve_straighten_pts"
	bl_options = {"REGISTER", "UNDO"}

	opt_influence = bpy.props.FloatProperty(
		name		= "Influence",
		default	 = 1.0,
		min		 = -1.0,
		max		 = 1.0
	)
	opt_steps = bpy.props.IntProperty(
		name		= "Steps",
		default	 = 3,
		min		 = 1,
		max		 = 100
	)
	opt_falloff = bpy.props.FloatProperty(
		name		= "Falloff",
		default	 = 1.5,
		min		 = 0.0,
		max		 = 3.0
	)

	opt_dir2head = bpy.props.BoolProperty(
		name		= "Direction: Head",
		default	 = True
	)
	opt_dir2tail = bpy.props.BoolProperty(
		name		= "Direction: Tail",
		default	 = True
	)

	def execute(self, context):
		active_obj = context.scene.objects.active
		if active_obj is None or active_obj.type != 'CURVE':
			self.report({'INFO'}, 'Use operator on curve type object')
			return {"CANCELLED"}
		curveData = active_obj.data
		okPts = 0
		for i, polyline in enumerate(curveData.splines):
			sel_points = getPolylineSelPoint(polyline)
			if len(sel_points) < 1:
				continue
			all_points = getPolylinePoint(polyline)
			pnt_root_map = {}
			sel_dirs = {}
			for j, curve_pt in enumerate(all_points):
				if curve_pt in sel_points:
					pt_co = Vector((curve_pt.co[0],curve_pt.co[1],curve_pt.co[2]))
					if curve_pt not in sel_dirs:
						sel_dirs[curve_pt] = []
					if j > 0:
						prev_p = all_points[j-1]
						prev_co = Vector((prev_p.co[0],prev_p.co[1],prev_p.co[2]))
						sel_dirs[curve_pt].append([(prev_co-pt_co).normalized(),-1])
					if j < len(all_points)-1:
						next_p = all_points[j+1]
						next_co = Vector((next_p.co[0],next_p.co[1],next_p.co[2]))
						sel_dirs[curve_pt].append([(next_co-pt_co).normalized(),1])
					if len(sel_dirs[curve_pt]) == 2:
						d1 = sel_dirs[curve_pt][0][0]
						d2 = sel_dirs[curve_pt][1][0]
						d_avg = ((d1+(-1.0*d2))*0.5).normalized()
						sel_dirs[curve_pt] = [[d_avg,-1],[-1*d_avg,1]]
					continue
				for k in range(j-self.opt_steps,j+self.opt_steps+1):
					if k==j or k<0 or k>=len(all_points):
						continue
					test_p = all_points[k]
					if test_p in sel_points:
						if curve_pt not in pnt_root_map:
							pnt_root_map[curve_pt] = []
						dst = 0.0
						for k2 in range(min(j,k),max(j,k)):
							p1_co = Vector((all_points[k2].co[0],all_points[k2].co[1],all_points[k2].co[2]))
							p2_co = Vector((all_points[k2+1].co[0],all_points[k2+1].co[1],all_points[k2+1].co[2]))
							dst = dst+(p2_co-p1_co).length
						weight = 1.0
						if self.opt_falloff > 0.0:
							weight = weight * pow(1.0-abs(float(k-j))/float(self.opt_steps+1.0),self.opt_falloff)
							#weight = pow(self.opt_falloff,abs(k-j))
						pnt_root_map[curve_pt].append([test_p, weight, j-k, dst])
			pt_new_co = {}
			for pt in pnt_root_map:
				if pt not in pt_new_co:
					pt_new_co[pt] = []
				pt_co = Vector((pt.co[0],pt.co[1],pt.co[2]))
				for pt_root_list in pnt_root_map[pt]:
					pt_root = pt_root_list[0]
					pt_root_co = Vector((pt_root.co[0],pt_root.co[1],pt_root.co[2]))
					pt2root_dir = (pt_co-pt_root_co).normalized()
					pt_root_wei = pt_root_list[1]
					pt_root_flow = pt_root_list[2]
					pt_root_dst = pt_root_list[3]
					pt_co_dst = pt_root_co + pt_root_dst*pt2root_dir
					if pt_root_flow < 0 and self.opt_dir2head == False:
						continue
					if pt_root_flow > 0 and self.opt_dir2tail == False:
						continue
					if pt_root in sel_dirs:
						pt_root_dirs = sel_dirs[pt_root]
						for rdir_list in pt_root_dirs:
							rdir = rdir_list[0]
							rdir_flow = rdir_list[1]
							#if pt2root_dir.dot(rdir)<0:
							#	continue
							if math.copysign(1,rdir_flow) == math.copysign(1,pt_root_flow):
								infl = (pt_root_wei*self.opt_influence)
								if infl<0:
									infl = -1.0*infl
									rdir = -1.0*rdir
								diff_quat = (infl*pt2root_dir.rotation_difference(rdir))
								diff_matRot = Matrix.Translation(pt_root_co) * diff_quat.to_matrix().to_4x4() * Matrix.Translation(-pt_root_co)
								#diff_co = diff_matRot*pt_co
								diff_co = diff_matRot*(pt_co.lerp(pt_co_dst,min(1,max(0,abs(infl)))))
								pt_new_co[pt].append(diff_co)
			for pt in pt_new_co:
				if pt.hide > 0:
					continue
				if len(pt_new_co[pt]) == 0:
					continue
				pt_co = Vector((pt.co[0],pt.co[1],pt.co[2]))
				new_co_sum = Vector((0,0,0))
				new_co_cnt = 0.0
				for new_co in pt_new_co[pt]:
					new_co_sum = new_co_sum+new_co
					new_co_cnt = new_co_cnt+1.0
				if new_co_cnt>0:
					new_co = new_co_sum/new_co_cnt
					#new_co = pt_co.lerp(new_co,self.opt_influence)
					pt.co = Vector((new_co[0],new_co[1],new_co[2],1))
					okPts = okPts+1
		self.report({'INFO'}, "Updated "+str(okPts)+" points")
		return {"FINISHED"}


class wplcurve_realigngp_pts(bpy.types.Operator):
	bl_idname = "curve.wplcurve_realigngp_pts"
	bl_label = "Align points to grease line"
	bl_options = {'REGISTER', 'UNDO'}

	opt_influence = bpy.props.FloatProperty(
		name		= "Influence",
		default	 = 1.0,
		min		 = -10.0,
		max		 = 10.0
	)

	opt_clearStrokes = bpy.props.BoolProperty(
		name="Clear Strokes",
		default=True
	)

	opt_invertDir = bpy.props.BoolProperty(
		name="Invert direction",
		default=False
	)

	@classmethod
	def poll( cls, context ):
		p = (isinstance(context.scene.objects.active, bpy.types.Object))
		return p

	def execute( self, context ):
		scene = context.scene
		region = view_getActiveRegion()
		eo_dir2cam = (region.view_rotation * Vector((0.0, 0.0, 1.0)))
		okPts = 0
		active_obj = context.scene.objects.active
		if active_obj is None or active_obj.type != 'CURVE':
			self.report({'INFO'}, 'Use operator on curve type object')
			return {"FINISHED"}
		
		usedGpLayers = []
		usedGps = 0
		curveData = active_obj.data
		for i, polyline in enumerate(curveData.splines):
			points = getPolylineSelPoint(polyline)
			if len(points) < 3:
				continue
			stroke2dPoints, stroke3dPoints_g, gpLayer = gpencil_to_screenpos_v2(context, 0, region, usedGps)
			if len(stroke2dPoints) == 0:
				break
			usedGps = usedGps+1
			if gpLayer is not None and gpLayer not in usedGpLayers:
				usedGpLayers.append(gpLayer)
			t_yp_px = []
			t_yp_py = []
			t_yp_pz = []
			len_trg = 0
			t_xp = []
			gp_p_last = None
			for gp_p in stroke3dPoints_g:
				t_yp_px.append(gp_p[0])
				t_yp_py.append(gp_p[1])
				t_yp_pz.append(gp_p[2])
				if gp_p_last is not None:
					len_trg = len_trg+(gp_p_last-gp_p).length
				t_xp.append(len_trg)
				gp_p_last = gp_p
			if len_trg>0.00001:
				for j, curve_pt in enumerate(points):
					okPts = okPts+1
					t_pos = float(j)/float(len(points)-1)
					if self.opt_invertDir:
						t_pos = 1.0 - t_pos
					new_co_g = Vector((np.interp(t_pos*len_trg, t_xp, t_yp_px),np.interp(t_pos*len_trg, t_xp, t_yp_py),np.interp(t_pos*len_trg, t_xp, t_yp_pz)))
					new_co_l = active_obj.matrix_world.inverted() * new_co_g
					curve_pt.co = curve_pt.co.lerp(Vector((new_co_l[0], new_co_l[1], new_co_l[2], 1)), self.opt_influence)

		if self.opt_clearStrokes and len(usedGpLayers)>0:
			for gpLayer in usedGpLayers:
				gpLayer.active_frame.clear()
		self.report({'INFO'}, "Updated "+str(okPts)+" points")
		return {"FINISHED"}

# class wplcurve_smooth_area(bpy.types.Operator):
# 	bl_label = "Area smoothing"
# 	bl_idname = "curve.wplcurve_smooth_area"
# 	bl_options = {"REGISTER", "UNDO"}
# 	opt_maxDistn = FloatVectorProperty(
# 		name="Distance, Lerp",
# 		size = 2,
# 		default=(0.05, 0.1)
# 	)
# 	opt_stabFac = IntProperty(
# 		name="Stability",
# 		default=1,
# 		min=0, max=100
# 	)
# 	opt_protectHead = BoolProperty(
# 		name="Protect Heads",
# 		default=True
# 	)
# 	opt_protectTails = BoolProperty(
# 		name="Protect Tails",
# 		default=False
# 	)
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
# 		selectedCurves = [obj for obj in context.selected_objects if obj.type == 'CURVE']
# 		ptsForces = {}
# 		ptsProtect = []
# 		ptsInit = {}
# 		for Curve in selectedCurves:
# 			curveData = Curve.data
# 			for polyline in curveData.splines:  # for strand point
# 				points = getPolylinePoint(polyline)
# 				pointsAll = points
# 				pointsSel = getPolylineSelPoint(polyline)
# 				for p in pointsAll:
# 					if p.hide:
# 						continue
# 					if self.opt_onlySelection and p not in pointsSel:
# 						ptsProtect.append(p)
# 					ptsForces[p] = []
# 					ptsInit[p] = Vector((p.co[0],p.co[1],p.co[2]))
# 				if self.opt_protectHead:
# 					ptsProtect.append(pointsAll[0])
# 				if self.opt_protectTails:
# 					ptsProtect.append(pointsAll[-1])
# 		for p1 in ptsForces:
# 			v1Co = Vector((p1.co[0],p1.co[1],p1.co[2]))
# 			for p2 in ptsForces:
# 				if p2 == p1:
# 					if self.opt_stabFac > 0:
# 						v2Co = Vector((p2.co[0],p2.co[1],p2.co[2]))
# 						for i in range(self.opt_stabFac):
# 							ptsForces[p1].append(v2Co)
# 					continue
# 				v2Co = Vector((p2.co[0],p2.co[1],p2.co[2]))
# 				distV = v1Co-v2Co
# 				if distV.length > self.opt_maxDistn[0]:
# 					continue
# 				ptsForces[p1].append(v2Co)
# 		okPts = 0
# 		for p1 in ptsForces:
# 			if p1 in ptsProtect:
# 				continue
# 			if len(ptsForces[p1])<1:
# 				continue
# 			p1f_sum = Vector((0,0,0))
# 			for f in ptsForces[p1]:
# 				p1f_sum = p1f_sum+f
# 			p1f_cur = ptsInit[p1]
# 			p1f_avg = p1f_sum/len(ptsForces[p1])
# 			print("p1f_avg",p1f_avg,len(ptsForces[p1]))
# 			p1f_cur = p1f_cur.lerp(p1f_avg,self.opt_maxDistn[1])
# 			p1.co = (p1f_cur[0],p1f_cur[1],p1f_cur[2],1)
# 			okPts = okPts+1
# 		self.report({'INFO'}, "Updated "+str(okPts)+" points")
# 		return {"FINISHED"}

# class wplcurve_symmetrize_pts(bpy.types.Operator):
# 	bl_label = "Make curve symmetrical"
# 	bl_idname = "curve.wplcurve_symmetrize_pts"
# 	bl_options = {"REGISTER", "UNDO"}

# 	opt_switchDir = BoolProperty(
# 		name="Invert direction",
# 		default=False
# 	)
# 	opt_xMirror = BoolProperty(
# 		name="X-Mirror",
# 		default=True
# 	)

# 	@staticmethod
# 	def execute(self, context):
# 		active_obj = context.scene.objects.active
# 		if active_obj is None or active_obj.type != 'CURVE':
# 			self.report({'INFO'}, 'Use operator on curve type object')
# 			return {"CANCELLED"}
# 		select_and_change_mode(active_obj, 'EDIT')
# 		curveData = active_obj.data
# 		for i, polyline in enumerate(curveData.splines):
# 			points = getPolylinePoint(polyline)
# 			selpoints = getPolylineSelPoint(polyline)
# 			if len(selpoints) < 1:
# 				continue
# 			mapping = []
# 			center = None #Vector((0,0,0))
# 			if len(points)%2 == 0:
# 				center_idx = int(len(points)*0.5)
# 				center = (points[center_idx-1].co+(points[center_idx].co))*0.5
# 				for i in range(center_idx):
# 					mapping.append((center_idx-i-1, center_idx+i))
# 			else:
# 				center_idx = int(len(points)*0.5)
# 				center = points[center_idx].co
# 				for i in range(center_idx):
# 					mapping.append((center_idx-(i+1), center_idx+(i+1)))
# 			p1_prv_co = center
# 			p2_prv_co = center
# 			for map_list in mapping:
# 				p1 = points[map_list[0]]
# 				p2 = points[map_list[1]]
# 				if self.opt_switchDir:
# 					p1 = points[map_list[1]]
# 					p2 = points[map_list[0]]
# 				p2.radius = p1.radius
# 				p2.tilt = p1.tilt
# 				if self.opt_xMirror:
# 					edge = p1.co-p1_prv_co
# 					edge = Vector((edge[0]*-1.0,edge[1],edge[2]))
# 					p2.co = Vector((p2_prv_co[0]+edge[0],p2_prv_co[1]+edge[1],p2_prv_co[2]+edge[2],1))
# 				p1_prv_co = p1.co
# 				p2_prv_co = p2.co
# 		return {"FINISHED"}

class wplcurve_smooth_pts(bpy.types.Operator):
	bl_label = "Smooth positions"
	bl_idname = "curve.wplcurve_smooth_pts"
	bl_options = {"REGISTER", "UNDO"}

	opt_iters = IntProperty(
		name="Iterations", default=10, min=1, max=1000
	)

	@staticmethod
	def execute(self, context):
		active_obj = context.scene.objects.active
		if active_obj is None or active_obj.type != 'CURVE':
			self.report({'INFO'}, 'Use operator on curve type object')
			return {"CANCELLED"}
		select_and_change_mode(active_obj, 'EDIT')
		for i in range(self.opt_iters):
			bpy.ops.curve.smooth()
		return {"FINISHED"}

class wplcurve_evenly_pts(bpy.types.Operator):
	bl_label = "Distribute points"
	bl_idname = "curve.wplcurve_evenly_pts"
	bl_options = {"REGISTER", "UNDO"}

	opt_onlySelection = BoolProperty(
		name="Only Selected",
		default=True
	)

	@staticmethod
	def invoke(self, context, event):
		if bpy.context.mode != 'OBJECT':
			self.opt_onlySelection = True
		elif bpy.context.mode == 'OBJECT':
			self.opt_onlySelection = False
		return self.execute(context)

	def execute(self, context):
		active_obj = context.scene.objects.active
		if active_obj is None or active_obj.type != 'CURVE':
			self.report({'INFO'}, 'Use operator on curve type object')
			return {"CANCELLED"}
		curveData = active_obj.data
		for i, polyline in enumerate(curveData.splines):
			points = getPolylinePoint(polyline)
			if self.opt_onlySelection:
				points = getPolylineSelPoint(polyline)
			if len(points) < 3:
				continue
			len_trg = 0
			t_xp = []
			t_yp_px = []
			t_yp_py = []
			t_yp_pz = []
			curve_pt_last = None
			for j, curve_pt in enumerate(points):
				t_yp_px.append(curve_pt.co[0])
				t_yp_py.append(curve_pt.co[1])
				t_yp_pz.append(curve_pt.co[2])
				if curve_pt_last is not None:
					len_trg = len_trg+(curve_pt_last.co-curve_pt.co).length
				t_xp.append(len_trg)
				curve_pt_last = curve_pt
			if len_trg>0.00001:
				for j, curve_pt in enumerate(points):
					t_pos = float(j)/float(len(points)-1)*len_trg
					new_co = Vector((np.interp(t_pos, t_xp, t_yp_px),np.interp(t_pos, t_xp, t_yp_py),np.interp(t_pos, t_xp, t_yp_pz),1))
					curve_pt.co = new_co
		return {"FINISHED"}

class wplcurve_smooth_til(bpy.types.Operator):
	bl_label = "Smooth tilt/radius"
	bl_idname = "curve.wplcurve_smooth_til"
	bl_description = "Smooth tilt/radius"
	bl_options = {"REGISTER", "UNDO"}

	opt_onlySelection = BoolProperty(
		name="Only Selected",
		default=True
	)
	opt_tilt_strength = IntProperty(
		name="Smooth tilt",
		default=2,
		min=-1, max=10
	)
	opt_tilt_add = FloatProperty(
		name="Additional rotation",
		min=-180.0, max=180.0,
		step=30,
		default=0.0,
	)
	opt_radius_strength = IntProperty(
		name="Smooth radius",
		default=2,
		min=-1, max=10
	)
	opt_radius_add = FloatProperty(
		name="Additional radius",
		min=-10.0, max=10.0,
		step=0.1,
		default=0.0,
	)
	opt_skipTips = BoolProperty(
		name="Protect Tips",
		default=True
	)
	opt_tilt_revert = BoolProperty(
		name="Revert tilt",
		default=False
	)
	opt_radius_revert = BoolProperty(
		name="Revert radius",
		default=False
	)

	@staticmethod
	def smooth(y, box_pts):
		len_y = len(y)
		smoothed = []
		max_val = 0
		for i in range(len(y)):
			max_val = max(max_val, y[i])
		for i in range(len(y)):
			if box_pts==0:
				smoothed.append(y[i])
				continue
			if box_pts<0:
				smoothed.append(max_val)
				continue
			low = max(0, i - box_pts)
			hi = min(len_y, i + box_pts)
			smoothed.append(np.sum(y[low:hi]) / (hi - low))  # average
		return smoothed

	def invoke(self, context, event):
		if bpy.context.mode != 'OBJECT':
			self.opt_onlySelection = True
		elif bpy.context.mode == 'OBJECT':
			self.opt_onlySelection = False
		return self.execute(context)

	def execute(self, context):
		active_obj = context.scene.objects.active
		if active_obj is None or active_obj.type != 'CURVE':
			self.report({'INFO'}, 'Use operator on curve type object')
			return {"CANCELLED"}
		curveData = active_obj.data
		for i, polyline in enumerate(curveData.splines):  # for strand point
			points = getPolylinePoint(polyline)
			if self.opt_onlySelection:
				points = getPolylineSelPoint(polyline)
			curveTiltList = [curvePoint.tilt for curvePoint in points]
			smoothedTilts = self.smooth(curveTiltList, self.opt_tilt_strength)
			curveRadList = [curvePoint.radius for curvePoint in points]
			smoothedRads = self.smooth(curveRadList, self.opt_radius_strength)
			for j, curvePoint in enumerate(points):
				if self.opt_skipTips:
					if j == 0 or j == len(points)-1:
						continue
				idxT = j
				idxR = j
				if self.opt_tilt_revert:
					idxT = len(points)-1-idxT
				if self.opt_radius_revert:
					idxR = len(points)-1-idxR
				curvePoint.tilt = smoothedTilts[idxT]+math.radians(self.opt_tilt_add)
				new_r = smoothedRads[idxR]+self.opt_radius_add
				if new_r > 0.0:
					curvePoint.radius = new_r
		return {"FINISHED"}

class wplcurve_curves_mirclon(bpy.types.Operator):
	bl_label = "Mirror duplicate"
	bl_idname = "curve.wplcurve_curves_mirclon"
	bl_options = {"REGISTER", "UNDO"}

	opt_onlySelection = BoolProperty(
		name="Only Selected",
		default=True
	)

	def invoke(self, context, event):
		if bpy.context.mode != 'OBJECT':
			self.opt_onlySelection = True
		elif bpy.context.mode == 'OBJECT':
			self.opt_onlySelection = False
		return self.execute(context)
	def execute(self, context):
		Curve = context.scene.objects.active
		if not Curve.type == 'CURVE':
			self.report({'INFO'}, 'Use operator on curve type object')
			return {"CANCELLED"}
		curveXMirror(Curve, self.opt_onlySelection)

		return {"FINISHED"}

class wplcurve_curves_unifydr(bpy.types.Operator):
	bl_label = "Unify direction"
	bl_idname = "curve.wplcurve_curves_unifydr"
	bl_options = {"REGISTER", "UNDO"}
	opt_mainDirection = FloatVectorProperty(
			name="Primary direction (begin->end)",
			default=(0,0,-1)
	)

	def execute(self, context):
		Curve = context.scene.objects.active
		if not Curve.type == 'CURVE':
			self.report({'INFO'}, 'Use operator on curve type object')
			return {"CANCELLED"}
		select_and_change_mode(Curve,'EDIT')
		maindir = Vector((self.opt_mainDirection[0],self.opt_mainDirection[1],self.opt_mainDirection[2]))
		maindir = maindir.normalized()
		curves2switch = []
		for i, polyline in enumerate(Curve.data.splines):
			# Fixing after mesh-curve conversions
			polyline.use_endpoint_u = True
			polyline.use_smooth = True
			points = getPolylinePoint(polyline)
			selpoints = getPolylineSelPoint(polyline)
			for point in points:
				point.select = False
			if len(selpoints) == 0 or len(points)<2:
				continue
			needSwitch = False
			p1 = Curve.matrix_world*points[0].co
			p1 = Vector((p1[0],p1[1],p1[2]))
			p2 = Curve.matrix_world*points[-1].co
			p2 = Vector((p2[0],p2[1],p2[2]))
			if (p1-p2).normalized().dot(maindir)>(p2-p1).normalized().dot(maindir):
				needSwitch = True
			if needSwitch:
				curves2switch.append(polyline)
		if len(curves2switch)>0:
			for polyline in curves2switch:
				points = getPolylinePoint(polyline)
				for point in points:
					point.select = True
			bpy.ops.curve.switch_direction()
		self.report({'INFO'}, "Updated "+str(len(curves2switch))+" curves")
		return {"FINISHED"}

class wplcurve_curves_hidepnt(bpy.types.Operator):
	bl_label = "Hide selected curves"
	bl_idname = "curve.wplcurve_curves_hidepnt"
	bl_options = {"REGISTER", "UNDO"}

	opt_actionType = EnumProperty(
		name="Action Type", default="HIDE",
		items=(("HIDE", "Hide", ""), ("HEADS", "Select heads", ""), ("TAILS", "Select tails", ""))
	)

	def execute(self, context):
		Curve = context.scene.objects.active
		if not Curve.type == 'CURVE':
			self.report({'INFO'}, 'Use operator on curve type object')
			return {"CANCELLED"}
		select_and_change_mode(Curve,"EDIT")
		curves_changed = 0
		sel_polylines = []
		for i, polyline in enumerate(Curve.data.splines):  # for strand point
			points = getPolylinePoint(polyline)
			selpoints = getPolylineSelPoint(polyline)
			if len(selpoints) == 0 or len(points)<2:
				continue
			sel_polylines.append((polyline,points))
		bpy.ops.curve.select_all(action='DESELECT')
		for plpair in sel_polylines:
			points = plpair[1]
			curves_changed = curves_changed+1
			if self.opt_actionType == 'HIDE':
				for j, curvePoint in enumerate(points):
					curvePoint.select = 1
				bpy.ops.curve.hide(unselected=False)
			if self.opt_actionType == 'HEADS':
				points[0].select = 1
			if self.opt_actionType == 'TAILS':
				points[-1].select = 1
		self.report({'INFO'}, "Updated "+str(curves_changed)+" curves")
		return {"FINISHED"}

# kWPDefaultBubbleElevVal = "0.0  #+0.005*FAC"
# class wplcurve_bubble_pnts(bpy.types.Operator):
# 	bl_label = "Pin to surface"
# 	bl_idname = "curve.wplcurve_bubble_pnts"
# 	bl_options = {"REGISTER", "UNDO"}

# 	opt_onlySelection = BoolProperty(
# 		name="Only Selected",
# 		default=True
# 	)
# 	opt_smoothLoops = IntProperty (
# 		name = "Smoothing loops",
# 		min = 0, max = 100,
# 		default = 3
# 	)
# 	opt_smoothPow = FloatProperty (
# 		name = "Smoothing pow",
# 		min = 0.0, max = 10.0,
# 		default = 1.0
# 	)
# 	opt_maxDistn = FloatProperty(
# 			name="Detection distance",
# 			min=0.00001, max=1000.0,
# 			default=1.0,
# 	)
# 	opt_EvalElev = StringProperty(
# 			name="Elevation",
# 			default=kWPDefaultBubbleElevVal,
# 	)
# 	opt_influence = FloatProperty(
# 			name="Influence",
# 			min=0.0, max=1.0,
# 			default=1.0,
# 	)
# 	opt_inverseDir = BoolProperty(
# 		name="Inverse direction",
# 		default=False,
# 	)
# 	opt_skipTips = BoolProperty(
# 		name="Protect Tips",
# 		default=False
# 	)
# 	def invoke(self, context, event):
# 		if bpy.context.mode != 'OBJECT':
# 			self.opt_onlySelection = True
# 		elif bpy.context.mode == 'OBJECT':
# 			self.opt_onlySelection = False
# 		return self.execute(context)

# 	def execute(self, context):
# 		Curve = context.scene.objects.active
# 		if not Curve.type == 'CURVE':
# 			self.report({'INFO'}, 'Use operator on curve type object')
# 			return {"CANCELLED"}
# 		bvh2collides = get_sceneColldersBVH(Curve,False)
# 		if len(bvh2collides) == 0:
# 			self.report({'ERROR'}, "Colliders not found: Need objects with collision modifier")
# 			return {'CANCELLED'}
# 		EvalElev_py = None
# 		try:
# 			EvalElev_py = compile(self.opt_EvalElev, "<string>", "eval")
# 		except:
# 			self.report({'ERROR'}, "Eval compilation: syntax error")
# 			return {'CANCELLED'}
# 		influDir = 1.0
# 		if self.opt_inverseDir:
# 			influDir = -1.0
# 		points_changed = 0
# 		for i, polyline in enumerate(Curve.data.splines):  # for strand point
# 			points = getPolylinePoint(polyline)
# 			allpoints = [point for point in points]
# 			if self.opt_onlySelection:
# 				points = getPolylineSelPoint(polyline)
# 			if len(points) == 0:
# 				continue
# 			for j, curvePoint in enumerate(points):  # for strand point
# 				if self.opt_skipTips and (j == 0 or j == len(points)-1):
# 					continue
# 				pt_coCur = Vector((curvePoint.co[0],curvePoint.co[1],curvePoint.co[2]))
# 				p_normal = None
# 				p_nearestCld = 9999
# 				p_nearestPnt = None
# 				for bvh_collide in bvh2collides:
# 					location, normal1, index, distance = bvh_collide.find_nearest(pt_coCur, self.opt_maxDistn)
# 					if normal1 is not None and distance < p_nearestCld:
# 						p_nearestPnt = location
# 						p_nearestCld = distance
# 						p_normal = normal1
# 				if p_nearestPnt is not None:
# 					normal2 = (p_nearestPnt-pt_coCur).normalized()*influDir
# 					if normal2 is not None and p_normal.dot(normal2) > 0.0:
# 						FAC = float(allpoints.index(curvePoint)+1)/float(len(allpoints))
# 						elevation = eval(EvalElev_py)
# 						p_nearestPnt = p_nearestPnt + p_normal*elevation
# 						if (p_nearestPnt-pt_coCur).length > kWPLRaycastEpsilonCCL:
# 							pt_coCur2 = pt_coCur.lerp(p_nearestPnt, self.opt_influence)
# 							curvePoint.co = (pt_coCur2[0],pt_coCur2[1],pt_coCur2[2],curvePoint.co[3])
# 							points_changed = points_changed+1
# 							if self.opt_smoothLoops > 0:
# 								pt_idx = allpoints.index(curvePoint)
# 								for k in range(pt_idx-self.opt_smoothLoops, pt_idx+self.opt_smoothLoops+1):
# 									if k < 0 or k == pt_idx or k >= len(allpoints):
# 										continue
# 									ptSm = allpoints[k]
# 									if ptSm in points:
# 										continue
# 									smoothInfl = pow(1.0-abs(k-pt_idx)/float(self.opt_smoothLoops), self.opt_smoothPow)
# 									ptSm_co = Vector((ptSm.co[0],ptSm.co[1],ptSm.co[2]))
# 									ptSm_co = ptSm_co+(pt_coCur2-pt_coCur)*smoothInfl
# 									ptSm.co = (ptSm_co[0], ptSm_co[1], ptSm_co[2], 1.0)
# 		self.report({'INFO'}, "Changed "+str(points_changed)+" points")
# 		return {"FINISHED"}


class wplcurve_smooth_disb(bpy.types.Operator):
	bl_label = "Distribute curves"
	bl_idname = "curve.wplcurve_smooth_disb"
	bl_options = {"REGISTER", "UNDO"}
	opt_distribRadius = BoolProperty(
			name="Distribute radius",
			default=True
		)
	opt_distribTilt = BoolProperty(
			name="Distribute tilt",
			default=True
		)
	opt_swapBndCurves = BoolProperty(
			name="Swap bound curves",
			default=False
		)
	opt_reshrink2convex = BoolProperty(
			name="Slide on convex",
			default=True
		)
	def execute(self, context):
		Curve = context.scene.objects.active
		if not Curve.type == 'CURVE':
			self.report({'INFO'}, 'Use operator on curve type object')
			return {"CANCELLED"}
		select_and_change_mode(Curve,'EDIT')
		curvesBorders = []
		curvesDistribute = []
		hullPts = []
		for i, polyline in enumerate(Curve.data.splines):
			points = getPolylinePoint(polyline)
			selpoints = getPolylineSelPoint(polyline)
			if len(selpoints) == 0:
				continue
			if len(selpoints) == 1:
				hullPts.extend(points)
				curvesBorders.append(polyline)
				continue
			hullPts.extend(points)
			curvesDistribute.append(polyline)
		if len(curvesBorders)<2:
			self.report({'INFO'}, 'Select two points on border curves')
			return {"CANCELLED"}
		if len(curvesDistribute)<1:
			self.report({'INFO'}, 'Select curves to distribute')
			return {"CANCELLED"}
		hullPtsCo = []
		for pt in hullPts:
			hullPtsCo.append(Vector((pt.co[0],pt.co[1],pt.co[2])))
		t1_xp = []# first border
		t1_yp_px = []
		t1_yp_py = []
		t1_yp_pz = []
		t1_yp_ra = []
		t1_yp_ti = []
		len_trg = 0
		curve_pt_last = None
		t1_polyline = curvesBorders[0]
		if self.opt_swapBndCurves:
			t1_polyline = curvesBorders[-1]
		if t1_polyline.type == 'NURBS' or t1_polyline.type == 'POLY':
			points = t1_polyline.points
		else:
			points = t1_polyline.bezier_points
		for j, curve_pt in enumerate(points):
			t1_yp_px.append(curve_pt.co[0])
			t1_yp_py.append(curve_pt.co[1])
			t1_yp_pz.append(curve_pt.co[2])
			t1_yp_ra.append(curve_pt.radius)
			t1_yp_ti.append(curve_pt.tilt)
			if curve_pt_last is not None:
				len_trg = len_trg+(curve_pt_last.co-curve_pt.co).length
			t1_xp.append(len_trg)
			curve_pt_last = curve_pt
		t1_len_trg = len_trg
		t2_xp = []# second border
		t2_yp_px = []
		t2_yp_py = []
		t2_yp_pz = []
		t2_yp_ra = []
		t2_yp_ti = []
		len_trg = 0
		curve_pt_last = None
		t2_polyline = curvesBorders[-1]
		if self.opt_swapBndCurves:
			t2_polyline = curvesBorders[0]
		if t2_polyline.type == 'NURBS' or t2_polyline.type == 'POLY':
			points = t2_polyline.points
		else:
			points = t2_polyline.bezier_points
		for j, curve_pt in enumerate(points):
			t2_yp_px.append(curve_pt.co[0])
			t2_yp_py.append(curve_pt.co[1])
			t2_yp_pz.append(curve_pt.co[2])
			t2_yp_ra.append(curve_pt.radius)
			t2_yp_ti.append(curve_pt.tilt)
			if curve_pt_last is not None:
				len_trg = len_trg+(curve_pt_last.co-curve_pt.co).length
			t2_xp.append(len_trg)
			curve_pt_last = curve_pt
		t2_len_trg = len_trg
		pts2upd = []# distribution
		for i, polyline in enumerate(curvesDistribute):
			points = getPolylinePoint(polyline)
			curve_frac = float(i+1)/float(len(curvesDistribute)+1)
			for j, curve_pt in enumerate(points):
				t_frac = float(j)/float(len(points)-1)
				t1_pos = t_frac*t1_len_trg
				t2_pos = t_frac*t2_len_trg
				new_co1 = Vector((np.interp(t1_pos, t1_xp, t1_yp_px),np.interp(t1_pos, t1_xp, t1_yp_py),np.interp(t1_pos, t1_xp, t1_yp_pz),1))
				new_rati1 = Vector((np.interp(t1_pos, t1_xp, t1_yp_ra),np.interp(t1_pos, t1_xp, t1_yp_ti)))
				new_co2 = Vector((np.interp(t2_pos, t2_xp, t2_yp_px),np.interp(t2_pos, t2_xp, t2_yp_py),np.interp(t2_pos, t2_xp, t2_yp_pz),1))
				new_rati2 = Vector((np.interp(t2_pos, t2_xp, t2_yp_ra),np.interp(t2_pos, t2_xp, t2_yp_ti)))
				curve_pt.co = new_co1.lerp(new_co2,curve_frac)
				new_rati = new_rati1.lerp(new_rati2,curve_frac)
				if self.opt_distribRadius:
					curve_pt.radius = new_rati[0]
				if self.opt_distribTilt:
					curve_pt.tilt = new_rati[1]
				pts2upd.append(curve_pt)
		if self.opt_reshrink2convex:
			bm_collide = bmesh.new()
			hullv = []
			for co in hullPtsCo:
				bm2v = bm_collide.verts.new(co)
				hullv.append(bm2v)
			bm_collide.verts.ensure_lookup_table()
			bm_collide.verts.index_update()
			result = bmesh.ops.convex_hull(bm_collide, input=hullv)
			bvh_collide = BVHTree.FromBMesh(bm_collide, epsilon = kWPLRaycastEpsilonCCL)
			bm_collide.free()
			for pt in pts2upd:
				p_co = Vector((pt.co[0],pt.co[1],pt.co[2]))
				loc, norm, index, distance = bvh_collide.find_nearest(p_co)
				if loc is not None:
					pt.co = Vector((loc[0],loc[1],loc[2],1))
		self.report({'INFO'}, "Updated "+str(len(pts2upd))+" curves")
		return {"FINISHED"}

# class wplcurve_stackup_pnts(bpy.types.Operator):
	# bl_label = "Stackup from surface"
	# bl_idname = "curve.wplcurve_stackup_pnts"
	# bl_options = {"REGISTER", "UNDO"}

	# opt_onlySelection = BoolProperty(
		# name="Only Selected",
		# default=True
	# )
	# opt_stackOnTail = BoolProperty(
		# name="Stack on tail, not head",
		# default=True,
	# )
	# opt_maxDistn = FloatProperty(
			# name="Detection distance",
			# min=0.00001, max=1000.0,
			# default=1.0,
	# )
	# opt_influenceDir = FloatProperty(
			# name="Influence 4shift",
			# min=0.0, max=1.0,
			# default=1.0,
	# )
	# opt_influenceRot = FloatProperty(
			# name="Influence 4rot",
			# min=0.0, max=1.0,
			# default=1.0,
	# )
	# opt_inverseDir = BoolProperty(
		# name="Inverse direction",
		# default=False,
	# )
	# opt_additionalRot = FloatProperty(
		# name="Additional rotation",
		# default=0.0,
	# )
	# def invoke(self, context, event):
		# if bpy.context.mode != 'OBJECT':
			# self.opt_onlySelection = True
		# elif bpy.context.mode == 'OBJECT':
			# self.opt_onlySelection = False
		# return self.execute(context)

	# def execute(self, context):
		# def rotateVert(vCo, rot, rot_orig, rot_axis):
			# rotM1p = Matrix.Rotation(rot,4,rot_axis)
			# rotM2p = Matrix.Translation(rot_orig) * rotM1p * Matrix.Translation(-rot_orig)
			# vco1 = rotM2p*vCo
			# return vco1
		# Curve = context.scene.objects.active
		# if not Curve.type == 'CURVE':
			# self.report({'INFO'}, 'Use operator on curve type object')
			# return {"CANCELLED"}
		# bvh2collides = get_sceneColldersBVH(Curve,False)
		# if len(bvh2collides) == 0:
			# self.report({'ERROR'}, "Colliders not found: Need objects with collision modifier")
			# return {'CANCELLED'}
		# influDir = 1.0
		# if self.opt_inverseDir:
			# influDir = -1.0
		# points_changed = 0
		# for i, polyline in enumerate(Curve.data.splines):  # for strand point
			# points = getPolylinePoint(polyline)
			# allpoints = [point for point in points]
			# if self.opt_onlySelection:
				# points = getPolylineSelPoint(polyline)
			# if len(points) < 2:
				# continue
			# p_coB = Vector((points[0].co[0],points[0].co[1],points[0].co[2]))
			# p_coB2 = Vector((points[0].co[0],points[0].co[1],points[0].co[2]))
			# if self.opt_stackOnTail:
				# p_coB = Vector((points[-1].co[0],points[-1].co[1],points[-1].co[2]))
				# p_coB2 = Vector((points[-2].co[0],points[-2].co[1],points[-2].co[2]))
			# p_normal = None
			# p_nearestCld = 9999
			# p_nearestPnt = None
			# for bvh_collide in bvh2collides:
				# location, normal1, index, distance = bvh_collide.find_nearest(p_coB, self.opt_maxDistn)
				# if normal1 is not None and distance < p_nearestCld:
					# p_nearestPnt = location
					# p_nearestCld = distance
					# p_normal = normal1
			# if p_nearestPnt is not None:
				# pt_shift = p_nearestPnt-p_coB
				# pt_rotQuat = (p_coB2-p_coB).normalized().rotation_difference(p_normal*influDir)
				# for j, curvePoint in enumerate(points):  # for strand point
					# p_coN = Vector((curvePoint.co[0],curvePoint.co[1],curvePoint.co[2]))
					# f_matRot = Matrix.Translation(p_coB) * pt_rotQuat.to_matrix().to_4x4() * Matrix.Translation(-p_coB)
					# p_coF = f_matRot*p_coN
					# p_co_lerped = p_coN.lerp(p_coF, self.opt_influenceRot)+pt_shift*self.opt_influenceDir
					# if abs(self.opt_additionalRot)>0.001:
						# p_co_lerped = rotateVert(p_co_lerped,math.radians(self.opt_additionalRot),p_coB,p_normal)
					# curvePoint.co = (p_co_lerped[0],p_co_lerped[1],p_co_lerped[2],curvePoint.co[3])
					# points_changed = points_changed+1
		# self.report({'INFO'}, "Changed "+str(points_changed)+" points")
		# return {"FINISHED"}

class wplcurve_align_tilt_view(bpy.types.Operator):
	bl_label = "Look2cam: Align tilt to camera"
	bl_idname = "curve.wplcurve_align_tilt_view"
	bl_options = {"REGISTER", "UNDO"}
	opt_onlySelection = BoolProperty(
		name="Only Selected",
		default=True
	)
	opt_independendSplines = BoolProperty(
		name="Independent splines",
		default=True
	)
	opt_stepsPrimary = FloatVectorProperty(
			name="Primary/Secondary steps",
			size=4,
			default=(-180,180,10,10)
	)
	opt_influence = FloatProperty(
			name="Influence",
			default=0.9,
	)

	@classmethod
	def poll(self, context):
		p = context.object and context.object.data and context.object.type == 'CURVE'
		return p

	def invoke(self, context, event):
		if bpy.context.mode != 'OBJECT':
			self.opt_onlySelection = True
		elif bpy.context.mode == 'OBJECT':
			self.opt_onlySelection = False
		return self.execute(context)

	def execute(self, context):
		active_obj = context.scene.objects.active
		if active_obj is None or active_obj.data is None:
			self.report({'ERROR'}, "No active object")
			return {'CANCELLED'}
		active_mesh = active_obj.data
		camera_obj = context.scene.objects.get(kWPLEdgesMainCam)
		if camera_obj is None:
			self.report({'ERROR'}, "Camera not found: "+kWPLEdgesMainCam)
			return {'CANCELLED'}
		camera_gCo = camera_obj.matrix_world.to_translation() #camera_obj.location
		camera_gDir = camera_obj.matrix_world.to_3x3()*Vector((0.0, 0.0, 1.0))
		camera_gOrtho = False
		if camera_obj.data.type == 'ORTHO':
			camera_gOrtho = True
		oldmode = select_and_change_mode(active_obj,'OBJECT')
		initilts = {}
		for i, polyline in enumerate(active_obj.data.splines):
			points = getPolylinePoint(polyline)
			for j, curvePoint in enumerate(points):
				initilts[curvePoint] = 0.0+curvePoint.tilt
		def tiltTryout(splnId, step_tilt, influence, doRealtesting):
			points_count = 0
			select_and_change_mode(active_obj,'OBJECT')
			for i, polyline in enumerate(active_obj.data.splines):
				# restoring tilts for non-tryout curves
				points = getPolylinePoint(polyline)
				if splnId < 0 or splnId != i:
					continue
				if self.opt_onlySelection:
					points = getPolylineSelPoint(polyline)
				if len(points) == 0:
					#nothing to do
					return None
				for j, curvePoint in enumerate(points):  # for strand point
					points_count = points_count+1
					curvePoint.tilt = initilts[curvePoint]+(step_tilt-initilts[curvePoint])*influence
			normalDifference = 0
			if doRealtesting:
				curveMesh = active_obj.to_mesh(context.scene, False, 'PREVIEW')
				bmFromCurve = bmesh.new()
				bmFromCurve.from_mesh(curveMesh)
				bmFromCurve.verts.ensure_lookup_table()
				bmFromCurve.faces.ensure_lookup_table()
				bmFromCurve.verts.index_update()
				bmFromCurve.faces.index_update()
				testedFaces = 0
				for f in bmFromCurve.faces:
					if camera_gOrtho:
						view_dir = camera_gDir
					else:
						f_co_g = active_obj.matrix_world*f.calc_center_median()
						view_dir = (camera_gCo-f_co_g).normalized()
					#fnrm_g = active_obj.matrix_world.to_3x3() * f.normal
					fnrm_g = active_obj.matrix_world.inverted().transposed().to_3x3() * f.normal
					ddt = view_dir.dot(fnrm_g)
					normalDifference = normalDifference + ddt
					testedFaces = testedFaces+1
				#print("-- testd:",testedFaces,len(bmFromCurve.faces))
				bpy.data.meshes.remove(curveMesh)
				bmFromCurve.free()
			#print("- Tryout for curve:", splnId,"; points affected:",points_count,"; angle:",math.degrees(step_tilt),"->",normalDifference)
			return normalDifference
		if self.opt_stepsPrimary[2]>1:
			for splnId in range(len(active_obj.data.splines)):
				maximalDiff = None
				minimalTilt = 0
				minimalTiltAddon = 0
				test_splnId = splnId
				if self.opt_independendSplines == False:
					test_splnId = -1
				for stp in range(int(self.opt_stepsPrimary[2])):
					angle = math.radians(self.opt_stepsPrimary[0])+float(stp)/float(self.opt_stepsPrimary[2]-1)*(math.radians(self.opt_stepsPrimary[1]-self.opt_stepsPrimary[0]))
					diff = tiltTryout(test_splnId, angle, 1.0, True)
					#print("tiltTryout primary", splnId, stp,angle,diff)
					if diff is not None and (maximalDiff is None or diff > maximalDiff):
						maximalDiff = diff
						minimalTilt = angle
				if self.opt_stepsPrimary[3]>1:
					fullStepDeg = (self.opt_stepsPrimary[1]-self.opt_stepsPrimary[0])/(self.opt_stepsPrimary[2]-1)
					finet1 = -fullStepDeg
					finet2 = fullStepDeg
					for stp in range(int(self.opt_stepsPrimary[3])):
						angle = math.radians(finet1)+float(stp)/float(self.opt_stepsPrimary[3]-1)*(math.radians(finet2-finet1))
						diff = tiltTryout(test_splnId, minimalTilt+angle, 1.0, True)
						#print("tiltTryout Finetune", splnId, stp, minimalTilt+angle, diff)
						if diff is not None and (maximalDiff is None or diff > maximalDiff):
							maximalDiff = diff
							minimalTiltAddon = angle
				if maximalDiff is not None:
					print("-- Align to view result:", splnId, math.degrees(minimalTilt+minimalTiltAddon), maximalDiff)
				tiltTryout(splnId, minimalTilt+minimalTiltAddon, self.opt_influence, False)
				if test_splnId < 0:
					break
		select_and_change_mode(active_obj,oldmode)
		self.report({'INFO'}, "Done")
		return {"FINISHED"}

class wplcurve_align_tilt_coll(bpy.types.Operator):
	bl_label = "Align tilt to colliders"
	bl_idname = "curve.wplcurve_align_tilt_coll"
	bl_options = {"REGISTER", "UNDO"}

	opt_onlySelection = BoolProperty(
		name="Only Selected",
		default=True
	)
	opt_independendSplines = BoolProperty(
		name="Independent splines",
		default=True
	)
	opt_stepsPrimary = FloatVectorProperty(
			name="Primary/Secondary steps",
			size=4,
			default=(-180,180,10,10)
	)
	opt_testDist = FloatProperty(
			name="Nearness distance",
			min=0.00001, max=100.0,
			default=0.1,
	)
	opt_tilt_add = FloatProperty(
			name="Additional rotation",
			min=-180.0, max=180.0,
			step=30,
			default=0.0,
	)

	@classmethod
	def poll(self, context):
		p = context.object and context.object.data and context.object.type == 'CURVE'
		return p

	def invoke(self, context, event):
		if bpy.context.mode != 'OBJECT':
			self.opt_onlySelection = True
		elif bpy.context.mode == 'OBJECT':
			self.opt_onlySelection = False
		return self.execute(context)

	def execute(self, context):
		active_obj = context.scene.objects.active
		if active_obj is None or active_obj.data is None:
			self.report({'ERROR'}, "No active object")
			return {'CANCELLED'}
		if abs(active_obj.scale[0]-1.0)+abs(active_obj.scale[1]-1.0)+abs(active_obj.scale[2]-1.0) > 0.001:
			self.report({'ERROR'}, "Scale not applied")
			return {'CANCELLED'}
		active_mesh = active_obj.data
		bvh2collides = get_sceneColldersBVH(None,False)
		if len(bvh2collides) == 0:
			self.report({'ERROR'}, "Colliders not found: Need objects with collision modifier")
			return {'CANCELLED'}
		initilts = {}
		for i, polyline in enumerate(active_obj.data.splines):
			points = getPolylinePoint(polyline)
			for j, curvePoint in enumerate(points):
				initilts[curvePoint] = curvePoint.tilt
		def tiltTryout(splnId, step_tilt, doRealtesting):
			points_count = 0
			if step_tilt > - 999:
				for i, polyline in enumerate(active_obj.data.splines):
					# restoring tilts for non-tryout curves
					points = getPolylinePoint(polyline)
					if splnId < 0 or splnId != i:
						continue
					if self.opt_onlySelection:
						points = getPolylineSelPoint(polyline)
					if len(points) == 0:
						#nothing to do
						return None
					for j, curvePoint in enumerate(points):  # for strand point
						points_count = points_count+1
						curvePoint.tilt = step_tilt
			normalDifference = 0
			if doRealtesting:
				bmFromCurve = bmesh.new()
				curveMesh = active_obj.to_mesh(context.scene, True, 'PREVIEW')
				bmFromCurve.from_mesh(curveMesh)
				bmFromCurve.verts.ensure_lookup_table()
				bmFromCurve.faces.ensure_lookup_table()
				bmFromCurve.verts.index_update()
				bmFromCurve.faces.index_update()
				for cld in bvh2collides:
					for f in bmFromCurve.faces:
						f_co_g = active_obj.matrix_world*f.calc_center_median()
						location, normal, index, distance = cld.find_nearest(f_co_g,self.opt_testDist)
						if normal is not None:
							fnrm_g = active_obj.matrix_world.inverted().transposed().to_3x3() * f.normal
							ddt = fnrm_g.dot(normal)
							normalDifference = normalDifference + ddt
				bpy.data.meshes.remove(curveMesh)
				bmFromCurve.free()
				#print("- Tryout for curve:", splnId,"; points affected:",points_count,"test tilt:", step_tilt,"normalDifference:",normalDifference)
			return normalDifference

		#tiltTryout(-1, -999, True)
		if self.opt_stepsPrimary[2]>1:
			for splnId in range(len(active_obj.data.splines)):
				maximalDiff = None
				minimalTilt = 0
				minimalTiltAddon = 0
				test_splnId = splnId
				if self.opt_independendSplines == False:
					test_splnId = -1
				#testing initial
				for stp in range(int(self.opt_stepsPrimary[2])):
					angle = math.radians(self.opt_stepsPrimary[0])+float(stp)/float(self.opt_stepsPrimary[2]-1)*(math.radians(self.opt_stepsPrimary[1]-self.opt_stepsPrimary[0]))
					diff = tiltTryout(test_splnId, angle, True)
					#print("tiltTryout primary", splnId, stp,angle,diff)
					if diff is not None and (maximalDiff is None or diff > maximalDiff):
						maximalDiff = diff
						minimalTilt = angle
				if self.opt_stepsPrimary[3]>1:
					fullStepDeg = (self.opt_stepsPrimary[1]-self.opt_stepsPrimary[0])/(self.opt_stepsPrimary[2]-1)
					finet1 = -fullStepDeg
					finet2 = fullStepDeg
					for stp in range(int(self.opt_stepsPrimary[3])):
						angle = math.radians(finet1)+float(stp)/float(self.opt_stepsPrimary[3]-1)*(math.radians(finet2-finet1))
						diff = tiltTryout(test_splnId,minimalTilt+angle, True)
						#print("tiltTryout Finetune", splnId, stp, minimalTilt+angle, diff)
						if diff is not None and (maximalDiff is None or diff > maximalDiff):
							maximalDiff = diff
							minimalTiltAddon = angle
				if maximalDiff is not None:
					print("-- Align to colliders result:", splnId, minimalTilt, minimalTiltAddon, maximalDiff)
				tiltTryout(splnId, minimalTilt+minimalTiltAddon+math.radians(self.opt_tilt_add), False)
				if test_splnId < 0:
					break
		self.report({'INFO'}, "Done")
		return {"FINISHED"}

class wplcurve_add_bevel(bpy.types.Operator):
	bl_label = "Create bevel"
	bl_idname = "curve.wplcurve_add_bevel"
	bl_options = {"REGISTER", "UNDO"}
	bl_description = "Add ribbon to curve profile"

	strandResU = IntProperty(
		name="Segments U", default=3, min=1, max=10
	)
	strandResV = IntProperty(
		name="Segments V", default=2, min=1, max=10
	)
	opt_strandWidth = FloatProperty(
		name="Strand Width", default=1.0, min=0.0, max=10
	)
	strandPeak = FloatProperty(
		name="Strand peak", default=0.4, min=0.0, max=10
	)
	strandUplift = FloatProperty(
		name="Strand uplift", default=0.0, min=-10, max=10
	)
	opt_tilt_add = FloatProperty(
		name="Additional tilt",
		min=-180.0, max=180.0,
		step=30,
		default=0.0
	)
	opt_replaceExistingBevel = BoolProperty(
		name="Auto-replace existing bevel",
		default=True
	)

	def invoke(self,context, event):
		if context.scene.objects.active is None or context.scene.objects.active.type != 'CURVE':
			self.report({'INFO'}, 'Select curve object first')
			return {"CANCELLED"}
		hairCurve = context.scene.objects.active
		# unitsScale = 1 #context.scene.unit_settings.scale_length
		# self.diagonal = math.sqrt(pow(hairCurve.dimensions[0], 2) + pow(hairCurve.dimensions[1], 2) + pow(hairCurve.dimensions[2], 2))  # to normalize some values
		bevelObj = hairCurve.data.bevel_object
		if bevelObj:
			points = bevelObj.data.splines[0].points[:]
			self.strandResV = len(points)-1
			self.strandResU = hairCurve.data.resolution_u
		return  self.execute(context)

	def execute(self, context):
		hairCurve = context.scene.objects.active
		pointsCo = []
		strandWidth = self.opt_strandWidth * max(0.001,hairCurve.data.bevel_depth)
		for i in range(self.strandResV + 1):
			x = 2 * i / self.strandResV - 1  # normalise and map from -1 to 1
			pointsCo.append((x * strandWidth , ((1 - x * x) * self.strandPeak + self.strandUplift) * strandWidth  , 0))  # **self.strandWidth to mantain proportion while changing widht
		# create the Curve Datablock
		if self.opt_replaceExistingBevel and hairCurve.data.bevel_object:
			curveBevelObj = hairCurve.data.bevel_object
			curveBevelObj.data.splines.clear()
			BevelCurveData = curveBevelObj.data
		else:
			BevelCurveData = bpy.data.curves.new("sys_"+hairCurve.name+kWPLCurveBvlPostfix, type='CURVE')  # new CurveData
			BevelCurveData.dimensions = '2D'
			curveBevelObj = bpy.data.objects.new("sys_"+hairCurve.name+kWPLCurveBvlPostfix, BevelCurveData)  # new object
			hairCurve.data.bevel_object = curveBevelObj
			makeObjectNoShadow(curveBevelObj, True, True)
		bevelSpline = BevelCurveData.splines.new('POLY')  # new spline
		bevelSpline.points.add(len(pointsCo) - 1)
		for i, coord in enumerate(pointsCo):
			x, y, z = coord
			bevelSpline.points[i].co = (x, y, z, 1)
		#curveBevelObj.use_fake_user = True
		materializeBevel(context, curveBevelObj, hairCurve)
		hairCurve.data.resolution_u = self.strandResU
		hairCurve.data.use_auto_texspace = True
		hairCurve.data.use_uv_as_generated = True
		hairCurve.data.show_normal_face = False
		if abs(self.opt_tilt_add) > 0.01:
			for i, polyline in enumerate(hairCurve.data.splines):  # for strand point
				points = getPolylinePoint(polyline)
				for j, curvePoint in enumerate(points):
					curvePoint.tilt = curvePoint.tilt+math.radians(self.opt_tilt_add)
		return {"FINISHED"}

class wplcurve_edit_bevel(bpy.types.Operator):
	bl_label = "Edit bevel"
	bl_idname = "curve.wplcurve_edit_bevel"
	bl_options = {"REGISTER", "UNDO"}
	bl_description = "Edit ribbon curve"

	opt_curveType = EnumProperty(
		name="Subcurve type", default="BEVEL",
		items=(("BEVEL", "Bevel", ""), ("TAPER", "Taper", ""))
	)

	def invoke(self,context, event):
		if context.scene.objects.active.type != 'CURVE':
			self.report({'INFO'}, 'Select curve object first')
			return {"CANCELLED"}
		return  self.execute(context)


	def execute(self, context):
		if context.scene.objects.active is None or context.scene.objects.active.type != 'CURVE':
			self.report({'INFO'}, 'Select curve object first')
			return {"CANCELLED"}
		hairCurve = context.scene.objects.active
		subcurveObj = None
		if self.opt_curveType == 'BEVEL':
			subcurveObj = hairCurve.data.bevel_object
		if self.opt_curveType == 'TAPER':
			subcurveObj = hairCurve.data.taper_object
		if subcurveObj is None:
			return {"CANCELLED"}
		if get_isLocalView():
			self.report({'ERROR'}, "Can`t work in Local view")
			return {'CANCELLED'}
		materializeBevel(context, subcurveObj, hairCurve)
		hairCurve.select = False
		subcurveObj.select = True
		select_and_change_mode(subcurveObj, 'EDIT')
		bpy.ops.view3d.localview()
		bpy.ops.view3d.viewnumpad(type='TOP')
		bpy.ops.curve.select_all(action = 'SELECT')
		return {"FINISHED"}

class wplcurve_curve_2mesh(bpy.types.Operator):
	bl_label = "Final meshing: Convert curve"
	bl_idname = "curve.wplcurve_curve_2mesh"
	bl_options = {"REGISTER", "UNDO"}
	bl_description = 'Bake curve to mesh with metadata'

	def execute(self, context):
		if get_isLocalView():
			self.report({'ERROR'}, "Can`t work in Local view")
			return {'CANCELLED'}
		if context.scene.objects.active is None or context.scene.objects.active.type != 'CURVE':
			self.report({'INFO'}, 'Select curve object first')
			return {"CANCELLED"}
		active_obj = context.scene.objects.active
		if active_obj.hide_select == True:
			self.report({'INFO'}, 'Curve not selectable')
			return {"CANCELLED"}
		select_and_change_mode(active_obj, 'OBJECT')
		needReAddMirror = False
		if len(toggleModifs(active_obj,['MIRROR'],None,None))>0:
			needReAddMirror = True
		needReAddEdgeSplit = False
		if len(toggleModifs(active_obj,['EDGE_SPLIT'],None,None))>0:
			needReAddEdgeSplit = True
		curveData = active_obj.data
		curve_poly_lencache = {}
		curve_poly_radcache = {}
		if len(active_obj.data.materials)>0:
			while len(active_obj.data.materials)<len(curveData.splines):
				active_obj.data.materials.append(active_obj.data.materials[0])
			for i,polyline in enumerate(curveData.splines):
				points = getPolylinePoint(polyline)
				polyline.material_index = i
				#bpy.ops.curve.select_all(action='DESELECT')
				#points[0].select = True
				#active_obj.data.active_material_index = i
				#bpy.ops.object.material_slot_assign()
				#bpy.ops.curve.select_all(action='DESELECT')
				clen = 0
				crad = 0
				clen_pprev = None
				for p in points:
					if clen_pprev is not None:
						clen = clen+(p.co-clen_pprev.co).length
					if p.radius > crad:
						crad = p.radius
					clen_pprev = p
				curve_poly_lencache[i] = clen
				curve_poly_radcache[i] = crad
		mfcName = "fin_"+active_obj.name # at start, since curves with "()" in name MUST end on (...) - for OSL
		mfcOld = context.scene.objects.get(mfcName)
		if mfcOld is not None:
			bpy.data.objects.remove(mfcOld, True)
		meshFromCurve = active_obj.to_mesh(bpy.context.scene, False, 'PREVIEW')
		meshObjFromCurve = bpy.data.objects.new(mfcName, meshFromCurve)
		bpy.context.scene.objects.link(meshObjFromCurve)
		meshObjFromCurve.parent = active_obj.parent
		meshObjFromCurve.matrix_world = active_obj.matrix_world
		meshObjFromCurve.color = active_obj.color
		meshObjFromCurve.cycles_visibility.camera = active_obj.cycles_visibility.camera
		meshObjFromCurve.cycles_visibility.diffuse = active_obj.cycles_visibility.diffuse
		meshObjFromCurve.cycles_visibility.glossy = active_obj.cycles_visibility.glossy
		meshObjFromCurve.cycles_visibility.transmission = active_obj.cycles_visibility.transmission
		meshObjFromCurve.cycles_visibility.scatter = active_obj.cycles_visibility.scatter
		meshObjFromCurve.cycles_visibility.shadow = active_obj.cycles_visibility.shadow
		if needReAddEdgeSplit:
			meshObjFromCurve.modifiers.new("Edge Split", 'EDGE_SPLIT')
		if needReAddMirror:
			meshObjFromCurve.modifiers.new("Mirror", 'MIRROR')
		meshObjFromCurve.modifiers.new("Subsurf", 'SUBSURF')
		if kWPLMeshColVC in active_obj:
			meshObjFromCurve[kWPLMeshColVC] = active_obj[kWPLMeshColVC]
		select_and_change_mode(meshObjFromCurve, 'OBJECT')
		active_obj.hide_render = True
		active_obj.hide_select = True
		active_obj.hide = True
		curvl_map = meshFromCurve.uv_layers.get(kWPLCurveUVCurvlen)
		if curvl_map is None:
			meshFromCurve.uv_textures.new(kWPLCurveUVCurvlen)
			curvl_map = meshFromCurve.uv_layers.get(kWPLCurveUVCurvlen)
		curvr_map = meshFromCurve.uv_layers.get(kWPLCurveUVCurvrad)
		if curvr_map is None:
			meshFromCurve.uv_textures.new(kWPLCurveUVCurvrad)
			curvr_map = meshFromCurve.uv_layers.get(kWPLCurveUVCurvrad)
		for poly in meshFromCurve.polygons:
			poly_curv = poly.material_index
			ipoly = poly.index
			for idx, lIdx in enumerate(meshFromCurve.polygons[ipoly].loop_indices):
				ivdx = meshFromCurve.polygons[ipoly].vertices[idx]
				curvl_map.data[lIdx].uv = Vector((poly_curv,curve_poly_lencache[poly_curv]))
				curvr_map.data[lIdx].uv = Vector((poly_curv,curve_poly_radcache[poly_curv]))
		bpy.ops.object.wpluvvg_islandsmid()
		return {"FINISHED"}

class wplcurve_recreate(bpy.types.Operator):
	bl_label = "Recreate from selected"
	bl_idname = "curve.wplcurve_recreate"
	bl_options = {"REGISTER", "UNDO"}

	opt_widthProfile = FloatVectorProperty(
		name = "Width profile (start, end, pow)",
		size = 3,
		default	 = kWPLDefaultEdgeProfile
	)
	opt_postSubd = IntProperty (
		name = "Subdivide curve",
		default = 0
	)
	opt_delUsed = BoolProperty (
		name = "Delete used",
		default = True
	)

	@classmethod
	def poll( cls, context ):
		p = context.object and context.object and context.object.type == 'CURVE'
		return p

	def execute(self, context):
		active_obj = context.scene.objects.active
		if active_obj is None or active_obj.type != 'CURVE':
			self.report({'INFO'}, 'Use operator on curve type object')
			return {"CANCELLED"}
		select_and_change_mode(active_obj, 'EDIT')
		curveData = active_obj.data
		basePoints = []
		(selected_polys,selected_polys_sp,_) = curve_getSelectedPolys(curveData, False, True)
		for i in range(len(selected_polys)):
			points_all = selected_polys[i]
			points_sel = selected_polys_sp[i]
			if(len(points_sel) > 0):
				for sp in points_sel:
					basePoints.append(sp)
		# first point. most far from others
		basePoints2 = []
		for sp1 in basePoints:
			sumDot = 0
			for sp2 in basePoints:
				for sp3 in basePoints:
					if sp1==sp2 or sp1==sp3 or sp2==sp3:
						continue
					sp1co = Vector((sp1.co[0], sp1.co[1], sp1.co[2]))
					sp2co = Vector((sp2.co[0], sp2.co[1], sp2.co[2]))
					sp3co = Vector((sp3.co[0], sp3.co[1], sp3.co[2]))
					sumDot = sumDot + (sp2co-sp1co).normalized().dot((sp3co-sp1co).normalized())
			basePoints2.append((sp1, sumDot))
		basePoints2 = sorted(basePoints2, key=lambda v:v[1], reverse=True)
		# sorting new points by distance
		basePoints3 = []
		basePoints3.append(basePoints2[0][0])
		while len(basePoints3)<len(basePoints):
			sp1 = basePoints3[-1]
			nextp = None
			nextpDist = 999
			for sp2 in basePoints:
				if sp2 in basePoints3:
					continue
				sp1co = Vector((sp1.co[0], sp1.co[1], sp1.co[2]))
				sp2co = Vector((sp2.co[0], sp2.co[1], sp2.co[2]))
				sp12len = (sp2co-sp1co).length
				if sp12len<nextpDist:
					nextpDist = sp12len
					nextp = sp2
			if nextp is None:
				break
			basePoints3.append(nextp)
		# creating new curve
		newPolyPoints = []
		if len(basePoints3) > 1:
			radMax = 0
			newPolyline = curveData.splines.new('NURBS')
			newPolyline.order_u = 3 # like bezier thing
			newPolyline.use_endpoint_u = True
			newPolyline.points.add(len(basePoints3) - 1)
			for j, sp in enumerate(basePoints3):
				if sp.radius > radMax:
					radMax = sp.radius
				newPolyPoints.append(newPolyline.points[j])
				newPolyline.points[j].co = (sp.co[0], sp.co[1], sp.co[2], 1)
				newPolyline.points[j].radius = sp.radius
			curve_rescaleRadius(newPolyPoints, self.opt_widthProfile, 0.5, radMax)
		if self.opt_delUsed:
			for poly in selected_polys:
				bpy.ops.curve.select_all(action='DESELECT')
				for p in poly:
					p.select = True
				bpy.ops.curve.delete(type='VERT')
		bpy.ops.curve.select_all(action='DESELECT')
		for sp in newPolyPoints:
			sp.select = True
		if self.opt_postSubd>0:
			for i in range(int(self.opt_postSubd)):
				bpy.ops.curve.subdivide()
		self.report({'INFO'}, "Done. verts="+str(len(newPolyPoints)))
		return {"FINISHED"}

class wplcurve_disjoint(bpy.types.Operator):
	bl_label = "Disjoint selected curves"
	bl_idname = "curve.wplcurve_disjoint"
	bl_options = {"REGISTER", "UNDO"}

	opt_widthProfile = bpy.props.FloatVectorProperty(
		name		= "Width profile (start, end, pow)",
		size = 3,
		default	 = kWPLDefaultEdgeProfile
	)

	@classmethod
	def poll( cls, context ):
		p = context.object and context.object and context.object.type == 'CURVE'
		return p

	def execute(self, context):
		active_obj = context.scene.objects.active
		if active_obj is None:
			self.report({'INFO'}, 'Nothing selected')
			return {"CANCELLED"}
		select_and_change_mode(active_obj, 'EDIT')
		curveData = active_obj.data
		(selected_polys,selected_polys_sp,_) = curve_getSelectedPolys(curveData, False, True)
		for i in range(len(selected_polys)):
			points_all = selected_polys[i]
			points_sel = selected_polys_sp[i]
			if(len(points_sel) == 1):
				# selecting to shorter end
				idx = points_all.index(points_sel[0])
				if idx > len(points_all)/2:
					if idx < len(points_all)-1:
						points_all[idx+1].select = True
				else:
					if idx > 0:
						points_all[idx-1].select = True
		bpy.ops.curve.delete(type='SEGMENT')
		(selected_polys,selected_polys_sp,_) = curve_getSelectedPolys(curveData, True, False)
		okCnt = 0
		for poly in selected_polys:
			if len(poly) <= 1:# clearing 1-pointed polis
				for p in poly:
					p.select = True
					okCnt = okCnt+1
				bpy.ops.curve.delete(type='VERT')
				continue
			radMax = 0
			for p in poly:
				if p.radius > radMax:
					radMax = p.radius
			curve_rescaleRadius(poly, self.opt_widthProfile, 0.5, radMax)
		self.report({'INFO'}, "Done. verts="+str(okCnt))
		return {"FINISHED"}

class wplcurve_merge(bpy.types.Operator):
	bl_idname = "curve.wplcurve_merge"
	bl_label = "Merge selected curves"
	bl_options = {'REGISTER', 'UNDO'}
	opt_mergeMeth = EnumProperty(
		items = [
			('NEAREST', "Nearest", "", 1),
			('RECUT', "Cut-off", "", 2),
		],
		name="Merge method",
		default='NEAREST',
	)
	opt_postSubdiv = IntProperty(
		name="Post-subdiv segments",
		min=0, max=10,
		default=2,
	)
	opt_widthProfile = bpy.props.FloatVectorProperty(
		name		= "Width profile (start, end, pow)",
		size = 3,
		default	 = kWPLDefaultEdgeProfile
	)
	@classmethod
	def poll( cls, context ):
		p = context.object and context.object and context.object.type == 'CURVE'
		return p

	def execute( self, context ):
		active_obj = context.scene.objects.active
		select_and_change_mode(active_obj,'EDIT')
		curveData = active_obj.data
		(selected_polys_all, selected_polys_pnt, selected_polys_curv) = curve_getSelectedPolys(curveData, True, True)
		if len(selected_polys_all) < 2:
			self.report({'ERROR'}, "Select two distinct curves first")
			return {'CANCELLED'}
		minpp = None
		if self.opt_mergeMeth == 'RECUT':
			minpp = []
			bpy.ops.curve.select_all(action='DESELECT')
			for curv in range(0,2):
				pt_sel = selected_polys_pnt[curv][0]
				pt_sel_idx = selected_polys_all[curv].index(pt_sel)
				total_pts = len(selected_polys_all[curv])
				#print("pt_sel_idx", pt_sel, pt_sel_idx, len(selected_polys_all[curv]))
				if pt_sel_idx == 0 or pt_sel_idx == total_pts-1:
					minpp.append(pt_sel)
					continue
				pt_curve = selected_polys_curv[curv]
				if pt_sel_idx < total_pts-1-pt_sel_idx:
					for i in reversed(range(0,pt_sel_idx)):
						curve_delPointByIndex(pt_curve, i)
					minpp.append(pt_curve.points[0])
				else:
					for i in reversed(range(pt_sel_idx+1,total_pts)):
						curve_delPointByIndex(pt_curve, i)
					minpp.append(pt_curve.points[pt_sel_idx])
		else:
			possibilities = [(selected_polys_all[0][0],selected_polys_all[1][0]),(selected_polys_all[0][0],selected_polys_all[1][-1]),(selected_polys_all[0][-1],selected_polys_all[1][0]),(selected_polys_all[0][-1],selected_polys_all[1][-1])]
			minlen = 9999
			for pp in possibilities:
				posn = (pp[0].co-pp[1].co).length
				if posn<minlen:
					minlen = posn
					minpp = pp
		if minpp is not None:
			minpp[0].select = True
			minpp[1].select = True
			bpy.ops.curve.make_segment()
			if self.opt_postSubdiv>0:
				for i in range(self.opt_postSubdiv):
					bpy.ops.curve.subdivide()
			(selected_polys_all, _, _) = curve_getSelectedPolys(curveData, False, False)
			for poly in selected_polys_all:
				radMax = 0
				for p in poly:
					if p.radius > radMax:
						radMax = p.radius
				curve_rescaleRadius(poly, self.opt_widthProfile, 0.5, radMax)
		return {'FINISHED'}

class wplcurve_fastpin_mesh(bpy.types.Operator):
	bl_idname = "mesh.wplcurve_fastpin_mesh"
	bl_label = "Store edges"
	bl_options = {'REGISTER', 'UNDO'}

	opt_flowDir = FloatVectorProperty(
		name	 = "Preferred direction",
		size	 = 3,
		min=-1.0, max=1.0,
		default	 = (0.0,0.0,-1.0)
	)

	@classmethod
	def poll( cls, context ):
		p = context.object and context.object and context.object.type == 'MESH'
		return p

	def execute( self, context ):
		active_obj = context.scene.objects.active
		if active_obj is None:
			self.report({'INFO'}, 'Nothing selected')
			return {"CANCELLED"}
		active_mesh = active_obj.data
		vertsIdx = get_selected_vertsIdx(active_mesh)
		edgesIdx = get_selected_edgesIdx(active_mesh)
		if len(edgesIdx)<1:
			self.report({'ERROR'}, "No selected edges found, select some edges first")
			return {'FINISHED'} # or all changes get lost!!!
		bpy.ops.object.mode_set( mode = 'EDIT' )
		#bpy.ops.mesh.select_mode(type="FACE")
		#bm = bmesh.from_edit_mesh( active_mesh )
		bm = bmesh.new()
		bm.from_object(active_obj, context.scene, deform=True, render=False, cage=True, face_normals=True)
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		(strands_points,strands_radius,strands_vidx) = getBmEdgesAsStrands_v04(bm, vertsIdx, edgesIdx, self.opt_flowDir, active_obj)
		if strands_points is None:
			self.report({'ERROR'}, "No edges found")
			return {'FINISHED'} # or all changes get lost!!!
		WPL_G.store["wplcurve_fastpin_mesh"] = strands_points
		self.report({'INFO'}, "Done. points="+str(len(strands_points[0])))
		return {'FINISHED'}

class wplcurve_fastpin_mesh_apl(bpy.types.Operator):
	bl_idname = "curve.wplcurve_fastpin_mesh_apl"
	bl_label = "Align points to stored edges"
	bl_options = {'REGISTER', 'UNDO'}

	opt_onlySelection = BoolProperty(
		name="Only Selected",
		default=True
	)

	opt_invertDir = BoolProperty(
		name="Invert direction",
		default=False
	)

	@classmethod
	def poll( cls, context ):
		p = context.object and context.object and context.object.type == 'CURVE'
		return p

	def execute( self, context ):
		active_obj = context.scene.objects.active
		if active_obj is None:
			self.report({'INFO'}, 'Nothing selected')
			return {"CANCELLED"}
		if bpy.context.mode != 'EDIT_CURVE':
			select_and_change_mode(active_obj,'EDIT')
		curveData = active_obj.data
		if ("wplcurve_fastpin_mesh" not in WPL_G.store) or (len(WPL_G.store["wplcurve_fastpin_mesh"]) == 0):
			self.report({'ERROR'}, "Pin points first")
			return {'CANCELLED'}
		okPts = 0
		curStr = 0
		strands_points = WPL_G.store["wplcurve_fastpin_mesh"]
		for i,polyline in enumerate(curveData.splines):
			pns = getPolylinePoint(polyline)
			if self.opt_onlySelection:
				pns = getPolylineSelPoint(polyline)
			if len(pns) == 0:
				continue
			strand = strands_points[curStr]
			t_yp_px = []
			t_yp_py = []
			t_yp_pz = []
			len_trg = 0
			t_xp = []
			gp_p_last = None
			for gp_p in strand:
				t_yp_px.append(gp_p[0])
				t_yp_py.append(gp_p[1])
				t_yp_pz.append(gp_p[2])
				if gp_p_last is not None:
					len_trg = len_trg+(gp_p_last-gp_p).length
				t_xp.append(len_trg)
				gp_p_last = gp_p
			if len_trg>0.00001:
				if polyline.type == 'NURBS' or polyline.type == 'POLY':
					for j, curve_pt in enumerate(pns):
						okPts = okPts+1
						t_pos = float(j)/float(len(pns)-1)
						if self.opt_invertDir:
							t_pos = 1.0 - t_pos
						new_co_g = Vector((np.interp(t_pos*len_trg, t_xp, t_yp_px), np.interp(t_pos*len_trg, t_xp, t_yp_py), np.interp(t_pos*len_trg, t_xp, t_yp_pz)))
						new_co_l = active_obj.matrix_world.inverted() * new_co_g
						curve_pt.co = Vector((new_co_l[0], new_co_l[1], new_co_l[2], 1))
				if polyline.type == 'BEZIER':
					# specially for Bezier Mesh Shaper
					for j, curve_pt in enumerate(pns):
						okPts = okPts+1
						t_pos = float(j)/float(len(pns)-1)
						t_pos_l = float(j-0.3)/float(len(pns)-1)
						t_pos_r = float(j+0.3)/float(len(pns)-1)
						if self.opt_invertDir:
							t_pos = 1.0 - t_pos
							t_pos_l = 1.0 - t_pos_l
							t_pos_r = 1.0 - t_pos_r
						new_co_g = Vector((np.interp(t_pos*len_trg, t_xp, t_yp_px), np.interp(t_pos*len_trg, t_xp, t_yp_py), np.interp(t_pos*len_trg, t_xp, t_yp_pz)))
						new_co_l = active_obj.matrix_world.inverted() * new_co_g
						new_coL_g = Vector((np.interp(t_pos_l*len_trg, t_xp, t_yp_px), np.interp(t_pos_l*len_trg, t_xp, t_yp_py), np.interp(t_pos_l*len_trg, t_xp, t_yp_pz)))
						new_coL_l = active_obj.matrix_world.inverted() * new_coL_g
						new_coR_g = Vector((np.interp(t_pos_r*len_trg, t_xp, t_yp_px), np.interp(t_pos_r*len_trg, t_xp, t_yp_py), np.interp(t_pos_r*len_trg, t_xp, t_yp_pz)))
						new_coR_l = active_obj.matrix_world.inverted() * new_coR_g
						if t_pos_l <= 0.0:
							new_coL_l = new_co_l - (new_coR_l-new_co_l)
						if t_pos_r >= 1.0:
							new_coR_l = new_co_l - (new_coL_l-new_co_l)
						curve_pt.co = Vector((new_co_l[0], new_co_l[1], new_co_l[2]))
						curve_pt.handle_left = Vector((new_coL_l[0], new_coL_l[1], new_coL_l[2]))
						curve_pt.handle_right = Vector((new_coR_l[0], new_coR_l[1], new_coR_l[2]))
			curStr = curStr+1
			if curStr >= len(strands_points):
				break
		self.report({'INFO'}, "Done. points="+str(okPts))
		return {'FINISHED'}

class wplcurve_fastpin_ini(bpy.types.Operator):
	bl_idname = "curve.wplcurve_fastpin_ini"
	bl_label = "Fast pin selected"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll( cls, context ):
		p = context.object and context.object and context.object.type == 'CURVE'
		return p

	def execute( self, context ):
		active_obj = context.scene.objects.active
		select_and_change_mode(active_obj,'EDIT')
		curveData = active_obj.data
		curvePtsMap = {}
		okCnt = 0
		for i,spl in enumerate(curveData.splines):
			pt_locks = []
			for j, pt in enumerate(spl.points):
				isSel = 0
				if pt.select:
					isSel = 1
				pt_co = Vector((pt.co[0],pt.co[1],pt.co[2]))
				pt_locks.append([j, pt_co, isSel])
				okCnt = okCnt+1
			curvePtsMap[str(i)] = pt_locks
		WPL_G.store["wplcurve_fastpin"] = curvePtsMap
		self.report({'INFO'}, "Done. points="+str(okCnt))
		return {'FINISHED'}

class wplcurve_fastpin_apl(bpy.types.Operator):
	bl_idname = "curve.wplcurve_fastpin_apl"
	bl_label = "Enforce pins"
	bl_options = {'REGISTER', 'UNDO'}

	opt_pinType = EnumProperty(
		name="Pin type", default="INISEL",
		items=(("INISEL", "Initially selected", ""), ("NOWSEL", "Currently selected", ""))
	)

	opt_influence = FloatProperty (
		name = "Influence",
		min = 0.0, max = 1.0,
		default = 1.0
	)
	opt_smoothLoops = IntProperty (
		name = "Smoothing loops",
		min = 0, max = 100,
		default = 3
	)
	opt_smoothPow = FloatProperty (
		name = "Smoothing pow",
		min = 0.0, max = 10.0,
		default = 1.0
	)

	@classmethod
	def poll( cls, context ):
		p = context.object and context.object and context.object.type == 'CURVE'
		return p

	def execute( self, context ):
		active_obj = context.scene.objects.active
		select_and_change_mode(active_obj,'EDIT')
		curveData = active_obj.data
		if "wplcurve_fastpin" not in WPL_G.store:
			self.report({'ERROR'}, "Pin points first")
			return {'CANCELLED'}
		okCnt = 0
		curvePtsMap = WPL_G.store["wplcurve_fastpin"]
		for i,spl in enumerate(curveData.splines):
			if str(i) not in curvePtsMap:
				continue
			pt_all = curvePtsMap[str(i)]
			pt_locks = []
			if self.opt_pinType == 'INISEL':
				for lock_data in pt_all:
					if lock_data[2] > 0:
						pt_locks.append(lock_data)
			else:
				for lock_data in pt_all:
					pt_idx = lock_data[0]
					if pt_idx >= 0 and pt_idx < len(spl.points):
						pt = spl.points[pt_idx]
						if pt.select:
							pt_locks.append(lock_data)
			for lock_data in pt_locks:
				pt_idx = lock_data[0]
				pt_coIni = lock_data[1]
				if pt_idx >= 0 and pt_idx < len(spl.points):
					okCnt = okCnt+1
					pt = spl.points[pt_idx]
					pt_coCur = Vector((pt.co[0],pt.co[1],pt.co[2]))
					if self.opt_pinType == 'INISEL':
						pt_coCur2 = pt_coCur.lerp(pt_coIni, self.opt_influence)
						pt.co = (pt_coCur2[0], pt_coCur2[1], pt_coCur2[2], 1.0)
					else:
						pt_coCur2 = pt_coIni.lerp(pt_coCur, self.opt_influence)
						pt_coCur = pt_coIni
					if self.opt_smoothLoops > 0:
						for k in range(pt_idx-self.opt_smoothLoops, pt_idx+self.opt_smoothLoops+1):
							if k < 0 or k == pt_idx or k >= len(spl.points):
								continue
							smoothInfl = pow(1.0-abs(k-pt_idx)/float(self.opt_smoothLoops), self.opt_smoothPow)
							ptSm = spl.points[k]
							ptSm_co = Vector((ptSm.co[0],ptSm.co[1],ptSm.co[2]))
							ptSm_co = ptSm_co+(pt_coCur2-pt_coCur)*smoothInfl
							ptSm.co = (ptSm_co[0], ptSm_co[1], ptSm_co[2], 1.0)
		self.report({'INFO'}, "Done. points="+str(okCnt))
		return {'FINISHED'}

def get_isCurve(obj, validTypes):
	isOkCurve = False
	if obj is not None and obj.type == 'CURVE' and obj.data.dimensions == '3D':
		isOkCurve = True
		for polyline in obj.data.splines:
			#if polyline.type == 'BEZIER':
			if (validTypes is not None) and (not (polyline.type in validTypes)):
				isOkCurve = False
	return isOkCurve

######################### ######################### #########################
######################### ######################### #########################
class WPLCurveTools_Panel1(bpy.types.Panel):
	bl_label = "Curve: Fix"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_category = 'WPL'

	@classmethod
	def poll( cls, context ):
		obj = context.scene.objects.active
		return obj

	def draw_header(self, context):
		layout = self.layout
		layout.label(text="")

	def draw(self, context):
		obj = context.scene.objects.active
		if obj is None:
			return
		layout = self.layout
		col = layout.column()
		isOkCurve = get_isCurve(obj, ['POLY', 'NURBS'])
		if isOkCurve:
			row = col.row()
			row.operator("curve.wplcurve_curves_hidepnt", text="Heads").opt_actionType = 'HEADS'
			row.operator("curve.wplcurve_curves_hidepnt", text="Tails").opt_actionType = 'TAILS'
			row.operator("curve.wplcurve_curves_hidepnt", text="HIDE", icon="PARTICLE_POINT").opt_actionType = 'HIDE'
			row = col.row()
			row.operator("curve.wplcurve_merge", icon="PARTICLE_POINT", text = "Merge curves").opt_mergeMeth = 'NEAREST'
			row.operator("curve.wplcurve_merge", icon="PARTICLE_POINT", text = "Merge here").opt_mergeMeth = 'RECUT'
			col.operator("curve.wplcurve_disjoint", icon="PARTICLE_POINT")
			col.operator("curve.wplcurve_recreate", icon="PARTICLE_POINT")
			col.operator("curve.wplcurve_taper_pts", icon="PARTICLE_POINT")
			col.separator()
			col.operator("curve.wplcurve_align_tilt_coll", icon="PARTICLE_TIP")
			col.operator("curve.wplcurve_align_tilt_view", icon="PARTICLE_TIP")
			col.operator("curve.wplcurve_curve_2mesh", icon="FILE_REFRESH")
		if obj.type == 'MESH':
			addc3 = col.operator("object.wpldeform_2curve", text = 'Add Detail curve (selected)') # WPL
			addc3.opt_targetTune = 'DETAIL'
			addc3.opt_sourceMeth = 'SELC'

class WPLCurveTools_Panel2(bpy.types.Panel):
	bl_label = "Curve: Edit"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_category = 'WPL'

	@classmethod
	def poll( cls, context ):
		obj = context.scene.objects.active
		return obj

	def draw_header(self, context):
		layout = self.layout
		layout.label(text="")

	def draw(self, context):
		obj = context.scene.objects.active
		if obj is None:
			return
		layout = self.layout
		col = layout.column()
		isOkCurve = get_isCurve(obj, ['POLY', 'NURBS'])
		if isOkCurve:
			col.operator("curve.wplcurve_add_bevel", icon="OUTLINER_OB_SURFACE")
			rowSb = col.row()
			if obj.data.bevel_object is not None:
				rowSb.operator("curve.wplcurve_edit_bevel", text='Edit Bevel', icon="OUTLINER_OB_SURFACE").opt_curveType = 'BEVEL'
			if obj.data.taper_object is not None:
				rowSb.operator("curve.wplcurve_edit_bevel", text='Edit Taper', icon="OUTLINER_OB_SURFACE").opt_curveType = 'TAPER'
			# col.separator()
			# col.operator("curve.wplcurve_bubble_pnts", icon="PARTICLE_TIP", text="Bubble to surface").opt_inverseDir = False
			# col.operator("curve.wplcurve_bubble_pnts", icon="PARTICLE_TIP", text="Land on surface").opt_inverseDir = True
			col.separator()
			row = col.row()
			row.operator("curve.wplcurve_curves_hidepnt", text="Heads").opt_actionType = 'HEADS'
			row.operator("curve.wplcurve_curves_hidepnt", text="Tails").opt_actionType = 'TAILS'
			row.operator("curve.wplcurve_curves_hidepnt", text="HIDE", icon="PARTICLE_POINT").opt_actionType = 'HIDE'
			col.operator("curve.wplcurve_smooth_pts", icon="MOD_SMOOTH")
			col.operator("curve.wplcurve_smooth_til", icon="MOD_SMOOTH")
			col.operator("curve.wplcurve_taper_pts", icon="PARTICLE_POINT")
			col.operator("curve.wplcurve_evenly_pts", icon="PARTICLE_POINT")
			col.operator("curve.wplcurve_straighten_pts", icon="PARTICLE_TIP")
			col.operator("curve.wplcurve_smooth_disb", icon="PARTICLE_TIP")
			col.separator()
			#col.operator("curve.wplcurve_smooth_area", icon="MOD_SMOOTH")
			#col.operator("curve.wplcurve_smooth_conv", icon="MOD_SMOOTH")
			#col.operator("curve.wplcurve_symmetrize_pts", icon="PARTICLE_POINT")
			col.operator("curve.wplcurve_fastpin_ini", icon="PARTICLE_TIP")
			op = col.operator("curve.wplcurve_fastpin_apl", icon="PARTICLE_POINT", text = "Smooth selection")
			op.opt_pinType = 'NOWSEL'
			op = col.operator("curve.wplcurve_fastpin_apl", icon="PARTICLE_POINT", text = "Enforce pinned")
			op.opt_pinType = 'INISEL'
			col.separator()
			row2 = col.row()
			row2.operator("curve.wplcurve_curves_unifydr", text="Unify opts")
			row2.operator("curve.wplcurve_curves_mirclon", text="X-Mirror", icon="SNAP_NORMAL")
			#col.operator("curve.wplcurve_stackup_pnts", icon="PARTICLE_TIP")
		col.separator()
		isOkCurveAny = get_isCurve(obj, None)
		if isOkCurveAny:
			if isOkCurve:
				col.operator("curve.wplcurve_realigngp_pts", icon="PARTICLE_TIP")
			col.operator("curve.wplcurve_fastpin_mesh_apl", icon="PARTICLE_TIP")
		if obj.type == 'MESH':
			col.operator("mesh.wplcurve_fastpin_mesh", icon="PARTICLE_TIP")
			col.operator("mesh.wplcurve_2curves", text="Edges to curves", icon="FILE_REFRESH")

def register():
	bpy.utils.register_module(__name__)

def unregister():
	bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
	register()
