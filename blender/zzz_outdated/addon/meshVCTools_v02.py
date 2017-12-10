import bpy
import bmesh
import math
import mathutils
from mathutils import Vector
from random import random, seed
from bpy_extras import view3d_utils
from bpy.props import (StringProperty,
						BoolProperty,
						IntProperty,
						FloatProperty,
						FloatVectorProperty,
						EnumProperty,
						PointerProperty,
						)
from bpy.types import (Panel,
						Operator,
						AddonPreferences,
						PropertyGroup,
						)

bl_info = {
	"name": "WPL DistBake Helpers",
	"author": "IPv6",
	"version": (0, 0, 1),
	"blender": (2, 78, 0),
	"location": "View3D > T-panel > WPL",
	"description": "Bake mesh features into vertext colors/UVMaps.",
	"warning": "",
	"wiki_url": "",
	"tracker_url": "",
	"category": ""}

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
def getPitValue(indexCur,indexMax,index50,Pits):
	value = 0.0
	if indexCur<index50:
		value = Pits[0]+(Pits[1]-Pits[0])*(indexCur/index50)
	else:
		value = Pits[1]+(Pits[2]-Pits[1])*((indexCur-index50)/(indexMax-index50))
	return value

def do_painting(context, active_object, active_mesh, color_map, paint_list, glob_refpoint, vc_refmode):
	print("do_painting, vertext count: ", len(paint_list))
	if vc_refmode == "shape":
		b_up = mathutils.Vector((0,1))
		b_ri = mathutils.Vector((1,0))
		# looking for external edges (dumb way, most left/right/up/down points)
		extr_list = []
		for vertex_data in paint_list:
			srt_ddx1 = sorted(filter(lambda plt: plt[3][1] <= vertex_data[3][1],paint_list), key=lambda plt: (plt[3][0]-vertex_data[3][0]))
			if(len(srt_ddx1)>0):
				if (srt_ddx1[0]) not in extr_list:
					extr_list.append(srt_ddx1[0])
				if ((srt_ddx1[::-1])[0]) not in extr_list:
					extr_list.append((srt_ddx1[::-1])[0])
			srt_ddx2 = sorted(filter(lambda plt: plt[3][1] > vertex_data[3][1],paint_list), key=lambda plt: (plt[3][0]-vertex_data[3][0]))
			if(len(srt_ddx2)>0):
				if (srt_ddx2[0]) not in extr_list:
					extr_list.append(srt_ddx2[0])
				if ((srt_ddx2[::-1])[0]) not in extr_list:
					extr_list.append((srt_ddx2[::-1])[0])
			srt_ddy1 = sorted(filter(lambda plt: plt[3][0] <= vertex_data[3][0],paint_list), key=lambda plt: (plt[3][1]-vertex_data[3][1]))
			if(len(srt_ddy1)>0):
				if (srt_ddy1[0]) not in extr_list:
					extr_list.append(srt_ddy1[0])
				if ((srt_ddy1[::-1])[0]) not in extr_list:
					extr_list.append((srt_ddy1[::-1])[0])
			srt_ddy2 = sorted(filter(lambda plt: plt[3][0] > vertex_data[3][0],paint_list), key=lambda plt: (plt[3][1]-vertex_data[3][1]))
			if(len(srt_ddy2)>0):
				if (srt_ddy2[0]) not in extr_list:
					extr_list.append(srt_ddy2[0])
				if ((srt_ddy2[::-1])[0]) not in extr_list:
					extr_list.append((srt_ddy2[::-1])[0])
		srt_ddp = sorted(extr_list, key=lambda plt: (plt[3]-extr_list[0][3]).length, reverse=True)
		maxdim = (srt_ddp[0][3]-extr_list[0][3]).length
		for vertex_data in paint_list:
			srt_dd = sorted(extr_list, key=lambda plt: (plt[3]-vertex_data[3]).length)
			srt_xp = sorted(extr_list, key=lambda plt: (plt[3][0]-vertex_data[3][0])/(1.0+abs(b_ri.dot(plt[3]-vertex_data[3]))))
			srt_yp = sorted(extr_list, key=lambda plt: (plt[3][1]-vertex_data[3][1])/(1.0+abs(b_up.dot(plt[3]-vertex_data[3]))))
			min_x = srt_xp[0][3][0]
			max_x = (srt_xp[::-1])[0][3][0]
			min_y = srt_yp[0][3][1]
			max_y = (srt_yp[::-1])[0][3][1]
			vec2d = vertex_data[3]
			xrel = (vec2d[0]-min_x)/(max_x-min_x)
			yrel = (vec2d[1]-min_y)/(max_y-min_y)
			drel = 2.0*(vertex_data[3]-srt_dd[0][3]).length/maxdim
			color_map.data[vertex_data[0]].color = (xrel,yrel,drel,1.0)
	if vc_refmode == "axis":
		min_x = 9999
		max_x = 0
		min_y = 9999
		max_y = 0
		min_nx = mathutils.Vector()
		max_nx = mathutils.Vector()
		for vertex_data in paint_list:
			vec2d = vertex_data[3] #location_to_region(vertex_data[1])
			if vec2d[0]<min_x:
				min_x = vec2d[0]
				min_nx = vertex_data[2]
			if vec2d[0]>max_x:
				max_x = vec2d[0]
				max_nx = vertex_data[2]
			min_y = min(min_y,vec2d[1])
			max_y = max(max_y,vec2d[1])
		#max_xy = max(max_x,max_y)
		nn_rads = math.acos(min_nx.dot(max_nx))
		for vertex_data in paint_list:
			vec2d = vertex_data[3] #location_to_region(vertex_data[1])
			xrel = (vec2d[0]-min_x)/(max_x-min_x)
			yrel = (vec2d[1]-min_y)/(max_y-min_y)
			#xrel = vec2d[0]/max_xy
			#yrel = vec2d[1]/max_xy
			#print("xrel: ",xrel," yrel", yrel)
			if (nn_rads>0):
				nrel = math.acos(min_nx.dot(vertex_data[2]))/nn_rads
			else:
				nrel = 0
			color_map.data[vertex_data[0]].color = (xrel,yrel,nrel,1.0)
	# if vc_refmode == "dist":
		# glob_refpoint2d = location_to_region(glob_refpoint)
		# maxlen3d = 0
		# minlen3d = 9999
		# maxlen2d = 0
		# minlen2d = 9999
		# for vertex_data in paint_list:
			# vec = vertex_data[1]-glob_refpoint
			# vec2d = vertex_data[3]-glob_refpoint2d
			# maxlen3d = max(maxlen3d,vec.length)
			# minlen3d = min(minlen3d,vec.length)
			# maxlen2d = max(maxlen2d,vec2d.length)
			# minlen2d = min(minlen2d,vec2d.length)
		# for vertex_data in paint_list:
			# vec3d = vertex_data[1]-glob_refpoint
			# reldist3d = (vec3d.length-minlen3d)/(maxlen3d-minlen3d)
			# vec2d = vertex_data[3]-glob_refpoint2d
			# reldist2d = (vec2d.length-minlen2d)/(maxlen2d-minlen2d)
			# color_map.data[vertex_data[0]].color = (reldist3d,reldist2d,vec3d.length*0.1,1.0)
		# return
	return

def op_find_and_paint(context, operator, active_object, color_map, vc_refmode):
	def make_paint_list(active_object, active_mesh, faces):
		# paint_list will contain all vertex color map indices to
		# be used for overpainting.
		paint_list = []
		i = 0
		for poly in active_mesh.polygons:
			face_is_selected = poly.index in faces
			for idx in poly.loop_indices:
				if face_is_selected:
					l = active_mesh.loops[idx] # The loop entry this polygon point refers to
					v = active_mesh.vertices[l.vertex_index] # The vertex data that loop entry refers to
					co_world = active_object.matrix_world * v.co
					co_world2d = location_to_region(co_world)
					norml = mathutils.Vector((v.normal.x,v.normal.y,v.normal.z))
					paint_list.append([i, co_world, norml, co_world2d])
				i += 1
		return paint_list
	if not (bpy.context.active_object.mode == 'VERTEX_PAINT') or not (bpy.context.active_object.data.use_paint_mask):
		operator.report({'ERROR'}, "Use face masking mode, while in Vertex Paint mode")
		return
	active_mesh = active_object.data
	#cursor = active_object.matrix_world.inverted()*get_active_context_cursor(context)
	cursor = get_active_context_cursor(context)
	faces = get_selected_facesIdx(active_mesh)
	if len(faces) == 0:
		operator.report({'ERROR'}, "No faces selected, select some faces first")
		return
	paint_list = make_paint_list(active_object, active_mesh, faces)
	do_painting(context, active_object, active_mesh, color_map, paint_list, cursor, vc_refmode)

def add_connected_bmverts(v,verts_list,selverts):
	v.tag = True
	if (selverts is not None) and (v.index not in selverts):
		return
	if v not in verts_list:
		verts_list.append(v)
	for edge in v.link_edges:
		ov = edge.other_vert(v)
		if (ov is not None) and not ov.tag:
			ov.tag = True
			if (selverts is not None) and (ov.index not in selverts):
				return
			if ov not in verts_list:
				verts_list.append(ov)
			add_connected_bmverts(ov,verts_list,selverts)

def location_to_region(worldcoords):
	out = view3d_utils.location_3d_to_region_2d(bpy.context.region, bpy.context.space_data.region_3d, worldcoords)
	return out

def region_to_location(viewcoords, depthcoords):
	out = view3d_utils.region_2d_to_location_3d(bpy.context.region, bpy.context.space_data.region_3d, viewcoords, depthcoords)
	return out

def get_active_context_cursor(context):
	scene = context.scene
	space = context.space_data
	cursor = (space if space and space.type == 'VIEW_3D' else scene).cursor_location
	return cursor

def get_selected_vertsIdx(active_mesh):
	# find selected faces
	bpy.ops.object.mode_set(mode='OBJECT')
	selectedVertsIdx = [e.index for e in active_mesh.vertices if e.select]
	return selectedVertsIdx

def force_visible_object(obj):
	if obj:
		if obj.hide == True:
			obj.hide = False
		for n in range(len(obj.layers)):
			obj.layers[n] = False
		current_layer_index = bpy.context.scene.active_layer
		obj.layers[current_layer_index] = True

def select_and_change_mode(obj,obj_mode,hidden=False):
	if obj:
		obj.select = True
		bpy.context.scene.objects.active = obj
		force_visible_object(obj)
		try:
			m = bpy.context.mode
			if bpy.context.mode!='OBJECT':
				bpy.ops.object.mode_set(mode='OBJECT')
			bpy.context.scene.update()
			bpy.ops.object.mode_set(mode=obj_mode)
			#print("Mode switched to ", obj_mode)
		except:
			pass
		obj.hide = hidden
	return m

#class bakeCursorDistanceToVc(bpy.types.Operator):
	# bl_idname = "object.wplbake_3dcurdist_to_vc"
	# bl_label = "VC: Bake 3D cursor coords"
	# bl_options = {'REGISTER', 'UNDO'}

	# @classmethod
	# def poll(self, context):
		# #Check if we have a mesh object active and are in vertex paint mode
		# p = context.object and context.object.data and (isinstance(context.scene.objects.active, bpy.types.Object) and isinstance(context.scene.objects.active.data, bpy.types.Mesh))
		# return p

	# def execute(self, context):
		# print("execute ", self.bl_idname)
		# active_object = context.scene.objects.active
		# if active_object is not None:
			# active_object.data.use_paint_mask = True
		# op_find_and_paint(context, self, active_object, !!! "dist")
		# bpy.ops.object.mode_set(mode='VERTEX_PAINT')
		# context.scene.update()
		# return {'FINISHED'}

# class WPLbake_mesh_centers(bpy.types.Operator):
# 	bl_idname = "object.wplbake_mesh_centers"
# 	bl_label = "UV: Bake mesh coords"
# 	bl_options = {'REGISTER', 'UNDO'}
# 	actionType = bpy.props.IntProperty()
#
# 	@classmethod
# 	def poll(self, context):
# 		# Check if we have a mesh object active
# 		p = context.object and context.object.data and (isinstance(context.scene.objects.active, bpy.types.Object) and isinstance(context.scene.objects.active.data, bpy.types.Mesh))
# 		return p
#
# 	def execute(self, context):
# 		print("execute ", self.bl_idname, type)
# 		operator = self
# 		vc_bakeOpts = context.scene.vc_bakeOpts
# 		active_object = context.scene.objects.active
# 		cursor = active_object.matrix_world.inverted()*get_active_context_cursor(context)
# 		print ("cursor position: ", cursor)
# 		active_mesh = active_object.data
# 		selfaces = get_selected_facesIdx(active_mesh)
# 		if len(selfaces) == 0:
# 			operator.report({'ERROR'}, "No faces selected, select some faces first")
# 			return {'FINISHED'}
# 		bpy.ops.object.mode_set(mode='OBJECT')
#
# 		if self.actionType == 2 or self.actionType == 6 or self.actionType == 3 or self.actionType == 5:
# 			bakemap_pref = vc_bakeOpts.bake_uvbase
# 			bakemap_x = bakemap_pref+"X"
# 			uv_layer_bx = active_mesh.uv_textures.get(bakemap_x)
# 			if uv_layer_bx is None:
# 				active_mesh.uv_textures.new(bakemap_x)
# 			bakemap_y = bakemap_pref+"Y"
# 			uv_layer_by = active_mesh.uv_textures.get(bakemap_y)
# 			if uv_layer_by is None:
# 				active_mesh.uv_textures.new(bakemap_y)
# 			bakemap_z = bakemap_pref+"Z"
# 			uv_layer_bz = active_mesh.uv_textures.get(bakemap_z)
# 			if uv_layer_bz is None:
# 				active_mesh.uv_textures.new(bakemap_z)
#
# 		if self.actionType == 4:
# 			bakemap_pref = vc_bakeOpts.bake_uvbase
# 			bakemap_a = bakemap_pref+"A"
# 			uv_layer_ba = active_mesh.uv_textures.get(bakemap_a)
# 			if uv_layer_ba is None:
# 				active_mesh.uv_textures.new(bakemap_a)
#
# 		bm = bmesh.new()
# 		bm.from_mesh(active_mesh)
# 		bm.verts.ensure_lookup_table()
# 		bm.faces.ensure_lookup_table()
# 		bm.verts.index_update()
#
# 		uv_values1 = {}
# 		uv_values2 = {}
# 		selverts = []
# 		for v in bm.verts:
# 			v.tag = False
# 		for face in bm.faces:
# 			face_is_selected = face.index in selfaces
# 			if face_is_selected:
# 				for vert, loop in zip(face.verts, face.loops):
# 					selverts.append(vert.index)
# 		print("Faces selected:", len(selfaces), "; Vertices selected:", len(selverts))
# 		for v in bm.verts:
# 			if v.tag == False:
# 				meshlist = []
# 				add_connected_bmverts(v,meshlist,selverts)
# 				if len(meshlist) > 0:
# 					if self.actionType == 2 or self.actionType == 6:
# 						medianpoint = mathutils.Vector()
# 						for mv in meshlist:
# 							medianpoint = medianpoint+mv.co
# 						medianpoint = medianpoint/len(meshlist)
# 						median_maxx = 0;
# 						median_maxy = 0;
# 						median_maxz = 0;
# 						for mv in meshlist:
# 							median_maxx = max(median_maxx, abs(mv.co[0]-medianpoint[0]))
# 							median_maxy = max(median_maxy, abs(mv.co[1]-medianpoint[1]))
# 							median_maxz = max(median_maxz, abs(mv.co[2]-medianpoint[2]))
# 						mediandivers = (median_maxx, median_maxy, median_maxz)
# 						print ("Mesh median: ", medianpoint, mediandivers)
# 						for mv in meshlist:
# 							if self.actionType == 2:
# 								uv_values1[mv.index] = (medianpoint-mv.co, mediandivers)
# 							else:
# 								uv_values1[mv.index] = (medianpoint, mediandivers)
# 					elif self.actionType == 3 or self.actionType == 5:
# 						median_maxx = 0;
# 						median_maxy = 0;
# 						median_maxz = 0;
# 						for mv in meshlist:
# 							median_maxx = max(median_maxx, abs(mv.co[0]-cursor[0]))
# 							median_maxy = max(median_maxy, abs(mv.co[1]-cursor[1]))
# 							median_maxz = max(median_maxz, abs(mv.co[2]-cursor[2]))
# 						mediandivers = (median_maxx, median_maxy, median_maxz)
# 						for mv in meshlist:
# 							if self.actionType == 3:
# 								uv_values1[mv.index] = (cursor-mv.co, mediandivers)
# 							else:
# 								uv_values1[mv.index] = (cursor, mediandivers)
# 					elif self.actionType == 4:
# 						min_x = 9999
# 						min_y = 9999
# 						max_x = 0
# 						max_y = 0
# 						for mv in meshlist:
# 							co_world = active_object.matrix_world * mv.co
# 							vec2d = location_to_region(co_world)
# 							max_x = max(max_x,vec2d[0])
# 							max_y = max(max_y,vec2d[1])
# 							min_x = min(min_x,vec2d[0])
# 							min_y = min(min_y,vec2d[1])
# 						projscale = min((max_x-min_x),(max_y-min_y))
# 						for mv in meshlist:
# 							co_world = active_object.matrix_world * mv.co
# 							vec2d = location_to_region(co_world)
# 							xrel = (vec2d[0]-min_x)/projscale
# 							yrel = (vec2d[1]-min_y)/projscale
# 							uv_values2[mv.index] = (xrel, yrel)
# 		ok_count = 0;
# 		if len(uv_values1)>0:
# 			uv_layer_bx = bm.loops.layers.uv.get(bakemap_x)
# 			uv_layer_by = bm.loops.layers.uv.get(bakemap_y)
# 			uv_layer_bz = bm.loops.layers.uv.get(bakemap_z)
# 			for face in bm.faces:
# 				for vert, loop in zip(face.verts, face.loops):
# 					if (vert.index in selverts) and (vert.index in uv_values1):
# 						loop[uv_layer_bx].uv = (uv_values1[vert.index][0][0],uv_values1[vert.index][1][0])
# 						loop[uv_layer_by].uv = (uv_values1[vert.index][0][1],uv_values1[vert.index][1][1])
# 						loop[uv_layer_bz].uv = (uv_values1[vert.index][0][2],uv_values1[vert.index][1][2])
# 						ok_count = ok_count+1
# 			bm.to_mesh(active_mesh)
# 		if len(uv_values2)>0:
# 			uv_layer_ba = bm.loops.layers.uv.get(bakemap_a)
# 			for face in bm.faces:
# 				for vert, loop in zip(face.verts, face.loops):
# 					if (vert.index in selverts) and (vert.index in uv_values2):
# 						loop[uv_layer_ba].uv = uv_values2[vert.index]
# 						ok_count = ok_count+1
# 			bm.to_mesh(active_mesh)
# 		bm.free()
# 		context.scene.update()
# 		print("Vertices baked:", ok_count)
# 		return {'FINISHED'}

###### ########## ######
class WPLbake_2daxis_to_vc(bpy.types.Operator):
	bl_idname = "object.wplbake_2daxis_to_vc"
	bl_label = "VC: Bake surface axis"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(self, context):
		# Check if we have a mesh object active and are in vertex paint mode
		p = context.object and context.object.data and (isinstance(context.scene.objects.active, bpy.types.Object) and isinstance(context.scene.objects.active.data, bpy.types.Mesh))
		return p

	def execute(self, context):
		print("execute ", self.bl_idname)
		active_object = context.scene.objects.active
		if active_object is None:
			return {'CANCELLED'}
		bpy.ops.object.mode_set(mode='VERTEX_PAINT')
		active_object.data.use_paint_mask = True
		vc_bakeOpts = context.scene.vc_bakeOpts
		color_map = active_object.data.vertex_colors.get(vc_bakeOpts.bake_vcnm)
		if color_map is None:
			self.report({'ERROR'}, "Target VC not found")
			return {'CANCELLED'}
		op_find_and_paint(context, self, active_object, color_map, "axis")
		bpy.ops.object.mode_set(mode='VERTEX_PAINT')
		context.scene.update()
		return {'FINISHED'}

class WPLbake_2dshape_to_vc(bpy.types.Operator):
	bl_idname = "object.wplbake_2dshape_to_vc"
	bl_label = "VC: Bake edgeshape"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(self, context):
		# Check if we have a mesh object active and are in vertex paint mode
		p = context.object and context.object.data and (isinstance(context.scene.objects.active, bpy.types.Object) and isinstance(context.scene.objects.active.data, bpy.types.Mesh))
		return p

	def execute(self, context):
		print("execute ", self.bl_idname)
		active_object = context.scene.objects.active
		if active_object is None:
			return {'CANCELLED'}
		bpy.ops.object.mode_set(mode='VERTEX_PAINT')
		active_object.data.use_paint_mask = True
		vc_bakeOpts = context.scene.vc_bakeOpts
		color_map = active_object.data.vertex_colors.get(vc_bakeOpts.bake_vcnm)
		if color_map is None:
			self.report({'ERROR'}, "Target VC not found")
			return {'CANCELLED'}
		op_find_and_paint(context, self, active_object, color_map, "shape")
		bpy.ops.object.mode_set(mode='VERTEX_PAINT')
		context.scene.update()
		return {'FINISHED'}

# class WPLbake_shpk_to_vc(bpy.types.Operator):
	# bl_idname = "object.wplbake_shpk_to_vc"
	# bl_label = "VC: Bake shapekey diff"
	# bl_options = {'REGISTER', 'UNDO'}

	# opt_r_infl = bpy.props.FloatProperty(
		# name		= "R: Positive shift influence",
		# min			= 0.0, max = 1000,
		# default	 	= 100.0
		# )
	# opt_b_infl = bpy.props.FloatProperty(
		# name		= "B: Negative shift influence",
		# min			= 0.0, max = 1000,
		# default	 	= 100.0
		# )
	# opt_g_infl = bpy.props.FloatProperty(
		# name		= "G: Normals influence",
		# min			= 0.0, max = 100,
		# default	 	= 1.0
		# )

	# @classmethod
	# def poll(self, context):
		# p = context.object and context.object.data and (isinstance(context.scene.objects.active, bpy.types.Object) and isinstance(context.scene.objects.active.data, bpy.types.Mesh))
		# return p

	# def execute(self, context):
		# print("execute ", self.bl_idname)
		# active_object = context.scene.objects.active
		# if active_object is None or active_object.data is None:
			# return {'CANCELLED'}
		# active_mesh = active_object.data
		# bpy.ops.object.mode_set(mode='OBJECT')
		# selectedVertsIdx = [v.index for v in active_mesh.vertices if v.select]
		# if len(selectedVertsIdx) < 3:
			# self.report({'ERROR'}, "Not enough selected vertices found")
			# return {'CANCELLED'}
		# active_object.data.use_paint_mask = True
		# vc_bakeOpts = context.scene.vc_bakeOpts
		# color_map = active_mesh.vertex_colors.get(vc_bakeOpts.bake_vcnm)
		# if color_map is None:
			# self.report({'ERROR'}, "Target VC not found")
			# return {'CANCELLED'}
		# shpk1 = active_mesh.shape_keys.key_blocks[vc_bakeOpts.bake_shk1]
		# shpk2 = active_mesh.shape_keys.key_blocks[vc_bakeOpts.bake_shk2]
		# if shpk1 is None or shpk2 is None:
			# self.report({'ERROR'}, "One of shapekeys not found")
			# return {'CANCELLED'}
		# for poly in active_mesh.polygons:
			# for loop_index in range(poly.loop_start, poly.loop_start + poly.loop_total):
				# vi = active_mesh.loops[loop_index].vertex_index
				# if (vi in selectedVertsIdx):
					# co1 = shpk1.data[vi].co
					# co2 = shpk2.data[vi].co
					# distP = (co1-co2).length
					# distN = distP
					# ndir = active_mesh.vertices[vi].normal.dot((co2-co1).normalized())
					# if ndir<=0:
						# distP = 0
					# else:
						# distN = 0
					# color_map.data[loop_index].color = (distP*self.opt_r_infl,abs(ndir*self.opt_g_infl),distN*self.opt_b_infl,1.0)
		# context.scene.update()
		# bpy.ops.object.mode_set(mode='VERTEX_PAINT')
		# return {'FINISHED'}

class WPLbake_rndcol_to_vc(bpy.types.Operator):
	bl_idname = "object.wplbake_rndcol_to_vc"
	bl_label = "VC: Bake random color"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(self, context):
		# Check if we have a mesh object active and are in vertex paint mode
		p = context.object and context.object.data and (isinstance(context.scene.objects.active, bpy.types.Object) and isinstance(context.scene.objects.active.data, bpy.types.Mesh))
		return p

	def execute(self, context):
		print("execute ", self.bl_idname)
		active_object = context.scene.objects.active
		if active_object is None:
			return {'CANCELLED'}
		active_mesh = active_object.data
		selfaces = get_selected_facesIdx(active_mesh)
		if len(selfaces) == 0:
			operator.report({'ERROR'}, "No faces selected, select some faces first")
			return {'CANCELLED'}
		bpy.ops.object.mode_set(mode='EDIT')
		vc_bakeOpts = context.scene.vc_bakeOpts
		color_map = active_object.data.vertex_colors.get(vc_bakeOpts.bake_vcnm)
		if color_map is None:
			self.report({'ERROR'}, "Target VC not found")
			return {'CANCELLED'}

		bm = bmesh.new()
		bm.from_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		vc_values = {}
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
				add_connected_bmverts(v,meshlist,selverts)
				if len(meshlist) > 0:
					rndc = (random(),random(),random(),1.0)
					for ov in meshlist:
						vc_values[ov.index] = rndc
		bpy.ops.object.mode_set(mode='OBJECT')
		context.scene.update()
		color_map = active_object.data.vertex_colors.get(vc_bakeOpts.bake_vcnm)
		color_map.active = True
		if len(vc_values)>0:
			for poly in active_mesh.polygons:
				face_is_selected = poly.index in selfaces
				if face_is_selected:
					ipoly = poly.index
					for idx, ivertex in enumerate(active_mesh.polygons[ipoly].loop_indices):
						ivdx = active_mesh.polygons[ipoly].vertices[idx]
						if (ivdx in vc_values):
							color_map.data[ivertex].color = vc_values[ivdx]
		bpy.ops.object.mode_set(mode='VERTEX_PAINT')
		context.scene.update()
		return {'FINISHED'}

class WPLbake_uv_to_vc(bpy.types.Operator):
	bl_idname = "object.wplbake_uv_to_vc"
	bl_label = "VC: Remap UV to VC"
	bl_options = {'REGISTER', 'UNDO'}

	FacURemap = FloatVectorProperty(
			name="U Remap (0%->50%->100%)",
			description="U Remap",
			size=3,
			min=0.0, max=1.0,
			default=(0.0,0.5,1.0),
	)
	FacUMid = FloatProperty(
			name = "U midpoint",
			min=0.01, max=0.99,
			default = 0.5
	)
	FacVRemap = FloatVectorProperty(
			name = "V Remap (0%->50%->100%)",
			description="V Remap",
			size=3,
			min=0.0, max=1.0,
			default=(0.0,0.5,1.0),
	)
	FacVMid = FloatProperty(
			name = "V midpoint",
			min=0.01, max=0.99,
			default = 0.5
	)
	#OpType = bpy.props.EnumProperty(
	#	name="Operation", default="ASIS",
	#	items=(("ASIS", "U->R, V->G", ""), ("ONLYU", "U->RGB", ""), ("ONLYV", "V->RGB", ""), ("MULUV", "U*V->RGB", ""))
	#)
	ROp = StringProperty(
			name = "R=",
			default = "U"
	)
	GOp = StringProperty(
			name = "G=",
			default = "V"
	)
	BOp = StringProperty(
			name = "B=",
			default = "max(max(R,G),B)"
	)

	@classmethod
	def poll(self, context):
		# Check if we have a mesh object active and are in vertex paint mode
		p = context.object and context.object.data and (isinstance(context.scene.objects.active, bpy.types.Object) and isinstance(context.scene.objects.active.data, bpy.types.Mesh))
		return p

	def execute(self, context):
		print("execute ", self.bl_idname)
		active_object = context.scene.objects.active
		if active_object is None:
			return {'CANCELLED'}
		active_mesh = active_object.data
		selverts = get_selected_vertsIdx(active_mesh)
		if len(selverts) == 0:
			operator.report({'ERROR'}, "No verts selected, select some verts first")
			return {'CANCELLED'}
		vc_bakeOpts = context.scene.vc_bakeOpts
		color_map = active_object.data.vertex_colors.get(vc_bakeOpts.bake_vcnm)
		if color_map is None:
			self.report({'ERROR'}, "Target VC not found")
			return {'CANCELLED'}
		uv_layer = active_mesh.uv_textures.active
		if uv_layer is None:
			self.report({'ERROR'}, "Active UV not found")
			return {'CANCELLED'}

		RopCode = None
		GopCode = None
		BopCode = None
		try:
			RopCode = compile(self.ROp, "<string>", "eval")
			GopCode = compile(self.GOp, "<string>", "eval")
			BopCode = compile(self.BOp, "<string>", "eval")
		except:
			self.report({'ERROR'}, "RGB ops: syntax error")
			return {'CANCELLED'}
		bm = bmesh.new()
		bm.from_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		uv_layer_bx = bm.loops.layers.uv.get(uv_layer.name)
		vertUvMap = {}
		for face in bm.faces:
			for vert, loop in zip(face.verts, face.loops):
				if (vert.index in selverts):
					vertUvMap[vert.index] = loop[uv_layer_bx].uv
		color_map = active_object.data.vertex_colors.get(vc_bakeOpts.bake_vcnm)
		for poly in active_mesh.polygons:
			for loop_index in range(poly.loop_start, poly.loop_start + poly.loop_total):
				vi = active_mesh.loops[loop_index].vertex_index
				if (vi in vertUvMap):
					oldColor = color_map.data[loop_index].color
					R = oldColor[0]
					G = oldColor[1]
					B = oldColor[2]
					U = getPitValue(vertUvMap[vi][0],1.0,self.FacUMid,self.FacURemap)
					V = getPitValue(vertUvMap[vi][1],1.0,self.FacVMid,self.FacVRemap)
					newR = eval(RopCode)
					newG = eval(GopCode)
					newB = eval(BopCode)
					color_map.data[loop_index].color = (newR,newG,newB)
		color_map.active = True
		bpy.ops.object.mode_set(mode='VERTEX_PAINT')
		return {'FINISHED'}

class WPLvert_selvccol( bpy.types.Operator ):
	bl_idname = "mesh.wplvert_selvccol"
	bl_label = "Pick faces by Brush color"
	bl_options = {'REGISTER', 'UNDO'}
	opt_colFuzz = bpy.props.FloatProperty(
		name		= "HSV color distance",
		default	 = 0.3
	)
	@classmethod
	def poll( cls, context ):
		return ( context.object is not None  and
				context.object.type == 'MESH' and
				context.area.type == 'VIEW_3D' and context.vertex_paint_object)

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
		active_object = context.scene.objects.active
		active_mesh = active_object.data
		if not active_mesh.vertex_colors:
			self.report({'ERROR'}, "Active object has no Vertex color layer")
			return {'CANCELLED'}
		select_and_change_mode(active_object,"VERTEX_PAINT")
		active_mesh.use_paint_mask = True
		br = self.current_brush(context)
		if br:
			#print("brush color:",br.color)
			basecol = Vector((br.color[0],br.color[1],br.color[2]))
			baselayr = active_mesh.vertex_colors.active
			vertx2sel = []
			for ipoly in range(len(active_mesh.polygons)):
				for idx, ivertex in enumerate(active_mesh.polygons[ipoly].loop_indices):
					ivdx = active_mesh.polygons[ipoly].vertices[idx]
					if (ivdx not in vertx2sel) and (baselayr.data[ivertex].color is not None):
						vcol = baselayr.data[ivertex].color
						dist = Vector((vcol[0],vcol[1],vcol[2]))
						if (dist-basecol).length <= self.opt_colFuzz:
							#print("Near color:",dist,basecol)
							vertx2sel.append(ivdx)
			select_and_change_mode(active_object,"OBJECT")
			for idx in vertx2sel:
				active_mesh.vertices[idx].select = True
			select_and_change_mode(active_object,"EDIT")
			bpy.context.tool_settings.mesh_select_mode = (True, False, False)
			select_and_change_mode(active_object,"VERTEX_PAINT")
		return {'FINISHED'}

class WPLvert_pickvccol( bpy.types.Operator ):
	bl_idname = "mesh.wplvert_pickvccol"
	bl_label = "Pick VC color from selection"
	bl_options = {'REGISTER', 'UNDO'}
	@classmethod
	def poll( cls, context ):
		return ( context.object is not None  and
				context.object.type == 'MESH' and
				context.area.type == 'VIEW_3D' and context.vertex_paint_object)

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
		active_object = context.scene.objects.active
		active_mesh = active_object.data
		if not active_mesh.vertex_colors:
			self.report({'ERROR'}, "Active object has no Vertex color layer")
			return {'CANCELLED'}
		select_and_change_mode(active_object,"OBJECT")
		selfaces = get_selected_facesIdx(active_mesh)
		select_and_change_mode(active_object,"VERTEX_PAINT")
		if len(selfaces) < 1:
			self.report({'ERROR'}, "Not enough verts, select verts first")
			return {'CANCELLED'}
		br = self.current_brush(context)
		if br:
			baselayr = active_mesh.vertex_colors.active
			vertx2cols = None
			vertx2cnt = 0
			for ipoly in range(len(active_mesh.polygons)):
				if ipoly in selfaces:
					for idx, ivertex in enumerate(active_mesh.polygons[ipoly].loop_indices):
						ivdx = active_mesh.polygons[ipoly].vertices[idx]
						if vertx2cnt == 0:
							vertx2cols = mathutils.Vector(baselayr.data[ivertex].color)
						else:
							vertx2cols = vertx2cols + mathutils.Vector(baselayr.data[ivertex].color)
						vertx2cnt = vertx2cnt+1
			br.color = mathutils.Vector((vertx2cols[0],vertx2cols[1],vertx2cols[2]))/vertx2cnt
		return {'FINISHED'}

######### ############ ################# ############
class WPLVCBakeSettings(PropertyGroup):
	# bake_uvbase = StringProperty(
		# name="UVMap prefix",
		# description="Bake into set of UVMaps",
		# default = "MeshPt_"
		# )
	# bake_shk1 = StringProperty(
		# name="Base shapekey",
		# description="Base shapekey",
		# default = ""
		# )
	# bake_shk2 = StringProperty(
		# name="Diff shapekey",
		# description="Diff shapekey",
		# default = ""
		# )
	bake_vcnm = StringProperty(
		name="Target VC",
		description="Target VC",
		default = ""
		)

class WPLBakeMeshFeatures_Panel2(bpy.types.Panel):
	bl_label = "VC baking"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_category = 'WPL'

	def draw(self, context):
		layout = self.layout
		vc_bakeOpts = context.scene.vc_bakeOpts
		active_object = context.scene.objects.active
		col = layout.column()
		if active_object is not None and active_object.data is not None:
			vertex_colors_d = active_object.data
			if vertex_colors_d is not None:
				col.separator()
				col.label("VC: Selection")
				col.prop_search(vc_bakeOpts, "bake_vcnm", vertex_colors_d, "vertex_colors", icon='GROUP_VCOL')
				col.operator("object.wplbake_2daxis_to_vc", text="Bake Flat projection") # normalized
				col.operator("object.wplbake_2dshape_to_vc", text="Bake Shape projection") # normalized
				#col.operator("object.wplbake_3dcurdist_to_vc", text="Bake 3D-cursor distance") # normalized
				col.separator()
				col.operator("object.wplbake_rndcol_to_vc", text="Bake random color")
				col.separator()
				col.operator("object.wplbake_uv_to_vc", text="Remap UV to VC (eval)")
				# shape_keys_d = active_object.data.shape_keys
				# if shape_keys_d is not None:
					# col.separator()
					# col.label("VC: Shapekey diffs")
					# col.prop_search(vc_bakeOpts, "bake_shk1", shape_keys_d, "key_blocks", icon='SHAPEKEY_DATA')
					# col.prop_search(vc_bakeOpts, "bake_shk2", shape_keys_d, "key_blocks", icon='SHAPEKEY_DATA')
					# col.operator("object.wplbake_shpk_to_vc", text="Bake Shapekey diff")

#class WPLBakeMeshFeatures_Panel3(bpy.types.Panel):
#	bl_label = "WPL Coords into UV"
#	bl_space_type = 'VIEW_3D'
#	bl_region_type = 'TOOLS'
#	bl_category = 'WPL'
#	def draw(self, context):
#		layout = self.layout
#		vc_bakeOpts = context.scene.vc_bakeOpts
#		active_object = context.scene.objects.active
#		col = layout.column()
#		if active_object is not None and active_object.data is not None:
#			col.label("UV: Selection")
#			col.prop(vc_bakeOpts, "bake_uvbase")
#			col.operator("object.wplbake_mesh_centers", text="Bake 2d-Axis (View Proj)").actionType = 4
#			col.operator("object.wplbake_mesh_centers", text="Bake offset: 3D Cursor").actionType = 3
#			col.operator("object.wplbake_mesh_centers", text="Bake offset: Mesh-mids").actionType = 2
#			col.operator("object.wplbake_mesh_centers", text="Bake local: 3D Cursor").actionType = 5
#			col.operator("object.wplbake_mesh_centers", text="Bake local: Mesh-mids").actionType = 6

class WPLPaintSelect_Panel(bpy.types.Panel):
	bl_label = "WPL: VC Selection"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_category = 'Tools'

	def draw_header(self, context):
		layout = self.layout
		layout.label(text="")

	def draw(self, context):
		layout = self.layout
		col = layout.column()

		col.separator()
		col.operator("mesh.wplvert_pickvccol", text="Pick color from faces")
		col.operator("mesh.wplvert_selvccol", text="Pick faces by Brush color")

def register():
	print("WPLBakeMeshFeatures_Panel register")
	bpy.utils.register_module(__name__)
	bpy.types.Scene.vc_bakeOpts = PointerProperty(type=WPLVCBakeSettings)

def unregister():
	print("WPLBakeMeshFeatures_Panel unregister")
	bpy.utils.unregister_module(__name__)
	del bpy.types.Scene.vc_bakeOpts
	bpy.utils.unregister_class(WPLVCBakeSettings)

if __name__ == "__main__":
	register()
