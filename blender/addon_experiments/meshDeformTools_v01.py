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
kWPLShrinkWrapMod = "WPL_PinnedVerts"
kWPLMeshDeformMod = "WPL_Meshdefrm"
kWPLBonesDefPostfix = "_wpldeform"
kWPLConvHullObj = "sys_hull"
kWPLSystemEmpty = "zzz_Support"
kWPLSystemLayer = 19

######################### ######################### #########################
######################### ######################### #########################
def moveObjectOnLayer(c_object, layId):
	#print("moveObjectOnLayer",c_object.name,layId)
	def layers(l):
		all = [False]*20
		all[l]=True
		return all
	c_object.layers = layers(layId)

def getSysEmpty(context,subname):
	emptyname = kWPLSystemEmpty
	if len(subname)>0:
		emptyname = subname
	empty = context.scene.objects.get(emptyname)
	if empty is None:
		empty = bpy.data.objects.new(emptyname, None)
		empty.empty_draw_size = 0.45
		empty.empty_draw_type = 'PLAIN_AXES'
		context.scene.objects.link(empty)
		moveObjectOnLayer(empty,kWPLSystemLayer)
		context.scene.update()
		if len(subname) > 0:
			empty.parent = getSysEmpty(context,"")
	return empty
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

def get_bmhistory_vertsIdx(active_bmesh):
	active_bmesh.verts.ensure_lookup_table()
	active_bmesh.verts.index_update()
	selectedVertsIdx = []
	for elem in active_bmesh.select_history:
		if isinstance(elem, bmesh.types.BMVert) and elem.select and elem.hide == 0:
			selectedVertsIdx.append(elem.index)
	return selectedVertsIdx
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

def getF3cValue(indexCur,indexMax,index50,F3c):
	value = 0.0
	if indexCur<index50:
		value = F3c[0]+(F3c[1]-F3c[0])*(float(indexCur)/max(0.001,index50))
	else:
		value = F3c[1]+(F3c[2]-F3c[1])*(float(indexCur-index50)/max(0.001,indexMax-index50))
	return value
def wpl_slope(v0,v1,v2,mid,pos): # for PY parameters
	return getF3cValue(pos,1.0,mid,(v0,v1,v2))
def wpl_mix(v0,v1,pos): # for PY parameters
	return v0+(v1-v0)*pos

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
def copyBMVertColtoFace(bm,vIdx,trgFace):
	bm.verts.ensure_lookup_table()
	bm.faces.ensure_lookup_table()
	bm.verts.index_update()
	allvcs = bm.loops.layers.color.keys()
	bm_v = bm.verts[vIdx]
	for llayer_key in allvcs:
		llayer = bm.loops.layers.color[llayer_key]
		cck = llayer_key+str(vIdx)
		if cck in vIdx_vccache:
			fcl = vIdx_vccache[cck]
		else:
			fcl = Vector((0,0,0))
			fcl_c = 0
			for lfc in bm_v.link_faces:
				for loop in lfc.loops:
					fcl = fcl+Vector((loop[llayer][0],loop[llayer][1],loop[llayer][2]))
					fcl_c = fcl_c+1
			if fcl_c>0:
				fcl = fcl/fcl_c
			vIdx_vccache[cck] = fcl
		for loop in trgFace.loops:
			loop[llayer] = (fcl[0],fcl[1],fcl[2],1)
def get_active_context_cursor(context):
	scene = context.scene
	space = context.space_data
	cursor = (space if space and space.type == 'VIEW_3D' else scene).cursor_location
	return cursor

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
def modfGetByType(c_object,modType):
	for md in c_object.modifiers:
		if md.type == modType: #'SUBSURF'
			return md
	return None
######################### ######################### #########################
######################### ######################### #########################
class wplmdefr_bind(bpy.types.Operator):
	bl_idname = "mesh.wplmdefr_bind"
	bl_label = "Multi-bind mesh/lat deform"
	bl_options = {'REGISTER', 'UNDO'}

	opt_makeWireInvis = BoolProperty(
		name="Surf: Wireframe & No-Render",
		default=True,
	)

	@classmethod
	def poll(self, context):
		# Check if we have a mesh object active and are in vertex paint mode
		#p = context.object and context.object.data and (isinstance(context.scene.objects.active, bpy.types.Object))
		if len(bpy.context.selected_objects)>0:
			return True
		return False

	def execute(self, context):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		#sel_all = [o.name for o in bpy.context.selected_objects]
		sel_all = []
		for sel_obj in bpy.context.selected_objects:
			if sel_obj.type == 'EMPTY' or sel_obj.type == 'ARMATURE' or sel_obj.data is None:
				continue
			sel_all.append(sel_obj.name)
		select_and_change_mode(active_obj,"OBJECT")
		if len(sel_all) == 0:
			self.report({'ERROR'}, "No objects selected")
			return {'CANCELLED'}
		deformToolsOpts = context.scene.deformToolsOpts
		cage_object = None
		try:
			cage_object = context.scene.objects[deformToolsOpts.bind_targ]
		except:
			pass
		if cage_object is None or (cage_object.type != 'MESH' and cage_object.type != 'LATTICE'):
			self.report({'ERROR'}, "No proper cage found, choose mesh/lattice object first")
			return {'CANCELLED'}
		for md in cage_object.modifiers:
			self.report({'ERROR'}, "Cage has modifier: "+md.type)
			return {'CANCELLED'}
		for i, sel_obj_name in enumerate(sel_all):
			sel_obj = context.scene.objects[sel_obj_name]
			if sel_obj.type == 'EMPTY' or sel_obj.type == 'ARMATURE' or sel_obj.data is None:
				continue
			if sel_obj.data.shape_keys is not None and len(sel_obj.data.shape_keys.key_blocks):
				self.report({'ERROR'}, "Some objects has shapekeys: "+sel_obj.name)
				return {'CANCELLED'}
		if self.opt_makeWireInvis:
			makeObjectNoShadow(cage_object, True, True)
		modname = kWPLMeshDeformMod
		error = 0
		for i, sel_obj_name in enumerate(sel_all):
			if sel_obj_name == cage_object.name:
				continue
			sel_obj = context.scene.objects[sel_obj_name]
			prevModifier = sel_obj.modifiers.get(modname)
			if prevModifier is not None:
				sel_obj.modifiers.remove(prevModifier)
			print("Handling object "+str(i+1)+" of "+str(len(sel_all)))
			bpy.context.scene.objects.active = sel_obj
			if sel_obj.type == 'MESH' or sel_obj.type == 'CURVE':
				if cage_object.type == 'LATTICE':
					meshdef_modifier = sel_obj.modifiers.new(name = modname, type = 'LATTICE')
					meshdef_modifier.object = cage_object
					meshdef_modifier.show_in_editmode = True
					meshdef_modifier.show_on_cage = True
				else:
					meshdef_modifier = sel_obj.modifiers.new(name = modname, type = 'MESH_DEFORM')
					meshdef_modifier.object = cage_object
					meshdef_modifier.precision = 5
					meshdef_modifier.use_dynamic_bind = True
					meshdef_modifier.show_in_editmode = True
					meshdef_modifier.show_on_cage = True
					if sel_obj.type == 'CURVE':
						modfSendBackByType(sel_obj, 'MIRROR') #before binding, mirror on curve not appliable
					modfSendBackByType(sel_obj, 'SUBSURF') #before binding
					bpy.ops.object.meshdeform_bind(modifier=modname)
			else:
				print({'ERROR'}, "Failed to add modifier for type "+sel_obj.type)
				error = error+1
		self.report({'INFO'}, "Done: count="+str(len(sel_all))+" errors:"+str(error))
		return {'FINISHED'}

class wplsdefr_bind(bpy.types.Operator):
	bl_idname = "mesh.wplsdefr_bind"
	bl_label = "Multi-bind surf deform"
	bl_options = {'REGISTER', 'UNDO'}

	opt_makeWireInvis = BoolProperty(
		name="Surf: Wireframe & No-Render",
		default=True,
	)

	@classmethod
	def poll(self, context):
		# Check if we have a mesh object active and are in vertex paint mode
		if len(bpy.context.selected_objects)>0:
			return True
		return False

	def execute(self, context):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		#sel_all = [o.name for o in bpy.context.selected_objects]
		sel_all = []
		for sel_obj in bpy.context.selected_objects:
			if sel_obj.type == 'EMPTY' or sel_obj.type == 'ARMATURE' or sel_obj.data is None:
				continue
			sel_all.append(sel_obj.name)
		select_and_change_mode(active_obj,"OBJECT")
		if len(sel_all) == 0:
			self.report({'ERROR'}, "No objects selected")
			return {'CANCELLED'}
		deformToolsOpts = context.scene.deformToolsOpts
		cage_object = None
		try:
			cage_object = context.scene.objects[deformToolsOpts.bind_targ]
		except:
			pass
		if cage_object is None or isinstance(cage_object.data, bpy.types.Mesh) == False:
			self.report({'ERROR'}, "No proper surface found, choose surface object first")
			return {'CANCELLED'}
		for i, sel_obj_name in enumerate(sel_all):
			sel_obj = context.scene.objects[sel_obj_name]
			if sel_obj.type == 'EMPTY' or sel_obj.type == 'ARMATURE' or sel_obj.data is None:
				continue
			if sel_obj.data.shape_keys is not None and len(sel_obj.data.shape_keys.key_blocks):
				self.report({'ERROR'}, "Some objects has shapekeys: "+sel_obj.name)
				return {'CANCELLED'}
		if self.opt_makeWireInvis:
			makeObjectNoShadow(cage_object, True, True)
		modname = kWPLMeshDeformMod
		error = 0
		for i, sel_obj_name in enumerate(sel_all):
			if sel_obj_name == cage_object.name:
				continue
			sel_obj = context.scene.objects[sel_obj_name]
			prevModifier = sel_obj.modifiers.get(modname)
			if prevModifier is not None:
				sel_obj.modifiers.remove(prevModifier)
			print("Handling object "+str(i+1)+" of "+str(len(sel_all)))
			bpy.context.scene.objects.active = sel_obj
			if sel_obj.type == 'MESH':
				surfdef_modifier = sel_obj.modifiers.new(name = modname, type = 'SURFACE_DEFORM')
				surfdef_modifier.target = cage_object
				#surfdef_modifier.falloff = 5
				modfSendBackByType(sel_obj, 'SUBSURF') #before binding
				bpy.ops.object.surfacedeform_bind(modifier=modname) #bpy.ops.object.
			else:
				print({'ERROR'}, "Failed to add modifier for type "+sel_obj.type)
				error = error+1
		self.report({'INFO'}, "Done: count="+str(len(sel_all))+" errors:"+str(error))
		return {'FINISHED'}

class wplmodifs_apply(bpy.types.Operator):
	bl_idname = "mesh.wplmodifs_apply"
	bl_label = "Apply deform modifier"
	bl_options = {'REGISTER', 'UNDO'}

	opt_ignoreMirror = BoolProperty(
		name="Ignore Mirror",
		default=False,
	)
	opt_ignoreArma = BoolProperty(
		name="Ignore Armature",
		default=False,
	)

	@classmethod
	def poll(self, context):
		# Check if we have a mesh object active
		if len(bpy.context.selected_objects)>0:
			return True
		return False

	def execute(self, context):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		#sel_all = [o.name for o in bpy.context.selected_objects]
		sel_all = []
		for sel_obj in bpy.context.selected_objects:
			if sel_obj.type == 'EMPTY' or sel_obj.type == 'ARMATURE' or sel_obj.data is None:
				continue
			sel_all.append(sel_obj.name)
		select_and_change_mode(active_obj,"OBJECT")
		if len(sel_all) == 0:
			self.report({'ERROR'}, "No objects selected")
			return {'CANCELLED'}
		for i, sel_obj_name in enumerate(sel_all):
			sel_obj = context.scene.objects[sel_obj_name]
			if sel_obj.type == 'EMPTY' or sel_obj.type == 'ARMATURE' or sel_obj.data is None:
				continue
			if sel_obj.data.shape_keys is not None and len(sel_obj.data.shape_keys.key_blocks):
				self.report({'ERROR'}, "Some objects has shapekeys: "+sel_obj.name)
				return {'CANCELLED'}
			for md in sel_obj.modifiers:
				if md.type == 'MIRROR' and self.opt_ignoreMirror == False:
					self.report({'ERROR'}, "Some objects has MIRROR modifier: "+sel_obj.name)
					return {'FINISHED'}
				if md.type == 'ARMATURE' and kWPLBonesDefPostfix not in md.name and self.opt_ignoreArma == False:
					self.report({'ERROR'}, "Some objects has ARMATURE modifier: "+sel_obj.name)
					return {'FINISHED'}
		error = 0
		done = 0
		for i, sel_obj_name in enumerate(sel_all):
			sel_obj = context.scene.objects[sel_obj_name]
			print("Handling object "+str(i+1)+" of "+str(len(sel_all)))
			try:
				#bpy.context.scene.objects.active = sel_obj
				select_and_change_mode(sel_obj, 'OBJECT')
				modname = kWPLShrinkWrapMod
				if sel_obj.modifiers.get(modname) is not None:
					bpy.ops.object.modifier_apply(apply_as='DATA', modifier=modname)
					groups2del = []
					for grp in sel_obj.vertex_groups:
						if grp.name.find(modname) >= 0:
							groups2del.append(grp.name)
					for grp in groups2del:
						vg = sel_obj.vertex_groups.get(grp)
						sel_obj.vertex_groups.remove(vg)
					done = done+1
				modname = kWPLMeshDeformMod
				if sel_obj.modifiers.get(modname) is not None:
					bpy.ops.object.modifier_apply(apply_as='DATA', modifier=modname)
					done = done+1

				modname = sel_obj.name+kWPLBonesDefPostfix
				if sel_obj.modifiers.get(modname) is not None:
					bpy.ops.object.modifier_apply(apply_as='DATA', modifier=modname)
					groups2del = []
					for grp in sel_obj.vertex_groups:
						if grp.name.find(modname) >= 0:
							groups2del.append(grp.name)
					for grp in groups2del:
						vg = sel_obj.vertex_groups.get(grp)
						sel_obj.vertex_groups.remove(vg)
					# can be set for several objects
					#if bpy.data.objects.get(modname) is not None:
					#	bpy.data.objects.remove(bpy.data.objects[modname], True)
					done = done+1
			except Exception as error:
				print({'ERROR'}, "Failed to apply modifier: "+error)
				error = error+1
		self.report({'INFO'}, "Done: count="+str(done)+" errors:"+str(error))
		return {'FINISHED'}

class wplhelpr_convhull(bpy.types.Operator):
	bl_idname = "object.wplhelpr_convhull"
	bl_label = "Add convex hull"
	bl_options = {'REGISTER', 'UNDO'}

	opt_makeWireInvis = BoolProperty(
		name="Wireframe & No-Render",
		default=True,
	)
	opt_combineAll = BoolProperty(
		name="Combine all verts",
		default=True,
	)
	opt_addDisplace = FloatProperty(
		name="Displace",
		min = -100, max = 100,
		default=0.0,
	)
	opt_addRemesh = IntProperty(
		name="Remesh",
		min = 0, max = 12,
		default=0,
	)

	@classmethod
	def poll(self, context):
		return ( context.object is not None)

	def execute(self, context):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		#bm2 = None
		meshes_verts = []
		needToSetObjectMode = True
		if bpy.context.mode != 'OBJECT':
			needToSetObjectMode = False
			sel_mesh = None
			#bm2 = bmesh.new()
			try:
				bpy.ops.mesh.select_mode(type='VERT')
				select_and_change_mode(active_obj, 'OBJECT' )
				sel_mesh = active_obj.to_mesh(context.scene, True, 'PREVIEW')
				if sel_mesh is None:
					self.report({'ERROR'}, "No mesh")
					return {'CANCELLED'}
				if self.opt_combineAll == True:
					mesh_verts = []
					for v in sel_mesh.vertices:
						if v.select:
							#bm2.verts.new(active_obj.matrix_world*v.co)
							mesh_verts.append(active_obj.matrix_world*v.co)
					if len(mesh_verts) >= 3:
						meshes_verts.append(mesh_verts)
				else:
					bm = bmesh.new() #bmesh.from_edit_mesh(active_mesh)
					bm.from_mesh(sel_mesh)
					bm.verts.ensure_lookup_table()
					bm.verts.index_update()
					selverts = []
					for bm_v in bm.verts:
						if bm_v.select:
							selverts.append(bm_v.index)
					allVertsIslandsed = splitBmVertsByLinks_v02(bm, selverts, True)
					for meshlist in allVertsIslandsed:
						if len(meshlist)>0:
							mesh_verts = []
							for bm_v2Idx in meshlist:
								bm_v2 = bm.verts[bm_v2Idx]
								mesh_verts.append(active_obj.matrix_world*bm_v2.co)
							if len(mesh_verts) >= 3:
								meshes_verts.append(mesh_verts)
				select_and_change_mode(active_obj, 'EDIT' )
			except Exception as e:
				print("Exception e",e)
				pass
			if sel_mesh is not None:
				bpy.data.meshes.remove(sel_mesh)
		else:
			#objs2check = [obj.name for obj in bpy.context.scene.objects if obj.select]
			objs2checkNames = [o.name for o in bpy.context.selected_objects]
			if len(objs2checkNames) < 1:
				self.report({'ERROR'}, "No objects selected")
				return {'CANCELLED'}
			#bm2 = bmesh.new()
			mesh_verts = []
			for sel_obj_name in objs2checkNames:
				sel_obj = context.scene.objects.get(sel_obj_name)
				print("Grabbing ",sel_obj)
				select_and_change_mode(sel_obj, 'OBJECT' )
				sel_mesh = None
				try:
					sel_mesh = sel_obj.to_mesh(context.scene, True, 'PREVIEW')
				except:
					pass
				if sel_mesh is None:
					print("No mesh for ",sel_obj)
					continue
				if self.opt_combineAll == False:
					mesh_verts = []
				for v in sel_mesh.vertices:
					#bm2.verts.new(sel_obj.matrix_world*v.co)
					mesh_verts.append(sel_obj.matrix_world*v.co)
				if self.opt_combineAll == False:
					if len(mesh_verts) >= 3:
						meshes_verts.append(mesh_verts)
				bpy.data.meshes.remove(sel_mesh)
			if self.opt_combineAll == True:
				if len(mesh_verts) >= 3:
					meshes_verts.append(mesh_verts)
		if len(meshes_verts) == 0:
			self.report({'ERROR'}, "Select more verts")
			return {'FINISHED'}
		bm2 = bmesh.new()
		for mesh_verts in meshes_verts:
			hullv = []
			for co in mesh_verts:
				bm2v = bm2.verts.new(co)
				hullv.append(bm2v)
			bm2.verts.ensure_lookup_table()
			bm2.verts.index_update()
			print("Adding convex: ",len(hullv))
			result = bmesh.ops.convex_hull(bm2, input=hullv)
			if "geom_unused" in result and len(result["geom_unused"])>0:
				for v in result["geom_unused"]:
					bm2.verts.remove(v)
		hullName = kWPLConvHullObj+"_"+active_obj.name
		hullOld = context.scene.objects.get(hullName)
		if hullOld is not None:
			bpy.data.objects.remove(hullOld, True)
		bm2m = bpy.data.meshes.new(kWPLConvHullObj+"_"+active_obj.name+"_mesh")
		bm2ob = bpy.data.objects.new(hullName, bm2m)
		#if transform_base is not None:
		#	bm2ob.matrix_world = transform_base.matrix_world
		bm2ob.parent = getSysEmpty(context,"")
		bpy.context.scene.objects.link(bm2ob)
		bm2.to_mesh(bm2m)
		modifiers = bm2ob.modifiers
		if abs(self.opt_addDisplace) > 0.0001:
			displ_modifier = modifiers.new('WPLTMPDISPL', type = 'DISPLACE')
			displ_modifier.direction = 'NORMAL'
			displ_modifier.mid_level = 0.0
			displ_modifier.strength = self.opt_addDisplace
		if self.opt_addRemesh > 0:
			remesh_modifier = modifiers.new('WPLTMPREMESH', 'REMESH')
			remesh_modifier.mode = 'SMOOTH'
			remesh_modifier.scale = 0.99
			remesh_modifier.use_remove_disconnected = False
			remesh_modifier.octree_depth = self.opt_addRemesh
		if self.opt_makeWireInvis:
			makeObjectNoShadow(bm2ob, True, True)
		if needToSetObjectMode:
			select_and_change_mode(bm2ob, 'OBJECT' )
			bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
		moveObjectOnLayer(bm2ob,kWPLSystemLayer)
		#select_and_change_mode(active_obj, 'OBJECT' )
		self.report({'INFO'}, "Done")
		return {'FINISHED'}

class wplhelpr_armatube(bpy.types.Operator):
	bl_idname = "object.wplhelpr_armatube"
	bl_label = "Add bb-armature"
	bl_options = {'REGISTER', 'UNDO'}

	opt_envelopeDist = FloatProperty(
		name = "Full distance",
		min = 0.0001, max = 100.0,
		default = 0.01
	)
	opt_basementDir = FloatVectorProperty(
		name = "Basement bone direction",
		size = 3,
		default = (0.0,0.0,1.0)
	)
	opt_bboneSegms = IntProperty(
		name = "BBone segments",
		min = 1, max = 100,
		default = 5
	)
	opt_detachBones = BoolProperty(
		name="Detach bones",
		default=False,
	)
	opt_withCorSmooth = BoolProperty(
		name="Add corrective smoothing",
		default=False,
	)
	opt_withBBoneDraw = BoolProperty(
		name="Show BBones",
		default=True,
	)
	@classmethod
	def poll(self, context):
		return True
	def execute(self, context):
		active_obj = context.scene.objects.active
		if active_obj is None or (active_obj.type != 'MESH' and active_obj.type != 'CURVE'):
			self.report({'ERROR'}, "No valid object found")
			return {'CANCELLED'}
		if abs(active_obj.scale[0]-1.0)+abs(active_obj.scale[1]-1.0)+abs(active_obj.scale[2]-1.0) > 0.001:
			self.report({'ERROR'}, "Scale not applied: "+active_obj.name)
			return {'CANCELLED'}
		is_local_view = sum(bpy.context.space_data.layers[:]) == 0
		if is_local_view:
			self.report({'ERROR'}, "Can`t work in Local view")
			return {'CANCELLED'}
		select_and_change_mode(active_obj,'EDIT')
		active_mesh = active_obj.data
		maxdim = max(max(active_obj.dimensions[0],active_obj.dimensions[1]),active_obj.dimensions[2])
		bm = None
		vertsIdx = []
		try:
			bm = bmesh.from_edit_mesh( active_mesh )
			vertsIdx = get_bmhistory_vertsIdx(bm)
		except:
			pass
		vertsCo = []
		if len(vertsIdx) <= 1:
			vertsCo.append(Vector((-0.5,0.0,0.0))*maxdim)
			vertsCo.append(Vector((0.5,0.0,0.0))*maxdim)
		else:
			for vIdx in vertsIdx:
				v = bm.verts[vIdx]
				vertsCo.append(v.co)
		tip_bones = False #adding pre- and post-verts for bone controls
		if self.opt_detachBones == False and len(vertsCo)>=2:
			tip_bones = True
			pre_v = vertsCo[0]-(vertsCo[1]-vertsCo[0]) #.normalized()self.opt_envelopeDist*0.33*
			vertsCo.insert(0,pre_v)
			post_v = vertsCo[-1]-(vertsCo[-2]-vertsCo[-1])
			vertsCo.append(post_v)
		bm2 = bmesh.new()
		bm2vPrev = None
		for vCo in vertsCo:
			bm2v = bm2.verts.new(vCo)
			if bm2vPrev is not None:
				bm2.edges.new([bm2vPrev,bm2v])
			bm2vPrev = bm2v
		armmeshModName = active_obj.name+kWPLBonesDefPostfix
		armmeshOBName = armmeshModName
		armmeshOBCageName = armmeshOBName+'_cage'
		armmeshOBNameSkin = armmeshOBName+'_skin'
		armmesh_mesh = bpy.data.meshes.new(armmeshOBName+"_mesh")
		bm2.to_mesh(armmesh_mesh)
		mesh_object = context.scene.objects.get(armmeshOBCageName)
		if mesh_object is not None:
			bpy.data.objects.remove(mesh_object, True)
		mesh_object = bpy.data.objects.new(name=armmeshOBCageName, object_data=armmesh_mesh)
		mesh_object.matrix_world = active_obj.matrix_world
		mesh_object.parent = getSysEmpty(context,"")
		bpy.context.scene.objects.link(mesh_object)
		moveObjectOnLayer(mesh_object,kWPLSystemLayer)
		bpy.context.scene.update()
		select_and_change_mode(mesh_object,'OBJECT')
		modifiers = mesh_object.modifiers
		skin_mod = modifiers.new(armmeshOBNameSkin, 'SKIN')
		skin_mod.use_x_symmetry = False
		skin_mod.use_y_symmetry = False
		skin_mod.use_z_symmetry = False
		skin_mod.show_in_editmode = True
		bpy.context.scene.objects.active = mesh_object
		select_and_change_mode(mesh_object,'OBJECT')
		bpy.ops.object.skin_armature_create(modifier=armmeshOBNameSkin)
		bpy.data.objects.remove(mesh_object, True)
		mesh_arm_object = context.scene.objects.get("Armature")
		if mesh_arm_object is not None:
			mesh_arm_object.name = armmeshOBName
			mesh_arm_object.parent = getSysEmpty(context,"")
			mesh_arm_object.show_x_ray = True
			mesh_arm_object.select = True
			armatAR = bpy.data.armatures.get(mesh_arm_object.data.name)
			if self.opt_withBBoneDraw and self.opt_bboneSegms > 1:
				armatAR.draw_type = 'BBONE'
			else:
				armatAR.draw_type = 'STICK'
			armatAR.use_auto_ik = True
			select_and_change_mode(mesh_arm_object,'EDIT')
			basementDir = Vector((self.opt_basementDir[0],self.opt_basementDir[1],self.opt_basementDir[2]))
			for i, eb in enumerate(armatAR.edit_bones):
				if tip_bones and (i == 0 or i == len(armatAR.edit_bones)-1):
					eb.bbone_segments = 1
				else:
					eb.bbone_segments = self.opt_bboneSegms
				eb.use_deform = True
				eb.envelope_weight = 1.0
				if self.opt_detachBones:
					eb.use_connect = False
					eb.use_inherit_rotation = False
					eb.use_inherit_scale = False
					eb.parent = None
			if basementDir.length > 0:
				active_obj_cenInArm = mesh_arm_object.matrix_world.inverted()*active_obj.location
				bone_root = armatAR.edit_bones.new("basement")
				bone_root.head = active_obj_cenInArm-maxdim*0.5*basementDir.normalized()
				bone_root.tail = active_obj_cenInArm+maxdim*0.5*basementDir.normalized()
				bone_root.use_deform = True
				bone_root.envelope_weight = 1.0
			bpy.ops.armature.select_all(action='SELECT')
			bpy.ops.transform.transform(mode='BONE_SIZE', value=(0.01, 0.01, 0.01, 0))
			for i, eb in enumerate(armatAR.edit_bones):
				if eb.name == "basement":
					eb.envelope_distance = 999
					eb.head_radius = 999
					eb.tail_radius = 999
				else:
					eb.envelope_distance = self.opt_envelopeDist
					eb.head_radius = self.opt_envelopeDist*0.3
					eb.tail_radius = self.opt_envelopeDist*0.3
			select_and_change_mode(mesh_arm_object,'POSE')
			mod = active_obj.modifiers.new(armmeshModName, 'ARMATURE')
			mod.object = mesh_arm_object
			mod.use_bone_envelopes = True
			mod.use_vertex_groups = False
			mod.use_deform_preserve_volume = True
			if self.opt_withCorSmooth and modfGetByType('CORRECTIVE_SMOOTH') is None:
				mod = active_obj.modifiers.new(armmeshModName+"_cc", 'CORRECTIVE_SMOOTH')
				mod.iterations = 10
				mod.use_pin_boundary =  True
		self.report({'INFO'}, "Done")
		return {'FINISHED'}

class wplhelpr_curvmesh(bpy.types.Operator):
	bl_idname = "object.wplhelpr_curvmesh"
	bl_label = "Add curve-driven surface"
	bl_options = {'REGISTER', 'UNDO'}

	opt_genType = bpy.props.EnumProperty(
		name="Mesh type", default="STRIPE",
		items=(("STRIPE", "Stripe", ""), ("CUBE", "Cube", ""))
		)
	opt_curveWidthFac = FloatProperty(
		name="Curve Width factor",
		min = 0, max = 100,
		default = 0.1,
	)
	opt_makeWireInvis = BoolProperty(
		name="Wireframe & No-Render",
		default=True,
	)

	@classmethod
	def poll(self, context):
		return True

	def execute(self, context):
		# creating curve
		active_obj = context.scene.objects.active
		if active_obj is None:
			self.report({'ERROR'}, "No object selected")
			return {'CANCELLED'}
		oldmode = select_and_change_mode(active_obj,'EDIT')
		active_mesh = active_obj.data
		bm = None
		vertsIdx = []
		try:
			bm = bmesh.from_edit_mesh( active_mesh )
			vertsIdx = get_bmhistory_vertsIdx(bm)
		except:
			pass
		if len(vertsIdx) <= 1:
			self.report({'ERROR'}, "No selected verts found, select some verts first")
			return {'CANCELLED'}
		#curpos = get_active_context_cursor(context)
		curveOBName = active_obj.name+'_defrm_curve'
		curveOBCageName = active_obj.name+'_defrm_cage'
		curveData = bpy.data.curves.new(curveOBCageName+'_dt', type='CURVE')
		curveData.dimensions = '3D'
		curveData.twist_mode = 'MINIMUM'
		curveData.fill_mode = 'FULL'
		curveOB = context.scene.objects.get(curveOBName)
		if curveOB is not None:
			bpy.data.objects.remove(curveOB, True)
		curveOB = bpy.data.objects.new(curveOBName, curveData)
		#curveOB.location = curpos
		curveOB.matrix_world = active_obj.matrix_world
		curveOB.parent = getSysEmpty(context,"")
		bpy.context.scene.objects.link(curveOB)
		moveObjectOnLayer(curveOB,kWPLSystemLayer)
		curveName = curveOB.name
		polyline = curveData.splines.new('POLY')
		polyline.use_endpoint_u = True
		edgesTotal = 0.0
		edgesTotalLen = 0.0
		curveLength = 0.0
		v_co_prev = None
		v_co_first = None
		#curveUnwrappedPoints = []
		for step,v_idx in enumerate(vertsIdx):
			if len(polyline.points) <= step:
				polyline.points.add(1)
			v = bm.verts[v_idx]
			if v_co_prev is None:
				v_co_first = v.co
				v_co_prev = v.co
				v_co_g = active_obj.matrix_world*v.co
				curveOB.location = v_co_g
			for e in v.link_edges:
				edgesTotal = edgesTotal+1
				edgesTotalLen = edgesTotalLen+e.calc_length()
			v_co_l = v.co-v_co_first
			polyline.points[step].co = (v_co_l[0], v_co_l[1], v_co_l[2], 1)
			curveLength = curveLength+(v.co-v_co_prev).length
			#curveUnwrappedPoints.append(Vector((curveLength,0,0)))
			v_co_prev = v_co_l
		# if self.opt_genType == 'LATT':
			# opt_stepsCount = len(vertsIdx)
			# lattice_data = bpy.data.lattices.new(name=curveOBCageName+'_ld')
			# lattice_data.interpolation_type_u = 'KEY_CATMULL_ROM'
			# lattice_data.interpolation_type_v = 'KEY_CATMULL_ROM'
			# lattice_data.interpolation_type_w = 'KEY_CATMULL_ROM'
			# lattice_data.points_u = opt_stepsCount+1
			# lattice_data.points_v = 2
			# lattice_data.points_w = 2
			# lattice_data.use_outside = True
			# lattice_object = context.scene.objects.get(curveOBCageName)
			# if lattice_object is not None:
				# bpy.data.objects.remove(lattice_object, True)
			# lattice_object = bpy.data.objects.new(name=curveOBCageName, object_data=lattice_data)
			# lattice_object.dimensions = Vector((2*curveLength/(opt_stepsCount-2),self.opt_stepSize,self.opt_stepSize))
			# lattice_data.transform(Matrix.Translation(Vector((curveLength*0.5,0,0))))
			# lattice_object.show_x_ray = True
			# lattice_object.parent = curveOB #getSysEmpty(context,"")
			# lattice_object.location = Vector((0,0,0))
			# bpy.context.scene.objects.link(lattice_object)
			# cage_ob = lattice_object
		bmWidth = edgesTotalLen/edgesTotal
		curveData.bevel_depth = bmWidth*self.opt_curveWidthFac
		curveData.bevel_resolution = 0
		polyline.order_u = 4
		polyline.resolution_u = 10
		bm2 = bmesh.new()
		if self.opt_genType == 'STRIPE':
			v1_prev = None
			v2_prev = None
			#for v in curveUnwrappedPoints:
			pointCount = max(3,int(curveLength/(bmWidth*4.0))-1)
			for i in range(pointCount):
				v = Vector((i*bmWidth,0,0))
				v1 = bm2.verts.new(v+Vector((0, bmWidth, 0)))
				v2 = bm2.verts.new(v-Vector((0, bmWidth, 0)))
				if v1_prev is not None:
					bm2.faces.new([v1_prev,v2_prev,v2,v1])
				v1_prev = v1
				v2_prev = v2
		if self.opt_genType == 'CUBE':
			bmesh.ops.create_cube(bm2,size=bmWidth) #,calc_uvs=True
		#curve_mesh = ??? #curveOB.to_mesh(context.scene, True, 'PREVIEW')
		curve_mesh = bpy.data.meshes.new(curveOBCageName+"_mesh")
		bm2.to_mesh(curve_mesh)
		mesh_object = context.scene.objects.get(curveOBCageName)
		if mesh_object is not None:
			bpy.data.objects.remove(mesh_object, True)
		mesh_object = bpy.data.objects.new(name=curveOBCageName, object_data=curve_mesh)
		mesh_object.parent = curveOB
		mesh_object.location = Vector((0,0,0))
		bpy.context.scene.objects.link(mesh_object)
		moveObjectOnLayer(mesh_object,kWPLSystemLayer)
		bpy.context.scene.update()
		select_and_change_mode(active_obj,'OBJECT')
		select_and_change_mode(mesh_object,'EDIT')
		bpy.ops.mesh.uv_texture_add()
		bpy.ops.mesh.select_all(action='SELECT')
		bpy.ops.uv.cube_project() #cube_size=0.99
		#bpy.ops.uv.select_all(action='SELECT')
		select_and_change_mode(mesh_object,'OBJECT')
		select_and_change_mode(active_obj,oldmode)
		#print("dims",curveOB.dimensions[0],mesh_object.dimensions[0])
		#mesh_object.scale = Vector((curveOB.dimensions[0]/mesh_object.dimensions[0],1.0,1.0))
		#mesh_object.scale = Vector((curveLength/mesh_object.dimensions[0],1.0,1.0))

		modifiers = mesh_object.modifiers
		if self.opt_genType == 'CUBE':
			relSize = 1.1
			pointCount = max(3,int(curveLength/(bmWidth*relSize*4.0))-1)
			array_mod = modifiers.new(curveName+"(A)", 'ARRAY')
			array_mod.count = pointCount
			array_mod.use_relative_offset = True
			array_mod.relative_offset_displace = (relSize,0,0)
			array_mod.use_merge_vertices = False # UV merge is bad
			array_mod.offset_u = 1.0
		curve_mod = modifiers.new(curveName+"(C)", 'CURVE')
		curve_mod.deform_axis = 'POS_X'
		curve_mod.object = curveOB
		curve_mod.show_in_editmode = True
		curve_mod.show_on_cage = True
		#solidf_modifier = modifiers.new('WPLTMPSOLDF', type = 'SOLIDIFY')
		#solidf_modifier.thickness = bmWidth
		#solidf_modifier.use_rim = True
		#solidf_modifier.offset = 0.0
		#if abs(self.opt_addDisplace) > 0.0001:
		#	displ_modifier = modifiers.new('WPLTMPDISPL', type = 'DISPLACE')
		#	displ_modifier.direction = 'NORMAL'
		#	displ_modifier.mid_level = 0.0
		#	displ_modifier.strength = self.opt_addDisplace
		#if self.opt_addRemesh > 0:
		#	remesh_modifier = modifiers.new('WPLTMPREMESH', 'REMESH')
		#	remesh_modifier.mode = 'SMOOTH'
		#	remesh_modifier.scale = 0.99
		#	remesh_modifier.use_remove_disconnected = False
		#	remesh_modifier.octree_depth = self.opt_addRemesh
		if self.opt_makeWireInvis:
			makeObjectNoShadow(mesh_object, True, True)
		makeObjectNoShadow(curveOB, True, True)
		self.report({'INFO'}, "Done")
		return {'FINISHED'}

kWPDefaultStepVal = "( 0.5*AL+0.5*(FL-AL) )*1.0"
kWPDefaultFalloffVal = "( 0.5*AL-SD*0.1+PD )*(0.8 if SD < 1.0 else 1.0)"
class wplwearoff_edge( bpy.types.Operator ):
	bl_idname = "mesh.wplwearoff_edge"
	bl_label = "Grow edges to colliders"
	bl_options = {'REGISTER', 'UNDO'}

	opt_loops = IntProperty(
		name = "Max Loops",
		min = 1, max = 200,
		default = 50
	)
	EvalS = StringProperty(
			name = "Side shift=",
			default = kWPDefaultStepVal
	)
	EvalF = StringProperty(
			name = "Normal shift=",
			default = kWPDefaultFalloffVal
	)
	@classmethod
	def poll( cls, context ):
		return ( context.object is not None  and
				context.object.type == 'MESH' )
	def execute( self, context ):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		bvh2collides = get_sceneColldersBVH(active_obj)
		edgesIdx = get_selected_edgesIdx(active_mesh)
		if len(edgesIdx) == 0:
			self.report({'ERROR'}, "No selected edges found")
			return {'FINISHED'}
		EvalF_py = None
		EvalS_py = None
		try:
			EvalF_py = compile(self.EvalF, "<string>", "eval")
			EvalS_py = compile(self.EvalS, "<string>", "eval")
		except:
			self.report({'ERROR'}, "Eval compilation: syntax error")
			return {'CANCELLED'}
		bpy.ops.object.mode_set( mode = 'EDIT' )
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.verts.index_update()
		bm.edges.ensure_lookup_table()
		bm.edges.index_update()
		bmduplisCache = {}
		clampedVerts = set()
		vertsNearpos = {}
		def getBmVertDupli(bm_v,v_dir):
			key = bm_v.index*10000 #+int(v_dir.dot(Vector((0,0,1)))*2)*1000+int(v_dir.dot(Vector((0,1,0)))*2)*100+int(v_dir.dot(Vector((1,0,0)))*2)*10
			if key in bmduplisCache:
				return bmduplisCache[key]
			v_dups = bmesh.ops.duplicate(bm, geom = [bm_v])
			vd = v_dups["geom"][0]
			bmduplisCache[key] = vd
			return vd
		def appendLiL(rootdic,key,val):
			if key not in rootdic:
				rootdic[key] = []
			rootdic[key].append(val)
		def shiftToCollider(bm_v,dist,fdir):
			# moving to surfaces
			vdAllFDst = []
			for bvh_collide in bvh2collides:
				near_location, near_normal, near_index, near_distance = bvh_collide.ray_cast(bm_v.co, fdir, 999)
				if near_distance is not None:
					vdAllFDst.append((near_location, near_normal, near_distance))
			if len(vdAllFDst) == 0:
				#clamp!!!
				clampedVerts.add(bm_v)
				return
			vdAllFDst = sorted(vdAllFDst, key=lambda pr: pr[2], reverse=True)
			near_location = vdAllFDst[0][0]
			vertsNearpos[bm_v] = near_location
			vdShift = (near_location-bm_v.co)
			#print("shiftToCollider",dist,vdShift.length,vdAllFDst[0][2])
			if dist >= vdShift.length:
				bm_v.co = near_location
				clampedVerts.add(bm_v)
				return
			bm_v.co = bm_v.co+vdShift.normalized()*dist

			vdAllMDst = []
			for bvh_collide in bvh2collides:
				near_locationM, near_normalM, near_indexM, near_distanceM = bvh_collide.ray_cast(bm_v.co, -1*fdir, 999)
				if near_distanceM is not None:
					vdAllMDst.append((near_locationM, near_normalM, near_distanceM))
			vdAllMDst = sorted(vdAllMDst, key=lambda pr: pr[2], reverse=True)
			if len(vdAllMDst)>0: # and vdAllMDst[0][2]<vdAllFDst[0][2])
				#clamp!!!
				near_location = vdAllMDst[0][0]
				bm_v.co = near_location
				clampedVerts.add(bm_v)
			return

		avgLen = 0
		for eIdx in edgesIdx:
			e = bm.edges[eIdx]
			avgLen = avgLen+e.calc_length()
		avgLen = avgLen/len(edgesIdx)
		edges2extent = []
		vertsDirs = {}
		for eIdx in edgesIdx:
			e = bm.edges[eIdx]
			if e.seam:
				continue
			if len(e.link_faces) != 1:
				continue
			if len(e.verts[0].link_edges) > 3:
				continue
			if len(e.verts[1].link_edges) > 3:
				continue
			mface = e.link_faces[0]
			edst = mface.calc_perimeter()/len(mface.edges)
			edges2extent.append((e,mface.normal,edst))
			mdir = (e.verts[0].co+e.verts[1].co)*0.5-mface.calc_center_median()
			appendLiL(vertsDirs,e.verts[0],mdir)
			appendLiL(vertsDirs,e.verts[1],mdir)
		vdst = 0.0
		for loopnum in range(self.opt_loops):
			#print("loopnum",loopnum)
			loopfac = float(loopnum)/float(self.opt_loops)
			edges2extentNext = []
			TI = loopfac
			AL = avgLen
			PD = vdst
			for v in vertsDirs:
				v_dirs = vertsDirs[v]
				if len(v_dirs)>1:
					v_dirs_ttl = Vector((0,0,0))
					for dir in v_dirs:
						v_dirs_ttl = v_dirs_ttl+dir
					vertsDirs[v] = [v_dirs_ttl/len(v_dirs)]
			for e_dat in edges2extent:
				e = e_dat[0]
				fnrm = e_dat[1]
				edst = e_dat[2]
				e_v1 = e.verts[0]
				e_v2 = e.verts[1]
				if e_v1 in clampedVerts and e_v2 in clampedVerts:
					continue
				vd1 = getBmVertDupli(e_v1,mdir)
				vd2 = getBmVertDupli(e_v2,mdir)
				FL = edst
				mdst = eval(EvalS_py)
				mdir = vertsDirs[e_v1][0]
				vd1.co = e_v1.co+mdir.normalized()*mdst
				appendLiL(vertsDirs,vd1,mdir)
				mdir = vertsDirs[e_v2][0]
				vd2.co = e_v2.co+mdir.normalized()*mdst
				appendLiL(vertsDirs,vd2,mdir)
				#maintaining edge length
				#vdc = (vd1.co+vd2.co)*0.5
				#vdn = (vd1.co-vd2.co).normalized()
				#vdd = (e_v1.co-e_v2.co).length
				#vd1.co = vdc+vdn*vdd*0.5
				#vd2.co = vdc-vdn*vdd*0.5
				SD = 0
				if e_v1 in vertsNearpos:
					SD = (vertsNearpos[e_v1]-e_v1.co).length
				vdst = eval(EvalF_py)
				shiftToCollider(vd1, vdst, fnrm)
				SD = 0
				if e_v2 in vertsNearpos:
					SD = (vertsNearpos[e_v2]-e_v2.co).length
				vdst = eval(EvalF_py)
				shiftToCollider(vd2, vdst, fnrm)
				f = bm.faces.new([e_v1,e_v2,vd2,vd1])
				f.select = True
				f.smooth = True
				copyBMVertColtoFace(bm,e_v1.index,f)
				if vd1 in clampedVerts and vd2 in clampedVerts:
					continue
				for fe in f.edges:
					if (fe.verts[0].index == vd1.index and fe.verts[1].index == vd2.index) or (fe.verts[1].index == vd1.index and fe.verts[0].index == vd2.index):
						edges2extentNext.append((fe,fnrm,edst))
			edges2extent = edges2extentNext
			if len(edges2extent) == 0:
				break
		bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		bm.normal_update()
		bmesh.update_edit_mesh(active_mesh, True)
		return {'FINISHED'}

kWPDefaultStripifyVal = "0.01 # *wpl_slope(10, 20, 10, 0.5, I)"
class wplstripify_edge( bpy.types.Operator ):
	bl_idname = "mesh.wplstripify_edge"
	bl_label = "Stripify edges"
	bl_options = {'REGISTER', 'UNDO'}
	EvalW = StringProperty(
			name = "Width=",
			default = kWPDefaultStripifyVal
	)
	EvalH = StringProperty(
			name = "Height=",
			default = kWPDefaultStripifyVal
	)
	EvalXY = StringProperty(
			name = "UV Offset=",
			default = "(0.0, 0.0)"
	)
	EvalNrm = StringProperty(
			name = "Normal=",
			default = "(Nx, Ny, Nz)"
	)
	EvalER = StringProperty(
			name = "RotFac=",
			default = "0.0"
	)
	opt_Solidify = BoolProperty(
		name="Solidify stripe",
		default=True
	)

	@classmethod
	def poll( cls, context ):
		return ( context.object is not None  and
				context.object.type == 'MESH' )
	def execute( self, context ):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		vertsIdx = get_selected_vertsIdx(active_mesh)
		edgesIdx = get_selected_edgesIdx(active_mesh)
		bpy.ops.object.mode_set( mode = 'EDIT' )
		#bpy.ops.mesh.select_mode(type="FACE")
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.verts.index_update()

		strands_points = None
		strands_vidx = None
		if len(edgesIdx) == 0 or 'VERT' in bm.select_mode:
			histVertsIdx = get_bmhistory_vertsIdx(bm)
			if len(histVertsIdx)>0:
				strands_points_line = []
				strands_vidx_line = []
				for vIdx in histVertsIdx:
					v = bm.verts[vIdx]
					strands_points_line.append(v.co)
					strands_vidx_line.append([v.index])
				strands_points=[strands_points_line]
				strands_vidx=[strands_vidx_line]
		if strands_points is None:
			if len(edgesIdx)<1:
				self.report({'ERROR'}, "No selected edges found, select some edges first")
				return {'CANCELLED'}
			(strands_points,strands_radius,strands_vidx) = getBmEdgesAsStrands_v02(bm, vertsIdx, edgesIdx, Vector((0,0,1)), 1)
		if strands_points is None:
			self.report({'ERROR'}, "No edges found, check selection (no looped, etc)")
			return {'CANCELLED'}
		if len(self.EvalW) == 0:
			self.EvalW = kWPDefaultStripifyValW
		if len(self.EvalH) == 0:
			self.EvalH = kWPDefaultStripifyValH
		EvalW_py = None
		EvalH_py = None
		EvalER_py = None
		EvalXY_py = None
		EvalNrm_py = None
		try:
			EvalW_py = compile(self.EvalW, "<string>", "eval")
			EvalH_py = compile(self.EvalH, "<string>", "eval")
			EvalER_py = compile(self.EvalER, "<string>", "eval")
			EvalXY_py = compile(self.EvalXY, "<string>", "eval")
			EvalNrm_py = compile(self.EvalNrm, "<string>", "eval")
		except:
			self.report({'ERROR'}, "Eval compilation: syntax error")
			return {'CANCELLED'}
		vIdx_cache = {}
		def getVertsForStrokePoint(bm,vIdx,flowDir,point_num,posFac):
			if vIdx in vIdx_cache:
				return vIdx_cache[vIdx]
			bm.verts.ensure_lookup_table()
			bm.verts.index_update()
			bm_v = bm.verts[vIdx]
			s3d = bm_v.co
			cen_dr = bm_v.normal
			cen_flow = flowDir.normalized() #s3d-bm.verts[prevIdx].co

			I = posFac
			Nx = cen_dr[0]
			Ny = cen_dr[1]
			Nz = cen_dr[2]
			l_width = eval(EvalW_py)
			h_offset = eval(EvalH_py)
			uv_offset = eval(EvalXY_py)
			nrm_eval = eval(EvalNrm_py)
			r_angl_s = math.pi*eval(EvalER_py)

			u_offset = uv_offset[0]
			v_offset = uv_offset[1]
			cen_dr = Vector((nrm_eval[0],nrm_eval[1],nrm_eval[2])).normalized()
			#cen_dr = cen_dr.normalized()
			#r_angl_t = math.pi*eval(EvalTR_py)+r_angl_s #getF3cValue(point_num,las_num,mid_num,self.TRotationF3c)
			cen_flow = cen_flow.normalized()
			cen_perp = cen_dr.cross(cen_flow)
			r_mat_s = Matrix.Rotation(r_angl_s, 4, cen_flow)
			cen_dr_s = r_mat_s*cen_dr
			cen_perp_vec = r_mat_s*cen_perp*l_width
			#r_mat_t = Matrix.Rotation(r_angl_t, 4, cen_flow)
			#cen_perp_vec = r_mat_t*cen_perp_vec
			s3d = s3d+u_offset*cen_perp.normalized()+v_offset*cen_dr.normalized()
			cen_p = s3d+cen_dr_s*h_offset
			v1_p = (cen_p+cen_perp_vec)
			v2_p = (cen_p-cen_perp_vec)
			#v1 = bm.verts.new(v1_p)
			#v2 = bm.verts.new(v2_p)
			v1_dups = bmesh.ops.duplicate(bm, geom = [bm_v])
			v1 = v1_dups["geom"][0]
			v1.co = v1_p
			v2_dups = bmesh.ops.duplicate(bm, geom = [bm_v])
			v2 = v2_dups["geom"][0]
			v2.co = v2_p
			if self.opt_Solidify:
				cen_p2 = s3d-cen_dr_s*h_offset
				v3_p = (cen_p2+cen_perp_vec)
				v4_p = (cen_p2-cen_perp_vec)
				v3 = bm.verts.new(v3_p)
				v4 = bm.verts.new(v4_p)
				vIdx_cache[vIdx] = (v1,v2,v4,v3)
			else:
				vIdx_cache[vIdx] = (v1,v2)
			#print("New points",vIdx,vIdx_cache[vIdx],cen_p,cen_dr,cen_perp)
			return vIdx_cache[vIdx]
		vIdx_vccache = {}
		for i, strand_curve in enumerate(strands_points):
			if len(strand_curve) < 2:
				continue
			lastVertIdx = 0
			flowDir = Vector((0,0,0))
			las_num = float(len(strand_curve))
			for j, co in enumerate(strand_curve):
				vIdx = strands_vidx[i][j][0]
				if j > 0:
					coLast = strand_curve[j-1]
					coThis = strand_curve[j]
					flowDir = coThis-coLast
					##########################################
					v_prev = getVertsForStrokePoint(bm,lastVertIdx,flowDir,j-1,float(j-1)/las_num)
					v_this = getVertsForStrokePoint(bm,vIdx,flowDir,j,float(j)/(las_num-1))
					f1 = bm.faces.new([v_prev[0],v_prev[1],v_this[1],v_this[0]])
					copyBMVertColtoFace(bm,vIdx,f1)
					if self.opt_Solidify:
						f2 = bm.faces.new([v_prev[1],v_prev[2],v_this[2],v_this[1]])
						f3 = bm.faces.new([v_prev[2],v_prev[3],v_this[3],v_this[2]])
						f4 = bm.faces.new([v_prev[3],v_prev[0],v_this[0],v_this[3]])
						copyBMVertColtoFace(bm,vIdx,f2)
						copyBMVertColtoFace(bm,vIdx,f3)
						copyBMVertColtoFace(bm,vIdx,f4)
					##########################################
				lastVertIdx = vIdx

		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		bm.normal_update()
		bmesh.update_edit_mesh(active_mesh, True)
		return {'FINISHED'}
######################### ######################### #########################
######################### ######################### #########################
class WPLDeformToolsSettings(bpy.types.PropertyGroup):
	bind_targ = StringProperty(
		name="Deformer",
		description="Object deformer",
		default = ""
	)

class WPLDeformTools_Panel1(bpy.types.Panel):
	bl_label = "Deform tools"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_category = 'WPL'

	def draw_header(self, context):
		layout = self.layout
		layout.label(text="")

	def draw(self, context):
		obj = context.scene.objects.active
		deformToolsOpts = context.scene.deformToolsOpts
		layout = self.layout
		col = layout.column()
		col.prop_search(deformToolsOpts, "bind_targ", context.scene, "objects",icon="SNAP_NORMAL")
		col.operator("mesh.wplmdefr_bind", text="Multi-bind mesh/lat deform")
		col.operator("mesh.wplsdefr_bind", text="Multi-bind surf deform")
		col.operator("mesh.wplmodifs_apply", text="Multi-apply deforms")
		col.separator()
		col.label("Helpers")
		col.operator("mesh.wplstripify_edge", text="Stripify edges")
		col.operator("mesh.wplwearoff_edge", text="Grow edges")
		col.separator()
		col.operator("object.wplhelpr_convhull", text="Convex hull from verts")
		col.separator()
		col.operator("object.wplhelpr_curvmesh", text="Add curve-driven surface")
		#col.operator("object.wplhelpr_armatube", text="Add bb-armature")

def register():
	print("WPLDeformTools_Panel1 registered")
	bpy.utils.register_module(__name__)
	bpy.types.Scene.deformToolsOpts = PointerProperty(type=WPLDeformToolsSettings)

def unregister():
	bpy.utils.unregister_module(__name__)
	bpy.utils.unregister_class(WPLDeformToolsSettings)


if __name__ == "__main__":
	register()
