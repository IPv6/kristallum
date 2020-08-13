import math
import copy
import mathutils
import time
import random
import string
import numpy as np
import datetime

import bpy
from bpy.props import *
import bpy.types
import bmesh
from mathutils import Vector, Matrix, Euler
from mathutils.bvhtree import BVHTree


bl_info = {
	"name": "Prop Heal Tools",
	"author": "IPv6",
	"version": (1, 2, 15),
	"blender": (2, 7, 9),
	"location": "View3D > T-panel > WPL",
	"description" : "",
	"warning"	 : "",
	"wiki_url"	: "",
	"tracker_url" : "",
	"category"	: "WPL"
	}

# MatRemap rules (opt_objmatReplRules):
# btn_->matBetonVC,mtl_->matMetalVC,gls_->matGlass,wdn_->FurnWood,emb_->emiBlue,emr_->emiRed,emg_->emiGreen,sgn_->SignboardC,*->matPlasticVC
kWPLSystemReestrObjs = "Reestr"
kWPLFrameBindPostfix = "_##"
kWPLFinShapekeyPrefix = "Finalize"
kWPLSystemLayer = 19
kWPLHideMaskVGroup = "_hidegeom"
kWPLMatpushKey = "_matrix"
kWPLEdgesMainCam = "zzz_MainCamera"

class WPL_G:
	store = {}

########### ############ ########### ############ ########### ############ ########### ############
########### ############ ########### ############ ########### ############ ########### ############
def moveObjectOnLayer(c_object, layId):
	#print("moveObjectOnLayer",c_object.name,layId)
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

def copyBpyStructFields(bpyFrom, bpyTo, fieldsCopy, filedSkip):
	print("copyBpyStructFields", bpyFrom, bpyTo)
	if bpyTo is None:
		return
	if isinstance(bpyFrom,dict):
		bpyFromDirItems = bpyFrom.keys()
	else:
		bpyFromDirItems = dir(bpyFrom)
	for property in bpyFromDirItems:
		#print("copyBpyStructFields",property)
		if "__" in property:
			continue
		inPropChanged = 0
		if filedSkip is not None:
			for fld in filedSkip:
				if fld in property:
					inPropChanged = -1
					break
		if inPropChanged >= 0:
			for fld in fieldsCopy:
				if (fld in property):
					if isinstance(bpyFrom,dict):
						val = bpyFrom[property]
					else:
						val = getattr(bpyFrom,property)
					if val is None or isinstance(val, str) or isinstance(val, int) or isinstance(val, float) or isinstance(val, bool) or isinstance(val, bpy.types.Object):
						#print("- updating field",property,"to",val)
						if isinstance(bpyTo,dict):
							bpyTo[property] = val
						else:
							setattr(bpyTo, property, val)
						inPropChanged = inPropChanged+1
						break
					#else:
					#	print("- skipping by type",type(val))
		if inPropChanged <= 0:
			print("- skipping field",property)

def strToTokens(sustrParts):
	if sustrParts is None or len(sustrParts) == 0:
		return []
	sustrParts = sustrParts.replace(";",",")
	sustrParts = sustrParts.replace("+",",")
	sustrParts = sustrParts.replace("|",",")
	stringTokens = [x.strip().lower() for x in sustrParts.split(",")]
	return stringTokens

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
########### ############ ########### ############ ########### ############ ########### ############
########### ############ ########### ############ ########### ############ ########### ############

class wplheal_massrename(bpy.types.Operator):
	bl_idname = "object.wplheal_massrename"
	bl_label = "Rename object deps"
	bl_options = {'REGISTER', 'UNDO'}
	# opt_dryRun = BoolProperty(
	# 		name = "Do nothing, dry run",
	# 		default = True
	# )
	opt_objReplc = StringProperty(
			name = "Replacement rules (...->...)", # #name - replaced with original name
			default = ""
	)

	@classmethod
	def poll( cls, context ):
		return True

	def execute( self, context ):
		objs2check = [obj for obj in bpy.context.scene.objects if obj.select]
		if len(objs2check) < 1:
			self.report({'ERROR'}, "No objects selected")
			return {'FINISHED'}
		# if self.opt_dryRun:
		# 	self.report({'INFO'}, "Dry run: Operation skipped")
		# 	return {'FINISHED'}
		count = 0
		for obj in objs2check:
			if obj.library is not None:
				continue
			baseName = obj.name
			print("Checking object", baseName)
			needUpdateObjName = False
			isObjectNameUpdateNeeded = False
			# in case of chinese chars - replacing
			baseName_noZapchars = ""
			for i in range(len(baseName)):
				#if baseName[i] > u'\u4e000' and baseName[i] < u'\u9fff':
				if ord(baseName[i]) > 256:
					baseName_noZapchars = baseName_noZapchars+"_"
					needUpdateObjName = True
				else:
					baseName_noZapchars = baseName_noZapchars+baseName[i]
			baseName = baseName_noZapchars
			while "__" in baseName:
				baseName = baseName.replace("__","_")
				needUpdateObjName = True
			objUpdated = False
			if len(self.opt_objReplc) > 0:
				replPair = self.opt_objReplc.split("->")
				if len(replPair) == 2:
					reFrom = replPair[0]
					reTo = replPair[1]
					reFrom = reFrom.replace("#name", baseName)
					reTo = reTo.replace("#name", baseName)
					baseName = baseName.replace(reFrom,reTo)
					needUpdateObjName = True
			if needUpdateObjName and baseName != obj.name:
				print("Renaming object", obj.name, "to", baseName)
				obj.name = baseName
				objUpdated = True
			namePostfix = ""
			if obj.type == 'ARMATURE':
				namePostfix = "_arm"
			if obj.data is not None and obj.data.name != baseName+namePostfix:
				print("Renaming data", obj.data.name, "to", baseName+namePostfix)
				obj.data.name = baseName+namePostfix
				objUpdated = True
			if obj.type == 'CURVE':
				if obj.data.bevel_object is not None:
					curveBevelName = "shape_"+baseName
					if curveBevelName != obj.data.bevel_object.name:
						print("Renaming curve bevel", obj.data.bevel_object.name, "to", curveBevelName)
						obj.data.bevel_object.name = curveBevelName
						obj.data.bevel_object.data.name = curveBevelName
						objUpdated = True
			if objUpdated:
				count = count+1
		self.report({'INFO'}, "Updated "+str(count)+" objects")
		return {'FINISHED'}


class wplheal_remunusdats(bpy.types.Operator):
	bl_idname = "object.wplheal_remunusdats"
	bl_label = "Remove unused datas"
	bl_options = {'REGISTER', 'UNDO'}

	# opt_skipIfParts = StringProperty(
			# name = "Objects/Mats to skip",
			# default = kWPLSystemReestrObjs
	# )
	opt_remMatsExcept = StringProperty(
			name = "Mats to skip (* for all unused)",
			default = "*"
	)
	opt_remShapeksExcept = StringProperty(
			name = "Shapekeys to skip (* for all shapekeys)",
			default = "*"
	)
	opt_delEmptEmpties = BoolProperty(
			name = "Delete empties with no childrens",
			default = True
	)
	opt_delEmptyMeshes = BoolProperty(
			name = "Delete meshes with no verts",
			default = True
	)

	@classmethod
	def poll( cls, context ):
		return True

	def execute( self, context ):
		objs2check = [obj for obj in bpy.context.scene.objects if obj.select]
		if len(objs2check) < 1:
			self.report({'ERROR'}, "No objects selected")
			return {'CANCELLED'}
		matcount = 0
		shpcount = 0
		empcount = 0

		# if len(self.opt_skipIfParts)>0:
			# skipNameParts = [x.strip().lower() for x in self.opt_skipIfParts.split(",")]
		# else:
			# skipNameParts = []
		for active_obj in objs2check:
			if active_obj is None or active_obj.library is not None:
				continue
			if active_obj.name.find(kWPLSystemReestrObjs) >= 0:
				continue
			if self.opt_delEmptEmpties and active_obj.type == 'EMPTY' and len(active_obj.children) == 0:
				print("Removing empty empty: "+active_obj.name)
				bpy.data.objects.remove(active_obj, True)
				empcount = empcount+1
				continue
			if self.opt_delEmptyMeshes and active_obj.type == 'MESH' and len(active_obj.data.vertices) == 0:
				print("Removing mesh with no verts: "+active_obj.name)
				bpy.data.objects.remove(active_obj, True)
				empcount = empcount+1
				continue
			if active_obj.type == 'MESH':
				print(" - checking",active_obj.name,len(active_obj.data.vertices),len(active_obj.data.polygons))
				select_and_change_mode(active_obj,"OBJECT")
				mat_slots = {}
				matcount_perobj = 0
				shpcount_perobj = 0
				for p in active_obj.data.polygons:
					mat_slots[p.material_index] = 1
				mat_slots = mat_slots.keys()
				for i in reversed(range(len(active_obj.material_slots))):
					if i not in mat_slots:
						if matcount_perobj == 0:
							print("Cleaning unused materials from "+active_obj.name)
						matcount_perobj = matcount_perobj+1
						mat_name = active_obj.material_slots[i].name
						if len(self.opt_remMatsExcept)>0 and self.opt_remMatsExcept.find(mat_name) >= 0:
							print("- skipping",mat_name)
							continue
						if mat_name.find(kWPLSystemReestrObjs) >= 0:
							print("- skipping",mat_name)
							continue
						print("- removing",mat_name)
						active_obj.active_material_index = i
						bpy.ops.object.material_slot_remove()
						matcount = matcount+1
				if active_obj.data is not None and active_obj.data.shape_keys is not None and len(active_obj.data.shape_keys.key_blocks):
					select_and_change_mode(active_obj,"OBJECT")
					keys = active_obj.data.shape_keys.key_blocks.keys()
					active_idx = 0
					for kk in reversed(keys):
						if shpcount_perobj == 0:
							print("Cleaning shapekeys from "+active_obj.name)
						shpcount_perobj = shpcount_perobj+1
						if kWPLFrameBindPostfix in kk or kWPLFinShapekeyPrefix in kk:
							print("- skipping",kk, ", stopping shapekey checks")
							break
						if len(self.opt_remShapeksExcept)>0 and self.opt_remShapeksExcept.find(kk) >= 0:
							print("- skipping",kk, ", stopping shapekey checks")
							break
						active_idx = keys.index(kk)
						print("- removing",kk,"at",active_idx)
						shape_key = active_obj.data.shape_keys.key_blocks[kk]
						active_obj.active_shape_key_index = active_idx
						shape_key.value = 0
						bpy.ops.object.shape_key_remove(all = False)
						active_obj.data.update()
						shpcount = shpcount+1
		self.report({'INFO'}, "Removed "+str(matcount)+" mats, "+str(shpcount)+" shapekeys, "+str(empcount)+" emptobjs")
		return {'FINISHED'}

# class wplheal_replaceobjs(bpy.types.Operator):
	# bl_idname = "object.wplheal_replaceobjs"
	# bl_label = "Replace selected with active"
	# bl_options = {'REGISTER', 'UNDO'}
	# opt_copyScale = BoolProperty(
		# name = "Copy scale",
		# default = True
	# )
	# opt_copyRotation = BoolProperty(
		# name = "Copy rotation",
		# default = True
	# )
	# opt_replaceWithChilds = BoolProperty(
		# name = "Replace with childs",
		# default = True
	# )
	# opt_useLinked = BoolProperty(
		# name = "Link duplicates to active",
		# default = True
	# )
	# opt_locationAdjust = bpy.props.EnumProperty(
		# name="Adjust location", default="NONE",
		# items=(("NONE", "No adjust", ""),("TOP", "Match top", ""), ("BOTTOM", "Match bottom", ""))
	# )

	# def delete_hierarchy(self,obj):
		# subobjs = set([obj])
		# def get_child_names(obj):
			# for child in obj.children:
				# subobjs.add(child)
				# if child.children:
					# get_child_names(child)
		# get_child_names(obj)
		# for obj in subobjs:
			# bpy.data.objects.remove(obj, True)

	# @classmethod
	# def poll( cls, context ):
		# return True
	# def execute( self, context ):
		# active_obj = context.scene.objects.active
		# if active_obj is None or (active_obj.type != 'MESH'):
			# self.report({'ERROR'}, "No active object found")
			# return {'CANCELLED'}
		# active_mesh = active_obj.data
		# active_mesh_tpl_nrm = 0
		# objs2check = [obj for obj in bpy.context.scene.objects if obj.select and not obj.hide]
		# selcount = 0
		# for obj in objs2check:
			# if obj.name == active_obj.name:
				# continue
			# obj_cloned = active_obj.copy()
			# if self.opt_useLinked == False:
				# obj_cloned.data = obj_cloned.data.copy()
			# obj_cloned.location = obj.location
			# if self.opt_copyScale:
				# obj_cloned.scale = obj.scale
			# if self.opt_copyRotation:
				# obj_cloned.rotation_euler = obj.rotation_euler
				# obj_cloned.rotation_quaternion = obj.rotation_quaternion
			# obj_bbox_corners = [obj.matrix_world * Vector(corner) for corner in obj.bound_box]
			# obj_cloned_bbox_corners = [obj_cloned.matrix_world * Vector(corner) for corner in obj_cloned.bound_box]
			# if self.opt_locationAdjust == 'TOP':
				# oldtop = min(item[2] for item in obj_bbox_corners)
				# newtop = min(item[2] for item in obj_cloned_bbox_corners)
				# obj_cloned.location = obj_cloned.location+Vector((0,0,oldtop-newtop))
			# if self.opt_locationAdjust == 'BOTTOM':
				# oldtop = max(item[2] for item in obj_bbox_corners)
				# newtop = max(item[2] for item in obj_cloned_bbox_corners)
				# obj_cloned.location = obj_cloned.location+Vector((0,0,oldtop-newtop))
			# bpy.context.scene.objects.link(obj_cloned)
			# selcount = selcount+1
			# obj_cloned.name = active_obj.name+"_"+str(selcount)
			# if self.opt_replaceWithChilds:
				# self.delete_hierarchy(obj)
			# else:
				# bpy.data.objects.remove(obj, True)
		# self.report({'INFO'}, "Replaced "+str(selcount)+" objects")
		# return {'FINISHED'}

kWPLTopologyFidelity = 1000
class wplheal_samegeom(bpy.types.Operator):
	bl_idname = "object.wplheal_samegeom"
	bl_label = "Select similar"
	bl_options = {'REGISTER', 'UNDO'}
	opt_sameVertCnt = BoolProperty(
			name = "Same vert count",
			default = True
	)
	opt_sameFaceCnt = BoolProperty(
			name = "Same face count",
			default = True
	)
	opt_sameLocalNrm = BoolProperty(
			name = "Same local normal",
			default = True
	)
	opt_sameFaceArea = BoolProperty(
			name = "Same face area",
			default = True
	)
	@classmethod
	def poll( cls, context ):
		return True
	def topologyMeasureN(self, obj, mesh, fidelity):
		nrm_ttl = Vector((0,0,0))
		for p in mesh.polygons:
			nrm = p.normal #already local!
			nrm_ttl = nrm_ttl+nrm
		fdl = str(int(nrm_ttl[0]*fidelity))+"_"+str(int(nrm_ttl[1]*fidelity))+"_"+str(int(nrm_ttl[2]*fidelity))
		return fdl
	def topologyMeasureA(self, obj, mesh, fidelity):
		area_ttl = 0
		for p in mesh.polygons:
			area_ttl = area_ttl+p.area
		fdl = str(int(area_ttl*fidelity))
		return fdl
	def execute( self, context ):
		active_obj = context.scene.objects.active
		if active_obj is None or (active_obj.type != 'MESH'):
			self.report({'ERROR'}, "No active object found")
			return {'CANCELLED'}
		active_mesh = active_obj.data
		active_mesh_tpl_nrm = 0
		if self.opt_sameLocalNrm:
			active_mesh_tpl_nrm = self.topologyMeasureN(active_obj, active_mesh, kWPLTopologyFidelity)
		active_mesh_tpl_area = 0
		if self.opt_sameFaceArea:
			active_mesh_tpl_area = self.topologyMeasureA(active_obj, active_mesh, kWPLTopologyFidelity)
		objs2check = [obj for obj in bpy.context.scene.objects if not obj.hide]
		selcount = 0
		for obj in objs2check:
			if obj.type != 'MESH':
				continue
			if self.opt_sameVertCnt and len(obj.data.vertices) != len(active_mesh.vertices):
				continue
			if self.opt_sameFaceCnt and len(obj.data.polygons) != len(active_mesh.polygons):
				continue
			if self.opt_sameLocalNrm and active_mesh_tpl_nrm != self.topologyMeasureN(obj, obj.data, kWPLTopologyFidelity):
				continue
			if self.opt_sameFaceArea and active_mesh_tpl_area != self.topologyMeasureA(obj, obj.data, kWPLTopologyFidelity):
				continue
			obj.select = True
			selcount = selcount+1
		self.report({'INFO'}, "Selected "+str(selcount)+" objects")
		return {'FINISHED'}

class wplheal_selbymats(bpy.types.Operator):
	bl_idname = "object.wplheal_selbymats"
	bl_label = "Select by mats"
	bl_options = {'REGISTER', 'UNDO'}

	opt_objmatOldParts = StringProperty(
			name = "Materials (* for all)",
			default = ""
	)
	@classmethod
	def poll( cls, context ):
		return True

	def execute( self, context ):
		additional_mats = []
		if len(self.opt_objmatOldParts) > 0:
			# autosubst
			if self.opt_objmatOldParts not in bpy.data.materials:
				for mat in bpy.data.materials:
					if self.opt_objmatOldParts.lower() in mat.name.lower():
						additional_mats.append(mat.name.lower())
						#self.opt_objmatOldParts = mat.name
						#break
		if len(self.opt_objmatOldParts) == 0:
			self.report({'INFO'}, "Dry run: Target Materials")
			return {'FINISHED'}
		objs2check = [obj for obj in bpy.context.scene.objects]
		bpy.ops.object.select_all(action = 'DESELECT')
		if len(objs2check) < 1:
			self.report({'ERROR'}, "Dry run: No objects to check/replace")
			return {'FINISHED'}
		bpy.ops.view3d.layers(nr=0, extend=False, toggle=False)
		objmatOldParts = strToTokens(self.opt_objmatOldParts)
		print("- Looking for", objmatOldParts, "in",len(objs2check),"objects")
		count = 0
		objCount = 0
		active_obj = None
		lastSel_obj = None
		for active_obj in objs2check:
			if (active_obj.type == 'MESH' or active_obj.type == 'CURVE' or active_obj.type == 'FONT') and active_obj.library is None:
				#print("Checking "+active_obj.name)
				mat_slots = {}
				matsUpdated = 0
				for slt in active_obj.material_slots:
					isNeedUpdMat = False
					slt_name = slt.name.lower()
					for opn in additional_mats:
						if opn == slt_name:
							isNeedUpdMat = True
							break
					for opn in objmatOldParts:
						if opn == '*' or opn in slt_name:
							isNeedUpdMat = True
							break
					if isNeedUpdMat:
						matsUpdated = matsUpdated+1
						lastSel_obj = active_obj
						print("- Selecting "+active_obj.name)
						lastSel_obj.select = True
						objCount = objCount+1
						break
		self.report({'INFO'}, "Selected "+str(objCount)+" objects")
		if lastSel_obj is not None:
			bpy.context.scene.objects.active = lastSel_obj
			bpy.context.scene.update()
		return {'FINISHED'}

class wplheal_replacemats(bpy.types.Operator):
	bl_idname = "object.wplheal_replacemats"
	bl_label = "Replace mats"
	bl_options = {'REGISTER', 'UNDO'}

	# TBD: #name - replaced with original name
	# zzz_* -> skipped, local_* -> skipped, library mats -> skipped
	opt_objmatReplRules = StringProperty(
			name = "Replacement rules ...->..., ...->..., *->...",  
			default = ""
	)
	opt_protectMat = StringProperty(
			name = "Protected mats",
			default = "local_,zzz_,<lib>"
	)

	@classmethod
	def poll( cls, context ):
		return True

	def execute( self, context ):
		if len(self.opt_objmatReplRules) == 0:
			self.report({'INFO'}, "Dry run: Target Materials")
			return {'FINISHED'}
		objs2check = [obj for obj in bpy.context.scene.objects if obj.select]
		if len(objs2check) < 1:
			self.report({'ERROR'}, "Dry run: No objects to check/replace")
			return {'FINISHED'}
		replMap = {}
		protcRulesTokens = strToTokens(self.opt_protectMat)
		replRulesTokens = strToTokens(self.opt_objmatReplRules)
		for tk in replRulesTokens:
			replPair = tk.split("->")
			if len(replPair) == 2:
				replCount = 0
				replMat = None
				replMatName = replPair[1]
				for mat in bpy.data.materials:
					if replPair[1].lower() in mat.name.lower():
						replMat = mat
						replMatName = mat.name
						replCount = replCount+1
						print("- adding replacement", replPair, replMatName)
				if replCount != 1 or replMat is None:
					self.report({'ERROR'}, "Ambigous replacement: ["+tk+","+str(replCount)+"]")
					return {'FINISHED'}
				replMap[replPair[0]] = replMat
		count = 0
		active_obj = None
		lastSel_obj = None
		for active_obj in objs2check:
			if active_obj.type == 'MESH' and active_obj.library is None:
				#print("Checking "+active_obj.name)
				mat_slots = {}
				matsUpdated = 0
				for slt in active_obj.material_slots:
					isProtected = False
					if len(protcRulesTokens) > 0 and slt.material is not None:
						if ("<lib>" in protcRulesTokens) and (slt.material.library is not None):
							#print("-- <lib>")
							isProtected = True
						for protTk in protcRulesTokens:
							if (protTk in slt.material.name.lower()):
								#print("-- protkey", protTk)
								isProtected = True
								break
					if isProtected:
						# skipping protected
						print("- Skipping "+slt.name+ ", protected mat")
						continue
					updMat = None
					slt_name = slt.name.lower()
					for opn in replMap.keys():
						if len(opn) > 1 and opn in slt_name:
							updMat = replMap[opn]
							break
					if updMat is None and "*" in replMap:
						updMat = replMap["*"]
					if updMat is not None:
						matsUpdated = matsUpdated+1
						lastSel_obj = active_obj
						# replacing
						print("- Changing "+slt.name+ " to "+updMat.name)
						slt.material = updMat
						count = count+1
					else:
						print("- Skipping "+slt.name+ ", unknown replace")
		self.report({'INFO'}, "Updated "+str(count)+" mat slots")
		if lastSel_obj is not None:
			bpy.context.scene.objects.active = lastSel_obj
			bpy.context.scene.update()
		return {'FINISHED'}

class wplheal_resetgeom(bpy.types.Operator):
	bl_idname = "object.wplheal_resetgeom"
	bl_label = "Reset geometry"
	bl_options = {'REGISTER', 'UNDO'}
	opt_makeSingleUser = bpy.props.BoolProperty(
		name		= "Make single user",
		default	 = False
		)
	opt_applyRotation = bpy.props.BoolProperty(
		name		= "Apply rotation",
		default	 = False
		)
	opt_tris2quad = bpy.props.BoolProperty(
		name		= "Tris2Quad",
		default	 = True
		)
	opt_removeDoubles = bpy.props.FloatProperty(
		name		= "Remove doubles+cleanup",
		min = 0.0, max = 100,
		default	 = 0.0
		)

	@classmethod
	def poll( cls, context ):
		return ( context.object is not None)

	def execute( self, context ):
		sel_all = [o.name for o in bpy.context.selected_objects]
		if len(sel_all) == 0:
			self.report({'ERROR'}, "No objects selected")
			return {'FINISHED'}
		skipCount = 0
		meshDataHandled = {}
		for i, sel_obj_name in enumerate(sel_all):
			active_obj = context.scene.objects.get(sel_obj_name)
			if active_obj.type == 'ARMATURE' or active_obj.type == 'EMPTY':
				continue
			if active_obj.library is not None:
				continue
			if (i%50) == 0:
				print("Handling object", active_obj.name, i, len(sel_all))
			select_and_change_mode(active_obj,"OBJECT")
			try:
				if self.opt_makeSingleUser and active_obj.data.users > 1:
					print("Making single-user: [",active_obj.name,"/",active_obj.data.name,"]; current count=",active_obj.data.users)
					bpy.ops.object.make_single_user(object=False, obdata=True)
				if active_obj.data.users < 2:
					changeOrigin = True
					for md in active_obj.modifiers:
						if md.type == 'MIRROR':
							changeOrigin = False
					if changeOrigin:
						bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
					bpy.ops.object.transform_apply(location=False, rotation=self.opt_applyRotation, scale=True)
				else:
					skipCount = skipCount+1
					print("Skipping object (multi-user): [",active_obj.name,"/",active_obj.data.name,"]; current count=",active_obj.data.users)
				if active_obj.type == 'MESH' and (active_obj.data.name not in meshDataHandled):
					meshDataHandled[active_obj.data.name] = 1
					if self.opt_removeDoubles > 0:
						select_and_change_mode(active_obj,"EDIT")
						bpy.ops.mesh.select_all(action = 'SELECT')
						bpy.ops.mesh.remove_doubles(threshold = self.opt_removeDoubles)
						bpy.ops.mesh.select_all(action = 'SELECT')
						bpy.ops.mesh.delete_loose()
						bpy.ops.mesh.select_all(action = 'SELECT')
						bpy.ops.mesh.set_normals_from_faces()
						bpy.ops.mesh.select_all(action = 'SELECT')
						bpy.ops.mesh.normals_make_consistent()
					if self.opt_tris2quad:
						select_and_change_mode(active_obj,"EDIT")
						bpy.ops.mesh.select_all(action = 'SELECT')
						bpy.ops.mesh.tris_convert_to_quads()
					select_and_change_mode(active_obj,"OBJECT")
			except:
				pass
		self.report({'INFO'}, "Objects updated: "+str(len(sel_all))+", skips: "+str(skipCount))
		return {'FINISHED'}

# class wplheal_stepphysics(bpy.types.Operator):
	# bl_idname = "object.wplheal_stepphysics"
	# bl_label = "Step and Apply physics"
	# bl_options = {'REGISTER', 'UNDO'}

	# opt_framesToSim = IntProperty(
		# name = "Frames",
		# default = 10
	# )

	# @classmethod
	# def poll( cls, context ):
		# p = (isinstance(context.scene.objects.active, bpy.types.Object))
		# return p

	# def execute( self, context ):
		# active_obj = context.scene.objects.active
		# if active_obj is None:
			# self.report({'ERROR'}, "No active object found")
			# return {'CANCELLED'}
		# active_mesh = active_obj.data
		# cur_frame = context.scene.frame_current
		# end_frame = cur_frame+self.opt_framesToSim
		# print("Saving modifiers...")
		# phys_mod = None
		# phys_mod_params = {}
		# for md in active_obj.modifiers:
			# if md.type == 'CLOTH':
				# phys_mod = md
				# phys_mod_params["name"] = phys_mod.name
				# phys_mod_params["type"] = phys_mod.type
				# phys_mod_params["settings"] = {}
				# phys_mod_params["settings_list"] = ["damping","stiffness","friction","density","goal","gravity","mass","quality","rest_shape_key","force","shrink","time_scale","use","group","voxel_cell_size"]
				# phys_mod_params["collision_settings"] = {}
				# phys_mod_params["collision_settings_list"] = ["collision","distance","self","use","damping","friction","group","repel_force"]
				# phys_mod_params["effector_weights"] = {}
				# phys_mod_params["effector_weights_list"] = ["all","apply","boid","charge","curve_guide","drag","force","gravity","group","harmonic","lennardjones","magnetic","smokeflow","texture","turbulence","vortex","wind"]
				# copyBpyStructFields(phys_mod.settings, phys_mod_params["settings"], phys_mod_params["settings_list"],None) #["effector_weights"]
				# copyBpyStructFields(phys_mod.collision_settings, phys_mod_params["collision_settings"], phys_mod_params["collision_settings_list"], None)
				# copyBpyStructFields(phys_mod.settings.effector_weights, phys_mod_params["effector_weights"], phys_mod_params["effector_weights_list"], None)
				# break
			# if md.type == 'SOFT_BODY':
				# phys_mod = md
				# phys_mod_params["name"] = phys_mod.name
				# phys_mod_params["type"] = phys_mod.type
				# phys_mod_params["settings"] = {}
				# phys_mod_params["settings_list"] = ["aero","aerodynamics_type","ball","bend","choke","collision","damping","error_threshold","friction","fuzzy","goal","gravity","mass","plastic","pull","push","estimate","shear","speed","spring","step","use","vertex"]
				# phys_mod_params["effector_weights"] = {}
				# phys_mod_params["effector_weights_list"] = ["all","apply","boid","charge","curve_guide","drag","force","gravity","group","harmonic","lennardjones","magnetic","smokeflow","texture","turbulence","vortex","wind"]
				# copyBpyStructFields(phys_mod.settings, phys_mod_params["settings"], phys_mod_params["settings_list"], None)
				# copyBpyStructFields(phys_mod.settings.effector_weights, phys_mod_params["effector_weights"], phys_mod_params["effector_weights_list"], None)
				# break
		# if phys_mod is not None:
			# print("Baking physics... ","-frames:",(end_frame-cur_frame),"-time:",datetime.datetime.now())
			# bpy.context.scene.frame_set(cur_frame)
			# phys_mod.point_cache.frame_start = cur_frame
			# phys_mod.point_cache.frame_end = end_frame
			# bpy.ops.ptcache.bake_all(bake=True)
			# print("Baking done!... ","-time:",datetime.datetime.now())
		# print("Switching frame...")
		# bpy.context.scene.frame_set(end_frame)
		# bpy.context.scene.update()
		# if phys_mod is not None:
			# bpy.ops.object.modifier_apply(apply_as='DATA', modifier=phys_mod.name)
		# else:
			# bpy.ops.object.convert(target='MESH', keep_original=False)
		# new_mat = active_obj.matrix_world
		# print("Going back...")
		# bpy.context.scene.frame_set(cur_frame)
		# bpy.context.scene.update()
		# print("Restoring modifiers...")
		# active_obj.matrix_world = new_mat
		# if phys_mod is not None:
			# newphys_modifier = active_obj.modifiers.new(phys_mod_params["name"], phys_mod_params["type"])
			# if phys_mod_params["type"] == 'CLOTH':
				# copyBpyStructFields(phys_mod_params["settings"], newphys_modifier.settings, phys_mod_params["settings_list"], None) #["effector_weights"]
				# copyBpyStructFields(phys_mod_params["collision_settings"], newphys_modifier.collision_settings, phys_mod_params["collision_settings_list"], None)
				# copyBpyStructFields(phys_mod_params["effector_weights"], newphys_modifier.settings.effector_weights, phys_mod_params["effector_weights_list"], None)
			# if phys_mod_params["type"] == 'SOFT_BODY':
				# copyBpyStructFields(phys_mod_params["settings"], newphys_modifier.settings, phys_mod_params["settings_list"], None)
				# copyBpyStructFields(phys_mod_params["effector_weights"], newphys_modifier.settings.effector_weights, phys_mod_params["effector_weights_list"], None)
			# bpy.ops.ptcache.free_bake_all()
		# print("Done!")
		# return {'FINISHED'}


class wplheal_tweakobj(bpy.types.Operator):
	bl_idname = "object.wplheal_tweakobj"
	bl_label = "Set collider flag"
	bl_options = {'REGISTER', 'UNDO'}

	opt_actionType = bpy.props.EnumProperty(
		name="Action", default="ADD",
		items=(("ADD", "Set collider", ""), ("REM", "Clear collider", ""))
	)

	@classmethod
	def poll( cls, context ):
		p = (isinstance(context.scene.objects.active, bpy.types.Object))
		return p
	def execute( self, context ):
		sel_all = [o.name for o in bpy.context.selected_objects]
		if len(sel_all) == 0:
			self.report({'ERROR'}, "No objects selected")
			return {'CANCELLED'}
		ok = 0
		for i, sel_obj_name in enumerate(sel_all):
			sel_obj = context.scene.objects[sel_obj_name]
			prevCld = modfGetByType(sel_obj, 'COLLISION')
			if prevCld is None:
				if self.opt_actionType == 'ADD':
					sel_obj.modifiers.new(name = 'wpl_collider', type = 'COLLISION')
					ok = ok+1
			else:
				if self.opt_actionType == 'REM':
					sel_obj.modifiers.remove(prevCld)
					ok = ok+1
		self.report({'INFO'}, "Marked "+str(ok)+" objects")
		return {'FINISHED'}


class wplheal_maskout(bpy.types.Operator):
	bl_idname = "mesh.wplheal_maskout"
	bl_label = "modf: HideGeom selection"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll( cls, context ):
		return ( context.object is not None and
				context.object.type == 'MESH' and
				bpy.context.mode == 'EDIT_MESH')

	def execute( self, context ):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		oldmode = select_and_change_mode(active_obj,"OBJECT")
		selvertsAll = get_selected_vertsIdx(active_mesh)
		if len(selvertsAll) == 0:
			self.report({'ERROR'}, "No selected vertices found")
			return {'FINISHED'}
		mask_group = getornew_vertgroup(active_obj, kWPLHideMaskVGroup)
		try:
			wpl_weigToolOpts = context.scene.uvvgtoolsOpts
			wpl_weigToolOpts.wei_gropnm = kWPLHideMaskVGroup # WPL
		except Exception as e:
			pass
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
		# if active_mesh.vertex_colors.get(kWPLMeshColVC) is not None:
		# 	colVC = active_mesh.vertex_colors.get(kWPLMeshColVC)
		# 	for ipoly in range(len(active_mesh.polygons)):
		# 		for idx, lIdx in enumerate(active_mesh.polygons[ipoly].loop_indices):
		# 			ivdx = active_mesh.polygons[ipoly].vertices[idx]
		# 			if ivdx in selvertsAll:
		# 				vcol = colVC.data[lIdx].color
		# 				vcolZero = (vcol[0],vcol[1],vcol[2], 0.0) #alpha = 0
		# 				colVC.data[lIdx].color = vcolZero
		mask_modifier = active_obj.modifiers.get(kWPLHideMaskVGroup)
		if mask_modifier is None:
			mask_modifier = active_obj.modifiers.new(name = kWPLHideMaskVGroup, type = 'MASK')
			mask_modifier.vertex_group = mask_group.name
			mask_modifier.invert_vertex_group = True
			mask_modifier.threshold = 0.9
			mask_modifier.show_in_editmode = True
			mask_modifier.show_on_cage = True
			# lapl_modifier = active_obj.modifiers.new(name = kWPLHideMaskVGroup+"_edgecut", type = 'LAPLACIANSMOOTH')
			# lapl_modifier.vertex_group = mask_group.name
			# lapl_modifier.use_volume_preserve = False
			# lapl_modifier.use_normalized = False
			# lapl_modifier.lambda_factor = 1.0
			# lapl_modifier.lambda_border = 1.0
			# lapl_modifier.iterations = 10
			# lapl_modifier.show_in_editmode = True
			# lapl_modifier.show_on_cage = True
		select_and_change_mode(active_obj,oldmode)
		active_mesh.update()
		self.report({'INFO'}, "Masked "+str(ok)+" verts")
		return {'FINISHED'}


class wplheal_pushmatrix(bpy.types.Operator):
	bl_idname = "object.wplheal_pushmatrix"
	bl_label = "Obj: Reset matrix"
	bl_options = {'REGISTER', 'UNDO'}

	opt_resetScale = BoolProperty(
		name	 = "And reset scale",
		default	 = True
	)
	opt_resetRotation = BoolProperty(
		name	 = "And reset rotation",
		default	 = True
	)
	opt_reset2Global = BoolProperty(
		name	 = "And to global",
		default	 = True
	)

	@classmethod
	def poll(self, context):
		p = context.object
		return p

	def execute(self, context):
		active_obj = context.scene.objects.active
		if active_obj is None:
			return {'CANCELLED'}
		if (self.opt_resetScale or self.opt_resetRotation or self.opt_reset2Global) and (kWPLMatpushKey in active_obj):
			self.report({'ERROR'}, "Matrix already pushed, can`t overwrite")
			return {'CANCELLED'}
		aLoc, aRot, aSca = active_obj.matrix_world.decompose()
		aRotEuler = aRot.to_euler('XYZ')
		matrlist = [aLoc[0],aLoc[1],aLoc[2],aRotEuler.x,aRotEuler.y,aRotEuler.z,aSca[0],aSca[1],aSca[2]]
		WPL_G.store[kWPLMatpushKey] = matrlist
		if (self.opt_resetScale or self.opt_resetRotation or self.opt_reset2Global):
			active_obj[kWPLMatpushKey] = matrlist
		if self.opt_resetScale:
			active_obj.scale=(1,1,1)
		if self.opt_resetRotation:
			active_obj.rotation_euler=(0,0,0)
		if self.opt_reset2Global and active_obj.parent is not None:
			bpy.context.scene.update()
			local_pos = active_obj.location.copy() #active_obj.matrix_world
			active_obj.matrix_world = active_obj.parent.matrix_world.inverted()
			bpy.context.scene.update()
			active_obj.location = local_pos
			bpy.context.scene.update()
		return {'FINISHED'}

class wplheal_popmatrix(bpy.types.Operator):
	bl_idname = "object.wplheal_popmatrix"
	bl_label = "Obj: Restore matrix"
	bl_options = {'REGISTER', 'UNDO'}

	opt_restoreOrigin = BoolProperty(
		name	 = "Restore origin",
		default	 = True
	)
	opt_restoreRotation = BoolProperty(
		name	 = "Restore rotation",
		default	 = True
	)
	opt_restoreScale = BoolProperty(
		name	 = "Restore scale",
		default	 = True
	)

	@classmethod
	def poll(self, context):
		p = context.object
		return p

	def execute(self, context):
		active_obj = context.scene.objects.active
		if active_obj is None:
			return {'CANCELLED'}
		matrlist = None
		if kWPLMatpushKey in active_obj:
			matrlist = active_obj[kWPLMatpushKey]
		elif kWPLMatpushKey in WPL_G.store:
			matrlist = WPL_G.store[kWPLMatpushKey]
		if matrlist is None:
			self.report({'ERROR'}, "No pushed matrix found")
			return {'CANCELLED'}
		aLoc, aRot, aSca = active_obj.matrix_world.decompose()
		aRot = aRot.to_euler('XYZ')

		#print("matrlist", matrlist[0], matrlist[1], matrlist[2], matrlist[3], matrlist[4], matrlist[5], matrlist[6], matrlist[7], matrlist[8])
		if self.opt_restoreOrigin:
			aLoc = Vector((float(matrlist[0]),float(matrlist[1]),float(matrlist[2])))
		if self.opt_restoreRotation:
			aRot = Euler((float(matrlist[3]),float(matrlist[4]),float(matrlist[5])), 'XYZ').to_quaternion()
		if self.opt_restoreScale:
			aSca = Vector((float(matrlist[6]),float(matrlist[7]),float(matrlist[8])))
		aLocM = mathutils.Matrix.Translation(aLoc)
		aRotM = aRot.to_matrix().to_4x4()
		aScaM = Matrix().Scale(aSca[0], 4, Vector((1,0,0)))
		aScaM *= Matrix().Scale(aSca[1], 4, Vector((0,1,0)))
		aScaM *= Matrix().Scale(aSca[2], 4, Vector((0,0,1)))
		active_obj.matrix_world = aLocM * aRotM * aScaM
		if kWPLMatpushKey in active_obj:
			del active_obj[kWPLMatpushKey]
		return {'FINISHED'}


class wplheal_wrapempty(bpy.types.Operator):
	bl_idname = "object.wplheal_wrapempty"
	bl_label = "Wrap in Empty"
	bl_options = {'REGISTER', 'UNDO'}

	opt_use3Dcursor = bpy.props.BoolProperty(
		name		= "Use current 3D cursor position",
		default	 = False
		)
	opt_putOnSameLevel = bpy.props.BoolProperty(
		name		= "Use same parent",
		default	 = True
		)
	
	@classmethod
	def poll( cls, context ):
		return True

	def execute( self, context ):
		objs2check = [obj for obj in bpy.context.scene.objects if obj.select]
		if len(objs2check) < 1:
			self.report({'ERROR'}, "No objects selected")
			return {'CANCELLED'}
		firstp = objs2check[0].parent
		count = 0
		empty = bpy.data.objects.new("wrapperEmpty", None)
		empty.empty_draw_size = 0.45
		empty.empty_draw_type = 'PLAIN_AXES'
		if self.opt_use3Dcursor:
			empty.location = get_active_context_cursor(context)
		else:
			#empty.location = Vector((0,0,0))
			loc = Vector((0,0,0))
			for obj in objs2check:
				loc = loc+obj.location
				print("- adding obj", obj.location)
			empty.location = loc/len(objs2check)
			print("- warp loc", loc/len(objs2check))
		context.scene.objects.link(empty)
		context.scene.update()
		if self.opt_putOnSameLevel and objs2check[0].parent is not None:
			locIni = empty.location
			#empty.location = firstp.matrix_world.inverted()*empty.location
			empty.parent = firstp
			empty.location = locIni
		moveObjectOnLayer(empty,kWPLSystemLayer)
		bpy.context.scene.objects.active = empty
		bpy.ops.object.parent_set(type='OBJECT', xmirror=False, keep_transform=True)
		for obj in objs2check:
			count = count+1
			if obj.type == 'ARMATURE':
				obj.parent = empty
		self.report({'INFO'}, "Wrapped "+str(count)+" objects")
		return {'FINISHED'}


class wplheal_objo2cursr(bpy.types.Operator):
	bl_idname = "object.wplheal_objo2cursr"
	bl_label = "Snap object orientation to active"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(self, context):
		return ( context.object is not None)

	def execute(self, context):
		active_obj = context.scene.objects.active
		if active_obj is None:
			self.report({'ERROR'}, "No objects selected")
			return {'CANCELLED'}
		bpy.ops.view3d.snap_cursor_to_active()
		bpy.ops.transform.create_orientation(name='_TEMP', use=True, overwrite=True)
		orient_rot = get_active_context_orient(context)
		if orient_rot is None:
			self.report({'ERROR'}, "No proper context/Invalid orientation")
			return {'FINISHED'}
		select_and_change_mode(active_obj, 'OBJECT') # to exit from possible edit
		for selected in context.selected_objects:
			if selected.type != 'MESH':
				continue
			bpy.context.scene.objects.active = selected
			matrix_world_old = selected.matrix_world
			aLoc, aRot, aSca = selected.matrix_world.decompose()
			aRotEuler = aRot.to_euler('XYZ')
			aLocM = mathutils.Matrix.Translation(aLoc)
			aRotM = orient_rot.to_quaternion().to_matrix().to_4x4()
			aScaM = Matrix().Scale(aSca[0], 4, Vector((1,0,0)))
			aScaM *= Matrix().Scale(aSca[1], 4, Vector((0,1,0)))
			aScaM *= Matrix().Scale(aSca[2], 4, Vector((0,0,1)))
			matrix_world_new = aLocM * aRotM * aScaM
			select_and_change_mode(active_obj,'EDIT')
			bm = bmesh.from_edit_mesh(active_obj.data)
			bmesh.ops.transform(bm, matrix= matrix_world_new.inverted()*matrix_world_old, verts=bm.verts) #, space=matrix_world_old )
			bm.normal_update()
			bmesh.update_edit_mesh(active_obj.data, True)
			select_and_change_mode(active_obj,'OBJECT')
			active_obj.matrix_world = matrix_world_new
		bpy.context.space_data.transform_orientation = 'LOCAL'
		bpy.context.space_data.pivot_point = 'MEDIAN_POINT'
		bpy.context.scene.objects.active = active_obj
		self.report({'INFO'}, "Done")
		return {'FINISHED'}

class wplheal_orig2cursr(bpy.types.Operator):
	bl_idname = "object.wplheal_orig2cursr"
	bl_label = "Snap origins to active"
	bl_options = {'REGISTER', 'UNDO'}

	opt_use3Dcursor = bpy.props.BoolProperty(
		name		= "Use current 3D cursor position",
		default	 = False
		)

	@classmethod
	def poll(self, context):
		return ( context.object is not None)

	def execute(self, context):
		active_obj = context.scene.objects.active
		if active_obj is None:
			self.report({'ERROR'}, "No objects selected")
			return {'CANCELLED'}
		if self.opt_use3Dcursor == False:
			if bpy.context.mode == 'OBJECT':
				# snapping to geomcenter of object
				local_bbox_center = 0.125 * sum((Vector(b) for b in active_obj.bound_box), Vector())
				bpy.context.scene.cursor_location = active_obj.matrix_world * local_bbox_center
			else:
				bpy.ops.view3d.snap_cursor_to_active()
		select_and_change_mode(active_obj, 'OBJECT') # to exit from possible edit
		for selected in context.selected_objects:
			bpy.context.scene.objects.active = selected
			bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
		bpy.context.scene.objects.active = active_obj
		self.report({'INFO'}, "Done")
		return {'FINISHED'}

class wplheal_parn2cursr(bpy.types.Operator):
	bl_idname = "object.wplheal_parn2cursr"
	bl_label = "Snap parent to active"
	bl_options = {'REGISTER', 'UNDO'}

	opt_use3Dcursor = bpy.props.BoolProperty(
		name		= "Use current 3D cursor position",
		default	 = False
		)

	@classmethod
	def poll(self, context):
		return ( context.object is not None)

	def execute(self, context):
		def deselect_all(cc):
			for selected in cc.selected_objects:
				selected.select = False
		active_obj = context.scene.objects.active
		if active_obj is None:
			self.report({'ERROR'}, "No objects selected")
			return {'CANCELLED'}
		# if parent not in the current set of views - nothing will happen! Snapping will be ignored
		bpy.ops.view3d.layers(nr=0, extend=False, toggle=False)
		if self.opt_use3Dcursor == False:
			bpy.ops.view3d.snap_cursor_to_active()
		select_and_change_mode(active_obj, 'OBJECT') # to exit from possible edit
		deselect_all(context)
		if len(active_obj.children) == 0 and active_obj.parent is not None:
			parent = active_obj.parent
		else:
			parent = active_obj
		print("Parent:", parent.name)
		child_objs = []
		for child in parent.children:
			child.select = True
			child_objs.append(child)
			bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
			child.select = False
		select_and_change_mode(parent, 'OBJECT')
		bpy.ops.view3d.snap_selected_to_cursor(use_offset=False)
		parent.select = False
		for child in child_objs:
			child.select = True
		parent.select = True
		bpy.context.scene.objects.active = parent
		bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)
		for child in child_objs:
			child.select = False
		parent.select = False
		active_obj.select = True
		bpy.context.scene.objects.active = active_obj
		self.report({'INFO'}, "Done")
		return {'FINISHED'}

########### ############ ########### ############ ########### ############ ########### ############
########### ############ ########### ############ ########### ############ ########### ############
class WPLHealingTools_Panel1(bpy.types.Panel):
	bl_label = "Prop: Heal"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_category = 'WPL'

	def draw_header(self, context):
		layout = self.layout
		layout.label(text="")

	def draw(self, context):
		layout = self.layout
		col = layout.column()

		box3 = col.box()
		opPush2 = box3.operator("object.wplheal_pushmatrix", text="Obj: Copy matrix")
		opPush2.opt_resetScale = False
		opPush2.opt_resetRotation = False
		opPush2.opt_reset2Global = False
		box3.operator("object.wplheal_popmatrix")
		box3.operator("mesh.wplverts_orialign", text="Move to 3D cursor").opt_mode = 'CUR' # WPL
		box3.separator()
		opPush1 = box3.operator("object.wplheal_pushmatrix", text="Copy+reset matrix")
		opPush1.opt_resetScale = True
		opPush1.opt_resetRotation = True
		opPush1.opt_reset2Global = True
		col.separator()
		box1 = col.box()
		box1.operator("mesh.wplheal_maskout", text='Hidegeom selected')
		row1 = box1.row()
		row1.operator("object.wplheal_tweakobj", text='Mark collider').opt_actionType = 'ADD'
		row1.operator("object.wplheal_tweakobj", text='Clear collider').opt_actionType = 'REM'
		col.separator()
		box4 = col.box()
		box4.operator("object.wplheal_wrapempty", text="Wrap in empty")
		box4.separator()
		box4.operator("object.wplheal_parn2cursr", text="Snap parent to active").opt_use3Dcursor = False
		box4.operator("object.wplheal_parn2cursr", text="Snap parent to 3D cursor").opt_use3Dcursor = True
		box4.separator()
		box4.operator("object.wplheal_orig2cursr", text="Snap origin to active").opt_use3Dcursor = False
		box4.operator("object.wplheal_orig2cursr", text="Snap origin to 3D cursor").opt_use3Dcursor = True
		box4.separator()
		box4.operator("object.wplheal_objo2cursr", text="Snap orientation to active")
		col.separator()
		box2 = col.box()
		box2.operator("object.wplheal_selbymats", text="Select by mats")
		box2.operator("object.wplheal_replacemats", text="Mass-replace mats")
		box2.separator()
		box2.operator("object.wplheal_remunusdats", text="Remove unused datas")
		box2.operator("object.wplheal_massrename", text="Rename object deps")
		box2.separator()
		box2.operator("object.wplheal_resetgeom", text="Reset geometry")
		box2.operator("object.wplheal_samegeom", text="Select similar to active")
		#col.operator("object.wplheal_replaceobjs", text="Replace selected with active")
		# col.separator()
		# box5 = col.box()
		# box5.label("Physics")
		# box5.operator("object.wplheal_stepphysics", text="Roll bpy-physics")

def register():
	print("WPLHealingTools_Panel1 registered")
	bpy.utils.register_module(__name__)

def unregister():
	bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
	register()
