# Operators:
# - Project mesh features into vertex color or UV-map (since vertext color limited to 255 gradations) for future use in material nodes
# TBD: Use normal-dispersion to get gradients. Much better than 3d-distance for mimicing geodesics

import bpy
import bmesh
import math
import mathutils
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
	"location": "View3D > Paint > Bake mesh features into VC",
	"description": "Bake mesh features of selected faces into active vertext color layer.",
	"warning": "",
	"wiki_url": "",
	"tracker_url": "",
	"category": "Paint"}

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
			color_map.data[vertex_data[0]].color = (xrel,yrel,drel)
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
			color_map.data[vertex_data[0]].color = (xrel,yrel,nrel)
	if vc_refmode == "dist":
		glob_refpoint2d = location_to_region(glob_refpoint)
		maxlen3d = 0
		minlen3d = 9999
		maxlen2d = 0
		minlen2d = 9999
		for vertex_data in paint_list:
			vec = vertex_data[1]-glob_refpoint
			vec2d = vertex_data[3]-glob_refpoint2d
			maxlen3d = max(maxlen3d,vec.length)
			minlen3d = min(minlen3d,vec.length)
			maxlen2d = max(maxlen2d,vec2d.length)
			minlen2d = min(minlen2d,vec2d.length)
		for vertex_data in paint_list:
			vec3d = vertex_data[1]-glob_refpoint
			reldist3d = (vec3d.length-minlen3d)/(maxlen3d-minlen3d)
			vec2d = vertex_data[3]-glob_refpoint2d
			reldist2d = (vec2d.length-minlen2d)/(maxlen2d-minlen2d)
			color_map.data[vertex_data[0]].color = (reldist3d,reldist2d,vec3d.length*0.1)
		return
	return

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
	
def get_selected_facesIdx(active_mesh):
	# find selected faces
	bpy.ops.object.mode_set(mode='OBJECT')
	faces = [f.index for f in active_mesh.polygons if f.select]
	# print("selected faces: ", faces)
	return faces

def op_find_and_paint(context, operator, active_object, vc_refmode):
	if not (bpy.context.active_object.mode == 'VERTEX_PAINT') or not (bpy.context.active_object.data.use_paint_mask):
		operator.report({'ERROR'}, "Use face masking mode, while in Vertex Paint mode")
		return
	active_mesh = active_object.data
	#cursor = active_object.matrix_world.inverted()*get_active_context_cursor(context)
	cursor = get_active_context_cursor(context)
	# use active color map, create one if none available
	if not active_mesh.vertex_colors:
		active_mesh.vertex_colors.new()
	color_map = active_mesh.vertex_colors.active

	faces = get_selected_facesIdx(active_mesh)
	# print("selected faces: ", faces)
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

class bakeCursorDistanceToVc(bpy.types.Operator):
	bl_idname = "object.bake_cursor_distance_to_vc"
	bl_label = "bakeCursorDistanceToVc"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(self, context):
		# Check if we have a mesh object active and are in vertex paint mode
		p = (isinstance(context.scene.objects.active, bpy.types.Object) and
			isinstance(context.scene.objects.active.data, bpy.types.Mesh))
		return p

	def execute(self, context):
		print("execute ", self.bl_idname)
		active_object = context.scene.objects.active
		if active_object is not None:
			active_object.data.use_paint_mask = True
		op_find_and_paint(context, self, active_object, "dist")
		bpy.ops.object.mode_set(mode='VERTEX_PAINT')
		context.scene.update()
		return {'FINISHED'}

class bakeProj2dAxisToVc(bpy.types.Operator):
	bl_idname = "object.bake_2daxis_to_vc"
	bl_label = "bakeProj2dAxisToVc"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(self, context):
		# Check if we have a mesh object active and are in vertex paint mode
		p = (isinstance(context.scene.objects.active, bpy.types.Object) and
			isinstance(context.scene.objects.active.data, bpy.types.Mesh))
		return p

	def execute(self, context):
		print("execute ", self.bl_idname)
		active_object = context.scene.objects.active
		bpy.ops.object.mode_set(mode='VERTEX_PAINT')
		if active_object is not None:
			active_object.data.use_paint_mask = True
		op_find_and_paint(context, self, active_object, "axis")
		bpy.ops.object.mode_set(mode='VERTEX_PAINT')
		context.scene.update()
		return {'FINISHED'}

class bakeShape2dAxisToVc(bpy.types.Operator):
	bl_idname = "object.bake_2dshape_to_vc"
	bl_label = "bakeShape2dAxisToVc"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(self, context):
		# Check if we have a mesh object active and are in vertex paint mode
		p = (isinstance(context.scene.objects.active, bpy.types.Object) and
			isinstance(context.scene.objects.active.data, bpy.types.Mesh))
		return p

	def execute(self, context):
		print("execute ", self.bl_idname)
		active_object = context.scene.objects.active
		bpy.ops.object.mode_set(mode='VERTEX_PAINT')
		if active_object is not None:
			active_object.data.use_paint_mask = True
		op_find_and_paint(context, self, active_object, "shape")
		bpy.ops.object.mode_set(mode='VERTEX_PAINT')
		context.scene.update()
		return {'FINISHED'}

class bakeMeshCentersToVc(bpy.types.Operator):
	bl_idname = "object.bake_mesh_centers_to_vc"
	bl_label = "bakeMeshCentersToVc"
	bl_options = {'REGISTER', 'UNDO'}
	actionType = bpy.props.IntProperty()

	@classmethod
	def poll(self, context):
		# Check if we have a mesh object active and are in vertex paint mode
		p = (isinstance(context.scene.objects.active, bpy.types.Object) and
			isinstance(context.scene.objects.active.data, bpy.types.Mesh))
		return p

	def execute(self, context):
		print("execute ", self.bl_idname, type)
		operator = self
		bakeOpts = context.scene.bakeOpts
		active_object = context.scene.objects.active
		cursor = active_object.matrix_world.inverted()*get_active_context_cursor(context)
		print ("cursor position: ", cursor)
		active_mesh = active_object.data
		selfaces = get_selected_facesIdx(active_mesh)
		if len(selfaces) == 0:
			operator.report({'ERROR'}, "No faces selected, select some faces first")
			return {'FINISHED'}
		bpy.ops.object.mode_set(mode='OBJECT')

		if self.actionType == 2 or self.actionType == 6 or self.actionType == 3 or self.actionType == 5:
			bakemap_pref = bakeOpts.bake_uvbase
			bakemap_x = bakemap_pref+"X"
			uv_layer_bx = active_mesh.uv_textures.get(bakemap_x)
			if uv_layer_bx is None:
				active_mesh.uv_textures.new(bakemap_x)
			bakemap_y = bakemap_pref+"Y"
			uv_layer_by = active_mesh.uv_textures.get(bakemap_y)
			if uv_layer_by is None:
				active_mesh.uv_textures.new(bakemap_y)
			bakemap_z = bakemap_pref+"Z"
			uv_layer_bz = active_mesh.uv_textures.get(bakemap_z)
			if uv_layer_bz is None:
				active_mesh.uv_textures.new(bakemap_z)

		if self.actionType == 4:
			bakemap_pref = bakeOpts.bake_uvbase
			bakemap_a = bakemap_pref+"A"
			uv_layer_ba = active_mesh.uv_textures.get(bakemap_a)
			if uv_layer_ba is None:
				active_mesh.uv_textures.new(bakemap_a)

		bm = bmesh.new()
		bm.from_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()

		uv_values1 = {}
		uv_values2 = {}
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
					if self.actionType == 1:
						rndc = (random(),random(),random())
						for mv in meshlist:
							vc_values[mv.index] = rndc
					elif self.actionType == 2 or self.actionType == 6:
						medianpoint = mathutils.Vector()
						for mv in meshlist:
							medianpoint = medianpoint+mv.co
						medianpoint = medianpoint/len(meshlist)
						median_maxx = 0;
						median_maxy = 0;
						median_maxz = 0;
						for mv in meshlist:
							median_maxx = max(median_maxx, abs(mv.co[0]-medianpoint[0]))
							median_maxy = max(median_maxy, abs(mv.co[1]-medianpoint[1]))
							median_maxz = max(median_maxz, abs(mv.co[2]-medianpoint[2]))
						mediandivers = (median_maxx, median_maxy, median_maxz)
						print ("Mesh median: ", medianpoint, mediandivers)
						for mv in meshlist:
							if self.actionType == 2:
								uv_values1[mv.index] = (medianpoint-mv.co, mediandivers)
							else:
								uv_values1[mv.index] = (medianpoint, mediandivers)
					elif self.actionType == 3 or self.actionType == 5:
						median_maxx = 0;
						median_maxy = 0;
						median_maxz = 0;
						for mv in meshlist:
							median_maxx = max(median_maxx, abs(mv.co[0]-cursor[0]))
							median_maxy = max(median_maxy, abs(mv.co[1]-cursor[1]))
							median_maxz = max(median_maxz, abs(mv.co[2]-cursor[2]))
						mediandivers = (median_maxx, median_maxy, median_maxz)
						for mv in meshlist:
							if self.actionType == 3:
								uv_values1[mv.index] = (cursor-mv.co, mediandivers)
							else:
								uv_values1[mv.index] = (cursor, mediandivers)
					elif self.actionType == 4:
						min_x = 9999
						min_y = 9999
						max_x = 0
						max_y = 0
						for mv in meshlist:
							co_world = active_object.matrix_world * mv.co
							vec2d = location_to_region(co_world)
							max_x = max(max_x,vec2d[0])
							max_y = max(max_y,vec2d[1])
							min_x = min(min_x,vec2d[0])
							min_y = min(min_y,vec2d[1])
						projscale = min((max_x-min_x),(max_y-min_y))
						for mv in meshlist:
							co_world = active_object.matrix_world * mv.co
							vec2d = location_to_region(co_world)
							xrel = (vec2d[0]-min_x)/projscale
							yrel = (vec2d[1]-min_y)/projscale
							uv_values2[mv.index] = (xrel, yrel)
		ok_count = 0;
		if len(vc_values)>0:
			if not active_mesh.vertex_colors:
				active_mesh.vertex_colors.new()
			color_map = active_mesh.vertex_colors.active
			for poly in active_mesh.polygons:
				face_is_selected = poly.index in selfaces
				if face_is_selected:
					for loop_index in range(poly.loop_start, poly.loop_start + poly.loop_total):
						vi = active_mesh.loops[loop_index].vertex_index
						if (vi in vc_values):#(vi in selverts) and
							color_map.data[loop_index].color = vc_values[vi]
		if len(uv_values1)>0:
			uv_layer_bx = bm.loops.layers.uv.get(bakemap_x)
			uv_layer_by = bm.loops.layers.uv.get(bakemap_y)
			uv_layer_bz = bm.loops.layers.uv.get(bakemap_z)
			for face in bm.faces:
				for vert, loop in zip(face.verts, face.loops):
					if (vert.index in selverts) and (vert.index in uv_values1):
						loop[uv_layer_bx].uv = (uv_values1[vert.index][0][0],uv_values1[vert.index][1][0])
						loop[uv_layer_by].uv = (uv_values1[vert.index][0][1],uv_values1[vert.index][1][1])
						loop[uv_layer_bz].uv = (uv_values1[vert.index][0][2],uv_values1[vert.index][1][2])
						ok_count = ok_count+1
			bm.to_mesh(active_mesh)
		if len(uv_values2)>0:
			uv_layer_ba = bm.loops.layers.uv.get(bakemap_a)
			for face in bm.faces:
				for vert, loop in zip(face.verts, face.loops):
					if (vert.index in selverts) and (vert.index in uv_values2):
						loop[uv_layer_ba].uv = uv_values2[vert.index]
						ok_count = ok_count+1
			bm.to_mesh(active_mesh)
		bm.free()
		context.scene.update()
		print("Vertices baked:", ok_count)
		bpy.ops.object.mode_set(mode='EDIT')
		return {'FINISHED'}


class BakeSettings(PropertyGroup):
	bake_uvbase = StringProperty(
		name="UVMap prefix",
		description="Bake into set of UVMaps",
		default = "MeshPt_"
		)
#	bake_shift = FloatProperty(
#		name = "Baking shift",
#		description = "Shift to make values positive",
#		default = 5.0
#		)
#	bake_scale = FloatProperty(
#		name = "Baking scale",
#		description = "Scale to fit 0..1, after shift",
#		default = 0.1
#		)

class BakeFeatures2VC_Panel(bpy.types.Panel):
	bl_label = "Bake Mesh Features"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'

	def draw_header(self, context):
		layout = self.layout
		layout.label(text="")

	def draw(self, context):
		layout = self.layout
		bakeOpts = context.scene.bakeOpts

		col = layout.column()
		col.label("Bake to VCol")
		col.operator("object.bake_2daxis_to_vc", text="Bake Flat projection)") # normalized
		col.operator("object.bake_2dshape_to_vc", text="Bake Shape projection") # normalized
		col.operator("object.bake_cursor_distance_to_vc", text="Bake 3D-cursor distance") # normalized
		col.operator("object.bake_mesh_centers_to_vc", text="Bake random color").actionType = 1
		col.separator()

		# display the properties
		col.label("Bake to UVMap")
		col.prop(bakeOpts, "bake_uvbase")
		col.operator("object.bake_mesh_centers_to_vc", text="Bake 2d-Axis (View Proj)").actionType = 4
		col.operator("object.bake_mesh_centers_to_vc", text="Bake offset: 3D Cursor").actionType = 3
		col.operator("object.bake_mesh_centers_to_vc", text="Bake offset: Mesh-mids").actionType = 2
		col.operator("object.bake_mesh_centers_to_vc", text="Bake local: 3D Cursor").actionType = 5
		col.operator("object.bake_mesh_centers_to_vc", text="Bake local: Mesh-mids").actionType = 6

def register():
	print("BakeFeatures2VC_Panel registered")
	bpy.utils.register_module(__name__)
	bpy.types.Scene.bakeOpts = PointerProperty(type=BakeSettings)

def unregister():
	bpy.utils.unregister_module(__name__)
	del bpy.types.Scene.bakeOpts

if __name__ == "__main__":
	register()

#https://raw.githubusercontent.com/varkenvarken/blenderaddons/master/connectedvertexcolors%20.py
#https://raw.githubusercontent.com/selfsame/vcol-compositor/master/bake_vertex_diffuse.py
#https://blender.stackexchange.com/questions/30841/how-to-view-vertex-colors
#https://github.com/zeffii/TubeTool

#https://blender.stackexchange.com/questions/40974/how-to-delete-all-faces-with-distance-to-other-object
#https://github.com/meta-androcto/blenderpython/blob/master/scripts/addons_extern/mesh_align_to_gpencil_view.py
#https://blenderartists.org/forum/showthread.php?393477-Geodesics-on-Surfaces

#https://blender.stackexchange.com/questions/882/how-to-find-image-coordinates-of-the-rendered-vertex
#https://blender.stackexchange.com/questions/43335/how-do-i-get-knife-project-operator-to-use-view-settings-within-the-operator
#https://blenderartists.org/forum/showthread.php?327216-How-to-access-the-view-3d-camera

#https://docs.blender.org/api/blender_python_api_current/
#https://docs.blender.org/api/blender_python_api_current/search.html?q=bmesh
#https://docs.blender.org/api/blender_python_api_current/mathutils.geometry.html