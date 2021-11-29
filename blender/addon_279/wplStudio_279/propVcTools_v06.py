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
	"version": (1, 3, 6),
	"blender": (2, 7, 9),
	"location": "View3D > T-panel > WPL",
	"description" : "",
	"warning"	 : "",
	"wiki_url"	: "",
	"tracker_url" : "",
	"category"	: "WPL"
	}


kWPLRaycastEpsilon = 0.0001

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

# def camera_pos(region_3d):
# 	""" Return position, rotation data about a given view for the first space attached to it """
# 	#https://stackoverflow.com/questions/9028398/change-viewport-angle-in-blender-using-python
# 	def camera_position(matrix):
# 		""" From 4x4 matrix, calculate camera location """
# 		t = (matrix[0][3], matrix[1][3], matrix[2][3])
# 		r = (
# 		  (matrix[0][0], matrix[0][1], matrix[0][2]),
# 		  (matrix[1][0], matrix[1][1], matrix[1][2]),
# 		  (matrix[2][0], matrix[2][1], matrix[2][2])
# 		)
# 		rp = (
# 		  (-r[0][0], -r[1][0], -r[2][0]),
# 		  (-r[0][1], -r[1][1], -r[2][1]),
# 		  (-r[0][2], -r[1][2], -r[2][2])
# 		)
# 		output = mathutils.Vector((
# 		  rp[0][0] * t[0] + rp[0][1] * t[1] + rp[0][2] * t[2],
# 		  rp[1][0] * t[0] + rp[1][1] * t[1] + rp[1][2] * t[2],
# 		  rp[2][0] * t[0] + rp[2][1] * t[1] + rp[2][2] * t[2],
# 		))
# 		return output
# 	#look_at = region_3d.view_location
# 	matrix = region_3d.view_matrix
# 	#rotation = region_3d.view_rotation
# 	camera_pos = camera_position(matrix)
# 	return camera_pos

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

def splitBmVertsByLinks_v02(bm, selverts, onlySel):
	totalIslands = []
	verts2walk = []
	usedverts = []
	if onlySel:
		for v in bm.verts:
			if v.index not in selverts:
				usedverts.append(v.index)
	if selverts is None:
		selverts = []
		for v in bm.verts:
			selverts.append(v.index)
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
	
def getAvgColor(active_mesh, bake_vcnm, selfaces):
	if selfaces is None or len(selfaces) == 0:
		return (None, None)
	color_map = active_mesh.vertex_colors.get(bake_vcnm)
	vertx2cols = None
	vertx2cnt = 0
	for ipoly in range(len(active_mesh.polygons)):
		if ipoly in selfaces:
			for idx, lIdx in enumerate(active_mesh.polygons[ipoly].loop_indices):
				if vertx2cols is None:
					vertx2cols = mathutils.Vector(color_map.data[lIdx].color)
				else:
					vertx2cols = vertx2cols + mathutils.Vector(color_map.data[lIdx].color)
				vertx2cnt = vertx2cnt+1
	pickedcol = mathutils.Vector((vertx2cols[0],vertx2cols[1],vertx2cols[2],vertx2cols[3]))/vertx2cnt
	print("- picked", pickedcol,"on",vertx2cnt)
	return (pickedcol, vertx2cnt)

# mathutils.geometry.intersect_point_line
# def projectPointOnPlaneByNormal(pOrig, pTarg, planeNrm):
# 	vec = pTarg-pOrig
# 	pTargProjected = pTarg - dot(vec, planeNrm) * planeNrm
# 	return pTargProjected
def dist2face(vec_in, vec_in2, vec_axis):
	# vec_in - point, vec_in2 - point on face, vec_axis - face normal
	# https://stackoverflow.com/questions/9605556/how-to-project-a-3d-point-to-a-3d-plane
	# p - (n . (p - o)) . n
	# Also: mathutils.geometry.distance_point_to_plane
	nrm = vec_axis.normalized()
	vec_faceproj = vec_in -( nrm.dot(vec_in-vec_in2)*nrm )
	vec_facedist = (vec_in-vec_faceproj).length
	return vec_facedist
########### ############ ########### ############ ########### ############ ########### ############
########### ############ ########### ############ ########### ############ ########### ############
class wplvc_selvccol(bpy.types.Operator):
	bl_idname = "mesh.wplvc_selvccol"
	bl_label = "Pick by color"
	bl_options = {'REGISTER', 'UNDO'}
	opt_target = EnumProperty(
		name="Target", default="COLORBR",
		items=(('COLORBR', "COLORBR", ""), ('COLORSL', "COLORSL", ""))
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
			pickedcol, vertx2cnt = getAvgColor(active_mesh, vctoolsOpts.bake_vcnm, selfaces)
			if pickedcol is None:
				self.report({'ERROR'}, "Nothing selected")
				return {'FINISHED'}
			basecol = Vector((pickedcol[0],pickedcol[1],pickedcol[2]))
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
		select_and_change_mode(active_obj,"OBJECT")
		selfaces = 0
		selverts = 0
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

class wplvc_resetvc(bpy.types.Operator):
	bl_idname = "mesh.wplvc_resetvc"
	bl_label = "Reset color to palette"
	bl_options = {'REGISTER', 'UNDO'}
	opt_resetIdx = IntProperty(
		name="Pallete id",
		min=0, max=10,
		default=0
	)
	def execute( self, context ):
		vctoolsOpts = context.scene.vctoolsOpts
		predefsCols = [vctoolsOpts.bake_vc_col_ref2_d0,vctoolsOpts.bake_vc_col_ref2_d1,vctoolsOpts.bake_vc_col_ref2_d2,vctoolsOpts.bake_vc_col_ref2_d3,vctoolsOpts.bake_vc_col_ref2_d4,vctoolsOpts.bake_vc_col_ref2_d5,vctoolsOpts.bake_vc_col_ref2_d6,vctoolsOpts.bake_vc_col_ref2_d7,vctoolsOpts.bake_vc_col_ref2_d8]
		if self.opt_resetIdx-1 < len(predefsCols):
			vctoolsOpts.bake_vc_col = predefsCols[self.opt_resetIdx-1]
		return {'FINISHED'}
	
class wplvc_cppaste(bpy.types.Operator):
	bl_idname = "mesh.wplvc_cppaste"
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
						for idx, mt in enumerate(sel_obj.material_slots):
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

class wplvc_pickvccol(bpy.types.Operator):
	bl_idname = "mesh.wplvc_pickvccol"
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
		pickedcol, vertx2cnt = getAvgColor(active_mesh, vctoolsOpts.bake_vcnm, selfaces)
		setActiveBrushColor(context, pickedcol)
		select_and_change_mode(active_obj, oldmode)
		self.report({'INFO'}, 'Picked from verts='+str(vertx2cnt))
		return {'FINISHED'}

class wplvc_islandsrnd(bpy.types.Operator):
	bl_idname = "mesh.wplvc_islandsrnd"
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

def updateObjVC(targetObj,method,vcName,newcol,rgbMask,infl,infl4vert,selverts,selfaces):
	def newColorWith(col1,col2,channelMask,vcInfl):
		oldcol = Vector((col1[0],col1[1],col1[2],1.0))
		R = col2[0]*channelMask[0] + oldcol[0]*(1.0-channelMask[0])
		G = col2[1]*channelMask[1] + oldcol[1]*(1.0-channelMask[1])
		B = col2[2]*channelMask[2] + oldcol[2]*(1.0-channelMask[2])
		newcol2 = Vector((R,G,B,1.0))
		newcol3 = oldcol+(newcol2-oldcol)*vcInfl
		return newcol3
	if method == 'PROP' or targetObj.type == 'CURVE' or targetObj.type == 'FONT':
		targetObj[vcName] = newColorWith((0,0,0,1),newcol,rgbMask,infl)
		return 1
	if targetObj.type != 'MESH':
		return -1
	active_mesh = targetObj.data
	color_map = active_mesh.vertex_colors.get(vcName)
	if (color_map is None):
		return -1
	setCount = 0
	for poly in active_mesh.polygons:
		ipoly = poly.index
		if (method == 'VERT') or (selfaces is None) or (ipoly in selfaces):
			for idx, lIdx in enumerate(active_mesh.polygons[ipoly].loop_indices):
				ivdx = active_mesh.polygons[ipoly].vertices[idx]
				if (method == 'FACE') or (selverts is None) or (ivdx in selverts):
					col = color_map.data[lIdx].color
					v_infl = infl
					if infl4vert is not None and ivdx in infl4vert:
						v_infl = v_infl * infl4vert[ivdx]
					lerped = newColorWith(col,newcol,rgbMask,v_infl)
					color_map.data[lIdx].color = lerped
					setCount = setCount+1
	return setCount

class wplvc_updcol(bpy.types.Operator):
	bl_idname = "mesh.wplvc_updcol"
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
	opt_rgbMask = FloatVectorProperty(
		name="RGB mask",
		size=3,
		default=(1.0, 1.0, 1.0)
	)
	# opt_smoothLoops = IntProperty(
	# 	name="Smoothing Loops",
	# 	min=0, max=10000,
	# 	default=0
	# )
	@classmethod
	def poll( cls, context ):
		p = (isinstance(context.scene.objects.active, bpy.types.Object))
		return p

	def execute( self, context ):
		vctoolsOpts = context.scene.vctoolsOpts
		active_obj = context.scene.objects.active
		if active_obj is None or len(vctoolsOpts.bake_vcnm) == 0:
			return {'CANCELLED'}
		if active_obj.type == 'MESH' and modfGetByType(active_obj,'SKIN') is not None:
			self.opt_target = 'PROP'
		if self.opt_target == 'PROP' or active_obj.type == 'CURVE' or active_obj.type == 'FONT' or modfGetByType(active_obj, 'REMESH') is not None:
			print("- wplvc_updcol",active_obj,'PROP',vctoolsOpts.bake_vc_col)
			updateObjVC(active_obj,'PROP',vctoolsOpts.bake_vcnm,vctoolsOpts.bake_vc_col,self.opt_rgbMask,self.opt_influence,None,None,None)
			return {'FINISHED'}
		oldmode = select_and_change_mode(active_obj,"OBJECT")
		active_mesh = active_obj.data
		selverts = get_selected_vertsIdx(active_mesh)
		selfaces = get_selected_facesIdx(active_mesh)
		if (self.opt_target == 'FACE' and len(selfaces) == 0) or (self.opt_target == 'VERT' and len(selverts) == 0):
			selverts = None #[e.index for e in active_mesh.vertices]
			selfaces = None #[f.index for f in active_mesh.polygons]
		gradinfo = None
		color_map = active_mesh.vertex_colors.get(vctoolsOpts.bake_vcnm)
		if color_map is None:
			color_map = active_mesh.vertex_colors.new(vctoolsOpts.bake_vcnm)
			# filling with zeros
			color_map = active_mesh.vertex_colors.get(vctoolsOpts.bake_vcnm)
			for poly in active_mesh.polygons:
				ipoly = poly.index
				for idx, lIdx in enumerate(active_mesh.polygons[ipoly].loop_indices):
					color_map.data[lIdx].color = Vector((0,0,0,1))
		active_mesh.vertex_colors.active = color_map
		setCount = updateObjVC(active_obj,self.opt_target,vctoolsOpts.bake_vcnm,vctoolsOpts.bake_vc_col,self.opt_rgbMask,self.opt_influence, gradinfo, selverts,selfaces)
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
		active_obj["wpl_last_paint"] = [selCenter, vctoolsOpts.bake_vc_col]
		select_and_change_mode(active_obj,oldmode)
		print("- wplvc_updcol",active_obj,self.opt_target,vctoolsOpts.bake_vc_col,'verts='+str(setCount))
		self.report({'INFO'}, color_map.name+': verts='+str(setCount))
		return {'FINISHED'}

class wplvc_makegrad(bpy.types.Operator):
	bl_idname = "mesh.wplvc_makegrad"
	bl_label = "Gradient from last"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll( cls, context ):
		p = (isinstance(context.scene.objects.active, bpy.types.Object))
		return p

	def execute( self, context ):
		vctoolsOpts = context.scene.vctoolsOpts
		active_obj = context.scene.objects.active
		if active_obj is None or len(vctoolsOpts.bake_vcnm) == 0 or active_obj.type != 'MESH':
			return {'CANCELLED'}
		if "wpl_last_paint" not in active_obj:
			self.report({'ERROR'}, "No previous paint operation found")
			return {'CANCELLED'}
		oldmode = select_and_change_mode(active_obj,"OBJECT")
		active_mesh = active_obj.data
		selverts = get_selected_vertsIdx(active_mesh)
		select_and_change_mode(active_obj,"EDIT")
		bm = bmesh.from_edit_mesh( active_mesh )
		histVerts = get_bmhistory_vertsIdx(bm)
		if len(histVerts) == 0:
			self.report({'ERROR'}, "No active vert found")
			return {'CANCELLED'}
		gradPnt2 = bm.verts[histVerts[0]].co
		gradCol2 = vctoolsOpts.bake_vc_col
		select_and_change_mode(active_obj,"OBJECT")
		color_map = active_mesh.vertex_colors.get(vctoolsOpts.bake_vcnm)
		if color_map is None:
			return {'CANCELLED'}
		gradCol1 = active_obj["wpl_last_paint"][1]
		gradPntRaw = active_obj["wpl_last_paint"][0]
		gradPnt1 = Vector((gradPntRaw[0],gradPntRaw[1],gradPntRaw[2]))
		gradDst = (gradPnt1-gradPnt2).length
		gradNrm = (gradPnt2-gradPnt1).normalized()
		gradinfo = {}
		for vIdx in selverts:
			v = active_mesh.vertices[vIdx]
			dst = dist2face(v.co, gradPnt1, gradNrm)
			infl = dst / gradDst
			gradinfo[v.index] = max(0.0, min(infl, 1.0))
		for poly in active_mesh.polygons:
			ipoly = poly.index
			for idx, lIdx in enumerate(active_mesh.polygons[ipoly].loop_indices):
				ivdx = active_mesh.polygons[ipoly].vertices[idx]
				if ivdx not in gradinfo:
					continue
				inf = gradinfo[ivdx]
				color_map.data[lIdx].color = Vector((gradCol2[0]*inf+gradCol1[0]*(1.0-inf),gradCol2[1]*inf+gradCol1[1]*(1.0-inf),gradCol2[2]*inf+gradCol1[2]*(1.0-inf),1))
		select_and_change_mode(active_obj,oldmode)
		self.report({'INFO'}, color_map.name+': verts='+str(len(gradinfo)))
		return {'FINISHED'}

class wplvc_masspalupd(bpy.types.Operator):
	bl_idname = "mesh.wplvc_masspalupd"
	bl_label = "Propagate color on scene"
	bl_options = {'REGISTER', 'UNDO'}

	opt_objmatOnly = StringProperty(
			name = "Target Materials (* for all, **/*** for Mat colors)",
			default = ""
	)

	@classmethod
	def poll( cls, context ):
		p = (isinstance(context.scene.objects.active, bpy.types.Object))
		return p

	def execute( self, context ):
		vctoolsOpts = context.scene.vctoolsOpts
		vcName = vctoolsOpts.bake_vcnm
		if len(self.opt_objmatOnly) == 0:
			self.report({'INFO'}, "Dry run: Target Materials")
			return {'FINISHED'}
		if len(vcName) == 0:
			self.report({'INFO'}, "Dry run: Target VC")
			return {'FINISHED'}
		objCount = 0
		meshDuples = {}
		for objx in bpy.data.objects:
			if objx.hide or not objx.select:
				continue
			if not(objx.type == 'MESH' or objx.type == 'CURVE' or objx.type == 'FONT'):
				continue
			if objx.data.name in meshDuples:
				# already updated
				continue
			else:
				meshDuples[objx.data.name] = True
			print("- object", objx.name, objx.data.name, "mats:", len(objx.material_slots))
			setCount = 0
			selfaces = None
			upd_color = vctoolsOpts.bake_vc_col
			if objx.type == 'MESH':
				active_mesh = objx.data
				color_map = objx.data.vertex_colors.get(vcName)
				if color_map is None:
					objx.data.vertex_colors.new(vcName)
				if len(objx.material_slots) > 0:
					if self.opt_objmatOnly == "**" or self.opt_objmatOnly == "***":
						# using per-material color for update
						for idx, mt in enumerate(objx.material_slots):
							mat_active = mt.material
							if mat_active is None:
								continue
							if (self.opt_objmatOnly == "**") and (mat_active.library is not None):
								# lib materials are protected
								print("- skipped [", idx+1, mt.name, "]: library mat, protected")
								continue
							upd_color = mat_active.diffuse_color
							selfaces= []
							for poly in active_mesh.polygons:
								slot = objx.material_slots[poly.material_index]
								mat = slot.material
								if mat.name == mat_active.name:
									selfaces.append(poly.index)
							if len(selfaces)>0:
								setCount = updateObjVC(objx,'FACE',vcName,upd_color,(1.0,1.0,1.0),1.0,None,None,selfaces)
								if setCount > 0:
									print("- updated [", idx+1, mt.name, "]:", setCount,"verts,", len(selfaces),"faces,", upd_color)
						objCount = objCount+1
					else:
						# all faces on materials with this name
						if len(self.opt_objmatOnly) > 1:
							selfaces= []
							for poly in active_mesh.polygons:
								slot = objx.material_slots[poly.material_index]
								mat = slot.material
								if self.opt_objmatOnly in mat.name:
									selfaces.append(poly.index)
							print("- material faces:", mat.name, len(selfaces))
						else:
							selfaces = None
						setCount = updateObjVC(objx,'FACE',vcName,upd_color,(1.0,1.0,1.0),1.0,None,None,selfaces)
						print("- updated ", setCount," verts")
						objCount = objCount+1
		print("- updated ",objCount," objects")
		self.report({'INFO'}, 'Updated = '+str(objCount))
		return {'FINISHED'}

######################### ######################### #########################
######################### ######################### #########################
def onUpdate_bake_vcnm_real(self, context):
	vctoolsOpts = context.scene.vctoolsOpts
	if len(vctoolsOpts.bake_vcnm_real)>0:
		vctoolsOpts.bake_vcnm = vctoolsOpts.bake_vcnm_real
		vctoolsOpts.bake_vcnm_real = ""

class WPLVCToolsSettings(bpy.types.PropertyGroup):
	bake_vc_col = FloatVectorProperty(
		name="VC Color",
		subtype='COLOR_GAMMA', #'COLOR'
		min=0.0, max=1.0,
		default = (1.0,1.0,1.0)
		)
	bake_vc_col_ref2_d0 = FloatVectorProperty(name="P1", subtype='COLOR_GAMMA', default = (0.5,0.0,0.0))
	bake_vc_col_ref2_d1 = FloatVectorProperty(name="P2", subtype='COLOR_GAMMA', default = (0.0,0.5,0.0))
	bake_vc_col_ref2_d2 = FloatVectorProperty(name="P3", subtype='COLOR_GAMMA', default = (0.0,0.0,0.5))
	bake_vc_col_ref2_d3 = FloatVectorProperty(name="P4", subtype='COLOR_GAMMA', default = (1.0,0.0,0.0))
	bake_vc_col_ref2_d4 = FloatVectorProperty(name="P5", subtype='COLOR_GAMMA', default = (0.0,1.0,0.0))
	bake_vc_col_ref2_d5 = FloatVectorProperty(name="P6", subtype='COLOR_GAMMA', default = (0.0,0.0,1.0))
	bake_vc_col_ref2_d6 = FloatVectorProperty(name="P7", subtype='COLOR_GAMMA', default = (1.0,1.0,1.0))
	bake_vc_col_ref2_d7 = FloatVectorProperty(name="P8", subtype='COLOR_GAMMA', default = (0.5,0.5,0.5))
	bake_vc_col_ref2_d8 = FloatVectorProperty(name="P9", subtype='COLOR_GAMMA', default = (0.0,0.0,0.0))

	# bake_vc_grad = BoolProperty(
	# 	name="Gradient from previous",
	# 	default = False
	# )
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
		if not(active_obj.type == 'MESH' or active_obj.type == 'CURVE' or active_obj.type == 'FONT'):
			col.label(text="Unsupported object type")
			return
		obj_data = active_obj.data
		box1 = col.box()
		row0 = box1.row()
		row0.prop(vctoolsOpts, "bake_vcnm")
		row0.prop_search(vctoolsOpts, "bake_vcnm_real", obj_data, "vertex_colors", icon='GROUP_VCOL')
		box1.separator()
		box1.prop(vctoolsOpts, "bake_vc_col", text="")
		box1.separator()
		row1 = box1.row()
		op1 = box1.operator("mesh.wplvc_updcol", text="->Faces")
		op1.opt_target = 'FACE'
		op1.opt_rgbMask = (1.0, 1.0, 1.0)
		op2 = box1.operator("mesh.wplvc_updcol", text="->Verts")
		op2.opt_target = 'VERT'
		op2.opt_rgbMask = (1.0, 1.0, 1.0)
		box1.separator()
		row3 = box1.row()
		op1 = row3.operator("mesh.wplvc_updcol", text="+f R")
		op1.opt_target = 'FACE'
		op1.opt_rgbMask = (1.0, 0.0, 0.0)
		op1 = row3.operator("mesh.wplvc_updcol", text="+f G")
		op1.opt_target = 'FACE'
		op1.opt_rgbMask = (0.0, 1.0, 0.0)
		op1 = row3.operator("mesh.wplvc_updcol", text="+f B")
		op1.opt_target = 'FACE'
		op1.opt_rgbMask = (0.0, 0.0, 1.0)
		row3 = box1.row()
		op1 = row3.operator("mesh.wplvc_updcol", text="+v R")
		op1.opt_target = 'VERT'
		op1.opt_rgbMask = (1.0, 0.0, 0.0)
		op1 = row3.operator("mesh.wplvc_updcol", text="+v G")
		op1.opt_target = 'VERT'
		op1.opt_rgbMask = (0.0, 1.0, 0.0)
		op1 = row3.operator("mesh.wplvc_updcol", text="+v B")
		op1.opt_target = 'VERT'
		op1.opt_rgbMask = (0.0, 0.0, 1.0)
		box1.separator()
		box1.operator("mesh.wplvc_pickvccol")
		row4 = box1.row()
		row4.operator("mesh.wplvc_cppaste", text="COPY").opt_op = 'COPY'
		row4.operator("mesh.wplvc_cppaste", text="PASTE").opt_op = 'PASTE'
		box2 = box1 #col.box()
		row3 = box2.row()
		row3.operator("mesh.wplvc_resetvc", text="1").opt_resetIdx = 1
		row3.prop(vctoolsOpts, "bake_vc_col_ref2_d0", text="")
		row3.operator("mesh.wplvc_resetvc", text="2").opt_resetIdx = 2
		row3.prop(vctoolsOpts, "bake_vc_col_ref2_d1", text="")
		row3.operator("mesh.wplvc_resetvc", text="3").opt_resetIdx = 3
		row3.prop(vctoolsOpts, "bake_vc_col_ref2_d2", text="")
		row4 = box2.row()
		row4.operator("mesh.wplvc_resetvc", text="4").opt_resetIdx = 4
		row4.prop(vctoolsOpts, "bake_vc_col_ref2_d3", text="")
		row4.operator("mesh.wplvc_resetvc", text="5").opt_resetIdx = 5
		row4.prop(vctoolsOpts, "bake_vc_col_ref2_d4", text="")
		row4.operator("mesh.wplvc_resetvc", text="6").opt_resetIdx = 6
		row4.prop(vctoolsOpts, "bake_vc_col_ref2_d5", text="")
		row5 = box2.row()
		row5.operator("mesh.wplvc_resetvc", text="7").opt_resetIdx = 7
		row5.prop(vctoolsOpts, "bake_vc_col_ref2_d6", text="")
		row5.operator("mesh.wplvc_resetvc", text="8").opt_resetIdx = 8
		row5.prop(vctoolsOpts, "bake_vc_col_ref2_d7", text="")
		row5.operator("mesh.wplvc_resetvc", text="9").opt_resetIdx = 9
		row5.prop(vctoolsOpts, "bake_vc_col_ref2_d8", text="")
		col.separator()
		col.separator()
		box3 = col.box()
		box3.operator("mesh.wplvc_selvccol", text="Mesh: Select by brush color").opt_target = 'COLORBR'
		box3.operator("mesh.wplvc_selvccol", text="Mesh: Select by selection color").opt_target = 'COLORSL'
		box3.operator("mesh.wplvc_makegrad")
		col.separator()
		box4 = col.box()
		box4.operator("mesh.wplvc_islandsrnd", text="Picker: Randomize Color").opt_target = 'BRUSH'
		box4.operator("mesh.wplvc_islandsrnd", text="Mesh: Randomize color").opt_target = 'SEL'
		box4.operator("mesh.wplvc_masspalupd", text="Objects: Mass-set all")

def register():
	bpy.utils.register_module(__name__)
	bpy.types.Scene.vctoolsOpts = PointerProperty(type=WPLVCToolsSettings)

def unregister():
	bpy.utils.unregister_module(__name__)
	del bpy.types.Scene.vctoolsOpts
	bpy.utils.unregister_class(WPLVCToolsSettings)

if __name__ == "__main__":
	register()
