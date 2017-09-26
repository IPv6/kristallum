import bpy
import bmesh
import math
import mathutils
import copy
from mathutils import Vector, Matrix
from math import radians

from random import random, seed
from bpy_extras import view3d_utils
from bpy_extras.object_utils import world_to_camera_view

from bpy.props import (StringProperty,
						BoolProperty,
						IntProperty,
						FloatProperty,
						FloatVectorProperty,
						EnumProperty,
						PointerProperty,
						BoolVectorProperty
						)
from bpy.types import (Panel,
						Operator,
						AddonPreferences,
						PropertyGroup,
						)

bl_info = {
	"name": "WPL Grease pencil scult tools",
	"author": "IPv6",
	"version": (1, 0),
	"blender": (2, 78, 0),
	"location": "View3D > T-panel > WPL",
	"description" : "",
	"warning"	: "",
	"wiki_url"	: "",
	"tracker_url" : "",
	"category"	: ""
	}

WPLGRDEFR_push_trg = [
	('AVG_NORMLS', "Averaged Normals", "", 1),
	('LST_NORMLS', "Last vertex Normal", "", 2),
	('IND_NORMLS', "Individual Normals", "", 3),
	('CAM_DIR', "Toward Camera", "", 4),
	('SCALE_CENTER', "Scale toward edge", "", 5),
	('ROTATE_CENTER', "Bend around edge", "", 6),
]

WPLGRDEFR_vcdr_trg = [
	('REPLACE_WHITE', "Replace (B/W)", "", 1),
	('ADD_WHITE', "Add (B/W)", "", 2),
	('ADDON_R', "R-Add", "", 3),
	('ADDON_G', "G-Add", "", 3),
	('ADDON_B', "B-Add", "", 3),
	('MAXON_R', "R-Maximum", "", 3),
	('MAXON_G', "G-Maximum", "", 3),
	('MAXON_B', "B-Maximum", "", 3),
]

######################### ######################### #########################
######################### ######################### #########################
def get_object_by_name(name):
	if name in bpy.data.objects:
		return bpy.data.objects[name]
	return None

def unselect_all():
	for obj in bpy.data.objects:
		obj.select = False

def force_visible_object(obj):
	if obj:
		if obj.hide == True:
			obj.hide = False
		for n in range(len(obj.layers)):
			obj.layers[n] = False
		current_layer_index = bpy.context.scene.active_layer
		obj.layers[current_layer_index] = True

def select_and_change_mode(obj,obj_mode,hidden=False):
	unselect_all()
	if obj:
		obj.select = True
		bpy.context.scene.objects.active = obj
		force_visible_object(obj)
		try:
			m=bpy.context.mode
			if bpy.context.mode!='OBJECT':
				bpy.ops.object.mode_set(mode='OBJECT')
			bpy.context.scene.update()
			bpy.ops.object.mode_set(mode=obj_mode)
			#print("Mode switched to ", obj_mode)
		except:
			pass
		obj.hide = hidden
	return m

def get_selectedVertsIdx(active_mesh):
	bpy.ops.object.mode_set(mode='OBJECT')
	selectedVertsIdx = [e.index for e in active_mesh.vertices if e.select]
	return selectedVertsIdx

def location_to_region(worldcoords, region):
	if region is None:
		region = bpy.context.space_data.region_3d
	print("location_to_region",worldcoords, region, bpy.context.region)
	out = view3d_utils.location_3d_to_region_2d(bpy.context.region, region, worldcoords)
	return out

def region_to_location(viewcoords, depthcoords, region):
	if region is None:
		region = bpy.context.space_data.region_3d
	out = view3d_utils.region_2d_to_location_3d(bpy.context.region, region, viewcoords, depthcoords)
	return out

def gpencil_to_screenpos(context, stroke_subdiv_limit, region):
	gp = 0
	sceneGP = bpy.context.scene.grease_pencil
	objectGP = bpy.context.active_object.grease_pencil
	if(check_if_scene_gp_exists(context)):
		gp = sceneGP.layers[-1].active_frame
	elif(check_if_object_gp_exists(context)):
		gp = objectGP.layers[-1].active_frame
	if(gp == 0):
		return []
	else:
		points_3d = [point.co for point in gp.strokes[-1].points if (len(gp.strokes) > 0)]
	if stroke_subdiv_limit>0:
		# dividing strokes until no lines bigger that stroke_subdiv_limit
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
			loc = location_to_region(p3d, region)
			if loc is not None:
				points_2d_vecs.append(Vector(loc))
				points_3d_vecs.append(Vector(p3d))
	return points_2d_vecs,points_3d_vecs

def check_if_any_gp_exists(context):
	if(check_if_object_gp_exists(context)):
		return True
	elif(check_if_scene_gp_exists(context)):
		return True
	else:
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

def check_if_scene_gp_exists(context):
	sceneGP = bpy.context.scene.grease_pencil

	if(sceneGP is not None):
		if(len(sceneGP.layers)>0):
				if(len(sceneGP.layers[-1].active_frame.strokes) > 0):
					return True

	return False

def vectors_to_screenpos(context, list_of_vectors, matrix, region):
	if type(list_of_vectors) is mathutils.Vector:
		return location_to_region(matrix * list_of_vectors, region)
	else:
		return [location_to_region(matrix * vector, region) for vector in list_of_vectors]


# Generic clamp function
def clamp(a, b, v):
	if (v <= a):
		return a
	elif (v >= b):
		return b
	else:
		return v

def get_camera_pos(region_3d):
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
	#matrix = region_3d.view_matrix
	#camera_pos = camera_position(matrix)
	cam_info = region_3d.view_matrix.inverted()
	camera_pos = cam_info.translation
	return camera_pos

def get_pointRelation2dset(vertex_2d, points_2d):
	minlen = 9999.0
	meta = [-1, -1, -1];
	for i, sv in enumerate(points_2d):
		ln = (vertex_2d-sv).length
		if ln < minlen:
			minlen = ln
			meta[0] = ln
			meta[1] = i
			meta[2] = 0
			if i>0:
				# detecting side
				v1 = points_2d[i]-points_2d[i-2]
				v1.resize_3d()
				v2 = vertex_2d-points_2d[i-2]
				v2.resize_3d()
				meta[2] = math.copysign(1.0,v1.cross(v2)[2])
	return meta

def fillListHolesInterpolated(arr, zeroVal):
	init_i = 0
	ini_v = arr[0]
	for i,v in enumerate(arr):
		if i > init_i and (v != zeroVal or i == len(arr)-1):
			for j in range(init_i, i):
				arr[j] = ini_v+(j-init_i)/(i-init_i)*(v-ini_v)
			init_i = i
			ini_v = v

def fillListHolesInpaint(arr, zeroVal):
	lastNonZero = zeroVal
	for i, std in enumerate(arr):
		if std == zeroVal:
			if lastNonZero != zeroVal:
				arr[i] = lastNonZero
		else:
			if lastNonZero == zeroVal:
				lastNonZero = std
				for j in range(0,i):
					arr[j] = lastNonZero

def getActiveRegion3d():
	reg3d = bpy.context.space_data.region_3d
	if reg3d is not None:
		return reg3d
	for area in bpy.context.screen.areas:
		if area.type == 'VIEW_3D':
			return area.spaces.active.region_3d

def getLastSelectedVert(bm):
	for elem in reversed(bm.select_history):
		#if isinstance(elem, bmesh.types.BMFace):
		#	return elem.normal
		if isinstance(elem, bmesh.types.BMVert):
			return elem
	return None

def getPitValue(indexCur,indexMax,index50,Pits):
	value = 0.0
	if indexCur<index50:
		value = Pits[0]+(Pits[1]-Pits[0])*(indexCur/index50)
	else:
		value = Pits[1]+(Pits[2]-Pits[1])*((indexCur-index50)/(indexMax-index50))
	return value

def dump(obj):
	for attr in dir(obj):
		if hasattr( obj, attr ):
			print( "obj.%s = %s" % (attr, getattr(obj, attr)))
######################### ######################### #########################
######################### ######################### #########################
g_strokeResl = 20
g_zeroVec = Vector((0,0,0))

def getVertsFD(verts2dPoints, verts3dPoints, stroke2dPoints, xFacMid, xFacs, xSlops, xInpaint):
	leftMaxDistancesInStroke = [0.0 for v in stroke2dPoints]
	rightMaxDistancesInStroke = [0.0 for v in stroke2dPoints]
	nearestStrokeInPoints = [(0,1) for v in verts2dPoints]
	metasInPoints = [None for v in verts2dPoints]
	xInpaint = max(1,xInpaint)
	for i, v in enumerate(verts2dPoints):
		v_meta = get_pointRelation2dset(Vector(v), stroke2dPoints)
		metasInPoints[i] = v_meta
		v_dist = v_meta[0]
		v_sIdx = v_meta[1]
		v_side = v_meta[2]
		nearestStrokeInPoints[i] = (v_sIdx,v_side)
		radiusInStroke = leftMaxDistancesInStroke
		if v_side < 0:
			radiusInStroke = rightMaxDistancesInStroke
		for j in range(-xInpaint, +xInpaint):
			jIdx = v_sIdx+j
			if jIdx>=0 and jIdx<len(radiusInStroke):
				#falloffedDist = v_dist-(v_dist*g_outlineWndFalloff)*(j/g_outlineWnd)
				if v_dist > radiusInStroke[jIdx]:
					radiusInStroke[jIdx] = v_dist
	fillListHolesInterpolated(leftMaxDistancesInStroke, 0)
	fillListHolesInterpolated(rightMaxDistancesInStroke, 0)
	#print("leftMaxDistancesInStroke",leftMaxDistancesInStroke)
	#print("rightMaxDistancesInStroke",rightMaxDistancesInStroke)
	#minDistancePoiInStroke = [g_zeroVec for v in stroke2dPoints]
	#minDistanceDirInStroke = [g_zeroVec for v in stroke2dPoints]
	#for i, stv in enumerate(stroke2dPoints):
	#	stv_meta = get_pointRelation2dset(Vector(stv), verts2dPoints)
	#	stv_dist = stv_meta[0]
	#	stv_sIdx = stv_meta[1]
	#	minDistancePoiInStroke[i] = verts3dPoints[stv_sIdx]
	#	if i>0 and minDistancePoiInStroke[i] != minDistancePoiInStroke[i-1]:
	#		minDistanceDirInStroke[i] = minDistancePoiInStroke[i]-minDistancePoiInStroke[i-1]
	#fillListHolesInpaint(minDistanceDirInStroke, g_zeroVec)
	# shifting
	midIdx = (len(stroke2dPoints)-1)*xFacMid
	fieldDispAlpha = []
	fieldDispNearstp = []
	for i, v in enumerate(verts2dPoints):
		v_meta = metasInPoints[i]
		v_dist = v_meta[0]
		v_sIdx = v_meta[1]
		v_side = v_meta[2]
		sidemuler = 1.0
		radiusInStroke = leftMaxDistancesInStroke
		if v_side < 0:
			sidemuler = -1.0
			radiusInStroke = rightMaxDistancesInStroke
		facGlobal = (1.0-v_dist/(0.0001+radiusInStroke[v_sIdx]))
		facPosition = getPitValue(v_sIdx,len(radiusInStroke),midIdx,xFacs)
		facSlop = getPitValue(v_sIdx,len(radiusInStroke),midIdx,xSlops)
		fieldDispAlpha.append(pow(facGlobal, facSlop)*facPosition)
		#fieldDispNearstp.append((minDistancePoiInStroke[v_sIdx], sidemuler*minDistanceDirInStroke[v_sIdx]))
	return fieldDispAlpha, nearestStrokeInPoints

def set_color2vertex(mesh, loopscache, vcol_layer, vertIdx, value, acttype):
	"""Paints a single vertex where vert is the index of the vertex
	and color is a tuple with the RGB values."""
	def changeColor(li, actcolor, acttype):
		if acttype == 'REPLACE_WHITE':
			vcol_layer.data[li].color = (value,value,value)
			return
		curcolor = vcol_layer.data[li].color
		if acttype == 'ADD_WHITE':
			vcol_layer.data[li].color = (curcolor[0]+value,curcolor[1]+value,curcolor[2]+value)
			return
		if acttype == 'MAXON_R':
			vcol_layer.data[li].color = (max(curcolor[0],value),curcolor[1],curcolor[2])
			return
		if acttype == 'MAXON_G':
			vcol_layer.data[li].color = (curcolor[0],max(curcolor[1],value),curcolor[2])
			return
		if acttype == 'MAXON_B':
			vcol_layer.data[li].color = (curcolor[0],curcolor[1],max(curcolor[2],value))
			return
		if acttype == 'ADDON_R':
			vcol_layer.data[li].color = (curcolor[0]+value,curcolor[1],curcolor[2])
			return
		if acttype == 'ADDON_G':
			vcol_layer.data[li].color = (curcolor[0],curcolor[1]+value,curcolor[2])
			return
		if acttype == 'ADDON_B':
			vcol_layer.data[li].color = (curcolor[0],curcolor[1],curcolor[2]+value)
			return
	if loopscache is None:
		for poly in mesh.polygons:
			for loop_index in poly.loop_indices:
				loop_vert_index = mesh.loops[loop_index].vertex_index
				if vertIdx == loop_vert_index:
					changeColor(loop_index, value, acttype)
					break
	else:
		for loop_index in loopscache:
			loop_vert_index = mesh.loops[loop_index].vertex_index
			if vertIdx == loop_vert_index:
				changeColor(loop_index, value, acttype)
######################### ######################### #########################
######################### ######################### #########################
class WPLGRDEFR_push(bpy.types.Operator):
	bl_idname = "mesh.wplgrdf_push"
	bl_label = "Push with last stroke"
	bl_options = {'REGISTER', 'UNDO'}

	push_trg = EnumProperty(
			items = WPLGRDEFR_push_trg,
			name="Target",
			description="Target",
			default='IND_NORMLS',
	)
	influence = FloatProperty(
			name="Influence",
			description="Influence",
			min=-100.0, max=100.0,
			default=0.1,
	)
	SlopePits = FloatVectorProperty(
			name="Slope (0%->50%->100%)",
			description="Sloppiness",
			size=3,
			min=0.0, max=5.0,
			default=(1.0,1.0,1.0),
	)
	FacPits = FloatVectorProperty(
			name="Impact (0%->50%->100%)",
			description="Impact",
			size=3,
			min=-1.0, max=1.0,
			default=(1.0,1.0,1.0),
	)
	FacMid = FloatProperty(
			name="Middle point",
			description="Middle point",
			min=0.0, max=1.0,
			default=0.5,
	)
	invertFld = BoolProperty(
			name="Invert distribution",
			description="Invert distribution",
			default=False,
	)
	limitFld2NV = BoolProperty(
			name="Shape distribution by N*I",
			description="Shape distribution by N*I",
			default=False,
	)
	inpaintStrk = IntProperty(
			name="Curvature simplification",
			description="Curvature simplification",
			min=0, max=1000,
			default=10,
	)

	@classmethod
	def poll(self, context):
		# Check if we have a mesh object active and are in vertex paint mode
		p = context.object and context.object.data and (isinstance(context.scene.objects.active, bpy.types.Object) and isinstance(context.scene.objects.active.data, bpy.types.Mesh)) and check_if_any_gp_exists(context)
		return p

	def execute(self, context):
		region = getActiveRegion3d()
		active_obj = context.scene.objects.active
		select_and_change_mode(active_obj, 'EDIT')
		edit_obj = bpy.context.edit_object
		active_mesh = edit_obj.data
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		# Get all selected vertices (in their local space).
		selectedVerts = [v for v in bm.verts if v.select]
		if len(selectedVerts) < 3:
			self.report({'ERROR'}, "Not enough selected vertices found")
			return {'CANCELLED'}
		stroke2dPoints, stroke3dPoints = gpencil_to_screenpos(context, g_strokeResl, region)
		if len(stroke2dPoints) < 3:
			self.report({'ERROR'}, "Grease pencil stroke too short or not found")
			return {'CANCELLED'}

		#verts_global_3d = [Vector(obj.matrix_world * v.co) for v in selectedVerts]
		eo_mx_inv = edit_obj.matrix_world.inverted()
		eo_dir2cam = eo_mx_inv * (region.view_rotation * Vector((0.0, 0.0, 1.0)))
		eo_dir2cam = Vector(eo_dir2cam).normalized()
		#eo_mx_norm = eo_mx_inv.transposed().to_3x3()
		verts3dPoints = [v.co for v in selectedVerts]
		verts2dPoints = vectors_to_screenpos(context, verts3dPoints, edit_obj.matrix_world, region)
		vertsFieldDispersion, nearestStrokeInPoints = getVertsFD(verts2dPoints, verts3dPoints, stroke2dPoints, self.FacMid, self.FacPits, self.SlopePits, self.inpaintStrk)
		shiftDir = eo_dir2cam
		if self.push_trg == 'AVG_NORMLS':
			# points most near to begin/end of stroke to get movement vector
			normalsSumm = g_zeroVec.copy()
			normalsCount = 0
			for i, v in enumerate(verts2dPoints):
				vnrm = (selectedVerts[i].normal).normalized() #(eo_mx_norm*selectedVerts[i].normal).normalized()
				normalsSumm = normalsSumm+vnrm*vertsFieldDispersion[i]
				normalsCount = normalsCount+1
			shiftDir = normalsSumm/normalsCount
		if self.push_trg == 'LST_NORMLS':
			lastv = getLastSelectedVert(bm)
			if lastv is not None:
				shiftDir = (lastv.normal).normalized() #(eo_mx_norm*lastvn).normalized()
		for i, v in enumerate(selectedVerts):
			fac = 1.0
			if self.invertFld:
				fac = self.influence*(1.0-vertsFieldDispersion[i])
			else:
				fac = self.influence*vertsFieldDispersion[i]
			if self.limitFld2NV:
				fac = fac*eo_dir2cam.dot(v.normal)
			if fac is not None:
				if self.push_trg == 'ROTATE_CENTER':
					s3dpIdx = nearestStrokeInPoints[i][0]
					stroke3dp = stroke3dPoints[s3dpIdx]
					if s3dpIdx+1 < len(stroke3dPoints):
						stroke3dd = stroke3dPoints[s3dpIdx+1]-stroke3dp
					else:
						stroke3dd = stroke3dp-stroke3dPoints[s3dpIdx-1]
					if nearestStrokeInPoints[i][1]<0:
						stroke3dd = -1*stroke3dd
					rotmat = Matrix.Rotation(math.pi*fac,4,stroke3dd)
					v.co = rotmat*(v.co-stroke3dp)+stroke3dp
					fac = None
			if fac is not None:
				if self.push_trg == 'IND_NORMLS':
					shiftDir = v.normal
				if self.push_trg == 'SCALE_CENTER':
					s3dpIdx = nearestStrokeInPoints[i][0]
					stroke3dp = stroke3dPoints[s3dpIdx]
					shiftDir = stroke3dp - v.co
				v.co = v.co + shiftDir*fac
		# Recalculate mesh normals (so lighting looks right).
		for edge in bm.edges:
			edge.normal_update()
		# Push bmesh changes back to the actual mesh datablock.
		bmesh.update_edit_mesh(active_mesh, True)
		return {'FINISHED'}

class WPLGRDEFR_vcdr(bpy.types.Operator):
	bl_idname = "mesh.wplgrdf_vcdr"
	bl_label = "Bake across stroke into VC"
	bl_options = {'REGISTER', 'UNDO'}

	vcdr_trg = EnumProperty(
			items = WPLGRDEFR_vcdr_trg,
			name="Action",
			description="Action",
			default='REPLACE_WHITE',
	)
	influence = FloatProperty(
			name="Influence",
			description="Influence",
			min=-1.0, max=1.0,
			default=1.0,
	)
	SlopePits = FloatVectorProperty(
			name="Slope (0%->50%->100%)",
			description="Sloppiness",
			size=3,
			min=0.0, max=5.0,
			default=(1.0,1.0,1.0),
	)
	FacPits = FloatVectorProperty(
			name="Impact (0%->50%->100%)",
			description="Impact",
			size=3,
			min=-1.0, max=1.0,
			default=(1.0,1.0,1.0),
	)
	FacMid = FloatProperty(
			name="Middle point",
			description="Middle point",
			min=0.0, max=1.0,
			default=0.5,
	)
	inpaintStrk = IntProperty(
			name="Curvature simplification",
			description="Curvature simplification",
			min=0, max=1000,
			default=10,
	)

	@classmethod
	def poll(self, context):
		# Check if we have a mesh object active and are in vertex paint mode
		p = context.object and context.object.data and (isinstance(context.scene.objects.active, bpy.types.Object) and isinstance(context.scene.objects.active.data, bpy.types.Mesh)) and check_if_any_gp_exists(context)
		return p

	def execute(self, context):
		region = getActiveRegion3d()
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		select_and_change_mode(active_obj, 'EDIT')
		edit_obj = bpy.context.edit_object
		active_mesh = edit_obj.data
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		# Get all selected vertices (in their local space).
		selectedVerts = [v for v in bm.verts if v.select]
		if len(selectedVerts) < 3:
			self.report({'ERROR'}, "Not enough selected vertices found")
			return {'CANCELLED'}
		selectedVertsIdx = [v.index for v in selectedVerts]
		selectedVertsLoops = [v.link_loops for v in selectedVerts]
		selectedVertsLoopsIdx = [item.index for sublist in selectedVertsLoops for item in sublist]
		stroke2dPoints, stroke3dPoints = gpencil_to_screenpos(context, g_strokeResl, region)
		if len(stroke2dPoints) < 3:
			self.report({'ERROR'}, "Grease pencil stroke too short or not found")
			return {'CANCELLED'}

		verts3dPoints = [v.co for v in selectedVerts]
		verts2dPoints = vectors_to_screenpos(context, verts3dPoints, edit_obj.matrix_world, region)
		vertsFieldDispersion, nearestStrokeInPoints = getVertsFD(verts2dPoints, verts3dPoints, stroke2dPoints, self.FacMid, self.FacPits, self.SlopePits, self.inpaintStrk)
		select_and_change_mode(active_obj, 'OBJECT')
		active_mesh = active_obj.data
		if not active_mesh.vertex_colors:
			active_mesh.vertex_colors.new()
		color_map = active_mesh.vertex_colors.active
		for i, vIdx in enumerate(selectedVertsIdx):
			fac = self.influence*vertsFieldDispersion[i]
			set_color2vertex(active_mesh, selectedVertsLoopsIdx, color_map, vIdx, fac, self.vcdr_trg)
		select_and_change_mode(active_obj, 'VERTEX_PAINT')
		return {'FINISHED'}

class WPLGRDEFR_vcal(bpy.types.Operator):
	bl_idname = "mesh.wplgrdf_vcal"
	bl_label = "Bake along stroke into VC"
	bl_options = {'REGISTER', 'UNDO'}

	vcdr_trg = EnumProperty(
			items = WPLGRDEFR_vcdr_trg,
			name="Action",
			description="Action",
			default='REPLACE_WHITE',
	)
	influence = FloatProperty(
			name="Influence",
			description="Influence",
			min=-1.0, max=1.0,
			default=1.0,
	)
	FacMid = FloatProperty(
			name="Middle point",
			description="Middle point",
			min=0.0, max=1.0,
			default=0.5,
	)
	inpaintStrk = IntProperty(
			name="Curvature simplification",
			description="Curvature simplification",
			min=0, max=1000,
			default=10,
	)

	@classmethod
	def poll(self, context):
		# Check if we have a mesh object active and are in vertex paint mode
		p = context.object and context.object.data and (isinstance(context.scene.objects.active, bpy.types.Object) and isinstance(context.scene.objects.active.data, bpy.types.Mesh)) and check_if_any_gp_exists(context)
		return p

	def execute(self, context):
		region = getActiveRegion3d()
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		select_and_change_mode(active_obj, 'EDIT')
		edit_obj = bpy.context.edit_object
		active_mesh = edit_obj.data
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		# Get all selected vertices (in their local space).
		selectedVerts = [v for v in bm.verts if v.select]
		if len(selectedVerts) < 3:
			self.report({'ERROR'}, "Not enough selected vertices found")
			return {'CANCELLED'}
		selectedVertsIdx = [v.index for v in selectedVerts]
		selectedVertsLoops = [v.link_loops for v in selectedVerts]
		selectedVertsLoopsIdx = [item.index for sublist in selectedVertsLoops for item in sublist]
		stroke2dPoints, stroke3dPoints = gpencil_to_screenpos(context, g_strokeResl, region)
		if len(stroke2dPoints) < 3:
			self.report({'ERROR'}, "Grease pencil stroke too short or not found")
			return {'CANCELLED'}

		verts3dPoints = [v.co for v in selectedVerts]
		verts2dPoints = vectors_to_screenpos(context, verts3dPoints, edit_obj.matrix_world, region)
		vertsFieldDispersion, nearestStrokeInPoints = getVertsFD(verts2dPoints, verts3dPoints, stroke2dPoints, self.FacMid, (1.0,0.5,0.0), (0,0,0), self.inpaintStrk)
		select_and_change_mode(active_obj, 'OBJECT')
		active_mesh = active_obj.data
		if not active_mesh.vertex_colors:
			active_mesh.vertex_colors.new()
		color_map = active_mesh.vertex_colors.active
		for i, vIdx in enumerate(selectedVertsIdx):
			fac = self.influence*vertsFieldDispersion[i]
			set_color2vertex(active_mesh, selectedVertsLoopsIdx, color_map, vIdx, fac, self.vcdr_trg)
		select_and_change_mode(active_obj, 'VERTEX_PAINT')
		return {'FINISHED'}

class WPLGRDEFR_selvnear(bpy.types.Operator):
	bl_idname = "mesh.wplgrdf_selvnear"
	bl_label = "Select verts under stroke"
	bl_options = {'REGISTER', 'UNDO'}

	maxdist = FloatProperty(
			name="Distance",
			description="Distance",
			min=0.0, max=100.0,
			default=0.5,
	)
	connOuter = BoolProperty(
			name="Connect outer edges",
			description="Connect outer edges",
			default=False,
	)

	@classmethod
	def poll(self, context):
		# Check if we have a mesh object active and are in vertex paint mode
		p = context.object and context.object.data and (isinstance(context.scene.objects.active, bpy.types.Object) and isinstance(context.scene.objects.active.data, bpy.types.Mesh)) and check_if_any_gp_exists(context)
		return p

	def execute(self, context):
		region = getActiveRegion3d()
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		select_and_change_mode(active_obj, 'EDIT')
		edit_obj = bpy.context.edit_object
		active_mesh = edit_obj.data
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		stroke2dPoints, stroke3dPoints = gpencil_to_screenpos(context, g_strokeResl, region)
		if len(stroke2dPoints) < 3:
			self.report({'ERROR'}, "Grease pencil stroke too short or not found")
			return {'CANCELLED'}

		verts2connect = []
		vertsprep = [(v, Vector(edit_obj.matrix_world * v.co)) for v in bm.verts]
		for s3d in stroke3dPoints:
			distSq = self.maxdist*self.maxdist
			closestv = None
			for vpp in vertsprep:
				vg = vpp[1]
				dsq = (vg-s3d).length_squared
				if dsq < distSq:
					#dsq = distSq
					closestv = vpp[0]
					if (closestv is not None) and (closestv not in verts2connect):
						closestv.select = True
						verts2connect.append(closestv)
		if self.connOuter and len(verts2connect)>0:
			bmesh.ops.connect_verts(bm, verts=verts2connect)
		bmesh.update_edit_mesh(active_mesh, True)
		return {'FINISHED'}


class WPLGRDEFR_selfnear(bpy.types.Operator):
	bl_idname = "mesh.wplgrdf_selfnear"
	bl_label = "Select verts under stroke"
	bl_options = {'REGISTER', 'UNDO'}

	maxdist = FloatProperty(
			name="Distance",
			description="Distance",
			min=0.0, max=100.0,
			default=0.5,
	)

	@classmethod
	def poll(self, context):
		# Check if we have a mesh object active and are in vertex paint mode
		p = context.object and context.object.data and (isinstance(context.scene.objects.active, bpy.types.Object) and isinstance(context.scene.objects.active.data, bpy.types.Mesh)) and check_if_any_gp_exists(context)
		return p

	def execute(self, context):
		region = getActiveRegion3d()
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		select_and_change_mode(active_obj, 'EDIT')
		edit_obj = bpy.context.edit_object
		active_mesh = edit_obj.data
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		stroke2dPoints, stroke3dPoints = gpencil_to_screenpos(context, g_strokeResl, region)
		if len(stroke2dPoints) < 3:
			self.report({'ERROR'}, "Grease pencil stroke too short or not found")
			return {'CANCELLED'}

		distSq = self.maxdist*self.maxdist
		for f in bm.faces:
			vg = Vector(edit_obj.matrix_world * f.calc_center_median())
			for s3d in stroke3dPoints:
				if (vg-s3d).length_squared < distSq:
					f.select = True
		bmesh.update_edit_mesh(active_mesh, True)
		return {'FINISHED'}

class WPLGRDEFR_snap(bpy.types.Operator):
	bl_idname = "mesh.wplgrdf_snap"
	bl_label = "Snap to last stroke"
	bl_options = {'REGISTER', 'UNDO'}

	FacInf = FloatVectorProperty(
			name="Influence (0%->50%->100%)",
			description="Influence",
			size=3,
			min=0.0, max=1.0,
			default=(1.0,0.6,0.0),
	)
	refc_maxd = FloatProperty(
			name="Snapping range",
			description="Snapping range",
			min=0.0, max=100.0,
			default=1.0,
	)
	FacMid = FloatProperty(
			name="Middle point",
			description="Middle point",
			min=0.0, max=1.0,
			default=0.5,
	)

	@classmethod
	def poll(self, context):
		# Check if we have a mesh object active and are in vertex paint mode
		p = context.object and context.object.data and (isinstance(context.scene.objects.active, bpy.types.Object) and isinstance(context.scene.objects.active.data, bpy.types.Mesh)) and check_if_any_gp_exists(context)
		return p

	def execute(self, context):
		region = getActiveRegion3d()
		active_obj = context.scene.objects.active
		select_and_change_mode(active_obj, 'EDIT')
		edit_obj = bpy.context.edit_object
		active_mesh = edit_obj.data
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		stroke2dPoints, stroke3dPoints = gpencil_to_screenpos(context, g_strokeResl, region)
		if len(stroke2dPoints) < 3:
			self.report({'ERROR'}, "Grease pencil stroke too short or not found")
			return {'CANCELLED'}
		selectedVerts = [v for v in bm.verts if v.select]
		if len(selectedVerts) < 3:
			self.report({'ERROR'}, "Not enough selected vertices found")
			return {'CANCELLED'}
		eo_mx_inv = edit_obj.matrix_world.inverted()
		lasIdx = len(stroke3dPoints)
		midIdx = lasIdx * self.FacMid
		for v in selectedVerts:
			v_meta = get_pointRelation2dset(Vector(edit_obj.matrix_world * v.co), stroke3dPoints)
			if v_meta[0] <= self.refc_maxd:
				s3dIdx = v_meta[1]
				facPosition = getPitValue(s3dIdx,lasIdx,midIdx,self.FacInf)
				s3dLoc = eo_mx_inv*stroke3dPoints[s3dIdx]
				v.co = v.co.lerp(s3dLoc,facPosition)

		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		bm.normal_update()
		# Push bmesh changes back to the actual mesh datablock.
		bmesh.update_edit_mesh(active_mesh, True)
		return {'FINISHED'}

class WPLGRDEFR_strf(bpy.types.Operator):
	bl_idname = "mesh.wplgrdf_strf"
	bl_label = "Stripify last stroke"
	bl_options = {'REGISTER', 'UNDO'}

	HeightPits = FloatVectorProperty(
			name="Stripe Height (0%->50%->100%)",
			description="Stripe Height",
			size=3,
			min=-100.0, max=100.0,
			default=(0.01,0.01,0.01),
	)
	WidthPits = FloatVectorProperty(
			name="Tile Width (0%->50%->100%)",
			description="Tile Width",
			size=3,
			min=0.001, max=100.0,
			default=(0.01,0.01,0.01),
	)
	l_offset = FloatProperty(
			name="Tile Length",
			description="Tile Length",
			min=0.0, max=100.0,
			default=0.01,
	)
	refc_maxd = FloatProperty(
			name="Max distance to ref face",
			description="Max distance to ref face",
			min=0.0, max=100.0,
			default=1.0,
	)
	FacMid = FloatProperty(
			name="Middle point",
			description="Middle point",
			min=0.0, max=1.0,
			default=0.5,
	)

	@classmethod
	def poll(self, context):
		# Check if we have a mesh object active and are in vertex paint mode
		p = context.object and context.object.data and (isinstance(context.scene.objects.active, bpy.types.Object) and isinstance(context.scene.objects.active.data, bpy.types.Mesh)) and check_if_any_gp_exists(context)
		return p

	def execute(self, context):
		region = getActiveRegion3d()
		active_obj = context.scene.objects.active
		select_and_change_mode(active_obj, 'EDIT')
		edit_obj = bpy.context.edit_object
		active_mesh = edit_obj.data
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		stroke2dPoints, stroke3dPoints = gpencil_to_screenpos(context, g_strokeResl, region)
		if len(stroke2dPoints) < 3:
			self.report({'ERROR'}, "Grease pencil stroke too short or not found")
			return {'CANCELLED'}
		#initial_verts = [v for v in bm.verts]
		initial_faces = [f for f in bm.faces]
		eo_mx_inv = edit_obj.matrix_world.inverted()
		eo_dir2cam = eo_mx_inv * (region.view_rotation * Vector((0.0, 0.0, 1.0)))
		eo_dir2cam = Vector(eo_dir2cam).normalized()
		lasIdx = len(stroke3dPoints)
		midIdx = lasIdx * self.FacMid
		s3dIdx_cache = {}
		def getVertsForStrokePoint(s3dIdx):
			if s3dIdx in s3dIdx_cache:
				return s3dIdx_cache[s3dIdx]
			s3d = stroke3dPoints[s3dIdx]
			cen_dr = eo_dir2cam
			distSqMin = self.refc_maxd*self.refc_maxd
			for f in initial_faces:
				vg = Vector(edit_obj.matrix_world * f.calc_center_median())
				dsq = (vg-s3d).length_squared
				if dsq < distSqMin:
					distSqMin = dsq
					cen_dr = f.normal
			if s3dIdx>0:
				cen_flow = stroke3dPoints[s3dIdx]-stroke3dPoints[s3dIdx-1]
			else:
				cen_flow = stroke3dPoints[s3dIdx+1]-stroke3dPoints[s3dIdx]
			l_width = getPitValue(s3dIdx,lasIdx,midIdx,self.WidthPits)
			h_offset = getPitValue(s3dIdx,lasIdx,midIdx,self.HeightPits)
			cen_flow = cen_flow.normalized()
			cen_dr = cen_dr.normalized()
			cen_perp = cen_dr.cross(cen_flow)
			cen_p = s3d+cen_dr*h_offset
			v1_p = (cen_p+cen_perp*l_width)
			v2_p = (cen_p-cen_perp*l_width)
			v1 = bm.verts.new(eo_mx_inv*v1_p)
			v2 = bm.verts.new(eo_mx_inv*v2_p)
			s3dIdx_cache[s3dIdx] = (v1,v2)
			#print("New points",s3dIdx,stroke3dPoints[s3dIdx],cen_p,cen_dr,cen_perp)
			return s3dIdx_cache[s3dIdx]
		prev_s3di = None
		for i,s3d in enumerate(stroke3dPoints):
			if i == 0:
				prev_s3di = i
			else:
				if (s3d-stroke3dPoints[prev_s3di]).length >= self.l_offset or i == lasIdx-1:
					v_prev = getVertsForStrokePoint(prev_s3di)
					v_this = getVertsForStrokePoint(i)
					bm.faces.new([v_prev[0],v_prev[1],v_this[1],v_this[0]])
					prev_s3di = i
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		bm.normal_update()
		# Push bmesh changes back to the actual mesh datablock.
		bmesh.update_edit_mesh(active_mesh, True)
		return {'FINISHED'}

class WPLGRDEFR_clear(bpy.types.Operator):
	bl_idname = "mesh.wplgrdf_clear"
	bl_label = "Clear strokes"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(self, context):
		return check_if_any_gp_exists(context)

	def execute(self, context):
		active_object = context.scene.objects.active
		if check_if_scene_gp_exists(context):
			context.scene.grease_pencil.clear()
		if check_if_object_gp_exists(context):
			active_object.grease_pencil.clear()
		context.scene.update()
		return {'FINISHED'}

######################### ######################### #########################
######################### ######################### #########################
class WPLGreaseDefr_Panel(bpy.types.Panel):
	bl_label = "GP tools"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_category = 'WPL'

	def draw_header(self, context):
		layout = self.layout
		layout.label(text="")

	def draw(self, context):
		layout = self.layout

		col = layout.column()
		col.label("Deform")
		col.operator("mesh.wplgrdf_push", text="Push with last stroke")
		col.operator("mesh.wplgrdf_snap", text="Snap to last stroke")
		col.operator("mesh.wplgrdf_strf", text="Stripify last stroke")
		col.separator()
		col.operator("mesh.wplgrdf_vcdr", text="VC-Bake across stroke")
		col.operator("mesh.wplgrdf_vcal", text="VC-Bake along stroke")
		col.separator()
		col.label("Selection")
		col.operator("mesh.wplgrdf_selvnear", text="Select verts under stroke")
		col.operator("mesh.wplgrdf_selfnear", text="Select faces under stroke")
		col.separator()

		col.operator("mesh.wplgrdf_clear", text="Clear strokes")

def register():
	print("WPLGreaseDefr_Panel registered")
	bpy.utils.register_module(__name__)

def unregister():
	bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
	register()
