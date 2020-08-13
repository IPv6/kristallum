import math
import copy
import mathutils
import time
import random
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
	"name": "Prop Pose Tools",
	"author": "IPv6",
	"version": (1, 3, 15),
	"blender": (2, 7, 9),
	"location": "View3D > T-panel > WPL",
	"warning": "",
	"wiki_url": "",
	"tracker_url": "",
	"category": "WPL"}

kWPLRaycastEpsilon = 0.000001
kWPLRaycastEpsilonCCL = 0.0001
kWPLConvexPrecision = 10000.0
kWPLHullIncKey = "wpl_helperobjs"
kGreaseStrokeResolution = 20
kWPLHelperBonesLayer = 15
kWPLArmaStickman = "_armSkel"
kWPLArmaStickmanMat = "StickmanA"

kArmStickmanBns_MB = 'breast, neck, clavicle, pelvis, spine, upperarm_R+upperarm_twist_R, upperarm_L+upperarm_twist_L, lowerarm_R+lowerarm_twist_R, lowerarm_L+lowerarm_twist_L, thigh_R+thigh_twist_R, thigh_L+thigh_twist_L, calf_R+calf_twist_R, calf_L+calf_twist_L, foot, thumb01, thumb02, thumb03, pinky00, ring00, middle00, index00, pinky01, ring01, middle01, index01, pinky02, ring02, middle02, index02, pinky03, ring03, middle03, index03'
kArmStickmanBnsWei_MB = '*:0.3; lowerarm_L:0.6; lowerarm_R:0.6; upperarm_twist_R:0.6; upperarm_twist_L:0.6; clavicle_L:0.6; clavicle_R:0.6; spine01:0.6; spine02:0.85; spine03:0.6; neck:0.6'
kArmStickmanBns_MLOW = 'bn_breast, bn_shoulder, bn_pelvis, bn_spine05+bn_spine06, bn_spine, bn_upperarm01.R+bn_upperarm02.R, bn_upperarm01.L+bn_upperarm02.L, bn_forearm01.R+bn_forearm02.R, bn_forearm01.L+bn_forearm02.L, bn_thigh01.R+bn_thigh02.R, bn_thigh01.L+bn_thigh02.L, bn_shin01.R+bn_shin02.R, bn_shin01.L+bn_shin02.L, bn_foot+bn_toe, bn_hand, bn_thumb01, bn_thumb02, bn_thumb03, bn_pinky01, bn_ring01, bn_middle01, bn_index01, bn_pinky02, bn_ring02, bn_middle02, bn_index02, bn_pinky03, bn_ring03, bn_middle03, bn_index03'
kArmStickmanBnsWei_MLOW = '*:0.3'


kArmSelHandsBns_MB = 'hand,pinky,ring,middle,index,thumb'
kArmSelHandsBns_MLOW = 'hand,pinky,ring,middle,index,thumb'


kArmShowIKBns_MB = 'IK_,root'
kArmShowDFBns_MB = 'breast, neck, clavicle, pelvis, spine, upperarm, lowerarm, thigh, calf, foot, thumb, pinky, ring, middle, index'
kArmShowIKBns_MLOW = 'ctrl_,properties'
kArmShowDFBns_MLOW = 'bn_'


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

def getHelperObjId(context):
	if kWPLHullIncKey not in context.scene:
		context.scene[kWPLHullIncKey] = 1
	curId = context.scene[kWPLHullIncKey]
	context.scene[kWPLHullIncKey] = context.scene[kWPLHullIncKey]+1
	return curId
	
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

def view_getActiveRegion():
	reg3d = bpy.context.space_data.region_3d
	if reg3d is not None:
		return reg3d
	for area in bpy.context.screen.areas:
		if area.type == 'VIEW_3D':
			return area.spaces.active.region_3d

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

def strToTokens(sustrParts):
	if sustrParts is None or len(sustrParts) == 0:
		return []
	sustrParts = sustrParts.replace(";",",")
	sustrParts = sustrParts.replace("+",",")
	sustrParts = sustrParts.replace("|",",")
	stringTokens = [x.strip().lower() for x in sustrParts.split(",")]
	return stringTokens

def coToKey(co_vec):
	key = str(int(co_vec[0]*kWPLConvexPrecision))+"_"+str(int(co_vec[1]*kWPLConvexPrecision))+"_"+str(int(co_vec[2]*kWPLConvexPrecision))
	return key

# def view_point3dToPoint2d(worldcoords, region):
	# if region is None:
		# region = bpy.context.space_data.region_3d
	# out = view3d_utils.location_3d_to_region_2d(bpy.context.region, region, worldcoords)
	# return out

# def vectors_to_screenpos(context, list_of_vectors, matrix, region):
	# if matrix is None:
		# matrix = mathutils.Matrix.Identity(4)
	# if type(list_of_vectors) is mathutils.Vector:
		# return view_point3dToPoint2d(matrix * list_of_vectors, region)
	# else:
		# return [view_point3dToPoint2d(matrix * vector, region) for vector in list_of_vectors]
		
# def screenpos_pointsRelation(vertex_2d, points_2d):
	# minlen = 9999.0
	# meta = [-1, -1, -1];
	# for i, sv in enumerate(points_2d):
		# ln = (vertex_2d-sv).length
		# if ln < minlen:
			# minlen = ln
			# meta[0] = ln
			# meta[1] = i
			# meta[2] = 0
			# if i>0: #detecting side
				# v1 = points_2d[i]-points_2d[i-2]
				# v1.resize_3d()
				# v2 = vertex_2d-points_2d[i-2]
				# v2.resize_3d()
				# meta[2] = math.copysign(1.0,v1.cross(v2)[2])
	# return meta
	
# def vectors_ptAtDistance(points_2d, distance):
	# leng = 0
	# sv_prev = None
	# for i, sv in enumerate(points_2d):
		# if sv_prev is None:
			# sv_prev = sv
		# leng_step = (sv-sv_prev).length
		# leng = leng+leng_step
		# if leng > distance:
			# return sv
		# sv_prev = sv
	# return sv_prev

# def gpencil_to_screenpos(context, stroke_subdiv_limit, region):
	# def check_if_scene_gp_exists(context):
		# sceneGP = bpy.context.scene.grease_pencil
		# if(sceneGP is not None):
			# if(len(sceneGP.layers)>0):
				# if(len(sceneGP.layers[-1].active_frame.strokes) > 0):
					# return True
		# return False
	# def check_if_object_gp_exists(context):
		# if bpy.context.active_object is None:
			# return False
		# objectGP = bpy.context.active_object.grease_pencil
		# if(objectGP is not None):
			# if(len(objectGP.layers)>0):
					# if(len(objectGP.layers[-1].active_frame.strokes) > 0):
						# return True
		# return False
	# gp = 0
	# sceneGP = bpy.context.scene.grease_pencil
	# objectGP = bpy.context.active_object.grease_pencil
	# gpLayer = None
	# if(check_if_scene_gp_exists(context)):
		# gpLayer = sceneGP.layers[-1]
		# gp = gpLayer.active_frame
	# elif(check_if_object_gp_exists(context)):
		# gpLayer = objectGP.layers[-1]
		# gp = gpLayer.active_frame
	# if(gp == 0):
		# return [],[],gpLayer
	# else:
		# points_3d = [point.co for point in gp.strokes[-1].points if (len(gp.strokes) > 0)]
	# if stroke_subdiv_limit>0:# dividing strokes until no lines bigger that stroke_subdiv_limit
		# points_3d_up = []
		# p3d_prev = None
		# for p3d in points_3d:
			# if p3d_prev is not None:
				# p2len = (Vector(p3d) - Vector(p3d_prev)).length
				# if p2len > stroke_subdiv_limit:
					# intrmd = p2len/stroke_subdiv_limit
					# for i in range(0, intrmd):
						# mid3d = Vector(p3d_prev).lerp(Vector(p3d),i/intrmd)
						# points_3d_up.append(mid3d)
			# points_3d_up.append(p3d)
			# p3d_prev = p3d
		# points_3d = points_3d_up
	# points_3d_vecs = []
	# points_2d_vecs = []
	# for p3d in points_3d:
		# if p3d is not None:
			# loc = view_point3dToPoint2d(p3d, region)
			# if loc is not None:
				# points_2d_vecs.append(Vector(loc))
				# points_3d_vecs.append(Vector(p3d))
	# return points_2d_vecs,points_3d_vecs,gpLayer

def get_bmhistory_vertsIdx(active_bmesh):
	active_bmesh.verts.ensure_lookup_table()
	active_bmesh.verts.index_update()
	selectedVertsIdx = []
	for elem in reversed(active_bmesh.select_history):
		if isinstance(elem, bmesh.types.BMVert) and elem.select and elem.hide == 0:
			selectedVertsIdx.append(elem.index)
	return selectedVertsIdx

def prepBoneLayers(l,mx):
	all = [False]*mx
	all[l]=True
	return all

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

def get_isLocalView():
	is_local_view = sum(bpy.context.space_data.layers[:]) == 0 #if hairCurve.layers_local_view[0]:
	return is_local_view

# def get_sceneColldersBVH(forObj, allowSelf):
# 	matrix_world_inv = None
# 	if forObj is not None:
# 		matrix_world = forObj.matrix_world
# 		matrix_world_inv = matrix_world.inverted()
# 	objs2checkAll = [obj for obj in bpy.data.objects]
# 	bvh2collides = []
# 	for obj in objs2checkAll:
# 		if allowSelf == False and forObj is not None and obj.name == forObj.name:
# 			continue
# 		if obj.hide == True:
# 			continue
# 		isColl = False
# 		if "_collider" in obj.name:
# 			isColl = True
# 		for md in obj.modifiers:
# 			if md.type == 'COLLISION':
# 				isColl = True
# 				break
# 		if isColl:
# 			print("- Collider found:",obj.name)
# 			bm_collide = None
# 			if obj.type != 'MESH':
# 				sel_mesh = None
# 				try:
# 					sel_mesh = obj.to_mesh(bpy.context.scene, True, 'PREVIEW')
# 				except:
# 					pass
# 				if sel_mesh is not None:
# 					bm_collide = bmesh.new()
# 					bm_collide.from_mesh(sel_mesh)
# 					bpy.data.meshes.remove(sel_mesh)
# 			else:
# 				bm_collide = bmesh.new()
# 				bm_collide.from_object(obj, bpy.context.scene)
# 			if bm_collide is not None:
# 				hiddenFaces = []
# 				for bm2f in bm_collide.faces:
# 					if bm2f.hide and bm2f not in hiddenFaces:
# 						hiddenFaces.append(bm2f)
# 				if len(hiddenFaces)>0:
# 					bmesh.ops.delete(bm_collide,geom=hiddenFaces,context=5)
# 				bm_collide.transform(obj.matrix_world)
# 				if matrix_world_inv is not None:
# 					bm_collide.transform(matrix_world_inv)
# 				bmesh.ops.recalc_face_normals(bm_collide, faces=bm_collide.faces) #??? strange results!!!
# 				bm_collide.verts.ensure_lookup_table()
# 				bm_collide.faces.ensure_lookup_table()
# 				bm_collide.verts.index_update()
# 				bvh_collide = BVHTree.FromBMesh(bm_collide, epsilon = kWPLRaycastEpsilonCCL)
# 				bm_collide.free()
# 				bvh2collides.append(bvh_collide)
# 	return bvh2collides
	
# def get_sceneBVHIntersectionFac(bm_test, bvh2collides, maxDist, selOnly):
# 	deepns = 0
# 	bm_test.verts.ensure_lookup_table()
# 	bm_test.verts.index_update()
# 	bm_test.faces.ensure_lookup_table()
# 	bm_test.faces.index_update()
# 	bvh_test = BVHTree.FromBMesh(bm_test, epsilon = kWPLRaycastEpsilonCCL)
# 	for bvh_collider in bvh2collides:
# 		#inter_pairs = bvh_test.overlap(bvh_collider)
# 		#collisns = collisns+len(inter_pairs)
# 		# for f_idxes in inter_pairs:
# 			# test_face = bm_test.faces[f_idxes[0]]
# 			# for v in test_face.verts: # looking face verts, placed "under" second bvh
# 				# n_loc, n_normal, n_index, n_distance = bvh_collider.find_nearest(v.co, 999)
# 				# if n_loc is not None and (v.co-n_loc).dot(n_normal) < 0:
# 					# deepns = deepns+n_distance
# 		for v in bm_test.verts: # looking face verts, placed "under" second bvh
# 			if selOnly and v.select == False:
# 				continue
# 			n_loc, n_normal, n_index, n_distance = bvh_collider.find_nearest(v.co, maxDist)
# 			if n_loc is not None and (v.co-n_loc).dot(n_normal) < 0:
# 				deepns = deepns+n_distance
# 	return deepns
#############################################################################################
#############################################################################################
class wplpose_ar_toggle(bpy.types.Operator):
	bl_idname = "object.wplpose_ar_toggle"
	bl_label = "Toggle bone stuff"
	bl_options = {'REGISTER', 'UNDO'}

	opt_postAction = EnumProperty(
		name="Action", default="XRAY",
		items=(("XRAY", "X-Ray", ""), ("REST", "Rest/Pose", ""), ("AUTOIK", "AUTOIK", ""), ("SCLINH_ON", "SCLINH_ON", ""), ("SCLINH_OFF", "SCLINH_OFF", ""), ("MOVLOC_OFF", "MOVLOC_OFF", ""), ("MOVLOC_ON", "MOVLOC_ON", ""))
	)

	@classmethod
	def poll( cls, context ):
		p = (isinstance(context.scene.objects.active, bpy.types.Object))
		return p

	def execute( self, context ):
		scene = context.scene
		armatr = get_related_arma(context.scene.objects.active)
		if armatr is None:
			self.report({'ERROR'}, "Works on Armature only")
			return {'CANCELLED'}
		armatr.hide = False
		if self.opt_postAction == "AUTOIK":
			#isEnable = not armatr.data.use_auto_ik
			selbones = {}
			isEnable = True
			select_and_change_mode(armatr,'EDIT')
			if "AUTOIK" in WPL_G.store:
				selbones = WPL_G.store["AUTOIK"]
				isEnable = False
				del WPL_G.store["AUTOIK"]
			else:
				isEnable = True
				for bone in armatr.data.bones:
					if bone.select:
						bone_name = bone.name
						ebone = armatr.data.edit_bones[bone_name]
						pbone = armatr.pose.bones[bone_name]
						selbones[bone_name] = [ebone.use_connect,pbone.lock_location,pbone.lock_rotation]
				WPL_G.store["AUTOIK"] = selbones
			for bone_name in selbones:
				ebone = armatr.data.edit_bones[bone_name]
				pbone = armatr.pose.bones[bone_name]
				if isEnable:
					ebone.use_connect = True
					pbone.lock_location = (False, False, False)
					pbone.lock_rotation = (False, False, False)
				else:
					prevSetup = selbones[bone_name]
					ebone.use_connect = prevSetup[0]
					pbone.lock_location = prevSetup[1]
					pbone.lock_rotation = prevSetup[2]
			select_and_change_mode(armatr,'POSE')
			armatr.data.use_auto_ik = isEnable
			self.report({'INFO'}, "AutoIK: "+str(isEnable))
		if self.opt_postAction == "XRAY":
			armatr.show_x_ray = not armatr.show_x_ray
		if self.opt_postAction == "REST":
			if armatr.data.pose_position == 'REST':
				armatr.data.pose_position = 'POSE'
				self.report({'INFO'}, "Armature in POSE mode")
				select_and_change_mode(armatr,'POSE')
			else:
				armatr.data.pose_position = 'REST'
				self.report({'INFO'}, "Armature in REST mode")
		if self.opt_postAction == "SCLINH_ON" or self.opt_postAction == "SCLINH_OFF":
			select_and_change_mode(armatr,"POSE")
			bpy.ops.pose.visual_transform_apply()
			for bone in armatr.data.bones:
				if bone.select:
					if self.opt_postAction == "SCLINH_ON":
						bone.use_inherit_scale = True
					if self.opt_postAction == "SCLINH_OFF":
						bone.use_inherit_scale = False
		if self.opt_postAction == "MOVLOC_ON" or self.opt_postAction == "MOVLOC_OFF":
			select_and_change_mode(armatr,"POSE")
			bpy.ops.pose.visual_transform_apply()
			for bone in armatr.data.bones:
				if bone.select:
					pbone = armatr.pose.bones[bone.name]
					if self.opt_postAction == "MOVLOC_ON":
						pbone.lock_location = (True, True, True)
					if self.opt_postAction == "MOVLOC_OFF":
						pbone.lock_location = (False, False, False)
		# if self.opt_postAction == "LAYER":
		# 	fillLrs = []
		# 	for bone in armatr.data.bones:
		# 		if bone.hide:
		# 			continue
		# 		for i,l in enumerate(bone.layers):
		# 			if l and (i not in fillLrs):
		# 				fillLrs.append(i)
		# 				break
		# 	fillLrs = sorted(fillLrs)
		# 	for i,l in enumerate(armatr.data.layers):
		# 		if l:
		# 			curVisInFill = 0
		# 			if i in fillLrs:
		# 				curVisInFill = fillLrs.index(i)
		# 			print("- active layer:",i,"next layer index:",curVisInFill,fillLrs)
		# 			armatr.data.layers = prepBoneLayers(fillLrs[(curVisInFill+1)%len(fillLrs)],len(armatr.data.layers))
		# 			break
		# 	select_and_change_mode(armatr,'POSE')
		return {'FINISHED'}


class wplpose_bn_applyconstr(bpy.types.Operator):
	bl_idname = "object.wplpose_bn_applyconstr"
	bl_label = "Apply constraints"
	bl_options = {'REGISTER', 'UNDO'}

	opt_postAction = EnumProperty(
		name="Action", default="CLEAR",
		items=(("CLEAR", "Drop constraints", ""), ("DISABLE", "Disable constraints", ""), ("ENABLE", "Enable constraints", ""))
	)

	@classmethod
	def poll( cls, context ):
		p = (isinstance(context.scene.objects.active, bpy.types.Object))
		return p

	def execute( self, context ):
		scene = context.scene
		armatr = get_related_arma(context.scene.objects.active)
		if armatr is None:
			self.report({'ERROR'}, "Works on Armature only")
			return {'CANCELLED'}
		if self.opt_postAction != "ENABLE":
			select_and_change_mode(armatr,"POSE")
			bpy.ops.pose.visual_transform_apply()
		select_and_change_mode(armatr,"OBJECT")
		boneNames = armatr.pose.bones.keys()
		selbones = []
		okBn = 0
		for bone_name in boneNames:
			bone = armatr.data.bones[bone_name]
			if bone.select:
				okBn = okBn+1
				selbones.append(bone_name)
		for bone_name in selbones:
			pbone = armatr.pose.bones[bone_name]
			if len(pbone.constraints) > 0:
				constrs = []
				for constr in pbone.constraints:
					constrs.append(constr)
				for constr in constrs:
					if self.opt_postAction == "CLEAR":
						pbone.constraints.remove(constr)
					if self.opt_postAction == "DISABLE":
						constr.mute = True
					if self.opt_postAction == "ENABLE":
						constr.mute = False
		if self.opt_postAction == "CLEAR":
			# disconnect for free movements
			select_and_change_mode(armatr,"EDIT")
			for bone_name in selbones:
				ebone = armatr.data.edit_bones[bone_name]
				ebone.use_connect = False
		select_and_change_mode(armatr,"OBJECT")
		select_and_change_mode(armatr,"POSE")
		self.report({'INFO'}, "Handled "+str(okBn)+" bones")
		return {'FINISHED'}

class wplpose_ar_select(bpy.types.Operator):
	bl_idname = "object.wplpose_ar_select"
	bl_label = "Select bones by substr"
	bl_options = {'REGISTER', 'UNDO'}

	opt_bones2use = StringProperty(
		name = "Names",
		default = ""
	)
	opt_action = bpy.props.EnumProperty(
		name="Action", default="HIDEOTH",
		items=(("SEL", "Select", ""), ("HIDEOTH", "Hide others", ""), ("SELHIDE", "Select+Hide others", ""), ("DESEL", "Deselect", ""))
	)

	@classmethod
	def poll( cls, context ):
		p = (isinstance(context.scene.objects.active, bpy.types.Object))
		return p

	def execute( self, context ):
		scene = context.scene
		armatr = get_related_arma(context.scene.objects.active)
		if armatr is None:
			self.report({'ERROR'}, "Works on Armature only")
			return {'CANCELLED'}
		select_and_change_mode(armatr,'POSE')
		armatr.data.layers = [True]*len(armatr.data.layers)
		bpy.ops.pose.reveal()
		if len(self.opt_bones2use) == 0:
			if self.opt_action == 'HIDEOTH':
				bpy.ops.pose.select_all(action = 'DESELECT')
			else:
				bpy.ops.pose.select_all(action='SELECT')
			return {'FINISHED'}
		if self.opt_action == 'SELHIDE' or self.opt_action == 'HIDEOTH':
			bpy.ops.pose.select_all(action = 'DESELECT')
		bnpref = [x.strip() for x in self.opt_bones2use.split(",")]
		boneNames = armatr.pose.bones.keys()
		if "|" in self.opt_bones2use:
			selbones = []
			for boneName in boneNames:
				bone = armatr.data.bones[boneName]
				if bone.select:
					selbones.append(bone)
			for bone in selbones:
				for prt in bnpref:
					if len(prt) == 0:
						continue
					# groups
					bnpref_sub = [x for x in prt.split("|")]
					isBoneInGroup = False
					for prt_sub in bnpref_sub:
						if prt_sub.lower() in bone.name.lower():
							isBoneInGroup = True
							break
					if isBoneInGroup:
						for prt_sub in bnpref_sub:
							if prt_sub in armatr.data.bones:
								bone_sub = armatr.data.bones[prt_sub]
								pbone_sub = armatr.pose.bones[prt_sub]
								pbone_sub.rotation_mode = "QUATERNION"
								if self.opt_action == 'SEL' or self.opt_action == 'SELHIDE' or self.opt_action == 'HIDEOTH':
									bone_sub.select = True
								else:
									bone_sub.select = False
		else:
			for boneName in boneNames:
				bone = armatr.data.bones[boneName]
				pbone = armatr.pose.bones[boneName]
				pbone.rotation_mode = "QUATERNION"
				if len(bnpref) == 0:
					bone.select = True
				else:
					for prt in bnpref:
						if len(prt) == 0:
							continue
						if prt.lower() in bone.name.lower():
							if self.opt_action == 'SEL' or self.opt_action == 'SELHIDE' or self.opt_action == 'HIDEOTH':
								bone.select = True
							else:
								bone.select = False
							break
		if self.opt_action == 'SELHIDE' or self.opt_action == 'HIDEOTH':
			bpy.ops.pose.hide(unselected=True)
		if self.opt_action == 'HIDEOTH':
			bpy.ops.pose.select_all(action = 'DESELECT')
		return {'FINISHED'}

class wplpose_bn_slide(bpy.types.Operator):
	bl_idname = "object.wplpose_bn_slide"
	bl_label = "Slide bones"
	bl_options = {'REGISTER', 'UNDO'}

	opt_rotats = FloatVectorProperty(
		name = "X-Y-Z",
		size = 3,
		step = 10,
		default = (0.0, 0.0, 0.0)
	)
	opt_falloff = FloatProperty(
		name="Dist Falloff",
		min=-10.0, max=10.0,
		default=0.0,
	)

	@classmethod
	def poll( cls, context ):
		p = (isinstance(context.scene.objects.active, bpy.types.Object))
		return p

	def execute( self, context ):
		def boneChain(bn):
			chain = []
			tt = bn
			while tt.parent is not None:
				chain.append(tt.parent)
				tt = tt.parent
			return chain
		#if bpy.context.mode != 'POSE':
		#	self.report({'ERROR'}, "Works in POSE mode only")
		#	return {'CANCELLED'}
		scene = context.scene
		armatr = get_related_arma(context.scene.objects.active)
		if armatr is None:
			self.report({'ERROR'}, "Works on Armature only")
			return {'CANCELLED'}
		#context_orient = get_active_context_orient(context)
		region = view_getActiveRegion()
		eo_dir2cam_g = (region.view_rotation * Vector((0.0, 0.0, 1.0)))
		eo_dir2cam_l = armatr.matrix_world.inverted().to_3x3() * eo_dir2cam_g
		armatr.hide = False
		boneNames = armatr.pose.bones.keys()
		okBones = 0
		minChain = 999
		maxChain = 0
		minDist = 999
		maxDist = 0
		curBones = []
		for boneName in boneNames:
			bone = armatr.data.bones[boneName]
			if bone.select:
				pbone = armatr.pose.bones[boneName]
				#pbone.rotation_mode = "YXZ"
				pbone.rotation_mode = "QUATERNION"
				pbone_chain = boneChain(pbone)
				deep1 = len(pbone_chain)
				minChain = min(minChain,deep1)
				maxChain = max(maxChain,deep1)
				dir2cam = (pbone.matrix*Vector((0,0,0))-eo_dir2cam_l).length
				minDist = min(minDist,dir2cam)
				maxDist = max(maxDist,dir2cam)
				curBones.append((pbone,deep1,dir2cam))
				okBones = okBones+1
		curBones = sorted(curBones,key=lambda p:p[1])
		print("bn_pair",curBones,minDist,maxDist)
		for bn_pair in curBones:
			bn = bn_pair[0]
			infl = 1.0
			# if maxChain > minChain and self.opt_falloff>0.0:
				# fac = (bn_pair[1]-minChain)/(maxChain-minChain)
				# facStep = 1.0/(maxChain-minChain+1)
				# bn_w1 = facStep+(1.0-facStep)*fac
				# infl = pow(bn_w1,self.opt_falloff)
			if maxDist > minDist and abs(self.opt_falloff)>0.0:
				fac = (bn_pair[2]-minDist)/(maxDist-minDist)
				if self.opt_falloff<0:
					fac = 1.0-fac
				infl = pow(fac, abs(self.opt_falloff))
			eul_prev = bn.rotation_quaternion.to_euler('XYZ')
			newX = eul_prev[0]+math.radians(self.opt_rotats[0])*infl
			newY = eul_prev[1]+math.radians(self.opt_rotats[1])*infl
			newZ = eul_prev[2]+math.radians(self.opt_rotats[2])*infl
			eul_new = mathutils.Euler((newX,newY,newZ), 'XYZ')
			bn.rotation_quaternion = eul_new.to_quaternion()
		self.report({'INFO'}, "Handled "+str(okBones)+" bones")
		return {'FINISHED'}

# class wplpose_bn_applypose(bpy.types.Operator):
# 	bl_idname = "object.wplpose_bn_applypose"
# 	bl_label = "Apply pose"
# 	bl_options = {'REGISTER', 'UNDO'}

# 	opt_poseIndex = IntProperty(
# 		name="Pose index",
# 		default=0
# 	)

# 	@classmethod
# 	def poll( cls, context ):
# 		p = (isinstance(context.scene.objects.active, bpy.types.Object))
# 		return p

# 	def execute( self, context ):
# 		scene = context.scene
# 		armatr = get_related_arma(context.scene.objects.active)
# 		if armatr is None:
# 			self.report({'ERROR'}, "Works on Armature only")
# 			return {'CANCELLED'}
# 		poselib = None
# 		try:
# 			poselib = armatr.pose_library
# 		except:
# 			#col.label("Select an armature for poses")
# 			pass
# 		if armatr is None:
# 			self.report({'ERROR'}, "Poselib not found")
# 			return {'CANCELLED'}
# 		armatr.hide = False
# 		select_and_change_mode(armatr,"OBJECT")
# 		if armatr.data.pose_position == 'REST':
# 			armatr.data.pose_position = 'POSE'
# 		bpy.ops.object.wplpose_ar_select()
# 		bpy.ops.poselib.apply_pose(pose_index = self.opt_poseIndex)
# 		return {'FINISHED'}

# class wplpose_bn_greasealign(bpy.types.Operator):
# 	bl_idname = "object.wplpose_bn_greasealign"
# 	bl_label = "Align bones to grease line"
# 	bl_options = {'REGISTER', 'UNDO'}
	
# 	opt_clearStrokes = bpy.props.BoolProperty(
# 		name="Clear Strokes",
# 		default=True
# 	)

# 	@classmethod
# 	def poll( cls, context ):
# 		p = (isinstance(context.scene.objects.active, bpy.types.Object))
# 		return p

# 	def execute( self, context ):
# 		def getPBoneHealTailLocations(pbone, bonearm):
# 			headm = bonearm.convert_space(pose_bone=pbone, matrix=pbone.matrix,  from_space='POSE', to_space='WORLD')
# 			tailm = bonearm.convert_space(pose_bone=pbone, matrix=Matrix.Translation(pbone.length*pbone.y_axis)*pbone.matrix,  from_space='POSE', to_space='WORLD')
# 			headmLoc = headm.to_translation()
# 			tailmLoc = tailm.to_translation()
# 			return [headmLoc, tailmLoc]
# 		scene = context.scene
# 		activeObject = context.scene.objects.active
# 		armatr = get_related_arma(activeObject)
# 		if armatr is None:
# 			self.report({'ERROR'}, "Works on Armature only")
# 			return {'CANCELLED'}
# 		select_and_change_mode(armatr,"POSE")
# 		bpy.ops.pose.visual_transform_apply()
# 		region = view_getActiveRegion()
# 		eo_dir2cam = (region.view_rotation * Vector((0.0, 0.0, 1.0)))
# 		stroke2dPoints, stroke3dPoints, gpLayer = gpencil_to_screenpos(context, 0, region) #kGreaseStrokeResolution
# 		if len(stroke2dPoints) == 0:
# 			self.report({'ERROR'}, "Grease pencil stroke not found")
# 			return {'CANCELLED'}
# 		okBn = 0
# 		verts3dPoints_local = []
# 		boneNames = armatr.pose.bones.keys()
# 		bonesPosits = []
# 		selectPBones = []
# 		for boneName in boneNames:
# 			pbone = armatr.pose.bones[boneName]
# 			ebone = armatr.data.bones[boneName]
# 			if ebone.select:
# 				selectPBones.append(pbone)
# 				bonesPosits.append( (len(pbone.parent_recursive), pbone) )
# 		if len(selectPBones) == 0:
# 			return {'FINISHED'}
# 		bonesPosits = sorted(bonesPosits,key=lambda p:p[0])
# 		pbonesTopSelectedRoot = {}
# 		pbonesSelectedParentChain = {}
# 		for pbone in selectPBones:
# 			pbone_tmp = pbone
# 			pbonesTopSelectedRoot[pbone] = pbone_tmp
# 			if pbone not in pbonesSelectedParentChain:
# 				pbonesSelectedParentChain[pbone] = []
# 			while pbone_tmp is not None and pbone_tmp.parent is not None and pbone_tmp.parent in selectPBones:
# 				pbone_tmp = pbone_tmp.parent
# 				pbonesTopSelectedRoot[pbone] = pbone_tmp
# 				pbonesSelectedParentChain[pbone].append(pbone_tmp)
# 		bonesLengths = {}
# 		for pbone in selectPBones:
# 			bonesLengths[pbone] = -1
# 			if pbonesTopSelectedRoot[pbone] == pbone:
# 				bonesLengths[pbone] = 0
# 		updatedBones = []
# 		checkAllBones = True
# 		while checkAllBones:
# 			checkAllBones = False
# 			for pbone in selectPBones:
# 				if pbone in updatedBones:
# 					continue
# 				if bonesLengths[pbonesTopSelectedRoot[pbone]] < 0:
# 					continue
# 				verts3dPoints = getPBoneHealTailLocations(pbone, armatr)
# 				pbone_atlens = vectors_to_screenpos(context, verts3dPoints, None, region)
# 				pbone_atlen1 = pbone_atlens[0]
# 				pbone_atlen2 = pbone_atlens[1]
# 				bonesLengths[pbone] = (pbone_atlen1-pbone_atlen2).length
# 				parentlens = 0
# 				for pbone_p in pbonesSelectedParentChain[pbone]:
# 					parentlens = parentlens+bonesLengths[pbone_p]
# 				gp_atlen1 = vectors_ptAtDistance(stroke2dPoints, parentlens)
# 				gp_atlen2 = vectors_ptAtDistance(stroke2dPoints, parentlens+bonesLengths[pbone])
# 				vec1 = (gp_atlen2-gp_atlen1).normalized()
# 				vec2 = (pbone_atlen2-pbone_atlen1).normalized()
# 				gp_pb_dot = vec1.dot(vec2)
# 				angle = math.acos(max(min(gp_pb_dot,1.0),-1.0))
# 				vec1.resize_3d()
# 				vec2.resize_3d()
# 				if vec1.cross(vec2)[2] > 0:
# 					angle = -1*angle
# 				bpy.ops.pose.select_all(action = 'DESELECT')
# 				pbone.bone.select = True
# 				# rotate around view
# 				print("Rotating:", math.degrees(angle), pbone.name, pbonesTopSelectedRoot[pbone].name, parentlens, parentlens+bonesLengths[pbone]) # [pbone_atlen1, pbone_atlen2],[gp_atlen1, gp_atlen2]
# 				bpy.ops.transform.rotate(value = angle, axis=eo_dir2cam, constraint_orientation='GLOBAL')
# 				checkAllBones = True
# 				updatedBones.append(pbone)
# 		bpy.ops.pose.select_all(action = 'DESELECT')
# 		for pbone in selectPBones:
# 			pbone.bone.select = True
# 		if self.opt_clearStrokes and gpLayer is not None:
# 			gpLayer.active_frame.clear()
# 		self.report({'INFO'}, "Handled "+str(len(selectPBones))+" bones")
# 		return {'FINISHED'}

class wplpose_bn_duplic(bpy.types.Operator):
	bl_idname = "object.wplpose_bn_duplic"
	bl_label = "Duplicate bones+vgs"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll( cls, context ):
		p = (isinstance(context.scene.objects.active, bpy.types.Object))
		return p

	def execute( self, context ):
		#if bpy.context.mode != 'POSE':
		#	self.report({'ERROR'}, "Works in POSE mode only")
		#	return {'CANCELLED'}
		scene = context.scene
		activeObject = context.scene.objects.active
		armatr = get_related_arma(activeObject)
		if armatr is None:
			self.report({'ERROR'}, "Works on Armature only")
			return {'CANCELLED'}
		select_and_change_mode(armatr,"POSE")
		boneNames = armatr.pose.bones.keys()
		okBn = 0
		selBones = {}
		origBones = []
		lastSelBonename = None
		for boneName in boneNames:
			origBones.append(boneName)
			bone = armatr.data.bones[boneName]
			if bone.select:
				lastSelBonename = boneName
				selBones[boneName] = ""
		if len(selBones) == 1 and lastSelBonename is not None:
			# adding R/L if needed
			mirrorBone = None
			if "_L" in lastSelBonename:
				mirrorBone = lastSelBonename.replace("_L","_R")
			if "_R" in lastSelBonename:
				mirrorBone = lastSelBonename.replace("_R","_L")
			if mirrorBone is not None:
				selBones[mirrorBone] = ""
				bone = armatr.data.bones[mirrorBone]
				bone.select = True
		bpy.ops.pose.visual_transform_apply()
		select_and_change_mode(armatr,"EDIT")
		bpy.ops.armature.duplicate()
		select_and_change_mode(armatr,"OBJECT")
		boneNames = armatr.data.bones.keys()
		for boneName in boneNames:
			if boneName not in origBones:
				#duplicate!!!
				pbone = armatr.pose.bones[boneName]
				pbone.lock_location = (False,False,False)
				ebone = armatr.data.bones[boneName]
				ebone.layers = prepBoneLayers(kWPLHelperBonesLayer,len(armatr.data.layers))
				for selb in selBones:
					if selb in boneName:
						okBn = okBn+1
						boneName_alt = "_"+boneName
						ebone.name = boneName_alt
						selBones[selb] = boneName_alt
						pbonesel = armatr.pose.bones[selb]
						constrs = []
						for constr in pbone.constraints:
							constrs.append(constr)
						for constr in constrs:
							pbone.constraints.remove(constr)
						pbone.rotation_quaternion = pbonesel.rotation_quaternion
						pbone.scale = pbonesel.scale
						print("- bone added:", selb, boneName_alt)
						break
		armatr.data.layers = prepBoneLayers(kWPLHelperBonesLayer,len(armatr.data.layers))
		select_and_change_mode(armatr,"OBJECT")
		okObjs = 0
		# for all object on same armature - creating clones of vertex groups
		for obj in bpy.data.objects:
			if obj == activeObject or obj.type != 'MESH':
				continue
			obj_armatr = get_related_arma(obj)
			if obj_armatr != armatr:
				continue
			print ("- handling object", obj.name, selBones)
			okVrts = 0
			context.scene.objects.active = obj
			for group_name in selBones:
				if len(selBones[group_name])>0 and (group_name in obj.vertex_groups):
					#bpy.ops.object.vertex_group_copy()
					group_o = obj.vertex_groups[group_name]
					group_c = obj.vertex_groups.new(name = selBones[group_name])
					print ("-- vg: ", group_c.name)
					obj.vertex_groups.active_index = group_o.index
					#bpy.ops.object.vertex_weight_copy()
					for v in obj.data.vertices:
						for g in v.groups:
							if g.group == group_o.index:
								group_c.add([v.index], g.weight, 'ADD')
								okVrts = okVrts+1
			if okVrts>0:
				okObjs = okObjs+1
		#context.scene.objects.active = activeObject
		select_and_change_mode(armatr,"POSE")
		self.report({'INFO'}, "Handled "+str(okBn)+" bones in "+str(okObjs)+" objs")
		return {'FINISHED'}

# class wplpose_shake2fit(bpy.types.Operator):
# 	bl_idname = "object.wplpose_shake2fit"
# 	bl_label = "Shake to fit"
# 	bl_options = {'REGISTER', 'UNDO'}

# 	opt_iters = IntProperty(
# 		name	 = "Iterations",
# 		min = 2, max = 100,
# 		default	 = 10
# 	)
	
# 	opt_maxDist = FloatProperty(
# 		name	 = "Detection Distance",
# 		default	 = 0.1
# 	)
	
# 	opt_offsetDist = FloatProperty(
# 		name	 = "Distance shake",
# 		default	 = 0.01
# 	)
	
# 	opt_rotaDist = FloatVectorProperty(
# 		name = "Rotation shake",
# 		size = 3,
# 		default = (10.0, 0.0, 1.0)
# 	)

# 	@classmethod
# 	def poll(self, context):
# 		p = context.object
# 		return p

# 	def execute(self, context):
# 		active_obj = context.scene.objects.active
# 		if active_obj is None or active_obj.type != 'MESH':
# 			self.report({'ERROR'}, "Select armatured mesh first")
# 			return {'CANCELLED'}
# 		selFaces = get_selected_facesIdx(active_obj.data)
# 		if len(selFaces) == 0:
# 			self.report({'ERROR'}, "Select faces to collide first")
# 			return {'CANCELLED'}
# 		armatr = get_related_arma(active_obj)
# 		if armatr is None:
# 			self.report({'ERROR'}, "Armatured mesh required")
# 			return {'CANCELLED'}
# 		bvh2collides = get_sceneColldersBVH(active_obj,False)
# 		if len(bvh2collides) == 0:
# 			self.report({'ERROR'}, "Colliders not found: Need objects with collision modifier")
# 			return {'CANCELLED'}
# 		select_and_change_mode(armatr,"POSE")
# 		bpy.ops.pose.visual_transform_apply()
# 		select_and_change_mode(armatr,"OBJECT")
# 		boneNames = armatr.pose.bones.keys()
# 		sel_pbones = []
# 		for boneName in boneNames:
# 			bone = armatr.data.bones[boneName]
# 			if bone.select:
# 				pbone = armatr.pose.bones[boneName]
# 				pbone.rotation_mode = 'QUATERNION'
# 				sel_pbones.append([pbone, pbone.matrix.copy(), pbone.rotation_quaternion.copy()])
# 		tests = []
# 		for i in range(0,self.opt_iters):
# 			# randomly shaking bones
# 			pbn_shakes = {}
# 			for pbn in sel_pbones:
# 				pbone = pbn[0]
# 				if i == 0:
# 					# default nothing-to-do transform
# 					rnd_offset = Vector((0,0,0))
# 					rnd_rotat = mathutils.Euler((0,0,0), 'XYZ')
# 				else:
# 					rotradX = math.radians(self.opt_rotaDist[0])
# 					rotradY = math.radians(self.opt_rotaDist[1])
# 					rotradZ = math.radians(self.opt_rotaDist[2])
# 					rnd_offset = Vector((random.uniform(-1*self.opt_offsetDist,self.opt_offsetDist),random.uniform(-1*self.opt_offsetDist,self.opt_offsetDist),random.uniform(-1*self.opt_offsetDist,self.opt_offsetDist)))
# 					rnd_rotat = (random.uniform(-1*rotradX,rotradX),random.uniform(-1*rotradY,rotradY),random.uniform(-1*rotradZ,rotradZ))
# 				pbn_shakes[pbone] = [rnd_offset,rnd_rotat]
# 			for pbn in sel_pbones:
# 				pbone = pbn[0]
# 				pbone_orig_mat = pbn[1]
# 				pbone_orig_quat = pbn[2]
# 				rnd_offset = pbn_shakes[pbone][0]
# 				rnd_rotat = pbn_shakes[pbone][1]
# 				pbone.matrix = Matrix.Translation(rnd_offset)*pbone_orig_mat
# 				eul_prev = pbone_orig_quat.to_euler('XYZ') #pbone.rotation_quaternion.to_euler('XYZ')
# 				newX = eul_prev[0]+rnd_rotat[0]
# 				newY = eul_prev[1]+rnd_rotat[1]
# 				newZ = eul_prev[2]+rnd_rotat[2]
# 				eul_new = mathutils.Euler((newX,newY,newZ), 'XYZ')
# 				pbone.rotation_quaternion = eul_new.to_quaternion()
# 			context.scene.update()
# 			fin_mesh = None
# 			try:
# 				fin_mesh = active_obj.to_mesh(bpy.context.scene, True, 'PREVIEW')
# 			except:
# 				pass
# 			if fin_mesh is None:
# 				break
# 			bm_active = bmesh.new()
# 			bm_active.from_mesh(fin_mesh)
# 			bpy.data.meshes.remove(fin_mesh)
# 			# deleting hidden/non selected
# 			hiddenFaces = []
# 			for bm2f in bm_active.faces:
# 				if bm2f.hide and bm2f not in hiddenFaces:
# 					hiddenFaces.append(bm2f)
# 				if bm2f.select == False and bm2f not in hiddenFaces:
# 					hiddenFaces.append(bm2f)
# 			if len(hiddenFaces)>0:
# 				bmesh.ops.delete(bm_active,geom=hiddenFaces,context=5)
# 			collisn = get_sceneBVHIntersectionFac(bm_active, bvh2collides, self.opt_maxDist, True)
# 			print("-",i,collisn,pbn_shakes)
# 			tests.append([collisn, pbn_shakes])
# 			bm_active.free()
# 		tests = sorted(tests, key=lambda pr: pr[0], reverse=False)
# 		top_test = tests[0]
# 		pbn_shakes = top_test[1]
# 		for pbn in sel_pbones:
# 			pbone = pbn[0]
# 			pbone_orig_mat = pbn[1]
# 			pbone_orig_quat = pbn[2]
# 			rnd_offset = pbn_shakes[pbone][0]
# 			rnd_rotat = pbn_shakes[pbone][1]
# 			pbone.matrix = Matrix.Translation(rnd_offset)*pbone_orig_mat
# 			eul_prev = pbone_orig_quat.to_euler('XYZ')
# 			newX = eul_prev[0]+rnd_rotat[0]
# 			newY = eul_prev[1]+rnd_rotat[1]
# 			newZ = eul_prev[2]+rnd_rotat[2]
# 			eul_new = mathutils.Euler((newX,newY,newZ), 'XYZ')
# 			pbone.rotation_quaternion = eul_new.to_quaternion()
# 		context.scene.update()
# 		select_and_change_mode(active_obj,"OBJECT")
# 		return {'FINISHED'}

class wplpose_bn_transf(bpy.types.Operator):
	bl_idname = "object.wplpose_bn_transf"
	bl_label = "Transfer bones"
	bl_options = {'REGISTER', 'UNDO'}

	opt_armFrom = StringProperty(
		name = "Armature From (Posed)",
		default = ""
	)
	opt_armTo = StringProperty(
		name = "Armature To (Rest)",
		default = ""
	)

	def execute(self, context):
		if len(self.opt_armFrom) == 0 or len(self.opt_armTo) == 0 or self.opt_armFrom == self.opt_armTo:
			self.report({'ERROR'}, "Armatures not found")
			return {'FINISHED'}
		armatrF = context.scene.objects.get(self.opt_armFrom)
		armatrT = context.scene.objects.get(self.opt_armTo)
		if armatrF is None or armatrT is None:
			self.report({'ERROR'}, "Armatures not found")
			return {'FINISHED'}
		print("- From:", armatrF.name, armatrF.data.name)
		print("- To:", armatrT.name, armatrT.data.name)
		select_and_change_mode(armatrF,"POSE")
		bpy.ops.pose.visual_transform_apply()
		boneNamesF = armatrF.pose.bones.keys()
		tranf_pbones = []
		for boneName in boneNamesF:
			pbone = armatrF.pose.bones[boneName]
			pbone.rotation_mode = 'QUATERNION'
			 #pbone.matrix.copy(), pbone.rotation_quaternion.copy()
			headInBoneSpace = Vector( (0, 0, 0) )
			tailInBoneSpace = Vector( (0, pbone.length, 0) )
			phead = pbone.matrix*headInBoneSpace # pbone.head
			ptail = pbone.matrix*tailInBoneSpace # pbone.tail
			tranf_pbones.append([boneName, phead, ptail])
		bonesUpdated = 0
		select_and_change_mode(armatrT,"EDIT")
		for bnData in tranf_pbones:
			ebone = armatrT.data.edit_bones[bnData[0]]
			if ebone is None:
				continue
			ebone.head = bnData[1]
			ebone.tail = bnData[2]
			bonesUpdated = bonesUpdated+1
		#bpy.ops.object.mode_set(mode='OBJECT')
		select_and_change_mode(armatrT,"OBJECT")
		bpy.context.scene.update() # context.scene.update()
		self.report({'INFO'}, "Updated "+str(bonesUpdated)+" bones: "+armatrF.name+"->"+armatrT.name)
		return {'FINISHED'}


class wplbind_armskel(bpy.types.Operator):
	bl_idname = "object.wplbind_armskel"
	bl_label = "Add armature stickman"
	bl_options = {'REGISTER', 'UNDO'}

	opt_bones2use = StringProperty(
		name="Bones",
		default = ""
	)
	opt_bonesWei = StringProperty(
		name = "Weights to use",
		default = "*:0.3",
	)
	opt_material = StringProperty(
		name = "Material",
		default = kWPLArmaStickmanMat,
	)
	
	def boneGeometry(self, l1, l2, x, z, baseSize, l1Size, l2Size ):#Create the bone geometry (vertices and faces)
		start = l1 + (l2-l1) * 0.01
		end = l2 - (l2-l1) * 0.2
		x1 = x * baseSize * l1Size * 0.1
		z1 = z * baseSize * l1Size * 0.1
		x2 = x * baseSize * l2Size * 0.1
		z2 = z * baseSize * l2Size * 0.1

		verts = [
			start - x1 + z1,
			start + x1 + z1,
			start - x1 - z1,
			start + x1 - z1,
			end - x2 + z2,
			end + x2 + z2,
			end - x2 - z2,
			end + x2 - z2
		] 
		return verts

	def execute(self, context):
		active_obj = context.scene.objects.active
		if active_obj is None or active_obj.type != 'MESH':
			self.report({'ERROR'}, "Select mesh with armature")
			return {'CANCELLED'}
		if get_isLocalView():
			self.report({'INFO'}, 'Can`t work in Local view')
			return {"CANCELLED"}
		if modfGetByType(active_obj,'MIRROR'):
			self.report({'INFO'}, 'MIRROR not allowed')
			return {"CANCELLED"}
		armatr = get_related_arma(active_obj)
		if armatr is None:
			self.report({'ERROR'}, "Armature not found")
			return {'CANCELLED'}
		prevStickman = findChildObjectByName(armatr, kWPLArmaStickman)
		if prevStickman is not None:
			bpy.data.objects.remove(prevStickman, do_unlink=True)
		stickname = "zzz_" + armatr.name + kWPLArmaStickman
		print("- adding stickman",stickname)
		meshData = bpy.data.meshes.new( stickname + "_mesh" )
		meshObj = bpy.data.objects.new( stickname, meshData )
		meshObj.parent = armatr
		#meshObj.hide_render = True
		meshObj.matrix_world = active_obj.matrix_world.copy()
		context.scene.objects.link( meshObj )
		vertexGroups = {}
		bm = bmesh.new()
		bnpref = [x.strip() for x in self.opt_bones2use.split(",")]
		#Goes through each bone
		select_and_change_mode(armatr, 'EDIT')
		okIndexes = {}
		boneWScale = {}
		boneWScalePairs = strToTokens(self.opt_bonesWei)
		for tk in boneWScalePairs:
			wscaPair = tk.split(":")
			if len(wscaPair) == 2:
				boneWScale[wscaPair[0]] = wscaPair[1]
		all_deformBns = [b for b in armatr.data.edit_bones if b.use_deform]
		all_okBones = []
		for editBone in all_deformBns:
			boneName = editBone.name
			isBoneOk = False
			firstBonePref = None
			secndBonePref = None
			for pref in bnpref:
				pref_real = pref
				pref_ext = None
				if '+' in pref_real:
					pref_ext = pref_real.split("+")
					pref_real = pref_ext[0]
				if pref_real in boneName:
					isBoneOk = True
					firstBonePref = pref_real
					if pref_ext is not None:
						secndBonePref = pref_ext[1]
					break
			if isBoneOk == False:
				print("- skipping bone", boneName)
				continue
			all_okBones.append((boneName, firstBonePref, secndBonePref))
		all_okBones = sorted(all_okBones, key=lambda pr: pr[1]+pr[0], reverse=False)
		usedVerts = {}
		#print("- boneWScale", boneWScale)
		for boneSet in all_okBones:
			boneName = boneSet[0]
			secndBone = boneSet[2]
			print("- adding mesh for", boneName, secndBone)
			poseBone = armatr.pose.bones[boneName]
			#Gets edit bone informations
			editBoneHead = editBone.head
			editBoneTail = editBone.tail
			editBoneVector = editBoneTail - editBoneHead
			editBoneSize = editBoneVector.dot( editBoneVector )
			editBoneRoll = editBone.roll
			editBoneX = editBone.x_axis
			editBoneZ = editBone.z_axis
			editBoneHeadRadius = editBone.head_radius
			editBoneTailRadius = editBone.tail_radius
			#Creates the mesh data for the bone
			baseSize = math.sqrt( editBoneSize )
			newVerts = []
			weiLimit = 0.0
			if "*" in boneWScale:
				weiLimit = float(boneWScale["*"])
			if weiLimit > 0.0 and active_obj.vertex_groups.get(boneName) is not None:
				wscale1 = weiLimit
				if boneName.lower() in boneWScale:
					wscale1 = float(boneWScale[boneName.lower()])
				newVerts, _, _ = get_vertgroup_verts( active_obj, active_obj.vertex_groups.get(boneName), wscale1)
				if secndBone is not None and active_obj.vertex_groups.get(secndBone) is not None:
					wscale2 = weiLimit
					if secndBone.lower() in boneWScale:
						wscale2 = float(boneWScale[secndBone.lower()])
					newVerts2, _, _ = get_vertgroup_verts( active_obj, active_obj.vertex_groups.get(secndBone), wscale2)
					newVerts = newVerts+newVerts2
			if len(newVerts) == 0:
				newVerts = self.boneGeometry( editBoneHead, editBoneTail, editBoneX, editBoneZ, baseSize, editBoneHeadRadius, editBoneTailRadius )
			hullv = []
			vertexGroups[boneName] = []
			for v_co in newVerts:
				coKey = coToKey(v_co)
				if coKey in usedVerts:
					continue
				usedVerts[coKey] = v_co
				bm2v = bm.verts.new(v_co)
				hullv.append(bm2v)
			if len(hullv) == 0:
				continue
			bm.verts.ensure_lookup_table()
			bm.verts.index_update()
			res = bmesh.ops.convex_hull(bm, input=hullv)
			for elem in res["geom"]:
				if isinstance(elem, bmesh.types.BMVert):
					okIndexes[elem.index] = 1.0
					vertexGroups[boneName].append((elem.index,1.0))
		select_and_change_mode(meshObj, 'OBJECT')
		bm.to_mesh(meshObj.data)
		#Assigns the vertex groups
		for name, vertexGroup in vertexGroups.items():
			groupObject = meshObj.vertex_groups.new(name)
			for (index, weight) in vertexGroup:
				groupObject.add([index], weight, 'REPLACE')
		select_and_change_mode(meshObj, 'EDIT')
		bpy.ops.mesh.select_all(action='SELECT')
		bpy.ops.mesh.delete_loose()
		select_and_change_mode(meshObj, 'OBJECT')
		#Creates the armature modifier
		modifier = meshObj.modifiers.new('ArmatureMod', 'ARMATURE')
		modifier.object = armatr
		modifier.use_bone_envelopes = False
		modifier.use_vertex_groups = True
		modifier.show_in_editmode = True
		modifier.show_on_cage = True
		meshObj.modifiers.new(name = 'wpl_collider', type = 'COLLISION')
		meshObj.data.update()
		bpy.ops.object.wpluvvg_islandsmid() # WPL
		if len(self.opt_material) > 0:
			for mat in bpy.data.materials:
				if self.opt_material in mat.name:
					meshObj.data.materials.append(mat)
					print("- assigned material", mat.name)
					break
		return {'FINISHED'}

######### ############ ################# ############
class WPLPosingTools_Panel1(bpy.types.Panel):
	bl_label = "Prop: Posing"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_category = 'WPL'

	def draw(self, context):
		active_obj = context.object
		layout = self.layout
		col = layout.column()
		box2 = col.box()
		op2 = box2.operator("object.wplpose_ar_select", text="Layer: Show IK")
		op2.opt_bones2use = select_by_arm(active_obj, kArmShowIKBns_MB, kArmShowIKBns_MLOW, "")
		op2.opt_action = 'HIDEOTH'
		op3 = box2.operator("object.wplpose_ar_select", text="Layer: Show DEF")
		op3.opt_bones2use = select_by_arm(active_obj, kArmShowDFBns_MB, kArmShowDFBns_MLOW, "")
		op3.opt_action = 'HIDEOTH'
		box2.separator()
		op2 = box2.operator("object.wplpose_ar_select", text="Bones: Select hands")
		op2.opt_bones2use = select_by_arm(active_obj, kArmSelHandsBns_MB, kArmSelHandsBns_MLOW, "")
		op2.opt_action = 'SELHIDE'
		op3 = box2.operator("object.wplpose_ar_select", text="Bones: Select all")
		op3.opt_bones2use = ''
		op3.opt_action = 'SELHIDE'
		box2.separator()
		box2.operator("object.wplpose_ar_toggle", text="Toggle Rest/Pose").opt_postAction = 'REST'
		box2.separator()
		box2.operator("object.wplpose_bn_applyconstr", text="Bones: Disable constraints").opt_postAction = 'CLEAR'
		row1 = box2.row()
		row1.operator("object.wplpose_ar_toggle", text="Move lock: OFF").opt_postAction = 'MOVLOC_OFF'
		row1.operator("object.wplpose_ar_toggle", text="Move lock: ON").opt_postAction = 'MOVLOC_ON'
		row1 = box2.row()
		row1.operator("object.wplpose_ar_toggle", text="Scale inh: OFF").opt_postAction = 'SCLINH_OFF'
		row1.operator("object.wplpose_ar_toggle", text="Scale inh: ON").opt_postAction = 'SCLINH_ON'
		col = layout.column()
		col.separator()
		col.separator()
		box3 = col.box()
		box3.operator("mesh.wpluvvg_smoothall", text="Weight smoothing") # WPL
		box3.operator("object.wplpose_bn_slide").opt_rotats = (0.0,0.0,0.0)
		#box3.operator("object.wplpose_shake2fit")
		box3.operator("object.wplpose_bn_duplic")
		#box3.operator("object.wplpose_bn_greasealign")
		#box3.operator("object.wplpose_ar_toggle", text="Bones: Toggle X-Ray").opt_postAction = 'XRAY'
		col.separator()
		op1 = col.operator("object.wplbind_armskel")
		op1.opt_bones2use = select_by_arm(active_obj, kArmStickmanBns_MB, kArmStickmanBns_MLOW, "")
		op1.opt_bonesWei = select_by_arm(active_obj, kArmStickmanBnsWei_MB, kArmStickmanBnsWei_MLOW, "")
		col.operator("object.wplpose_bn_transf")
		# if armatr is not None:
		# 	poselib = None
		# 	try:
		# 		poselib = armatr.pose_library
		# 	except:
		# 		#col.label("Select an armature for poses")
		# 		pass
		# 	if poselib is not None:
		# 		col.separator()
		# 		col.label(text="Pose Library")
		# 		pose_index = 0
		# 		for p in poselib.pose_markers:
		# 			col.operator("object.wplpose_bn_applypose", text = "Apply pose: "+p.name).opt_poseIndex = pose_index
		# 			pose_index = pose_index+1

def register():
	bpy.utils.register_module(__name__)

def unregister():
	bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
	register()
