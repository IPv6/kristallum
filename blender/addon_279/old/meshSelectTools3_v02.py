import math
import copy
import mathutils
import time
import random
from random import random, seed

import bpy
from bpy.props import *
import bpy.types
import bmesh
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

bl_info = {
	"name": "WPL Mesh Helpers",
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
kWPLSelBufferUVMap = "_tmpMeshSel_"
kWPLShrinkWrapMod = "WPL_PinnedVerts"

########### ############ ########### ############ ########### ############ ########### ############
########### ############ ########### ############ ########### ############ ########### ############
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

def get_active_context_cursor(context):
	scene = context.scene
	space = context.space_data
	cursor = (space if space and space.type == 'VIEW_3D' else scene).cursor_location
	return cursor

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
def get_less_vertsMap_v01(obj, set_of_vertsIdx, iterations=1):
	polygons = obj.data.polygons
	vertices = obj.data.vertices
	vert2loopMap = {}
	for vIdx in set_of_vertsIdx:
		vert2loopMap[vIdx] = 1.0
	while iterations != 0:
		verts_to_remove = set()
		for poly in polygons:
			poly_verts_idx = poly.vertices
			for v_idx in poly_verts_idx:
				if v_idx not in set_of_vertsIdx:
					for v_idx in poly_verts_idx:
						verts_to_remove.add(v_idx)
					break
		set_of_vertsIdx.difference_update(verts_to_remove)
		for vIdx in set_of_vertsIdx:
			vert2loopMap[vIdx] = vert2loopMap[vIdx]+1.0
		iterations -= 1
	return vert2loopMap

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

def visibilitySelect(active_obj, active_mesh, context, actionSelectType, fuzz):
	selverts = get_selected_vertsIdx(active_mesh)
	bpy.ops.object.mode_set( mode = 'EDIT' )
	bpy.ops.mesh.select_all(action = 'DESELECT')
	scene = bpy.context.scene
	bm = bmesh.from_edit_mesh( active_mesh )
	bm.verts.ensure_lookup_table()
	bm.faces.ensure_lookup_table()
	bm.verts.index_update()
	cameraOrigin = camera_pos(bpy.context.space_data.region_3d)
	affectedVerts = []
	fuzzlist = [(0,0,0),(fuzz,0,0),(-fuzz,0,0),(0,fuzz,0),(0,-fuzz,0),(0,0,fuzz),(0,0,-fuzz)]
	for face in bm.faces:
		for vert in face.verts:
			for fuzzpic in fuzzlist:
				if vert.index not in affectedVerts:
					# Cast a ray from the "camera" position
					co_world = active_obj.matrix_world * vert.co + mathutils.Vector(fuzzpic)
					direction = co_world - cameraOrigin;
					direction.normalize()
					result, location, normal, faceIndex, object, matrix = scene.ray_cast( cameraOrigin, direction )
					#print ("result",result," faceIndex",faceIndex," vert",vert, " verts", bm.faces[faceIndex].verts)
					if result and object.name == active_obj.name:
						facevrt = [ e.index for e in bm.faces[faceIndex].verts]
						#print ("vert.index",vert.index," facevrt",facevrt)
						if vert.index in facevrt:
							affectedVerts.append(vert.index)
	#bmesh.update_edit_mesh( active_mesh )
	bpy.ops.object.mode_set(mode='OBJECT')
	if actionSelectType == 0:
		for vertIdx in affectedVerts:
			active_mesh.vertices[vertIdx].select = True
	elif actionSelectType == 1:
		for vertIdx in selverts:
			if vertIdx in affectedVerts:
				active_mesh.vertices[vertIdx].select = True
	elif actionSelectType == 2:
		for vertIdx in selverts:
			if vertIdx not in affectedVerts:
				active_mesh.vertices[vertIdx].select = True
	bpy.ops.object.mode_set(mode='EDIT')
	#context.tool_settings.mesh_select_mode = (True, False, False)
	bpy.ops.mesh.select_mode(type="VERT")

########### ############ ########### ############ ########### ############ ########### ############
########### ############ ########### ############ ########### ############ ########### ############
class WPLvert_selvisible( bpy.types.Operator ):
	bl_idname = "mesh.wplvert_selvisible"
	bl_label = "Select visible verts"
	bl_options = {'REGISTER', 'UNDO'}
	opt_rayFuzz = bpy.props.FloatProperty(
		name		= "Fuzziness",
		default	 = 0.05
	)
	@classmethod
	def poll( cls, context ):
		return ( context.object is not None  and
				context.object.type == 'MESH' )

	def execute( self, context ):
		if not bpy.context.space_data.region_3d.is_perspective:
			self.report({'ERROR'}, "Can`t work in ORTHO mode")
			return {'CANCELLED'}
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		visibilitySelect(active_obj, active_mesh, context, 0, self.opt_rayFuzz )
		return {'FINISHED'}

class WPLvert_deselunvisible( bpy.types.Operator ):
	bl_idname = "mesh.wplvert_deselunvisible"
	bl_label = "Deselect invisible verts"
	bl_options = {'REGISTER', 'UNDO'}
	opt_rayFuzz = bpy.props.FloatProperty(
		name		= "Fuzziness",
		default	 = 0.05
	)
	@classmethod
	def poll( cls, context ):
		return ( context.object is not None  and
				context.object.type == 'MESH' )

	def execute( self, context ):
		if not bpy.context.space_data.region_3d.is_perspective:
			self.report({'ERROR'}, "Can`t work in ORTHO mode")
			return {'CANCELLED'}
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		visibilitySelect(active_obj, active_mesh, context, 1, self.opt_rayFuzz )
		return {'FINISHED'}

class WPLvert_deselvisible( bpy.types.Operator ):
	bl_idname = "mesh.wplvert_deselvisible"
	bl_label = "Deselect visible verts"
	bl_options = {'REGISTER', 'UNDO'}
	opt_rayFuzz = bpy.props.FloatProperty(
		name		= "Fuzziness",
		default	 = 0.05
	)
	@classmethod
	def poll( cls, context ):
		return ( context.object is not None  and
				context.object.type == 'MESH' )

	def execute( self, context ):
		if not bpy.context.space_data.region_3d.is_perspective:
			self.report({'ERROR'}, "Can`t work in ORTHO mode")
			return {'CANCELLED'}
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		visibilitySelect(active_obj, active_mesh, context, 2, self.opt_rayFuzz )
		return {'FINISHED'}

class WPLvert_save2buff(bpy.types.Operator):
	bl_idname = "mesh.wplvert_save2buff"
	bl_label = "Save 2 buffer"
	bl_options = {'REGISTER', 'UNDO'}

	opt_action = EnumProperty(
		name="Action", default="SAVE",
		items=(("SAVE", "SAVE", ""), ("ADD", "ADD", ""), ("REM", "REM", ""))
	)

	@classmethod
	def poll(self, context):
		# Check if we have a mesh object active and are in vertex paint mode
		p = context.object and context.object.data and context.object.type == 'MESH'
		return p

	def execute(self, context):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		oldmode = select_and_change_mode(active_obj, 'OBJECT')
		seltoolsOpts = context.scene.seltoolsOpts
		bufMap = kWPLSelBufferUVMap+seltoolsOpts.sel_buff
		vg = getornew_vertgroup(active_obj,bufMap)
		#uv_layer_holdr = active_mesh.uv_textures.get(bufMap)
		#if uv_layer_holdr is None:
		#	active_mesh.uv_textures.new(bufMap)
		#bm = bmesh.from_edit_mesh(active_mesh)
		#bm.verts.ensure_lookup_table()
		#bm.faces.ensure_lookup_table()
		#bm.verts.index_update()
		#uv_layer_holdr = bm.loops.layers.uv.get(bufMap)
		#for face in bm.faces:
		#	for vert, loop in zip(face.verts, face.loops):
		#loop[uv_layer_holdr].uv = (float(vert.index),vert.select)
		ok_cnt = 0
		for vert in active_mesh.vertices:
			idx = vert.index
			wmod = 'REPLACE'
			try:
				oldval = vg.weight(idx)
			except Exception as e:
				wmod = 'ADD'
				oldval = 0
			selval = oldval
			if self.opt_action == "SAVE":
				selval = 0
				if vert.select:
					ok_cnt = ok_cnt+1
					selval = 1
			if self.opt_action == "ADD":
				selval = oldval
				if vert.select:
					ok_cnt = ok_cnt+1
					selval = 1
			if self.opt_action == "REM":
				selval = oldval
				if vert.select:
					ok_cnt = ok_cnt+1
					selval = 0
			newval = selval
			vg.add([idx], newval, wmod)
		select_and_change_mode(active_obj, oldmode)
		self.report({'INFO'}, str(ok_cnt)+" verts saved to "+seltoolsOpts.sel_buff)
		return {'FINISHED'}

class WPLvert_loadbuff(bpy.types.Operator):
	bl_idname = "mesh.wplvert_loadbuff"
	bl_label = "Load from buffer"
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
		seltoolsOpts = context.scene.seltoolsOpts
		bufMap = kWPLSelBufferUVMap+seltoolsOpts.sel_buff
		vg = getornew_vertgroup(active_obj,bufMap)
		bpy.ops.mesh.select_mode(type='VERT')
		#uv_layer_holdr = active_mesh.uv_textures.get(bufMap)
		#if uv_layer_holdr is None:
		#	active_mesh.uv_textures.new(bufMap)
		#bm = bmesh.from_edit_mesh(active_mesh)
		#bm.verts.ensure_lookup_table()
		#bm.faces.ensure_lookup_table()
		#bm.verts.index_update()
		#uv_layer_holdr = bm.loops.layers.uv.get(bufMap)
		#for face in bm.faces:
		#	for vert, loop in zip(face.verts, face.loops):
		#		selidx = int(loop[uv_layer_holdr].uv[0]+0.1)
		#		if abs(selidx-vert.index) < 0.5:
		#			selval = loop[uv_layer_holdr].uv[1]
		#			if selval>0:
		#				vert.select = True
		#				#verts2sel.append(vert.index)
		#bmesh.update_edit_mesh(active_mesh)
		select_and_change_mode(active_obj, 'OBJECT')
		for vert in active_mesh.vertices:
			idx = vert.index
			oldval = 0
			try:
				oldval = vg.weight(idx)
			except Exception as e:
				wmod = 'ADD'
				oldval = 0
			if oldval > 0.001:
				vert.select = True
		select_and_change_mode(active_obj, 'EDIT') # select proper faces, etc
		self.report({'INFO'}, "Selection state restored")
		return {'FINISHED'}

class WPLvert_floodsel( bpy.types.Operator ):
	bl_idname = "mesh.wplvert_floodsel"
	bl_label = "Flood-select linked"
	bl_options = {'REGISTER', 'UNDO'}
	opt_floodDir = FloatVectorProperty(
		name	 = "Flood direction",
		size	 = 3,
		min=-1.0, max=1.0,
		default	 = (0.0,0.0,1.0)
	)
	opt_floodDist = IntProperty(
		name	 = "Max Loops",
		default	 = 10
	)
	@classmethod
	def poll( cls, context ):
		return ( context.object is not None  and
				context.object.type == 'MESH' )

	def execute( self, context ):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		selverts = get_selected_vertsIdx(active_mesh)
		if len(selverts) == 0:
			self.report({'ERROR'}, "No selected verts found, select some")
			return {'CANCELLED'}
		select_and_change_mode(active_obj, 'EDIT')
		bpy.ops.mesh.select_mode(type="FACE")
		edit_obj = bpy.context.edit_object
		active_mesh = edit_obj.data
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		checked_verts = copy.copy(selverts)
		verts_shifts = {}
		floodDir = mathutils.Vector((self.opt_floodDir[0],self.opt_floodDir[1],self.opt_floodDir[2])).normalized()
		#propagation_stages = []
		opt_floodFuzz = 1.5
		for stage in range(1,self.opt_floodDist+1):
			stage_verts = {}
			checked_verts_cc = copy.copy(checked_verts)
			for v_idx in checked_verts_cc:
				if v_idx in selverts and stage>1:
					continue
				v = bm.verts[v_idx]
				for edg in v.link_edges:
					v2 = edg.other_vert(v)
					if v2.index not in checked_verts_cc:
						flowfir = (v2.co-v.co).normalized()
						flowdot = flowfir.dot(floodDir)
						flowang = math.acos(flowdot)
						if(flowang < opt_floodFuzz) or stage>1:
							active_mesh.vertices[v2.index].select = True
							v2.select = True
							if v2.index not in checked_verts:
								checked_verts.append(v2.index)
							if(v2.index not in stage_verts):
								stage_verts[v2.index] = []
							if v_idx not in stage_verts[v2.index]:
								stage_verts[v2.index].append(v_idx)
			if len(stage_verts) == 0:
				break
			#propagation_stages.append(stage_verts)
		#bmesh.update_edit_mesh( active_mesh )
		bpy.ops.mesh.select_mode(type="VERT")
		return {'FINISHED'}

class wplshsel_snap(bpy.types.Operator):
	bl_idname = "mesh.wplshsel_snap"
	bl_label = "Shrinkwrap selected to nearest"
	bl_options = {'REGISTER', 'UNDO'}

	opt_offset = bpy.props.FloatProperty(
		name		= "Offset",
		default	 	= 0.0
	)

	@classmethod
	def poll(self, context):
		# Check if we have a mesh object active and are in vertex paint mode
		p = context.object and context.object.data and context.object.type == 'MESH'
		return p

	def execute(self, context):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		vertsIdx = get_selected_vertsIdx(active_mesh)
		if len(vertsIdx) == 0:
			vertsIdx = [e.index for e in active_mesh.vertices]
		matrix_world = active_obj.matrix_world
		matrix_world_inv = active_obj.matrix_world.inverted()
		matrix_world_nrml = matrix_world_inv.transposed().to_3x3()
		nearObject = None
		nearObjectDist = 99999
		histVertlist = vertsIdx
		if(len(histVertlist) > 50):
			bm_tmp = bmesh.new()
			bm_tmp.from_mesh(active_mesh)
			bm_tmp.verts.index_update()
			histVertlist = [elem.index for elem in bm_tmp.select_history if isinstance(elem, bmesh.types.BMVert)]
			bm_tmp.free()
			if len(histVertlist) == 0:
				histVertlist = vertsIdx
			histVertlist = histVertlist[:50]
		for vIdx in histVertlist:
			s_v = active_mesh.vertices[vIdx]
			vFrom = matrix_world*s_v.co
			vDir = (matrix_world_nrml*s_v.normal)
			(result, loc_g, normal, index, obj, matrix) = bpy.context.scene.ray_cast(vFrom+vDir*kRaycastEpsilon, vDir)
			if result and obj.name != active_obj.name:
				resultDist = (loc_g-vFrom).length
				if resultDist<nearObjectDist:
					nearObject = obj
					nearObjectDist = resultDist
			vDir = -1*vDir
			(result, loc_g, normal, index, obj, matrix) = bpy.context.scene.ray_cast(vFrom+vDir*kRaycastEpsilon, vDir)
			if result and obj.name != active_obj.name:
				resultDist = (loc_g-vFrom).length
				if resultDist<nearObjectDist:
					nearObject = obj
					nearObjectDist = resultDist
		if nearObject is None:
			self.report({'ERROR'}, "No convinient target found")
			return {'CANCELLED'}
		modname = kWPLShrinkWrapMod
		bpy.ops.object.modifier_remove(modifier=modname)
		modifiers = active_obj.modifiers
		shrinkwrap_modifier = modifiers.new(name = modname, type = 'SHRINKWRAP')
		shrinkwrap_modifier.offset = self.opt_offset
		shrinkwrap_modifier.target = nearObject
		shrinkwrap_modifier.use_keep_above_surface = True
		#shrinkwrap_modifier.use_apply_on_spline = True
		shrinkwrap_modifier.wrap_method = 'NEAREST_SURFACEPOINT'

		vg_root = active_obj.vertex_groups.get(modname)
		if vg_root is not None:
			active_obj.vertex_groups.remove(vg_root)
		vg_root = active_obj.vertex_groups.new(modname)
		for vIdx in vertsIdx:
			updateVertWeight(vg_root, vIdx, 1.0, None)
		shrinkwrap_modifier.vertex_group = vg_root.name
		select_and_change_mode(active_obj,"EDIT")
		return {'FINISHED'}

class WPLvert_selvccol( bpy.types.Operator ):
	bl_idname = "mesh.wplvert_selvccol"
	bl_label = "Pick faces by Brush color"
	bl_options = {'REGISTER', 'UNDO'}
	opt_colFuzz = bpy.props.FloatProperty(
		name		= "HSV color distance",
		default	 = 0.1
	)
	@classmethod
	def poll( cls, context ):
		return ( context.object is not None  and
				context.object.type == 'MESH' and
				context.area.type == 'VIEW_3D') # and context.vertex_paint_object

	def current_brush(self, context):
		if context.area.type == 'VIEW_3D' and context.vertex_paint_object:
			brush = context.tool_settings.vertex_paint.brush
		elif context.area.type == 'VIEW_3D' and context.image_paint_object:
			brush = context.tool_settings.image_paint.brush
		elif context.area.type == 'IMAGE_EDITOR' and  context.space_data.mode == 'PAINT':
			brush = context.tool_settings.image_paint.brush
		else :
			brush = None
		return brush

	def execute( self, context ):
		seltoolsOpts = context.scene.seltoolsOpts
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		if active_mesh.vertex_colors.get(seltoolsOpts.bake_vcnm) is None:
			self.report({'ERROR'}, "Target VC not found")
			return {'CANCELLED'}
		oldmode = select_and_change_mode(active_obj,"OBJECT")
		#active_mesh.use_paint_mask = True
		#br = self.current_brush(context)
		#if br:
		#	basecol = Vector((br.color[0],br.color[1],br.color[2]))
		#else:
		basecol = Vector((seltoolsOpts.bake_vccol[0],seltoolsOpts.bake_vccol[1],seltoolsOpts.bake_vccol[2]))
		#color_map = active_mesh.vertex_colors.active
		color_map = active_mesh.vertex_colors.get(seltoolsOpts.bake_vcnm)
		active_mesh.vertex_colors.active = color_map
		vertx2sel = []
		for ipoly in range(len(active_mesh.polygons)):
			for idx, ivertex in enumerate(active_mesh.polygons[ipoly].loop_indices):
				ivdx = active_mesh.polygons[ipoly].vertices[idx]
				if (ivdx not in vertx2sel) and (color_map.data[ivertex].color is not None):
					vcol = color_map.data[ivertex].color
					dist = Vector((vcol[0],vcol[1],vcol[2]))
					if (dist-basecol).length <= self.opt_colFuzz:
						#print("Near color:",dist,basecol)
						vertx2sel.append(ivdx)
		for idx in vertx2sel:
			active_mesh.vertices[idx].select = True
		select_and_change_mode(active_obj,"EDIT")
		bpy.context.tool_settings.mesh_select_mode = (True, False, False)
		select_and_change_mode(active_obj,oldmode)
		return {'FINISHED'}

class WPLvert_pickvccol( bpy.types.Operator ):
	bl_idname = "mesh.wplvert_pickvccol"
	bl_label = "Pick VC color from selection"
	bl_options = {'REGISTER', 'UNDO'}
	@classmethod
	def poll( cls, context ):
		return ( context.object is not None  and
				context.object.type == 'MESH' and
				context.area.type == 'VIEW_3D') # and context.vertex_paint_object

	def current_brush(self, context):
		if context.area.type == 'VIEW_3D' and context.vertex_paint_object:
			brush = context.tool_settings.vertex_paint.brush
		elif context.area.type == 'VIEW_3D' and context.image_paint_object:
			brush = context.tool_settings.image_paint.brush
		elif context.area.type == 'IMAGE_EDITOR' and  context.space_data.mode == 'PAINT':
			brush = context.tool_settings.image_paint.brush
		else :
			brush = None
		return brush

	def execute( self, context ):
		seltoolsOpts = context.scene.seltoolsOpts
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		if active_mesh.vertex_colors.get(seltoolsOpts.bake_vcnm) is None:
			self.report({'ERROR'}, "Target VC not found")
			return {'CANCELLED'}
		oldmode = select_and_change_mode(active_obj,"OBJECT")
		selfaces = get_selected_facesIdx(active_mesh)
		select_and_change_mode(active_obj,"VERTEX_PAINT")
		if len(selfaces) < 1:
			self.report({'ERROR'}, "Not enough verts, select verts first")
			return {'CANCELLED'}
		#color_map = active_mesh.vertex_colors.active
		color_map = active_mesh.vertex_colors.get(seltoolsOpts.bake_vcnm)
		active_mesh.vertex_colors.active = color_map
		vertx2cols = None
		vertx2cnt = 0
		for ipoly in range(len(active_mesh.polygons)):
			if ipoly in selfaces:
				for idx, ivertex in enumerate(active_mesh.polygons[ipoly].loop_indices):
					ivdx = active_mesh.polygons[ipoly].vertices[idx]
					if vertx2cnt == 0:
						vertx2cols = mathutils.Vector(color_map.data[ivertex].color)
					else:
						vertx2cols = vertx2cols + mathutils.Vector(color_map.data[ivertex].color)
					vertx2cnt = vertx2cnt+1
		pickedcol = mathutils.Vector((vertx2cols[0],vertx2cols[1],vertx2cols[2]))/vertx2cnt
		seltoolsOpts.bake_vccol = (pickedcol[0],pickedcol[1],pickedcol[2])
		seltoolsOpts.bake_vccol_ref = seltoolsOpts.bake_vccol
		try:
			wplEdgeBuildProps = context.scene.wplEdgeBuildProps
			wplEdgeBuildProps.opt_edgeCol = seltoolsOpts.bake_vccol
		except:
			pass
		br = self.current_brush(context)
		if br:
			br.color = pickedcol
		select_and_change_mode(active_obj,oldmode)
		return {'FINISHED'}

class wplvert_islandsrnd(bpy.types.Operator):
	bl_idname = "mesh.wplvert_islandsrnd"
	bl_label = "Randomize colors"
	bl_options = {'REGISTER', 'UNDO'}

	opt_colorHueRnd = bpy.props.FloatProperty(
		name		= "Hue randomity",
		default	 = 0.0
	)
	opt_colorSatRnd = bpy.props.FloatProperty(
		name		= "Sat randomity",
		default	 = 0.0
	)
	opt_colorValRnd = bpy.props.FloatProperty(
		name		= "Val randomity",
		default	 = 1.0
	)

	@classmethod
	def poll(self, context):
		# Check if we have a mesh object active and are in vertex paint mode
		p = context.object and context.object.data and (isinstance(context.scene.objects.active, bpy.types.Object) and isinstance(context.scene.objects.active.data, bpy.types.Mesh))
		return p

	def execute(self, context):
		print("execute ", self.bl_idname)
		active_obj = context.scene.objects.active
		if active_obj is None:
			self.report({'ERROR'}, "No active object found")
			return {'CANCELLED'}
		active_mesh = active_obj.data
		selfaces = get_selected_facesIdx(active_mesh)
		if len(selfaces) == 0:
			self.report({'ERROR'}, "No faces selected, select some faces first")
			return {'CANCELLED'}
		bpy.ops.object.mode_set(mode='EDIT')

		seltoolsOpts = context.scene.seltoolsOpts
		if active_mesh.vertex_colors.get(seltoolsOpts.bake_vcnm) is None:
			self.report({'ERROR'}, "Target VC not found")
			return {'CANCELLED'}

		bm = bmesh.new()
		bm.from_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		vc_randomies = {}
		selverts = []
		for v in bm.verts:
			v.tag = False
		for face in bm.faces:
			face_is_selected = face.index in selfaces
			if face_is_selected:
				for vert, loop in zip(face.verts, face.loops):
					selverts.append(vert.index)
		print("Faces selected:", len(selfaces), "; Vertices selected:", len(selverts))
		for v in bm.verts:
			if v.tag == False:
				meshlist = []
				addConnectedBmVerts_v02(1, bm, v, meshlist, selverts)
				if len(meshlist) > 0:
					rndc = (random(),random(),random(),1.0)
					for ov in meshlist:
						vc_randomies[ov.index] = rndc
		bpy.ops.object.mode_set(mode='OBJECT')
		context.scene.update()
		color_map = active_obj.data.vertex_colors.get(seltoolsOpts.bake_vcnm)
		active_mesh.vertex_colors.active = color_map
		if len(vc_randomies)>0:
			for poly in active_mesh.polygons:
				face_is_selected = poly.index in selfaces
				if face_is_selected:
					ipoly = poly.index
					for idx, ivertex in enumerate(active_mesh.polygons[ipoly].loop_indices):
						ivdx = active_mesh.polygons[ipoly].vertices[idx]
						if (ivdx in vc_randomies):
							rndms = vc_randomies[ivdx]
							curcolor = mathutils.Color((color_map.data[ivertex].color[0],color_map.data[ivertex].color[1],color_map.data[ivertex].color[2]))
							newHmin = max(0.0,curcolor.h-self.opt_colorHueRnd)
							newHmax = min(1.0,curcolor.h+self.opt_colorHueRnd)
							newSmin = max(0.0,curcolor.s-self.opt_colorSatRnd)
							newSmax = min(1.0,curcolor.s+self.opt_colorSatRnd)
							newVmin = max(0.0,curcolor.v-self.opt_colorValRnd)
							newVmax = min(1.0,curcolor.v+self.opt_colorValRnd)
							newcolor = curcolor.copy()
							newcolor.hsv = (newHmin+rndms[0]*(newHmax-newHmin),newSmin+rndms[1]*(newSmax-newSmin),newVmin+rndms[2]*(newVmax-newVmin))
							color_map.data[ivertex].color = (newcolor[0],newcolor[1],newcolor[2],1.0)
		bpy.ops.object.mode_set(mode='VERTEX_PAINT')
		context.scene.update()
		return {'FINISHED'}

class WPLvert_updcol( bpy.types.Operator ):
	bl_idname = "mesh.wplvert_updcol"
	bl_label = "Update color"
	bl_options = {'REGISTER', 'UNDO'}
	opt_target = EnumProperty(
		name="Target", default="FACE",
		items=(("FACE", "FACE", ""), ("VERT", "VERT", ""), ("PROP", "Custom prop", ""))
	)
	opt_influence = FloatProperty(
		name="Influence",
		min=0.0001, max=1.0,
		default=1
	)
	opt_insetLoops = IntProperty(
		name="Smoothing Loops",
		min=0, max=10000,
		default=0
	)
	opt_invertInfl = BoolProperty(
		name="Invert Influence",
		default=False
	)
	@classmethod
	def poll( cls, context ):
		p = (isinstance(context.scene.objects.active, bpy.types.Object))
		return p

	def execute( self, context ):
		seltoolsOpts = context.scene.seltoolsOpts
		def newColorWith(col,vert2loopMap):
			oldcolor = Vector((col[0],col[1],col[2],1))
			if seltoolsOpts.bake_vccol_mask[0]:
				R = seltoolsOpts.bake_vccol[0]
			else:
				R = oldcolor[0]
			if seltoolsOpts.bake_vccol_mask[1]:
				G = seltoolsOpts.bake_vccol[1]
			else:
				G = oldcolor[1]
			if seltoolsOpts.bake_vccol_mask[2]:
				B = seltoolsOpts.bake_vccol[2]
			else:
				B = oldcolor[2]
			newcolor = Vector((R,G,B,1))
			dopinfluence = 1.0
			if vert2loopMap is not None and ivdx in vert2loopMap:
				dopinfluence = vert2loopMap[ivdx]
			tltInfl = self.opt_influence*dopinfluence
			if self.opt_invertInfl:
				tltInfl = 1.0-tltInfl
			lerped = oldcolor.lerp(newcolor,tltInfl)
			return lerped
		active_obj = context.scene.objects.active
		if active_obj is None or len(seltoolsOpts.bake_vcnm) == 0:
			return {'CANCELLED'}
		seltoolsOpts.bake_vccol_ref = seltoolsOpts.bake_vccol
		if self.opt_target == 'PROP' or active_obj.type == 'CURVE':
			prop_name = seltoolsOpts.bake_vcnm #"vc_"+seltoolsOpts.bake_vcnm
			lerped = newColorWith((0,0,0),None)
			active_obj[prop_name] = lerped
			return {'FINISHED'}
		active_mesh = active_obj.data
		if active_mesh.vertex_colors.get(seltoolsOpts.bake_vcnm) is None and len(seltoolsOpts.bake_vcnm) == 0:
			self.report({'ERROR'}, "Target VC not found")
			return {'CANCELLED'}
		oldmode = select_and_change_mode(active_obj,"OBJECT")
		selfaces = get_selected_facesIdx(active_mesh)
		selverts = get_selected_vertsIdx(active_mesh)
		if (self.opt_target == 'FACE' and len(selfaces) == 0) or (self.opt_target == 'VERT' and len(selverts) == 0):
			#self.report({'ERROR'}, "No faces selected, select some faces first")
			#return {'CANCELLED'}
			selfaces = [f.index for f in active_mesh.polygons]
			selverts = [e.index for e in active_mesh.vertices]
		vert2loopMap = None
		if self.opt_insetLoops>0:
			selvertsCpy = set(copy.copy(selverts))
			vert2loopMap = get_less_vertsMap_v01(active_obj, selvertsCpy, self.opt_insetLoops)
			for vIdx in selverts:
				vert2loopMap[vIdx] = (vert2loopMap[vIdx]-1.0)/float(self.opt_insetLoops)
		color_map = active_mesh.vertex_colors.get(seltoolsOpts.bake_vcnm)
		if color_map is None:
			color_map = active_mesh.vertex_colors.new(seltoolsOpts.bake_vcnm)
		active_mesh.vertex_colors.active = color_map
		setCount = 0
		for poly in active_mesh.polygons:
			ipoly = poly.index
			if (self.opt_target == 'VERT') or (ipoly in selfaces):
				for idx, ivertex in enumerate(active_mesh.polygons[ipoly].loop_indices):
					ivdx = active_mesh.polygons[ipoly].vertices[idx]
					if (self.opt_target == 'FACE') or (ivdx in selverts):
						col = color_map.data[ivertex].color
						lerped = newColorWith(col,vert2loopMap)
						setCount = setCount+1
						#print("Colors",oldcolor,newcolor,lerped,self.opt_influence,dopinfluence)
						color_map.data[ivertex].color = lerped
		select_and_change_mode(active_obj,oldmode)
		self.report({'INFO'}, color_map.name+': verts='+str(setCount))
		return {'FINISHED'}

######################### ######################### #########################
######################### ######################### #########################
def onUpdate_bake_vcnm_real(self, context):
	seltoolsOpts = context.scene.seltoolsOpts
	if len(seltoolsOpts.bake_vcnm_real)>0:
		seltoolsOpts.bake_vcnm = seltoolsOpts.bake_vcnm_real
		seltoolsOpts.bake_vcnm_real = ""

class WPLSelToolsSettings(bpy.types.PropertyGroup):
	sel_buff = EnumProperty(
		name="Selection Buffer",
		items = [
			('BUFFER1', "Buffer 1", ""),
			('BUFFER2', "Buffer 2", ""),
			('BUFFER3', "Buffer 3", "")
		],
		default='BUFFER1',
	)
	bake_vccol = FloatVectorProperty(
		name="VC Color",
		subtype='COLOR_GAMMA',
		min=0.0, max=1.0,
		default = (1.0,1.0,1.0)
		)
	bake_vccol_ref = FloatVectorProperty(
		name="Raw",
		subtype='COLOR',
		min=0.0, max=1.0,
		default = (1.0,1.0,1.0)
		)
	bake_vccol_ref_d1 = FloatVectorProperty(
		name="W",
		subtype='COLOR_GAMMA',
		default = (1.0,1.0,1.0)
		)
	bake_vccol_ref_d2 = FloatVectorProperty(
		name="B",
		subtype='COLOR_GAMMA',
		default = (0.0,0.0,0.0)
		)
	bake_vccol_ref_d3 = FloatVectorProperty(
		name="R",
		subtype='COLOR_GAMMA',
		default = (1.0,0.0,0.0)
		)
	bake_vccol_ref_d4 = FloatVectorProperty(
		name="G",
		subtype='COLOR_GAMMA',
		default = (0.0,1.0,0.0)
		)
	bake_vccol_ref_d5 = FloatVectorProperty(
		name="B",
		subtype='COLOR_GAMMA',
		default = (0.0,0.0,1.0)
		)
	bake_vccol_mask = BoolVectorProperty(
		name="Color Mask",
		size = 3,
		default = (True,True,True)
		)
	bake_vcnm = StringProperty(
		name="Target VC",
		default = ""
		)
	bake_vcnm_real = StringProperty(
		name="VC",
		default = "",
		update=onUpdate_bake_vcnm_real
		)

class WPLSelectFeatures_Panel1(bpy.types.Panel):
	bl_label = "Selection helpers"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_category = 'WPL'

	def draw_header(self, context):
		layout = self.layout
		layout.label(text="")

	def draw(self, context):
		layout = self.layout
		col = layout.column()
		seltoolsOpts = context.scene.seltoolsOpts

		col.separator()
		col.label("Selection control")
		col.operator("mesh.wplvert_selvisible", text="Select visible")
		col.operator("mesh.wplvert_deselvisible", text="Deselect visible")
		col.operator("mesh.wplvert_deselunvisible", text="Deselect invisible")
		col.separator()
		col.operator("mesh.wplvert_floodsel", text="Flood-select linked")
		col.operator("mesh.wplshsel_snap", text="Shrinkwrap selected to nearest")

		col.separator()
		col.prop(seltoolsOpts, "sel_buff")
		row = col.row()
		row.operator("mesh.wplvert_save2buff", text="Save").opt_action = 'SAVE'
		row.operator("mesh.wplvert_save2buff", text="Add").opt_action = 'ADD'
		row.operator("mesh.wplvert_save2buff", text="Rem").opt_action = 'REM'
		col.operator("mesh.wplvert_loadbuff", text="Load from buffer")


class WPLPaintSelect_Panel(bpy.types.Panel):
	bl_label = "VC helpers"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_category = 'WPL'

	def draw_header(self, context):
		layout = self.layout
		layout.label(text="")

	def draw(self, context):
		layout = self.layout
		seltoolsOpts = context.scene.seltoolsOpts
		active_obj = context.scene.objects.active
		col = layout.column()

		if active_obj is not None and active_obj.data is not None:
			obj_data = active_obj.data
			if obj_data is not None:
				row0 = col.row()
				row0.prop(seltoolsOpts, "bake_vcnm")
				row0.prop_search(seltoolsOpts, "bake_vcnm_real", obj_data, "vertex_colors", icon='GROUP_VCOL')
				col.prop(seltoolsOpts, "bake_vccol")
				row1 = col.row()
				row1.prop(seltoolsOpts, "bake_vccol_mask", text = "R,G,B")
				row2 = col.row()
				row2.operator("mesh.wplvert_updcol", text="->Faces").opt_target = 'FACE'
				row2.operator("mesh.wplvert_updcol", text="->Verts").opt_target = 'VERT'

		col.separator()
		col.operator("mesh.wplvert_pickvccol", text="Pick color from faces")
		col.operator("mesh.wplvert_selvccol", text="Mesh: Select faces by color")
		col.operator("mesh.wplvert_islandsrnd", text="Islands: Randomize color")
		col.separator()
		row3 = col.row()
		row3.prop(seltoolsOpts, "bake_vccol_ref")
		row3.prop(seltoolsOpts, "bake_vccol_ref_d1")
		row3.prop(seltoolsOpts, "bake_vccol_ref_d2")
		row4 = col.row()
		row4.prop(seltoolsOpts, "bake_vccol_ref_d3")
		row4.prop(seltoolsOpts, "bake_vccol_ref_d4")
		row4.prop(seltoolsOpts, "bake_vccol_ref_d5")

def register():
	print("WPLSelectFeatures_Panel registered")
	bpy.utils.register_module(__name__)
	bpy.types.Scene.seltoolsOpts = PointerProperty(type=WPLSelToolsSettings)

def unregister():
	bpy.utils.unregister_module(__name__)
	bpy.utils.unregister_class(WPLSelToolsSettings)

if __name__ == "__main__":
	register()
