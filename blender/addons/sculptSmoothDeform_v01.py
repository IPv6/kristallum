# TBD: mix deform between original pos and current one
# TBD: recast movements basing on face normal+offset
# TBD: simple "collisions" - "normals" raycasting+mindist


import bpy
import bmesh
import math
import copy
import mathutils
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
	"name": "WPL Smooth Deforming",
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

kRaycastEpsilon = 0.01
kWPLSmoothHolderUVMap1 = "_tmpPosHolder1"
kWPLSmoothHolderUVMap2 = "_tmpPosHolder2"
#class WPLSMTHDEF_G:
#	mesh_name = ""
	#mesh_snap = {}

######################### ######################### #########################
######################### ######################### #########################
def force_visible_object(obj):
	if obj:
		if obj.hide == True:
			obj.hide = False
		for n in range(len(obj.layers)):
			obj.layers[n] = False
		current_layer_index = bpy.context.scene.active_layer
		obj.layers[current_layer_index] = True
def unselect_all():
	for obj in bpy.data.objects:
		obj.select = False
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

def get_selected_vertsIdx(active_mesh):
	# find selected faces
	bpy.ops.object.mode_set(mode='OBJECT')
	selectedVertsIdx = [e.index for e in active_mesh.vertices if e.select]
	return selectedVertsIdx
######################### ######################### #########################
######################### ######################### #########################
class WPLsmthdef_snap(bpy.types.Operator):
	bl_idname = "mesh.wplsmthdef_snap"
	bl_label = "Remember mesh state"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(self, context):
		# Check if we have a mesh object active and are in vertex paint mode
		p = context.object and context.object.data and (isinstance(context.scene.objects.active, bpy.types.Object) and isinstance(context.scene.objects.active.data, bpy.types.Mesh))
		return p

	def execute(self, context):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		select_and_change_mode(active_obj, 'EDIT')
		edit_obj = bpy.context.edit_object
		active_mesh = edit_obj.data
		uv_layer_holdr1 = active_mesh.uv_textures.get(kWPLSmoothHolderUVMap1)
		if uv_layer_holdr1 is None:
			active_mesh.uv_textures.new(kWPLSmoothHolderUVMap1)
		uv_layer_holdr2 = active_mesh.uv_textures.get(kWPLSmoothHolderUVMap2)
		if uv_layer_holdr2 is None:
			active_mesh.uv_textures.new(kWPLSmoothHolderUVMap2)
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		uv_layer_holdr1 = bm.loops.layers.uv.get(kWPLSmoothHolderUVMap1)
		uv_layer_holdr2 = bm.loops.layers.uv.get(kWPLSmoothHolderUVMap2)
		for face in bm.faces:
			for vert, loop in zip(face.verts, face.loops):
				loop[uv_layer_holdr1].uv = (vert.co[0],vert.co[1])
				loop[uv_layer_holdr2].uv = (vert.co[2],0)
		return {'FINISHED'}
		
class WPLsmthdef_apply(bpy.types.Operator):
	bl_idname = "mesh.wplsmthdef_apply"
	bl_label = "Apply mesh deformations"
	bl_options = {'REGISTER', 'UNDO'}

	SmoothingLoops = FloatProperty(
			name="Smoothing Loops",
			description="Loops",
			min=0.0, max=1000.0,
			default=3.0,
	)
	Sloppiness = FloatProperty(
			name="Sloppiness",
			description="Sloppiness",
			min=0.0, max=100.0,
			default=1.0,
	)

	@classmethod
	def poll(self, context):
		# Check if we have a mesh object active and are in vertex paint mode
		p = context.object and context.object.data and (isinstance(context.scene.objects.active, bpy.types.Object) and isinstance(context.scene.objects.active.data, bpy.types.Mesh))
		return p

	def execute(self, context):
		active_obj = context.scene.objects.active
		active_mesh = active_obj.data
		#if WPLSMTHDEF_G.mesh_name != active_obj.name:
		if (active_mesh.uv_textures.get(kWPLSmoothHolderUVMap1) is None) or (active_mesh.uv_textures.get(kWPLSmoothHolderUVMap2) is None):
			self.report({'ERROR'}, "This object not snapped, snap mesh first")
			return {'FINISHED'}
		selverts = get_selected_vertsIdx(active_mesh)
		select_and_change_mode(active_obj, 'EDIT')
		edit_obj = bpy.context.edit_object
		active_mesh = edit_obj.data
		bm = bmesh.from_edit_mesh(active_mesh)
		bm.verts.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.index_update()
		verts_map = {}
		uv_layer_holdr1 = bm.loops.layers.uv.get(kWPLSmoothHolderUVMap1)
		uv_layer_holdr2 = bm.loops.layers.uv.get(kWPLSmoothHolderUVMap2)
		for face in bm.faces:
			for vert, loop in zip(face.verts, face.loops):
				verts_map[vert.index] = mathutils.Vector((loop[uv_layer_holdr1].uv[0], loop[uv_layer_holdr1].uv[1], loop[uv_layer_holdr2].uv[0]))
		if len(selverts) == 0:
			selverts = []
			for v in bm.verts:
				if verts_map[v.index] is not None:
					if (v.co-verts_map[v.index]).length > kRaycastEpsilon:
						# vert moved
						selverts.append(v.index)
		if len(selverts) == 0:
			self.report({'ERROR'}, "No moved/selected verts found")
			return {'FINISHED'}
		checked_verts = copy.copy(selverts)
		verts_shifts = {}
		propagation_stages = []
		for stage in range(1,int(self.SmoothingLoops)+1):
			stage_verts = {}
			checked_verts_cc = copy.copy(checked_verts)
			for v_idx in checked_verts_cc:
				v = bm.verts[v_idx]
				if (v_idx not in verts_shifts) and (v_idx in verts_map):
					verts_shifts[v_idx] = mathutils.Vector(v.co - verts_map[v_idx])
				for edg in v.link_edges:
					v2 = edg.other_vert(v)
					if v2.index not in checked_verts_cc:
						#print("found new vert",v2.index,"at stage",stage)
						#v2.select = True
						if v2.index not in checked_verts:
							checked_verts.append(v2.index)
						if(v2.index not in stage_verts):
							stage_verts[v2.index] = []
						if v_idx not in stage_verts[v2.index]:
							stage_verts[v2.index].append(v_idx)
			if len(stage_verts) == 0:
				break
			propagation_stages.append(stage_verts)
		#print("vert stages",propagation_stages)
		#print("verts_shifts",verts_shifts)
		stage_cnt = 1.0
		for stage_verts in propagation_stages:
			stage_weight = pow(1.0-stage_cnt/len(propagation_stages),self.Sloppiness)
			#print("processing vert stage",stage_verts)
			for s_idx in stage_verts:
				avg_shift = mathutils.Vector((0,0,0))
				avg_count = 0.0
				for p_idx in stage_verts[s_idx]:
					avg_shift = avg_shift+verts_shifts[p_idx]
					avg_count = avg_count+1.0
				if avg_count>0:
					s_shift = mathutils.Vector(avg_shift)/avg_count
					verts_shifts[s_idx] = s_shift
					s_v = bm.verts[s_idx]
					#print("shifting vert",s_idx, s_v.index, s_v.co,verts_map[s_idx])
					s_v.co = s_v.co+s_shift*stage_weight
			stage_cnt = stage_cnt+1.0
		bm.normal_update()
		bmesh.update_edit_mesh(active_mesh, True)
		return {'FINISHED'}

class WPLSmoothDeform_Panel(bpy.types.Panel):
	bl_label = "Smooth Deforming"
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
		col.operator("mesh.wplsmthdef_snap", text="Remember mesh state")
		col.operator("mesh.wplsmthdef_apply", text="Apply mesh deformations")

def register():
	print("WPLSmoothDeform_Panel registered")
	bpy.utils.register_module(__name__)

def unregister():
	bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
	register()
