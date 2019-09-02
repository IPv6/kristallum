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
	"name": "Prop VC Tools",
	"author": "IPv6",
	"version": (1, 2, 9),
	"blender": (2, 7, 9),
	"location": "View3D > T-panel > WPL",
	"description" : "",
	"warning"	 : "",
	"wiki_url"	: "",
	"tracker_url" : "",
	"category"	: "WPL"
	}


kRaycastEpsilon = 0.0001
kWPLPalIslUVPostfix = "_pal"

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
def getVertWeightMap(active_obj, vgname):
	weights = {}
	vgroup = active_obj.vertex_groups.get(vgname)
	if vgroup is not None:
		for index, vert in enumerate(active_obj.data.vertices):
			for group in vert.groups:
				if group.group == vgroup.index:
					weights[index] = group.weight
	return weights

def getBmVertGeodesicDistmap_v04(bme, step_vIdx, maxloops, maxdist, ignoreHidden, limitWalk2verts):
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
			for f in v.link_faces:
				for fv in f.verts:
					if ignoreHidden == True and fv.hide != 0:
						continue
					if limitWalk2verts is not None and fv.index not in limitWalk2verts:
						continue
					if fv.index not in vertStepMap:
						fv_dist = vertDistMap[vIdx]+(fv.co-v.co).length
						if fv.index not in vertDistMap:
							vertDistMap[fv.index] = fv_dist
							vertOriginMap[fv.index] = vertOriginMap[vIdx]
							if fv_dist <= maxdist:
								nextStepIdx[fv.index] = vIdx
						elif vertDistMap[fv.index] > fv_dist:
							vertDistMap[fv.index] = fv_dist
							vertOriginMap[fv.index] = vertOriginMap[vIdx]
							if fv_dist <= maxdist:
								nextStepIdx[fv.index] = vIdx
		print("- step",curStep+1,len(step_vIdx),len(nextStepIdx))
		step_vIdx = []
		for vIdxNext in nextStepIdx:
			step_vIdx.append(vIdxNext)
		if len(step_vIdx) == 0:
			break
	return vertDistMap, vertOriginMap

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
	vctoolsOpts = context.scene.vctoolsOpts
	vctoolsOpts.bake_vc_col = (newcol[0],newcol[1],newcol[2])
	try:
		wplEdgeBuildProps = context.scene.wplEdgeBuildProps
		wplEdgeBuildProps.opt_edgeCol = vctoolsOpts.bake_vc_col
	except:
		pass
	br = getActiveBrush(context)
	if br:
		br.color = mathutils.Vector((newcol[0],newcol[1],newcol[2]))
		
def modfGetByType(c_object,modType):
	for md in c_object.modifiers:
		if md.type == modType: #'SUBSURF'
			return md
	return None
	
def getAvgColor(active_mesh, bake_vcnm, selfaces):
	if selfaces is None or len(selfaces) == 0:
		return (None, None,None,0)
	color_map = active_mesh.vertex_colors.get(bake_vcnm)
	palette_map = active_mesh.uv_layers.get(bake_vcnm+kWPLPalIslUVPostfix)
	colpal = 0
	colisl = 0
	colpalislIsFound = False
	vertx2cols = None
	vertx2cnt = 0
	for ipoly in range(len(active_mesh.polygons)):
		if ipoly in selfaces:
			for idx, lIdx in enumerate(active_mesh.polygons[ipoly].loop_indices):
				if colpalislIsFound == False and palette_map is not None:
					colpalislIsFound = True
					pal = palette_map.data[lIdx].uv
					colpal = pal[0]
					colisl = pal[1]
				if vertx2cols is None:
					vertx2cols = mathutils.Vector(color_map.data[lIdx].color)
				else:
					vertx2cols = vertx2cols + mathutils.Vector(color_map.data[lIdx].color)
				vertx2cnt = vertx2cnt+1
	pickedcol = mathutils.Vector((vertx2cols[0],vertx2cols[1],vertx2cols[2],vertx2cols[3]))/vertx2cnt
	print("- picked", pickedcol,"on",vertx2cnt)
	return (pickedcol, colpal, colisl, vertx2cnt)
########### ############ ########### ############ ########### ############ ########### ############
########### ############ ########### ############ ########### ############ ########### ############
class wplvcop_selvccol( bpy.types.Operator ):
	bl_idname = "mesh.wplvcop_selvccol"
	bl_label = "Pick by color/palette"
	bl_options = {'REGISTER', 'UNDO'}
	opt_target = EnumProperty(
		name="Target", default="COLORBR",
		items=(('COLORBR', "COLORBR", ""), ('COLORSL', "COLORSL", ""), ('PALETTE', "PALETTE", ""), ('ISLAND', "ISLAND", ""))
	)
	opt_colFuzz = bpy.props.FloatProperty(
		name	= "Color distance (HSV/PaletteId)",
		default	= 0.1
	)
	@classmethod
	def poll( cls, context ):
		return ( context.object is not None and context.object.type == 'MESH') # and context.area.type == 'VIEW_3D'

	def execute( self, context ):
		vctoolsOpts = context.scene.vctoolsOpts
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		if active_mesh.vertex_colors.get(vctoolsOpts.bake_vcnm) is None:
			self.report({'ERROR'}, "Target VC not found")
			return {'CANCELLED'}
		oldmode = select_and_change_mode(active_obj,"OBJECT")
		basecol = Vector((vctoolsOpts.bake_vc_col[0],vctoolsOpts.bake_vc_col[1],vctoolsOpts.bake_vc_col[2]))
		if self.opt_target == 'COLORSL':
			selfaces = get_selected_facesIdx(active_mesh)
			pickedcol, colpal, colisl, vertx2cnt = getAvgColor(active_mesh, vctoolsOpts.bake_vcnm, selfaces)
			basecol = Vector((pickedcol[0],pickedcol[1],pickedcol[2]))
		basepal = float(vctoolsOpts.bake_vc_plt)
		baseisl = float(vctoolsOpts.bake_vc_isl)
		palette_map = active_mesh.uv_layers.get(vctoolsOpts.bake_vcnm+kWPLPalIslUVPostfix)
		color_map = active_mesh.vertex_colors.get(vctoolsOpts.bake_vcnm)
		active_mesh.vertex_colors.active = color_map
		vertx2sel = []
		facex2sel = []
		for ipoly in range(len(active_mesh.polygons)):
			for idx, lIdx in enumerate(active_mesh.polygons[ipoly].loop_indices):
				ivdx = active_mesh.polygons[ipoly].vertices[idx]
				if (ivdx not in vertx2sel) and (ipoly not in facex2sel):
					if (self.opt_target == 'COLORBR' or self.opt_target == 'COLORSL') and (color_map.data[lIdx].color is not None):
						vcol = color_map.data[lIdx].color
						dist = Vector((vcol[0],vcol[1],vcol[2]))
						if (dist-basecol).length <= self.opt_colFuzz:
							vertx2sel.append(ivdx)
					if self.opt_target == 'PALETTE' and palette_map is not None:
						dist = palette_map.data[lIdx].uv[0]
						if abs(dist-basepal) <= self.opt_colFuzz:
							facex2sel.append(ipoly)
					if self.opt_target == 'ISLAND' and palette_map is not None:
						dist = palette_map.data[lIdx].uv[1]
						if abs(dist-baseisl) <= self.opt_colFuzz:
							facex2sel.append(ipoly)
		select_and_change_mode(active_obj,"OBJECT")
		selfaces = 0;
		selverts = 0;
		if len(vertx2sel)>0:
			for idx in vertx2sel:
				active_mesh.vertices[idx].select = True
				selverts = selverts+1
		if len(facex2sel)>0:
			for idx in facex2sel:
				active_mesh.polygons[idx].select = True
				selfaces = selfaces+1
		select_and_change_mode(active_obj,"EDIT")
		if len(vertx2sel)>0:
			bpy.ops.mesh.select_mode(type='VERT')
		if len(facex2sel)>0:
			bpy.ops.mesh.select_mode(type="FACE")
		if oldmode != 'OBJECT':
			select_and_change_mode(active_obj,oldmode)
		self.report({'INFO'}, 'Selected verts='+str(selverts)+' faces='+str(selfaces))
		return {'FINISHED'}

class wplvcop_resetvc( bpy.types.Operator ):
	bl_idname = "mesh.wplvcop_resetvc"
	bl_label = "Reset color to palette"
	bl_options = {'REGISTER', 'UNDO'}
	opt_resetIdx = IntProperty(
		name="Pallete id",
		min=0, max=10,
		default=0
	)
	def execute( self, context ):
		vctoolsOpts = context.scene.vctoolsOpts
		predefsCols = [vctoolsOpts.bake_vc_col_ref_d0,vctoolsOpts.bake_vc_col_ref_d1,vctoolsOpts.bake_vc_col_ref_d2,vctoolsOpts.bake_vc_col_ref_d3,vctoolsOpts.bake_vc_col_ref_d4,vctoolsOpts.bake_vc_col_ref_d5,vctoolsOpts.bake_vc_col_ref_d6,vctoolsOpts.bake_vc_col_ref_d7,vctoolsOpts.bake_vc_col_ref_d8]
		if self.opt_resetIdx-1 < len(predefsCols):
			vctoolsOpts.bake_vc_plt = self.opt_resetIdx
			vctoolsOpts.bake_vc_col = predefsCols[self.opt_resetIdx-1]
		return {'FINISHED'}
	
class wplvcop_cppaste( bpy.types.Operator ):
	bl_idname = "mesh.wplvcop_cppaste"
	bl_label = "Copy/Paste VC"
	bl_options = {'REGISTER', 'UNDO'}
	opt_op = EnumProperty(
		name="Operation", default="COPY",
		items=(('COPY', "COPY", ""), ('PASTE', "PASTE", ""))
	)
	@classmethod
	def poll( cls, context ):
		return ( context.object is not None and context.object.type == 'MESH')

	def execute( self, context ):
		sel_all = []
		for sel_obj in bpy.context.selected_objects:
			sel_all.append(sel_obj)
		vctoolsOpts = context.scene.vctoolsOpts
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		oldmode = select_and_change_mode(active_obj,"OBJECT")
		selfaces = get_selected_facesIdx(active_mesh)
		kVCStoreKey = "vcCopyPaste"
		if self.opt_op == 'COPY':
			if len(selfaces) < 1:
				self.report({'ERROR'}, "Select faces first")
				return {'CANCELLED'}
			faceDescr = {}
			faceDescr['obj_name'] = active_obj.name
			for ipoly in range(len(active_mesh.polygons)):
				if ipoly in selfaces:
					faceDescr['material_index'] = active_mesh.polygons[ipoly].material_index
					faceDescr['material_name'] = active_obj.material_slots[faceDescr['material_index']].name
					faceDescr['colors'] = {}
					for idx, lIdx in enumerate(active_mesh.polygons[ipoly].loop_indices):
						ivdx = active_mesh.polygons[ipoly].vertices[idx]
						for vc in active_mesh.vertex_colors:
							col = vc.data[lIdx].color
							pickedcol = Vector((col[0], col[1], col[2]))
							faceDescr['colors'][vc.name] = pickedcol
							if vc.name == vctoolsOpts.bake_vcnm:
								setActiveBrushColor(context, pickedcol)
					break
			WPL_G.store[kVCStoreKey] = faceDescr
			print('COPY:',faceDescr)
			self.report({'INFO'}, 'COPY: Done')
		if self.opt_op == 'PASTE':
			if kVCStoreKey not in WPL_G.store:
				self.report({'ERROR'}, "Nothing copied")
				return {'CANCELLED'}
			faceDescr = copy.copy(WPL_G.store[kVCStoreKey])
			if len(sel_all) > 1:
				selfaces = None #ignored
			facespasted = 0
			objpasted = 0
			for sel_obj in sel_all:
				if sel_obj.type=='MESH':
					sel_mesh = sel_obj.data
					objpasted = objpasted+1
					if faceDescr['obj_name'] != sel_obj.name:
						# checking materials, VCS, adding missing
						isMatFound = False
						for idx,mt in enumerate(sel_obj.material_slots):
							if mt.name == faceDescr['material_name']:
								isMatFound = True
								faceDescr['material_index'] = idx
								break
						if isMatFound == False:
							#adding material
							mt = bpy.data.materials.get(faceDescr['material_name'])
							if mt is None:
								self.report({'ERROR'}, "Unknown material")
								return {'CANCELLED'}
							sel_obj.data.materials.append(mt)
							faceDescr['material_index'] = len(sel_obj.material_slots)-1
					facescolors = faceDescr['colors']
					for cl_name in facescolors:
						if sel_mesh.vertex_colors.get(cl_name) is None:
							sel_mesh.vertex_colors.new(cl_name)
					for ipoly in range(len(sel_mesh.polygons)):
						if (selfaces is None) or (ipoly in selfaces):
							sel_mesh.polygons[ipoly].material_index = faceDescr['material_index']
							facespasted = facespasted+1
							for idx, lIdx in enumerate(sel_mesh.polygons[ipoly].loop_indices):
								ivdx = sel_mesh.polygons[ipoly].vertices[idx]
								for vc in sel_mesh.vertex_colors:
									if vc.name in facescolors:
										col = facescolors[vc.name]
										vc.data[lIdx].color = (col[0],col[1],col[2],1.0)
			self.report({'INFO'}, 'PASTE: Done, faces='+str(facespasted)+' in '+str(objpasted)+' obj')
		return {'FINISHED'}

class wplvcop_pickvccol( bpy.types.Operator ):
	bl_idname = "mesh.wplvcop_pickvccol"
	bl_label = "Pick color from faces"
	bl_options = {'REGISTER', 'UNDO'}
	@classmethod
	def poll( cls, context ):
		return ( context.object is not None and context.object.type == 'MESH') #and context.area.type == 'VIEW_3D') # and context.vertex_paint_object

	def execute( self, context ):
		vctoolsOpts = context.scene.vctoolsOpts
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		if active_mesh.vertex_colors.get(vctoolsOpts.bake_vcnm) is None:
			self.report({'ERROR'}, "Target VC not found")
			return {'CANCELLED'}
		oldmode = select_and_change_mode(active_obj,"OBJECT")
		selfaces = get_selected_facesIdx(active_mesh)
		select_and_change_mode(active_obj,"VERTEX_PAINT")
		if len(selfaces) < 1:
			self.report({'ERROR'}, "Select faces first")
			return {'CANCELLED'}
		print("- picking from", len(selfaces),"faces on",active_obj.name,"for",vctoolsOpts.bake_vcnm)
		color_map = active_mesh.vertex_colors.get(vctoolsOpts.bake_vcnm)
		active_mesh.vertex_colors.active = color_map
		pickedcol, colpal, colisl, vertx2cnt = getAvgColor(active_mesh, vctoolsOpts.bake_vcnm, selfaces)
		vctoolsOpts.bake_vc_plt = colpal
		vctoolsOpts.bake_vc_isl = colisl
		setActiveBrushColor(context, pickedcol) #after bake_vc_plt!!!
		select_and_change_mode(active_obj, oldmode)
		self.report({'INFO'}, 'Picked from verts='+str(vertx2cnt))
		return {'FINISHED'}

class wplvcop_islandsmid(bpy.types.Operator):
	bl_idname = "mesh.wplvcop_islandsmid"
	bl_label = "Setup Islands"
	bl_options = {'REGISTER', 'UNDO'}

	opt_targetVc = StringProperty(
		name="Target VC",
		default = "Islands"
	)
	opt_targetUV = StringProperty(
		name="Target UV",
		default = ""
	)

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
		vctoolsOpts = context.scene.vctoolsOpts

		out_VCName = self.opt_targetVc
		if len(out_VCName) == 0:
			out_VCName = vctoolsOpts.bake_vcnm

		out_UVName = self.opt_targetUV
		if len(out_UVName) == 0:
			out_UVName = vctoolsOpts.bake_vcnm+kWPLPalIslUVPostfix

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
		islandId = 0
		selVertsIslandsed = splitBmVertsByLinks_v02(bm, selverts, False)
		for meshlist in selVertsIslandsed:
			if len(meshlist)>0:
				islandId = islandId+1.0
				for vidx in meshlist:
					islandPerVert[vidx] = islandId
		bpy.ops.object.mode_set(mode='OBJECT')

		palette_mapvc = active_obj.data.vertex_colors.get(out_VCName)
		if palette_mapvc is None:
			palette_mapvc = active_mesh.vertex_colors.new(out_VCName)
		if palette_mapvc is not None and len(islandPerVert)>0:
			for poly in active_mesh.polygons:
				ipoly = poly.index
				for idx, lIdx in enumerate(active_mesh.polygons[ipoly].loop_indices):
					ivdx = active_mesh.polygons[ipoly].vertices[idx]
					if (ivdx in islandPerVert):
						islfrac = islandPerVert[ivdx]
						newcolor = Vector((0.1+0.95*(islfrac/islandId), 0.95-0.9*(islfrac/islandId), 0.5+0.45*islfrac/islandId))
						palette_mapvc.data[lIdx].color = (newcolor[0],newcolor[1],newcolor[2],1.0)

		palette_mapuv = active_mesh.uv_layers.get(out_UVName)
		if palette_mapuv is not None and len(islandPerVert)>0:
			for poly in active_mesh.polygons:
				ipoly = poly.index
				for idx, lIdx in enumerate(active_mesh.polygons[ipoly].loop_indices):
					ivdx = active_mesh.polygons[ipoly].vertices[idx]
					if (ivdx in islandPerVert):
						islfrac = islandPerVert[ivdx]
						palette_mapuv.data[lIdx].uv = Vector((palette_mapuv.data[lIdx].uv[0],islfrac))
			
		self.report({'INFO'}, 'Islands found='+str(islandId))
		context.scene.update()
		return {'FINISHED'}

class wplvcop_islandsrnd(bpy.types.Operator):
	bl_idname = "mesh.wplvcop_islandsrnd"
	bl_label = "Randomize colors"
	bl_options = {'REGISTER', 'UNDO'}
	opt_target = EnumProperty(
		name="Target", default="SEL",
		items=(('SEL', "Active selection", ""), ('BRUSH', "Active brush", ""))
	)
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
		p = context.object and context.object.data and (isinstance(context.scene.objects.active, bpy.types.Object) and isinstance(context.scene.objects.active.data, bpy.types.Mesh))
		return p

	def randCol(self, oldcol,rndms):
		curcolor = mathutils.Color((oldcol[0],oldcol[1],oldcol[2]))
		newHmin = max(0.0,curcolor.h-self.opt_colorHueRnd)
		newHmax = min(1.0,curcolor.h+self.opt_colorHueRnd)
		newSmin = max(0.0,curcolor.s-self.opt_colorSatRnd)
		newSmax = min(1.0,curcolor.s+self.opt_colorSatRnd)
		newVmin = max(0.0,curcolor.v-self.opt_colorValRnd)
		newVmax = min(1.0,curcolor.v+self.opt_colorValRnd)
		newcolor = curcolor.copy()
		newcolor.hsv = (newHmin+rndms[0]*(newHmax-newHmin),newSmin+rndms[1]*(newSmax-newSmin),newVmin+rndms[2]*(newVmax-newVmin))
		return newcolor

	def execute(self, context):
		vctoolsOpts = context.scene.vctoolsOpts
		active_obj = context.scene.objects.active
		if active_obj is None:
			self.report({'ERROR'}, "No active object found")
			return {'CANCELLED'}
		if self.opt_target == 'BRUSH':
			rndc = (random(),random(),random())
			newcolor = self.randCol(vctoolsOpts.bake_vc_col,rndc)
			setActiveBrushColor(context, newcolor)
			return {'FINISHED'}
		active_mesh = active_obj.data
		selfaces = get_selected_facesIdx(active_mesh)
		if len(selfaces) == 0:
			self.report({'ERROR'}, "No faces selected, select some faces first")
			return {'CANCELLED'}
		bpy.ops.object.mode_set(mode='EDIT')

		if active_mesh.vertex_colors.get(vctoolsOpts.bake_vcnm) is None:
			self.report({'ERROR'}, "Target VC not found")
			return {'CANCELLED'}

		bm = bmesh.new()
		bm.from_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		vc_randomies = {}
		selverts = []
		for face in bm.faces:
			face_is_selected = face.index in selfaces
			if face_is_selected:
				for vert, loop in zip(face.verts, face.loops):
					selverts.append(vert.index)
		print("Faces selected:", len(selfaces), "; Vertices selected:", len(selverts))
		selVertsIslandsed = splitBmVertsByLinks_v02(bm, selverts, False)
		for meshlist in selVertsIslandsed:
			if len(meshlist)>0:
				rndc = (random(),random(),random(),1.0)
				for vidx in meshlist:
					vc_randomies[vidx] = rndc
		bpy.ops.object.mode_set(mode='OBJECT')
		color_map = active_obj.data.vertex_colors.get(vctoolsOpts.bake_vcnm)
		active_mesh.vertex_colors.active = color_map
		if len(vc_randomies)>0:
			for poly in active_mesh.polygons:
				face_is_selected = poly.index in selfaces
				if face_is_selected:
					ipoly = poly.index
					for idx, lIdx in enumerate(active_mesh.polygons[ipoly].loop_indices):
						ivdx = active_mesh.polygons[ipoly].vertices[idx]
						if (ivdx in vc_randomies):
							rndms = vc_randomies[ivdx]
							newcolor = self.randCol(color_map.data[lIdx].color,rndms)
							color_map.data[lIdx].color = (newcolor[0],newcolor[1],newcolor[2],1.0)
		bpy.ops.object.mode_set(mode='VERTEX_PAINT')
		context.scene.update()
		return {'FINISHED'}

def updateObjVC(targetObj,method,vcName,newcol,newpal,newisl,colmask,infl,infl4vert,selverts,selfaces):
	if method == 'FACE_PALMASK' and newpal < 1:
		return -1
	def newColorWith(col1,col2,vcMask,vcInfl):
		oldcol = Vector((col1[0],col1[1],col1[2],1.0))
		R = col2[0] if vcMask[0] else oldcol[0]
		G = col2[1] if vcMask[1] else oldcol[1]
		B = col2[2] if vcMask[2] else oldcol[2]
		newcol2 = Vector((R,G,B,1.0))
		newcol3 = oldcol+(newcol2-oldcol)*vcInfl
		return newcol3
	def newPalIslWith(palisl1,palisl2,vcMask):
		newpal2 = palisl2[0] if (vcMask[4] or palisl1 is None) else palisl1[0]
		newisl2 = palisl2[1] if (vcMask[3] or palisl1 is None) else palisl1[1]
		return Vector((newpal2,newisl2))
	if method == 'PROP' or targetObj.type == 'CURVE':
		pal = None
		if (vcName+kWPLPalIslUVPostfix) in targetObj:
			pal = targetObj[vcName+kWPLPalIslUVPostfix]
		if method == 'FACE_PALMASK':
			#if pal is None or abs(pal-newpal) > 0.01:
			return 0
		targetObj[vcName] = newColorWith((0,0,0,1),newcol,colmask,infl)
		if newpal != 0 or newisl != 0 or pal is not None:
			targetObj[vcName+kWPLPalIslUVPostfix] = newPalIslWith(pal,(newpal,newisl),colmask)
		return 1
	if targetObj.type != 'MESH':
		return -1
	active_mesh = targetObj.data
	color_map = active_mesh.vertex_colors.get(vcName)
	if (color_map is None):
		return -1
	palette_map = active_mesh.uv_layers.get(vcName+kWPLPalIslUVPostfix)
	if (colmask[3] != False or colmask[4] != False) or (method == 'FACE_PALMASK'):
		if (palette_map is None):
			return -1
	setCount = 0
	for poly in active_mesh.polygons:
		ipoly = poly.index
		if (method == 'VERT') or (selfaces is None) or (ipoly in selfaces):
			for idx, lIdx in enumerate(active_mesh.polygons[ipoly].loop_indices):
				ivdx = active_mesh.polygons[ipoly].vertices[idx]
				if (method == 'FACE' or method == 'FACE_PALMASK') or (selverts is None) or (ivdx in selverts):
					if palette_map is not None:
						pal = palette_map.data[lIdx].uv
						if method == 'FACE_PALMASK' and abs(pal[0]-newpal) > 0.01:
							continue
						palette_map.data[lIdx].uv = newPalIslWith(pal,(newpal,newisl),colmask)
					col = color_map.data[lIdx].color
					v_infl = infl
					if infl4vert is not None and ivdx in infl4vert:
						v_infl = v_infl * infl4vert[ivdx]
					lerped = newColorWith(col,newcol,colmask,v_infl)
					color_map.data[lIdx].color = lerped
					#print("- replacing ",(col[0],col[1],col[2]),"with",(newcol[0],newcol[1],newcol[2]),"mask:",colmask,"infl:",infl)
					setCount = setCount+1
	return setCount

class wplvcop_updcol( bpy.types.Operator ):
	bl_idname = "mesh.wplvcop_updcol"
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
	opt_smoothLoops = IntProperty(
		name="Smoothing Loops",
		min=0, max=10000,
		default=0
	)
	@classmethod
	def poll( cls, context ):
		p = (isinstance(context.scene.objects.active, bpy.types.Object))
		return p

	def execute( self, context ):
		vctoolsOpts = context.scene.vctoolsOpts
		active_obj = context.scene.objects.active
		if active_obj is None or len(vctoolsOpts.bake_vcnm) == 0:
			return {'CANCELLED'}
		if self.opt_target == 'PROP' or active_obj.type == 'CURVE':
			updateObjVC(active_obj,self.opt_target,vctoolsOpts.bake_vcnm,vctoolsOpts.bake_vc_col,vctoolsOpts.bake_vc_plt,vctoolsOpts.bake_vc_isl,vctoolsOpts.bake_vc_mask,self.opt_influence,None,None,None)
			return {'FINISHED'}
		oldmode = select_and_change_mode(active_obj,"OBJECT")
		active_mesh = active_obj.data
		selverts = get_selected_vertsIdx(active_mesh)
		selfaces = get_selected_facesIdx(active_mesh)
		if (self.opt_target == 'FACE' and len(selfaces) == 0) or (self.opt_target == 'VERT' and len(selverts) == 0):
			selverts = None #[e.index for e in active_mesh.vertices]
			selfaces = None #[f.index for f in active_mesh.polygons]
		gradinfo = None
		if self.opt_smoothLoops > 0 and selverts is not None and selfaces is not None:
			if gradinfo is None:
				gradinfo = {}
			for i in range(self.opt_smoothLoops):
				frc = ((self.opt_smoothLoops+1)-(i+1))*1.0/float(self.opt_smoothLoops+1)
				select_and_change_mode(active_obj,"EDIT")
				bpy.ops.mesh.select_more()
				select_and_change_mode(active_obj,"OBJECT")
				selverts2 = get_selected_vertsIdx(active_mesh)
				selfaces2 = get_selected_facesIdx(active_mesh)
				for vIdx in selverts2:
					if vIdx not in selverts and vIdx not in gradinfo:
						gradinfo[vIdx] = frc
						selverts.append(vIdx)
				for fIdx in selfaces2:
					if fIdx not in selfaces:
						selfaces.append(fIdx)
		color_map = active_mesh.vertex_colors.get(vctoolsOpts.bake_vcnm)
		if color_map is None:
			color_map = active_mesh.vertex_colors.new(vctoolsOpts.bake_vcnm)
		active_mesh.vertex_colors.active = color_map
		palette_map = None
		if vctoolsOpts.bake_vc_mask[3] != False or vctoolsOpts.bake_vc_mask[4] != False:
			palette_map = active_mesh.uv_layers.get(vctoolsOpts.bake_vcnm+kWPLPalIslUVPostfix)
			if palette_map is None:
				# creating new EMPTY uv
				active_mesh.uv_textures.new(vctoolsOpts.bake_vcnm+kWPLPalIslUVPostfix)
				palette_map = active_mesh.uv_layers.get(vctoolsOpts.bake_vcnm+kWPLPalIslUVPostfix)
				if palette_map is None:
					# uv-maps limit hit
					self.report({'ERROR'}, "Can`t create UV on ["+active_obj.name+"]")
					return {'CANCELLED'}
				for poly in active_mesh.polygons:
					ipoly = poly.index
					for idx, lIdx in enumerate(active_mesh.polygons[ipoly].loop_indices):
						palette_map.data[lIdx].uv = Vector((0,0))
		if vctoolsOpts.bake_vc_grad and "vc_paint_center" in active_obj:
			if selverts is not None:
				gradObj = active_obj["vc_paint_center"]
				gradPnt = Vector((gradObj[0],gradObj[1],gradObj[2]))
				maxDist = 0
				minDist = 9999
				for vIdx in selverts:
					v = active_mesh.vertices[vIdx]
					dst = (v.co-gradPnt).length
					if dst > maxDist:
						maxDist = dst
					if dst < minDist:
						minDist = dst
				if maxDist>0:
					if gradinfo is None:
						gradinfo = {}
					for vIdx in selverts:
						v = active_mesh.vertices[vIdx]
						dst = (v.co-gradPnt).length
						infl = (dst-minDist)/(maxDist-minDist)
						if v.index in gradinfo:
							gradinfo[v.index] = gradinfo[v.index]*infl
						else:
							gradinfo[v.index] = infl
		setCount = updateObjVC(active_obj,self.opt_target,vctoolsOpts.bake_vcnm,vctoolsOpts.bake_vc_col,vctoolsOpts.bake_vc_plt,vctoolsOpts.bake_vc_isl,vctoolsOpts.bake_vc_mask,self.opt_influence,gradinfo,selverts,selfaces)
		# storing gradient data
		selCenter = Vector((0,0,0))
		if selverts is not None:
			selCenterCnt = 0.0
			for vIdx in selverts:
				v = active_mesh.vertices[vIdx]
				selCenter = selCenter+v.co
				selCenterCnt = selCenterCnt+1.0
			if selCenterCnt>0.0:
				selCenter = selCenter/selCenterCnt
		active_obj["vc_paint_center"] = selCenter
		select_and_change_mode(active_obj,oldmode)
		self.report({'INFO'}, color_map.name+': verts='+str(setCount))
		return {'FINISHED'}

class wplvcop_masspalupd( bpy.types.Operator ):
	bl_idname = "mesh.wplvcop_masspalupd"
	bl_label = "Palette: Propagate pal-color on scene"
	bl_options = {'REGISTER', 'UNDO'}

	opt_filterRestr = EnumProperty(
		name="Restriction", default="PAL",
		items=(("PAL", "PALLETTE", ""), ("ALL", "NO FILTER", ""))
	)

	@classmethod
	def poll( cls, context ):
		p = (isinstance(context.scene.objects.active, bpy.types.Object))
		return p

	def execute( self, context ):
		vctoolsOpts = context.scene.vctoolsOpts
		if self.opt_filterRestr == 'PAL' and vctoolsOpts.bake_vc_plt == 0:
			self.report({'ERROR'}, "Palette #0 can`t be used")
			return {'CANCELLED'}
		objCount = 0
		meshDuples = {}
		vcName = vctoolsOpts.bake_vcnm
		print(" - VC:",vcName," Palette:",vctoolsOpts.bake_vc_plt,"Color:",vctoolsOpts.bake_vc_col)
		for objx in bpy.data.objects:
			if objx.hide or not objx.select:
				continue
			if not(objx.type == 'MESH' or objx.type == 'CURVE'):
				continue
			if objx.data.name in meshDuples:
				# already updated
				continue
			else:
				meshDuples[objx.data.name] = True
			print("- object", objx.name, objx.data.name)
			setCount = 0
			if objx.type == 'MESH':
				color_map = objx.data.vertex_colors.get(vcName)
				if color_map is None:
					objx.data.vertex_colors.new(vcName)
			if self.opt_filterRestr == 'PAL':
				setCount = updateObjVC(objx,'FACE_PALMASK',vcName,vctoolsOpts.bake_vc_col,vctoolsOpts.bake_vc_plt,vctoolsOpts.bake_vc_isl,(True,True,True,False,False),1.0,None,None,None)
			if self.opt_filterRestr == 'ALL':
				setCount = updateObjVC(objx,'FACE',vcName,vctoolsOpts.bake_vc_col,vctoolsOpts.bake_vc_plt,vctoolsOpts.bake_vc_isl,(True,True,True,False,False),1.0,None,None,None)
			if setCount > 0:
				print(" - updated ",setCount," verts")
				objCount = objCount+1
		self.report({'INFO'}, 'Updated = '+str(objCount)+" for Palette #"+str(vctoolsOpts.bake_vc_plt))
		return {'FINISHED'}

######################### ######################### #########################
######################### ######################### #########################
def onUpdate_bake_vcnm_real(self, context):
	vctoolsOpts = context.scene.vctoolsOpts
	if len(vctoolsOpts.bake_vcnm_real)>0:
		vctoolsOpts.bake_vcnm = vctoolsOpts.bake_vcnm_real
		vctoolsOpts.bake_vcnm_real = ""

def onUpdate_bake_vc_plt(self, context):
	vctoolsOpts = context.scene.vctoolsOpts
	if vctoolsOpts.bake_vc_plt >= 1:
		predefsCols = [vctoolsOpts.bake_vc_col_ref_d0,vctoolsOpts.bake_vc_col_ref_d1,vctoolsOpts.bake_vc_col_ref_d2,vctoolsOpts.bake_vc_col_ref_d3,vctoolsOpts.bake_vc_col_ref_d4,vctoolsOpts.bake_vc_col_ref_d5,vctoolsOpts.bake_vc_col_ref_d6,vctoolsOpts.bake_vc_col_ref_d7,vctoolsOpts.bake_vc_col_ref_d8]
		if vctoolsOpts.bake_vc_plt < len(predefsCols)+1:
			vctoolsOpts.bake_vc_col = predefsCols[vctoolsOpts.bake_vc_plt-1]
			#print("Color set to:",vctoolsOpts.bake_vc_plt)

class WPLVCToolsSettings(bpy.types.PropertyGroup):
	bake_vc_col = FloatVectorProperty(
		name="VC Color",
		subtype='COLOR_GAMMA', #'COLOR'
		min=0.0, max=1.0,
		default = (1.0,1.0,1.0)
		)
	bake_vc_col_ref_d0 = FloatVectorProperty(name="P1", subtype='COLOR_GAMMA', default = (1.0,1.0,1.0))
	bake_vc_col_ref_d1 = FloatVectorProperty(name="P2", subtype='COLOR_GAMMA', default = (1.0,1.0,1.0))
	bake_vc_col_ref_d2 = FloatVectorProperty(name="P3", subtype='COLOR_GAMMA', default = (1.0,1.0,1.0))
	bake_vc_col_ref_d3 = FloatVectorProperty(name="P4", subtype='COLOR_GAMMA', default = (1.0,1.0,1.0))
	bake_vc_col_ref_d4 = FloatVectorProperty(name="P5", subtype='COLOR_GAMMA', default = (1.0,1.0,1.0))
	bake_vc_col_ref_d5 = FloatVectorProperty(name="P6", subtype='COLOR_GAMMA', default = (1.0,1.0,1.0))
	bake_vc_col_ref_d6 = FloatVectorProperty(name="P7", subtype='COLOR_GAMMA', default = (1.0,1.0,1.0))
	bake_vc_col_ref_d7 = FloatVectorProperty(name="P8", subtype='COLOR_GAMMA', default = (0.5,0.5,0.5))
	bake_vc_col_ref_d8 = FloatVectorProperty(name="P9", subtype='COLOR_GAMMA', default = (0.0,0.0,0.0))

	bake_vc_plt = IntProperty(
		name="Palette",
		min = 0, max = 100,
		default = 0,
		update=onUpdate_bake_vc_plt
	)
	bake_vc_isl = IntProperty(
		name="Island",
		min = -100, max = 100,
		default = 0
	)
	bake_vc_grad = BoolProperty(
		name="Gradient from previous",
		default = False
	)
	bake_vc_mask = BoolVectorProperty(
		name="Color Mask",
		size = 5,
		default = (True,True,True,False,False)
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

class WPLVCTools_Panel(bpy.types.Panel):
	bl_label = "Prop: VC"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_category = 'WPL'

	def draw_header(self, context):
		layout = self.layout
		layout.label(text="")

	def draw(self, context):
		layout = self.layout
		vctoolsOpts = context.scene.vctoolsOpts
		active_obj = context.scene.objects.active
		col = layout.column()
		if active_obj is None or active_obj.data is None:
			col.label(text="No active object")
			return
		obj_data = active_obj.data
		box1 = col.box()
		row0 = box1.row()
		row0.prop(vctoolsOpts, "bake_vcnm")
		row0.prop_search(vctoolsOpts, "bake_vcnm_real", obj_data, "vertex_colors", icon='GROUP_VCOL')
		box1.separator()
		box1.prop(vctoolsOpts, "bake_vc_col", text="")
		row2 = box1.row()
		row2.prop(vctoolsOpts, "bake_vc_isl")
		row2.prop(vctoolsOpts, "bake_vc_plt")
		if vctoolsOpts.bake_vc_mask[3] == False and vctoolsOpts.bake_vc_mask[4] == False:
			row2.active = False
		row1 = box1.row()
		row1.prop(vctoolsOpts, "bake_vc_mask", text = "RGB-IP")
		box1.prop(vctoolsOpts, "bake_vc_grad")
		row3 = box1.row()
		op1 = row3.operator("mesh.wplvcop_updcol", text="->Faces")
		op1.opt_target = 'FACE'
		op1.opt_smoothLoops = 0
		op2 = row3.operator("mesh.wplvcop_updcol", text="->Verts")
		op2.opt_target = 'VERT'
		op2.opt_smoothLoops = 0
		box1.separator()
		box1.operator("mesh.wplvcop_pickvccol")
		row4 = box1.row()
		row4.operator("mesh.wplvcop_cppaste", text="COPY").opt_op = 'COPY'
		row4.operator("mesh.wplvcop_cppaste", text="PASTE").opt_op = 'PASTE'
		box2 = box1 #col.box()
		row3 = box2.row()
		row3.operator("mesh.wplvcop_resetvc", text="1").opt_resetIdx = 1
		row3.prop(vctoolsOpts, "bake_vc_col_ref_d0", text="")
		row3.operator("mesh.wplvcop_resetvc", text="2").opt_resetIdx = 2
		row3.prop(vctoolsOpts, "bake_vc_col_ref_d1", text="")
		row3.operator("mesh.wplvcop_resetvc", text="3").opt_resetIdx = 3
		row3.prop(vctoolsOpts, "bake_vc_col_ref_d2", text="")
		row4 = box2.row()
		row4.operator("mesh.wplvcop_resetvc", text="4").opt_resetIdx = 4
		row4.prop(vctoolsOpts, "bake_vc_col_ref_d3", text="")
		row4.operator("mesh.wplvcop_resetvc", text="5").opt_resetIdx = 5
		row4.prop(vctoolsOpts, "bake_vc_col_ref_d4", text="")
		row4.operator("mesh.wplvcop_resetvc", text="6").opt_resetIdx = 6
		row4.prop(vctoolsOpts, "bake_vc_col_ref_d5", text="")
		row5 = box2.row()
		row5.operator("mesh.wplvcop_resetvc", text="7").opt_resetIdx = 7
		row5.prop(vctoolsOpts, "bake_vc_col_ref_d6", text="")
		row5.operator("mesh.wplvcop_resetvc", text="8").opt_resetIdx = 8
		row5.prop(vctoolsOpts, "bake_vc_col_ref_d7", text="")
		row5.operator("mesh.wplvcop_resetvc", text="9").opt_resetIdx = 9
		row5.prop(vctoolsOpts, "bake_vc_col_ref_d8", text="")
		col.separator()
		col.separator()
		box3 = col.box()
		box3.operator("mesh.wplvcop_selvccol", text="Mesh: Select by brush color").opt_target = 'COLORBR'
		box3.operator("mesh.wplvcop_selvccol", text="Mesh: Select by selection color").opt_target = 'COLORSL'
		box3.operator("mesh.wplvcop_selvccol", text="Mesh: Select faces by palette").opt_target = 'PALETTE'
		box3.operator("mesh.wplvcop_selvccol", text="Mesh: Select faces by island").opt_target = 'ISLAND'
		col.separator()
		box4 = col.box()
		box4.operator("mesh.wplvcop_islandsrnd", text="Picker: Randomize Color").opt_target = 'BRUSH'
		box4.operator("mesh.wplvcop_islandsrnd", text="Islands: Randomize color").opt_target = 'SEL'
		box4.operator("mesh.wplvcop_islandsmid", text="Islands: Generate islands (UV/VC)")
		box4.operator("mesh.wplvcop_masspalupd", text="Objects: Mass-set (pallete only)").opt_filterRestr = 'PAL'
		box4.operator("mesh.wplvcop_masspalupd", text="Objects: Mass-set all").opt_filterRestr = 'ALL'

def register():
	bpy.utils.register_module(__name__)
	bpy.types.Scene.vctoolsOpts = PointerProperty(type=WPLVCToolsSettings)

def unregister():
	bpy.utils.unregister_module(__name__)
	del bpy.types.Scene.vctoolsOpts
	bpy.utils.unregister_class(WPLVCToolsSettings)

if __name__ == "__main__":
	register()
