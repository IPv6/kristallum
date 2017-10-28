import bpy
import bmesh
import math
import mathutils
import copy
from mathutils import Vector
from random import random, seed
from mathutils.bvhtree import BVHTree
from bpy_extras import view3d_utils
from bpy_extras.object_utils import world_to_camera_view

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
	"name": "WPL Mesh Helpers",
	"author": "IPv6",
	"version": (1, 0),
	"blender": (2, 78, 0),
	"location": "View3D > T-panel > WPL",
	"description" : "",
	"warning"	 : "",
	"wiki_url"	: "",
	"tracker_url" : "",
	"category"	: ""
	}

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

def get_selected_facesIdx(active_mesh):
	# find selected faces
	bpy.ops.object.mode_set(mode='OBJECT')
	faces = [f.index for f in active_mesh.polygons if f.select]
	# print("selected faces: ", faces)
	return faces

def get_selected_edgesIdx(active_mesh):
	# find selected faces
	bpy.ops.object.mode_set(mode='OBJECT')
	selectedEdgesIdx = [e.index for e in active_mesh.edges if e.select]
	return selectedEdgesIdx

def get_selected_vertsIdx(active_mesh):
	# find selected faces
	bpy.ops.object.mode_set(mode='OBJECT')
	selectedVertsIdx = [e.index for e in active_mesh.vertices if e.select]
	return selectedVertsIdx

def visibilitySelect(active_object, active_mesh, context, actionSelectType, fuzz):
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
					co_world = active_object.matrix_world * vert.co + mathutils.Vector(fuzzpic)
					direction = co_world - cameraOrigin;
					direction.normalize()
					result, location, normal, faceIndex, object, matrix = scene.ray_cast( cameraOrigin, direction )
					#print ("result",result," faceIndex",faceIndex," vert",vert, " verts", bm.faces[faceIndex].verts)
					if result and object.name == active_object.name:
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

class WPLvert_selvccol( bpy.types.Operator ):
	bl_idname = "mesh.wplvert_selvccol"
	bl_label = "Select by VC color"
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
			return {'FINISHED'}
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
							print("Near color:",dist,basecol)
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
			return {'FINISHED'}
		select_and_change_mode(active_object,"OBJECT")
		selfaces = get_selected_facesIdx(active_mesh)
		select_and_change_mode(active_object,"VERTEX_PAINT")
		if len(selfaces) < 1:
			self.report({'ERROR'}, "Not enough verts, select verts first")
			return {'FINISHED'}
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
		active_object = context.scene.objects.active
		active_mesh = active_object.data
		visibilitySelect(active_object, active_mesh, context, 0, self.opt_rayFuzz )
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
		active_object = context.scene.objects.active
		active_mesh = active_object.data
		visibilitySelect(active_object, active_mesh, context, 1, self.opt_rayFuzz )
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
		active_object = context.scene.objects.active
		active_mesh = active_object.data
		visibilitySelect(active_object, active_mesh, context, 2, self.opt_rayFuzz )
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
		default	 = 100
	)
	opt_floodFuzz = FloatProperty(
		name	 = "Max angle to select",
		default	 = 0.3
	)
	opt_floodContinue = FloatProperty(
		name	 = "Max angle to flood",
		default	 = 1.6
	)
	@classmethod
	def poll( cls, context ):
		return ( context.object is not None  and
				context.object.type == 'MESH' )

	def execute( self, context ):
		active_object = context.scene.objects.active
		active_mesh = active_object.data
		selverts = get_selected_vertsIdx(active_mesh)
		if len(selverts) == 0:
			self.report({'ERROR'}, "No selected verts found, select some")
			return {'FINISHED'}
		select_and_change_mode(active_object, 'EDIT')
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
		for stage in range(1,self.opt_floodDist+1):
			stage_verts = {}
			checked_verts_cc = copy.copy(checked_verts)
			for v_idx in checked_verts_cc:
				v = bm.verts[v_idx]
				for edg in v.link_edges:
					v2 = edg.other_vert(v)
					if v2.index not in checked_verts_cc:
						flowfir = (v2.co-v.co).normalized()
						flowdot = flowfir.dot(floodDir)
						flowang = math.acos(flowdot)
						if(flowang < self.opt_floodFuzz):
							v2.select = True
						if(flowang < self.opt_floodContinue):
							if v2.index not in checked_verts:
								checked_verts.append(v2.index)
							if(v2.index not in stage_verts):
								stage_verts[v2.index] = []
							if v_idx not in stage_verts[v2.index]:
								stage_verts[v2.index].append(v_idx)
			if len(stage_verts) == 0:
				break
			#propagation_stages.append(stage_verts)
		return {'FINISHED'}

class WPLSelectFeatures_Panel(bpy.types.Panel):
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

		col.separator()
		col.label("Selection control")
		col.operator("mesh.wplvert_selvisible", text="Select visible")
		col.operator("mesh.wplvert_deselvisible", text="Deselect visible")
		col.operator("mesh.wplvert_deselunvisible", text="Deselect invisible")
		col.separator()
		col.operator("mesh.wplvert_floodsel", text="Flood-select linked")

class WPLPaintSelect_Panel(bpy.types.Panel):
	bl_label = "VC Selection helpers"
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
		col.operator("mesh.wplvert_selvccol", text="Select by VC color")

def register():
	print("WPLSelectFeatures_Panel registered")
	bpy.utils.register_module(__name__)

def unregister():
	bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
	register()
